# Importing necessary libraries
import sys
sys.path.append('/usr/local/airflow/dags/stm/')  # Adding the STM directory to the airflow container path

# Importing Airflow and other required modules
from datetime import datetime, timedelta
from airflow.decorators import dag, task 
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText 
from airflow.utils.email import send_mime_email  

# Setting default arguments for the DAG
default_args = {
    "owner": "eq02977",
    "description": "STM No Work Report",
    "email": ["stm.alerts@bell.ca"],
    "start_date": datetime(2024,9,15),
    "retries":0,
    "email_on_failure": True,
    "retry_delays":timedelta(minutes=2)
}

# Defining the DAG
@dag(
    dag_id="no_work_report",
    description="no_work_report", 
    default_args=default_args, 
    catchup=False, 
    schedule_interval='*/10 * * * *', # runs every 10 minutes
    tags=["saira", "stm", "control_plan"]
)
def main_task():
    agents_df = extract_agents()
    ldap_df = extract_ldap(agents_df)
    nowork = extract_nowork(ldap_df)
    send_email(nowork)
    data_load_to_Elastic(nowork, account_index_name='bbm_aiml_saira_nowork_report-prod')

# Task to extract agent data
@task()
def extract_agents():
    # Importing necessary libraries
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook 
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable 
    from utils.sql_query import DB 
    import pandas as pd 

    # Setting up database connection and executing query
    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"
    query = db.get_agents_stm()  # Query to fetch agent data
    if query != '':
        print(query)
        mssql_hook = MsSqlHook(mssql_conn_id=connection_id)  # MSSQL connection
        agents = mssql_hook.get_pandas_df(query)  # Fetching data as a DataFrame
        print(len(agents))
        return agents  # Returning the extracted data
    
    return pd.DataFrame()  # Return empty DataFrame if no query is provided

# Task to extract LDAP data for agents
@task()
def extract_ldap(agents):
    from airflow.models.connection import Connection  
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')  
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import teradatasql  
    import pandas as pd

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id_td = "teradata_stm"  # Teradata connection ID
    
    if not agents.empty:
        # Preparing query with agent IDs
        agent_ids = agents['agent_id'].tolist()
        agent_ids_str = ', '.join(f"'{agent_id}'" for agent_id in agent_ids)
        agent_ids_str = f"({agent_ids_str})"
        query_td = db.get_ldap_data(agent_ids_str)  # Query for LDAP data
        if query_td != '':
            conn = Connection.get_connection_from_secrets(connection_id_td)  # Fetching connection details
            with teradatasql.connect(host=conn.host, user=conn.login, password=conn.password) as connect:
                ldap_df = pd.read_sql(query_td, connect)  # Executing query and fetching data
            print(len(ldap_df))
                
            return ldap_df
    
    return pd.DataFrame()  # Return empty DataFrame if no data is fetched

# Task to extract no work data and merge with LDAP data
@task()
def extract_nowork(ldap_df):
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.sql_query import DB
    import pandas as pd

    env_var = AiflowEnvVariable()
    db = DB(env_var)
    connection_id = "bbm_stm"
    query_nowork = db.get_nowork()  # Query to fetch no work data
    nowork = pd.DataFrame()
    email_data = pd.DataFrame()
    if query_nowork != '':
        print(query_nowork)
        mssql_hook = MsSqlHook(mssql_conn_id=connection_id)  # MSSQL connection
        nowork = mssql_hook.get_pandas_df(query_nowork)  # Fetching no work data
        print(len(nowork))

        # Merging no work data with LDAP data
        nowork = nowork.merge(ldap_df, how='left', left_on='agent_id', right_on='person_login1')

        # Cleaning and formatting data
        nowork.fillna('none', inplace=True)
        nowork['assign_date'] = pd.to_datetime(nowork['assign_date'], utc=True)
        nowork['assign_date_est'] = nowork['assign_date'].dt.tz_convert('US/Eastern')
        nowork['hour_of_day'] = nowork['assign_date_est'].dt.hour
        nowork['assign_date_est'] = nowork['assign_date_est'].dt.strftime('%Y-%m-%d %H:%M:%S')

        # Selecting relevant columns
        nowork = nowork[['id', 'agent_id', 'assign_date_est', 'work_status', 'person_pein', 'person_full_name', 
                         'person_manager_name', 'person_manager_pein', 'person_hrchy_level4_name', 
                         'person_hrchy_level4_pein', 'person_hrchy_level4_tier', 'person_hrchy_level3_name', 
                         'person_hrchy_level3_pein', 'person_hrchy_level3_tier', 'hour_of_day']]
        # Preparing email data
        email_data = nowork[['agent_id', 'person_full_name', 'assign_date_est', 'work_status', 
                             'person_manager_name', 'person_hrchy_level4_name', 'person_hrchy_level3_name']]

        return {"nowork": nowork, "email_data": email_data}  # Returning no work and email data
    return {"nowork": nowork, "email_data": email_data}  # Returning empty data if query fails

# @task()
# def get_cp_emails(no_work):
#     nowork = no_work["nowork"]
#     from airflow.models.connection import Connection
#     import sys
#     sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
#     from utils.envs.airflow_env_variable import AiflowEnvVariable
#     from utils.sql_query import DB
#     import teradatasql
#     import pandas as pd

