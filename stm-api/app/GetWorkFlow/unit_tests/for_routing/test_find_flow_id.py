import sys
import os
# Add the parent of 'for_routing' (i.e., the directory containing routing.py) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import unittest
from unittest.mock import MagicMock, patch
from routing import find_flow_id

class TestFindFlowId(unittest.TestCase):
    @patch('routing.DB')
    def test_flow_id_found(self, mock_db):
        con = MagicMock()
        cur = MagicMock()
        con.cursor.return_value = cur
        cur.execute.return_value.fetchall.side_effect = [[(42,)], [(42,)]]
        mock_db.dim_flow.return_value = 'dim_flow'
        request_dict = {
            'requestSource': 'bcom',
            'customerSupportModel': 'non-standard',
            'requestType': 'inquiry',
            'focTarget': 1
        }
        flow_id = find_flow_id(con, request_dict)
        self.assertEqual(flow_id, 42)

    @patch('routing.DB')
    def test_flow_id_not_found(self, mock_db):
        con = MagicMock()
        cur = MagicMock()
        con.cursor.return_value = cur
        cur.execute.return_value.fetchall.side_effect = [[], []]
        mock_db.dim_flow.return_value = 'dim_flow'
        request_dict = {
            'requestSource': 'other',
            'customerSupportModel': 'other',
            'requestType': 'other',
            'focTarget': 0
        }
        flow_id = find_flow_id(con, request_dict)
        self.assertEqual(flow_id, 0)

if __name__ == '__main__':
    unittest.main()
