import sys
import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GetWorkFlow')))
from search_requests_utils import get_requests_from_smartpath_elastic

class TestGetRequestsFromSmartpathElastic(unittest.IsolatedAsyncioTestCase):
    @patch('search_requests_utils.api')
    @patch('search_requests_utils.start_scroll_elastic_requests')
    @patch('search_requests_utils.continue_scroll_elastic_requests')
    async def test_get_requests_from_smartpath_elastic(self, mock_continue, mock_start, mock_api):
        # Setup mocks
        mock_api.auth_token = 'token'

        mock_start.return_value = MagicMock(
            headers={'x-scroll-id': 'scrollid'},
            text='{"metadata": {"totalRecordCount": 2}, "results": [1]}'
        )
        mock_start.return_value.raise_for_status = lambda: None

        mock_continue.return_value = MagicMock(
            text='{"results": []}'  # Empty results to stop the loop
        )
        mock_continue.return_value.raise_for_status = lambda: None

        async def mock_start_coroutine(*args, **kwargs):
            return mock_start.return_value

        async def mock_continue_coroutine(*args, **kwargs):
            return mock_continue.return_value

        mock_start.side_effect = mock_start_coroutine
        mock_continue.side_effect = mock_continue_coroutine

        # Patch json.loads to handle both calls
        with patch('search_requests_utils.json.loads', side_effect=[
            {'metadata': {'totalRecordCount': 2}, 'results': [1]},
            {'results': [2]},  # First continue scroll
            {'results': []}   # Second continue scroll to break the loop
        ]):
            result = await get_requests_from_smartpath_elastic('2024-01-01', 10, True)
            self.assertEqual(result, [1, 2])

if __name__ == '__main__':
    unittest.main()