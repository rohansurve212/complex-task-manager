import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from unittest.mock import patch, MagicMock
from elastic_api_index import load_data_to_index

class TestLoadDataToIndex(unittest.TestCase):
    @patch('elastic_api_index.helpers.bulk')
    @patch('elastic_api_index.elastic_data_generator')
    def test_empty_dict(self, mock_gen, mock_bulk):
        es_connection = MagicMock()
        load_data_to_index(es_connection, [], ['foo'], 'index')
        mock_bulk.assert_not_called()
        mock_gen.assert_not_called()

    @patch('elastic_api_index.helpers.bulk')
    @patch('elastic_api_index.elastic_data_generator')
    def test_successful_bulk(self, mock_gen, mock_bulk):
        es_connection = MagicMock()
        mock_gen.return_value = iter([{'_id': 1}])
        load_data_to_index(es_connection, [{'foo': 'bar'}], ['foo'], 'index')
        mock_bulk.assert_called_once()
        mock_gen.assert_called_once()

    @patch('elastic_api_index.helpers.bulk', side_effect=Exception('fail'))
    @patch('elastic_api_index.elastic_data_generator')
    def test_bulk_exception(self, mock_gen, mock_bulk):
        es_connection = MagicMock()
        mock_gen.return_value = iter([{'_id': 1}])
        # Should not raise, just print
        load_data_to_index(es_connection, [{'foo': 'bar'}], ['foo'], 'index')
        mock_bulk.assert_called_once()
        mock_gen.assert_called_once()

if __name__ == '__main__':
    unittest.main()
