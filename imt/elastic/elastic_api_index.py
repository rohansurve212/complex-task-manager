import os
import time
import pyodbc
from elasticsearch import Elasticsearch, helpers
import pandas as pd
import json
import requests
from datetime import datetime, timedelta, timezone
from Elastic.elastic_api_index import smarttask_api_search_request
from elastic_utils import (
    initialize_elastic_connection,
    get_service_user_OC_token,
    prepare_data_and_load_to_index
)
import sys

# Add the parent directory to sys.path to allow importing modules
syspath = sys.path.append(os.path.abspath(os.path.dirname(
                                    os.path.dirname(__file__)
                                    )
                                ))
print(sys.path)

from shared.db import DB
from elastic_settings import (
    all_cols,
    nested_cols,
    INDEX_NAME,
    mappings,
    make_request_body,
    get_auth_header
)

import logging
from logging.handlers import TimedRotatingFileHandler
import warnings

# Suppress specific warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Initialize loggers for Elastic and Cron
elasticLogger = logging.getLogger("Elastic log")
cronLogger = logging.getLogger("Cron log")
elasticLogger.setLevel(logging.INFO)
cronLogger.setLevel(logging.INFO)

# Setup file handlers for log rotation (daily at midnight, retaining 5 backups)
elasticHandler = TimedRotatingFileHandler('home/aiml/assets/stm/imt/elastic/log/elastic.log',when="midnight",interval=1,backupCount=5)
# elasticHandler = logging.StreamHandler(sys.stdout)
cronHandler = TimedRotatingFileHandler('home/aiml/assets/stm/imt/elastic/log/cron.log',when="midnight",interval=1,backupCount=5)
# cronHandler = logging.StreamHandler(sys.stdout)

# Define log message format
formatter = logging.Formatter('%(asctime)s - %(message)s')
elasticHandler.setFormatter(formatter)
cronHandler.setFormatter(formatter)

# Attach handlers to loggers
elasticLogger.addHandler(elasticHandler)
cronLogger.addHandler(cronHandler)

elasticLogger.info(f"SYS PATH -------> {syspath}")
cronLogger.info("CRON LOGS")

from shared.all_envs import sp_vars

def start_scroll_elastic_requests(sp_vars, auth_header, date, limit=10_000, filter_comp=False):
    """Start an Elasticsearch scroll request to fetch data in batches."""

    url = f"{sp_vars.base_url}/smartpath/smarttask/order/_startScroll?offset=0&limit={limit}&fields="
    
    # Prepare payload dynamically based on the provided date
    payload = json.dumps(make_request_body(date=date, filter_comp=filter_comp))
    print("PAYLOAD MAIN------->", payload)
    print("URL START SCROLL ----------------------------------------->", url)
    elasticLogger.info(f"payload -------> {payload}")
    headers = get_auth_header(auth_header)

    # Proxy settings (if any)
    proxies = {
            "http": None,
            "https": None
        }
    post_request = requests.post(url=url, headers=headers, data=payload, proxies=proxies, verify=False)
    # print("response_text -------------------------------------------------------------------------------->", post_request.text)

    return post_request

def create_elastic_index(es_connection, index_name):
    """Create a new index in Elasticsearch with the given mappings."""
    es_connection.indices.create(index=index_name, body=mappings)
    print("CREATE ELASTIC INDEX DONE ------------------------------->")

def get_results_from_smartpath_api(sp_vars, date, limit=500, filter_comp=False):
    """Fetch results from the SmartPath API."""

    service_token = get_service_user_OC_token(sp_vars)
    access_token = json.loads(service_token.text)['access_token']
    r = smarttask_api_search_request(sp_vars, access_token, date, limit, filter_comp)
    # print('CONTENT', r.content)
    r_dict = json.loads(r.text)

    # Raise error if metadata is missing
    if 'metadata' not in r_dict.keys():
        raise KeyError
    meta_data = r_dict['metadata']
    return r_dict['results']

