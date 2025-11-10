from contextlib import closing
import sys
sys.path.append('../..')
from datetime import datetime, timedelta
import random
import simpy
import pandas as pd
import pyodbc
import numpy as np
import teradatasql
pd.options.mode.chained_assignment = None  # default='warn'
from shared.all_envs import TD_HOST, TD_USER, TD_PASS, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS

def input_with_default(prompt, default):
    # Display the prompt with the default value
    user_input = input(f"{prompt} [{default}]: ")
    # Return the user input if provided, otherwise return the default value
    return user_input or default


def localize_and_convert(column, initial_tz='UTC', target_tz='UTC'):
    """Localize and convert a datetime column to the target timezone"""
    return pd.to_datetime(column).dt.tz_localize(initial_tz).dt.tz_convert(target_tz).dt.floor('s')


def calculate_dates(row, env):
    # timezone = pytz.utc
    # simulation_start_date = timezone.localize(datetime.strptime(SIMULATION_START_DATE, "%Y-%m-%d"))
    # order_date = datetime.now() + timedelta(days=(row['orderdate'] - simulation_start_date).days)
    order_date = datetime.now() + timedelta(seconds=env.now)
    assignment_date = order_date + timedelta(seconds=row['actual_assignment_time'])
    pickup_date = order_date + timedelta(days=row['ttpu'])
    if pd.isna(row['actual_completion_time']):
        completion_date = pd.NaT
    else:
        completion_date = assignment_date + timedelta(seconds=row['actual_completion_time'])
    return pd.Series([order_date, assignment_date, pickup_date, completion_date], index=['order_date', 'assignment_date', 'pickup_date', 'completion_date'])


def build_ttpu_targets_dataframe():
    """Retrieve a list of foc_targets/slas from the JARVIS database

    Returns:
        Dataframe: List of all foc_targets/slas
    """
    with closing(
        pyodbc.connect('DRIVER=Teradata Database ODBC Driver 17.20; DBCNAME='+TD_HOST+'; UID='+TD_USER+'; PWD='+TD_PASS+';')
        ) as conn:
        sql_foc_targets = f"""SELECT request_source, 
                                     product, 
                                     service_region, 
                                     request_type, 
                                     time_to_pickup_target_days AS source_focTarget_new,
                                     contract_sla AS has_sla_new,
                                     gk_id AS source_goldenCustomer_id
                              FROM GRP_JARVIS_ANALYSIS.dim_smtpth_stm_trgt;"""
        df = pd.read_sql(sql_foc_targets, conn)
        
        # Replace 'NA' with '' and gk_id to string values
        df.replace('NA', '', inplace=True)
        df['source_goldenCustomer_id'] = df['source_goldenCustomer_id'].astype(str)
        print("FOC-TARGET TABLE LOADED")
    return df


