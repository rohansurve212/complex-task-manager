import unittest
from unittest.mock import MagicMock, patch
import asyncio
import pandas as pd
import pyodbc
from typing import List, Dict
import logging
import os
import sys

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))  # Navigate up to the 'app' directory
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Mocking shared.db and elastic_settings
class MockDB:
    @staticmethod
    def permission_agent():
        return "mock_permission_agent"

    @staticmethod
    def skill_agent_priority():
        return "mock_skill_agent_priority"

    @staticmethod
    def skill_config():
        return "mock_skill_config"

    @staticmethod
    def skill_attributes():
        return "mock_skill_attributes"

# Mocking elastic_settings
query_fields = [
    "request_id",
    "source.externalId",
    "lastUpdated",
    "accessPolicyTag",
    "workOrder.status",
    "workOrder.product",
    "workOrder.followUpDate",
    "workOrder.controlDesk",
    "workOrder.group",
    "workOrder.assignee.id",
    "workOrder.tags",
    "source.orderDate",
    "source.requestedStartDate",
    "source.requestType",
    "source.requestSource",
    "source.customerSupportModel",
    "source.businessUnit",
    "source.status",
    "source.product",
    "source.serviceRegion",
    "source.goldenCustomer.id",
    "source.goldenCustomer.name",
    "source.customer",
    "source.customerMarketSegment",
    "source.preferredLanguage",
    "source.focTarget",
    "has_sla",
    "source.referredType"
]

INDEX_NAME = "mock_index_name"

def make_elastic_query(last_request_date, limit=10000, filter_comp=False):
    return {}

# Mocking shared.all_envs
class MockAllEnvs:
    MSSQL_CONNECTION_STRING = "mock_mssql_connection_string"
    SMARTPATH_ELASTIC_URL = "mock_smartpath_elastic_url"

# Apply mocks to the module
DB = MockDB()
ALL_ENVS = MockAllEnvs()

# Adjust sys.path (same logic as in the original file)
try:
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    STM_API_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..'))  # stm-api
    STM_ROOT = os.path.abspath(os.path.join(STM_API_DIR, '..'))  # stm-1
    SHARED_DIR = os.path.join(STM_ROOT, 'shared')
    for p in [STM_API_DIR, STM_ROOT, SHARED_DIR]:
        if p not in sys.path:
            sys.path.insert(0, p)
except Exception as e:
    print(f"[search_requests.py] sys.path patch failed: {e}")

# Import the module to be tested AFTER mocking and path adjustments
from app.GetWorkFlow.search_requests import (
    agent_permissions_async, agent_permissions_sync,
    agent_skillsets_async, agent_skillsets_sync,
    agent_skills_config_async, agent_skills_config_sync,
    get_p1_escalation_async, get_p1_escalation_sync,
    updated_elastic_to_df, skills_filtering
)
from app.GetWorkFlow.search_requests_utils import filter_static, find_requests_for_skill, get_requests_from_smartpath_elastic, elastic_response_to_df, flatten


# Setup logging (same as in original file)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("API log")

