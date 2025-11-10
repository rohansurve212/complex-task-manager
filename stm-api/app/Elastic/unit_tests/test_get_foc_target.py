import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import MagicMock

from elastic_api_index import get_foc_target

class TestGetFocTarget(unittest.TestCase):
    def setUp(self):
        self.cur = MagicMock()
        self.res = {
            'source': {
                'requestSource': 'A',
                'product': 'B',
                'serviceRegion': 'C',
                'requestType': 'D'
            }
        }

    def test_all_keys_present_and_db_returns_value(self):
        self.cur.execute().fetchall.return_value = [[42]]
        self.assertEqual(get_foc_target(self.cur, self.res), 42)

    def test_all_keys_present_and_db_returns_none(self):
        self.cur.execute().fetchall.return_value = [[None]]
        self.assertIsNone(get_foc_target(self.cur, self.res))

    def test_db_returns_empty(self):
        self.cur.execute().fetchall.return_value = []
        self.assertEqual(get_foc_target(self.cur, self.res), 0)

    def test_missing_keys(self):
        res = {'source': {}}
        self.assertEqual(get_foc_target(self.cur, res), 0)

    def test_non_string_values(self):
        res = {'source': {'requestSource': None, 'product': None, 'serviceRegion': None, 'requestType': None}}
        with self.assertRaises(AttributeError):
            get_foc_target(self.cur, res)

if __name__ == '__main__':
    unittest.main()
