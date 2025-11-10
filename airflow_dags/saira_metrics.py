import sys
# Adding the directory containing additional Python modules to the system path
sys.path.append('/usr/local/airflow/dags/stm/')

from datetime import datetime, timedelta
from airflow.decorators import dag, task

# Default arguments for the DAG, including owner, description, and notification settings
default_args = {
    "owner": "eq02977",
    "description": "SAiRA Performance metrics",
    "email": ["stm.alerts@bell.ca"],  
    "start_date": datetime(2024, 2, 17), 
    "retries": 0,  
    "email_on_failure": True,  
    "retry_delays": timedelta(minutes=2) 
}

@dag(
    dag_id="saira_performance_metric", 
    description="saira_performance_metric", 
    default_args=default_args,  
    catchup=False, 
    schedule_interval='0 0 * * MON',  #runs at midnight (UTC) every monday
    tags=["saira", "stm", "control_plan"]  
)
def main_task():
    getwork_df = extract_data_sqlserver() 
    filtered_df = filter_data(getwork_df) 
    data_load_to_Elastic(filtered_df, account_index_name='bbm_aiml_saira_control_plan-prod') 

@task()
def extract_data_sqlserver():
    # Task to extract data from SQL Server using Airflow's MSSQL hook
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB

    # Initialize environment variables and database connection
    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"  # Connection ID for MSSQL
    query = db.get_sql_query()  # Retrieve the SQL query
    print(query)
    mssql_hook = MsSqlHook(mssql_conn_id=connection_id)  # MSSQL hook for connecting to the database
    getwork_df = mssql_hook.get_pandas_df(query)  # Execute the query and fetch data as a Pandas DataFrame
    print(len(getwork_df))  # Print the number of rows fetched

    return getwork_df

@task()
def filter_data(getwork):
    # Task to filter and preprocess the extracted data
    import pandas as pd

    # Convert the 'assign_date' column to datetime and create additional columns
    getwork['assign_date'] = pd.to_datetime(getwork['assign_date'], errors='coerce', format='%y-%m-%d-%H:%M:%S')
    getwork['week'] = getwork['assign_date'].dt.strftime('%G-%V')  # Extract ISO week
    getwork['start_date_of_week'] = pd.to_datetime(getwork['week'] + '-1', format='%G-%V-%w')  # Start date of the week

    # Map short request sources to their full names
    getwork['source_full'] = getwork['request_source'].copy()
    getwork.loc[getwork['request_source'] == 'ssc', 'source_full'] = 'Self Serve Center'
    getwork.loc[getwork['request_source'] == 'pwo', 'source_full'] = 'Presales Workflow Optimization'
    getwork.loc[getwork['request_source'] == 'pss', 'source_full'] = 'Public Self Serve'
    getwork.loc[getwork['request_source'] == 'eom', 'source_full'] = 'Enterprise Order Manager'

    # Select and preprocess specific columns for the final filtered dataframe
    filtered_dataframe = getwork[['id', 'agent_id', 'request_id', 'work_status', 'assign_date', 'service_region', 
                                   'global_latency', 'smartpath_latency', 'stm_latency', 'start_date_of_week', 
                                   'source_full']]
    filtered_dataframe['agent_id'] = filtered_dataframe['agent_id'].fillna('none')  # Handle missing agent IDs
    filtered_dataframe['request_id'] = filtered_dataframe['request_id'].fillna('none')  # Handle missing request IDs
    filtered_dataframe['work_status'] = filtered_dataframe['work_status'].fillna('none')  # Handle missing work status
    filtered_dataframe['service_region'] = filtered_dataframe['service_region'].fillna('none')  # Handle missing regions
    filtered_dataframe['source_full'] = filtered_dataframe['source_full'].fillna('none')  # Handle missing sources
    filtered_dataframe['assign_date'] = filtered_dataframe['assign_date'].dt.strftime('%Y-%m-%d %H:%M:%S')  # Format date
    filtered_dataframe['start_date_of_week'] = filtered_dataframe['start_date_of_week'].dt.strftime('%Y-%m-%d %H:%M:%S')  # Format week start date

    print(filtered_dataframe.columns)  # Print column names
    print(len(filtered_dataframe))  # Print the number of rows in the filtered dataframe

    return filtered_dataframe

@task.virtualenv(requirements=['elasticsearch'])
def data_load_to_Elastic(dataframe, account_index_name):
    # Task to load the processed data into Elasticsearch
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.elastic_utils import EsManagement
    sys.path.append('/usr/local/airflow/dags/stm/')

    # Skip execution if the dataframe is empty
    if dataframe.empty:
        return

    import warnings
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")  # Suppress warnings

    # Define the Elasticsearch index mapping
    data_map = {"mappings": {
                "properties": {
                'id': {"type":"integer"},
                "agent_id": {"type":"keyword"},
                'request_id':{"type":"keyword"},
                'work_status':{"type":"keyword"},
                'assign_date':{"type":"date","format":"yyyy-MM-dd HH:mm:ss"},
                'service_region':{"type":"keyword"},
                'global_latency':{"type":"double"},
                'smartpath_latency':{"type":"double"},
                "stm_latency": {"type":"double"},
                'start_date_of_week':{"type":"date","format":"yyyy-MM-dd HH:mm:ss"},
                'source_full':{"type":"keyword"}

        }
    }}

    # Convert the dataframe to a list of records and insert into Elasticsearch
    array = dataframe.to_dict('records')
    env_var = AiflowEnvVariable()
    es_connection = EsManagement(env_var)
    es_connection.insert_documents(account_index_name, array, 'id')

# Trigger the DAG workflow
data = main_task()