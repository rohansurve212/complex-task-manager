import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parsing_agent_skills import delete_record
import unittest
from unittest.mock import patch, MagicMock

class TestDeleteRecord(unittest.TestCase):

    @patch('parsing_agent_skills.logger')  # Patch logger (important!)
    def test_successful_deletion(self, mock_logger):
        """Test successful deletion from the database."""
        # Mock the database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Define the query and value
        query = "DELETE FROM mytable WHERE id = %s"
        value = (123,)  # Example ID to delete

        # Call the function
        delete_record(mock_conn, query, value)

        # Assertions
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(query, value)
        mock_conn.commit.assert_called_once()
        mock_logger.info.assert_called_once()

    @patch('parsing_agent_skills.logger')  # Patch logger (important!)
    def test_deletion_error(self, mock_logger):
        """Test deletion error and rollback."""
        # Mock the database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Define the query and value
        query = "DELETE FROM mytable WHERE id = %s"
        value = (123,)  # Example ID to delete

        # Configure the cursor to raise an exception when execute is called
        mock_cursor.execute.side_effect = Exception("Simulated database error")

        # Call the function
        delete_record(mock_conn, query, value)

        # Assertions
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(query, value)
        mock_conn.rollback.assert_called_once()
        mock_logger.error.assert_called_once()

    @patch('parsing_agent_skills.logger')
    def test_invalid_query(self, mock_logger):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate exception on execute
        mock_cursor.execute.side_effect = Exception('Query error')
        delete_record(mock_conn, None, ('val',))
        mock_logger.error.assert_called()
        mock_conn.rollback.assert_called()

    @patch('parsing_agent_skills.logger')
    def test_invalid_values(self, mock_logger):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate exception on execute
        mock_cursor.execute.side_effect = Exception('Values error')
        delete_record(mock_conn, 'DELETE FROM table WHERE id=?', None)
        mock_logger.error.assert_called()
        mock_conn.rollback.assert_called()

    @patch('parsing_agent_skills.logger')
    def test_commit_failure(self, mock_logger):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.commit.side_effect = Exception('Commit failed')
        # Should log error and rollback
        delete_record(mock_conn, 'DELETE FROM table WHERE id=?', ('val',))
        self.assertTrue(mock_conn.rollback.called)
        mock_logger.error.assert_called()

if __name__ == '__main__':
    unittest.main()