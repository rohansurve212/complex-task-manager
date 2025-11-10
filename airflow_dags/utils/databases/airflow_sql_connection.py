# Import necessary classes from Airflow and custom utils
from airflow.models.connection import Connection
from utils.databases.sql_connection import SqlConnection, ConnectionInfo

# Define a class that extends SqlConnection to work with Airflow connections
class AirflowSqlConnection(SqlConnection):
    # Method to retrieve connection information using a connection ID
    def get_connection_info(self, connection_id: str) -> ConnectionInfo:
        # Get the connection object from Airflow's secrets backend
        conn = Connection.get_connection_from_secrets(connection_id)
        # Return the connection information encapsulated in a ConnectionInfo object
        return ConnectionInfo(conn.schema, conn.host, conn.port, conn.login, conn.password)
