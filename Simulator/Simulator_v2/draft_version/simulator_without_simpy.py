from datetime import datetime, timezone
import time
import pandas as pd
import pyodbc
import numpy as np
import teradatasql
import sys
sys.path.append('../..')
from shared.all_envs import TD_HOST, TD_USER, TD_PASS, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS
pd.options.mode.chained_assignment = None  # default='warn'

PRIORIZATION_ALGORITHM = 'foc'  # Options: 'fifo', 'foc'
SIMULATOR_DEFAULT_TTPU = 8  # Default Time to Process Unit
# Statistical Metrics
metrics = {
    'total_foc_met': 0,
    'total_requests_processed': 0,
    'total_time_to_assign': 0,
    'total_processing_time': 0
}
count_all = 0
count_empty = 0
count_x = 0

def localize_and_convert(column, initial_tz='UTC', target_tz='UTC'):
    """Localize and convert a datetime column to the target timezone"""
    return pd.to_datetime(column).dt.tz_localize(initial_tz).dt.tz_convert(target_tz).dt.floor('s')


def build_request_dataframe():
    """
        This function builds the request dataframe
    """
    query_td = f"""
                    SELECT	smtpth_req_id, smtpth_req_start_dt, smtpth_req_comp_dt
                    FROM GRP_JARVIS_ANALYSIS.fact_smtpth_request_v2 
                    WHERE CAST(smtpth_req_start_dt AS DATE) >= DATE '2024-01-01' 
                    and CAST(smtpth_req_start_dt AS DATE) < DATE '2024-04-01' and 
                    smtpth_req_start_dt is not null and smtpth_req_comp_dt is not null
                """

    qry_getwork = f"""
                      SELECT *
                      FROM [bbm_stm].[dbo].[getwork_results] 
                      WHERE assign_date >= '2024-01-01' and assign_date < '2024-04-01'
                   """

    qry_escalation = f"""
                          SELECT *
                          FROM [bbm_stm].[dbo].[escalation]
                      """
    
    # Connection to Teradata and MS SQL Server
    with teradatasql.connect(host=TD_HOST,user=TD_USER, password=TD_PASS) as conn_td:
        requests = pd.read_sql(query_td, conn_td)

    conn_mssql = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
    
    getwork = pd.read_sql_query(qry_getwork, conn_mssql)
    escalation = pd.read_sql_query(qry_escalation, conn_mssql)

    # Dropping nulls and merging the dataframes to get completion date
    getwork = getwork.loc[~getwork['external_id'].isna()]

    # Adding is_escalated column
    getwork['is_escalated'] = np.where(getwork['external_id'].isin(escalation['request_id']), 1, 0)

    getwork_with_comp_date = getwork.merge(
        requests,
        left_on=['request_id'],
        right_on=['smtpth_req_id'],
        how='left'
    )
    getwork_with_comp_date = getwork_with_comp_date.loc[~getwork_with_comp_date['smtpth_req_comp_dt'].isna()]

    # Making sure both time columns are in the same time zone (UTC)
    getwork_with_comp_date['assign_date'] = localize_and_convert(getwork_with_comp_date['assign_date'])
    getwork_with_comp_date['orderdate'] = localize_and_convert(getwork_with_comp_date['orderdate'])
    getwork_with_comp_date['smtpth_req_comp_dt'] = localize_and_convert(getwork_with_comp_date['smtpth_req_comp_dt'], 'America/New_York', 'UTC')

    # Calculating actual completion time in seconds
    getwork_with_comp_date['actual_completion_time'] = (getwork_with_comp_date['smtpth_req_comp_dt'] - getwork_with_comp_date['assign_date']).dt.total_seconds()
    
    request_df = getwork_with_comp_date[['request_id', 'agent_id', 'orderdate','ttpu','assign_date', 'skill_id', 'request_source', 
                                          'product', 'service_region', 'request_type', 'customer_support_model',
                                          'control_desk', 'golden_customer', 'customer_market_segment',
                                          'preferred_language', 'external_id', 'is_escalated', 'smtpth_req_comp_dt',
                                          'actual_completion_time']].drop_duplicates()

    request_df['list_rfs'] = request_df['skill_id'].apply(lambda x : [x])

    return request_df


def process_request(request_df, request):
    """
        Process the request for the time duration equal to actual handle time
        and update the performance metrics
    """
    global metrics
    global count_all
    count_all += 1

    if request.empty:
        print(f"Request ID ---> {request['request_id']}")
        global count_empty
        count_empty += 1
        return # If request is empty, exit the function
    
    global count_x
    count_x += 1
    
    request_time_to_assign = (request['assign_date'] - request['orderdate']).days
    request_time_to_process = request['actual_completion_time']
    request_foc_target = request['ttpu']

    # Time out for actual request handle time
    time.sleep(request_time_to_process/1000000000000000000)

    # Update performance metrics
    metrics['total_time_to_assign'] += request_time_to_assign
    metrics['total_processing_time'] += request_time_to_process
    if request_time_to_assign <= request_foc_target:
        metrics['total_foc_met'] += 1
    metrics['total_requests_processed'] += 1

    # Remove the assigned request from requests_df
    request_df.drop(request_df[(request_df['request_id'] == request['request_id']) & (request_df['assign_date'] == request['assign_date'])].index, inplace=True)


