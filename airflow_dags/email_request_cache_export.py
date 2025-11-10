import sys
sys.path.append('/usr/local/airflow/dags/stm/')

from datetime import datetime, timedelta
from airflow.decorators import dag, task
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from airflow.utils.email import send_mime_email
import os

# Default arguments for the DAG
default_args = {
    "owner": "eq42183",
    "description": "Export STM cache and send via email daily",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
    "email_on_failure": True,
    "retry_delay": timedelta(minutes=5)
}

# Define the DAG
@dag(
    dag_id="email_request_cache_export",
    description="Export STM request cache and send via email",
    default_args=default_args,
    catchup=False,
    schedule_interval='30 12 * * 1-5',  # Mon-Fri at 12:30 PM UTC (8:30 AM EST)
    tags=["stm", "cache", "export", "email"]
)
def main_dag():
    
    # Task to find and retrieve today's cache CSV file
    @task()
    def get_cache_file():
        """Find today's cache CSV file from the requisite folder"""
        today = datetime.now().strftime("%Y-%m-%d")  # Format: 2025-08-25
        cache_filename = f"updated_cache_{today}.csv"
        log_folder = "/usr/local/airflow/files/stm_assets/api/log/" 
        
        # Look for today's cache CSV file in the log folder
        cache_path = os.path.join(log_folder, cache_filename)
        print(f"Looking for cache file: {cache_path}")
        if os.path.exists(cache_path):
            # Get file info
            file_size = os.path.getsize(cache_path) / (1024 * 1024)  # Size in MB
            mod_time = datetime.fromtimestamp(os.path.getmtime(cache_path))

            return {
                "file_exists": True,
                "file_path": cache_path,
                "filename": cache_filename,
                "file_size": round(file_size, 2),
                "mod_time": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": None
            }
        
        # If no file found
        print(f"Cache file not found: {cache_path}")
        return {
            "file_exists": False,
            "filename": cache_filename,
            "error": f"Cache file not found: {cache_filename} in {log_folder}"
        }
    
    # Task to send email with cache CSV file attachment
    @task()
    def send_cache_email(file_info):
        """Send email with cache CSV file attached"""
        import sys
        sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
        from utils.envs.airflow_env_variable import AiflowEnvVariable
        from utils.email_recipients import Email
        
        env_var = AiflowEnvVariable()
        email = Email(env_var)
        email_recipients = email.get_email_recipients_for_request_cache()
        
        # Create email
        email_file = MIMEMultipart()
        
        if file_info["file_exists"] and file_info["error"] is None:
            # Success case - attach cache CSV file
            msg_text_html = f'''
            <html>
            <body>
                <h2>STM Cache Export - Daily Report</h2>
                <p><strong>Export Date:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>File Name:</strong> {file_info["filename"]}</p>
                <p><strong>File Size:</strong> {file_info["file_size"]} MB</p>
                <p><strong>Status:</strong> <span style="color: green;">✓ Cache File Found</span></p>
                
                <h3>Cache Contents Summary</h3>
                <p>The attached CSV file contains the current state of the STM request cache, including:</p>
                <ul>
                    <li>Active requests in the SAiRA Request pool</li>
                    <li>Request metadata and routing information</li>
                    <li>Time To Pick-Up and SLA information</li>
                </ul>
                
                <p><em>This is an automated export from the STM system.</em></p>
            </body>
            </html>
            '''
            
            # Attach cache CSV file
            try:
                with open(file_info["file_path"], "rb") as attachment:
                    part = MIMEBase('text', 'csv')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{file_info["filename"]}"'
                )
                email_file.attach(part)
                
            except Exception as e:
                msg_text_html += f'<p><strong>Warning:</strong> Could not attach file: {str(e)}</p>'
        
        else:
            # Error case - no attachment
            msg_text_html = f'''
            <html>
            <body>
                <h2>STM Cache Export - Daily Report</h2>
                <p><strong>Export Date:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>Expected File:</strong> {file_info["filename"]}</p>
                <p><strong>Status:</strong> <span style="color: red;">✗ Cache File Not Found</span></p>
                
                <h3>Error Details</h3>
                <p>{file_info["error"]}</p>
                
                <p><em>Please check the STM system and file export process.</em></p>
            </body>
            </html>
            '''
        
        email_file.attach(MIMEText(msg_text_html, 'html'))
        email_file['From'] = "stm.alerts@bell.ca"
        to_list = email_recipients
        email_file['To'] = ', '.join(to_list)
        # Send email
        subject = f'STM Cache Export - {datetime.now().strftime("%Y-%m-%d")}'
        if not file_info["file_exists"]:
            subject += ' - FILE NOT FOUND'
        email_file['Subject'] = subject
        
        send_mime_email(email_file["From"], to_list, email_file)
        
        print(f"Cache export email sent to: {email_recipients}")
        return {"email_sent": True, "recipients": email_recipients}
    
    # Define task dependencies
    file_info = get_cache_file()
    email_result = send_cache_email(file_info)
    
    file_info >> email_result

# Instantiate the DAG
dag_instance = main_dag()