import sys
sys.path.append('..')
import logging
import pandas as pd
import datetime
from typing import Dict
from shared.db import DB
from shared.all_envs import DEFAULT_TTPU

logger = logging.getLogger("API log")

MINUTES_IN_A_DAY = 1440.0

def time_difference(timestamp: datetime.datetime) -> float:
    """
    Compute the time difference between the current UTC time and a given timestamp.
    Calculates the difference in minutes between a provided timestamp and the current time.

    Args:
        timestamp (datetime.datetime): The timestamp to compare with the current UTC time.

    Returns:
        float: The time difference in minutes.
    """
    return (datetime.datetime.now(timestamp.tzinfo) - timestamp).total_seconds()/60.0

def find_flow_id(con: object, request_dict: Dict) -> int:
    """
    Determine the flow ID scenario for a request based on its characteristics.

    Queries the dim_flow database table to find the corresponding flow ID for a given request's attributes.

    Args:
        con (object): SQL database connection.
        request_dict (Dict): A dictionary containing request characteristics, including:
            - skill_id (str)
            - requestStartDate (datetime)
            - requestSource (str)
            - customerSupportModel (str)
            - requestType (str)
            - focTarget (int)

    Returns:
        int: The flow ID for the request. Returns 0 if no match is found.
    """
    cur = con.cursor()
    #Find request characteristics
    if request_dict['requestSource'] == 'bcom': 
        source = 'bcom' 
    else: source = 'other'

    if 'customerSupportModel' in request_dict.keys():
        if request_dict['customerSupportModel'] == 'non-standard':
            support_model = 'non-standard'
        else:
            support_model = 'other'
    else:
        support_model = 'other'

    if 'inquiry' in request_dict['requestType']:
        request_type = 'inquiry'
    elif request_dict['requestType'] == 'disconnect':
        request_type = 'disconnect'
    elif request_dict['requestType'] in ['new','move','Move','add','Add','change','Change']:
        request_type = 'nmac'
    else: 
        request_type = 'other'

    foc_target = request_dict['focTarget']

    #Find flow_id in dim_flow table
    sql = (
        f"SELECT flow_id FROM {DB.dim_flow()} "
        f"WHERE request_source = '{source}' "
        f"AND customer_support_model = '{support_model}' "
        f"AND request_type='{request_type}' "
        f"AND foc_target= {str(foc_target)}"
        )

    response = cur.execute(sql).fetchall()
    if len(response) == 0:
        flow_id = 0
    else: 
        flow_id = int(cur.execute(sql).fetchall()[0][0])

    return flow_id

def priority_score_new(row: Dict) -> float:
    """
    Calculate the priority score for a request.

    The score is based on the request's age and its time-to-pickup (FOC target). 
    Older requests and those with shorter FOC targets are given higher scores.

    Args:
        row (Dict): A dictionary containing request attributes, including:
            - requestOrderDate (datetime)
            - focTarget (int)
            - skillPriority (int) [optional]

    Returns:
        float: The calculated priority score for the request.
    """
    #Initialise the score at the age of a request
    score = time_difference(row['requestOrderDate'])

    if row['focTarget'] > 0:
        score = score / row['focTarget']
    else:
        score = score / DEFAULT_TTPU

    return score

def priority_score_followup(row: Dict) -> float:
    """
    Calculate the priority score for a followup request.

    The score is based on time difference from expected completion date if available,
    otherwise from request order date. Higher time difference means higher priority.

    Args:
        row (Dict): A dictionary containing request attributes, including:
            - requestOrderDate (datetime)
            - expectedCompletionDate (datetime) [optional]

    Returns:
        float: The calculated priority score for the request.
    """
    # Check if expectedCompletionDate field exists and is valid, otherwise use requestOrderDate
    if ('expectedCompletionDate' in row and 
        row['expectedCompletionDate'] is not None and 
        not pd.isna(row['expectedCompletionDate'])):
        try:
            score = time_difference(row['expectedCompletionDate'])/MINUTES_IN_A_DAY
        except (TypeError, ValueError):
            # Fallback to requestOrderDate if expectedCompletionDate is invalid
            score = time_difference(row['requestOrderDate'])/MINUTES_IN_A_DAY
    else:
        score = time_difference(row['requestOrderDate'])/MINUTES_IN_A_DAY

    # Ensure we return a valid number, fallback to 0 if still NaN
    return score if not pd.isna(score) else 0.0

def top_priority_request(filtered_reqs: pd.DataFrame) -> dict:
    """
    Identify the request with the highest priority score.

    Applies the priority_score function to each request in the DataFrame and selects the 
    request with the highest score. For followup requests, if there are ties, select
    the one with the earliest requestOrderDate.

    Args:
        filtered_reqs (pd.DataFrame): A DataFrame of filtered requests.

    Returns:
        dict: The row corresponding to the request with the highest priority score.
    """
    # Compute the priority score for each eligible request and depending on characteristics
    if filtered_reqs['is_followup'].any():
        filtered_reqs['score'] = filtered_reqs.apply(priority_score_followup, axis=1)
        
        # Find the maximum score, handle NaN case
        max_score = filtered_reqs['score'].max()
        
        # If all scores are NaN, return first available request
        if pd.isna(max_score):
            return filtered_reqs.iloc[0]
        
        # Get all requests with the maximum score
        max_score_reqs = filtered_reqs[filtered_reqs['score'] == max_score]
        
        # Safety check for empty result
        if max_score_reqs.empty:
            return filtered_reqs.iloc[0]
        
        # If there are ties, pick the one with earliest requestOrderDate
        if len(max_score_reqs) > 1:
            earliest_idx = max_score_reqs['requestOrderDate'].idxmin()
            return filtered_reqs.loc[earliest_idx]
        else:
            return max_score_reqs.iloc[0]
    else:
        # For regular requests, return the request with the highest score
        filtered_reqs['score'] = filtered_reqs.apply(priority_score_new, axis=1)
        return filtered_reqs.loc[filtered_reqs['score'].idxmax()]

def routing(filtered_reqs: pd.DataFrame):
    """
    Perform the routing algorithm to select the best request for assignment.

    Processes a DataFrame of filtered requests to calculate priority scores and select 
    the top-priority request for routing.

    Args:
        filtered_reqs (pd.DataFrame): A DataFrame containing eligible requests after filtering.

    Returns:
        dict: The top-priority request as a dictionary containing:
            - requestId (str): The ID of the selected request.
            - skill_id (str): The skill ID associated with the request.
            - from_absent_agent (bool): Whether the request is from an absent agent.
        None: If no eligible requests are found.
    """
    if filtered_reqs.empty:
        return None
    
    return top_priority_request(filtered_reqs)