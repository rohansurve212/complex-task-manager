import os
from dotenv import load_dotenv
import requests
import json
import pandas as pd
import pyodbc
from util_init_db import * 
from shared.all_envs import sp_vars, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS, SMARTPATH_ENV
import urllib3
import logging
from logging.handlers import TimedRotatingFileHandler
urllib3.disable_warnings()

def get_authentication_agent_assignment():
    # To Do- add the url as variables in the .env
    if SMARTPATH_ENV.lower() == 'qa' or SMARTPATH_ENV.lower() == 'prod':
        url = f"{sp_vars.base_url}/login/oauth"
    else:
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
    url = f'{sp_vars.base_url}/smartpath/queue/assignment/all?limit={limit}&offset={offset}'
    payload = ""
    headers = {
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json;charset=UTF-8',
    'Authorization': f'Bearer {atoken}',
    'Cookie': '769825ffaec97adc91f8e9803cedd989=0e799fcf0ea603ca83fafcdea5054c66; db4fdfa0d404bc10acda4670ccb15825=3bd0e8dfdb5e5afe4ae4d90d93ceedc8; OCWEBSESSIONID=69403966-ded2-450f-b597-fd17b1b43e97; OC_LANDING_PAGE=/smartpath; _pk_id.5.5e08=47b4e56b75a78c77.1691085809.; _pk_ses.5.5e08=1; bportal_idp={"lang":"en_CA"}'
    }
    logging.info("RESPOBSE BEFORE ------------------------>")
    response = requests.request("GET", url, headers=headers, data=payload,verify=False)
    logging.info(response)
    logging.info("RESPONSE After ------------------------> {response.text}")
    return response


#total_elements=13200

if __name__ == "__main__": 
    
    atoken = get_authentication_agent_assignment()
    access_token = json.loads(atoken.text)['access_token']
    logging.info(access_token)
    total_elements=json.loads(get_all_agent_assignment(access_token,limit=1, offset=0).text)['totalElements']

    conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
    
    # Here we need to loop over pages that there is ... offset should be from 0 - 28*100 to cappture all pages
    for i in range(0,total_elements,500):
        r= get_all_agent_assignment(access_token,limit=500, offset=i)
        r_dict = json.loads(r.text)
        with open('init_skill_agent.json', 'w') as fp:
            json.dump(r_dict, fp)
        #update the db accordingly
        get_agent_assignment_and_update_db('init_skill_agent.json',conn)

    conn.close()