def continue_scroll_elastic_requests(sp_vars, auth_header, date, scroll_id, filter_comp):
    """Continue the Elasticsearch scroll request using the scroll ID."""

    url = f"{sp_vars.base_url}/smartpath/smarttask/order/_continueScroll?scrollId={scroll_id}"

    # Prepare payload dynamically based on the provided date
    payload = json.dumps(make_request_body(date=date, filter_comp=filter_comp))
    headers = get_auth_header(auth_header)

    # Proxy settings (if any)
    proxies = {
            "http": None,
            "https": None
        }
    print("PAYLOAD CONTINUE SCROLL--------------->", payload)
    elasticLogger.info(f"PAYLOAD CONTINUE SCROLL---------------> {payload}")
    return requests.request("POST", url, headers=headers, data=payload, proxies=proxies, verify=False)

def smartpath_data_to_elastic_stm(sp_vars, date, limit=500, index_name=INDEX_NAME, create_index=False, filter_comp=False):
    """Fetch data from SmartPath and load it into an Elasticsearch index."""

    # Establish a connection to Elasticsearch
    es_connection = initialize_elastic_connection()

    # Fetch access token for the API
    service_token = get_service_user_OC_token(sp_vars)
    access_token = json.loads(service_token.text)['access_token']
    print("ACCESS TOKEN ------------------------------------------------------->", access_token)
    
    # Start the scroll request
    response = start_scroll_elastic_requests(sp_vars, access_token, date, limit, filter_comp)
    # print('Start Respose Headers', start_response.headers)
    _print_request_ids(response)

    # Extract scroll ID from response headers
    scroll_id = response.headers['x-scroll-id']
    print(f"({datetime.now()}) reading scroll_id: ----------------------------------------------------->", scroll_id)
    
    # Create the index if specified
    if create_index:
        create_elastic_index(es_connection, index_name)

    # Load initial data to the index
    prepare_data_and_load_to_index(es_connection, 
                                   json.loads(response.text)['results'],
                                   index_name)

    # Fetch remaining data in scrolls
    while True:
        start_time = time.time()

        # scroll_id = response.headers['x-scroll-id']
        print(f"({datetime.now()}) reading scroll_id: ----------------------------------------------------->", scroll_id)
        response = continue_scroll_elastic_requests(
                sp_vars, access_token, date, scroll_id, filter_comp
            )
        _print_request_ids(response)
        scroll_id = response.headers['x-scroll-id']
        next_scroll_response_text = json.loads(response.text)
        try:
            # Fetch results from the current scroll
            next_scroll_results = next_scroll_response_text['results']
            # next_scroll_response_total.update(next_scroll_results)
        except:
            # Exit loop if no results are fetched
            print("Failed to get scroll response text -------------------------------------------------------------------------->")
            break
        prepare_data_and_load_to_index(es_connection, next_scroll_results, index_name)
        
        print(f"---{time.time() - start_time} seconds ---")

        if not next_scroll_results:
            break

def _print_request_ids(response):
    # print("RESPONSE -------------------------------->", response)
    """Helper function to print request IDs and metadata."""
    results = json.loads(response.text)['results']
    # print("RESPONSE -------------------------------->", results)
    count = 0
    for result in results:
        id = result['id']
        lastUpdated = result['lastUpdated']
        status = result['source']['status']
        if 'assignee' in result['workOrder'].keys():
            assignee = result['workOrder']['assignee']['id']
        else:
            assignee = "No assignee"
        count = count + 1
        # print(f'{id}, lastUpdated={lastUpdated}, status={status}, assignee={assignee}')
    print(f"--- Received {count} requests in this scroll at ({datetime.now()}) ---")
    print(f"--------")

if __name__ == '__main__':
    # Measure the execution time of the script
    start_time = time.time()
    smartpath_data_to_elastic_stm(
        sp_vars,
        date="2022-03-20T14:21:30",  #(datetime.now(timezone.utc) - timedelta(seconds=4)).strftime('%Y-%m-%dT%H:%M:%S'),  # "2022-03-20T14:21:30",
        limit=500,
        index_name=INDEX_NAME, 
        create_index=False,
        filter_comp=False
    )
    end_time = time.time()
    print(f"Time taken for smartpath_data_to_elastic_stm(): {end_time - start_time} seconds")