#     env_var = AiflowEnvVariable()
#     db = DB(env_var)
#     connection_id_td = "teradata_stm"
#     cp_emails = pd.DataFrame()
#     if not nowork.empty:
#         cp2_peins = nowork['person_hrchy_level4_pein'].unique().tolist()
#         cp3_peins = nowork['person_hrchy_level3_pein'].unique().tolist()
#         cp_peins = cp2_peins + cp3_peins
#         cp_peins_str = ', '.join(f"'{cp_pein}'" for cp_pein in cp_peins)
#         cp_peins_str = f"({cp_peins_str})"
#         query_cp_emails = db.get_cp_emails(cp_peins_str)
#         if query_cp_emails != '':
#             conn = Connection.get_connection_from_secrets(connection_id_td)
#             with teradatasql.connect(host=conn.host,user=conn.login, password=conn.password) as connect:
#                 cp_emails = pd.read_sql(query_cp_emails, connect)
#             print(len(cp_emails))
        
#     return cp_emails

# Task to send email alert
@task()
def send_email(no_work):
    # Extract the email data from the input dictionary
    email_data = no_work["email_data"]
    
    # Add the required directory to the system path for importing utilities
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    
    # Import environment variables and email recipient utilities
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.email_recipients import Email

    # Initialize environment variables and the Email utility class
    env_var = AiflowEnvVariable()
    email = Email(env_var)
    
    # Retrieve email recipients specific to the no_work condition
    email_rec = email.get_email_recipients_for_no_work()

    # if not cp_emails.empty:

    #     cp_emails = cp_emails['person_email'].tolist()
    #     email_rec += cp_emails
    # print(email_rec)
    
    # If there is email data, proceed to generate and send an email alert
    if not email_data.empty:
        # Create a new MIME email object
        email_file = MIMEMultipart()
        
        # Define the HTML content for the email body
        msg_text_html = '''
            ===============================  Warning =============================== <br>
         Hello, <br> Note that an email alert was triggered for the STM Application.<br><br>
        <h4>The work_status of some request(s) was either NO_WORK or NO_ASSIGNMENT </h4>
        <br>
        <h4>Details:</h4>
        <table border="1">
            <tr>
                <th>Agent ID</th>
                <th>Agent Name</th>
                <th>Assign Date</th>
                <th>Work Status</th>
                <th>Manager Name</th>
                <th>CP2 Name</th>
                <th>CP3 Name</th>
            </tr>
        '''
        
        # Add rows to the HTML table for each record in the email data
        for index, row in email_data.iterrows():
            msg_text_html += f'''
            <tr>
                <td>{row['agent_id']}</td>
                <td>{row['person_full_name']}</td>
                <td>{row['assign_date_est']}</td>
                <td>{row['work_status']}</td>
                <td>{row['person_manager_name']}</td>
                <td>{row['person_hrchy_level4_name']}</td>
                <td>{row['person_hrchy_level3_name']}</td>
            </tr>
            '''
        
        # Close the HTML table and add a footer
        msg_text_html += '''
            </table>
            <br>
            <i>This is an auto-generated email</i>
        '''
        
        # Attach the HTML content to the email
        msg_text = MIMEText(msg_text_html, 'html')
        email_file.attach(msg_text)
        
        # Set email sender, recipients, and subject
        email_file['From'] = "stm.alerts@bell.ca"
        to_list = email_rec
        email_file['To'] = ', '.join(to_list)
        email_file['Subject'] = "STM Work Status is either No Work or No Assignment -- EMAIL Alert"

        # Send the email
        send_mime_email(email_file["From"], to_list, email_file)    
    else:
        # Log a message if no anomalies are found
        print("No anomaly found")

@task.virtualenv(requirements=['elasticsearch'])
def data_load_to_Elastic(no_work, account_index_name):
    # Extract the "nowork" DataFrame from the input dictionary
    nowork = no_work["nowork"]
    
    # Add the required directory to the system path for importing utilities
    import sys
    sys.path.append('/usr/local/airflow/dags/stm/airflow_dags/')
    
    # Import environment variables and Elasticsearch utility class
    from utils.envs.airflow_env_variable import AiflowEnvVariable
    from utils.elastic_utils import EsManagement

    sys.path.append('/usr/local/airflow/dags/stm/')
    
    # Early return if the DataFrame is empty
    if nowork.empty:
        print('no data to load')
        return

    # Suppress warnings for unverified HTTPS requests
    import warnings
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    # Define the Elasticsearch mappings for the data schema
    data_map = {"mappings": {
                "properties": {
                'id': {"type":"integer"},
                'agent_id':{"type":"keyword"},
                'assign_date_est':{"type":"date","format":"yyyy-MM-dd HH:mm:ss"},
                'work_status':{"type":"keyword"},
                'person_pein':{"type":"keyword"},
                'person_full_name':{"type":"keyword"},
                'person_manager_name':{"type":"keyword"},
                'person_manager_pein':{"type":"keyword"},
                'person_hrchy_level4_name':{"type":"keyword"},
                'person_hrchy_level4_pein':{"type":"keyword"},
                'person_hrchy_level4_tier':{"type":"keyword"},
                'person_hrchy_level3_name':{"type":"keyword"},
                'person_hrchy_level3_pein':{"type":"keyword"},
                'person_hrchy_level3_tier':{"type":"keyword"},
                'hour_of_day':{"type":"integer"}
   
            }
        }
    }
    
    # Convert the "nowork" DataFrame to a dictionary format for insertion
    array = nowork.to_dict('records')
    
    # Initialize environment variables and Elasticsearch management utility
    env_var = AiflowEnvVariable()
    es_connection = EsManagement(env_var)
    
    # Insert the data into Elasticsearch
    es_connection.insert_documents(account_index_name, array, 'id')

# Run the main task
data = main_task()
