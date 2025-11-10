import sys
sys.path.append('/usr/local/airflow/dags/stm/')

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from airflow.utils.email import send_mime_email

default_args ={
    "owner":"eq02977",
    "description":"Summary of when the agents ran out of P1 requests for the first time during the day.",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024,11,25),
    "retries":0,
    "email_on_failure": True,
    "retries":0,
    "retry_delays":timedelta(minutes=2)}

@dag (
    dag_id= "email_p1_completion_time",
    description = "email_p1_completion_time",
    default_args = default_args,
    catchup = False,
    schedule_interval= '0 10 * * *',    
    tags=["saira","stm","control_plan"]
)

def main_task():
    getwork_df = extract_data_sqlserver()
    final_df = extract_ldap(getwork_df)
    send_email(final_df)

@task()
def extract_data_sqlserver():
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    import pandas as pd
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"
    query = db.get_sql_query_p1_p2()
    if query == '':
        return pd.DataFrame()
    print(query)
    mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
    getwork_df = mssql_hook.get_pandas_df(query)
    print(len(getwork_df))
    getwork_df['assign_date'] = pd.to_datetime(getwork_df['assign_date'],utc=True)
    getwork_df['assign_date_est'] = getwork_df['assign_date'].dt.tz_convert('US/Eastern')
    getwork_df['assign_date_est'] = getwork_df['assign_date_est'].dt.strftime('%Y-%m-%d %H:%M:%S')
    query_priority = db.get_skill_agent_priority()
    if query_priority == '':
        return pd.DataFrame()
    print(query_priority)
    skill_priority = mssql_hook.get_pandas_df(query_priority)
    print(len(skill_priority))
    getwork_df = getwork_df.merge(skill_priority, left_on=['agent_id','skill_id'], right_on=['agent_id','skill_id'], how='left')
    getwork_df = getwork_df.dropna(axis=0, subset=['skill_priority'])
    filtered_df = getwork_df.loc[getwork_df['skill_priority'] != 1]
    result = filtered_df.sort_values('assign_date').groupby('agent_id').first().reset_index()

    return result

@task()
def extract_ldap(df):
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
    
    if df.empty:
        return pd.DataFrame()
    agent_ids = df['agent_id'].tolist()
    agent_ids_str = ', '.join(f"'{agent_id}'" for agent_id in agent_ids)
    agent_ids_str = f"({agent_ids_str})"
    query_td = db.get_ldap_data(agent_ids_str)
    if query_td == '':
        return pd.DataFrame()
    conn = Connection.get_connection_from_secrets(connection_id_td)
    with teradatasql.connect(host=conn.host,user=conn.login, password=conn.password) as connect:
        ldap_df = pd.read_sql(query_td, connect)
        print(len(ldap_df))
    df = df.merge(ldap_df, how = 'left', left_on='agent_id', right_on='person_login1')
    df = df[['agent_id','person_full_name','external_id','assign_date_est','skill_id','skill_name','skill_priority','person_manager_name', 'person_hrchy_level4_name', 'person_hrchy_level3_name']]
    print(df)        
    return df

@task()
def send_email(df):
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.email_recipients import Email

    env_var = AiflowEnvVariable()
    email = Email(env_var)
    email_rec = email.get_email_recipients_for_idle_time()
    if not df.empty:
        email_file = MIMEMultipart()
        
        msg_text_html = '''
            ===============================  Warning =============================== <br>
         Hello, <br> This is a summary of when agents started working on P2 requests for the first time during the day.<br><br>
        <h4>The summary is about yesterday. </h4>
        <br>
        <h4>Details:</h4>
        <table border="1">
            <tr>
                <th>Agent ID</th>
                <th>Agent Name</th>
                <th>Request ID</th>
                <th>Assign Date</th>
                <th>Skill ID</th>
                <th>Skill Name</th>
                <th>Skill Priority</th>
                <th>Manager Name</th>
                <th>CP2 Name</th>
                <th>CP3 Name</th>
            </tr>
        '''

        for index, row in df.iterrows():
            msg_text_html += f'''
            <tr>
                <td>{row['agent_id']}</td>
                <td>{row['person_full_name']}</td>
                <td>{row['external_id']}</td>
                <td>{row['assign_date_est']}</td>
                <td>{row['skill_id']}</td>
                <td>{row['skill_name']}</td>
                <td>{row['skill_priority']}</td>
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
        email_file['Subject'] = "Summary of Agents' first P2 requests"

        send_mime_email(email_file["From"], to_list, email_file)    
    else:
        print("No anomaly found")

data = main_task()