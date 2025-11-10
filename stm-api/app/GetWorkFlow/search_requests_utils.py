import sys
sys.path.append('..')
import json
import logging
import time
import numpy as np
import pandas as pd
from typing import List
import asyncio
import pyodbc
import requests
import httpx
from datetime import datetime, timezone
from app.Elastic.initialize_elastic_index import continue_scroll_elastic_requests, start_scroll_elastic_requests
from shared.all_envs import *

from shared.db import DB
from app import api

from app.Elastic.elastic_api_index import initialize_elastic_connection
from app.Elastic.elastic_settings import query_fields, make_elastic_query

logger = logging.getLogger("API log")

# Map skill attribute name in skill configuration to its corresponding request attribute name in the request DataFrame
skillAttribute_to_requestAttribute_mapping = {
       'requestSource'         : 'source_requestSource',
       'product'               : 'workOrder_product',
       'serviceRegion'         : 'source_serviceRegion',
       'customerSupportModel'  : 'source_customerSupportModel',
       'controlDesk'           : 'workOrder_controlDesk',
       'goldenCustomer'        : 'source_goldenCustomer_id',
       'customerMarketSegment' : 'source_customerMarketSegment',
       'preferredlanguage'     : 'source_preferredLanguage',
       'requestType'           : 'source_requestType'
}

async def absent_agents_async(mssql_conn: object) -> List:
    """
    Asynchronously retrieve a list of absent agents from the MSSQL database.

    This function wraps the synchronous absent_agents_sync function to execute 
    in a non-blocking manner using an asyncio event loop.

    Args:
        mssql_conn (object): Database connection object for MSSQL.

    Returns:
        List: A list of IDs for absent agents.
    """
    loop = asyncio.get_running_loop()
    absent_agent_ids = await loop.run_in_executor(None, absent_agents_sync, mssql_conn)
    return absent_agent_ids

def absent_agents_sync(mssql_conn: object) -> List:
    """
    Synchronously retrieve a list of absent agents from the MSSQL database.

    Queries the agent table in the database to fetch all agent IDs marked as absent.

    Args:
        mssql_conn (object): Database connection object for MSSQL.

    Returns:
        List: A list of IDs for absent agents.
    """
    with mssql_conn() as conn:
        cur = conn.cursor()
        sql_absent_agents = f"SELECT agent_id FROM {DB.agent()} WHERE is_absent = 'True';"
        absent_agent_ids = [agent[0] for agent in cur.execute(sql_absent_agents).fetchall()]
    return absent_agent_ids

