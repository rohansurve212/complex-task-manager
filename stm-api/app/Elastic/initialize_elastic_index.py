import sys
sys.path.append('..')
import json
import requests
import time
import httpx
import logging

from app.Elastic.elastic_settings import all_cols, make_request_body, get_auth_header, INDEX_NAME, mappings
from app.Elastic.elastic_api_index import (
    initialize_elastic_connection,
    get_service_user_OC_token,
    prepare_data_for_elastic,
    load_data_to_index
)
import urllib3
urllib3.disable_warnings()
from shared.all_envs import sp_vars

logger = logging.getLogger("API log")

def create_elastic_index(es_connection, index_name):
    es_connection.indices.create(index=index_name, body=mappings)

async def start_scroll_elastic_requests(sp_vars, auth_header, date, limit, filter_comp):
    url = f"{sp_vars.base_url}/smartpath/smarttask/order/_startScroll?offset=0&limit={limit}&fields="
    payload = json.dumps(make_request_body(date=date, filter_comp=filter_comp))
    headers = get_auth_header(auth_header)
    proxies = {
            "http://": None,
            "https://": None
        }
    # Use httpx.AsyncClient with increased timeout for asynchronous http requests
    timeout = httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=10.0)
    async with httpx.AsyncClient(proxies=proxies, verify=False, timeout=timeout) as client:
        response = await client.post(url, headers=headers, content=payload)
    return response

async def continue_scroll_elastic_requests(sp_vars, auth_header, date, scroll_id, filter_comp):
    url = f"{sp_vars.base_url}/smartpath/smarttask/order/_continueScroll?scrollId={scroll_id}"
    payload = json.dumps(make_request_body(date=date, filter_comp=filter_comp))
    headers = get_auth_header(auth_header)
    proxies = {
            "http://": None,
            "https://": None
        }
    # Use httpx.AsyncClient with increased timeout for asynchronous http requests
    timeout = httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=10.0)
    try:
        async with httpx.AsyncClient(proxies=proxies, verify=False, timeout=timeout) as client:
            response = await client.post(url, headers=headers, content=payload)
            # Log response status for debugging
            if response.status_code != 200:
                logger.error(f"continueScroll API returned status {response.status_code}: {response.text}")
            return response  
    except httpx.TimeoutException as e:
        logger.error(f"Timeout error in continueScroll API: {e}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Request error in continueScroll API: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in continueScroll API: {e}")
        raise

def prepare_data_and_load_to_index(es_connection, results, index_name):
    df_dict = prepare_data_for_elastic(results, all_cols)
    load_data_to_index(es_connection, df_dict, all_cols, index_name)

def smartpath_data_to_elastic_stm(sp_vars, date, limit, index_name, create_index, filter_comp):

    es_connection = initialize_elastic_connection()

    service_token = get_service_user_OC_token(sp_vars)
    access_token = json.loads(service_token.text)['access_token']
    start_response = start_scroll_elastic_requests(sp_vars, access_token, date, limit, filter_comp)
    print('Start Respose Headers', start_response.headers)
    scroll_id = start_response.headers['x-scroll-id']

    if create_index:
        create_elastic_index(es_connection, INDEX_NAME)

    prepare_data_and_load_to_index(es_connection, 
                                   json.loads(start_response.text)['results'],
                                   index_name)

    while True:
        start_time = time.time()

        next_scroll_response_raw = continue_scroll_elastic_requests(
                sp_vars, access_token, date, scroll_id, filter_comp
            )
        next_scroll_response_text = json.loads(next_scroll_response_raw.text)

        try:
            next_scroll_results = next_scroll_response_text['results']
        except:
            print(next_scroll_response_text)
            break
        prepare_data_and_load_to_index(es_connection, next_scroll_results, index_name)
        
        print(f"---{time.time() - start_time} seconds ---")

        if not next_scroll_results:
            break


if __name__ == '__main__':
    smartpath_data_to_elastic_stm(
        sp_vars,
        "2022-07-12T10:00:00",
        limit=500,
        index_name=INDEX_NAME, 
        create_index=False, 
        filter_comp=True
    )
