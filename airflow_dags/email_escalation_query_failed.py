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
    "description":"Notify user if the escalation table query fails",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024,6,1),
    "retries":0,
    "email_on_failure": True,
    "retry_delays":timedelta(minutes=2)}

# Define the DAG
@dag (
    dag_id= "email_escalation_query_failed",
    description = "Notify user if the escalation table query fails",
    default_args = default_args,
    catchup = False,
    schedule_interval= '*/10 * * * *', # runs every 10 minutes
    tags=["saira","stm","email_alert"]
) 

def main_task():
    error = query_escalation_table()
    send_email(error)

# Task to query the escalation table
@task()
def query_escalation_table():
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB

    try:
        env_var = AiflowEnvVariable()
        db = DB(env_var)
        connection_id = "bbm_stm"
        query = db.get_sql_query_escalation()
        print(query)
        mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
        escalation = mssql_hook.get_pandas_df(query)
        print(len(escalation))
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return str(e)

# Task to send email if the escalation table query fails
@task()
def send_email(error):
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.email_recipients import Email

    env_var = AiflowEnvVariable()
    email = Email(env_var)
    email_rec = email.get_email_recipients()
    if error:
        email_file = MIMEMultipart()
        
        msg_text_html = '''
            ===============================  Warning =============================== <br>
         Hello, <br> Note that an email alert was triggered for the STM Application.<br><br>
        <h4>The escalation table query failed because of the following error:</h4>
        <br><br>
        <h4>Error details: {} </h4>
        <br><br>
        <i>This is an auto-generated email</i>
        '''.format(error)
        msg_text = MIMEText(msg_text_html, 'html')
        email_file.attach(msg_text)
        email_file['From'] = "stm.alerts@bell.ca"
        to_list = email_rec
        email_file['To'] = ', '.join(to_list)
        email_file['Subject'] = "Escalation Table Query failed -- EMAIL Alert"

        send_mime_email(email_file["From"], to_list, email_file)    
    else:
        print("No anomaly found")

# Instantiate the DAG
data = main_task()
