# Import required libraries for datetime handling, OS interaction, data handling, and database connectivity
from datetime import datetime, timezone
import os
import time
import pyodbc
from elasticsearch import Elasticsearch, helpers
import pandas as pd
import json
import requests
import logging

# Import environment variables and configurations specific to the application
from shared.all_envs import sp_vars, SMARTPATH_ENV, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS

# Import database utilities and Elasticsearch settings
from shared.db import DB
from elastic_settings import (
    all_cols,
    nested_cols,
    INDEX_NAME,
    mappings,
    make_request_body,
    get_auth_header
)

def initialize_elastic_connection():
    """
    Initialize and return a connection to the Elasticsearch server.
    Uses credentials and server information from environment variables.
    """
    es_connection = Elasticsearch(ELASTIC_SERVER, 
                                  verify_certs=False,  # Disable SSL certificate verification
                                  http_auth=(ELASTIC_USER, ELASTIC_PASS))  # Authenticate with username and password
    return es_connection

def prepare_data_and_load_to_index(es_connection, results, index_name):
    """
    Prepares data for Elasticsearch indexing and loads it into the specified index.
    - Converts results into the required format.
    - Indexes the data into Elasticsearch.
    """
    print(f"({datetime.now()}) prepare_data_for_elastic -----------------------------------------------------------------> ELASTIC")
    df_dict = prepare_data_for_elastic(results, all_cols)  # Prepare data for indexing
    print(f"({datetime.now()}) load_data_to_index")
    load_data_to_index(es_connection, df_dict, all_cols, index_name)  # Load data into the index

def get_service_user_OC_token(sp_vars):
    """Post request to generate authentication token"""
    print("Smartpath Env is --->", SMARTPATH_ENV)
    print("base url: ", sp_vars.base_url)
    if SMARTPATH_ENV.lower() == 'qa':
        url = f"{sp_vars.base_url}/login/oauth"
    else:
        if SMARTPATH_ENV.lower() == 'prod':
            url = f"{sp_vars.base_url}/login/oauth"
            print("moved into IF OF ELSE --------------> getting the url ----------------->", url)
        else:
            url = f"{sp_vars.base_url}/auth/realms/oc/protocol/openid-connect/token"
            print("moved into ELSE OF ELSE --------------> getting the url ----------------->", url)
    payload=f"grant_type=password&client_id=oc-backend&"+\
            f"client_secret={sp_vars.client_secret}&"+\
            f"username={sp_vars.user}&password={sp_vars.pw}"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 's_fid=58721E86E26E77E4-333FBE8EFDDF0106; s_vi=[CS]v1|32365FED0A8D54B4-600006F320DD0574[CE]; BEP_LANGUAGE=en; showprovinceselector=true; BBMUID=SegmentMode=enterprise&VisitorID=1ea58976-83b6-4b68-a91f-0a37ab0ce780; gemini=region=ON|language=en|province=ON|LarSegmentType=; _gcl_au=1.1.447402542.1687448725; _fbp=fb.1.1687448725416.419022717; _ga_RHH5313TEK=GS1.1.1687456148.2.0.1687456148.60.0.0; lanAkamaPro=AwccyOOIAQAADyyvlaPpPB3hJ5E-G_80EPjQP8AC3hEVi8OOoeeSLeqYjzH0Ac4v-f6uchRAwH8AAEB3AAAAAA|1|0|6860dd40df50ce0a5bdcde8180209c8a7a734759; TLTUID=A3CB92DEB8AEE242E3689C4F5ECDFAA1; AMCV_48B034FA53CF9FD10A490D44%40AdobeOrg=359503849%7CMCAID%7C32365FED0A8D54B4-600006F320DD0574%7CMCIDTS%7C19538%7CMCMID%7C06075730019815422410473480349897117208%7CMCAAMLH-1688607936%7C7%7CMCAAMB-1688607936%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1688010336s%7CNONE%7CvVersion%7C5.0.1; _scid=0b724351-611a-45c7-8f09-8b4b1eb6c61f; _tt_enable_cookie=1; _ttp=_Tv5AkV0165AYbf_3iAbh7Emi-X; _clck=15juquh|2|fcv|0|1268; _sctr=1%7C1687924800000; _ga=GA1.1.261313119.1687448724; mbox=PC#23b4832a551440a3b7046de8ae2d1a17.34_0#1750693525|session#e0646a19b7b84e2a80cb0cd0492f5fdb#1688005007; coveo_visitorId=d6814970-47a9-46ec-e571-f71c19475d29; da_lid=9189AD439A73EA13C3A2BB99FF50E1D537|0|0|0; _uetvid=ce188cb0111311ee95e49935519933ad; nmstat=1b5c442c-eb6a-5d56-1c80-c87712f28163; _scid_r=0b724351-611a-45c7-8f09-8b4b1eb6c61f; _ga_MK50H7QB2L=GS1.1.1688003136.4.1.1688003156.40.0.0; _ga_MTKGWZ28E4=GS1.1.1688003139.1.1.1688003156.43.0.0; _pk_id.5.ecd4=291887ad27d2b0f1.1690296106.; rxVisitor=1684848599996B0QJR243N77UR4O8TPRV35E06H5A2OE4; bportal_idp={"lang":"en_CA"}; db4fdfa0d404bc10acda4670ccb15825=ae7fcf030e5768885ef7f6d977792d24; OC_LANDING_PAGE=/smartpath; 769825ffaec97adc91f8e9803cedd989=e813aef8fefdcd3f8450194188b93087; _pk_ref.5.ecd4=%5B%22%22%2C%22%22%2C1693932905%2C%22%2Fsmartpath%2Fconfirm%22%5D; _pk_ses.5.ecd4=1; OCWEBSESSIONID=1b59e660-5b74-438b-862b-45574371832b'
    }

    proxies = {
            "http": None,
            "https": None
        }
    logging.debug('This will get logged')
    return requests.request("POST", url, headers=headers, data=payload, proxies=proxies, verify=False)

