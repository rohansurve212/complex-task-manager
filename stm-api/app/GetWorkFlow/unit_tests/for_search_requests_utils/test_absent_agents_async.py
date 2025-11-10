import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GetWorkFlow')))
from search_requests_utils import absent_agents_async

class TestAbsentAgentsAsync(unittest.IsolatedAsyncioTestCase):
    async def test_absent_agents_async_returns_list(self):
        # Mock the sync function to return a known list
        with patch('search_requests_utils.absent_agents_sync', return_value=[1, 2, 3]):
            mssql_conn = MagicMock()
            result = await absent_agents_async(mssql_conn)
            self.assertEqual(result, [1, 2, 3])

if __name__ == '__main__':
    unittest.main()
