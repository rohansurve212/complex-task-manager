import sys
import os
import datetime
import pandas as pd
# Add the parent of 'for_routing' (i.e., the directory containing routing.py) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import unittest
from unittest.mock import patch, MagicMock
from routing import routing, priority_score, find_flow_id

class TestRouting(unittest.TestCase):
    @patch('routing.top_priority_request')
    def test_routing_with_data(self, mock_top):
        mock_top.return_value = {'requestId': '1', 'score': 10}
        df = pd.DataFrame([{'requestId': '1', 'score': 10}])
        result = routing(df)
        self.assertEqual(result, {'requestId': '1', 'score': 10})

    def test_routing_empty(self):
        df = pd.DataFrame([])
        self.assertIsNone(routing(df))

    def test_routing_identical_scores(self):
        now = datetime.datetime.now()
        df = pd.DataFrame([
            {'requestOrderDate': now, 'focTarget': 1, 'requestId': 'A'},
            {'requestOrderDate': now, 'focTarget': 1, 'requestId': 'B'}
        ])
        # Should return one of the rows, deterministic by idxmax (first occurrence)
        result = routing(df)
        self.assertIn(result['requestId'], ['A', 'B'])

    def test_priority_score_missing_requestOrderDate(self):
        row = {'focTarget': 10}
        with self.assertRaises(KeyError):
            priority_score(row)

    def test_priority_score_missing_focTarget(self):
        now = datetime.datetime.now()
        row = {'requestOrderDate': now}
        with self.assertRaises(KeyError):
            priority_score(row)

    def test_find_flow_id_missing_keys(self):
        con = MagicMock()
        con.cursor.return_value = MagicMock()
        # Missing 'requestSource', 'customerSupportModel', 'requestType', 'focTarget'
        request_dict = {}
        with self.assertRaises(KeyError):
            find_flow_id(con, request_dict)

if __name__ == '__main__':
    unittest.main()
