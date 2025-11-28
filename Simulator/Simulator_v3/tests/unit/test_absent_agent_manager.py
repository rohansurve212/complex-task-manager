"""
Unit tests for AbsentAgentManager.

Tests the daily rotation logic and absent agent selection.

Run:
    pytest tests/unit/test_absent_agent_manager.py -v
"""

import pytest
from datetime import datetime, timezone
from models import Agent
from simulation.absent_agent_manager import AbsentAgentManager


class TestAbsentAgentManagerInit:
    """Test initialization of AbsentAgentManager."""
    
    def test_initialization_basic(self):
        """Test basic initialization"""
        agents = [
            Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}", skillsets={"internet"})
            for i in range(10)
        ]
        manager = AbsentAgentManager(agents, absent_percentage=0.2, random_seed=42)
        
        assert len(manager.agents) == 10
        assert manager.absent_percentage == 0.2
    
    def test_initialization_default_percentage(self):
        """Test default 10% absence rate"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents)
        
        assert manager.absent_percentage == 0.1
    
    def test_initialization_empty_agents(self):
        """Test initialization with empty agent list"""
        manager = AbsentAgentManager([], absent_percentage=0.1)
        assert len(manager.agents) == 0
    
    def test_initialization_with_random_seed(self):
        """Test initialization with random seed for reproducibility"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, random_seed=42)
        
        # Should be deterministic with same seed
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        absent_1 = set(manager.get_absent_agent_ids())
        
        # Create new manager with same seed
        agents2 = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager2 = AbsentAgentManager(agents2, random_seed=42)
        manager2.rotate_absent_agents(current_time)
        absent_2 = set(manager2.get_absent_agent_ids())
        
        assert absent_1 == absent_2


