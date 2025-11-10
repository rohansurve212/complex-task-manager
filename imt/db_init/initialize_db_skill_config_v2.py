import os
from dotenv import load_dotenv
import requests
import json
import pandas as pd
import pyodbc
from util_init_db import * 
from shared.all_envs import sp_vars, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS, SMARTPATH_ENV
import urllib3
urllib3.disable_warnings()
import logging

''' 
This code is to connect to the services GET all skillsets and GET all agent Assignments to be able to initialize our database
'''

def get_authentication_skills_config():

    if SMARTPATH_ENV.lower() == 'qa' or SMARTPATH_ENV.lower() == 'prod':
        url = f"{sp_vars.base_url}/login/oauth"
    else:
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

    url = f'{sp_vars.base_url}/smartpath/queue/all?limit={limit}&offset={offset}'

    payload = ""
    headers = {
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json;charset=UTF-8',
    'Authorization': f'Bearer {atoken}',
    'Cookie': '769825ffaec97adc91f8e9803cedd989=0e799fcf0ea603ca83fafcdea5054c66; db4fdfa0d404bc10acda4670ccb15825=3bd0e8dfdb5e5afe4ae4d90d93ceedc8; OCWEBSESSIONID=69403966-ded2-450f-b597-fd17b1b43e97; OC_LANDING_PAGE=/smartpath; _pk_id.5.5e08=47b4e56b75a78c77.1691085809.; bportal_idp={"lang":"en_CA"}; _pk_ref.5.5e08=%5B%22%22%2C%22%22%2C1691098092%2C%22%2Fsmartpath%2Fconfirm%22%5D; _pk_ses.5.5e08=1'
    }

    response = requests.request("GET", url, headers=headers, data=payload,verify=False)


    return response

def refresh_token_skills_config(limit,offset):

    new_token = get_authentication_skills_config()
    new_access_token = json.loads(new_token.text)['access_token']
    logging.info(f"Changed the access_token successfully --------------------------------> {new_access_token}")
    new_skills_config = get_all_skills_config(new_access_token, limit,offset)
    return new_skills_config


if __name__ == "__main__": 

    atoken = get_authentication_skills_config()
    access_token = json.loads(atoken.text)['access_token']
    # Get the number of elements to update
    total_elements=json.loads(get_all_skills_config(access_token,limit=1, offset=0).text)['totalElements']
    
    conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS)
    # HEre we need to loop over pages that there is ... offset should be from 0 - 28*100 to cappture all pages
    a= round(total_elements/1000)
    for j in range (a+1):
        for i in range(1000*j,1000*(j+1),500):                                       
            r= get_all_skills_config(access_token,limit=500, offset=i)
            logging.info(f"r HEADERS ------------------------------------------------------------------------> {r.headers}")
            try:
                r_dict = json.loads(r.text)
            except json.decoder.JSONDecodeError as e:
                logging.info(f"GOT ERROR JSON DECODE ERROR -------------------------------> {e}")
                r = refresh_token_skills_config(limit=500, offset=i)
                logging.info(f"r.text is ------------------------------------------------> {r.text}")
                r_dict = json.loads(r.text)
                logging.info(f"r_dict Value ----------------------------------------------> {r_dict}")
            with open('init_skill_config.json', 'w') as fp:
                json.dump(r_dict, fp)
            # update the db accordingly
            get_skill_config_and_update_db('init_skill_config.json', conn)    
            logging.info("successfully updated GET_AGENT_ASSIGNMENT_AND_UPDATE_DB ------------------------------------------->")
    conn.close()
