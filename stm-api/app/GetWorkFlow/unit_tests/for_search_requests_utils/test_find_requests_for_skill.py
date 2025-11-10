import sys
import os
import unittest
import pandas as pd
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GetWorkFlow')))
from search_requests_utils import find_requests_for_skill

class TestFindRequestsForSkill(unittest.TestCase):
    @patch('search_requests_utils.logger')
    def test_find_requests_for_skill(self, mock_logger):
        df = pd.DataFrame({
            'source_requestSource': ['foo', 'bar'],
            'workOrder_product': ['p1', 'p2'],
            'source_serviceRegion': ['r1', 'r2'],
            'source_customerSupportModel': ['c1', 'c2'],
            'workOrder_controlDesk': ['cd1', 'cd2'],
            'source_goldenCustomer_id': ['g1', 'g2'],
            'source_customerMarketSegment': ['cms1', 'cms2'],
            'source_preferredLanguage': ['en', 'fr'],
            'source_requestType': ['type1', 'type2']
        })
        skill_configuration = {
            'requestSource': ['foo'],
            'product': ['p1'],
            'serviceRegion': ['r1'],
            'customerSupportModel': ['c1'],
            'controlDesk': ['cd1'],
            'goldenCustomer': ['g1'],
            'customerMarketSegment': ['cms1'],
            'preferredlanguage': ['en'],
            'requestType': ['type1'],
            'skill_id': 'id',
            'skill_name': 'name',
            'skill_priority': 1,
            'tag': 'tag'
        }
        result = find_requests_for_skill(df, skill_configuration)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['source_requestSource'], 'foo')

    def test_find_requests_for_skill_empty(self):
        df = pd.DataFrame({
            'source_requestSource': ['foo'],
            'workOrder_product': ['p1'],
            'source_serviceRegion': ['r1'],
            'source_customerSupportModel': ['c1'],
            'workOrder_controlDesk': ['cd1'],
            'source_goldenCustomer_id': ['g1'],
            'source_customerMarketSegment': ['cms1'],
            'source_preferredLanguage': ['en'],
            'source_requestType': ['type1']
        })
        skill_configuration = {
            'requestSource': ['bar'],
            'product': ['p2'],
            'serviceRegion': ['r2'],
            'customerSupportModel': ['c2'],
            'controlDesk': ['cd2'],
            'goldenCustomer': ['g2'],
            'customerMarketSegment': ['cms2'],
            'preferredlanguage': ['fr'],
            'requestType': ['type2'],
            'skill_id': 'id',
            'skill_name': 'name',
            'skill_priority': 1,
            'tag': 'tag'
        }
        result = find_requests_for_skill(df, skill_configuration)
        self.assertEqual(len(result), 0)

if __name__ == '__main__':
    unittest.main()
