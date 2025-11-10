import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from unittest.mock import patch, MagicMock
from elastic_api_index import smartpath_data_to_elastic_stm

class TestSmartpathDataToElasticStm(unittest.TestCase):
    @patch('elastic_api_index.load_data_to_index')
    @patch('elastic_api_index.create_elastic_index')
    @patch('elastic_api_index.initialize_elastic_connection')
    @patch('elastic_api_index.prepare_data_for_elastic')
    @patch('elastic_api_index.get_results_from_smartpath_api')
    def test_create_index_true(self, mock_get_results, mock_prepare, mock_init, mock_create, mock_load):
        sp_vars = MagicMock()
        mock_get_results.return_value = [1]
        mock_prepare.return_value = [{'foo': 'bar'}]
        mock_init.return_value = 'es_conn'
        smartpath_data_to_elastic_stm(sp_vars, '2024-01-01', create_index=True)
        mock_create.assert_called_once()
        mock_load.assert_called_once()

    @patch('elastic_api_index.load_data_to_index')
    @patch('elastic_api_index.create_elastic_index')
    @patch('elastic_api_index.initialize_elastic_connection')
    @patch('elastic_api_index.prepare_data_for_elastic')
    @patch('elastic_api_index.get_results_from_smartpath_api')
    def test_create_index_false(self, mock_get_results, mock_prepare, mock_init, mock_create, mock_load):
        sp_vars = MagicMock()
        mock_get_results.return_value = [1]
        mock_prepare.return_value = [{'foo': 'bar'}]
        mock_init.return_value = 'es_conn'
        smartpath_data_to_elastic_stm(sp_vars, '2024-01-01', create_index=False)
        mock_create.assert_not_called()
        mock_load.assert_called_once()

    @patch('elastic_api_index.load_data_to_index', side_effect=Exception('fail'))
    @patch('elastic_api_index.create_elastic_index')
    @patch('elastic_api_index.initialize_elastic_connection')
    @patch('elastic_api_index.prepare_data_for_elastic')
    @patch('elastic_api_index.get_results_from_smartpath_api')
    def test_error_in_load(self, mock_get_results, mock_prepare, mock_init, mock_create, mock_load):
        sp_vars = MagicMock()
        mock_get_results.return_value = [1]
        mock_prepare.return_value = [{'foo': 'bar'}]
        mock_init.return_value = 'es_conn'
        with self.assertRaises(Exception):
            smartpath_data_to_elastic_stm(sp_vars, '2024-01-01', create_index=False)

if __name__ == '__main__':
    unittest.main()