def build_request_dataframe(env):
    """
        This function builds the request dataframe
    """
    query_td = f"""
                    SELECT	smtpth_req_id, smtpth_req_start_dt, smtpth_req_comp_dt
                    FROM GRP_JARVIS_ANALYSIS.fact_smtpth_request_v2 
                    WHERE CAST(smtpth_req_start_dt AS DATE) >= DATE '{SIMULATION_START_DATE}'
                    and CAST(smtpth_req_start_dt AS DATE) < DATE '{SIMULATION_END_DATE}' and 
                    smtpth_req_start_dt is not null and smtpth_req_comp_dt is not null
                """

    qry_getwork = f"""
                      SELECT *
                      FROM [bbm_stm].[dbo].[getwork_results] 
                      WHERE assign_date >= '{SIMULATION_START_DATE}' 
                      and assign_date < '{SIMULATION_END_DATE}'
                      and work_status = 'WORK'
                      ORDER BY [assign_date]
                   """

    qry_escalation = f"""
                          SELECT *
                          FROM [bbm_stm].[dbo].[escalation]
                      """

    qry_managers = f"""
                       SELECT person_login1, person_full_name, person_manager_name, person_hrchy_level4_name AS CP2_name, 
                       person_hrchy_level3_name AS CP3_name, person_scd_current_row 
                       FROM GRP_JARVIS_ANALYSIS.dim_person WHERE person_scd_current_row = 1
                    """
    
    qry_priority = f"""
                        SELECT *
                        FROM [bbm_stm].[dbo].[skill_agent_priority]
                    """

    # Connection to Teradata and MS SQL Server
    with teradatasql.connect(host=TD_HOST,user=TD_USER, password=TD_PASS) as conn_td:
        requests = pd.read_sql(query_td, conn_td)
        managers = pd.read_sql(qry_managers, conn_td)

    conn_mssql = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
    
    getwork = pd.read_sql_query(qry_getwork, conn_mssql)
    escalation = pd.read_sql_query(qry_escalation, conn_mssql)

    # Dropping nulls and merging the dataframes to get completion date
    getwork = getwork.loc[~getwork['external_id'].isna()]

    # Adding is_escalated column
    getwork['is_escalated'] = np.where(getwork['external_id'].isin(escalation['request_id']), 1, 0)
    TOTAL_ESCALATIONS = getwork['is_escalated'].sum()
    print(f"Total number of escalations: {TOTAL_ESCALATIONS}")

    getwork_with_comp_date = getwork.merge(
        requests,
        left_on=['request_id'],
        right_on=['smtpth_req_id'],
        how='left'
    )

    getwork_with_comp_date = getwork_with_comp_date.merge(
        managers,
        left_on=['agent_id'],
        right_on=['person_login1'],
        how='left'
    )

    getwork_with_comp_date.loc[getwork_with_comp_date['agent_id'] == 'david.rainsford', ['CP2_name', 'CP3_name']] = ['VERONIQUE TURENNE', 'NATHALIE ROMPRE']

    # Making sure both time columns are in the same time zone (UTC)
    getwork_with_comp_date['assign_date'] = localize_and_convert(getwork_with_comp_date['assign_date'])
    getwork_with_comp_date['orderdate'] = localize_and_convert(getwork_with_comp_date['orderdate'])
    getwork_with_comp_date['smtpth_req_comp_dt'] = localize_and_convert(getwork_with_comp_date['smtpth_req_comp_dt'], 'America/New_York', 'UTC')

    # Calculating actual assignment and completion time in seconds
    getwork_with_comp_date['actual_assignment_time'] = (getwork_with_comp_date['assign_date'] - getwork_with_comp_date['orderdate']).dt.total_seconds()
    getwork_with_comp_date['actual_completion_time'] = (getwork_with_comp_date['smtpth_req_comp_dt'] - getwork_with_comp_date['assign_date']).dt.total_seconds()
    
    request_df = getwork_with_comp_date[['request_id', 'agent_id', 'CP2_name', 'CP3_name', 'orderdate', 'assign_date', 'ttpu', 'skill_id', 'request_source', 
                                          'product', 'service_region', 'request_type', 'customer_support_model',
                                          'control_desk', 'golden_customer', 'customer_market_segment',
                                          'preferred_language', 'external_id', 'is_escalated',
                                          'actual_assignment_time', 'actual_completion_time']].drop_duplicates()

    print(f"TOTAL_SIMULATION_DURATION_DAYS ---> {TOTAL_SIMULATION_DURATION_DAYS}")

    request_df['list_rfs'] = request_df['skill_id'].apply(lambda row: [row])

    # Add a column to track assignment status
    request_df['assigned'] = False

    # Add a column to track time between two consecutive clicks
    request_df['time_since_last_click'] = (request_df['assign_date'].shift(-1) - request_df['assign_date']).dt.total_seconds()
    request_df['time_since_last_click'] = request_df['time_since_last_click'].fillna(0)

    # Update TTPu Target values if new targets are provided
    if NEW_TTPu_TARGETS == "yes":
        # Option 1 - Read from Teradata table
        new_targets_df = build_ttpu_targets_dataframe()
        # Option 2 - Run below line instead of above line if you want to read from a local CSV file instead of Teradata table
        # to test values for new TTPu targets
        # new_targets_df = pd.read_csv("ttpu_targets.csv")
        ttpuTargetColumns = ['request_source', 'product', 'service_region', 'request_type']
        request_df = request_df.merge(new_targets_df, 
                  on=ttpuTargetColumns,
                  how='left')
        request_df['ttpu'] = request_df['source_focTarget_new'].apply(lambda x: float(SIMULATOR_DEFAULT_TTPU) if np.isnan(x) else float(x))
        request_df['has_sla'] = request_df['has_sla_new'].apply(lambda x: False if ((x == 0) | (np.isnan(x))) else True)
        request_df.drop(columns=['source_focTarget_new', 'has_sla_new'], inplace=True)
    else:
        request_df['has_sla'] = 0

    # Add columns to track simulated assignment date and completion date
    request_df['simulated_assignment_date'] = datetime.now() + timedelta(seconds=env.now)
    request_df['simulated_completion_date'] = datetime.now() + timedelta(seconds=env.now)

    # Add columns to track performance metrics
    request_df['actual_total_foc_met'] = 0
    request_df['actual_total_sla_met'] = 0
    request_df['actual_nmac_foc_met'] = 0
    request_df['simulated_assignment_time'] = 0
    request_df['simulated_completion_time'] = 0
    request_df['simulated_total_foc_met'] = 0
    request_df['simulated_total_sla_met'] = 0
    request_df['simulated_nmac_foc_met'] = 0

    # Add the new datetime values to each row in the DataFrame
    request_df[['order_date', 'assignment_date', 'pickup_date', 'completion_date']] = \
        request_df.apply(lambda row: calculate_dates(row, env), axis=1)
    
    # request_df.to_csv("initial_requests.csv", encoding="utf-8")

    # If testing P1P2 feature, add a column to track skill priority
    if TEST_P1P2_FEATURE == "yes":
        # Read skill priority values from MS SQL Server
        skill_agent_priority = pd.read_sql_query(qry_priority, conn_mssql)
        request_df = request_df.merge(skill_agent_priority, 
                  left_on=['skill_id', 'agent_id'],
                  right_on=['skill_id', 'agent_id'],
                  how='left',
                  suffixes=('', '_y'))
        request_df['skill_priority'] = request_df['skill_priority'].apply(lambda x: 0 if np.isnan(x) else x)
    
    return request_df


