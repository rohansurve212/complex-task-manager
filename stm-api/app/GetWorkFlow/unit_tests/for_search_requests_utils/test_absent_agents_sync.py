import sys
import os
import unittest
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GetWorkFlow')))
from search_requests_utils import absent_agents_sync

class TestAbsentAgentsSync(unittest.TestCase):
    def test_absent_agents_sync_returns_list(self):
        # Mock DB and cursor
        mssql_conn = MagicMock()
        context = mssql_conn().__enter__.return_value
        cursor = context.cursor.return_value
        cursor.execute.return_value.fetchall.return_value = [(1,), (2,), (3,)]
        with patch('search_requests_utils.DB.agent', return_value='agent_table'):
            result = absent_agents_sync(mssql_conn)
            self.assertEqual(result, [1, 2, 3])

if __name__ == '__main__':
    unittest.main()
