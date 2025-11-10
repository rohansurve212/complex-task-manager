# Import necessary modules and add project directory to the airflow docker container path
import sys
sys.path.append('/usr/local/airflow/dags/stm/')

from datetime import datetime, timedelta
from airflow.decorators import dag, task

# Default arguments for the DAG
default_args = {
    "owner": "eq73914",
    "description": "Populating the dashboard with unassigned escalated requests",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2025,7,1),
    "retries":0,
    "email_on_failure": True,
    "retry_delay":timedelta(minutes=2)}

# Define the DAG
@dag (
    dag_id= "unassigned_escalation_reqs_dashboard",
    description = "Populating the dashboard with unassigned escalated requests",
    default_args = default_args,
    catchup = False,
    schedule_interval= '0 9 * * 1-5',  # Runs at 5 AM EST, Mon to Fri
    tags=["saira","stm","email_alert"]
)

def main_task():
    unassigned_reqs = query_escalations_unassigned()
    data_load_to_Elastic(unassigned_reqs, account_index_name='bbm_aiml_saira_unassigned_escalated_reqs-prod')

# Task to extract unassinged escalated requests
@task()
def query_escalations_unassigned():
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import pandas as pd

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"
    query = db.get_unassigned_escalated_requests_dashboard()

    if query != '':
        print(query)
        mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
        requests = mssql_hook.get_pandas_df(query)
        print(len(requests))
        return requests
    
    return pd.DataFrame()

@task.virtualenv(requirements=['elasticsearch'])
def data_load_to_Elastic(unassigned_reqs, account_index_name):
    # Add the required directory to the system path for importing utilities
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    
    # Import environment variables and Elasticsearch utility class
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.elastic_utils import EsManagement

    sys.path.append('/usr/local/airflow/dags/stm/')
    
    # Early return if the DataFrame is empty
    if unassigned_reqs.empty:
        print('no data to load')
        return

    # Suppress warnings for unverified HTTPS requests
    import warnings
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    # Convert the "unassigned_reqs" DataFrame to a dictionary format for insertion
    array = unassigned_reqs.to_dict('records')
    
    # Initialize environment variables and Elasticsearch management utility
    env_var = AiflowEnvVariable()
    es_connection = EsManagement(env_var)

    # # Create the Elasticsearch index with the defined mapping
    # es_connection.create_index(account_index_name, data_map)
    
    # Insert the data into Elasticsearch
    es_connection.insert_documents(account_index_name, array, 'request_id')

# Instantiate the DAG
data = main_task()

# Last Updated July 24th, 2025, 11:21 AM 