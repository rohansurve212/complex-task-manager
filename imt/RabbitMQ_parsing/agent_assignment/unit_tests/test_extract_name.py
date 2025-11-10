import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parsing_agent_skills import extract_name
import unittest

#Testing extract_name
class TestExtractName(unittest.TestCase):

    def test_valid_name(self):
        name_string = "Doe, John"
        expected_full_name = "John Doe"
        actual_full_name = extract_name(name_string)
        self.assertEqual(actual_full_name, expected_full_name)

    def test_valid_name_with_middle_name(self):
        name_string = "Doe, John Michael"
        expected_full_name = "John Doe"
        actual_full_name = extract_name(name_string)
        self.assertEqual(actual_full_name, expected_full_name)

if __name__ == '__main__':
    unittest.main()