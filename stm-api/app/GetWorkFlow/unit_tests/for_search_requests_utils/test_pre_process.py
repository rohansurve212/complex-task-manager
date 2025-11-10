import sys
import os
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GetWorkFlow')))
from search_requests_utils import pre_process

class TestPreProcess(unittest.TestCase):
    def test_pre_process(self):
        perms = ['OC-SmartPath-GoC-Level2', 'OC-SmartPath-Retail', 'OC-SmartPath-BBM', 'OC-SmartPath-TrunkSide']
        expected = ['goclevel2', 'retail', 'bbm', 'trunkside']
        self.assertEqual(pre_process(perms), expected)
        self.assertEqual(pre_process(['foo']), ['foo'])
    def test_pre_process_empty(self):
        self.assertEqual(pre_process([]), [])

if __name__ == '__main__':
    unittest.main()
