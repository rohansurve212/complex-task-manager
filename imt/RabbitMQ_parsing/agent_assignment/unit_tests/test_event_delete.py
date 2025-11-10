import sys
import os
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parsing_agent_skills import event_delete

class TestEventDelete(unittest.TestCase):
    @patch('shared.db.DB.skill_agent_priority', return_value='dbo.uat_skill_agent_priority')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.delete_record')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_record_does_not_exist(self, mock_extract_skills_data, mock_delete_record, mock_logger, mock_db_skill_agent_priority):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate record does not exist
        mock_cursor.fetchall.return_value = []
        mock_extract_skills_data.return_value = ('srcDel', 'skillDel', 'agentDel', None, 1, '2025-06-19')
        skillsDict = {'dummy': 'data'}
        event_delete(mock_conn, skillsDict)
        mock_delete_record.assert_not_called()
        mock_logger.error.assert_any_call('The record does not exist, a delete cannot be made. SourceId=srcDel')

    @patch('shared.db.DB.skill_agent_priority', return_value='dbo.uat_skill_agent_priority')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.delete_record')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_record_exists_and_deletes(self, mock_extract_skills_data, mock_delete_record, mock_logger, mock_db_skill_agent_priority):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate record exists
        mock_cursor.fetchall.return_value = [(1,)]
        mock_extract_skills_data.return_value = ('srcDel', 'skillDel', 'agentDel', None, 1, '2025-06-19')
        skillsDict = {'dummy': 'data'}
        event_delete(mock_conn, skillsDict)
        mock_delete_record.assert_called_once()
        mock_logger.info.assert_any_call('Deleting record, SourceId=srcDel')

    @patch('shared.db.DB.skill_agent_priority', return_value='dbo.uat_skill_agent_priority')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.delete_record')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_delete_raises_exception(self, mock_extract_skills_data, mock_delete_record, mock_logger, mock_db_skill_agent_priority):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate record exists
        mock_cursor.fetchall.return_value = [(1,)]
        # Simulate exception on execute
        mock_cursor.execute.side_effect = Exception('DB error')
        mock_extract_skills_data.return_value = ('srcDel', 'skillDel', 'agentDel', None, 1, '2025-06-19')
        skillsDict = {'dummy': 'data'}
        event_delete(mock_conn, skillsDict)
        mock_logger.exception.assert_any_call('Error in deleting priority for routing filter id skillDel for agent agentDel. Error message: DB error')
        self.assertTrue(mock_conn.rollback.called)

if __name__ == '__main__':
    unittest.main()
