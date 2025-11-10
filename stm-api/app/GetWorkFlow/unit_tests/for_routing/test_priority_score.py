import sys
import os
# Add the parent of 'for_routing' (i.e., the directory containing routing.py) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import datetime
import unittest
from unittest.mock import patch
from routing import priority_score

class TestPriorityScore(unittest.TestCase):
    @patch('routing.time_difference')
    def test_positive_foc_target(self, mock_time_diff):
        mock_time_diff.return_value = 20
        row = {'requestOrderDate': datetime.datetime.now(), 'focTarget': 10}
        self.assertEqual(priority_score(row), 2)

    @patch('routing.time_difference')
    @patch('routing.DEFAULT_TTPU', 5)
    def test_zero_foc_target(self, mock_time_diff):
        mock_time_diff.return_value = 10
        row = {'requestOrderDate': datetime.datetime.now(), 'focTarget': 0}
        self.assertEqual(priority_score(row), 2)

if __name__ == '__main__':
    unittest.main()
