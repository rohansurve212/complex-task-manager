import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parsing_agent_skills import rmp_parsing

class TestRmpParsing(unittest.TestCase):
    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.event_create')
    @patch('parsing_agent_skills.event_change')
    @patch('parsing_agent_skills.event_delete')
    def test_create_event(self, mock_event_delete, mock_event_change, mock_event_create, mock_logger):
        conn = MagicMock()
        message = json.dumps({
            "sourceId": "src1",
            "event": {"eventType": "Create"}
        })
        rmp_parsing(message, conn)
        mock_event_create.assert_called_once()
        mock_event_change.assert_not_called()
        mock_event_delete.assert_not_called()
        mock_logger.info.assert_any_call('Starting event for sourceId src1... The eventType is Create.')

    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.event_create')
    @patch('parsing_agent_skills.event_change')
    @patch('parsing_agent_skills.event_delete')
    def test_change_event(self, mock_event_delete, mock_event_change, mock_event_create, mock_logger):
        conn = MagicMock()
        message = json.dumps({
            "sourceId": "src2",
            "event": {"eventType": "Change"}
        })
        rmp_parsing(message, conn)
        mock_event_create.assert_not_called()
        mock_event_change.assert_called_once()
        mock_event_delete.assert_not_called()
        mock_logger.info.assert_any_call('Starting event for sourceId src2... The eventType is Change.')

    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.event_create')
    @patch('parsing_agent_skills.event_change')
    @patch('parsing_agent_skills.event_delete')
    def test_delete_event(self, mock_event_delete, mock_event_change, mock_event_create, mock_logger):
        conn = MagicMock()
        message = json.dumps({
            "sourceId": "src3",
            "event": {"eventType": "Delete"}
        })
        rmp_parsing(message, conn)
        mock_event_create.assert_not_called()
        mock_event_change.assert_not_called()
        mock_event_delete.assert_called_once()
        mock_logger.info.assert_any_call('Starting event for sourceId src3... The eventType is Delete.')

    @patch('parsing_agent_skills.logger')
    @patch('parsing_agent_skills.event_create')
    @patch('parsing_agent_skills.event_change')
    @patch('parsing_agent_skills.event_delete')
    def test_unknown_event_type(self, mock_event_delete, mock_event_change, mock_event_create, mock_logger):
        conn = MagicMock()
        message = json.dumps({
            "sourceId": "src4",
            "event": {"eventType": "Unknown"}
        })
        rmp_parsing(message, conn)
        mock_event_create.assert_not_called()
        mock_event_change.assert_not_called()
        mock_event_delete.assert_not_called()
        mock_logger.info.assert_any_call('Starting event for sourceId src4... The eventType is Unknown.')

if __name__ == '__main__':
    unittest.main()
