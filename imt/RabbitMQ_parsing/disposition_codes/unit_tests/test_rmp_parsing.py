import sys
import os
import unittest
from unittest import mock
import json

# Add the parent directory to sys.path so parsing_disposition_codes can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parsing_disposition_codes import rmp_parsing

class TestRmpParsing(unittest.TestCase):
    @mock.patch('parsing_disposition_codes.event_change')
    def test_rmp_parsing_calls_event_change_on_change(self, mock_event_change):
        conn = mock.Mock()
        message = json.dumps({
            'sourceId': 'agent1',
            'event': {
                'eventType': 'Change',
                'event': {
                    'params': {
                        'newStatus': 'absent',
                        'oldStatus': 'available'
                    }
                },
                'eventTime': '2025-06-20T12:34:56.123456Z'
            }
        })
        rmp_parsing(message, conn)
        mock_event_change.assert_called_once()

    @mock.patch('parsing_disposition_codes.event_change')
    def test_rmp_parsing_ignores_non_change(self, mock_event_change):
        conn = mock.Mock()
        message = json.dumps({
            'sourceId': 'agent1',
            'event': {
                'eventType': 'OtherType',
                'event': {},
                'eventTime': '2025-06-20T12:34:56.123456Z'
            }
        })
        rmp_parsing(message, conn)
        mock_event_change.assert_not_called()

    def test_rmp_parsing_invalid_json(self):
        conn = mock.Mock()
        with self.assertRaises(json.JSONDecodeError):
            rmp_parsing('not a json', conn)

    def test_rmp_parsing_missing_event_type(self):
        conn = mock.Mock()
        message = json.dumps({
            'sourceId': 'agent1',
            'event': {
                # 'eventType' is missing
                'event': {},
                'eventTime': '2025-06-20T12:34:56.123456Z'
            }
        })
        with self.assertRaises(KeyError):
            rmp_parsing(message, conn)

    def test_rmp_parsing_missing_event(self):
        conn = mock.Mock()
        message = json.dumps({
            'sourceId': 'agent1'
            # 'event' is missing
        })
        with self.assertRaises(KeyError):
            rmp_parsing(message, conn)

if __name__ == '__main__':
    unittest.main()