def build_agent_dataframe(requests_df):
    """
        This function builds the agent dataframe
    """
    return requests_df.groupby('agent_id')['list_rfs'].apply(lambda x: x.explode().dropna().unique()).reset_index()
    

def run(env, agents, request_df):
    try:
        start_run = env.now
        while not request_df[request_df['assigned'] == False].empty:
            for _, request_row in request_df.iterrows():
                agent_row = agents.loc[agents['agent_id'] == request_row['agent_id']].iloc[0]
                if request_df[request_df['assigned'] == False].empty:
                    break
                yield env.process(assign_request(env, agent_row, request_df, NEW_TTPu_TARGETS, is_push_model=False, last_request_of_day=False, original_request=request_row))
            yield env.timeout(1) # Allow the environment to process the event
        print(f"Total time taken by regular run(): {env.now - start_run} seconds")
        return "Simulation completed"
    except Exception as e:
        print(f"Error processing request: {e}")


def run_push_model(env, agents, request_df, PUSH_REQUESTS_PER_DAY):
    try:
        start_run = env.now
        daily_total_limit = len(agents) * PUSH_REQUESTS_PER_DAY
        print(f"Number of agents: {len(agents)} and number of requests assigned per day: {daily_total_limit}")
        while not request_df[request_df['assigned'] == False].empty:
            # Requests to be assigned each day
            round_count = 0
            current_assignment_count = 1
            while round_count < PUSH_REQUESTS_PER_DAY:
                for _, request_row in request_df.iterrows():
                    agent_row = agents.loc[agents['agent_id'] == request_row['agent_id']].iloc[0]
                    if request_df[request_df['assigned'] == False].empty:
                        break
                    if current_assignment_count % daily_total_limit == 0:
                        print(f"Current assignment count: {current_assignment_count} and it is the last request of the day.")
                        yield env.process(assign_request(env, agent_row, request_df, is_push_model=True, last_request_of_day=True, selected_request=request_row))
                    else:
                        print(f"Current assignment count: {current_assignment_count}.")
                        yield env.process(assign_request(env, agent_row, request_df, is_push_model=True, last_request_of_day=False, selected_request=request_row))
                    current_assignment_count += 1
                round_count += 1
                   
        print(f"Total time taken by push model run(): {env.now - start_run} seconds")
        return "Simulation completed"      
    except Exception as e:
        print(f"Error processing request: {e}")


