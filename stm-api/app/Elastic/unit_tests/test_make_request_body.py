import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from elastic_settings import make_request_body

class TestMakeRequestBody(unittest.TestCase):
    def test_default_filter_comp_false(self):
        date = '2024-01-01T00:00:00'
        body = make_request_body(date)
        self.assertIn('@type', body)
        self.assertEqual(body['@type'], 'SearchDetails')
        self.assertIn('filter', body)
        self.assertEqual(body['filter'][0]['groupOperator'], 'AND')
        self.assertIn('sort', body)
        self.assertEqual(body['sort'][0]['direction'], 'DESC')
        # Check that workOrder.status filter is not present
        filters = [f['field'] for f in body['filter'][0]['filter']]
        self.assertNotIn('workOrder.status', filters)

    def test_filter_comp_true(self):
        date = '2024-01-01T00:00:00'
        body = make_request_body(date, filter_comp=True)
        self.assertIn('@type', body)
        self.assertEqual(body['@type'], 'SearchDetails')
        self.assertIn('filter', body)
        self.assertEqual(body['filter'][0]['groupOperator'], 'AND')
        self.assertIn('sort', body)
        self.assertEqual(body['sort'][0]['direction'], 'DESC')
        # Check that workOrder.status filter is present
        filters = [f['field'] for f in body['filter'][0]['filter']]
        self.assertIn('workOrder.status', filters)
        self.assertIn('workOrder.controlDesk', filters)

    def test_date_in_body(self):
        date = '2025-06-25T12:00:00'
        body = make_request_body(date)
        found = False
        for f in body['filter'][0]['filter']:
            if f['field'] == 'lastUpdated':
                self.assertEqual(f['value'][0], date)
                found = True
        self.assertTrue(found)

if __name__ == '__main__':
    unittest.main()
