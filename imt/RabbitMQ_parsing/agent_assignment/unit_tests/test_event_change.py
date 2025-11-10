import sys
import os
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parsing_agent_skills import event_change

class TestEventChange(unittest.TestCase):
    @patch('shared.db.DB.skill_agent_priority', return_value='dbo.uat_skill_agent_priority')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.event_create')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_record_does_not_exist_calls_event_create(self, mock_extract_skills_data, mock_event_create, mock_logger, mock_db_skill_agent_priority):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate record does not exist
        mock_cursor.fetchall.return_value = []
        # Return values for oldValue and newValue
        mock_extract_skills_data.side_effect = [
            ('srcOld', 'skillOld', 'agentOld', None, 1, '2025-06-19'),
            ('srcNew', 'skillNew', 'agentNew', None, 2, '2025-06-19')
        ]
        skillsDict = {'dummy': 'data'}
        event_change(mock_conn, skillsDict)
        mock_event_create.assert_called_once_with(mock_conn, skillsDict)
        mock_logger.error.assert_any_call('The record does not exist, so create a new entry for this agent. SourceId=srcOld')

    @patch('shared.db.DB.skill_agent_priority', return_value='dbo.uat_skill_agent_priority')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.event_create')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_record_exists_updates_priority(self, mock_extract_skills_data, mock_event_create, mock_logger, mock_db_skill_agent_priority):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate record exists
        mock_cursor.fetchall.return_value = [(1,)]
        # Return values for oldValue and newValue
        mock_extract_skills_data.side_effect = [
            ('srcOld', 'skillOld', 'agentOld', None, 1, '2025-06-19'),
            ('srcNew', 'skillNew', 'agentNew', None, 2, '2025-06-19')
        ]
        skillsDict = {'dummy': 'data'}
        event_change(mock_conn, skillsDict)
        mock_event_create.assert_not_called()
        mock_logger.info.assert_any_call('Updating record, sourceId=srcOld')
        mock_logger.info.assert_any_call('Successfully updated priority for routing filter id skillNew for agent agentNew')
        self.assertTrue(mock_conn.commit.called)
        self.assertTrue(mock_cursor.execute.called)

    @patch('shared.db.DB.skill_agent_priority', return_value='dbo.uat_skill_agent_priority')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.event_create')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_update_raises_exception(self, mock_extract_skills_data, mock_event_create, mock_logger, mock_db_skill_agent_priority):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate record exists
        mock_cursor.fetchall.return_value = [(1,)]
        # Simulate exception on execute
        mock_cursor.execute.side_effect = Exception('DB error')
        # Return values for oldValue and newValue
        mock_extract_skills_data.side_effect = [
            ('srcOld', 'skillOld', 'agentOld', None, 1, '2025-06-19'),
            ('srcNew', 'skillNew', 'agentNew', None, 2, '2025-06-19')
        ]
        skillsDict = {'dummy': 'data'}
        event_change(mock_conn, skillsDict)
        mock_logger.exception.assert_any_call('Error in updating priority for routing filter id skillNew for agent agentNew. Error message: DB error')
        self.assertTrue(mock_conn.rollback.called)

if __name__ == '__main__':
    unittest.main()
