import requests
import json
import pandas as pd
import pyodbc
from util_init_db import * 
from shared.all_envs import sp_vars, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS

total_elements=13200 #Normally should find in API response

def get_authentication_agent_assignment():
    url = f"{sp_vars.base_url}/auth/realms/oc/protocol/openid-connect/token"

    payload=f"grant_type=password&client_id=oc-backend&client_secret={sp_vars.client_secret}&username={sp_vars.user}&password={sp_vars.pw}"
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': 'db4fdfa0d404bc10acda4670ccb15825=2a50a3c37d5e6020cba6f3bc9a4833a3; e69f1ea65bfd1ce3ad5996309f24ac3e=158f4ddc38a2bbed54c93b3f8153a5a1'
    }

    response = requests.request("POST", url, headers=headers, data=payload,verify=False)

    return response


def get_all_agent_assignment(atoken,limit,offset):
    # for this case the total number of pages is 2
    url = f'{sp_vars.base_url}/api/service-order/queue/assignment/all?limit={limit}&offset={offset}'
    payload = ""
    headers = {
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json;charset=UTF-8',
    'Authorization': f'Bearer {atoken}',
    'Cookie': 'db4fdfa0d404bc10acda4670ccb15825=2a50a3c37d5e6020cba6f3bc9a4833a3; e69f1ea65bfd1ce3ad5996309f24ac3e=158f4ddc38a2bbed54c93b3f8153a5a1'
    }

    response = requests.request("GET", url, headers=headers, data=payload,verify=False)

    return response


if __name__ == "__main__": 
    atoken = get_authentication_agent_assignment()
    access_token = json.loads(atoken.text)['access_token']
    # HEre we need to loop over pages that there is ... offset should be from 0 - 28*100 to cappture all pages
    for i in range(0,total_elements,100):
        r= get_all_agent_assignment(access_token,limit=100, offset=i)
        r_dict = json.loads(r.text)
        with open('init_skill_agent.json', 'w') as fp:
            json.dump(r_dict, fp)

        server = SQL_SERVER
        database = DATABASE
        username = SQL_USER
        password = SQL_PASS
        conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+password)


        #update the db accordingly
        get_agent_assignment_and_update_db('init_skill_agent.json',conn)
