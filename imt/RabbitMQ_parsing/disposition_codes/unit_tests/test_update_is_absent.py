import sys
import os
import unittest
from unittest import mock

# Add the parent directory to sys.path so parsing_disposition_codes can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parsing_disposition_codes import update_is_absent

class TestUpdateIsAbsent(unittest.TestCase):
    def setUp(self):
        self.conn = mock.Mock()
        self.cursor = mock.Mock()
        self.conn.cursor.return_value = self.cursor

    def test_update_success(self):
        update_is_absent(self.conn, 'agent1', True)
        self.cursor.execute.assert_called_once()
        self.conn.commit.assert_called_once()
        self.conn.rollback.assert_not_called()

    def test_update_exception(self):
        self.cursor.execute.side_effect = Exception('DB error')
        update_is_absent(self.conn, 'agent1', False)
        self.conn.rollback.assert_called_once()
        self.conn.commit.assert_not_called()

    @mock.patch('parsing_disposition_codes.logger')
    def test_update_missing_cursor(self, mock_logger):
        # Simulate conn.cursor() raising an AttributeError
        self.conn.cursor.side_effect = AttributeError('no cursor')
        update_is_absent(self.conn, 'agent1', True)
        self.conn.rollback.assert_called_once()
        mock_logger.exception.assert_called_once()

    def test_update_invalid_agent_id(self):
        # Simulate passing None as agent_id
        update_is_absent(self.conn, None, True)
        self.cursor.execute.assert_called()
        self.conn.commit.assert_called()

    def test_update_invalid_value(self):
        # Simulate passing an unexpected value type
        update_is_absent(self.conn, 'agent1', 12345)
        self.cursor.execute.assert_called()
        self.conn.commit.assert_called()

if __name__ == '__main__':
    unittest.main()
