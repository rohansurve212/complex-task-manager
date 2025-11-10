import sys
sys.path.append('..')
import asyncio
import pyodbc
from itertools import product
import sqlite3
from typing import Dict, List
import logging

from shared.db import DB
from app.GetWorkFlow.search_requests_utils import *
from app.Elastic.elastic_settings import query_fields, make_elastic_query, INDEX_NAME
from shared.all_envs import *

logger = logging.getLogger("API log")

async def agent_permissions_async(mssql_conn: object, agent_id: str) -> List:
    """
    Retrieve agent permissions asynchronously.

    This function wraps the synchronous agent_permissions_sync function to run in a 
    non-blocking manner using an asyncio event loop.

    Args:
        mssql_conn (object): Database connection object for MSSQL.
        agent_id (str): The agent's ID.

    Returns:
        List: A list of all permissions assigned to the agent.
    """
    loop = asyncio.get_running_loop()
    # Use run_in_executor to run the synchronous DB operation in a thread pool
    permissions = await loop.run_in_executor(None, agent_permissions_sync, mssql_conn, agent_id)
    return permissions

def agent_permissions_sync(mssql_conn: object, agent_id: str) -> List[Dict]:
    """
    Retrieve agent permissions synchronously from the database.

    Queries the permission_agent table to fetch all permissions associated with a specific agent.

    Args:
        mssql_conn (object): Database connection object for MSSQL.
        agent_id (str): The agent's ID.

    Returns:
        List[Dict]: A list of permissions assigned to the agent.
    """
    permissions = []
    with mssql_conn() as conn:
        cur = conn.cursor()
        sql_permissions = f"SELECT permission FROM {DB.permission_agent()} WHERE agent_id = '{agent_id}';"
        # Execute the query and fetch all results
        permissions = [permission[0] for permission in cur.execute(sql_permissions).fetchall()]
    return permissions

async def agent_skillsets_async(mssql_conn: object, agent_id: str) -> List[Dict]:
    """
    Retrieve agent skillsets asynchronously.

    This function wraps the synchronous agent_skillsets_sync function to run in a 
    non-blocking manner using an asyncio event loop.

    Args:
        mssql_conn (object): Database connection object for MSSQL.
        agent_id (str): The agent's ID.

    Returns:
        List[Dict]: A list of skillsets assigned to the agent.
    """
    loop = asyncio.get_running_loop()
    # Use run_in_executor to run the synchronous DB operation in a thread pool
    skillsets = await loop.run_in_executor(None, agent_skillsets_sync, mssql_conn, agent_id)
    return skillsets

def agent_skillsets_sync(mssql_conn: object, agent_id: str) -> List[Dict]:
    """
    Retrieve agent skillsets synchronously from the database.

    Queries the database to fetch all active skillsets associated with a specific agent, 
    including skill ID, name, and priority.

    Args:
        mssql_conn (object): Database connection object for MSSQL.
        agent_id (str): The agent's ID.

    Returns:
        List[Dict]: A list of dictionaries containing skill IDs, names, and priorities.
    """
    skillsets = []
    with mssql_conn() as conn:
        cur = conn.cursor()
        sql_skillsets = (
            f'''
            SELECT  
                T1.skill_id,
                T2.skill_name,
                T1.skill_priority  
            FROM {DB.skill_agent_priority()} AS T1 
                INNER JOIN {DB.skill_config()} AS T2 
                ON T1.skill_id = T2.skill_id 
            WHERE agent_id = '{agent_id}' 
                AND T1.skill_id IS NOT NULL  
                AND skill_distribution = 'FILTER'
                and skill_status = 'ACTIVE'
            '''
        )
        # Execute the query and fetch all results
        skillsets = [
            {'skill_id': row[0], 'skill_name': row[1], 'skill_priority': row[2]}
            for row in cur.execute(sql_skillsets).fetchall()
        ]
    return skillsets

