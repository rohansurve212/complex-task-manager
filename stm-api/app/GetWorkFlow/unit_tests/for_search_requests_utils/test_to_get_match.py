import sys
import os
import unittest
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GetWorkFlow')))
from search_requests_utils import to_get_match

class TestToGetMatch(unittest.TestCase):
    def test_to_get_match(self):
        df = pd.DataFrame({'accessPolicyTag': [['foo', 'bar'], ['baz']], 'other': [1, 2]})
        permis_list = ['foo', 'bar']
        result = to_get_match(df.copy(), permis_list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['accessPolicyTag'], ['foo', 'bar'])
    def test_to_get_match_no_match(self):
        df = pd.DataFrame({'accessPolicyTag': [['foo'], ['bar']], 'other': [1, 2]})
        permis_list = ['baz']
        result = to_get_match(df.copy(), permis_list)
        self.assertEqual(len(result), 0)

if __name__ == '__main__':
    unittest.main()
