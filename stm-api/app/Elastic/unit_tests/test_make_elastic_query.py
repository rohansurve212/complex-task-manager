import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from elastic_settings import make_elastic_query

class TestMakeElasticQuery(unittest.TestCase):
    def test_default_query_fields(self):
        date = '2024-01-01T00:00:00'
        query = make_elastic_query(date)
        self.assertIn('query', query)
        self.assertIn('fields', query)
        self.assertIsInstance(query['fields'], list)
        self.assertIn('request_id', query['fields'])
        self.assertIn('workOrder.tags', str(query))
        self.assertIn('lastUpdated', str(query))

    def test_custom_query_fields(self):
        date = '2024-01-01T00:00:00'
        fields = ['foo', 'bar']
        query = make_elastic_query(date, query_fields=fields)
        self.assertEqual(query['fields'], fields)

    def test_filter_comp_true(self):
        date = '2024-01-01T00:00:00'
        query = make_elastic_query(date, filter_comp=True)
        self.assertIn('must_not', query['query']['bool'])
        self.assertIn('terms', str(query['query']['bool']['must_not']))
        self.assertIn('completed', str(query['query']['bool']['must_not']))
        self.assertIn('cancelled', str(query['query']['bool']['must_not']))

    def test_date_in_query(self):
        date = '2025-06-25T12:00:00'
        query = make_elastic_query(date)
        self.assertIn(date, str(query))

if __name__ == '__main__':
    unittest.main()
