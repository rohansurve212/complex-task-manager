import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from initialize_elastic_index import continue_scroll_elastic_requests

class TestContinueScrollElasticRequests(unittest.IsolatedAsyncioTestCase):
    @patch('initialize_elastic_index.httpx.AsyncClient')
    @patch('initialize_elastic_index.make_request_body')
    @patch('initialize_elastic_index.get_auth_header')
    async def test_successful_post(self, mock_get_auth_header, mock_make_request_body, mock_async_client):
        sp_vars = MagicMock()
        sp_vars.base_url = 'http://test-url'
        mock_get_auth_header.return_value = {'Authorization': 'Bearer token'}
        mock_make_request_body.return_value = {'foo': 'bar'}
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_client.post.return_value = mock_response
        mock_async_client.return_value.__aenter__.return_value = mock_client
        response = await continue_scroll_elastic_requests(sp_vars, 'token', '2024-01-01', 'scrollid', False)
        self.assertEqual(response, mock_response)
        mock_client.post.assert_awaited_once()

if __name__ == '__main__':
    unittest.main()
