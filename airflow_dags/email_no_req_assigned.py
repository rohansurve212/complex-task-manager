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
    "description":"Notify user if no request has been assigned for past 2 hours",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024,4,1),
    "retries":0,
    "email_on_failure": True,
    "retry_delays":timedelta(minutes=2)}

# Define the DAG
@dag (
    dag_id= "email_no_req_assigned",
    description = "Notify user if no request has been assigned for past 2 hours",
    default_args = default_args,
    catchup = False,
    schedule_interval= '0 13-23/2 * * 1-5', # runs every 2 hours from mon to fri 8 am to 6 pm
    tags=["saira","stm","email_alert"]
) 
def main_task():
    getwork_df = extract_data_sqlserver()
    send_email(getwork_df)

# Task to extract data from SQL Server for requests assigned in the last 2 hours
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
    query = db.get_sql_query_no_req_assigned()
    print(query)
    mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
    getwork_df = mssql_hook.get_pandas_df(query)
    print(len(getwork_df))

    return getwork_df

# Task to send email if no request has been assigned for the past 2 hours
@task()
def send_email(getwork):
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.email_recipients import Email

    env_var = AiflowEnvVariable()
    email = Email(env_var)
    email_rec = email.get_email_recipients()
    if getwork.empty:
        email_file = MIMEMultipart()
        
        msg_text_html = '''
            ===============================  Warning =============================== <br>
         Hello, <br> Note that an email alert was triggered for the STM Application.<br><br>
        <h4>There have been no requests assigned to any agents in the last 2 hours. Please check if there is an issue.</h4>
        <br><br>
        <i>This is an auto-generated email</i>
        '''
        msg_text = MIMEText(msg_text_html, 'html')
        email_file.attach(msg_text)
        email_file['From'] = "stm.alerts@bell.ca"
        to_list = email_rec
        email_file['To'] = ', '.join(to_list)
        email_file['Subject'] = "No request assignments in the past 2 hours -- EMAIL Alert"

        send_mime_email(email_file["From"], to_list, email_file)    
    else:
        print("No anomaly found")

# Instantiate the DAG
data = main_task()
