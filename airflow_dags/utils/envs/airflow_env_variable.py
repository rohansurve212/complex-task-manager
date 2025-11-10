# Add the project directory to the airflow docker container path
import sys
sys.path.append("/usr/local/airflow/dags/stm/airflow_dags/")

# Import necessary classes from custom utils
from utils.envs.env_variable import EnvVariable
from utils.databases.sql_connection import SqlConnection

# Define a class that extends EnvVariable to work with Airflow environment variables
class AiflowEnvVariable(EnvVariable):
    # Method to get a variable as a string
    def get_variable(self, name) -> str:
        from airflow_dags.airflow import Airflow
        return Airflow.get_variable(name)

    # Method to get a variable as a float
    def get_variable_float(self, name) -> float:
        from airflow_dags.airflow import Airflow
        return Airflow.get_variable_float(name)

    # Method to get a variable as an integer
    def get_variable_int(self, name) -> int:
        from airflow_dags.airflow import Airflow
        return Airflow.get_variable_int(name)

    # Method to get a SQL connection
    def get_connection(self) -> SqlConnection:
        from utils.databases.airflow_sql_connection import AirflowSqlConnection
        return AirflowSqlConnection()