async def get_requests_from_smartpath_elastic(date, limit, filter_comp) -> list:
    """
    Asynchronously fetch requests from Smartpath ElasticSearch with retry logic and timeout handling.

    Uses Smartpath APIs to retrieve requests updated since a given date, iterating 
    through the results using scrolling. Includes comprehensive error handling,
    retry logic, and timeout management.

    Args:
        date (str): Starting date for fetching requests.
        limit (int): Maximum number of requests to fetch in one batch.
        filter_comp (bool): Whether to apply additional filters.

    Returns:
        list: A list of request records retrieved from Smartpath ElasticSearch.
    """
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            access_token = api.auth_token
            
            logger.info(f'Starting ElasticSearch request fetch (attempt {attempt + 1}/{max_retries})')
            start_response = await start_scroll_elastic_requests(sp_vars, access_token, date, limit, filter_comp)
            start_response.raise_for_status()
            
            scroll_id = start_response.headers['x-scroll-id']
            next_scroll_response_text = json.loads(start_response.text)
            total_documents = next_scroll_response_text["metadata"]["totalRecordCount"]
            logger.info(f'Total documents to fetch: {total_documents}')
            
            next_scroll_results = next_scroll_response_text['results']
            
            while True:
                logger.info(f'Downloading smartpath request ({len(next_scroll_results)}/{total_documents})')
                
                # Break if we've reached or exceeded the total document count
                if len(next_scroll_results) >= total_documents:
                    logger.info(f'Reached total document count: {len(next_scroll_results)}/{total_documents}')
                    break
                
                try:
                    next_scroll_response_raw = await continue_scroll_elastic_requests(
                            sp_vars, access_token, date, scroll_id, filter_comp
                        )
                    next_scroll_response_raw.raise_for_status()
                    
                    # Check if response has content
                    if not next_scroll_response_raw.text:
                        logger.warning('Empty response from scroll API, ending scroll')
                        break
                        
                    try:
                        next_scroll_response_text = json.loads(next_scroll_response_raw.text)
                    except json.JSONDecodeError as json_error:
                        logger.error(f'Failed to parse JSON response from scroll API: {json_error}')
                        logger.error(f'Response text: {next_scroll_response_raw.text[:500]}...')
                        break

                    new_results = next_scroll_response_text.get('results', [])
                    if not new_results:
                        logger.info('No more results returned from scroll API')
                        break
                    
                    # Check if adding new results would exceed total count
                    if len(next_scroll_results) + len(new_results) > total_documents:
                        # Only add the remaining results needed to reach total count
                        remaining_count = total_documents - len(next_scroll_results)
                        next_scroll_results = next_scroll_results + new_results[:remaining_count]
                        logger.info(f'Limited results to total document count: {len(next_scroll_results)}/{total_documents}')
                        break
                    else:
                        next_scroll_results = next_scroll_results + new_results
                
                except httpx.TimeoutException as timeout_error:
                    logger.error(f'Timeout during scroll continuation: {timeout_error}')
                    if next_scroll_results:
                        logger.warning(f'Partial fetch completed with {len(next_scroll_results)} results due to timeout')
                        break
                    else:
                        raise timeout_error
                except httpx.HTTPStatusError as http_error:
                    logger.error(f'HTTP error during scroll continuation: {http_error.response.status_code} - {http_error.response.text}')
                    if next_scroll_results:
                        logger.warning(f'Partial fetch completed with {len(next_scroll_results)} results due to HTTP error')
                        break
                    else:
                        raise http_error       
                except Exception as scroll_error:
                    logger.error(f'Error during scroll continuation: {type(scroll_error).__name__}: {scroll_error}')
                    # If we have some results, break and return what we have
                    if next_scroll_results:
                        logger.warning(f'Partial fetch completed with {len(next_scroll_results)} results due to scroll error')
                        break
                    else:
                        # If no results yet, re-raise to trigger retry
                        raise scroll_error
            
            logger.info(f'Successfully fetched {len(next_scroll_results)} requests from ElasticSearch')
            return next_scroll_results
            
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                logger.warning(f"Request attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {max_retries} attempts failed. Last error: {e}")
                # Return empty list instead of raising exception to prevent application crash
                logger.warning("Returning empty result list due to persistent errors")
                return []

