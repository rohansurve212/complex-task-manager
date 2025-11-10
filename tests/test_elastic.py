import os
import sys
import json
sys.path.append(os.path.abspath(os.path.dirname(
                                    os.path.dirname(__file__)
                                    )))

from Elastic.elastic_settings import (
    all_cols,
    INDEX_NAME,
)
from Elastic.elastic_api_index import (
    get_results_from_smartpath_api,
    prepare_data_for_elastic,
    initialize_elastic_connection,
)
import unittest

INDEX_NAME = 'bbm_aiml_stm_test'


class TestRequestFromElastic(unittest.TestCase):
    
    def setUp(self):
        f = open('dummy_smartpath_response.json')
        r_dict = json.load(f)

        self.df_dict = prepare_data_for_elastic(r_dict['results'], all_cols)
        self.es = initialize_elastic_connection()
        
        for i, my_dict in enumerate(self.df_dict):
            self.es.index(
                index = INDEX_NAME,
                id = f"elastic_test_doc_{i}",
                body = my_dict
            )

    def test_sp_query_limit(self):
        """Test that using a limit of 10001 creates an error"""
        with self.assertRaises(KeyError):
            get_results_from_smartpath_api("2022-04-11T14:21:30", limit=10_001)
            

    def test_if_docs_exist(self):
        """test that the docs added in setUp have a request_id and a source key"""
        for i in range(len(self.df_dict)):
            doc = self.es.get(index=INDEX_NAME, id=f"elastic_test_doc_{i}")
            
            self.assertTrue(doc)
            self.assertTrue('request_id' in doc['_source'].keys())
            self.assertTrue('source' in doc['_source'].keys())


    def test_query_new_docs(self):
        """Test that querying the created docs returns the same amount of docs that were in the json file"""
        test_data = {  "query": { "bool": { "filter": [{
                "ids": {"values": ["elastic_test_doc_0", "elastic_test_doc_1"]
            }}]}}}
            
        resp = self.es.search(index=INDEX_NAME, body=test_data)
        self.assertEqual(len(resp['hits']['hits']), len(self.df_dict))

    def tearDown(self):
        for i in range(len(self.df_dict)):
            self.es.delete(index=INDEX_NAME, id=f"elastic_test_doc_{i}")


if __name__ == '__main__':
    unittest.main()