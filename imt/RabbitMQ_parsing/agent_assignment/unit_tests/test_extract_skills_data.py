import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parsing_agent_skills import extract_skills_data
import unittest

class TestExtractSkillsData(unittest.TestCase):

    def test_valid_new_value(self):
        """Test with a valid skillsDict and value_type='newValue'."""
        skillsDict = {
            "sourceId": "source123",
            "event": {
                "eventTime": "2024-01-01T10:00:00.123",
                "event": {
                    "newValue": {
                        "queueId": "queue456",
                        "userId": "user789",
                        "individualId": "pein101",
                        "priority": 5
                    }
                }
            }
        }
        source_id, skill_id, agent_id, agent_pein, skill_priority, last_updated = extract_skills_data(skillsDict)
        self.assertEqual(source_id, "source123")
        self.assertEqual(skill_id, "queue456")
        self.assertEqual(agent_id, "user789")
        self.assertEqual(agent_pein, "pein101")
        self.assertEqual(skill_priority, 5)
        self.assertEqual(last_updated, "2024-01-01 10:00:00")

    def test_valid_old_value(self):
        """Test with a valid skillsDict and value_type='oldValue'."""
        skillsDict = {
            "sourceId": "source123",
            "event": {
                "eventTime": "2024-01-01T10:00:00.123",
                "event": {
                    "oldValue": {
                        "queueId": "queue456",
                        "userId": "user789",
                        "individualId": "pein101",
                        "priority": 5
                    }
                }
            }
        }
        source_id, skill_id, agent_id, agent_pein, skill_priority, last_updated = extract_skills_data(skillsDict, value_type='oldValue')
        self.assertEqual(source_id, "source123")
        self.assertEqual(skill_id, "queue456")
        self.assertEqual(agent_id, "user789")
        self.assertEqual(agent_pein, "pein101")
        self.assertEqual(skill_priority, 5)
        self.assertEqual(last_updated, "2024-01-01 10:00:00")

    def test_missing_keys(self):
        """Test with missing keys in the skillsDict."""
        skillsDict = {
            "event": {
                "eventTime": "2024-01-01T10:00:00.123",
                "event": {}
            }
        }
        source_id, skill_id, agent_id, agent_pein, skill_priority, last_updated = extract_skills_data(skillsDict)
        self.assertIsNone(source_id)
        self.assertIsNone(skill_id)
        self.assertIsNone(agent_id)
        self.assertIsNone(agent_pein)
        self.assertIsNone(skill_priority)
        self.assertEqual(last_updated, "2024-01-01 10:00:00")

    def test_missing_event_time(self):
        """Test with missing eventTime in the skillsDict."""
        skillsDict = {
            "sourceId": "source123",
            "event": {
                "event": {
                    "newValue": {
                        "queueId": "queue456",
                        "userId": "user789",
                        "individualId": "pein101",
                        "priority": 5
                    }
                }
            }
        }
        with self.assertRaises(KeyError):
            extract_skills_data(skillsDict)

    def test_invalid_event_time_format(self):
        """Test with an invalid eventTime format in the skillsDict."""
        skillsDict = {
            "sourceId": "source123",
            "event": {
                "eventTime": "2024-01-01 10:00:00",  # Invalid format
                "event": {
                    "newValue": {
                        "queueId": "queue456",
                        "userId": "user789",
                        "individualId": "pein101",
                        "priority": 5
                    }
                }
            }
        }
        with self.assertRaises(ValueError):
            extract_skills_data(skillsDict)

if __name__ == '__main__':
    unittest.main()