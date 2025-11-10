# Import necessary modules and add project directory to the airflow docker container path
import sys
sys.path.append('/usr/local/airflow/dags/stm/')

from datetime import datetime, timedelta
from airflow.decorators import dag, task

# Default arguments for the DAG
default_args ={
    "owner":"eq02977",
    "description":"SAiRA Performance metric - FOC success rate",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024,2,17),
    "retries":0,
    "email_on_failure": True,
    "retry_delays":timedelta(minutes=2)}

# Define the DAG
@dag (
    dag_id= "saira_foc_metric",
    description = "saira_foc_metric",
    default_args = default_args,
    catchup = False,
    schedule_interval= '0 0 * * MON',   # runs at midnight (UTC) every Monday
    tags=["saira","stm","control_plan"]
) 
def main_task():
    getwork_df = extract_data_sqlserver()
    df_teradata = extract_data_teradata(getwork_df)
    load_to_Elastic(getwork_df, df_teradata, account_index_name='bbm_aiml_saira_foc_metric-prod')

# Task to extract getwork data from SQL Server
@task()
def extract_data_sqlserver():
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import numpy as np
    import pandas as pd

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"
    query = db.get_sql_query_foc()
    if query != '':
        print(query)
        mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
        getwork_df = mssql_hook.get_pandas_df(query)
        print(len(getwork_df))
        # Filter out rows where 'work_status' is 'NO_WORK' or 'NO_ASSIGNMENT'
        getwork_df = getwork_df[~getwork_df['work_status'].isin(['NO_WORK','NO_ASSIGNMENT'])]

        # Sort the DataFrame by 'request_id' and 'assign_date'
        getwork_df = getwork_df.sort_values(by=['request_id','assign_date'])

        # Drop duplicates, keeping the first occurrence of each 'request_id'
        first_assigned = getwork_df.drop_duplicates(subset=['request_id'], keep='first')

        # Select specific columns and create a copy of the DataFrame
        first_assigned = first_assigned[['id','request_id', 'orderdate', 'ttpu', 'assign_date', 'request_type']].copy()

        # Calculate the actual time to process (TTPU) in days
        first_assigned['actual_ttpu'] = (first_assigned['assign_date'] - getwork_df['orderdate']).dt.days

        # Determine if the FOC (First Order Complete) target was met
        first_assigned['foc_met'] = np.where(first_assigned['actual_ttpu'] <= first_assigned['ttpu'], 1, 0)

        # Format 'assign_date' and 'orderdate' columns as strings
        first_assigned['assign_date'] = first_assigned['assign_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        first_assigned['orderdate'] = first_assigned['orderdate'].dt.strftime('%Y-%m-%d %H:%M:%S')
        print(len(first_assigned))
        return first_assigned
    
    return pd.DataFrame()

# Task to extract data from Teradata
@task()
def extract_data_teradata(getwork_df):
    from airflow.models.connection import Connection
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import teradatasql
    import pandas as pd
    import numpy as np

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id_td = "teradata_stm"
    query_td = db.get_teradata_query_foc()
    if query_td != '':
        print(query_td)
        conn = Connection.get_connection_from_secrets(connection_id_td)
        with teradatasql.connect(host=conn.host,user=conn.login, password=conn.password) as connect:
            df_teradata = pd.read_sql(query_td, connect)
        print(len(df_teradata))
        # Filter out rows where 'smtpth_req_id' is in 'getwork_df' 'request_id'
        df_teradata = df_teradata[~df_teradata['smtpth_req_id'].isin(getwork_df['request_id'])]

        # Convert 'smtpth_req_action' to lowercase
        df_teradata['smtpth_req_action'] = df_teradata['smtpth_req_action'].str.lower()

        # Set default TTPU value to 7.0
        df_teradata['ttpu'] = 7.0

        # Update TTPU value to 6.0 for specific actions
        df_teradata.loc[df_teradata['smtpth_req_action'].isin(['add','change','move','new']), 'ttpu'] = 6.0

        # Calculate the actual TTPU in days
        df_teradata['actual_ttpu'] = (df_teradata['smtpth_req_start_dt'] - df_teradata['smtpth_req_create_dt']).dt.days

        # Convert 'actual_ttpu' to float64
        df_teradata['actual_ttpu'] = df_teradata['actual_ttpu'].astype('float64')

        # Determine if the FOC target was met
        df_teradata['foc_met'] = np.where(df_teradata['ttpu'] >= df_teradata['actual_ttpu'], 1, 0)

        # Add a new column 'id' with default value 0
        df_teradata['id'] = 0

        # Rename columns to match the required format
        df_teradata = df_teradata.rename(columns={'smtpth_req_id': 'request_id', 'smtpth_req_create_dt': 'orderdate', 'smtpth_req_start_dt': 'assign_date', 'smtpth_req_action': 'request_type'})

        # Format 'assign_date' and 'orderdate' columns as strings
        df_teradata['assign_date'] = df_teradata['assign_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_teradata['orderdate'] = df_teradata['orderdate'].dt.strftime('%Y-%m-%d %H:%M:%S')

        # Sort the DataFrame by 'assign_date'
        df_teradata = df_teradata.sort_values(by=['assign_date'])
        return df_teradata
        
    return pd.DataFrame()

# Task to load data to Elasticsearch
@task.virtualenv(requirements=['elasticsearch'])
def load_to_Elastic(getwork_df, teradata_df, account_index_name):
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.elastic_utils import EsManagement
    sys.path.append('/usr/local/airflow/dags/stm/')

    if (getwork_df.empty) and (teradata_df.empty):
        print('No data to load to Elastic')
        return

    import warnings
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    data_map = {"mappings": {
                "properties": {
                'id': {"type":"integer"},
                'request_id':{"type":"keyword"},
                'orderdate':{"type":"date","format":"yyyy-MM-dd HH:mm:ss"},
                'assign_date':{"type":"date","format":"yyyy-MM-dd HH:mm:ss"},
                'request_type':{"type":"keyword"},
                'ttpu':{"type":"integer"},
                'actual_ttpu':{"type":"integer"},
                'foc_met':{"type":"integer"}
                }       
                                        
            }
        }
    
    array = getwork_df.to_dict('records')
    env_var = AiflowEnvVariable()
    es_connection = EsManagement(env_var)
    es_connection.insert_documents(account_index_name, array, 'id')
    array1 = teradata_df.to_dict('records')
    es_connection.insert_documents(account_index_name, array1, 'request_id')

# Instantiate the DAG
data = main_task()
