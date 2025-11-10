import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from elastic_api_index import elastic_data_generator

class TestElasticDataGenerator(unittest.TestCase):
    def test_yields_correct_dict(self):
        df = [
            {'request_id': 1, 'foo': 'bar'},
            {'request_id': 2, 'foo': 'baz'}
        ]
        cols = ['request_id', 'foo']
        index_name = 'test-index'
        gen = elastic_data_generator(df, cols, index_name)
        docs = list(gen)
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0]['_id'], 1)
        self.assertEqual(docs[0]['_index'], index_name)
        self.assertEqual(docs[0]['_source']['foo'], 'bar')
        self.assertEqual(docs[1]['_id'], 2)
        self.assertEqual(docs[1]['_source']['foo'], 'baz')

    def test_missing_keys(self):
        df = [{}]
        cols = ['request_id', 'foo']
        index_name = 'test-index'
        gen = elastic_data_generator(df, cols, index_name)
        doc = next(gen)
        self.assertEqual(doc['_id'], None)
        self.assertEqual(doc['_source']['foo'], ['No Data'])

if __name__ == '__main__':
    unittest.main()
