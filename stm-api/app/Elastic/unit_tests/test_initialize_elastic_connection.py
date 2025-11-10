import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch
from elastic_api_index import initialize_elastic_connection

class TestInitializeElasticConnection(unittest.TestCase):
    @patch('elastic_api_index.Elasticsearch')
    @patch('elastic_api_index.ELASTIC_SERVER', 'server')
    @patch('elastic_api_index.ELASTIC_USER', 'user')
    @patch('elastic_api_index.ELASTIC_PASS', 'pass')
    def test_connection_created(self, mock_es):
        initialize_elastic_connection()
        mock_es.assert_called_once_with('server', verify_certs=False, http_auth=('user', 'pass'))

if __name__ == '__main__':
    unittest.main()
