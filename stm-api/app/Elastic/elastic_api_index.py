import sys
sys.path.append('..')
import os
import pyodbc
from elasticsearch import Elasticsearch, helpers
import pandas as pd
import json
import requests
from datetime import datetime, timedelta, timezone

from shared.db import DB
from app.Elastic.elastic_settings import (
    all_cols,
    nested_cols,
    INDEX_NAME,
    mappings,
    make_request_body,
    get_auth_header
)
from shared.all_envs import sp_vars, SMARTPATH_ENV, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS, ELASTIC_SERVER, ELASTIC_USER, ELASTIC_PASS
import urllib3
urllib3.disable_warnings()

def get_service_user_OC_token(sp_vars):
    """Post request to generate authentication token"""
    print("Smartpath Env is --->", SMARTPATH_ENV)
    print("base url: ", sp_vars.base_url)
    if SMARTPATH_ENV.lower() in ['qa', 'prod']:
        url = f"{sp_vars.base_url}/login/oauth"
    else:
        url = f"{sp_vars.base_url}/auth/realms/oc/protocol/openid-connect/token"
    payload=f"grant_type=password&client_id=oc-backend&"+\
            f"client_secret={sp_vars.client_secret}&"+\
            f"username={sp_vars.user}&password={sp_vars.pw}"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 's_fid=58721E86E26E77E4-333FBE8EFDDF0106; s_vi=[CS]v1|32365FED0A8D54B4-600006F320DD0574[CE]; BEP_LANGUAGE=en; showprovinceselector=true; BBMUID=SegmentMode=enterprise&VisitorID=1ea58976-83b6-4b68-a91f-0a37ab0ce780; gemini=region=ON|language=en|province=ON|LarSegmentType=; _gcl_au=1.1.447402542.1687448725; _fbp=fb.1.1687448725416.419022717; _ga_RHH5313TEK=GS1.1.1687456148.2.0.1687456148.60.0.0; lanAkamaPro=AwccyOOIAQAADyyvlaPpPB3hJ5E-G_80EPjQP8AC3hEVi8OOoeeSLeqYjzH0Ac4v-f6uchRAwH8AAEB3AAAAAA|1|0|6860dd40df50ce0a5bdcde8180209c8a7a734759; TLTUID=A3CB92DEB8AEE242E3689C4F5ECDFAA1; AMCV_48B034FA53CF9FD10A490D44%40AdobeOrg=359503849%7CMCAID%7C32365FED0A8D54B4-600006F320DD0574%7CMCIDTS%7C19538%7CMCMID%7C06075730019815422410473480349897117208%7CMCAAMLH-1688607936%7C7%7CMCAAMB-1688607936%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1688010336s%7CNONE%7CvVersion%7C5.0.1; _scid=0b724351-611a-45c7-8f09-8b4b1eb6c61f; _tt_enable_cookie=1; _ttp=_Tv5AkV0165AYbf_3iAbh7Emi-X; _clck=15juquh|2|fcv|0|1268; _sctr=1%7C1687924800000; _ga=GA1.1.261313119.1687448724; mbox=PC#23b4832a551440a3b7046de8ae2d1a17.34_0#1750693525|session#e0646a19b7b84e2a80cb0cd0492f5fdb#1688005007; coveo_visitorId=d6814970-47a9-46ec-e571-f71c19475d29; da_lid=9189AD439A73EA13C3A2BB99FF50E1D537|0|0|0; _uetvid=ce188cb0111311ee95e49935519933ad; nmstat=1b5c442c-eb6a-5d56-1c80-c87712f28163; _scid_r=0b724351-611a-45c7-8f09-8b4b1eb6c61f; _ga_MK50H7QB2L=GS1.1.1688003136.4.1.1688003156.40.0.0; _ga_MTKGWZ28E4=GS1.1.1688003139.1.1.1688003156.43.0.0; _pk_id.5.ecd4=291887ad27d2b0f1.1690296106.; rxVisitor=1684848599996B0QJR243N77UR4O8TPRV35E06H5A2OE4; s_cc=true; bportal_idp={"lang":"en_CA"}; dtCookie=v_4_srv_9_sn_6AECA4743C10A976C7485E5ED0BBF827_perc_100000_ol_0_mul_1_app-3A46f1a806c667dad3_1_app-3Af7d3dd3c15111ccf_1_rcs-3Acss_0; TLP02cf917d=028702b9c909856e9e81e636da08c8aad0114ac2c293b10b65ee032e6488af24e1a4fdedb90a4c41b773279cea3d49ffedef0b2cce4f979712b965eef6434a08d473915ef6d927eeb91213b83a33ea5bfdac7ba798051bd95f40e6affd7498e5bbebaedfaae02fa7221dd390fcad31eb359d66562a; BEPSESSION=/JVdZta8W8e8LRjqYo365lyR76J7hTPG1TsSbIHTGZ4oG+kL2+qzU9ac9LvHBwmhV6EKfofo2SWyPW5OyEiJ/VEUXrNNiRgvTnVp7vnPw9ISuAv3B+oci4MgseR2xmkCUy5GKTbSK3GG1qRN1JV3E0he8CMoAeLx/GKJgj/aUSWKxf9i2ZBcHjBLCm24OzbrAk84Oq+f+iokDVID98MXgG4gRX+oLjHBJzXLAojQvJNCAyCBIKQZpwXQ2oJZNAZk0F/rp22qUWGqEY46EbyMWyQsH1WNOgY0x3xPTzDgcvDLOVpnOHYSmOzwOzG5Ud7NWv7tC1SikpwY2sCl20ZT2776aLxZuvYUtr+trQp/TZPxM8CGTx5/eFylBcxJS8DIoJuFMWzVRtA0hjcIAOQJZ/811fj+ID7AiMbDKR76YotS428wo/ZRs+eBwgEDo/ML5VCO3HlK3YS4x4SPRU3zTGf8jnwyFT04+jdcpplnNyrg0eOnMGGqIpk4R/UALk8wOkLKn+UUI5YG/CWnOUvXGagLuyi0vbFoeR4noLIOtJE2FqhqHp/bUQpuv0ie4LVQCIWblJwv3xG1y7vtr8OvQAo0X4DfrrC2de4RfgEeOyoDt7vNLNBTws3C8cimPhXrlh2/00HYuZQ34ab6SFrjguT7QoWC2loBPDBaG8ympeqsykSxjMdJxZFySrqIzltyf0le0XdsybGh+OFFvACZWEncVeEG2FWg67jqGTkUM5esGxTYYi9DelBswlLp5JfvwEBH1Cqu8xaphPB6mHkc58outIenyoNFLOFc8Gh3G6UsnHeuPW+rRp+Q800SKpJ37lEPyTLmQ28lTZfpvXM+kcjYpB/7SYwpQ2zJDq/5BOaxCdv5qfq9aI5Y9rXehOMUfWCtClxRrBOHlfk0kdTVsRUKQswgsed8GD5iTkBRI/rywBZVqczYKAi/Dg3vV182aAdMxw24YBNHbiNTHN8ggm3uJHfqZU1TZphk12UF3+vec013KizA9m6QpDHclu6/uUVKTh0mcA8QebDP8N/KXG2UEaB84boDbPZPibntvyYGG0nBsYXunStq5rmT6g0nvccooeO+EtGIkuKu5wPls+dPfCMTqDwbnCvTw13Ng6a3Tq4rv0o9tXTLqxi2jrcUOgN8BO2n7Hw6gVsatsd4EC7ihpYSlyM8CDM7Or+nWAjS1yJjdGkhhViOtAo8d9lBojptrrZR3bqDJHI7qz7zzvBc7bPIgO24KF/IRYqkoZdm5iAg5jXE21qsQZ34aJ/W; db4fdfa0d404bc10acda4670ccb15825=057419bc4f251bd1eebadb784a15f6e2; OC_LANDING_PAGE=/smartpath; OCWEBSESSIONID=f9324098-4c9c-4019-9cf0-d191ad832666; s_tp=2014; rxvt=1692359938255|1692358137606; dtPC=9$358137601_487h-vJWPADMCNPCMRBJVTCJSVUHICFLHHJMSE-0e0; s_ppve=Home%253AEmployee%2520directory%2C46%2C36%2C923; dtLatC=2; dtSa=true%7CS%7C-1%7C-%7C-%7C1692358138267%7C358137601_487%7Chttps%3A%2F%2Fbellnet.int.bell.ca%2Fdirectory-search%3Fpein%3DEQ29059%7C%7C%7C%7C; _pk_ref.5.ecd4=%5B%22%22%2C%22%22%2C1692363581%2C%22%2Fsmartpath%2Fconfirm%22%5D; 769825ffaec97adc91f8e9803cedd989=31b45c2a6cf2f1cec76e6af2ba9ccff4'
    }
    proxies = {
            "http": None,
            "https": None
        }

    return requests.request("POST", url, headers=headers, data=payload, proxies=proxies, verify=False)

