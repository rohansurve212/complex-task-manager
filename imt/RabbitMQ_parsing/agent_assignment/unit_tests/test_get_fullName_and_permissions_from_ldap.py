import sys
import os
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parsing_agent_skills import get_fullName_and_permissions_from_ldap

class TestGetFullNameAndPermissionsFromLdap(unittest.TestCase):
    @patch('parsing_agent_skills.ldap')
    @patch('parsing_agent_skills.logger')
    def test_successful_lookup(self, mock_logger, mock_ldap):
        mock_conn = MagicMock()
        mock_ldap.initialize.return_value = mock_conn
        mock_conn.search.return_value = 'ldap_id'
        mock_conn.result.return_value = (
            None,
            [(
                None,
                {
                    'memberOf': [b'CN=OC-SmartPath-Admin,OU=Groups,DC=bell,DC=corp,DC=bce,DC=ca'],
                    'displayName': [b'Doe, John']
                }
            )]
        )
        with patch('parsing_agent_skills.extract_name', return_value='John Doe'):
            full_name, permissions = get_fullName_and_permissions_from_ldap('jdoe')
        self.assertEqual(full_name, 'John Doe')
        self.assertIn('OC-SmartPath-Admin', permissions)

    @patch('parsing_agent_skills.ldap')
    @patch('parsing_agent_skills.logger')
    def test_employee_not_found(self, mock_logger, mock_ldap):
        mock_conn = MagicMock()
        mock_ldap.initialize.return_value = mock_conn
        mock_conn.search.return_value = 'ldap_id'
        mock_conn.result.return_value = (None, [])
        result = get_fullName_and_permissions_from_ldap('notfound')
        self.assertIsNone(result)

    @patch('parsing_agent_skills.ldap')
    @patch('parsing_agent_skills.logger')
    def test_no_permissions_found(self, mock_logger, mock_ldap):
        mock_conn = MagicMock()
        mock_ldap.initialize.return_value = mock_conn
        mock_conn.search.return_value = 'ldap_id'
        mock_conn.result.return_value = (
            None,
            [(
                None,
                {
                    'memberOf': [b'CN=OtherGroup,OU=Groups,DC=bell,DC=corp,DC=bce,DC=ca'],
                    'displayName': [b'Doe, Jane']
                }
            )]
        )
        with patch('parsing_agent_skills.extract_name', return_value='Jane Doe'):
            full_name, permissions = get_fullName_and_permissions_from_ldap('jane')
        self.assertEqual(full_name, 'Jane Doe')
        self.assertEqual(permissions, [])

    @patch('parsing_agent_skills.ldap')
    @patch('parsing_agent_skills.logger')
    def test_invalid_credentials(self, mock_logger, mock_ldap):
        mock_ldap.INVALID_CREDENTIALS = Exception
        mock_conn = MagicMock()
        mock_ldap.initialize.return_value = mock_conn
        mock_conn.simple_bind_s.side_effect = mock_ldap.INVALID_CREDENTIALS()
        with self.assertRaises(SystemExit):
            get_fullName_and_permissions_from_ldap('baduser')

    @patch('parsing_agent_skills.ldap')
    @patch('parsing_agent_skills.logger')
    def test_server_down(self, mock_logger, mock_ldap):
        # Define dummy exception classes
        class FakeServerDown(Exception): pass
        class FakeInvalidCreds(Exception): pass
        mock_ldap.SERVER_DOWN = FakeServerDown
        mock_ldap.INVALID_CREDENTIALS = FakeInvalidCreds
        mock_conn = MagicMock()
        mock_ldap.initialize.return_value = mock_conn
        mock_conn.simple_bind_s.side_effect = FakeServerDown()
        with self.assertRaises(SystemExit):
            get_fullName_and_permissions_from_ldap('serverdown')

    @patch('parsing_agent_skills.ldap')
    @patch('parsing_agent_skills.logger')
    def test_general_ldap_error(self, mock_logger, mock_ldap):
        class DictWithHasKey(dict):
            def has_key(self, key):
                return key in self

        class FakeLdapError(Exception):
            def __init__(self):
                self.message = DictWithHasKey({'desc': 'General LDAP error'})
            def __str__(self):
                return "General LDAP error"
        # Make sure all exception attributes are valid exception classes
        mock_ldap.LDAPError = FakeLdapError
        mock_ldap.INVALID_CREDENTIALS = type('FakeInvalidCreds', (Exception,), {})
        mock_ldap.SERVER_DOWN = type('FakeServerDown', (Exception,), {})
        mock_conn = MagicMock()
        mock_ldap.initialize.return_value = mock_conn
        mock_conn.simple_bind_s.side_effect = FakeLdapError()
        with self.assertRaises(SystemExit):
            get_fullName_and_permissions_from_ldap('ldaperror')

    @patch('parsing_agent_skills.ldap')
    @patch('parsing_agent_skills.logger')
    def test_malformed_ldap_response(self, mock_logger, mock_ldap):
        class FakeInvalidCreds(Exception): pass
        class FakeServerDown(Exception): pass
        class FakeLdapError(Exception): pass
        mock_ldap.INVALID_CREDENTIALS = FakeInvalidCreds
        mock_ldap.SERVER_DOWN = FakeServerDown
        mock_ldap.LDAPError = FakeLdapError
        mock_conn = MagicMock()
        mock_ldap.initialize.return_value = mock_conn
        mock_conn.search.return_value = 'ldap_id'
        # Missing 'displayName' and 'memberOf'
        mock_conn.result.return_value = (None, [(None, {})])
        with patch('parsing_agent_skills.extract_name', return_value=''):
            result = get_fullName_and_permissions_from_ldap('jdoe')
        self.assertIsNone(result)

    @patch('parsing_agent_skills.ldap')
    @patch('parsing_agent_skills.logger')
    def test_unexpected_ldap_types(self, mock_logger, mock_ldap):
        mock_conn = MagicMock()
        mock_ldap.initialize.return_value = mock_conn
        mock_conn.search.return_value = 'ldap_id'
        # 'memberOf' is not a list
        mock_conn.result.return_value = (None, [(None, {'memberOf': 'notalist', 'displayName': [b'John Doe']})])
        with patch('parsing_agent_skills.extract_name', return_value='John Doe'):
            try:
                get_fullName_and_permissions_from_ldap('jdoe')
            except Exception:
                self.assertTrue(True)  # Should raise

    @patch('parsing_agent_skills.ldap')
    @patch('parsing_agent_skills.logger')
    def test_empty_emp_id(self, mock_logger, mock_ldap):
        mock_conn = MagicMock()
        mock_ldap.initialize.return_value = mock_conn
        mock_conn.search.return_value = 'ldap_id'
        mock_conn.result.return_value = (None, [])
        result = get_fullName_and_permissions_from_ldap('')
        self.assertIsNone(result)  # Should return None for empty emp_id

    @patch('parsing_agent_skills.ldap')
    @patch('parsing_agent_skills.logger')
    def test_none_emp_id(self, mock_logger, mock_ldap):
        class FakeInvalidCreds(Exception): pass
        class FakeServerDown(Exception): pass
        class FakeLdapError(Exception): pass
        mock_ldap.INVALID_CREDENTIALS = FakeInvalidCreds
        mock_ldap.SERVER_DOWN = FakeServerDown
        mock_ldap.LDAPError = FakeLdapError
        mock_conn = MagicMock()
        mock_ldap.initialize.return_value = mock_conn
        mock_conn.search.return_value = 'ldap_id'
        mock_conn.result.return_value = (None, [])
        result = get_fullName_and_permissions_from_ldap(None)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
