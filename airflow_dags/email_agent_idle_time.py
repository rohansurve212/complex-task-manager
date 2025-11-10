# Import necessary modules and add project directory to the airflow docker container path
import sys
sys.path.append('/usr/local/airflow/dags/stm/')

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from airflow.utils.email import send_mime_email

# Default arguments for the DAG
default_args ={
    "owner":"eq02977",
    "description":"Notify user if push model agent idle for more than 6 minutes",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024,10,15),
    "retries":0,
    "email_on_failure": True,
    "retry_delays":timedelta(minutes=2)}

# Define the DAG
@dag (
    dag_id= "email_agent_idle_time",
    description = "email_agent_idle_time",
    default_args = default_args,
    catchup = False,
    schedule_interval= '*/3 12-23 * * 1-5',  # runs every 3 minutes from mon to fri 7 am to 7 pm
    tags=["saira","stm","control_plan"]
)

def main_task():
    agents_df = extract_agents()
    idle_agents = extract_ldap(agents_df)
    send_email(idle_agents)
    idle_agents_each_run = available_agents_each_run()
    send_email_idle_agents(idle_agents_each_run)

# Task to extract agents idle for more than 6 minutes
@task()
def extract_agents():
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import pandas as pd

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"
    query = db.get_agents_push_model_6_minutes()

    if query != '':
        print(query)
        mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
        agents = mssql_hook.get_pandas_df(query)
        print(len(agents))
        return agents
    
    return pd.DataFrame()

# Task to extract LDAP data
@task()
def extract_ldap(agents):
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
    
    if not agents.empty:
        agent_ids = agents['agent_id'].tolist()
        agent_ids_str = ', '.join(f"'{agent_id}'" for agent_id in agent_ids)
        agent_ids_str = f"({agent_ids_str})"
        query_td = db.get_ldap_data(agent_ids_str)

        if query_td != '':
            conn = Connection.get_connection_from_secrets(connection_id_td)
            with teradatasql.connect(host=conn.host,user=conn.login, password=conn.password) as connect:
                ldap_df = pd.read_sql(query_td, connect)
            print(len(ldap_df))
            if not ldap_df.empty:
                return ldap_df
            return pd.DataFrame()
        return pd.DataFrame()
    return pd.DataFrame


# Task to send email with idle agents information
@task()
def send_email(idle_agents):
    print(idle_agents)
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.email_recipients import Email

    env_var = AiflowEnvVariable()
    email = Email(env_var)
    email_rec = email.get_email_recipients_for_idle_time()
    if not idle_agents.empty:
        email_file = MIMEMultipart()
        
        msg_text_html = '''
            ===============================  Warning =============================== <br>
         Hello, <br> Note that an email alert was triggered for the STM Application Push Model.<br><br>
        <h4>The following agents have been idle for more than 6 minutes (2 push model runs) </h4>
        <br>
        <h4>Details:</h4>
        <table border="1">
            <tr>
                <th>Agent ID</th>
                <th>Agent Name</th>
                <th>Manager Name</th>
                <th>CP2 Name</th>
                <th>CP3 Name</th>
            </tr>
        '''

        for index, row in idle_agents.iterrows():
            msg_text_html += f'''
            <tr>
                <td>{row['person_login1']}</td>
                <td>{row['person_full_name']}</td>
                <td>{row['person_manager_name']}</td>
                <td>{row['person_hrchy_level4_name']}</td>
                <td>{row['person_hrchy_level3_name']}</td>
            </tr>
            '''

        msg_text_html += '''
            </table>
            <br>
            <i>This is an auto-generated email</i>
        '''
        msg_text = MIMEText(msg_text_html, 'html')
        email_file.attach(msg_text)
        email_file['From'] = "stm.alerts@bell.ca"
        to_list = email_rec
        email_file['To'] = ', '.join(to_list)
        email_file['Subject'] = "STM Agents Idle for more than 6 minutes -- EMAIL Alert"

        send_mime_email(email_file["From"], to_list, email_file)    
    else:
        print("No anomaly found")

# Task to get the number of available agents in each run
@task()
def available_agents_each_run():
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import pandas as pd

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"
    query = db.get_idle_push_agents()

    if query != '':
        print(query)
        mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
        agents = mssql_hook.get_pandas_df(query)
        print(len(agents))
        return len(agents)
    
    return 0

# Task to send email if there are more than 5 idle agents in the current run
@task()
def send_email_idle_agents(idle_agents_each_run):
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.email_recipients import Email

    env_var = AiflowEnvVariable()
    email = Email(env_var)
    email_rec = email.get_email_recipients()
    if idle_agents_each_run > 5:
        email_file = MIMEMultipart()
    
        msg_text_html = '''
            ===============================  Warning =============================== <br>
        Hello, <br> Note that an email alert was triggered for the STM Application Push Model.<br><br>
        <h4>There were more than 5 idle agents in the current push model run. </h4>
        <br>
        <i>This is an auto-generated email</i>
        '''
        msg_text = MIMEText(msg_text_html, 'html')
        email_file.attach(msg_text)
        email_file['From'] = "stm.alerts@bell.ca"
        to_list = email_rec
        email_file['To'] = ', '.join(to_list)
        email_file['Subject'] = "More than 5 idle agents in the push run -- EMAIL Alert"

        send_mime_email(email_file["From"], to_list, email_file)    
    else:
        print("No anomaly found")

# Instantiate the DAG
data = main_task()