def build_agent_dataframe(requests_df):
    """
        This function builds the agent dataframe
    """
    return requests_df.groupby('agent_id')['list_rfs'].apply(lambda x: x.explode().dropna().unique()).reset_index()
    

def assign_request(agent, requests_df):
    """
        This function looks at the agent info passed as argument, 
        looks for requests in the requests dataframe where agent routing filters
        match with request routing filters and then sends those requests to a 
        prioritization algorithm which returns a single request
    """

    # Filter the requests based on the escalated flag
    escalated_requests = requests_df[(requests_df['is_escalated'] == True) & (requests_df['assigned'] == False)]
    non_escalated_requests = requests_df[(requests_df['is_escalated'] == False) & (requests_df['assigned'] == False)]
    
    # Check if there are any escalated requests
    if not escalated_requests.empty:
        # Filter the escalated requests based on routing filters, if any of the agents one are present in the request list, add request to eligible_requests
        eligible_requests = escalated_requests[escalated_requests.apply(lambda x: any(rf in agent['list_rfs'] for rf in x['list_rfs']), axis=1)]
    else:
        # Filter the non-escalated requests based on routing filters, if any of the agents one are present in the request list, add request to eligible_requests
        eligible_requests = non_escalated_requests[non_escalated_requests.apply(lambda x: any(rf in agent['list_rfs'] for rf in x['list_rfs']), axis=1)]
    
    # Check if there are any eligible requests
    if eligible_requests.empty:
        print(f"No eligible requests found for agent {agent['agent_id']}")
        return
    
    # Use the prioritization algorithm to assign a request among the eligible requests
    assigned_request = prioritize_requests(eligible_requests)
    print(f"Request {assigned_request.request_id} is being processed by pein {agent['agent_id']} at time {datetime.now()}")
    
    # Mark the request as assigned
    request_df.loc[(request_df['request_id'] == assigned_request.request_id) & (request_df['assign_date'] == assigned_request.assign_date), 'assigned'] = True
    
    # Assign the prioritized request to the agent
    process_request(requests_df, assigned_request)


def prioritize_requests(requests):
    """
        This function receives a request dataframe and runs a 
        prioritization algorithm to return a single request
    """
    # Calculate the time difference between the current time and the order date
    now_series = pd.Series([datetime.now(timezone.utc)] * len(requests), index=requests.index)
    requests['time_difference'] = (now_series - requests['orderdate']).dt.total_seconds()/60.0

    # First-In-First-Out: Select the request that arrived earliest
    if PRIORIZATION_ALGORITHM == 'fifo':
        # Sort the requests based on the time difference
        requests.sort_values(by='time_difference', ascending=False, inplace=True)

    # Current mode of operation: Select the request with the highest score
    elif PRIORIZATION_ALGORITHM == 'foc':
        # Calculate the score for each request
        requests['score'] = requests['time_difference'] / requests['ttpu']
        requests['score'].fillna(requests['time_difference']/SIMULATOR_DEFAULT_TTPU, inplace=True)
        # Sort the requests based on the score
        requests.sort_values(by='score', ascending=False, inplace=True)
    
    # Return the top priority request
    return requests.iloc[0]

def run(agents_df, request_df):
    try:
        while not request_df[request_df['assigned'] == False].empty:
            for idx, agent_row in agents_df.iterrows():
                if request_df[request_df['assigned'] == False].empty:
                    break
                assign_request(agent_row, request_df)
            time.sleep(1/1000000)
    except Exception as e:
        print(f"Error processing request: {e}")


if __name__ == "__main__":
    print(f"Starting the simulation {datetime.now()}")

    # Build the request dataframe
    request_df = build_request_dataframe()
    request_df['assigned'] = False
    agents_df = build_agent_dataframe(request_df)

    print(f"BEFORE PROCESSING ---> Total no. of requests in requests_df is {len(request_df)}")

    # Process each request in the dataframe
    # try:
    #     for idx, request_row in request_df.iterrows():
    #         process_request(request_df, request_row)
    # except Exception as e:
    #     print(f"Error processing request: {e}")

    run(agents_df, request_df)

    print(f"AFTER PROCESSING ---> Total no. of requests in requests_df is {len(request_df)}")

    print(f"Count Overall ---> {count_all}")
    print(f"Count Empty ---> {count_empty}")
    print(f"Count X ---> {count_x}")

    # Print statistics
    print("\nSimulation Statistics:")
    print(f"Total Requests Processed: {metrics['total_requests_processed']}")
    if metrics['total_requests_processed'] > 0:
        print(f"Percentage of FOC Met: {metrics['total_foc_met'] / metrics['total_requests_processed'] * 100:.2f}%")
        print(f"Average Time to Assign: {metrics['total_time_to_assign'] / metrics['total_requests_processed']:.2f} days")
        print(f"Average Processing Time: {(metrics['total_processing_time']/(24 * 3600)) / metrics['total_requests_processed']:.2f} days")
    print("Simulation completed")