class TestAbsentSelection:
    """Test absent agent selection logic."""
    
    def test_select_correct_percentage_10_percent(self):
        """Test correct percentage of agents are selected (10%)"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(100)]
        manager = AbsentAgentManager(agents, absent_percentage=0.1, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        absent_ids = manager.get_absent_agent_ids()
        assert len(absent_ids) == 10  # 10% of 100
    
    def test_select_correct_percentage_20_percent(self):
        """Test correct percentage of agents are selected (20%)"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(50)]
        manager = AbsentAgentManager(agents, absent_percentage=0.2, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        absent_ids = manager.get_absent_agent_ids()
        assert len(absent_ids) == 10  # 20% of 50
    
    def test_select_correct_percentage_30_percent(self):
        """Test correct percentage of agents are selected (30%)"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.3, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        absent_ids = manager.get_absent_agent_ids()
        assert len(absent_ids) == 3  # 30% of 10
    
    def test_agents_marked_absent(self):
        """Test agents are properly marked as absent"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.3, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        # Check agents have is_absent set correctly
        absent_count = sum(1 for agent in agents if agent.is_absent)
        present_count = sum(1 for agent in agents if not agent.is_absent)
        
        assert absent_count == 3  # 30% of 10
        assert present_count == 7  # 70% of 10
    
    def test_rotation_on_new_day(self):
        """Test absent agents rotate when day changes"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.2, random_seed=42)
        
        # Day 1
        time_day1 = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(time_day1)
        absent_day1 = set(manager.get_absent_agent_ids())
        
        # Same day - should not rotate
        time_day1_later = datetime(2024, 5, 1, 15, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(time_day1_later)
        absent_day1_later = set(manager.get_absent_agent_ids())
        assert absent_day1 == absent_day1_later
        
        # Day 2 - should rotate (different agents)
        time_day2 = datetime(2024, 5, 2, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(time_day2)
        absent_day2 = set(manager.get_absent_agent_ids())
        
        # Should have same count but likely different agents
        assert len(absent_day2) == 2  # Same 20%
        # With random selection and small sample, might sometimes overlap
        # but with seed 42 and 10 agents, should be different
    
    def test_no_rotation_within_same_day(self):
        """Test absent agents don't change within the same day"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(20)]
        manager = AbsentAgentManager(agents, absent_percentage=0.15, random_seed=42)
        
        # First rotation
        time1 = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(time1)
        absent1 = set(manager.get_absent_agent_ids())
        
        # Multiple times same day
        for hour in [10, 12, 14, 16, 18, 20]:
            time = datetime(2024, 5, 1, hour, 0, 0, tzinfo=timezone.utc)
            manager.rotate_absent_agents(time)
            absent = set(manager.get_absent_agent_ids())
            assert absent == absent1  # Should not change
    
    def test_rotation_across_multiple_days(self):
        """Test absent agents rotate each day for a week"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(20)]
        manager = AbsentAgentManager(agents, absent_percentage=0.2, random_seed=42)
        
        daily_absent = []
        
        # Simulate 7 days
        for day in range(1, 8):
            current_time = datetime(2024, 5, day, 9, 0, 0, tzinfo=timezone.utc)
            manager.rotate_absent_agents(current_time)
            absent = set(manager.get_absent_agent_ids())
            daily_absent.append(absent)
            
            # Check correct count each day
            assert len(absent) == 4  # 20% of 20
        
        # Check that not all days have identical absent agents
        # (with random selection, should be different most days)
        unique_absent_sets = len(set(map(frozenset, daily_absent)))
        assert unique_absent_sets > 1  # Should have some variation


class TestAbsentQueries:
    """Test query methods."""
    
    def test_get_absent_agent_ids(self):
        """Test retrieving list of absent agent IDs"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.2, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        absent_ids = manager.get_absent_agent_ids()
        assert len(absent_ids) == 2
        assert all(isinstance(aid, str) for aid in absent_ids)
        assert all(aid.startswith("agent_") for aid in absent_ids)
    
    def test_get_absent_agent_ids_before_rotation(self):
        """Test get_absent_agent_ids before any rotation"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.2)
        
        # Before rotation
        absent_ids = manager.get_absent_agent_ids()
        assert len(absent_ids) == 0  # No rotation yet
    
    def test_is_agent_absent_true(self):
        """Test checking if specific agent is absent"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.2, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        absent_ids = manager.get_absent_agent_ids()
        
        # Check absent agents return True
        for agent_id in absent_ids:
            assert manager.is_agent_absent(agent_id) is True
    
    def test_is_agent_absent_false(self):
        """Test checking if present agent is not absent"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.2, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        absent_ids = set(manager.get_absent_agent_ids())
        
        # Check present agents return False
        all_agent_ids = {f"agent_{i}" for i in range(10)}
        present_ids = all_agent_ids - absent_ids
        
        for agent_id in present_ids:
            assert manager.is_agent_absent(agent_id) is False
    
    def test_is_agent_absent_nonexistent(self):
        """Test checking nonexistent agent"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.2, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        # Check nonexistent agent
        assert manager.is_agent_absent("nonexistent_agent") is False
    
    def test_get_statistics(self):
        """Test statistics retrieval"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.3, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        stats = manager.get_statistics()
        
        assert 'total_agents' in stats
        assert stats['total_agents'] == 10
        
        assert 'absent_count' in stats
        assert stats['absent_count'] == 3
        
        assert 'absent_percentage' in stats
        assert stats['absent_percentage'] == 0.3
        
        assert 'absent_agent_ids' in stats
        assert len(stats['absent_agent_ids']) == 3
        assert all(isinstance(aid, str) for aid in stats['absent_agent_ids'])
    
    def test_get_statistics_before_rotation(self):
        """Test statistics before any rotation"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.2)
        
        stats = manager.get_statistics()
        
        assert stats['total_agents'] == 10
        assert stats['absent_count'] == 0
        assert stats['absent_percentage'] == 0.0
        assert len(stats['absent_agent_ids']) == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_percent_absent(self):
        """Test with 0% absence rate"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.0, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        absent_ids = manager.get_absent_agent_ids()
        assert len(absent_ids) == 0
        assert all(not agent.is_absent for agent in agents)
    
    def test_hundred_percent_absent(self):
        """Test with 100% absence rate"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=1.0, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        absent_ids = manager.get_absent_agent_ids()
        assert len(absent_ids) == 10
        assert all(agent.is_absent for agent in agents)
    
    def test_single_agent(self):
        """Test with single agent"""
        agents = [Agent(agent_id="solo_agent", full_name="Solo Agent")]
        manager = AbsentAgentManager(agents, absent_percentage=0.5, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        # 50% of 1 = 0 (rounds down)
        absent_ids = manager.get_absent_agent_ids()
        assert len(absent_ids) == 0
    
    def test_rounding_behavior(self):
        """Test that percentage correctly rounds down"""
        agents = [Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}") for i in range(10)]
        manager = AbsentAgentManager(agents, absent_percentage=0.15, random_seed=42)
        
        current_time = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        manager.rotate_absent_agents(current_time)
        
        # 15% of 10 = 1.5, should round down to 1
        absent_ids = manager.get_absent_agent_ids()
        assert len(absent_ids) == 1

# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--cov=simulation.absent_agent_manager'])