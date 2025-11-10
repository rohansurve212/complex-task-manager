import sys
import os
import unittest
import pandas as pd
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GetWorkFlow')))
from search_requests_utils import filter_static

class TestFilterStatic(unittest.TestCase):
    @patch('search_requests_utils.pre_process', return_value=['foo'])
    @patch('search_requests_utils.to_get_match')
    def test_filter_static(self, mock_to_get_match, mock_pre_process):
        df = pd.DataFrame({
            'source_businessUnit': ['wireless', 'other'],
            'workOrder_assignee_id': ['nan', 'nan'],
            'workOrder_status': ['new', 'customerreplied'],
            'workOrder_tags': [['LOCKED'], ['NEW_INTERNAL_NOTE']],
            'workOrder_product': ['p1', 'p2'],
            'source_product': ['sp1', 'sp2'],
            'source_serviceRegion': ['r1', 'r2'],
            'source_requestType': ['t1', 't2'],
            'source_goldenCustomer_id': ['nan', 'nan'],
            'source_requestSource': ['s1', 's2'],
            'workOrder_followUpDate': [
                pd.Timestamp('2025-01-01T00:00:00', tz='UTC'),
                pd.Timestamp('2025-01-02T00:00:00', tz='UTC')
            ],
        })
        tenant = 'wireless'
        permissions = ['foo']
        all_absent_agent_ids = []
        mock_to_get_match.return_value = df
        result = filter_static(df, tenant, permissions, all_absent_agent_ids)
        self.assertTrue(isinstance(result, pd.DataFrame))
        self.assertEqual(len(result), 2)

if __name__ == '__main__':
    unittest.main()