def format_df_for_search(df, query_fields):
    """
    Format and preprocess a DataFrame for searching and SLA merging.

    Processes a DataFrame of requests by:
    - Formatting timestamps.
    - Handling null values.
    - Lowercasing string values.
    - Merging SLA-related information from the SLA table.

    Args:
        df (pd.DataFrame): The DataFrame containing request data.
        query_fields (list): Fields to query in the DataFrame.

    Returns:
        pd.DataFrame: A preprocessed DataFrame ready for searching.
    """
    foc_targets = api.df_foc_targets
    df.columns = [c.replace('.', '_') for c in query_fields]

    df['lastUpdated'] = pd.to_datetime(df.lastUpdated, utc=True, format='ISO8601', errors='coerce')
    df['source_requestedStartDate'] = pd.to_datetime(df.source_requestedStartDate, format='ISO8601', errors='coerce')
    df['workOrder_followUpDate'] = pd.to_datetime(df.workOrder_followUpDate, format='ISO8601', errors='coerce')
    df['source_orderDate'] = pd.to_datetime(df.source_orderDate, format='ISO8601', errors='coerce')
    df['workOrder_expectedCompletionDate'] = pd.to_datetime(df.workOrder_expectedCompletionDate, format='ISO8601', errors='coerce')

    df.loc[df['workOrder_product'].isnull(), 'workOrder_product'] = df['source_product']

    req_attr_and_gckey_columns = ['workOrder_product', 'workOrder_controlDesk', 'source_requestType', 'source_goldenCustomer_id']
    gc_sla_merge_columns = ['source_requestType', 'source_goldenCustomer_id']
    fed_sla_merge_columns = ['source_requestType', 'workOrder_controlDesk']
    non_sla_merge_columns = ['source_requestType', 'workOrder_product']

    # Convert all the string values to lowercase in the columns to match on 
    for col in req_attr_and_gckey_columns:
        df[col] = df[col].apply(lambda x: str(x).replace(' ', '').lower() if x is not None else '')
        foc_targets[col] = foc_targets[col].apply(lambda x: str(x).replace(' ', '').lower() if x is not None else '')

    gc_sla_foc_targets = foc_targets[foc_targets['source_goldenCustomer_id'] != 'nan']
    fed_sla_foc_targets = foc_targets[foc_targets['workOrder_controlDesk'] == 'federalgov']
    non_sla_foc_targets = foc_targets[
        (foc_targets['source_goldenCustomer_id'] == 'nan') & 
        (foc_targets['workOrder_controlDesk'] == 'nan')
    ]

    sla_customers = gc_sla_foc_targets['source_goldenCustomer_id'].unique().tolist()

    # Firstly, identify federal SLA requests (these take priority)
    fed_sla_requests = df[df['workOrder_controlDesk'] == 'federalgov']

    # Then, identify golden customer SLA requests, but exclude those that are already in federal
    gc_sla_requests = df[
        (df['source_goldenCustomer_id'].isin(sla_customers)) & 
        (df['workOrder_controlDesk'] != 'federalgov') # Exclude federal requests
    ]
    
    # Non-SLA requests: everything that's not in either SLA category
    non_sla_requests = df[
        ~((df['source_goldenCustomer_id'].isin(sla_customers)) | 
          (df['workOrder_controlDesk'] == 'federalgov'))
    ]
    
    # Merge gc_sla_requests with gc_sla_foc_targets on gc_sla_merge_columns
    gc_sla_requests = gc_sla_requests.merge(
        gc_sla_foc_targets, 
        on=gc_sla_merge_columns,
        how='left',
        suffixes=('', '_y'))
    gc_sla_requests = gc_sla_requests.drop(columns=
    ['workOrder_product_y', 'workOrder_controlDesk_y'])

    # Merge fed_sla_requests with fed_sla_foc_targets on fed_sla_merge_columns
    fed_sla_requests = fed_sla_requests.merge(
        fed_sla_foc_targets, 
        on=fed_sla_merge_columns,
        how='left',
        suffixes=('', '_y'))
    fed_sla_requests = fed_sla_requests.drop(columns=
    ['workOrder_product_y', 'source_goldenCustomer_id_y'])
    
    # Merge non_sla_requests with non_sla_foc_targets on non_sla_merge_columns
    non_sla_requests = non_sla_requests.merge(
        non_sla_foc_targets,
        on=non_sla_merge_columns,
        how='left',
        suffixes=('', '_y'))
    non_sla_requests = non_sla_requests.drop(columns=['source_goldenCustomer_id_y', 'workOrder_controlDesk_y'])
    
    all_requests = pd.concat([gc_sla_requests, fed_sla_requests, non_sla_requests], ignore_index=True)
    all_requests['source_focTarget'] = all_requests['source_focTarget_new'].apply(lambda x: float(DEFAULT_TTPU) if np.isnan(x) else float(x))
    all_requests['has_sla'] = all_requests['has_sla_new'].apply(lambda x: False if ((x == 0) | (np.isnan(x))) else True)
    all_requests.drop(columns=['source_focTarget_new', 'has_sla_new'], inplace=True)

    nan_cols = [
        'accessPolicyTag', 'workOrder_controlDesk', 'workOrder_assignee_id', 'source_requestType', 'workOrder_group', 'workOrder_tags', 'workOrder_product', 'workOrder_status', 'source_customerSupportModel', 'source_product', 'source_serviceRegion', 'source_status',
        'source_goldenCustomer_id', 'source_goldenCustomer_name', 'source_customer', 'source_customerMarketSegment', 
        'source_requestSource', 'source_businessUnit', 'source_preferredLanguage', 'source_originator_email'
        ]
 
    for col in nan_cols:
        all_requests[col] = all_requests[col].fillna('nan')
        all_requests[col] = all_requests[col].apply(lambda x: x.lower() if isinstance(x, str) else x)

    # Process source_focTarget for external requests based on requestSource and email domain conditions
    # Condition 1: requestSource in specific values
    condition1 = all_requests['source_requestSource'].isin(['ssc', 'pss', 'eom', 'eomtask'])
    
    # Condition 2: requestSource is 'email' AND originator_email does NOT have Bell domain
    bell_domains = ['@bell.ca', '@bellaliant.ca', '@bellmts.ca']
    email_condition = all_requests['source_requestSource'].isin(['email', 'kana', 'egain'])
    
    # Check if email does NOT contain any of the Bell domains
    has_bell_domain = all_requests['source_originator_email'].str.contains('|'.join(bell_domains), case=False, na=False)
    condition2 = email_condition & (~has_bell_domain)
    
    # Apply 80% reduction to source_focTarget for rows meeting either condition
    external_requests = condition1 | condition2
    all_requests.loc[external_requests, 'source_focTarget'] = all_requests.loc[external_requests, 'source_focTarget'] * 0.8

    return all_requests