def assign_request(env, agent, request_df, NEW_TTPu_TARGETS, is_push_model=False, last_request_of_day=False, original_request=None):
    """
        This function looks at the agent info passed as argument, 
        looks for requests in the requests dataframe where agent routing filters
        match with request routing filters and then sends those requests to a 
        prioritization algorithm which returns a single request
    """
    if NEW_TTPu_TARGETS == "yes":
        if PRIORIZATION_ALGORITHM != 'fifo':
            # # Filter the requests based on the sla and escalated flag
            # sla_escalated_requests = request_df[(request_df['has_sla'] == True) & (request_df['is_escalated'] == True) & (request_df['assigned'] == False)]
            # sla_non_escalated_requests = request_df[(request_df['has_sla'] == True) & (request_df['is_escalated'] == False) & (request_df['assigned'] == False)]
            # non_sla_escalated_requests = request_df[(request_df['has_sla'] == False) & (request_df['is_escalated'] == True) & (request_df['assigned'] == False)]
            # non_sla_non_escalated_requests = request_df[(request_df['has_sla'] == False) & (request_df['is_escalated'] == False) & (request_df['assigned'] == False)]

            # dfs = [sla_escalated_requests, sla_non_escalated_requests, non_sla_escalated_requests, non_sla_non_escalated_requests]
            
            # # Loop through the dataframes to find the first non-empty dataframe that fits the agent routing filters
            # for df in dfs:
            #     if not df.empty:
            #         # Filter the requests based on agent id, if any of the agents one are present in the request list, add request to eligible_requests
            #         eligible_requests = df[df['agent_id'] == agent['agent_id']]
            #         break

            # Filter the requests based on agent id, if any of the agents one are present in the request list, add request to eligible_requests
            eligible_requests = request_df[(request_df['agent_id'] == agent['agent_id']) & (request_df['assigned'] == False)]

            # Check if there are any eligible requests
            if eligible_requests.empty:
                print(f"No eligible requests found for agent {agent['agent_id']}")
                return
        else:
            eligible_requests = request_df[request_df['assigned'] == False]
    
        # Use the prioritization algorithm to assign a request among the eligible requests
        assigned_request = prioritize_requests(env, eligible_requests)
    else:
        if TEST_P1P2_FEATURE == "yes":
            # Filter the requests based on agent id, if any of the agents one are present in the request list, add request to eligible_requests
            eligible_requests = request_df[(request_df['agent_id'] == agent['agent_id']) & (request_df['assigned'] == False)]

            # Look for P1 requests and prioritize only from p1 requests
            p1_requests = eligible_requests[eligible_requests['skill_priority'] == 1]
            if len(p1_requests) > 0:
                assigned_request = prioritize_requests(env, p1_requests)
            else:
                # Prioritize from all requests
                assigned_request = prioritize_requests(env, eligible_requests)
        else:
            assigned_request = original_request
    print(f"Request {assigned_request.request_id} is being processed by agent {agent['agent_id']}")
    
    # Mark the request as assigned and update its simulated_assignment_time to original_request's actual_assignment_time
    request_df.loc[(request_df['request_id'] == assigned_request.request_id) & (request_df['assignment_date'] == assigned_request.assignment_date), 'assigned'] = True
    assigned_request['simulated_assignment_time'] = original_request['actual_assignment_time']
    
    # Assign the prioritized request to the agent
    yield env.process(process_request(env, request_df, assigned_request, is_push_model, last_request_of_day))


def prioritize_requests(env, requests):
    """
        This function receives a request dataframe and runs a 
        prioritization algorithm to return a single request
    """
    if requests.empty:
        raise ValueError("No requests available to prioritize")
    
    # Calculate the time difference between the current time and the order date
    now_series = pd.Series([datetime.now() + timedelta(seconds=env.now)] * len(requests), index=requests.index)
    requests['time_difference'] = (now_series - requests['order_date']).dt.total_seconds()/60.0

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
    if requests.iloc[0]['score'] <= 0:
        return
    return requests.iloc[0]


