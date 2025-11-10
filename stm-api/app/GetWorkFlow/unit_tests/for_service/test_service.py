import sys
import os

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import unittest
from unittest.mock import MagicMock, patch
import asyncio
import pandas as pd
import pyodbc
from typing import List, Dict
import logging

# Mocking necessary modules and classes
class MockMSSQLConnection:
    def __init__(self):
        self.cursor_mock = MagicMock()
        self.connection_mock = MagicMock()  # Add a mock connection object
        self.connection_mock.cursor = lambda: self.cursor_mock  # Set cursor attribute on connection

    def __enter__(self):
        return self.connection_mock  # Return the mock connection object

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockElasticRequests:
    def get_requests(self):
        return pd.DataFrame()

class MockSPVars:
    base_url = "http://mock_base_url"

# Patching shared.all_envs to use the mock
from unittest import mock

class TestRoutingService(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        from service import RoutingService, SmartpathAPI  # Import here
        self.con_mssql_mock = MockMSSQLConnection()
        self.agent_id = "agent123"
        self.db_agent = "mock_db_agent"
        self.db_escalation = "mock_db_escalation"
        self.tenant = "mock_tenant"
        self.x_correlation_id = "mock_correlation_id"
        self.routing_service = RoutingService(
            self.con_mssql_mock,
            self.agent_id,
            self.db_agent,
            self.db_escalation,
            self.tenant,
            self.x_correlation_id
        )
        self.e_requests_mock = MockElasticRequests()

    @mock.patch('service.sp_vars', new=MockSPVars()) # ADD PATCH HERE
    @patch('service.agent_skillsets_async')
    @patch('service.agent_permissions_async')
    @patch('service.agent_skills_config_async')
    @patch('service.absent_agents_async')
    @patch('service.get_p1_escalation_async')
    @patch('service.routing')
    async def test_run(self, routing_mock, get_p1_escalation_async_mock, absent_agents_async_mock, agent_skills_config_async_mock, agent_permissions_async_mock, agent_skillsets_async_mock):
        # Mock successful fetching of agent data
        from service import RoutingService, SmartpathAPI, DF_TITLES #IMPORT NOW
        agent_skillsets_async_mock.return_value = [{'skill_id': 'skill1'}]
        agent_permissions_async_mock.return_value = ['permission1']
        agent_skills_config_async_mock.return_value = [{'skill_id': 'skill1', 'goldenCustomer': []}]
        absent_agents_async_mock.return_value = []
        get_p1_escalation_async_mock.return_value = []

        # Mock requests in the cache
        df_requests = pd.DataFrame({
            'source_externalId': ['req1', 'req2'],
            'source_requestType': ['winback', 'standard'],
            'source_goldenCustomer_id': ['1005108494', 'other'],
            'workOrder_controlDesk': ['atlanticpns', 'other'],
            'has_sla': [True, False],
            'skillPriority': [1, 2]
        })
        self.e_requests_mock.get_requests = MagicMock(return_value=df_requests)

        # Mock the skills_filtering function to return a DataFrame
        with patch('service.skills_filtering') as skills_filtering_mock:
            skills_filtering_mock.return_value = df_requests  # Return the mocked DataFrame

            # Mock the routing function to return a dummy request
            from collections import namedtuple
            Request = namedtuple('Request', ['requestId', 'skillId', 'skillPriority'])
            routing_mock.return_value = Request(requestId='req1', skillId='skill1', skillPriority=1)

            request, status = await self.routing_service.run(self.e_requests_mock)

            self.assertIsNotNone(request)
            self.assertEqual(request.requestId, 'req1')
            self.assertEqual(status, "REQUEST RETURNED")

class TestSmartpathAPI(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        from service import SmartpathAPI
        self.agent_id = "agent123"
        self.full_name = "Test Agent"
        self.request_id = "req123"
        self.skill_id = "skill123"
        self.auth_token = "mock_auth_token"
        self.correlation_id = "mock_correlation_id"
        self.from_absent_agent = "True"
        self.referredType = "ServiceOrder"
        self.x_authorization_for = "mock_x_auth"

        self.smartpath_api = SmartpathAPI(
            self.agent_id,
            self.full_name,
            self.request_id,
            self.skill_id,
            self.auth_token,
            self.correlation_id,
            self.from_absent_agent,
            self.referredType,
            self.x_authorization_for
        )

    def test_get_auth_header_assign(self):
        from service import SmartpathAPI
        self.smartpath_api = SmartpathAPI(
            self.agent_id,
            self.full_name,
            self.request_id,
            self.skill_id,
            self.auth_token,
            self.correlation_id,
            self.from_absent_agent,
            self.referredType,
            self.x_authorization_for
        )
        headers = self.smartpath_api.get_auth_header_assign()
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['x-correlation-id'], self.correlation_id)
        self.assertEqual(headers['Authorization'], f'Bearer {self.auth_token}')
        self.assertEqual(headers['x-authorization-for'], self.x_authorization_for)

    def test_get_auth_header_assigneeAndOrderStatus(self):
        from service import SmartpathAPI
        self.smartpath_api = SmartpathAPI(
            self.agent_id,
            self.full_name,
            self.request_id,
            self.skill_id,
            self.auth_token,
            self.correlation_id,
            self.from_absent_agent,
            self.referredType,
            self.x_authorization_for
        )
        headers = self.smartpath_api.get_auth_header_assigneeAndOrderStatus()
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['x-correlation-id'], self.correlation_id)
        self.assertEqual(headers['Authorization'], f'Bearer {self.auth_token}')

    def test_get_auth_header_event(self):
        from service import SmartpathAPI
        self.smartpath_api = SmartpathAPI(
            self.agent_id,
            self.full_name,
            self.request_id,
            self.skill_id,
            self.auth_token,
            self.correlation_id,
            self.from_absent_agent,
            self.referredType,
            self.x_authorization_for
        )
        headers = self.smartpath_api.get_auth_header_event()
        self.assertEqual(headers['Content-Type'], 'application/json;charset=UTF-8')
        self.assertEqual(headers['Authorization'], f'Bearer {self.auth_token}')
        self.assertEqual(headers['x-authorization-for'], self.x_authorization_for)

    def test_make_request_body(self):
        from service import SmartpathAPI
        self.smartpath_api = SmartpathAPI(
            self.agent_id,
            self.full_name,
            self.request_id,
            self.skill_id,
            self.auth_token,
            self.correlation_id,
            self.from_absent_agent,
            self.referredType,
            self.x_authorization_for
        )
        request_body = self.smartpath_api.make_request_body(
            request_id = self.request_id,
            date = "2023-01-01T00:00:00Z",
            correlation_id = self.correlation_id,
            agent_id = self.agent_id,
            full_name = self.full_name,
            skill_id = self.skill_id,
            from_absent_agent = self.from_absent_agent,
            referredType = self.referredType
        )
        self.assertEqual(request_body['dataDomain'], 'serviceOrder')

        self.smartpath_api.referredType = "ProductOrder"
        request_body = self.smartpath_api.make_request_body(
            request_id = self.request_id,
            date = "2023-01-01T00:00:00Z",
            correlation_id = self.correlation_id,
            agent_id = self.agent_id,
            full_name = self.full_name,
            skill_id = self.skill_id,
            from_absent_agent = self.from_absent_agent,
            referredType = self.referredType
        )
        self.assertEqual(request_body['dataDomain'], 'serviceOrder')

if __name__ == "__main__":
    unittest.main()