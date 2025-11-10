import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from elastic_api_index import nested_col_nans_to_dict

class TestNestedColNansToDict(unittest.TestCase):
    def test_empty_results(self):
        self.assertEqual(nested_col_nans_to_dict([], ['a']), [])

    def test_missing_nested_col(self):
        results = [{'foo': 1}]
        expected = [{'foo': 1, 'bar': {'value': 'no-data'}}]
        out = nested_col_nans_to_dict([{'foo': 1}], ['bar'])
        self.assertEqual(out, expected)

    def test_all_nested_cols_present(self):
        results = [{'foo': 1, 'bar': {'value': 2}}]
        out = nested_col_nans_to_dict(results, ['bar'])
        self.assertEqual(out, results)

    def test_multiple_results_and_cols(self):
        results = [{'foo': 1}, {'bar': {'value': 2}}]
        expected = [
            {'foo': 1, 'bar': {'value': 'no-data'}},
            {'bar': {'value': 2}}
        ]
        out = nested_col_nans_to_dict([{'foo': 1}, {'bar': {'value': 2}}], ['bar'])
        self.assertEqual(out, expected)

    def test_multiple_nested_cols(self):
        results = [{'foo': 1}]
        expected = [{'foo': 1, 'bar': {'value': 'no-data'}, 'baz': {'value': 'no-data'}}]
        out = nested_col_nans_to_dict([{'foo': 1}], ['bar', 'baz'])
        self.assertEqual(out, expected)

    def test_no_nested_cols(self):
        results = [{'foo': 1}]
        expected = [{'foo': 1}]
        out = nested_col_nans_to_dict([{'foo': 1}], [])
        self.assertEqual(out, expected)

if __name__ == '__main__':
    unittest.main()
