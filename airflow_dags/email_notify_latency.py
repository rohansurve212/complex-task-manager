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
    "description":"Notify user if latency is over 50s",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024,2,17),
    "retries":0,
    "email_on_failure": True,
    "retry_delays":timedelta(minutes=2)}

# Define the DAG
@dag (
    dag_id= "email_notify_latency",
    description = "Notify user if latency is over 50s",
    default_args = default_args,
    catchup = False,
    schedule_interval= '*/10 * * * *', # runs every 10 minutes
    tags=["saira","stm","latency","email_alert"]
) 
def main_task():
    getwork_df = extract_data_sqlserver()
    latency_df = filter_data(getwork_df)
    send_email(latency_df)

# Task to extract data from SQL Server for the past 10 minutes
@task()
def extract_data_sqlserver():
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"
    query = db.get_sql_query_alerts()
    print(query)
    mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
    getwork_df = mssql_hook.get_pandas_df(query)
    print(len(getwork_df))

    return getwork_df

# Task to filter data for latency over 50 seconds
@task()
def filter_data(getwork):
    import pandas as pd
    latency_data = getwork[['agent_id', 'request_id', 'external_id', 'assign_date', 'global_latency']]
    latency_data = getwork.loc[getwork['global_latency'] >= 50]

    if len(latency_data) > 0:
        print(latency_data)
    
    return latency_data

# Task to send email if latency is over 50 seconds
@task()
def send_email(latency):
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.email_recipients import Email

    env_var = AiflowEnvVariable()
    email = Email(env_var)
    email_rec = email.get_email_recipients()
    if not latency.empty:
        email_file = MIMEMultipart()
        
        msg_text_html = '''
            ===============================  Warning =============================== <br>
         Hello, <br> Note that an email alert was triggered for the STM Application.<br><br>
        <h4>The global latency of some request(s) was over 50 seconds </h4>
        <br>
        <h4>Details:</h4>
        <table border="1">
            <tr>
                <th>Agent ID</th>
                <th>Request ID</th>
                <th>External ID</th>
                <th>Assign Date</th>
                <th>Global Latency</th>
            </tr>
        '''

        for index, row in latency.iterrows():
            msg_text_html += f'''
            <tr>
                <td>{row['agent_id']}</td>
                <td>{row['request_id']}</td>
                <td>{row['external_id']}</td>
                <td>{row['assign_date']}</td>
                <td>{row['global_latency']}</td>
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
        email_file['Subject'] = "STM Global Latency Over 50 seconds -- EMAIL Alert"

        send_mime_email(email_file["From"], to_list, email_file)    
    else:
        print("No anomaly found")

# Instantiate the DAG
data = main_task()
