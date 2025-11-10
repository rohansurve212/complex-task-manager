import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from unittest.mock import MagicMock
from elastic_api_index import create_elastic_index

class TestCreateElasticIndex(unittest.TestCase):
    def test_create_called_with_correct_args(self):
        es_connection = MagicMock()
        create_elastic_index(es_connection, 'my-index')
        es_connection.indices.create.assert_called_once()
        args, kwargs = es_connection.indices.create.call_args
        self.assertEqual(kwargs['index'], 'my-index')
        self.assertIn('body', kwargs)

if __name__ == '__main__':
    unittest.main()
