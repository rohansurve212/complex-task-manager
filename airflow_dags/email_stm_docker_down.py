# Import necessary modules and add project directory to the airflow docker container path
import sys
sys.path.append('/usr/local/airflow/dags/stm/')

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from airflow.utils.email import send_mime_email
from datetime import datetime

# Default arguments for the DAG
default_args ={
    "owner":"eq02977",
    "description":"Notify user if STM-API Docker Container is down",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024,7,1),
    "retries":0,
    "email_on_failure": True,
    "retry_delays":timedelta(minutes=2)}

# Define the DAG
@dag (
    dag_id= "email_stm_docker_down",
    description = "Notify user if STM-API Docker Container is down",
    default_args = default_args,
    catchup = False,
    schedule_interval= '* * * * *', # runs at every minute
    tags=["saira","stm","email_alert"]
)

def main_task():
    cont_down = read_log_file()
    send_email(cont_down)

# Task to read the log file and check if the container is down
@task()
def read_log_file():
    cont_down = False
    log_file_path = '/usr/local/airflow/files/stm_assets/api/log/api.log'
    
    try:
        with open(log_file_path, 'r') as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1]
                timestamp_str = last_line.split(' - ')[0]
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                current_time = datetime.now()
                if current_time - timestamp > timedelta(seconds=10):
                    cont_down = True
            else:
                cont_down = True # If log file is empty
    except FileNotFoundError:
        print(f"Log file not found: {log_file_path}")

    return cont_down

# Task to send email if the container is down
@task()
def send_email(cont_down):
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.email_recipients import Email

    env_var = AiflowEnvVariable()
    email = Email(env_var)
    email_rec = email.get_email_recipients()
    if cont_down:
        email_file = MIMEMultipart()
        
        msg_text_html = '''
            ===============================  Warning =============================== <br>
         Hello, <br> Note that an email alert was triggered for the STM Application.<br><br>
        <h4>STM-API Docker Container seems to be down. Please check the container logs.</h4>
        <br><br>
        <i>This is an auto-generated email</i>
        '''
        msg_text = MIMEText(msg_text_html, 'html')
        email_file.attach(msg_text)
        email_file['From'] = "stm.alerts@bell.ca"
        to_list = email_rec
        email_file['To'] = ', '.join(to_list)
        email_file['Subject'] = "STM-API Docker Container Down -- EMAIL Alert"

        send_mime_email(email_file["From"], to_list, email_file)    
    else:
        print("No anomaly found")

# Instantiate the DAG
data = main_task()