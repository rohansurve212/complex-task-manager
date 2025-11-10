import sys
sys.path.append('/usr/local/airflow/dags/stm/')

from datetime import datetime, timedelta
from airflow.decorators import dag, task

default_args ={
    "owner":"eq02977",
    "description":"SAiRA Push Model metrics - Idle Agents Count",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024,11,25),
    "retries":0,
    "email_on_failure": True,
    "retries":0,
    "retry_delays":timedelta(minutes=2)}

@dag (
    dag_id= "idle_agents_count",
    description = "idle_agents_count",
    default_args = default_args,
    catchup = False,
    schedule_interval= '*/3 12-22 * * 1-5',    
    tags=["saira","stm","control_plan"]
)

def main_task():
    idle_agents = extract_idle_agents()
    data_load_to_Elastic(idle_agents,account_index_name = 'bbm_aiml_saira_idle_agents-prod')

@task()
def extract_idle_agents():
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import pandas as pd
    from datetime import datetime

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"
    query = db.get_idle_push_agents()
    if query != '':
        print(query)
        mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
        agents = mssql_hook.get_pandas_df(query)
        print(len(agents))
        idle_count = pd.DataFrame()
        idle_count['timestamp'] = datetime.now()
        idle_count['timestamp'] = idle_count['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        idle_count['idle_agents'] = len(agents)

        return idle_count
    return pd.DataFrame()

@task.virtualenv(requirements=['elasticsearch'])
def data_load_to_Elastic(idle_agents,account_index_name):
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.elastic_utils import EsManagement
    sys.path.append('/usr/local/airflow/dags/stm/')

    if idle_agents.empty:
        print('no data to load')
        return

    import warnings
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    data_map = {"mappings": {
                "properties": {
                'timestamp': {"type":"date","format":"yyyy-MM-dd HH:mm:ss"},
                'idle_agents':{"type":"integer"}
                                        
            }
        }
    }
    
    array = idle_agents.to_dict('records')
    env_var = AiflowEnvVariable()
    es_connection = EsManagement(env_var)
    es_connection.insert_documents(account_index_name, array, 'timestamp')

data = main_task()