def clean_tags(x):
    """
    Clean and process tags in a list or string.

    Converts tags into a lowercase format, handles underscores, and concatenates multi-part 
    tags into a single string.

    Args:
        x (list or str): A tag or a list of tags to be processed.

    Returns:
        list: A processed list of cleaned tags.
    """
    def process_string(s):
        stmp = s.split('_')
        if len(stmp) == 2:
            return stmp[1].lower()
        elif len(stmp) >= 3:
            return "".join(stmp[1:]).lower()
        else:
            return s.lower()

    if isinstance(x, list):
        if not x:  # Check if the list is empty
            return ['']
        return [process_string(item) for item in x]
    else:
        return [process_string(x)]

def flatten(d, parent_key='', sep='.'):
    """
    Flatten a nested dictionary.

    Converts a nested dictionary into a flat dictionary with keys representing the hierarchy using a separator.

    Args:
        d (dict): The dictionary to flatten.
        parent_key (str, optional): The base key for the current level of nesting. Defaults to ''.
        sep (str, optional): Separator used to indicate nesting levels in keys. Defaults to '.'.

    Returns:
        dict: A flattened dictionary.
    """
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key != '' else k
        if isinstance(v, dict):
            items.update(flatten(v, new_key, sep=sep))
        else:
            if new_key == 'id':
                new_key = 'request_id'
            items[new_key] = v
    return items

def elastic_response_to_df(response, query_fields):
    """
    Convert an ElasticSearch response into a DataFrame.

    Processes a dictionary response from ElasticSearch, flattens it, and applies filtering and cleaning.

    Args:
        response (dict): The ElasticSearch response.
        query_fields (list): List of fields to include in the DataFrame.

    Returns:
        pd.DataFrame: A DataFrame containing the processed ElasticSearch data.
    """
    # Flatten each dictionary in the response
    flattened_response = [flatten(d) for d in response]
    # Create a dataframe using the flattened response
    df = pd.DataFrame(flattened_response, columns=query_fields)
    result = format_df_for_search(df, query_fields)
    
    result = clean_tags_column(result)
    result = result[
        (result['accessPolicyTag'].astype(bool)) & 
        (~result['accessPolicyTag'].apply(lambda x: any("test" in s.lower() for s in x)))
    ]
    return result

def clean_tags_column(df):
    """
    Clean and preprocess the 'tags' column in a DataFrame.

    Processes each tag or list of tags in the specified column to standardize their format.

    Args:
        df (pd.DataFrame): The DataFrame containing a 'tags' column.

    Returns:
        pd.DataFrame: The DataFrame with cleaned tags.
    """
    # Function to process each tag
    def process_tag(tag):
        if not tag or isinstance(tag, float):  # handle NaNs and None
            return ''
        parts = tag.split('_')
        return "".join(parts[1:]).lower() if len(parts) > 1 else tag.lower()

    # Function to process a list of tags
    def process_tags(tags):
        if isinstance(tags, list):
            return [process_tag(tag) for tag in tags]
        else:
            return [process_tag(tags)]
        
    for col in ['accessPolicyTag']:
        df[col] = df[col].apply(process_tags)

    return df

def pre_process(permission_list):
    """
    Preprocess a list of permissions.

    Removes unnecessary elements from permission strings and converts them to lowercase.

    Args:
        permission_list (list): A list of permission strings.

    Returns:
        list: A processed list of permissions.
    """
    #pre-processing on the permission list
    #example permissions = ['OC-SmartPath-GoC-Level2','OC-SmartPath-Retail' , 'OC-SmartPath-BBM' ]
    #remove the unnecessary words
    x1 =[]
    #remove all underscore
    for s in permission_list:
        stmp = s.split('-')
    
        if len(stmp)>=3:
            if stmp[2] == 'TrunkSide':
                x1.append("".join(stmp[2]).lower())
            else:
                x1.append("".join(stmp[2:]).lower())
        else:
            x1.append(s.lower())
    return x1

