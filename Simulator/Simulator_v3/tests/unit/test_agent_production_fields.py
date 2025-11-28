"""
Unit tests for Agent model production routing fields and methods.

Tests the new fields and helper methods added for production routing:
- is_absent
- is_in_followup_window()

Run:
    pytest tests/unit/test_agent_production_fields.py -v
"""

import pytest
from datetime import datetime, timezone
from models import Agent


class TestAgentAbsence:
    """Test agent absence tracking."""
    
    def test_is_absent_default(self):
        """Test default is_absent is False"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        assert agent.is_absent is False
    
    def test_is_absent_true(self):
        """Test setting is_absent to True at initialization"""
        agent = Agent(agent_id="john.doe", full_name="John Doe", is_absent=True)
        assert agent.is_absent is True
    
    def test_is_absent_false_explicit(self):
        """Test explicitly setting is_absent to False"""
        agent = Agent(agent_id="john.doe", full_name="John Doe", is_absent=False)
        assert agent.is_absent is False
    
    def test_set_absent_true(self):
        """Test changing absence status to True"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        agent.is_absent = True
        assert agent.is_absent is True
    
    def test_set_absent_false(self):
        """Test changing absence status to False"""
        agent = Agent(agent_id="john.doe", full_name="John Doe", is_absent=True)
        agent.is_absent = False
        assert agent.is_absent is False
    
    def test_toggle_absent(self):
        """Test toggling absence status multiple times"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        
        agent.is_absent = True
        assert agent.is_absent is True
        
        agent.is_absent = False
        assert agent.is_absent is False
        
        agent.is_absent = True
        assert agent.is_absent is True


class TestFollowupWindow:
    """Test follow-up window detection."""
    
    def test_in_first_window_start(self):
        """Test time at start of first follow-up window (14:00 UTC)"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 2:00 PM UTC (start of window)
        current_time = datetime(2024, 5, 1, 14, 0, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is True
    
    def test_in_first_window_middle(self):
        """Test time in middle of first follow-up window (14:30 UTC)"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 2:30 PM UTC (middle of window)
        current_time = datetime(2024, 5, 1, 14, 30, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is True
    
    def test_in_first_window_end(self):
        """Test time at end of first follow-up window (15:30 UTC)"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 3:30 PM UTC (end of window)
        current_time = datetime(2024, 5, 1, 15, 30, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is True
    
    def test_in_second_window_start(self):
        """Test time at start of second follow-up window (19:30 UTC)"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 7:30 PM UTC (start of window)
        current_time = datetime(2024, 5, 1, 19, 30, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is True
    
    def test_in_second_window_middle(self):
        """Test time in middle of second follow-up window (19:45 UTC)"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 7:45 PM UTC (middle of window)
        current_time = datetime(2024, 5, 1, 19, 45, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is True
    
    def test_in_second_window_end(self):
        """Test time at end of second follow-up window (20:00 UTC)"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 8:00 PM UTC (end of window)
        current_time = datetime(2024, 5, 1, 20, 0, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is True
    
    def test_outside_windows_morning(self):
        """Test time outside follow-up windows (morning)"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 9:00 AM UTC (outside windows)
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is False
    
    def test_outside_windows_afternoon(self):
        """Test time outside follow-up windows (afternoon)"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 4:00 PM UTC (outside windows, between windows)
        current_time = datetime(2024, 5, 1, 16, 0, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is False
    
    def test_outside_windows_evening(self):
        """Test time outside follow-up windows (evening)"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 9:00 PM UTC (outside windows)
        current_time = datetime(2024, 5, 1, 21, 0, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is False
    
    def test_just_before_first_window(self):
        """Test time just before first window starts"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 1:59 PM UTC (just before window)
        current_time = datetime(2024, 5, 1, 13, 59, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is False
    
    def test_just_after_first_window(self):
        """Test time just after first window ends"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 3:31 PM UTC (just after window)
        current_time = datetime(2024, 5, 1, 15, 31, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is False
    
    def test_just_before_second_window(self):
        """Test time just before second window starts"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 7:29 PM UTC (just before window)
        current_time = datetime(2024, 5, 1, 19, 29, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is False
    
    def test_just_after_second_window(self):
        """Test time just after second window ends"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 8:01 PM UTC (just after window)
        current_time = datetime(2024, 5, 1, 20, 1, 0, tzinfo=timezone.utc)
        assert agent.is_in_followup_window(current_time) is False
    
    def test_custom_window_single(self):
        """Test custom follow-up window parameters (single window)"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 10:00 AM UTC
        current_time = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        
        # Custom window: 9:00-11:00 (disable second window)
        assert agent.is_in_followup_window(
            current_time, 
            window_1_start=9.0, 
            window_1_end=11.0,
            window_2_start=99.0,  # Disabled
            window_2_end=99.0
        ) is True
    
    def test_custom_window_different_times(self):
        """Test custom follow-up windows with different times"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 8:30 AM UTC
        current_time = datetime(2024, 5, 1, 8, 30, 0, tzinfo=timezone.utc)
        
        # Custom windows: 8:00-9:00 and 12:00-13:00
        assert agent.is_in_followup_window(
            current_time,
            window_1_start=8.0,
            window_1_end=9.0,
            window_2_start=12.0,
            window_2_end=13.0
        ) is True
    
    def test_custom_window_outside(self):
        """Test time outside custom follow-up windows"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        # 10:00 AM UTC
        current_time = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        
        # Custom windows: 8:00-9:00 and 12:00-13:00
        assert agent.is_in_followup_window(
            current_time,
            window_1_start=8.0,
            window_1_end=9.0,
            window_2_start=12.0,
            window_2_end=13.0
        ) is False


class TestAgentSerialization:
    """Test serialization of new fields."""
    
    def test_to_dict_includes_is_absent(self):
        """Test to_dict includes is_absent field"""
        agent = Agent(agent_id="john.doe", full_name="John Doe", is_absent=True)
        data = agent.to_dict()
        
        assert 'is_absent' in data
        assert data['is_absent'] is True
    
    def test_to_dict_is_absent_false(self):
        """Test to_dict with is_absent=False"""
        agent = Agent(agent_id="john.doe", full_name="John Doe", is_absent=False)
        data = agent.to_dict()
        
        assert 'is_absent' in data
        assert data['is_absent'] is False
    
    def test_from_dict_restores_is_absent_true(self):
        """Test from_dict restores is_absent=True"""
        data = {
            'agent_id': 'john.doe',
            'full_name': 'John Doe',
            'skillsets': ['internet'],
            'is_absent': True
        }
        agent = Agent.from_dict(data)
        assert agent.is_absent is True
    
    def test_from_dict_restores_is_absent_false(self):
        """Test from_dict restores is_absent=False"""
        data = {
            'agent_id': 'john.doe',
            'full_name': 'John Doe',
            'skillsets': ['internet'],
            'is_absent': False
        }
        agent = Agent.from_dict(data)
        assert agent.is_absent is False
    
    def test_from_dict_missing_is_absent(self):
        """Test from_dict with missing is_absent (backward compatibility)"""
        data = {
            'agent_id': 'john.doe',
            'full_name': 'John Doe',
            'skillsets': ['internet']
        }
        # Should not raise exception, should default to False
        agent = Agent.from_dict(data)
        assert agent.is_absent is False
    
    def test_round_trip_serialization(self):
        """Test complete round-trip: Agent -> dict -> Agent"""
        original = Agent(
            agent_id="john.doe",
            full_name="John Doe",
            skillsets={"internet", "voice"},
            is_absent=True
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = Agent.from_dict(data)
        
        # Verify new field matches
        assert restored.is_absent == original.is_absent
        assert restored.agent_id == original.agent_id
        assert restored.full_name == original.full_name

# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--cov=models.agent'])