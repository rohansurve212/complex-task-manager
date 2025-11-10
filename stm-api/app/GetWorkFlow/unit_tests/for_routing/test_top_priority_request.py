import sys
import os
import datetime
import pandas as pd
# Add the parent of 'for_routing' (i.e., the directory containing routing.py) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import unittest
from routing import top_priority_request

class TestTopPriorityRequest(unittest.TestCase):
    def test_top_priority(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        df = pd.DataFrame([
            {'requestOrderDate': now - datetime.timedelta(minutes=10), 'focTarget': 1},
            {'requestOrderDate': now - datetime.timedelta(minutes=20), 'focTarget': 2},
            {'requestOrderDate': now - datetime.timedelta(minutes=30), 'focTarget': 3},
        ])
        top = top_priority_request(df)
        self.assertIn('focTarget', top)
        self.assertTrue(top['score'] >= 0)

    def test_empty_dataframe(self):
        df = pd.DataFrame([])
        with self.assertRaises(ValueError):
            top_priority_request(df)

if __name__ == '__main__':
    unittest.main()
