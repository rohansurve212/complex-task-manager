import sys
import os
import datetime
# Add the parent of 'for_routing' (i.e., the directory containing routing.py) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import unittest
from routing import time_difference

class TestTimeDifference(unittest.TestCase):
    def test_now(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertAlmostEqual(time_difference(now), 0, delta=0.01)

    def test_past(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        past = now - datetime.timedelta(minutes=10)
        self.assertAlmostEqual(time_difference(past), 10, delta=0.1)

    def test_future(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        future = now + datetime.timedelta(minutes=5)
        self.assertAlmostEqual(time_difference(future), -5, delta=0.1)

if __name__ == '__main__':
    unittest.main()