async def agent_skills_config_async(mssql_conn: object, skillsets: List) -> List[Dict]:
    """
    Retrieve skill configurations asynchronously for a list of skillsets.

    This function wraps the synchronous agent_skills_config_sync function to run in a 
    non-blocking manner using an asyncio event loop.

    Args:
        mssql_conn (object): Database connection object for MSSQL.
        skillsets (List): A list of skillsets.

    Returns:
        List[Dict]: A list of dictionaries containing skill configurations.
    """
    loop = asyncio.get_running_loop()
    skill_configs = await loop.run_in_executor(None, agent_skills_config_sync, mssql_conn, skillsets)
    return skill_configs

def agent_skills_config_sync(mssql_conn: object, skillsets: List) -> Dict:
    """
    Retrieve skill configurations synchronously for a list of skillsets.

    Queries the database to fetch skill configurations, merging them with the provided 
    skillsets and transforming the data for further processing.

    Args:
        mssql_conn (object): Database connection object for MSSQL.
        skillsets (List): A list of skillsets.

    Returns:
        List[Dict]: A list of dictionaries containing skill configurations.
    """
    skill_ids = [skillset['skill_id'] for skillset in skillsets]
    placeholders = ', '.join(['?' for _ in skill_ids])
    with mssql_conn() as conn:
        sql_skills_config = f"SELECT * FROM {DB.skill_attributes()} WHERE skill_id IN ({placeholders});"
        result_df = pd.read_sql_query(sql_skills_config, conn, params=skill_ids)

    skillsets_df = pd.DataFrame(skillsets).drop(columns=['skill_name'])
    result_df = result_df.merge(skillsets_df, on='skill_id', how='left')
    
    result_df.fillna('', inplace=True)
    skill_columns = ['skill_id', 'skill_name','skill_priority']
    csv_columns = ['goldenCustomer', 'controlDesk', 'customerMarketSegment', 'preferredlanguage', 'requestSource', 
                   'product', 'serviceRegion', 'customerSupportModel', 'requestType', 'tag']
    
    for column in result_df.columns:
        if column in csv_columns:
            result_df[column] = result_df[column].apply(lambda x: [item.lower() for item in x.split(';')])
        elif column in skill_columns:
            result_df[column] = result_df[column].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else x)

    return result_df.to_dict(orient='records')

async def get_p1_escalation_async(mssql_conn: object, escalation_table: str) -> List:
    """
    Retrieve priority 1 escalation request IDs asynchronously.

    This function wraps the synchronous get_p1_escalation_sync function to run in a 
    non-blocking manner using an asyncio event loop.

    Args:
        mssql_conn (object): Database connection object for MSSQL.
        escalation_table (str): Name of the escalation table.

    Returns:
        List: A list of request IDs in uppercase that have priority 1 and are open.
    """
    loop = asyncio.get_running_loop()
    request_ids = await loop.run_in_executor(None, get_p1_escalation_sync, mssql_conn, escalation_table)
    return request_ids

def get_p1_escalation_sync(mssql_conn: object, escalation_table) -> List:
    """
    Retrieve priority 1 escalation request IDs synchronously.

    Queries the escalation table to fetch all request IDs with priority 1 and status 'open'.

    Args:
        mssql_conn (object): Database connection object for MSSQL.
        escalation_table (str): Name of the escalation table.

    Returns:
        List: A list of request IDs in uppercase.
    """
    with mssql_conn() as conn:
        sql_escalated_requests = f"SELECT * FROM {escalation_table} where status='open' and priority=1"
        result_df = pd.read_sql(sql_escalated_requests, conn)
        
    return result_df['request_id'].str.upper().tolist()

async def updated_elastic_to_df(last_request_date, filter_comp= False, query_fields=None) -> pd.DataFrame:
    """
    Fetch updated requests from Smartpath ElasticSearch database and convert them to a DataFrame.

    This function retrieves all request IDs that were last updated after a specified timestamp 
    and preprocesses them into a DataFrame.

    Args:
        last_request_date (str): Timestamp of the last request date in ISO format.
        filter_comp (bool): Flag to enable or disable component filtering (default is False).
        query_fields (list): List of fields to include in the query.

    Returns:
        pd.DataFrame: A DataFrame containing the processed requests.
    """
    # Reduced limit from 10000 to 8000 to prevent timeouts and improve performance
    elastic_resp_new = await get_requests_from_smartpath_elastic(
        last_request_date, limit=8000, filter_comp=filter_comp)
    df = elastic_response_to_df(elastic_resp_new, query_fields=query_fields)
    return df

