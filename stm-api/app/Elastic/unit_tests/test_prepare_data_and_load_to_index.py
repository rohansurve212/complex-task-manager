import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from unittest.mock import patch, MagicMock
from initialize_elastic_index import prepare_data_and_load_to_index

class TestPrepareDataAndLoadToIndex(unittest.TestCase):
    @patch('initialize_elastic_index.prepare_data_for_elastic')
    @patch('initialize_elastic_index.load_data_to_index')
    def test_prepare_and_load(self, mock_load, mock_prepare):
        es_connection = MagicMock()
        results = [{'foo': 'bar'}]
        mock_prepare.return_value = [{'bar': 'baz'}]
        prepare_data_and_load_to_index(es_connection, results, 'test-index')
        mock_prepare.assert_called_once_with(results, mock_prepare.call_args[0][1])
        mock_load.assert_called_once()

if __name__ == '__main__':
    unittest.main()