def smarttask_api_search_request(sp_vars, auth_header, date, limit=10000, filter_comp=False):
    """Search the API based on payload found in elastic_settings.py
    The date in this payload is dynamic"""
    
    print("base url: ", sp_vars.base_url)
    url = f"{sp_vars.base_url}/smartpath/smarttask/order/_startScroll?offset=0&limit={limit}&fields="

    payload = json.dumps(make_request_body(date=date, filter_comp=filter_comp))
    headers = get_auth_header(auth_header)

    proxies = {
            "http": None,
            "https": None
        }
    print('RESPONSE---->', requests.request("POST", url, headers=headers, data=payload, proxies = proxies, verify=False).content)
    return requests.request("POST", url, headers=headers, data=payload, proxies = proxies, verify=False)

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
        'DRIVER={ODBC Driver 17 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes'
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

############
# Code to create index
############

def initialize_elastic_connection():
    
    es_connection = Elasticsearch(ELASTIC_SERVER, 
                                  verify_certs = False,
                                  http_auth=(ELASTIC_USER, ELASTIC_PASS))
    return es_connection

def elastic_data_generator(df, cols, index_name):
    for _, line in enumerate(df):
        yield {
          '_op_type': 'index',
          '_index': index_name,
          '_id': line.get('request_id'),
          'type': '_doc',
          '_source': 
            {k: line.get(k, ['No Data']) for k in cols}
        }

