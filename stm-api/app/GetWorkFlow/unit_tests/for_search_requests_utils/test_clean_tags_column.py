import sys
import os
import unittest
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GetWorkFlow')))
from search_requests_utils import clean_tags_column

class TestCleanTagsColumn(unittest.TestCase):
    def test_clean_tags_column(self):
        df = pd.DataFrame({'accessPolicyTag': [['A_B', 'C'], ['D_E'], [None], ['F']]})
        result = clean_tags_column(df.copy())
        self.assertTrue(all(isinstance(tags, list) for tags in result['accessPolicyTag']))
        self.assertIn('b', result['accessPolicyTag'][0])
        self.assertIn('c', result['accessPolicyTag'][0])
        self.assertIn('e', result['accessPolicyTag'][1])
        self.assertEqual(result['accessPolicyTag'][2], [''])
        self.assertIn('f', result['accessPolicyTag'][3])

if __name__ == '__main__':
    unittest.main()
