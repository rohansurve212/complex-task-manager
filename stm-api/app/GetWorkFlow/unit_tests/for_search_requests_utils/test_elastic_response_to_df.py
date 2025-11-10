import sys
import os
import unittest
import pandas as pd
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GetWorkFlow')))
from search_requests_utils import elastic_response_to_df

class TestElasticResponseToDf(unittest.TestCase):
    @patch('search_requests_utils.format_df_for_search')
    def test_elastic_response_to_df(self, mock_format):
        mock_format.return_value = pd.DataFrame({'accessPolicyTag': [['foo']], 'score': [1]})
        response = [{'a': 1, 'b': {'c': 2}}]
        query_fields = ['a', 'b.c']
        result = elastic_response_to_df(response, query_fields)
        self.assertTrue(isinstance(result, pd.DataFrame))
        self.assertIn('accessPolicyTag', result.columns)

if __name__ == '__main__':
    unittest.main()
