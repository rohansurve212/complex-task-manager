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
    "owner": "eq02977",
    "description": "Notify user if a docker container is down",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024, 6, 1),
    "retries": 0,
    "email_on_failure": True,
    "retry_delay": timedelta(minutes=2)
}

# Define the DAG
@dag(
    dag_id="email_docker_container_down",
    description="Notify user if a docker container is down",
    default_args=default_args,
    catchup=False,
    schedule_interval='*/2 * * * *', # runs every 2 minutes
    tags=["saira", "stm", "email_alert"]
)
def main_dag():
    
    # Task to read log files and check for errors
    @task()
    def read_log_file():
        cont_down = [False, False, False]
        log_file_paths = [
            '/usr/local/airflow/files/stm_assets/imt/rmq_agent/log/agent_skills.log',
            '/usr/local/airflow/files/stm_assets/imt/rmq_disp/log/disposition_codes.log',
            '/usr/local/airflow/files/stm_assets/imt/rmq_skills/log/skillset_configuration.log'
        ]
        container_names = [
            'imt-rmq-agent',
            'imt-rmq-disp',
            'imt-rmq-skills'
        ]
        down_containers = []
        
        for i, log_file_path in enumerate(log_file_paths):
            try:
                with open(log_file_path, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-1:]:
                        if "Retrying attempt" in line or "Error" in line or "error" in line:
                            cont_down[i] = True
                            down_containers.append(container_names[i])
            except FileNotFoundError:
                print(f"Log file not found: {log_file_path}")

        return {"cont_down": cont_down, "down_containers": down_containers}

    # Task to send email if any container is down
    @task()
    def send_email(log_info):
        cont_down = log_info["cont_down"]
        down_containers = log_info["down_containers"]
        
        sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
        from utils.envs.airflow_env_variable import AiflowEnvVariable
        from utils.email_recipients import Email

        env_var = AiflowEnvVariable()
        email = Email(env_var)
        email_rec = email.get_email_recipients()
        
        if any(cont_down):
            email_file = MIMEMultipart()
            
            down_containers_str = '<br>'.join(down_containers)
            msg_text_html = f'''
                ===============================  Warning =============================== <br>
                Hello, <br> Note that an email alert was triggered for the STM Application.<br><br>
                <h4>The following docker container(s) are down, please check the corresponding log files:</h4>
                <p>{down_containers_str}</p>
                <br><br>
                <i>This is an auto-generated email</i>
            '''
            msg_text = MIMEText(msg_text_html, 'html')
            email_file.attach(msg_text)
            email_file['From'] = "stm.alerts@bell.ca"
            to_list = email_rec
            email_file['To'] = ', '.join(to_list)
            email_file['Subject'] = "Docker Container Down -- EMAIL Alert"

            send_mime_email(email_file["From"], to_list, email_file)    
        else:
            print("No anomaly found")

    # Execute tasks
    log_info = read_log_file()
    send_email(log_info)

# Instantiate the DAG
data = main_dag()