class TestSearchRequests(unittest.TestCase):

    def setUp(self):
        self.mssql_conn_mock = MagicMock()
        self.cursor_mock = MagicMock()
        self.mssql_conn_mock.return_value.__enter__.return_value = MagicMock(cursor=lambda: self.cursor_mock)
        self.loop = asyncio.get_event_loop()

    def test_agent_permissions_sync(self):
        self.cursor_mock.execute.return_value.fetchall.return_value = [("permission1",), ("permission2",)]
        permissions = agent_permissions_sync(self.mssql_conn_mock, "agent123")
        self.assertEqual(permissions, ["permission1", "permission2"])
        self.cursor_mock.execute.assert_called_once()

    def test_agent_skillsets_sync(self):
        self.cursor_mock.execute.return_value.fetchall.return_value = [
            ("skill1", "Skill One", 1),
            ("skill2", "Skill Two", 2)
        ]
        skillsets = agent_skillsets_sync(self.mssql_conn_mock, "agent123")
        expected = [
            {'skill_id': 'skill1', 'skill_name': 'Skill One', 'skill_priority': 1},
            {'skill_id': 'skill2', 'skill_name': 'Skill Two', 'skill_priority': 2}
        ]
        self.assertEqual(skillsets, expected)
        self.cursor_mock.execute.assert_called_once()

    @patch('pandas.read_sql')
    def test_get_p1_escalation_sync(self, mock_read_sql):
        mock_read_sql.return_value = pd.DataFrame({
            'request_id': ['req1', 'req2'],
            'status': ['open', 'open'],
            'priority': [1, 1]
        })
        request_ids = get_p1_escalation_sync(self.mssql_conn_mock, "escalation_table")
        self.assertEqual(request_ids, ['REQ1', 'REQ2'])
        mock_read_sql.assert_called_once()

    @patch('app.GetWorkFlow.search_requests.get_requests_from_smartpath_elastic')
    @patch('app.GetWorkFlow.search_requests.elastic_response_to_df')
    async def test_updated_elastic_to_df(self, mock_elastic_response_to_df, mock_get_requests_from_smartpath_elastic):
        # Mock the elastic search response
        mock_get_requests_from_smartpath_elastic.return_value = {'hits': {'hits': []}}
        # Mock the conversion to dataframe
        mock_elastic_response_to_df.return_value = pd.DataFrame({'request_id': ['req1', 'req2']})

        df = await updated_elastic_to_df('2023-01-01', filter_comp=True, query_fields=['request_id'])

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df['request_id']), ['req1', 'req2'])
        mock_get_requests_from_smartpath_elastic.assert_called_once_with('2023-01-01', limit=10000, filter_comp=True)
        mock_elastic_response_to_df.assert_called_once_with({'hits': {'hits': []}}, query_fields=['request_id'])

    @patch('app.GetWorkFlow.search_requests.filter_static')
    @patch('app.GetWorkFlow.search_requests.find_requests_for_skill')
    def test_skills_filtering(self, mock_find_requests_for_skill, mock_filter_static):
        # Mock initial DataFrame and static filter result
        initial_df = pd.DataFrame({'request_id': ['req1', 'req2', 'req3']})
        mock_filter_static.return_value = pd.DataFrame({'request_id': ['req1', 'req2']})

        # Mock skill configurations
        configurations = [
            {'skill_id': 'skill1', 'skill_name': 'Skill One', 'skill_priority': 1},
            {'skill_id': 'skill2', 'skill_name': 'Skill Two', 'skill_priority': 2}
        ]

        # Mock requests found for each skill
        mock_find_requests_for_skill.side_effect = [
            pd.DataFrame({'request_id': ['req1'], 'source_externalId': ['ext1'], 'source_orderDate': ['2023-01-01'],
                           'source_requestedStartDate': ['2023-01-02'], 'source_requestSource': ['sourceA'],
                           'source_customerSupportModel': ['modelX'], 'source_requestType': ['typeY'],
                           'source_focTarget': ['targetZ'], 'from_absent_agent': [False], 'source_referredType': ['refT'],
                           'workOrder_product': ['prod1'], 'workOrder_controlDesk': ['desk1'], 'workOrder_followUpDate': ['2023-01-03'],
                           'source_serviceRegion': ['regionA'], 'source_goldenCustomer_name': ['goldCust'],
                           'source_customerMarketSegment': ['segmentB'], 'source_preferredLanguage': ['langC'],
                           'workOrder_status': ['open'], 'workOrder_assignee_id': ['assignee1'], 'has_sla': [True],
                           'is_escalated': [False], 'is_winback': [True], 'is_exclusive_atlantic_routingFilter': [False],
                           'workOrder_tags': [['LOCKED']]}),
            pd.DataFrame({'request_id': ['req2'], 'source_externalId': ['ext2'], 'source_orderDate': ['2023-01-04'],
                           'source_requestedStartDate': ['2023-01-05'], 'source_requestSource': ['sourceB'],
                           'source_customerSupportModel': ['modelW'], 'source_requestType': ['typeV'],
                           'source_focTarget': ['targetU'], 'from_absent_agent': [True], 'source_referredType': ['refS'],
                           'workOrder_product': ['prod2'], 'workOrder_controlDesk': ['desk2'], 'workOrder_followUpDate': ['2023-01-06'],
                           'source_serviceRegion': ['regionB'], 'source_goldenCustomer_name': ['goldCust2'],
                           'source_customerMarketSegment': ['segmentC'], 'source_preferredLanguage': ['langD'],
                           'workOrder_status': ['closed'], 'workOrder_assignee_id': ['assignee2'], 'has_sla': [False],
                           'is_escalated': [True], 'is_winback': [False], 'is_exclusive_atlantic_routingFilter': [True],
                           'workOrder_tags': [[]]})
        ]

        # Expected result after skills filtering and renaming
        expected_result = pd.DataFrame({
            'requestId': ['req1', 'req2'],
            'externalId': ['ext1', 'ext2'],
            'requestOrderDate': ['2023-01-01', '2023-01-04'],
            'requestStartDate': ['2023-01-02', '2023-01-05'],
            'requestSource': ['sourceA', 'sourceB'],
            'customerSupportModel': ['modelX', 'modelW'],
            'requestType': ['typeY', 'typeV'],
            'focTarget': ['targetZ', 'targetU'],
            'fromAbsentAgent': [False, True],
            'referredType': ['refT', 'refS'],
            'skillId': ['skill1', 'skill2'],
            'skillName': ['Skill One', 'Skill Two'],
            'product': ['prod1', 'prod2'],
            'controlDesk': ['desk1', 'desk2'],
            'followUpDate': ['2023-01-03', '2023-01-06'],
            'serviceRegion': ['regionA', 'regionB'],
            'goldenCustomerName': ['goldCust', 'goldCust2'],
            'customerMarketSegment': ['segmentB', 'segmentC'],
            'preferredLanguage': ['langC', 'langD'],
            'requestStatus': ['open', 'closed'],
            'requestAssignee': ['assignee1', 'assignee2'],
            'has_sla': [True, False],
            'is_escalated': [False, True],
            'is_winback': [True, False],
            'is_exclusive_atlantic_routingFilter': [False, True],
            'skillPriority': [1, 2]
        })

        # Call the function
        result = skills_filtering(initial_df, configurations, [], 'tenant', [])

        # Assert that the result is as expected
        pd.testing.assert_frame_equal(result.sort_index(axis=1), expected_result.sort_index(axis=1))

        # Assert that the mock functions were called with the correct arguments
        mock_filter_static.assert_called_once_with(initial_df, 'tenant', [], [])
        self.assertEqual(mock_find_requests_for_skill.call_count, len(configurations))

if __name__ == "__main__":
    unittest.main()