def to_get_match(df_tmp, permis_list):
    """
    Filter a DataFrame based on a permission list.

    Applies filtering to retain rows where all tags in the 'accessPolicyTag' column match the permission list.

    Args:
        df_tmp (pd.DataFrame): The DataFrame to filter.
        permis_list (list): List of permissions to match.

    Returns:
        pd.DataFrame: A filtered DataFrame containing only matching rows.
    """
    df_tmp.reset_index(inplace=True, drop=True)
    df_tmp["flag"] = [
        1 if isinstance(tags, list) and all(tag in permis_list for tag in tags) else 0 
        for tags in df_tmp["accessPolicyTag"]
    ]
    df_tmp = df_tmp[df_tmp["flag"] == 1]
    del df_tmp["flag"]
    df_tmp.reset_index(inplace=True, drop=True)
    return df_tmp

def followup_priority_filter(df, agent_id, now) -> pd.DataFrame:
    """
    Check if there are any followups for this agent and filter accordingly.
    Prioritize based on whether there has been a customer update or internal note added.

    Args:
        df (pd.DataFrame): The DataFrame containing request data.
        agent_id (str): The agent ID to filter follow-up requests for.

    Returns:
        pd.DataFrame: A filtered DataFrame containing follow-up requests for the specified agent.
    """
    # First, consider all rows that have a followUpDate set and are assigned to this agent
    df_followups_all_assigned = df[
        (~df['workOrder_followUpDate'].isna()) &
        (df['workOrder_assignee_id'] == agent_id)
    ].copy()

    if df_followups_all_assigned.empty:
        return pd.DataFrame()

    # Create boolean mask for customer updates or internal notes on all those self-assigned followups
    def _has_internal_note_or_customer_update(tags, status):
        has_note = isinstance(tags, list) and ('NEW_INTERNAL_NOTE' in tags)
        is_customer_replied = (status == 'customerreplied')
        return has_note or is_customer_replied

    cust_update_or_internal_note_mask = df_followups_all_assigned.apply(
        lambda row: _has_internal_note_or_customer_update(row.get('workOrder_tags'), row.get('workOrder_status')),
        axis=1
    )

    # Bucket A: All self-assigned followups that have a customer update or internal note (regardless of followUpDate <= now)
    df_followups_cust_update_or_internal_note = df_followups_all_assigned[cust_update_or_internal_note_mask]

    # Bucket B: Self-assigned followups that do NOT have customer update/internal note AND whose followUpDate is due (<= now)
    df_followups_no_cust_update_nor_internal_note = df_followups_all_assigned[
        (~cust_update_or_internal_note_mask) &
        (df_followups_all_assigned['workOrder_followUpDate'] <= now)
    ]

    # Further subdivide each bucket based on workOrder_expectedCompletionDate
    # Bucket 1: Customer update/internal note + has expected completion date
    df_cust_update_with_expected_completion_date = df_followups_cust_update_or_internal_note[
        (~df_followups_cust_update_or_internal_note['workOrder_expectedCompletionDate'].isna())
    ]

    # Bucket 2: Customer update/internal note + no expected completion date
    df_cust_update_without_expected_completion_date = df_followups_cust_update_or_internal_note[
        (df_followups_cust_update_or_internal_note['workOrder_expectedCompletionDate'].isna())
    ]

    # Bucket 3: No customer update/internal note + has expected completion date
    df_no_cust_update_with_expected_completion_date = df_followups_no_cust_update_nor_internal_note[
        (~df_followups_no_cust_update_nor_internal_note['workOrder_expectedCompletionDate'].isna())
    ]

    # Bucket 4: No customer update/internal note + no expected completion date
    df_no_cust_update_without_expected_completion_date = df_followups_no_cust_update_nor_internal_note[
        (df_followups_no_cust_update_nor_internal_note['workOrder_expectedCompletionDate'].isna())
    ]

    # Priority order: Bucket 1 -> Bucket 2 -> Bucket 3 -> Bucket 4
    priority_buckets = {
        "Customer Update/Internal Note + Expected Completion Date": df_cust_update_with_expected_completion_date,
        "Customer Update/Internal Note + No Expected Completion Date": df_cust_update_without_expected_completion_date,
        "No Customer Update/Internal Note + Expected Completion Date": df_no_cust_update_with_expected_completion_date,
        "No Customer Update/Internal Note + No Expected Completion Date": df_no_cust_update_without_expected_completion_date
    }

    for bucket_num, (bucket_name, bucket_df) in enumerate(priority_buckets.items(), 1):
        if bucket_df.empty:
            continue
        else:
            logger.info(f"BUCKET {bucket_num} ({bucket_name}) - FOLLOW-UP REQUESTS FOUND: {bucket_df.shape[0]} requests")
            return bucket_df

    return pd.DataFrame()

