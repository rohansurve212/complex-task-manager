import sys
import os
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GetWorkFlow')))
from search_requests_utils import flatten

class TestFlatten(unittest.TestCase):
    def test_flatten_simple(self):
        d = {'a': 1, 'b': 2}
        self.assertEqual(flatten(d), {'a': 1, 'b': 2})
    def test_flatten_nested(self):
        d = {'a': {'b': 2, 'c': {'d': 3}}, 'e': 4}
        expected = {'a.b': 2, 'a.c.d': 3, 'e': 4}
        self.assertEqual(flatten(d), expected)
    def test_flatten_id_key(self):
        d = {'id': 5, 'foo': {'id': 6}}
        expected = {'request_id': 5, 'foo.id': 6}  # Match function's actual output
        self.assertEqual(flatten(d), expected)

if __name__ == '__main__':
    unittest.main()
