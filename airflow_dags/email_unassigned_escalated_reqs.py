# Import necessary modules and add project directory to the airflow docker container path
import sys
sys.path.append('/usr/local/airflow/dags/stm/')

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from airflow.utils.email import send_mime_email

# Default arguments for the DAG
default_args = {
    "owner": "eq73914",
    "description": "Notify user if an escalated request has been unassigned for at least 24 hours",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2025,7,1),
    "retries":0,
    "email_on_failure": True,
    "retry_delay":timedelta(minutes=2)}

# Define the DAG
@dag (
    dag_id= "email_unassigned_escalation_req",
    description = "Notify user if an escalated request has been unassigned for at least 24 hours",
    default_args = default_args,
    catchup = False,
    schedule_interval= '0 11-23 * * 1-5',  # 7 am to 7 pm EST,  every hour, Mon to Fri
    tags=["saira","stm","email_alert"]
)

def main_task():
    unassigned_reqs = query_escalations_unassigned()
    send_email(unassigned_reqs)

# Task to extract unassinged escalated requests
@task()
def query_escalations_unassigned():
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import pandas as pd

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"
    query = db.get_unassigned_escalated_requests()

    if query != '':
        print(query)
        mssql_hook = MsSqlHook(mssql_conn_id=connection_id)
        requests = mssql_hook.get_pandas_df(query)
        print(len(requests))
        return requests
    
    return pd.DataFrame()

# Task to send email with idle agents information
@task()
def send_email(requests):
    print(requests)
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.email_recipients import Email

    env_var = AiflowEnvVariable()
    email = Email(env_var)
    email_rec = email.get_email_recipients_for_unassigned_escalations()
    
    if not requests.empty:
        email_file = MIMEMultipart()
        
        msg_text_html = '''
            ===============================  Warning =============================== <br>
         Hello, <br> Note that an email alert was triggered for the STM Application.<br><br>
        <h4>The following requests have been escalated at least 24 hours ago, and have not yet been assigned to an agent.</h4>
        <br>
        <h4>Details:</h4>
        <table border="1" style="margin-left: auto; margin-right: auto; display: inline-table; text-align: center;">
            <tr>
                <th style="padding: 2px; margin: 0; line-height: 1; text-align: center;">Request ID</th>
                <th style="padding: 2px; margin: 0; line-height: 1; text-align: center;">Reason for Escalation</th>
                <th style="padding: 2px; margin: 0; line-height: 1; text-align: center;">Submission Date (Eastern Time)</th>
            </tr>
        '''

        for _, row in requests.iterrows():
            msg_text_html += f'''
            <tr>
                <td style="padding: 2px; margin: 0; line-height: 1; text-align: center;">{row['request_id']}</td>
                <td style="padding: 2px; margin: 0; line-height: 1; text-align: center;">{row['request_reason']}</td>
                <td style="padding: 2px; margin: 0; line-height: 1; text-align: center;">{row['eastern_submission_dt']}</td>
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
        email_file['Subject'] = "STM Escalated Request(s) Not Assigned -- EMAIL Alert"

        send_mime_email(email_file["From"], to_list, email_file)

    else:
        print("No anomaly found.")

# Instantiate the DAG
data = main_task()