# Import necessary modules
import time
import json
import logging
from typing import Dict

import numbers
import numpy as np
import pandas as pd
from elasticsearch import Elasticsearch

# Import custom environment variable classes
from utils.envs.env_variable import EnvVariable, EnvironmentType

# Class to manage Elasticsearch operations
class EsManagement:
    es_client: Elasticsearch
    _env_var: EnvVariable
    
    # Initialize the Elasticsearch client with environment variables
    def __init__(self, env_var: EnvVariable):
        self._env_var = env_var
        
        self.es_client = Elasticsearch(
            [env_var.get_variable("WHITESPACE_ELASTICSEARCH_HOST")],
            verify_certs = False,
            http_auth=(env_var.get_variable("WHITESPACE_ELASTICSEARCH_ACCESS_KEY"), env_var.get_variable("WHITESPACE_ELASTICSEARCH_ACCESS_SECRET"))
        )
        logging.info(self.es_client.ping())

    # Method to get the index name based on the environment type
    def _get_index_name(self, index_name: str) -> str:
        if self._env_var.get_environment_type() == EnvironmentType.Prod:
            return f'{index_name}_prod'
        return index_name
    
    # Method to create an Elasticsearch index
    def create_index(self, index_name: str, mapping: Dict):
        """
        Create an ES index.
        :param index_name: Name of the index.
        :param mapping: Mapping of the index
        """
        
        index_name = self._get_index_name(index_name)
        logging.info(f"Creating index {index_name} with the following schema: {json.dumps(mapping, indent=2)}")
        self.es_client.indices.create(index=index_name, ignore=400, body=mapping)
        
        # Validate if the index is created successfully
        return self.es_client.indices.get_mapping(index=index_name)

    # Method to get search results as a DataFrame
    def get_as_dataframe(self, index_name: str, query, scroll_timeout='2s', print_log=False) -> pd.DataFrame:
        from pandas import json_normalize

        import warnings
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")

        index_name = self._get_index_name(index_name)
        resp = self.es_client.search(
            index=index_name, 
            body=query,
            scroll=scroll_timeout
        )
        all_docs = pd.DataFrame()
        total_docs = resp["hits"]["total"]["value"]
        print('total_docs:', total_docs)

        # keep track of pass scroll _id
        old_scroll_id = resp['_scroll_id']
        if print_log:
            print("FIRST SCROLL ID:", resp['_scroll_id'])

        # use a 'while' iterator to loop over document 'hits'
        while len(resp['hits']['hits']):
            
            df = json_normalize(resp['hits']['hits'])
            all_docs = pd.concat([all_docs, df])
            
            if print_log:
                total = len(all_docs)
                print(f'{total}/{total_docs}')
            
            # make a request using the Scroll API
            resp = self.es_client.scroll(
                scroll_id=old_scroll_id,
                scroll=scroll_timeout # length of time to keep search context
            )

            # check if there's a new scroll ID
            if print_log and old_scroll_id != resp['_scroll_id']:
                print("NEW SCROLL ID:", resp['_scroll_id'])

            # keep track of pass scroll _id
            old_scroll_id = resp['_scroll_id']

        return all_docs

    # Method to get aggregation results as a DataFrame
    def get_aggegation_as_dataframe(self, index_name: str, query) -> pd.DataFrame:
        from pandas import json_normalize

        import warnings
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")

        index_name = self._get_index_name(index_name)
        resp = self.es_client.search(
            index=index_name, 
            body=query,
        )
        
        df = json_normalize(resp['aggregations']['0']['buckets'])
        return df

    # Method to populate an index from a CSV file
    def populate_index(self, path: str, index_name: str) -> None:
        """
        Populate an index from a CSV file.
        :param path: The path to the CSV file.
        :param index_name: Name of the index to which documents should be written.
        """
        
        index_name = self._get_index_name(index_name)
        df = pd.read_csv(path).replace({np.nan: None})
        logging.info(f"Writing {len(df.index)} documents to ES index {index_name}")
        for doc in df.apply(lambda x: x.to_dict(), axis=1):
            self.es_client.index(index=index_name, body=json.dumps(doc))
    
    # Method to insert a single document into an index
    def insert_document(self, index_name: str, document: dict) -> None:
        index_name = self._get_index_name(index_name)
        
        id = None
        if '_id' in document:
            id = document['_id']
            del document['_id']
        
        print(f"Writing a document to ES index {index_name}")
        self.es_client.index(index=index_name, body=json.dumps(document), id=id)

    # Method to insert multiple documents into an index in bulk
    def insert_documents(self, index_name: str, documents: list, id_field: str, index_name_func: bool = False, batch_size: int = 10000, timeout='5m') -> None:
        if index_name_func:
            index_name = self._get_index_name(index_name)
        
        for i in range(0, len(documents), batch_size):
            print(f'Elastic bulk insert [{i}: {i+batch_size}] into index {index_name}')
            actions = []
            for doc in documents[i: i+batch_size]:
                action = {"index": {"_index": index_name, "_id": doc[id_field]}}
                actions.append(action)
                actions.append(doc)

            self._bulk(index_name, actions, timeout)

    # Method to update multiple documents in an index in bulk
    def update_documents(self, index_name: str, documents: list, id_field: str, batch_size: int = 10000, exclude_nan = False, timeout='5m') -> None:
        index_name = self._get_index_name(index_name)
        
        for i in range(0, len(documents), batch_size):
            print(f'Elastic bulk update [{i}: {i+batch_size}] into index {index_name}')
            actions = []
            for doc in documents[i: i+batch_size]:
                action = {"update": {"_index": index_name, "_id": doc[id_field]}}
                actions.append(action)
                
                if exclude_nan:
                    for k in list(doc.keys()):
                        if isinstance(doc[k], numbers.Number) and np.isnan(doc[k]):
                            del doc[k]
                
                actions.append({"doc": doc})

        self._bulk(index_name, actions, timeout)

    # Method to check if a document exists in an index
    def document_exists(self, index_name, doc_id):
        # Check if a document with the specified ID exists in the index
        response = self.es_client.exists(index=index_name, id=doc_id)
        return response

    # Helper method to perform bulk operations
    def _bulk(self, index_name: str, actions, timeout: str):
        max_retry = 3
        retry = 0
        success = False
        retry_delay = [0, 5, 10, 30]
        
        while not success and retry <= max_retry:
            try:
                self.es_client.bulk(index=index_name, operations=actions, timeout=timeout)
                success = True

            except Exception as ex:
                if str(ex) == 'Connection timed out':
                    retry += 1
                    if retry <= max_retry:
                        print(f'Request timed out. Retry #{retry} will occur in {retry_delay[retry]} sec.')
                        time.sleep(retry_delay[retry]) 
                    else:
                        print(f'Request timed out. Maximum number of retry ({retry}) reached.')
                        raise
                else:
                    print(f'Crashing with error : ' + str(ex))
                    raise

