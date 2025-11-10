import sys
import os
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GetWorkFlow')))
from search_requests_utils import clean_tags

class TestCleanTags(unittest.TestCase):
    def test_clean_tags_list(self):
        self.assertEqual(clean_tags(['A_B', 'C_D_E']), ['b', 'de'])
        self.assertEqual(clean_tags(['A']), ['a'])
        self.assertEqual(clean_tags([]), [''])
    def test_clean_tags_string(self):
        self.assertEqual(clean_tags('A_B'), ['b'])
        self.assertEqual(clean_tags('A'), ['a'])
    def test_clean_tags_empty(self):
        self.assertEqual(clean_tags([]), [''])

if __name__ == '__main__':
    unittest.main()