def create_elastic_index(es_connection, index_name):
    es_connection.indices.create(index=index_name, body=mappings)

def load_data_to_index(es_connection, df_dict, cols, index_name):
    if not df_dict:
        print("Empty dict - Nothing was indexed")
        return
    else:
        try:
            resp = helpers.bulk(es_connection, elastic_data_generator(df_dict, cols, index_name))
            print(f"Finished indexing data to {index_name}")
        except Exception as e:
            print(e)

def get_results_from_smartpath_api(sp_vars, date, limit=500, filter_comp=False):

    service_token = get_service_user_OC_token(sp_vars)
    access_token = json.loads(service_token.text)['access_token']
    r = smarttask_api_search_request(sp_vars, access_token, date, limit, filter_comp)
    r_dict = json.loads(r.text)

    if 'metadata' not in r_dict.keys():
        raise KeyError
    meta_data = r_dict['metadata']

    print("="*30)
    print(f"Call limit: {meta_data['limit']}")
    print(f"Total record count: {meta_data['totalRecordCount']}")
    print("="*30)
    print("base url: ", sp_vars.base_url)

    return r_dict['results']

def smartpath_data_to_elastic_stm(sp_vars, date, create_index=False, limit=10000, filter_comp=False):

    # Prepare data for indexation
    results = get_results_from_smartpath_api(sp_vars, date, limit, filter_comp)    
    
    df_dict = prepare_data_for_elastic(results, all_cols)

    es_connection = initialize_elastic_connection() 

    if create_index:
        create_elastic_index(es_connection, INDEX_NAME)

    load_data_to_index(es_connection, df_dict, all_cols, INDEX_NAME)

if __name__ == '__main__':
    smartpath_data_to_elastic_stm(
        sp_vars,
        # date=(datetime.now(timezone.utc) - timedelta(seconds=5)).strftime('%Y-%m-%dT%H:%M:%S'),  # "2022-03-20T14:21:30", 
        date="2020-01-01T14:21:30",
        create_index=False,
        filter_comp=False
    )
