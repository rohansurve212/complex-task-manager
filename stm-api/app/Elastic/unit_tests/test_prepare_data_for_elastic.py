import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock

from elastic_api_index import prepare_data_for_elastic

class TestPrepareDataForElastic(unittest.TestCase):
    @patch('elastic_api_index.nested_col_nans_to_dict')
    @patch('elastic_api_index.get_foc_target')
    @patch('elastic_api_index.pd.DataFrame')
    @patch('elastic_api_index.pyodbc.connect')
    def test_prepare_data_normal(self, mock_connect, mock_df, mock_get_foc_target, mock_nested_col_nans_to_dict):
        mock_nested_col_nans_to_dict.side_effect = lambda results, nested_cols: results
        mock_get_foc_target.return_value = 42
        mock_con = MagicMock()
        mock_connect.return_value = mock_con
        mock_cur = MagicMock()
        mock_con.cursor.return_value = mock_cur
        mock_df_inst = MagicMock()
        mock_df.return_value = mock_df_inst
        mock_df_inst.fillna.return_value = mock_df_inst
        mock_df_inst.to_dict.return_value = [{'source': {'focTarget': 42}, 'request_id': 1}]
        results = [{'source': {}, 'id': 1}]
        all_cols = ['source', 'request_id']
        out = prepare_data_for_elastic(results, all_cols)
        self.assertEqual(out, [{'source': {'focTarget': 42}, 'request_id': 1}])

    @patch('elastic_api_index.nested_col_nans_to_dict', side_effect=lambda results, nested_cols: results)
    @patch('elastic_api_index.get_foc_target', return_value=0)
    @patch('elastic_api_index.pd.DataFrame')
    @patch('elastic_api_index.pyodbc.connect')
    def test_empty_results(self, mock_connect, mock_df, mock_get_foc_target, mock_nested_col_nans_to_dict):
        mock_con = MagicMock()
        mock_connect.return_value = mock_con
        mock_cur = MagicMock()
        mock_con.cursor.return_value = mock_cur
        mock_df_inst = MagicMock()
        mock_df.return_value = mock_df_inst
        mock_df_inst.fillna.return_value = mock_df_inst
        mock_df_inst.to_dict.return_value = []
        results = []
        all_cols = ['source', 'request_id']
        out = prepare_data_for_elastic(results, all_cols)
        self.assertEqual(out, [])

if __name__ == '__main__':
    unittest.main()
