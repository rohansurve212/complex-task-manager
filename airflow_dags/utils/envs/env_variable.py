# Import the abstract base class module and Enum class
from abc import ABC, abstractmethod
from enum import Enum

# Import necessary classes from custom utils
from utils.databases.sql_connection import ConnectionInfo, SqlConnection

# Enum to define environment types
class EnvironmentType(str, Enum):
    Prod = 'prod'
    Dev = 'dev'

# Abstract base class for environment variables
class EnvVariable(ABC):
    # Method to get the environment type
    def get_environment_type(self) -> EnvironmentType:
        env_type = self.get_variable('env')
        print('environment_type:', env_type)
        if env_type == 'prod':
            return EnvironmentType.Prod
        return EnvironmentType.Dev
    
    # Abstract method to get a variable as a string
    @abstractmethod
    def get_variable(self, name) -> str:
        pass

    # Abstract method to get a variable as a float
    @abstractmethod
    def get_variable_float(self, name) -> float:
        pass

    # Abstract method to get a variable as an integer
    @abstractmethod
    def get_variable_int(self, name) -> int:
        pass

    # Abstract method to get a SQL connection
    @abstractmethod
    def get_connection(self) -> SqlConnection:
        pass
    
    # Method to get connection information using a connection ID
    def get_connection_info(self, connection_id) -> ConnectionInfo:
        return self.get_connection().get_connection_info(connection_id)
