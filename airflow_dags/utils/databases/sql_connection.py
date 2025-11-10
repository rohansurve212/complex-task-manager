# Import the abstract base class module
from abc import ABC, abstractmethod

# Class to hold connection information
class ConnectionInfo:
    # Define attributes for the connection information
    database: str
    host: str
    port: str
    user: str
    password: str
    
    # Initialize the connection information attributes
    def __init__(self, database: str, host: str, port: str, user: str, password: str):
        self.database = database
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        
# Abstract base class for SQL connections
class SqlConnection(ABC):
    # Abstract method to get connection information
    @abstractmethod
    def get_connection_info(self, connection_id) -> ConnectionInfo:
        pass

