# Add the project directory to the Airflow Docker container path for module imports
import sys
sys.path.append('/usr/local/airflow/dags/stm/')

# Import necessary modules for DAG and task creation
from datetime import datetime, timedelta
from airflow.decorators import dag, task

# Default arguments to configure the DAG
default_args ={
    "owner":"eq02977",
    "description":"SAiRA Push Model metrics - Idle Time",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024,10,31),
    "retries":0,
    "email_on_failure": True,
    "retry_delays":timedelta(minutes=2)}

@dag (
    dag_id= "idle_time_metric",
    description = "idle_time_metric",
    default_args = default_args,
    catchup = False,
    schedule_interval= '0 0 * * *',    
    tags=["saira","stm","push_model"]
)

def main_task():
    idle_time = extract_data_idle_time()
    data = extract_cp_data(idle_time) 
    data_load_to_Elastic(data, account_index_name='bbm_aiml_saira_idle_time-prod')

# Task to extract idle time data from the database
@task()
def extract_data_idle_time():
    # Import required modules and utility functions
    from airflow.models.connection import Connection
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import teradatasql
    import pandas as pd

    # Initialize environment variables and database utility
    env_var = AiflowEnvVariable()
    db = DB(env_var)

    # Define connection IDs for databases
    connection_id = "bbm_stm"
    connection_id_td = "teradata_stm"

    # Query to get STM agent data
    query_sql = db.get_stm_agents()
    if query_sql != '':
        print(query_sql)
        # Fetch data from MSSQL
        mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
        getwork_df = mssql_hook.get_pandas_df(query_sql)
        print(len(getwork_df))

    # Extract agent IDs for further processing
    agent_ids = getwork_df['agent_id'].unique().tolist()
    agent_ids_str = ', '.join(f"'{agent_id}'" for agent_id in agent_ids)
    agent_ids_str = f"({agent_ids_str})"

    # Query to get idle time data from Teradata
    query_td = db.get_idle_time(agent_ids_str)
    if query_td != '':
        print(query_td)
        # Establish connection to Teradata
        conn = Connection.get_connection_from_secrets(connection_id_td)
        with teradatasql.connect(host=conn.host, user=conn.login, password=conn.password) as connect:
            ldap_df = pd.read_sql(query_td, connect)
        print(len(ldap_df))

        # Return an empty DataFrame if no data is found
        if ldap_df.empty:
            return pd.DataFrame()

        # Process the idle time data
        ldap_df.loc[ldap_df['smtpth_disp_event_newStat'] == 'available', 'total_work_time'] = 0
        daily_totals = ldap_df.groupby(['smtpth_disp_date', 'smtpth_disp_relParty_id', 'smtpth_disp_relParty_name'])[['total_available_time', 'total_work_time']].sum().reset_index()

        # Format and structure the output
        daily_totals['id'] = daily_totals['smtpth_disp_date'].astype(str) + '_' + daily_totals['smtpth_disp_relParty_id']
        daily_totals['smtpth_disp_date'] = (pd.to_datetime(daily_totals['smtpth_disp_date'].astype(str) + ' 05:00:00', format='%Y-%m-%d %H:%M:%S').dt.strftime('%Y-%m-%d %H:%M:%S'))
        daily_totals = daily_totals[['id', 'smtpth_disp_date', 'smtpth_disp_relParty_id', 'smtpth_disp_relParty_name', 'total_available_time', 'total_work_time']]

        return daily_totals

    # Return an empty DataFrame if no query is available
    return pd.DataFrame()

# Task to process additional CP data
@task()
def extract_cp_data(df):
    from airflow.models.connection import Connection
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import teradatasql
    import pandas as pd

    # Initialize environment variables and database utility
    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id_td = "teradata_stm"

    # Return an empty DataFrame if input data is empty
    if df.empty:
        return pd.DataFrame()

    # Extract unique agent IDs from the input data
    agent_ids = df['smtpth_disp_relParty_id'].unique().tolist()
    agent_ids_str = ', '.join(f"'{agent_id}'" for agent_id in agent_ids)
    agent_ids_str = f"({agent_ids_str})"

    # Query to fetch CP data for the agents
    query_cp = db.get_cp_data(agent_ids_str)
    if query_cp != '':
        print(query_cp)
        # Establish connection to Teradata and fetch the CP data
        conn = Connection.get_connection_from_secrets(connection_id_td)
        with teradatasql.connect(host=conn.host, user=conn.login, password=conn.password) as connect:
            cp_df = pd.read_sql(query_cp, connect)
        print(len(cp_df))

    # Merge the input data with CP data
    df = df.merge(cp_df, left_on='smtpth_disp_relParty_id', right_on='person_login1', how='left')
    df = df.drop('person_login1', axis=1)
    return df

# Task to load data into Elasticsearch
@task.virtualenv(requirements=['elasticsearch'])
def data_load_to_Elastic(dataframe, account_index_name):
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.elastic_utils import EsManagement
    sys.path.append('/usr/local/airflow/dags/stm/')

    # Return if the DataFrame is empty
    if dataframe.empty:
        return

    # Suppress HTTPS request warnings
    import warnings
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    # Define Elasticsearch index mapping
    data_map = {"mappings": {
                "properties": {
                'id': {"type":"keyword"},
                'smtpth_disp_date':{"type":"date","format":"yyyy-MM-dd HH:mm:ss"},
                "smtpth_disp_relParty_id": {"type":"keyword"},
                "smtpth_disp_relParty_name": {"type":"keyword"},
                "total_available_time": {"type":"integer"},
                "total_work_time": {"type":"integer"},
                "person_manager_name": {"type": "keyword"},
                "person_hrchy_level4_name": {"type": "keyword"},
                "person_hrchy_level4_tier": {"type": "keyword"},
                "person_hrchy_level3_name": {"type": "keyword"},
                "person_hrchy_level3_tier": {"type": "keyword"}
            }
        }
    }

    # Convert DataFrame to dictionary for Elasticsearch
    array = dataframe.to_dict('records')

    # Load data into Elasticsearch
    env_var = AiflowEnvVariable()
    es_connection = EsManagement(env_var)
    es_connection.insert_documents(account_index_name, array, 'id')

# Execute the main task
data = main_task()