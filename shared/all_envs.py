import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

ENVIRONMENT = os.getenv('ENVIRONMENT')
SMARTPATH_ENV = os.getenv('SMARTPATH_ENV')
API_VERSION = os.getenv('API_VERSION')

SP_CLIENT_SECRET = os.getenv(f'{SMARTPATH_ENV.upper()}_CLIENT_SECRET')
SP_USER = os.getenv(f'{SMARTPATH_ENV.upper()}_USER')
SP_PASSWORD = os.getenv(f'{SMARTPATH_ENV.upper()}_PASSWORD')

ELASTIC_SERVER = os.getenv('ELASTIC_SERVER')
ELASTIC_USER = os.getenv('ELASTIC_USER')
ELASTIC_PASS = os.getenv('ELASTIC_PASS')

SQL_SERVER = os.getenv('SQL_SERVER')
PORT = os.getenv('PORT')
DATABASE = os.getenv('DATABASE')
SQL_USER = os.getenv('SQL_USER')
SQL_PASS = os.getenv('SQL_PASS')

PROD_LDAP_HOST = os.getenv('PROD_LDAP_HOST')
PROD_LDAP_USER = os.getenv('PROD_LDAP_USER')
PROD_LDAP_PASS = os.getenv('PROD_LDAP_PASS')

RABBIT_USER = os.getenv(f'{ENVIRONMENT.upper()}_RABBIT_USER')
RABBIT_PWD = os.getenv(f'{ENVIRONMENT.upper()}_RABBIT_PWD')
RABBIT_IP = os.getenv(f'{ENVIRONMENT.upper()}_RABBIT_IP')
RABBIT_PORT = os.getenv(f'{ENVIRONMENT.upper()}_RABBIT_PORT')

RABBITMQ_DEFAULT_PORT1 = os.getenv('RABBITMQ_DEFAULT_PORT1')
RABBITMQ_DEFAULT_PORT2 = os.getenv('RABBITMQ_DEFAULT_PORT2')
RABBITMQ_DEFAULT_USER = os.getenv('RABBITMQ_DEFAULT_USER')
RABBITMQ_DEFAULT_PASS = os.getenv('RABBITMQ_DEFAULT_PASS')

TD_HOST = os.getenv('TD_HOST')
TD_USER = os.getenv('TD_USER')
TD_PASS = os.getenv('TD_PASS')

LOGGER_LEVEL = os.getenv('LOGGER_LEVEL')
ENABLE_PUSH_MODEL = os.getenv('ENABLE_PUSH_MODEL', 'True')

DEFAULT_TTPU = int(os.getenv('DEFAULT_TTPU', '8'))
if not DEFAULT_TTPU:
    DEFAULT_TTPU = 8

DEFAULT_CACHE_HISTORY = int(os.getenv('DEFAULT_CACHE_HISTORY', '90'))
if not DEFAULT_CACHE_HISTORY:
    DEFAULT_CACHE_HISTORY = 90

@dataclass
class SPVars:
    """
    This is a centralized class variable that stores all SmartPath variables.
    """
    if SMARTPATH_ENV.lower() == 'prod':
        base_url = f"https://api.operationcentre.ms.bell.ca"
    else:
        base_url = f"https://api.qa.operationcentre.ms.bell.ca"

    base_url: base_url = base_url
    env: SMARTPATH_ENV = SMARTPATH_ENV
    client_secret: SP_CLIENT_SECRET = SP_CLIENT_SECRET
    user: SP_USER = SP_USER
    pw: SP_PASSWORD = SP_PASSWORD

sp_vars = SPVars()