def prepare_data_for_elastic(results, all_cols):
    """
    1. Make custom nan values for flattened fields for indexation puposes
    2. Append foc targets to API results
    3. Then create a dataframe that is converted to a list of dicts. This format is
    requred for Elasticsearch indexation. Each dictionnary will become an Elastci doc"""

    # 1
    results = nested_col_nans_to_dict(results, nested_cols)

    # 2
    con = pyodbc.connect(
        'DRIVER={ODBC Driver 18 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes'
    )
    cur = con.cursor()

    for res in results:
        foc_target = get_foc_target(cur, res)
        res['source']['focTarget'] = foc_target
        res['request_id'] = res['id']
        del res['id']

    # 3
    df = pd.DataFrame(data=results, columns=all_cols)
    df = df.fillna('nan')
    return df.to_dict('records')

def nested_col_nans_to_dict(results, nested_cols):
    """For each flattened field, we cannot use 'nan' values when there is no data. If there is no data
    for a flattened field, we must represent the fact that there is no data by a dictionary"""

    for resp in results:
        for nested_col in nested_cols:
            if nested_col not in resp.keys():
                resp.update({nested_col: {"value": "no-data"}})
    return results


def get_foc_target(cur, res):
    """Assumption: if either of the columns to retrieve an foc target from the db is None,
    we assume the foctarget is 0"""

    sql_query_values = {}
    for col in ['requestSource', 'product', 'serviceRegion', 'requestType']:
        if col in res['source'].keys():
            sql_query_values[col] = res['source'][col].lower()
        else:
            sql_query_values[col] = None

    if not all(
        (isinstance(sql_query_values['requestSource'], str),
         isinstance(sql_query_values['product'], str),
         isinstance(sql_query_values['serviceRegion'], str),
         isinstance(sql_query_values['requestType'], str))
         ):
        return 0

    sql = f"""SELECT CASE WHEN foc_target IS NULL THEN 0 ELSE foc_target 
             END as focTarget FROM {DB.foc_targets()}
    WHERE request_source='""" + sql_query_values['requestSource'] + """'
    AND product='""" + sql_query_values['product'] + """'
    AND service_region='""" + sql_query_values['serviceRegion'] + """'
    AND request_type='""" + sql_query_values['requestType'] + "'"
    foc_target = cur.execute(sql).fetchall()
    
    if not foc_target:
        return 0
    return foc_target[0][0]


def load_data_to_index(es_connection, df_dict, cols, index_name):
    """
    Loads prepared data into an Elasticsearch index.
    Uses the bulk API for efficient indexing.
    """
    if df_dict == []:
        print("Empty dict - Nothing was indexed")
        return
    else:
        try:
            resp = helpers.bulk(es_connection, elastic_data_generator(df_dict, cols, index_name))
            print(f"{datetime.now(timezone.utc)} Finished indexing data to {index_name}")
        except Exception as e:
            print(e)


def elastic_data_generator(df, cols, index_name):
    """
    A generator function to yield data in the format required for Elasticsearch bulk indexing.
    """
    for _, line in enumerate(df):
        yield {
          '_op_type': 'index',
          '_index': index_name,
          '_id': line.get('request_id'),
          'type': '_doc',
          '_source': 
            {k: line.get(k, ['No Data']) for k in cols}
        }