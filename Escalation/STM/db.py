import os

from dotenv import load_dotenv

# Load environment variables from the .env file located at '/app/shared/.env'
load_dotenv('/app/shared/.env')

# Define the DB class to manage table name retrieval based on environment
class DB:
    # Retrieve the value of the 'ENVIRONMENT' environment variable
    _env = os.getenv('ENVIRONMENT')

    @staticmethod
    def escalation():
        # Returns the table name for 'escalation' based on the environment
        return DB._get_table_name('escalation')

    @staticmethod
    def agent():
        # Returns the table name for 'agent' based on the environment
        return DB._get_table_name('agent')
    
    @staticmethod
    def _get_table_name(table_name: str) -> str:
        # If the environment is 'PROD', return the table name as is
        if DB._env == "PROD":
            return f"{table_name}"
        # Otherwise, prepend 'uat_' to the table name for non-production environments
        return f"uat_{table_name}"