def process_request(env, request_df, request, is_push_model=False, last_request_of_day=False):
    """
        Process the request for the time duration equal to actual handle time
        and update the performance metrics
    """

    if request.empty:
        return # If request is empty, exit the function

    # If using a Push Model
    if is_push_model and (datetime.now() + timedelta(seconds=env.now) - request['order_date']).days > 0:
        diff = (datetime.now() + timedelta(seconds=env.now) - request['order_date']).total_seconds()
        print(f"Diff between Order date and Simulated Assignment Date - {(datetime.now() + timedelta(seconds=env.now) - request['order_date']).days} days OR {diff} seconds")
        simulated_assignment_date = datetime.now() + timedelta(seconds=env.now) + timedelta(seconds=diff)
        print(f"Simulated Assignment Date - {simulated_assignment_date} and simulated time to assign is {(simulated_assignment_date - request['order_date']).days} days")
    else:
        # If using a Regular Model
        if NEW_TTPu_TARGETS == "yes":
            simulated_assignment_time = int(random.uniform(request['simulated_assignment_time']*0.95, request['simulated_assignment_time']*1.05))
        else:
            simulated_assignment_time = int(random.uniform(request['actual_assignment_time']*0.95, request['actual_assignment_time']*1.05))
        simulated_assignment_date = request['order_date'] + timedelta(seconds=simulated_assignment_time)
        if pd.isna(request['actual_completion_time']):
            simulated_completion_time = np.nan
            simulated_completion_date = pd.NaT
        else:
            simulated_completion_time = int(random.uniform(request['actual_completion_time']*0.95, request['actual_completion_time']*1.05))
            simulated_completion_date = request['order_date'] + timedelta(seconds=simulated_completion_time)

    processed_request = (request_df['request_id'] == request.request_id) & (request_df['assignment_date'] == request.assignment_date)
    request_df.loc[processed_request, 'simulated_assignment_time'] = simulated_assignment_time
    request_df.loc[processed_request, 'simulated_assignment_date'] = simulated_assignment_date
    request_df.loc[processed_request, 'simulated_completion_time'] = simulated_completion_time
    request_df.loc[processed_request, 'simulated_completion_date'] = simulated_completion_date

    request['simulated_assignment_time'] = simulated_assignment_time

    # Update performance metrics
    if request['actual_assignment_time'] <= request['ttpu']*SECONDS_PER_DAY:
        request_df.loc[processed_request, 'actual_total_foc_met'] = 1
        if request['has_sla'] == 1:
            request_df.loc[processed_request, 'actual_total_sla_met'] = 1
        if request['request_type'] in ('new', 'move', 'add', 'change'):
            request_df.loc[processed_request, 'actual_nmac_foc_met'] = 1

    if request['simulated_assignment_time'] <= request['ttpu']*SECONDS_PER_DAY:
        request_df.loc[processed_request, 'simulated_total_foc_met'] = 1
        if request['has_sla'] == 1:
            request_df.loc[processed_request, 'simulated_total_sla_met'] = 1
        if request['request_type'] in ('new', 'move', 'add', 'change'):
            request_df.loc[processed_request, 'simulated_nmac_foc_met'] = 1

    metrics['total_requests_processed'] += 1
    
    # If using Regular Model, time out for actual wait time between two consecutive Get Work clicks
    if not is_push_model:
        print(f"Waiting for {request['time_since_last_click']} seconds")
        yield env.timeout(request['time_since_last_click'])

    # If using Push Model, time out for the entire day if it is the last request of the day
    if is_push_model and last_request_of_day:
        yield env.timeout(SECONDS_PER_DAY)

    print(f"Processed request {request['request_id']}. Total requests processed: {metrics['total_requests_processed']}")


