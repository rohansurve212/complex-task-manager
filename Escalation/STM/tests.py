from django.test import TestCase

# Create your tests here.
import os
from dotenv import load_dotenv
load_dotenv('.env')
ELASTIC_USER = os.getenv('ELASTIC_USER')
ELASTIC_PASS = os.getenv('ELASTIC_PASS')
print(ELASTIC_USER)

os.getenv('SQL_SERVER')
os.getenv('DATABASE')
os.getenv('SQL_USER')
os.getenv('SQL_PASS')
os.getenv('PORT')

os.getenv('ELASTIC_USER')
os.getenv('UAT_CLIENT_SECRET')

print(os.environ.get('ELASTIC_USER'))
print(os.getenv('ELASTIC_USER'))
os.getenv('ENVIRONMENT')

ELASTIC_SERVER = 'https://paas-mtrl-blmcih-data-03.qc.bell.ca:9200/'
print(ELASTIC_SERVER)

print(os.getenv('ELASTIC_SERVER'))

import os
from dotenv import load_dotenv
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__name__)))
load_dotenv(os.path.join(BASE_DIR, "mysite", ".env"))
# load_dotenv(os.path.join(BASE_DIR, '.env'))
print(os.getenv('ELASTIC_SERVER'))
os.environ.get()
os.environ


from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__name__)))
BASE_DIR
os.getenv('SECRET_KEY')

import os
import environ

env = environ.Env()
# read th .env file
environ.Env.read_env()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env('ELASTIC_SERVER')

from django.core.exceptions import ImproperlyConfigured
import environ
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, 'mysite/.env'))
env('ELASTIC_USER')

os.getenv('SECRET_KEY')
BASE_DIR


import os
import environ
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
env = environ.Env()
environ.Env.read_env()


def get_env_variable(var_name):
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "set the %s environment variable" % var_name
        raise ImproperlyConfigured(error_msg)


SECRET_KEY = get_env_variable('ELASTIC_USER')

BASE_DIR

dotenv_path = Path('mysite/.env')
load_dotenv(dotenv_path=dotenv_path)
os.getenv('ELASTIC_USER')
os.getenv('SQL_SERVER')
os.environ.get('ELASTIC_USER')


ELASTIC_SERVER = os.getenv('ELASTIC_SERVER')
print(ELASTIC_SERVER)
ELASTIC_USER = os.getenv('ELASTIC_USER')
ELASTIC_PASS = os.getenv('ELASTIC_PASS')
from elasticsearch import Elasticsearch
es_connection_test = Elasticsearch(ELASTIC_SERVER, 
                                    verify_certs = False,
                                    http_auth=(ELASTIC_USER, ELASTIC_PASS))