import sys
import os
import unittest
from unittest import mock
from datetime import datetime

# Add the parent directory to sys.path so parsing_disposition_codes can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parsing_disposition_codes import event_change

class TestEventChange(unittest.TestCase):
    def setUp(self):
        self.conn = mock.Mock()
        self.cursor = mock.Mock()
        self.conn.cursor.return_value = self.cursor
        self.skillsDict = {
            'sourceId': 'agent1',
            'event': {
                'event': {
                    'params': {
                        'newStatus': 'absent',
                        'oldStatus': 'available'
                    }
                },
                'eventTime': '2025-06-20T12:34:56.123456Z'
            }
        }

    @mock.patch('parsing_disposition_codes.update_is_absent')
    @mock.patch('parsing_disposition_codes.logger')
    def test_event_change_new_status_absent(self, mock_logger, mock_update_is_absent):
        event_change(self.conn, self.skillsDict)
        mock_update_is_absent.assert_any_call(self.conn, 'agent1', 'True')
        self.cursor.execute.assert_called()
        self.conn.commit.assert_called()
        mock_logger.info.assert_any_call(
            'Changing disposition status for agent agent1 from available to absent at timestamp 2025-06-20 12:34:56')

    @mock.patch('parsing_disposition_codes.update_is_absent')
    @mock.patch('parsing_disposition_codes.logger')
    def test_event_change_old_status_absent(self, mock_logger, mock_update_is_absent):
        self.skillsDict['event']['event']['params']['newStatus'] = 'available'
        self.skillsDict['event']['event']['params']['oldStatus'] = 'absent'
        event_change(self.conn, self.skillsDict)
        mock_update_is_absent.assert_any_call(self.conn, 'agent1', 'False')
        self.cursor.execute.assert_called()
        self.conn.commit.assert_called()

    @mock.patch('parsing_disposition_codes.update_is_absent')
    @mock.patch('parsing_disposition_codes.logger')
    def test_event_change_both_statuses_absent(self, mock_logger, mock_update_is_absent):
        self.skillsDict['event']['event']['params']['newStatus'] = 'absent'
        self.skillsDict['event']['event']['params']['oldStatus'] = 'absent'
        event_change(self.conn, self.skillsDict)
        mock_update_is_absent.assert_any_call(self.conn, 'agent1', 'True')
        mock_update_is_absent.assert_any_call(self.conn, 'agent1', 'False')
        self.cursor.execute.assert_called()
        self.conn.commit.assert_called()

    @mock.patch('parsing_disposition_codes.update_is_absent')
    @mock.patch('parsing_disposition_codes.logger')
    def test_event_change_update_exception(self, mock_logger, mock_update_is_absent):
        self.cursor.execute.side_effect = Exception('DB error')
        event_change(self.conn, self.skillsDict)
        self.conn.rollback.assert_called()
        mock_logger.exception.assert_called()

    @mock.patch('parsing_disposition_codes.update_is_absent')
    @mock.patch('parsing_disposition_codes.logger')
    def test_event_change_missing_keys(self, mock_logger, mock_update_is_absent):
        # Remove 'oldStatus' key
        broken_dict = {
            'sourceId': 'agent1',
            'event': {
                'event': {
                    'params': {
                        'newStatus': 'absent'
                    }
                },
                'eventTime': '2025-06-20T12:34:56.123456Z'
            }
        }
        with self.assertRaises(KeyError):
            event_change(self.conn, broken_dict)

    @mock.patch('parsing_disposition_codes.update_is_absent')
    @mock.patch('parsing_disposition_codes.logger')
    def test_event_change_invalid_event_time(self, mock_logger, mock_update_is_absent):
        # Invalid eventTime format
        self.skillsDict['event']['eventTime'] = 'not-a-date'
        with self.assertRaises(ValueError):
            event_change(self.conn, self.skillsDict)

if __name__ == '__main__':
    unittest.main()