def calculate_performance_metrics(request_df, PUSH_REQUESTS_PER_DAY):
    unique_requests_idx = request_df.groupby('request_id')['assignment_date'].idxmin()
    unique_requests = request_df.loc[unique_requests_idx]
    TOTAL_NUMBER_OF_SLA_REQUESTS = len(unique_requests[unique_requests['has_sla'] == True])

    # Get Overall Metrics
    overall_total_number_of_agents = len(unique_requests['agent_id'].unique())
    overall_total_number_of_requests = len(unique_requests)
    overall_total_number_of_nmac_requests = len(unique_requests[unique_requests['request_type'].isin(['new', 'move', 'add', 'change'])])
    overall_actual_assignment_time = round(unique_requests['actual_assignment_time'].mean() / SECONDS_PER_DAY, 2) if SECONDS_PER_DAY > 0 else 0
    overall_simulated_assignment_time = round(unique_requests['simulated_assignment_time'].mean() / SECONDS_PER_DAY, 2) if SECONDS_PER_DAY > 0 else 0
    overall_actual_std_assignment_time = round(unique_requests['actual_assignment_time'].std() / SECONDS_PER_DAY, 2) if SECONDS_PER_DAY > 0 else 0
    overall_simulated_std_assignment_time = round(unique_requests['simulated_assignment_time'].std() / SECONDS_PER_DAY, 2) if SECONDS_PER_DAY > 0 else 0
    overall_actual_coeffVar_assignment_time = round(overall_actual_std_assignment_time / overall_actual_assignment_time, 2) if overall_actual_assignment_time > 0 else 0
    overall_simulated_coeffVar_assignment_time = round(overall_simulated_std_assignment_time / overall_simulated_assignment_time, 2) if overall_simulated_assignment_time > 0 else 0
    overall_actual_total_foc_met = round((unique_requests['actual_total_foc_met'].sum() / overall_total_number_of_requests) * 100, 2) if overall_total_number_of_requests > 0 else 0
    overall_simulated_total_foc_met = round((unique_requests['simulated_total_foc_met'].sum() / overall_total_number_of_requests) * 100, 2) if overall_total_number_of_requests > 0 else 0
    overall_actual_nmac_foc_met = round((unique_requests['actual_nmac_foc_met'].sum() / overall_total_number_of_nmac_requests) * 100, 2) if overall_total_number_of_nmac_requests > 0 else 0
    overall_simulated_nmac_foc_met = round((unique_requests['simulated_nmac_foc_met'].sum() / overall_total_number_of_nmac_requests) * 100, 2) if overall_total_number_of_nmac_requests > 0 else 0
    overall_metrics = pd.DataFrame({
        'CP3_name': 'Overall',
        'CP2_name': '',
        'Number of Agents': overall_total_number_of_agents,
        'Number of Requests': overall_total_number_of_requests,
        'Average Actual Assignment Time (days)': overall_actual_assignment_time,
        'Average Simulated Assignment_time (days)': overall_simulated_assignment_time,
        'Standard Deviation of Actual Assignment Time (days)': overall_actual_std_assignment_time,
        'Standard Deviation of Simulated Assignment Time (days)': overall_simulated_std_assignment_time,
        'Coefficient of Variation of Actual Assignment Time': overall_actual_coeffVar_assignment_time,
        'Coefficient of Variation of Simulated Assignment Time': overall_simulated_coeffVar_assignment_time,
        'Actual Total Requests met TTPu Targets (%)': overall_actual_total_foc_met,
        'Simulated Total Requests met TTPu Targets (%)': overall_simulated_total_foc_met,
        'Actual NMAC Requests met TTPu Targets (%)': overall_actual_nmac_foc_met,
        'Simulated NMAC Requests met TTPu Targets (%)': overall_simulated_nmac_foc_met
    }, index=['o'])
    
    grouped_unique_requests_by_managers = unique_requests.groupby(['CP3_name', 'CP2_name'])

    def calculate_grouped_metrics(x):
        total_number_of_agents = len(x['agent_id'].unique())
        total_number_of_requests = len(x)
        total_number_of_nmac_requests = len(x[x['request_type'].isin(['new', 'move', 'add', 'change'])])
        actual_assignment_time = round(x['actual_assignment_time'].mean() / SECONDS_PER_DAY, 2)
        simulated_assignment_time = round(x['simulated_assignment_time'].mean() / SECONDS_PER_DAY, 2)
        actual_std_assignment_time = round(x['actual_assignment_time'].std() / SECONDS_PER_DAY, 2)
        simulated_std_assignment_time = round(x['simulated_assignment_time'].std() / SECONDS_PER_DAY, 2)
        actual_coeffVar_assignment_time = round(actual_std_assignment_time / actual_assignment_time, 2) if actual_assignment_time > 0 else 0
        simulated_coeffVar_assignment_time = round(simulated_std_assignment_time / simulated_assignment_time, 2) if simulated_assignment_time > 0 else 0
        actual_total_foc_met = round((x['actual_total_foc_met'].sum() / total_number_of_requests) * 100, 2) if total_number_of_requests > 0 else 0
        simulated_total_foc_met = round((x['simulated_total_foc_met'].sum() / total_number_of_requests) * 100, 2) if total_number_of_requests > 0 else 0
        actual_nmac_foc_met = round((x['actual_nmac_foc_met'].sum() / total_number_of_nmac_requests) * 100, 2) if total_number_of_nmac_requests > 0 else 0
        simulated_nmac_foc_met = round((x['simulated_nmac_foc_met'].sum() / total_number_of_nmac_requests) * 100, 2) if total_number_of_nmac_requests > 0 else 0
        return pd.Series([
            total_number_of_agents, total_number_of_requests, 
            actual_assignment_time, simulated_assignment_time, 
            actual_std_assignment_time, simulated_std_assignment_time,
            actual_coeffVar_assignment_time, simulated_coeffVar_assignment_time,
            actual_total_foc_met, simulated_total_foc_met, 
            actual_nmac_foc_met, simulated_nmac_foc_met
            ], 
            index=[
                'Number of Agents', 'Number of Requests', 
                'Average Actual Assignment Time (days)', 'Average Simulated Assignment_time (days)', 
                'Standard Deviation of Actual Assignment Time (days)', 'Standard Deviation of Simulated Assignment Time (days)',
                'Coefficient of Variation of Actual Assignment Time', 'Coefficient of Variation of Simulated Assignment Time',
                'Actual Total Requests met TTPu Targets (%)', 'Simulated Total Requests met TTPu Targets (%)',
                'Actual NMAC Requests met TTPu Targets (%)', 'Simulated NMAC Requests met TTPu Targets (%)'
            ])

    grouped_results = grouped_unique_requests_by_managers.apply(calculate_grouped_metrics).reset_index()
    grouped_results = pd.concat([grouped_results, overall_metrics])

    grouped_results.to_csv("grouped_results.csv", encoding="utf-8")

    # DEBUG STATEMENTS
    # unique_requests.to_csv("unique_requests_actual.csv", encoding="utf-8")

    # Print statistics
    # print(f"\nSimulation Statistics for duration {SIMULATION_START_DATE} - {SIMULATION_END_DATE}:")
    # print(f"Total Requests Processed: {len(request_df)}")
    # if metrics['total_requests_processed'] > 0:
    #     print("Performance Metrics for Actual Historical Data")
    #     print(f"---- Average Time To Assign A Request: {(unique_requests['actual_assignment_time'].mean()/SECONDS_PER_DAY):.2f} days")
    #     print(f"---- Median Time To Assign A Request: {(unique_requests['actual_assignment_time'].median()/SECONDS_PER_DAY):.2f} days")
    #     print(f"---- Average Time To Complete A Request: {(unique_requests['actual_completion_time'].mean()/SECONDS_PER_DAY):.2f} days")
    #     print(f"---- Median Time To Complete A Request: {(unique_requests['actual_completion_time'].median()/SECONDS_PER_DAY):.2f} days")
    #     print(f"---- Percentage of Total Requests that met FOC: {unique_requests['actual_total_foc_met'].sum()/len(unique_requests) * 100:.2f}%")
    #     print(f"---- Percentage of NMAC Requests that met FOC: {unique_requests['actual_nmac_foc_met'].sum()/TOTAL_NUMBER_OF_NMAC_REQUESTS * 100:.2f}%")
    #     print(f"---- Percentage of SLA Requests that met FOC: N/A (No SLA requests found)")
    #     if PUSH_REQUESTS_PER_DAY > 0:
    #         print(f"Performance Metrics for Simulated Data using Push Model")
    #     else:
    #         print(f"Performance Metrics for Simulated Data using Current Prioritization Algorithm - {PRIORIZATION_ALGORITHM}")
    #     print(f"---- Average Time To Assign A Request: {(unique_requests['simulated_assignment_time'].mean()/SECONDS_PER_DAY):.2f} days")
    #     print(f"---- Median Time To Assign A Request: {(unique_requests['simulated_assignment_time'].median()/SECONDS_PER_DAY):.2f} days")
    #     print(f"---- Average Time To Complete A Request: {(unique_requests['simulated_completion_time'].mean()/SECONDS_PER_DAY):.2f} days")
    #     print(f"---- Median Time To Complete A Request: {(unique_requests['simulated_completion_time'].median()/SECONDS_PER_DAY):.2f} days")
    #     print(f"---- Percentage of Total Requests that met FOC: {unique_requests['simulated_total_foc_met'].sum()/len(unique_requests) * 100:.2f}%")
    #     print(f"---- Percentage of NMAC Requests that met FOC: {unique_requests['simulated_nmac_foc_met'].sum()/TOTAL_NUMBER_OF_NMAC_REQUESTS * 100:.2f}%")
    #     print(f"---- Percentage of SLA Requests that met FOC: N/A (No SLA requests found)")
    #     print("Simulation completed")


