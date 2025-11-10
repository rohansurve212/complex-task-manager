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
sys.modules['shared.db'].DB = object
sys.modules['Elastic'] = types.ModuleType('Elastic')
sys.modules['Elastic.elastic_settings'] = types.ModuleType('Elastic.elastic_settings')
# Add all required attributes to the fake elastic_settings module
sys.modules['Elastic.elastic_settings'].all_cols = []
sys.modules['Elastic.elastic_settings'].nested_cols = []
sys.modules['Elastic.elastic_settings'].INDEX_NAME = ""
sys.modules['Elastic.elastic_settings'].mappings = {}
sys.modules['Elastic.elastic_settings'].make_request_body = lambda date, filter_comp=False: {"date": date, "filter_comp": filter_comp}
sys.modules['Elastic.elastic_settings'].get_auth_header = lambda auth_header: {"Authorization": f"Bearer {auth_header}"}
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

from elastic_api_index import smarttask_api_search_request

class DummySpVars:
    def __init__(self, base_url):
        self.base_url = base_url

class TestSmarttaskApiSearchRequest(unittest.TestCase):
    @patch('elastic_api_index.requests.request')
    @patch('elastic_api_index.make_request_body', side_effect=lambda date, filter_comp=False: {"date": date, "filter_comp": filter_comp})
    @patch('elastic_api_index.get_auth_header', side_effect=lambda auth_header: {"Authorization": f"Bearer {auth_header}"})
    def test_basic_request(self, mock_get_auth_header, mock_make_request_body, mock_request):
        sp_vars = DummySpVars('http://test-url')
        mock_response = MagicMock()
        mock_response.content = b'{"results": []}'
        mock_request.return_value = mock_response

        result = smarttask_api_search_request(sp_vars, "token", "2024-01-01", limit=123, filter_comp=True)
        self.assertEqual(result, mock_response)
        mock_make_request_body.assert_called_once_with(date="2024-01-01", filter_comp=True)
        mock_get_auth_header.assert_called_once_with("token")
        self.assertGreaterEqual(mock_request.call_count, 1)
        args, kwargs = mock_request.call_args_list[0]
        self.assertEqual(args[0], "POST")
        self.assertIn("/smartpath/smarttask/order/_startScroll", args[1])
        self.assertIn("offset=0&limit=123", args[1])
        self.assertIn('headers', kwargs)
        self.assertIn('data', kwargs)
        self.assertIn('proxies', kwargs)
        self.assertFalse(kwargs['verify'])

    @patch('elastic_api_index.requests.request', side_effect=Exception("Request failed"))
    @patch('elastic_api_index.make_request_body', side_effect=lambda date, filter_comp=False: {"date": date, "filter_comp": filter_comp})
    @patch('elastic_api_index.get_auth_header', side_effect=lambda auth_header: {"Authorization": f"Bearer {auth_header}"})
    def test_request_exception(self, mock_get_auth_header, mock_make_request_body, mock_request):
        sp_vars = DummySpVars('http://test-url')
        with self.assertRaises(Exception) as context:
            smarttask_api_search_request(sp_vars, "token", "2024-01-01")
        self.assertIn("Request failed", str(context.exception))

    @patch('elastic_api_index.requests.request')
    @patch('elastic_api_index.make_request_body', side_effect=lambda date, filter_comp=False: {"date": date, "filter_comp": filter_comp})
    @patch('elastic_api_index.get_auth_header', side_effect=lambda auth_header: {"Authorization": f"Bearer {auth_header}"})
    def test_missing_base_url(self, mock_get_auth_header, mock_make_request_body, mock_request):
        class IncompleteSpVars:
            pass
        sp_vars = IncompleteSpVars()
        with self.assertRaises(AttributeError):
            smarttask_api_search_request(sp_vars, "token", "2024-01-01")

if __name__ == '__main__':
    unittest.main()