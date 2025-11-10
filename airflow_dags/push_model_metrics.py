# Add the system path
import sys
sys.path.append('/usr/local/airflow/dags/stm/')

# Import required libraries
from datetime import datetime, timedelta
from airflow.decorators import dag, task

# Define default arguments for the DAG
default_args = {
    "owner": "eq02977",  
    "description": "SAiRA Push Model metrics",  
    "email": ["stm.alerts@bell.ca"],  
    "start_date": datetime(2024, 10, 14), 
    "retries": 0, 
    "email_on_failure": True, 
    "retry_delays": timedelta(minutes=2) 
}

# Define the DAG
@dag(
    dag_id="push_model_metric",  
    description="push_model_metric", 
    default_args=default_args, 
    catchup=False,  
    schedule_interval='0 0 * * *', # runs at midnight (UTC) every day
    tags=["saira", "stm", "push_model"] 
)
def main_task():
    getwork_df = extract_data_sqlserver()
    ldap_df = ldap_data(getwork_df)
    data_load_to_Elastic(ldap_df, account_index_name='bbm_aiml_saira_push_model-prod')

# Task to extract data from SQL Server
@task()
def extract_data_sqlserver():
    # Import necessary libraries and modules
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    import pandas as pd
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB

    # Initialize environment variables and database utilities
    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"  # SQL Server connection ID
    
    # Fetch the SQL query for the task
    query = db.get_push_model_data()
    if query != '':
        # Log the query and execute it
        print(query)
        mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
        getwork_df = mssql_hook.get_pandas_df(query)
        print(len(getwork_df))  # Log the number of records fetched
        
        return getwork_df  # Return the fetched data
    return pd.DataFrame()  # Return an empty DataFrame if no query

# Task to fetch LDAP data and merge with extracted data
@task()
def ldap_data(getwork):
    # Import necessary libraries and modules
    from airflow.models.connection import Connection
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import teradatasql
    import pandas as pd

    # Initialize environment variables and database utilities
    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id_td = "teradata_stm"  # Teradata connection ID
    
    if not getwork.empty:
        # Extract unique agent IDs and format them for the query
        agent_ids = getwork['agent_id'].unique().tolist()
        agent_ids_str = ', '.join(f"'{agent_id}'" for agent_id in agent_ids)
        agent_ids_str = f"({agent_ids_str})"
        
        # Fetch the LDAP query
        query_td = db.get_ldap_data(agent_ids_str)
        if query_td != '':
            # Establish a connection to Teradata and execute the query
            conn = Connection.get_connection_from_secrets(connection_id_td)
            with teradatasql.connect(host=conn.host, user=conn.login, password=conn.password) as connect:
                ldap_df = pd.read_sql(query_td, connect)
            print(len(ldap_df))  # Log the number of records fetched
            
            # Merge LDAP data with the original data
            getwork = getwork.merge(ldap_df, left_on='agent_id', right_on='person_login1', how='left')

            # Format and clean the data
            getwork['assign_date'] = pd.to_datetime(getwork['assign_date'], errors='coerce', format='%y-%m-%d-%H:%M:%S')
            ldap_df = getwork[['id', 'agent_id', 'request_id', 'assign_date', 'correlation_id', 'request_type', 
                               'global_latency', 'smartpath_latency', 'stm_latency', 'person_pein', 'person_full_name', 
                               'person_manager_name', 'person_manager_pein', 'person_hrchy_level4_name', 
                               'person_hrchy_level4_pein', 'person_hrchy_level4_tier', 'person_hrchy_level3_name', 
                               'person_hrchy_level3_pein', 'person_hrchy_level3_tier']]
            
            # Reformat the assign_date and update correlation_id
            ldap_df['assign_date'] = ldap_df['assign_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            ldap_df['correlation_id'] = ldap_df['correlation_id'].apply(lambda x: 'push_model' if 'push_model' in x else x)
            print(ldap_df.columns)  # Log column names
            print(len(ldap_df))  # Log the number of final records
            
            return ldap_df  # Return the processed data
    return pd.DataFrame()  # Return an empty DataFrame if input is empty

# Task to load data into Elasticsearch
@task.virtualenv(requirements=['elasticsearch'])
def data_load_to_Elastic(dataframe, account_index_name):
    # Import necessary libraries and modules
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.elastic_utils import EsManagement
    sys.path.append('/usr/local/airflow/dags/stm/')

    # Early exit if the input DataFrame is empty
    if dataframe.empty:
        return

    # Suppress warnings for unverified HTTPS requests
    import warnings
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    # Define the Elasticsearch data schema
    data_map = {"mappings": {
                "properties": {
                'id': {"type":"integer"},
                "agent_id": {"type":"keyword"},
                'request_id':{"type":"keyword"},
                'assign_date':{"type":"date","format":"yyyy-MM-dd HH:mm:ss"},
                'hour_minute':{"type":"keyword"},
                'correlation_id':{"type":"keyword"},
                'request_type':{"type":"keyword"},
                'global_latency':{"type":"double"},
                'smartpath_latency':{"type":"double"},
                "stm_latency": {"type":"double"},
                "person_pein": {"type":"keyword"},
                "person_full_name": {"type":"keyword"},
                "person_manager_name": {"type":"keyword"},
                "person_manager_pein": {"type":"keyword"},
                "person_hrchy_level4_name": {"type":"keyword"},
                "person_hrchy_level4_pein": {"type":"keyword"},
                "person_hrchy_level4_tier": {"type":"keyword"},
                "person_hrchy_level3_name": {"type":"keyword"},
                "person_hrchy_level3_pein": {"type":"keyword"},
                "person_hrchy_level3_tier": {"type":"keyword"}

            }
        }
    }
    
    # Convert the DataFrame to a dictionary of records
    array = dataframe.to_dict('records')
    
    # Initialize environment variables and Elasticsearch management utility
    env_var = AiflowEnvVariable()
    es_connection = EsManagement(env_var)
    
    # Insert the data into the Elasticsearch index
    es_connection.insert_documents(account_index_name, array, 'id')

# Run the DAG's main task
data = main_task()