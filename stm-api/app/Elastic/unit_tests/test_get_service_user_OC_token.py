import sys
import os
import types
import unittest
from unittest.mock import patch, MagicMock

# Ensure the parent directory is in sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Patch sys.modules to allow import without actual dependencies
sys.modules['shared'] = types.ModuleType('shared')
sys.modules['shared.db'] = types.ModuleType('shared.db')
sys.modules['shared.db'].DB = object  # Add dummy DB
sys.modules['Elastic'] = types.ModuleType('Elastic')
sys.modules['Elastic.elastic_settings'] = types.ModuleType('Elastic.elastic_settings')
sys.modules['Elastic.elastic_settings'].all_cols = []
sys.modules['Elastic.elastic_settings'].nested_cols = []
sys.modules['Elastic.elastic_settings'].INDEX_NAME = ""
sys.modules['Elastic.elastic_settings'].mappings = {}
sys.modules['Elastic.elastic_settings'].make_request_body = lambda *a, **kw: {}
sys.modules['Elastic.elastic_settings'].get_auth_header = lambda *a, **kw: {}
sys.modules['shared.all_envs'] = types.ModuleType('shared.all_envs')
sys.modules['shared.all_envs'].sp_vars = None
sys.modules['shared.all_envs'].SMARTPATH_ENV = "qa"
sys.modules['shared.all_envs'].SQL_SERVER = ""
sys.modules['shared.all_envs'].DATABASE = ""
sys.modules['shared.all_envs'].SQL_USER = ""
sys.modules['shared.all_envs'].SQL_PASS = ""
sys.modules['shared.all_envs'].ELASTIC_SERVER = ""
sys.modules['shared.all_envs'].ELASTIC_USER = ""
sys.modules['shared.all_envs'].ELASTIC_PASS = ""

# Patch requests in sys.modules so it can be mocked
import types as _types
sys.modules['requests'] = _types.ModuleType('requests')
sys.modules['requests'].request = MagicMock()

from elastic_api_index import get_service_user_OC_token

class DummySpVars:
    def __init__(self, base_url, client_secret, user, pw):
        self.base_url = base_url
        self.client_secret = client_secret
        self.user = user
        self.pw = pw

class TestGetServiceUserOCToken(unittest.TestCase):
    @patch('elastic_api_index.SMARTPATH_ENV', 'qa')
    @patch('elastic_api_index.requests.request')
    def test_qa_env_url(self, mock_request):
        sp_vars = DummySpVars('http://test-url', 'secret', 'user', 'pw')
        mock_response = MagicMock()
        mock_request.return_value = mock_response

        result = get_service_user_OC_token(sp_vars)
        self.assertEqual(result, mock_response)
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertIn('/login/oauth', args[1])

    @patch('elastic_api_index.SMARTPATH_ENV', 'dev')
    @patch('elastic_api_index.requests.request')
    def test_non_qa_prod_env_url(self, mock_request):
        sp_vars = DummySpVars('http://dev-url', 'secret', 'user', 'pw')
        mock_response = MagicMock()
        mock_request.return_value = mock_response

        result = get_service_user_OC_token(sp_vars)
        self.assertEqual(result, mock_response)
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertIn('/auth/realms/oc/protocol/openid-connect/token', args[1])

    @patch('elastic_api_index.SMARTPATH_ENV', 'prod')
    @patch('elastic_api_index.requests.request')
    def test_prod_env_url(self, mock_request):
        sp_vars = DummySpVars('http://prod-url', 'secret', 'user', 'pw')
        mock_response = MagicMock()
        mock_request.return_value = mock_response

        result = get_service_user_OC_token(sp_vars)
        self.assertEqual(result, mock_response)
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertIn('/login/oauth', args[1])

    @patch('elastic_api_index.SMARTPATH_ENV', 'qa')
    @patch('elastic_api_index.requests.request')
    def test_payload_and_headers(self, mock_request):
        sp_vars = DummySpVars('http://test-url', 'secret', 'user', 'pw')
        mock_response = MagicMock()
        mock_request.return_value = mock_response

        get_service_user_OC_token(sp_vars)
        args, kwargs = mock_request.call_args
        # Check payload
        self.assertIn('data', kwargs)
        self.assertIn('client_secret=secret', kwargs['data'])
        self.assertIn('username=user', kwargs['data'])
        self.assertIn('password=pw', kwargs['data'])
        # Check headers
        self.assertIn('headers', kwargs)
        self.assertIn('Content-Type', kwargs['headers'])
        self.assertEqual(kwargs['headers']['Content-Type'], 'application/x-www-form-urlencoded')
        # Check proxies
        self.assertIn('proxies', kwargs)
        self.assertEqual(kwargs['proxies'], {"http": None, "https": None})

    @patch('elastic_api_index.SMARTPATH_ENV', 'qa')
    @patch('elastic_api_index.requests.request', side_effect=Exception("Request failed"))
    def test_request_exception(self, mock_request):
        sp_vars = DummySpVars('http://test-url', 'secret', 'user', 'pw')
        # The function does not handle exceptions, so it should propagate
        with self.assertRaises(Exception) as context:
            get_service_user_OC_token(sp_vars)
        self.assertIn("Request failed", str(context.exception))

    @patch('elastic_api_index.SMARTPATH_ENV', 'qa')
    @patch('elastic_api_index.requests.request')
    def test_missing_spvars_attribute(self, mock_request):
        # Remove 'client_secret' from sp_vars
        class IncompleteSpVars:
            def __init__(self):
                self.base_url = 'http://test-url'
                self.user = 'user'
                self.pw = 'pw'
        sp_vars = IncompleteSpVars()
        with self.assertRaises(AttributeError):
            get_service_user_OC_token(sp_vars)

if __name__ == '__main__':
    unittest.main()