# Import necessary modules and add project directory to the airflow docker container path
import sys
sys.path.append('/usr/local/airflow/dags/stm/')

from datetime import datetime, timedelta
from airflow.decorators import dag, task

# Default arguments for the DAG
default_args = {
    "owner": "eq73914",
    "description": "Populating the dashboard with follow up day of week analysis data",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2025,7,1),
    "retries":0,
    "email_on_failure": True,
    "retry_delay":timedelta(minutes=2)}

# Define the DAG
@dag (
    dag_id= "follow_up_dow_dashboard",
    description = "Populating the dashboard with follow up day of week analysis data",
    default_args = default_args,
    catchup = False,
    schedule_interval= '0 9 * * 1-5',  # Runs at 5 AM EST, Mon to Fri
    tags=["saira","stm","follow_up_analysis"]
)

def main_task():
    dow_analysis_overview = query_dow_analysis_overview()
    dow_analysis_agents = query_dow_analysis_agents()
    data_load_to_Elastic(dow_analysis_overview, account_index_name='bbm_aiml_saira_follow_up_dow_overview-dev', id_column='New Follow Up Date Day of Week')
    data_load_to_Elastic(dow_analysis_agents, account_index_name='bbm_aiml_saira_follow_up_dow_agents-dev', id_column='Agent')


# Task to extract LDAP data
@task()
def query_dow_analysis_overview():
    from airflow.models.connection import Connection
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import teradatasql
    import pandas as pd

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id_td = "teradata_stm"
    query_td = db.get_dow_analysis_overview()

    if query_td != '':
            conn = Connection.get_connection_from_secrets(connection_id_td)
            with teradatasql.connect(host=conn.host,user=conn.login, password=conn.password) as connect:
                dow_analysis_overview_df = pd.read_sql(query_td, connect)
            print(len(dow_analysis_overview_df))
            if not dow_analysis_overview_df.empty:
                return dow_analysis_overview_df
            return pd.DataFrame()
    return pd.DataFrame()

# Task to extract LDAP data
@task()
def query_dow_analysis_agents():
    from airflow.models.connection import Connection
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import teradatasql
    import pandas as pd

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id_td = "teradata_stm"
    query_td = db.get_dow_analysis_agents()

    if query_td != '':
            conn = Connection.get_connection_from_secrets(connection_id_td)
            with teradatasql.connect(host=conn.host,user=conn.login, password=conn.password) as connect:
                dow_analysis_agents_df = pd.read_sql(query_td, connect)
            print(len(dow_analysis_agents_df))
            if not dow_analysis_agents_df.empty:
                return dow_analysis_agents_df
            return pd.DataFrame()
    return pd.DataFrame()


@task.virtualenv(requirements=['elasticsearch'])
def data_load_to_Elastic(dataframe, account_index_name, id_column):
    # Add the required directory to the system path for importing utilities
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    
    # Import environment variables and Elasticsearch utility class
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.elastic_utils import EsManagement

    sys.path.append('/usr/local/airflow/dags/stm/')
    
    # Early return if the DataFrame is empty
    if dataframe.empty:
        print('no data to load')
        return

    # Suppress warnings for unverified HTTPS requests
    import warnings
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    # Convert the "data" DataFrame to a dictionary format for insertion
    array = dataframe.to_dict('records')

    # Initialize environment variables and Elasticsearch management utility
    env_var = AiflowEnvVariable()
    es_connection = EsManagement(env_var)

    # Insert the data into Elasticsearch
    es_connection.insert_documents(account_index_name, array, id_column)

# Instantiate the DAG
data = main_task()