def skills_filtering(df, configurations, permissions, tenant, all_absent_agent_ids, agent_id) -> pd.DataFrame:
    """
    Filter requests based on agent skills and static rules.

    This function applies static and skill-based filters to a DataFrame of requests, 
    assigning skill attributes to eligible requests.

    Args:
        df (pd.DataFrame): DataFrame containing all requests.
        configurations (List): List of skill configurations.
        permissions (List): List of agent permissions.
        tenant (str): Tenant identifier.
        all_absent_agent_ids (List): List of absent agent IDs.

    Returns:
        pd.DataFrame: A filtered DataFrame containing eligible requests with skill attributes.
    """
    start_time = time.time()
    df_common_filter = filter_static(df, tenant, permissions, all_absent_agent_ids, agent_id)
    logger.info(f'Time taken for static filtering: {time.time() - start_time}')

    if df_common_filter.empty:
        return pd.DataFrame()

    dfs_to_concat = []  # Store DataFrames to concat later
    
    start_time = time.time()
    for configuration in configurations:
        logger.info(f'Started skills_filtering with routing Filters name {configuration["skill_name"]} and ID {configuration["skill_id"]} and priority {configuration["skill_priority"]}')
        
        df_reqs = find_requests_for_skill(df_common_filter, configuration)
        if not df_reqs.empty:
            # Add skill_id and skill_name and skill_priority without copying the df
            df_reqs = df_reqs.assign(skillId=configuration['skill_id'], skillName=configuration['skill_name'], skillPriority=configuration['skill_priority'])
            dfs_to_concat.append(df_reqs)
    logger.info(f'Time taken for looping over all RFs: {time.time() - start_time}')

    if not dfs_to_concat:
        return pd.DataFrame()

    # Concatenate all at once
    filtered_reqs = pd.concat(dfs_to_concat, ignore_index=True)
    
    # Efficiently rename columns and drop duplicates
    rename_map = {
        'request_id': 'requestId',
        'source_externalId': 'externalId',
        'source_orderDate': 'requestOrderDate',
        'source_requestedStartDate': 'requestStartDate',
        'source_requestSource': 'requestSource',
        'source_customerSupportModel': 'customerSupportModel',
        'source_requestType': 'requestType',
        'source_focTarget': 'focTarget',
        'from_absent_agent': 'fromAbsentAgent',
        'source_referredType': 'referredType',
        'workOrder_product': 'product',
        'workOrder_controlDesk': 'controlDesk',
        'workOrder_followUpDate':'followUpDate',
        'source_serviceRegion': 'serviceRegion',
        'source_goldenCustomer_name': 'goldenCustomerName',
        'source_customerMarketSegment': 'customerMarketSegment',
        'source_preferredLanguage': 'preferredLanguage',
        'workOrder_status': 'requestStatus',
        'workOrder_assignee_id': 'requestAssignee',
        'workOrder_expectedCompletionDate': 'expectedCompletionDate'
    }
    # Select required columns and drop duplicates based on 'requestId'
    filtered_reqs = (filtered_reqs.rename(columns=rename_map)
                     .drop_duplicates('requestId')
                     [[
                        'requestId', 'externalId', 'requestOrderDate', 'requestStartDate', 'requestSource', 'customerSupportModel', 'requestType', 'focTarget', 
                        'fromAbsentAgent', 'referredType', 'skillId', 'skillName','product', 'controlDesk', 'followUpDate', 'serviceRegion', 'goldenCustomerName', 
                        'customerMarketSegment', 'preferredLanguage', 'requestStatus', 'requestAssignee',
                        'has_sla','is_escalated', 'is_winback', 'is_exclusive_atlantic_routingFilter', 'skillPriority',
                        'expectedCompletionDate', 'is_followup'
                    ]])

    return filtered_reqs