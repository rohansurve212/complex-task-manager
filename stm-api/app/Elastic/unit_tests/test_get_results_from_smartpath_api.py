import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from unittest.mock import patch, MagicMock
from elastic_api_index import get_results_from_smartpath_api

class TestGetResultsFromSmartpathApi(unittest.TestCase):
    @patch('elastic_api_index.smarttask_api_search_request')
    @patch('elastic_api_index.get_service_user_OC_token')
    def test_normal(self, mock_token, mock_search):
        sp_vars = MagicMock()
        mock_token.return_value.text = '{"access_token": "tok"}'
        mock_search.return_value.text = '{"metadata": {"limit": 5, "totalRecordCount": 10}, "results": [1,2,3]}'
        out = get_results_from_smartpath_api(sp_vars, '2024-01-01')
        self.assertEqual(out, [1,2,3])

    @patch('elastic_api_index.smarttask_api_search_request')
    @patch('elastic_api_index.get_service_user_OC_token')
    def test_missing_metadata(self, mock_token, mock_search):
        sp_vars = MagicMock()
        mock_token.return_value.text = '{"access_token": "tok"}'
        mock_search.return_value.text = '{"results": [1,2,3]}'
        with self.assertRaises(KeyError):
            get_results_from_smartpath_api(sp_vars, '2024-01-01')

    @patch('elastic_api_index.smarttask_api_search_request')
    @patch('elastic_api_index.get_service_user_OC_token')
    def test_missing_access_token(self, mock_token, mock_search):
        sp_vars = MagicMock()
        mock_token.return_value.text = '{}'
        mock_search.return_value.text = '{"metadata": {"limit": 5, "totalRecordCount": 10}, "results": [1,2,3]}'
        with self.assertRaises(KeyError):
            get_results_from_smartpath_api(sp_vars, '2024-01-01')

    @patch('elastic_api_index.smarttask_api_search_request', side_effect=Exception('fail'))
    @patch('elastic_api_index.get_service_user_OC_token')
    def test_api_error(self, mock_token, mock_search):
        sp_vars = MagicMock()
        mock_token.return_value.text = '{"access_token": "tok"}'
        with self.assertRaises(Exception):
            get_results_from_smartpath_api(sp_vars, '2024-01-01')

if __name__ == '__main__':
    unittest.main()
