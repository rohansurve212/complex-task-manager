import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from elastic_settings import get_auth_header

class TestGetAuthHeader(unittest.TestCase):
    def test_valid_token(self):
        token = 'abc123'
        header = get_auth_header(token)
        self.assertEqual(header['Authorization'], f'Bearer {token}')
        self.assertEqual(header['Content-Type'], 'application/json')

    def test_empty_token(self):
        token = ''
        header = get_auth_header(token)
        self.assertEqual(header['Authorization'], 'Bearer ')
        self.assertEqual(header['Content-Type'], 'application/json')

    def test_none_token(self):
        token = None
        header = get_auth_header(token)
        self.assertEqual(header['Authorization'], 'Bearer None')
        self.assertEqual(header['Content-Type'], 'application/json')

if __name__ == '__main__':
    unittest.main()
