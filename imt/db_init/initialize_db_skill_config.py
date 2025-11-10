import requests
import json
import pandas as pd
import pyodbc
from util_init_db import * 
from shared.all_envs import sp_vars, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS

''' 
This code is to connect to the services GET all skillsets and GET all agent Assignments to be able to initialize our database
'''

def get_authentication_skills_config():

    url = f"{sp_vars.base_url}/auth/realms/oc/protocol/openid-connect/token"

    payload=f"grant_type=password&client_id=oc-backend&client_secret={sp_vars.client_secret}&username={sp_vars.user}&password={sp_vars.pw}"
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': 'db4fdfa0d404bc10acda4670ccb15825=c99df4981f39cff9bad680b320e80dfe; e69f1ea65bfd1ce3ad5996309f24ac3e=63543081f83bde75f4a3d9008fb0dba3'
    }

    response = requests.request("POST", url, headers=headers, data=payload,verify=False)

    return response


def get_all_skills_config(atoken,limit,offset):

    url = f'{sp_vars.base_url}/api/service-order/queue/all?limit={limit}&offset={offset}'

    payload = ""
    headers = {
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json;charset=UTF-8',
    'Authorization': f'Bearer {atoken}',
    'Cookie': 'db4fdfa0d404bc10acda4670ccb15825=c99df4981f39cff9bad680b320e80dfe; e69f1ea65bfd1ce3ad5996309f24ac3e=63543081f83bde75f4a3d9008fb0dba3'
    }

    response = requests.request("GET", url, headers=headers, data=payload,verify=False)


    return response


if __name__ == "__main__": 

    # Separating into three parts because token changes
    for j in range(3):
        atoken = get_authentication_skills_config()
        access_token = json.loads(atoken.text)['access_token']
        # HEre we need to loop over pages that there is ... offset should be from 0 - 28*100 to cappture all pages
        for i in range(1000*j,1000*(j+1),262):
            r= get_all_skills_config(access_token,limit=262, offset=i)
            r_dict = json.loads(r.text)
            with open('init_skill_config.json', 'w') as fp:
                json.dump(r_dict, fp)
            
            server = SQL_SERVER
            database = DATABASE
            username = SQL_USER
            password = SQL_PASS
            conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+password)

            #update the db accordingly
            get_skill_config_and_update_db('init_skill_config.json',conn)

            conn.close()