def filter_static(df, tenant, permissions, all_absent_agent_ids, agent_id) -> pd.DataFrame:
    """
    Apply static filters to a DataFrame of requests.

    Filters requests based on business unit, access policy, absence status, and permissions.

    Args:
        df (pd.DataFrame): The DataFrame containing request data.
        tenant (str): The tenant identifier for filtering.
        permissions (list): List of permissions for filtering.
        all_absent_agent_ids (list): List of IDs for absent agents.

    Returns:
        pd.DataFrame: A filtered DataFrame.
    """
    # 1.
    if tenant.lower() == 'wireless':
        df_tmp_1 = df.loc[df['source_businessUnit'] == 'wireless']
    elif len(tenant) > 0 and tenant.isalnum() and tenant.lower() != 'wireless':
        df_tmp_1 = df.loc[df['source_businessUnit'] != 'wireless']
    else:
        df_tmp_1 = df.copy()
    # logger.info(f"Time taken for 1st static filter(): {time.time() - start_time} seconds")
    # logger.debug("BusinessUnit in ('Wireless'): %s", str(df_tmp_1.shape))

    # 2.
    now = datetime.now(timezone.utc)
    current_time = now.time()
    is_followup_time = (
        (current_time >= datetime.strptime("14:00", "%H:%M").time() and 
         current_time <= datetime.strptime("15:30", "%H:%M").time()) or
        (current_time >= datetime.strptime("19:30", "%H:%M").time() and 
         current_time <= datetime.strptime("20:00", "%H:%M").time())
    )

    # Initialize df_filtered
    df_filtered = pd.DataFrame()

    # Check if current time is within the designated hours (1:30-2:00 PM UTC or 9:30-10:00 AM EST OR 6:30-7:00 PM UTC OR 2:30-3:00 PM EST) for follow-up requests AND the agent is in the PILOT list
    pilot_agent_list = ['eq42183',
                        'bccs.n410362',
                        'bccs.n335248',
                        'anna.borjal',
                        'bccs.n414439',
                        'bccs.n295601',
                        'danielle.stockley1',
                        'danny.bonora',
                        'dianne.gillespiedixo',
                        'donna.hicken',
                        'bccs.n250686',
                        'edward.orrego1',
                        'emily_t.mariconda',
                        'bccs.a220038',
                        'bccs.n226231',
                        'bccs.p000625',
                        'jane_r.richards',
                        'bccs.n358696',
                        'ba00440',
                        'bccs.n435942',
                        'bccs.n375560',
                        'bccs.a364515',
                        'bccs.a489686',
                        'louissamuel.papine',
                        'marie_vesta.fontai',
                        'bccs.n337807',
                        'bccs.3011204',
                        'melanie.barrette1',
                        'bccs.n429959',
                        'bccs.n425141',
                        'bccs.n334061',
                        'bccs.n288584',
                        'bccs.n332722',
                        'bccs.a534119',
                        'bccs.a591501',
                        'bccs.a368209',
                        'bccs.n381946',
                        'rommel.bellosillo',
                        'bccs.n378987',
                        'samia.rkhami1',
                        'bccs.a369798',
                        'bccs.p001889',
                        'bccs.a304901',
                        'bccs.n382053',
                        'stella.purcell',
                        'wendi.osborne',
                        'bccs.n314662',
                    ]

    if is_followup_time and (agent_id in pilot_agent_list):
        # 2.A. Follow-up Requests (self-assigned with follow-up date passed) - Primary during follow-up time
        df_filtered = followup_priority_filter(df_tmp_1, agent_id, now)
        if not df_filtered.empty:
            df_filtered['from_absent_agent'] = False
            df_filtered['is_followup'] = True
            logger.info(f"Follow-up requests found during follow-up time: {df_filtered.shape[0]} requests")

        # If no follow-up requests found during follow-up time, fall back to CMO requests
        if df_filtered.empty:
            # 2.B. CMO (new and absent agent requests) - Fallback during follow-up time
            logger.info("No follow-up requests found during follow-up time, falling back to CMO requests")

            # Assignee is null
            df_unassigned = df_tmp_1[df_tmp_1['workOrder_assignee_id']=='nan'].copy()
            df_unassigned['from_absent_agent'] = False

            # Status is new 
            df_unassigned_new = df_unassigned[df_unassigned['workOrder_status'] == 'new']

            # Status is customer replied
            df_unassigned_customer_replied = df_unassigned[df_unassigned['workOrder_status'] == 'customerreplied']
            
            # logger.debug("no assignee filter: {} {}".format(d1.shape, d1['request_id']))

            # Assignee in absents
            df_assigned_absent = df_tmp_1[(df_tmp_1['workOrder_assignee_id']!='nan') & (df_tmp_1['workOrder_assignee_id'].isin(all_absent_agent_ids))].copy()
            df_assigned_absent['from_absent_agent'] = True

            # Remove requests that are locked and have any status other than 'orderConfirmed'
            df_assigned_absent = df_assigned_absent[~((df_assigned_absent['workOrder_status'] != 'orderconfirmed') & (df_assigned_absent['workOrder_tags'].apply(lambda x: 'LOCKED' in x)))]
    
            # Agent is absent & status is customer replied
            df_assigned_customer_replied = df_assigned_absent[df_assigned_absent['workOrder_status'] == 'customerreplied']
    
            # Agent is absent & status is not customer replied
            df_assigned_not_customer_replied = df_assigned_absent[df_assigned_absent['workOrder_status'] != 'customerreplied']

            # Agent is absent & status is not customer replied & there is a new internal note added
            df_assigned_not_customer_replied_new_note = df_assigned_not_customer_replied[df_assigned_not_customer_replied['workOrder_tags'].apply(lambda x: 'NEW_INTERNAL_NOTE' in x)]

            # Agent is absent & status is not customer replied & there is NO new internal note added
            df_assigned_not_customer_replied_no_new_note = df_assigned_not_customer_replied[~df_assigned_not_customer_replied['workOrder_tags'].apply(lambda x: 'NEW_INTERNAL_NOTE' in x)]
    
            # logger.debug("assignee in all_list filter:  %s", str(d2.shape))

            # Filtering for the follow-up date on selected cases
            # df_follow_up_date = pd.concat([df_unassigned_new, df_assigned_not_customer_replied_no_new_note], ignore_index=True)
            df_follow_up_date = df_unassigned_new.copy() # Pilot with only unassigned new requests
            df_follow_up_date = df_follow_up_date[(df_follow_up_date['workOrder_followUpDate'].isna()) | (df_follow_up_date['workOrder_followUpDate'] <= now)]
    
            # Merging back all cases together:
            # 1. all cases that have customer replied status
            # 2. all cases (absent agent requests) that have new internal note
            # 3. all cases whose follow-up date has passed
            df_filtered = pd.concat([
                df_unassigned_customer_replied, 
                df_assigned_customer_replied, df_assigned_not_customer_replied_new_note, 
                df_follow_up_date])
            
            if not df_filtered.empty:
                df_filtered['is_followup'] = False
                logger.info(f"CMO requests found during follow-up time: {df_filtered.shape[0]} requests")

    else:
        # 2.C. CMO (new and absent agent requests) - Primary during non-follow-up time

        # Assignee is null
        df_unassigned = df_tmp_1[df_tmp_1['workOrder_assignee_id']=='nan'].copy()
        df_unassigned['from_absent_agent'] = False

        # Status is new 
        df_unassigned_new = df_unassigned[df_unassigned['workOrder_status'] == 'new']

        # Status is customer replied
        df_unassigned_customer_replied = df_unassigned[df_unassigned['workOrder_status'] == 'customerreplied']

        # Assignee in absents
        df_assigned_absent = df_tmp_1[(df_tmp_1['workOrder_assignee_id']!='nan') & (df_tmp_1['workOrder_assignee_id'].isin(all_absent_agent_ids))].copy()
        df_assigned_absent['from_absent_agent'] = True
        # logger.debug("IS assignee filter: {0} {1} {2}".format(d2.shape, d2['request_id'], d2['workOrder_assignee']))

        # Remove requests that are locked and have any status other than 'orderConfirmed'
        df_assigned_absent = df_assigned_absent[~((df_assigned_absent['workOrder_status'] != 'orderconfirmed') & (df_assigned_absent['workOrder_tags'].apply(lambda x: 'LOCKED' in x)))]

        # Agent is absent & status is customer replied
        df_assigned_customer_replied = df_assigned_absent[df_assigned_absent['workOrder_status'] == 'customerreplied']

        # Agent is absent & status is not customer replied
        df_assigned_not_customer_replied = df_assigned_absent[df_assigned_absent['workOrder_status'] != 'customerreplied']

        # Agent is absent & status is not customer replied & there is a new internal note added
        df_assigned_not_customer_replied_new_note = df_assigned_not_customer_replied[df_assigned_not_customer_replied['workOrder_tags'].apply(lambda x: 'NEW_INTERNAL_NOTE' in x)]

        # Agent is absent & status is not customer replied & there is NO new internal note added
        df_assigned_not_customer_replied_no_new_note = df_assigned_not_customer_replied[~df_assigned_not_customer_replied['workOrder_tags'].apply(lambda x: 'NEW_INTERNAL_NOTE' in x)]

        # logger.debug("assignee in all_list filter:  %s", str(d2.shape))

        # Filtering for the follow-up date on selected cases
        # df_follow_up_date = pd.concat([df_unassigned_new, df_assigned_not_customer_replied_no_new_note], ignore_index=True)
        df_follow_up_date = df_unassigned_new.copy() # Pilot with only unassigned new requests
        df_follow_up_date = df_follow_up_date[(df_follow_up_date['workOrder_followUpDate'].isna()) | (df_follow_up_date['workOrder_followUpDate'] <= now)]

        # Merging back all cases together:
        # 1. all cases that have customer replied status
        # 2. all cases (absent agent requests) that have new internal note
        # 3. all cases whose follow-up date has passed
        df_filtered = pd.concat([
            df_unassigned_customer_replied, 
            df_assigned_customer_replied, df_assigned_not_customer_replied_new_note, 
            df_follow_up_date])
        
        if not df_filtered.empty:
            df_filtered['is_followup'] = False
            logger.info(f"CMO requests found during non-follow-up time: {df_filtered.shape[0]} requests")

        # If no CMO requests found during non-follow-up time, fall back to follow-up requests
        if df_filtered.empty and (agent_id in pilot_agent_list):
            # 2.D. Follow-up Requests - Fallback during non-follow-up time
            logger.info("No CMO requests found during non-follow-up time, falling back to follow-up requests")
            df_filtered = followup_priority_filter(df_tmp_1, agent_id, now)
            if not df_filtered.empty:
                df_filtered['from_absent_agent'] = False
                df_filtered['is_followup'] = True
                logger.info(f"Follow-up requests found during non-follow-up time: {df_filtered.shape[0]} requests")

    # 3.
    permis_list = pre_process(permissions)
    logger.info(f"PERMISSION LIST ----> {str(permis_list)}")
    df_final = to_get_match(df_filtered, permis_list)
    
    return df_final

def find_requests_for_skill(df: pd.DataFrame, skill_configuration: dict) -> pd.DataFrame:
    """
    Filter requests in a DataFrame based on skill configuration.

    Applies filtering logic to match requests with the attributes defined in the skill configuration.

    Args:
        df (pd.DataFrame): The DataFrame containing request data.
        skill_configuration (dict): A dictionary containing skill attributes and their values.

    Returns:
        pd.DataFrame: A DataFrame containing requests that match the skill configuration.
    """
    # Preprocess the skill_configuration to remove empty attributes
    skill_configuration = {k: v for k, v in skill_configuration.items() if v != ['']}
    attribute_list = [k for k in skill_configuration.keys() if k not in ('skill_id', 'skill_name', 'skill_priority', 'tag')]

    df_original = df
    filter_info_list = {}
    for skill_attr in attribute_list:
        if skill_configuration[skill_attr]:
            request_attr = skillAttribute_to_requestAttribute_mapping[skill_attr]
            df = df[df[request_attr].isin(skill_configuration[skill_attr])]
            filter_info_list[skill_attr] = len(df)
    logger.info(f"filtering from {len(df_original)} requests {filter_info_list}")

    return df