if __name__ == "__main__":
    print(f"Starting the simulation {datetime.now()}")
    env = simpy.Environment()

    PRIORIZATION_ALGORITHM = ""  # Options: 'fifo', 'foc'
    SIMULATOR_DEFAULT_TTPU = 8.0  # Default Time to PickUp
    SECONDS_PER_DAY = 24 * 60 * 60
    SIMULATION_START_DATE = ""
    SIMULATION_END_DATE = ""
    PUSH_REQUESTS_PER_DAY = 10
    TOTAL_ESCALATIONS = 0

    metrics = {
        'total_requests_processed': 0
    }

    print("Please provide values for below prompts, press enter to accept default values")
    PRIORIZATION_ALGORITHM = input_with_default("Please enter the prioritization method (fifo, foc): ", "foc")
    SIMULATION_START_DATE = input_with_default("Please enter the simulation start date (YYYY-MM-DD): ", "2024-05-01")
    SIMULATION_END_DATE = input_with_default("Please enter the simulation end date (YYYY-MM-DD): ", "2024-06-01")
    PUSH_REQUESTS_PER_DAY = int(input_with_default("Please enter the number of requests to push each day: ", 0))
    NEW_TTPu_TARGETS = input_with_default("Do you want to test new TTPu targets? (yes/ no): ", "no")
    TEST_P1P2_FEATURE = input_with_default("Do you want to test P1P2 feature? (yes/ no): ", "no")

    sim_start_date = datetime.strptime(SIMULATION_START_DATE, "%Y-%m-%d")
    sim_end_date = datetime.strptime(SIMULATION_END_DATE, "%Y-%m-%d")
    TOTAL_SIMULATION_DURATION_DAYS = (sim_end_date - sim_start_date).days

    # Build the request and agent dataframe
    request_df = build_request_dataframe(env)
    agents_df = build_agent_dataframe(request_df)

    print(f"BEFORE PROCESSING ---> Total no. of requests in requests_df is {len(request_df[request_df['assigned'] == False])}")

    if PUSH_REQUESTS_PER_DAY > 0:
        proc = env.process(run_push_model(env, agents_df, request_df, PUSH_REQUESTS_PER_DAY))
    else:
        proc = env.process(run(env, agents_df, request_df))
    env.run(until=proc)

    calculate_performance_metrics(request_df, PUSH_REQUESTS_PER_DAY)

    # # DEBUG STATEMENTS
    # print(f"AFTER PROCESSING ---> Total no. of requests in requests_df is {len(request_df[request_df['assigned'] == False])}")
    # request_df.to_csv("final_requests.csv", encoding="utf-8")