import sys
import os
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parsing_agent_skills import event_create

class TestEventCreate(unittest.TestCase):
    @patch('shared.db.DB.agent', return_value='dbo.uat_agent')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.get_fullName_and_permissions_from_ldap')
    @patch('parsing_agent_skills.insert_into')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_agent_already_exists(self, mock_extract_skills_data, mock_insert_into, mock_get_fullName_and_permissions_from_ldap, mock_logger, mock_db_agent):
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate agent already exists
        mock_cursor.fetchall.return_value = [(1,)]
        mock_extract_skills_data.return_value = ('src1', 'skill1', 'agent1', 'pein1', 1, '2025-06-19')
        skillsDict = {'dummy': 'data'}
        # Call
        event_create(mock_conn, skillsDict)
        # Should not call get_fullName_and_permissions_from_ldap or insert_into for agent
        mock_get_fullName_and_permissions_from_ldap.assert_not_called()
        mock_insert_into.assert_not_called()
        mock_logger.info.assert_any_call('Agent agent1 with pein pein1 already exists in dbo.uat_agent: SourceId=src1')

    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.get_fullName_and_permissions_from_ldap')
    @patch('parsing_agent_skills.insert_into')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_agent_does_not_exist(self, mock_extract_skills_data, mock_insert_into, mock_get_fullName_and_permissions_from_ldap, mock_logger):
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate agent does not exist
        mock_cursor.fetchall.return_value = []
        mock_extract_skills_data.return_value = ('src2', 'skill2', 'agent2', 'pein2', 2, '2025-06-19')
        mock_get_fullName_and_permissions_from_ldap.return_value = ('Agent Two', ['perm1', 'perm2'])
        skillsDict = {'dummy': 'data'}
        # Call
        event_create(mock_conn, skillsDict)
        # Should call get_fullName_and_permissions_from_ldap and insert_into for agent
        mock_get_fullName_and_permissions_from_ldap.assert_called_once_with('agent2')
        self.assertTrue(mock_insert_into.called)
        mock_logger.info.assert_any_call('Permissions successfully updated for agent agent2')

    @patch('shared.db.DB.agent', return_value='dbo.uat_agent')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.get_fullName_and_permissions_from_ldap')
    @patch('parsing_agent_skills.insert_into')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_skill_assignment_already_exists(self, mock_extract_skills_data, mock_insert_into, mock_get_fullName_and_permissions_from_ldap, mock_logger, mock_db_agent):
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate agent exists
        mock_cursor.fetchall.side_effect = [[(1,)], [(1,)]]  # First for agent, second for skill assignment
        mock_extract_skills_data.return_value = ('src3', 'skill3', 'agent3', 'pein3', 3, '2025-06-19')
        skillsDict = {'dummy': 'data'}
        # Call
        event_create(mock_conn, skillsDict)
        # Should not insert new skill assignment
        self.assertTrue(mock_logger.info.called)
        mock_logger.info.assert_any_call('Agent agent3 with pein pein3 already exists in dbo.uat_agent: SourceId=src3')

    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.get_fullName_and_permissions_from_ldap')
    @patch('parsing_agent_skills.insert_into')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_skill_assignment_new(self, mock_extract_skills_data, mock_insert_into, mock_get_fullName_and_permissions_from_ldap, mock_logger):
        # Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Simulate agent exists, skill assignment does not
        mock_cursor.fetchall.side_effect = [[(1,)], []]  # First for agent, second for skill assignment
        mock_extract_skills_data.return_value = ('src4', 'skill4', 'agent4', 'pein4', 4, '2025-06-19')
        skillsDict = {'dummy': 'data'}
        # Call
        event_create(mock_conn, skillsDict)
        # Should execute merge query for new skill assignment
        self.assertTrue(mock_cursor.execute.called)
        self.assertTrue(mock_conn.commit.called)

    @patch('shared.db.DB.agent', return_value='dbo.uat_agent')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.get_fullName_and_permissions_from_ldap')
    @patch('parsing_agent_skills.insert_into')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_malformed_skillsDict(self, mock_extract_skills_data, mock_insert_into, mock_get_fullName_and_permissions_from_ldap, mock_logger, mock_db_agent):
        mock_conn = MagicMock()
        # Simulate extract_skills_data raising KeyError
        mock_extract_skills_data.side_effect = KeyError('missing key')
        with self.assertRaises(KeyError):
            event_create(mock_conn, {})

    @patch('shared.db.DB.agent', return_value='dbo.uat_agent')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.get_fullName_and_permissions_from_ldap')
    @patch('parsing_agent_skills.insert_into')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_empty_permissions(self, mock_extract_skills_data, mock_insert_into, mock_get_fullName_and_permissions_from_ldap, mock_logger, mock_db_agent):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_extract_skills_data.return_value = ('src', 'skill', 'agent', 'pein', 1, '2025-06-19')
        mock_get_fullName_and_permissions_from_ldap.return_value = ('Agent', [])
        skillsDict = {'dummy': 'data'}
        event_create(mock_conn, skillsDict)
        mock_logger.info.assert_any_call('Permissions successfully updated for agent agent')

    @patch('shared.db.DB.agent', return_value='dbo.uat_agent')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.get_fullName_and_permissions_from_ldap')
    @patch('parsing_agent_skills.insert_into')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_none_agent_id(self, mock_extract_skills_data, mock_insert_into, mock_get_fullName_and_permissions_from_ldap, mock_logger, mock_db_agent):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_extract_skills_data.return_value = ('src', 'skill', None, 'pein', 1, '2025-06-19')
        mock_get_fullName_and_permissions_from_ldap.return_value = ('Agent', ['perm'])
        skillsDict = {'dummy': 'data'}
        event_create(mock_conn, skillsDict)
        mock_logger.info.assert_any_call('Permissions successfully updated for agent None')

    @patch('shared.db.DB.agent', return_value='dbo.uat_agent')
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.get_fullName_and_permissions_from_ldap')
    @patch('parsing_agent_skills.insert_into')
    @patch('parsing_agent_skills.extract_skills_data')
    def test_db_error_on_insert(self, mock_extract_skills_data, mock_insert_into, mock_get_fullName_and_permissions_from_ldap, mock_logger, mock_db_agent):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_extract_skills_data.return_value = ('src', 'skill', 'agent', 'pein', 1, '2025-06-19')
        mock_get_fullName_and_permissions_from_ldap.return_value = ('Agent', ['perm'])
        mock_insert_into.side_effect = Exception('DB error')
        skillsDict = {'dummy': 'data'}
        event_create(mock_conn, skillsDict)
        mock_logger.exception.assert_any_call('Error in adding agent agent. Error message: DB error')
        self.assertTrue(mock_conn.rollback.called)

if __name__ == '__main__':
    unittest.main()
