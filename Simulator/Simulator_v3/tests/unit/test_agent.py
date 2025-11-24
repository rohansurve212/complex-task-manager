"""
Unit tests for Agent model.

Run with: pytest tests/unit/test_agent.py -v
"""

import pytest

# Import components to test
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.agent import Agent, AgentState


# ============================================================================
# TEST: Agent Creation
# ============================================================================

class TestAgentCreation:
    """Test suite for creating Agent objects"""
    
    def test_create_minimal_agent(self):
        """Test creating agent with only required fields"""
        agent = Agent(
            agent_id="john.doe",
            full_name="John Doe"
        )
        
        assert agent.agent_id == "john.doe"
        assert agent.full_name == "John Doe"
        assert agent.state == AgentState.IDLE
        assert len(agent.skillsets) == 0
        assert agent.current_request is None
    
    def test_create_agent_with_skills(self):
        """Test creating agent with skillsets"""
        agent = Agent(
            agent_id="jane.smith",
            full_name="Jane Smith",
            skillsets={"internet", "voice", "tv"}
        )
        
        assert len(agent.skillsets) == 3
        assert agent.has_skill("internet")
        assert agent.has_skill("voice")
        assert agent.has_skill("tv")
    
    def test_create_agent_with_all_fields(self):
        """Test creating agent with all optional fields"""
        agent = Agent(
            agent_id="bob.wilson",
            full_name="Bob Wilson",
            skillsets={"internet"},
            permissions={"region": "ontario", "product": "internet"},
            manager_name="Sarah Johnson",
            cp2_name="Toronto Team",
            cp3_name="Ontario Region",
            metadata={"hire_date": "2020-01-15"}
        )
        
        assert agent.manager_name == "Sarah Johnson"
        assert agent.cp2_name == "Toronto Team"
        assert agent.cp3_name == "Ontario Region"
        assert "region" in agent.permissions
    
    def test_create_agent_empty_id_fails(self):
        """Test that empty agent_id raises error"""
        with pytest.raises(ValueError, match="agent_id cannot be empty"):
            Agent(agent_id="", full_name="John Doe")
    
    def test_create_agent_empty_name_fails(self):
        """Test that empty full_name raises error"""
        with pytest.raises(ValueError, match="full_name cannot be empty"):
            Agent(agent_id="john.doe", full_name="")
    
    def test_agent_id_whitespace_stripped(self):
        """Test that whitespace is stripped from agent_id"""
        agent = Agent(
            agent_id="  john.doe  ",
            full_name="  John Doe  "
        )
        
        assert agent.agent_id == "john.doe"
        assert agent.full_name == "John Doe"


# ============================================================================
# TEST: State Management
# ============================================================================

class TestAgentStateManagement:
    """Test suite for agent state transitions"""
    
    def test_initial_state_is_idle(self):
        """Test that new agents start in IDLE state"""
        agent = Agent(agent_id="john", full_name="John")
        assert agent.state == AgentState.IDLE
        assert agent.is_available
        assert not agent.is_working
    
    def test_set_state_to_working(self):
        """Test transitioning to WORKING state"""
        agent = Agent(agent_id="john", full_name="John")
        agent.set_state(AgentState.WORKING, timestamp=100.0)
        
        assert agent.state == AgentState.WORKING
        assert not agent.is_available
        assert agent.is_working
    
    def test_set_state_to_unavailable(self):
        """Test transitioning to UNAVAILABLE state"""
        agent = Agent(agent_id="john", full_name="John")
        agent.set_state(AgentState.UNAVAILABLE, timestamp=100.0)
        
        assert agent.state == AgentState.UNAVAILABLE
        assert not agent.is_available
        assert not agent.is_working
    
    def test_make_available_convenience_method(self):
        """Test make_available() convenience method"""
        agent = Agent(agent_id="john", full_name="John")
        agent.set_state(AgentState.WORKING, timestamp=0.0)
        agent.make_available(timestamp=100.0)
        
        assert agent.is_available
    
    def test_make_unavailable_convenience_method(self):
        """Test make_unavailable() convenience method"""
        agent = Agent(agent_id="john", full_name="John")
        agent.make_unavailable(timestamp=100.0)
        
        assert agent.state == AgentState.UNAVAILABLE
    
    def test_invalid_state_raises_error(self):
        """Test that invalid state raises ValueError"""
        agent = Agent(agent_id="john", full_name="John")
        
        with pytest.raises(ValueError, match="Invalid state"):
            agent.set_state("invalid_state")


# ============================================================================
# TEST: Work Assignment
# ============================================================================

class TestWorkAssignment:
    """Test suite for request assignment and completion"""
    
    def test_assign_request_when_idle(self):
        """Test assigning request to idle agent"""
        agent = Agent(agent_id="john", full_name="John")
        agent.assign_request("REQ_001", timestamp=100.0)
        
        assert agent.current_request == "REQ_001"
        assert agent.is_working
        assert len(agent.work_history) == 1
        assert agent.work_history[0]['request_id'] == "REQ_001"
        assert agent.work_history[0]['assigned_at'] == 100.0
        assert agent.work_history[0]['completed_at'] is None
    
    def test_cannot_assign_when_working(self):
        """Test that assigning to working agent raises error"""
        agent = Agent(agent_id="john", full_name="John")
        agent.assign_request("REQ_001", timestamp=100.0)
        
        with pytest.raises(ValueError, match="not available"):
            agent.assign_request("REQ_002", timestamp=200.0)
    
    def test_cannot_assign_empty_request_id(self):
        """Test that empty request_id raises error"""
        agent = Agent(agent_id="john", full_name="John")
        
        with pytest.raises(ValueError, match="request_id cannot be empty"):
            agent.assign_request("", timestamp=100.0)
    
    def test_complete_request(self):
        """Test completing assigned request"""
        agent = Agent(agent_id="john", full_name="John")
        agent.assign_request("REQ_001", timestamp=100.0)
        completed_id = agent.complete_request(timestamp=250.0)
        
        assert completed_id == "REQ_001"
        assert agent.current_request is None
        assert agent.is_available
        
        # Check work history
        assert agent.work_history[0]['completed_at'] == 250.0
        assert agent.work_history[0]['duration'] == 150.0
    
    def test_complete_request_without_assignment_fails(self):
        """Test that completing without assignment raises error"""
        agent = Agent(agent_id="john", full_name="John")
        
        with pytest.raises(RuntimeError, match="no current request"):
            agent.complete_request(timestamp=100.0)
    
    def test_multiple_assignments(self):
        """Test multiple assignments over time"""
        agent = Agent(agent_id="john", full_name="John")
        
        # First assignment
        agent.assign_request("REQ_001", timestamp=0.0)
        agent.complete_request(timestamp=100.0)
        
        # Second assignment
        agent.assign_request("REQ_002", timestamp=150.0)
        agent.complete_request(timestamp=300.0)
        
        # Third assignment
        agent.assign_request("REQ_003", timestamp=350.0)
        agent.complete_request(timestamp=500.0)
        
        assert len(agent.work_history) == 3
        assert agent.work_count == 3
        assert all(w['completed_at'] is not None for w in agent.work_history)
    
    def test_work_history_with_metadata(self):
        """Test that metadata is stored in work history"""
        agent = Agent(agent_id="john", full_name="John")
        
        agent.assign_request(
            "REQ_001",
            timestamp=100.0,
            metadata={"skill_id": "internet", "priority": "high"}
        )
        
        assert agent.work_history[0]['skill_id'] == "internet"
        assert agent.work_history[0]['priority'] == "high"


# ============================================================================
# TEST: Skills Management
# ============================================================================

class TestSkillsManagement:
    """Test suite for skill-related operations"""
    
    def test_has_skill(self):
        """Test checking for specific skill"""
        agent = Agent(
            agent_id="john",
            full_name="John",
            skillsets={"internet", "voice"}
        )
        
        assert agent.has_skill("internet")
        assert agent.has_skill("voice")
        assert not agent.has_skill("tv")
    
    def test_has_any_skill(self):
        """Test checking for any of multiple skills"""
        agent = Agent(
            agent_id="john",
            full_name="John",
            skillsets={"internet"}
        )
        
        assert agent.has_any_skill(["internet", "voice"])
        assert agent.has_any_skill(["voice", "internet"])
        assert not agent.has_any_skill(["tv", "voice"])
    
    def test_has_all_skills(self):
        """Test checking for all specified skills"""
        agent = Agent(
            agent_id="john",
            full_name="John",
            skillsets={"internet", "voice", "tv"}
        )
        
        assert agent.has_all_skills(["internet", "voice"])
        assert agent.has_all_skills(["internet"])
        assert not agent.has_all_skills(["internet", "voice", "phone"])
    
    def test_add_skill(self):
        """Test adding a new skill"""
        agent = Agent(
            agent_id="john",
            full_name="John",
            skillsets={"internet"}
        )
        
        agent.add_skill("voice")
        
        assert agent.has_skill("voice")
        assert len(agent.skillsets) == 2
    
    def test_remove_skill(self):
        """Test removing a skill"""
        agent = Agent(
            agent_id="john",
            full_name="John",
            skillsets={"internet", "voice"}
        )
        
        removed = agent.remove_skill("voice")
        
        assert removed is True
        assert not agent.has_skill("voice")
        assert len(agent.skillsets) == 1
    
    def test_remove_nonexistent_skill(self):
        """Test removing skill that doesn't exist"""
        agent = Agent(
            agent_id="john",
            full_name="John",
            skillsets={"internet"}
        )
        
        removed = agent.remove_skill("tv")
        
        assert removed is False
        assert len(agent.skillsets) == 1
    
    def test_skills_list_property(self):
        """Test skills_list property returns sorted list"""
        agent = Agent(
            agent_id="john",
            full_name="John",
            skillsets={"voice", "internet", "tv"}
        )
        
        skills = agent.skills_list
        
        assert isinstance(skills, list)
        assert skills == sorted(skills)  # Should be sorted
        assert len(skills) == 3


# ============================================================================
# TEST: Metrics Calculation
# ============================================================================

class TestMetricsCalculation:
    """Test suite for metrics and calculations"""
    
    def test_work_count_empty(self):
        """Test work count for new agent"""
        agent = Agent(agent_id="john", full_name="John")
        assert agent.work_count == 0
    
    def test_work_count_after_assignments(self):
        """Test work count after completing work"""
        agent = Agent(agent_id="john", full_name="John")
        
        agent.assign_request("REQ_001", timestamp=0.0)
        agent.complete_request(timestamp=100.0)
        assert agent.work_count == 1
        
        agent.assign_request("REQ_002", timestamp=150.0)
        agent.complete_request(timestamp=250.0)
        assert agent.work_count == 2
    
    def test_work_count_excludes_incomplete(self):
        """Test that work count only includes completed work"""
        agent = Agent(agent_id="john", full_name="John")
        
        agent.assign_request("REQ_001", timestamp=0.0)
        agent.complete_request(timestamp=100.0)
        
        agent.assign_request("REQ_002", timestamp=150.0)
        # Don't complete second request
        
        assert agent.work_count == 1  # Only first is completed
    
    def test_calculate_utilization_zero_time(self):
        """Test utilization with zero simulation time"""
        agent = Agent(agent_id="john", full_name="John")
        utilization = agent.calculate_utilization(total_simulation_time=0.0)
        assert utilization == 0.0
    
    def test_calculate_utilization_basic(self):
        """Test basic utilization calculation"""
        agent = Agent(agent_id="john", full_name="John")
        
        agent.assign_request("REQ_001", timestamp=0.0)
        agent.complete_request(timestamp=100.0)  # Worked for 100 seconds
        
        utilization = agent.calculate_utilization(total_simulation_time=200.0)
        assert utilization == 0.5  # 100/200 = 50%
    
    def test_average_handle_time_none_when_no_work(self):
        """Test average handle time with no completed work"""
        agent = Agent(agent_id="john", full_name="John")
        avg_time = agent.get_average_handle_time()
        assert avg_time is None
    
    def test_average_handle_time_single_request(self):
        """Test average handle time with one request"""
        agent = Agent(agent_id="john", full_name="John")
        
        agent.assign_request("REQ_001", timestamp=0.0)
        agent.complete_request(timestamp=150.0)
        
        avg_time = agent.get_average_handle_time()
        assert avg_time == 150.0
    
    def test_average_handle_time_multiple_requests(self):
        """Test average handle time with multiple requests"""
        agent = Agent(agent_id="john", full_name="John")
        
        agent.assign_request("REQ_001", timestamp=0.0)
        agent.complete_request(timestamp=100.0)  # 100 seconds
        
        agent.assign_request("REQ_002", timestamp=150.0)
        agent.complete_request(timestamp=350.0)  # 200 seconds
        
        avg_time = agent.get_average_handle_time()
        assert avg_time == 150.0  # (100 + 200) / 2


# ============================================================================
# TEST: Data Conversion
# ============================================================================

class TestDataConversion:
    """Test suite for data conversion methods"""
    
    def test_to_dict(self):
        """Test converting agent to dictionary"""
        agent = Agent(
            agent_id="john.doe",
            full_name="John Doe",
            skillsets={"internet", "voice"},
            manager_name="Sarah Johnson"
        )
        
        data = agent.to_dict()
        
        assert data['agent_id'] == "john.doe"
        assert data['full_name'] == "John Doe"
        assert isinstance(data['skillsets'], list)
        assert len(data['skillsets']) == 2
        assert data['state'] == "idle"
        assert data['manager_name'] == "Sarah Johnson"
    
    def test_to_production_format(self):
        """Test converting to production format"""
        agent = Agent(
            agent_id="john.doe",
            full_name="John Doe",
            skillsets={"internet", "voice"},
            permissions={"region": "ontario"},
            cp2_name="Toronto Team"
        )
        
        prod_data = agent.to_production_format()
        
        assert prod_data['agent_id'] == "john.doe"
        assert prod_data['full_name'] == "John Doe"
        assert isinstance(prod_data['skillsets'], list)
        assert 'permissions' in prod_data
        assert prod_data['CP2_name'] == "Toronto Team"
    
    def test_from_dict(self):
        """Test creating agent from dictionary"""
        data = {
            'agent_id': 'jane.smith',
            'full_name': 'Jane Smith',
            'skillsets': ['internet', 'tv'],
            'permissions': {'region': 'ontario'},
            'manager_name': 'Sarah Johnson',
            'cp2_name': 'Toronto Team',
            'cp3_name': 'Ontario Region'
        }
        
        agent = Agent.from_dict(data)
        
        assert agent.agent_id == 'jane.smith'
        assert agent.full_name == 'Jane Smith'
        assert agent.has_skill('internet')
        assert agent.has_skill('tv')
        assert agent.manager_name == 'Sarah Johnson'
    
    def test_round_trip_conversion(self):
        """Test converting to dict and back"""
        original = Agent(
            agent_id="bob.wilson",
            full_name="Bob Wilson",
            skillsets={"internet"},
            manager_name="Mike Peters"
        )
        
        data = original.to_dict()
        reconstructed = Agent.from_dict(data)
        
        assert reconstructed.agent_id == original.agent_id
        assert reconstructed.full_name == original.full_name
        assert reconstructed.skillsets == original.skillsets


# ============================================================================
# TEST: Special Methods
# ============================================================================

class TestSpecialMethods:
    """Test suite for __repr__, __str__, __eq__, __hash__"""
    
    def test_repr(self):
        """Test __repr__ for debugging"""
        agent = Agent(
            agent_id="john.doe",
            full_name="John Doe",
            skillsets={"internet"}
        )
        
        repr_str = repr(agent)
        assert "john.doe" in repr_str
        assert "John Doe" in repr_str
        assert "IDLE" in repr_str
    
    def test_str(self):
        """Test __str__ for display"""
        agent = Agent(agent_id="john.doe", full_name="John Doe")
        str_representation = str(agent)
        
        assert "John Doe" in str_representation
        assert "john.doe" in str_representation
        assert "IDLE" in str_representation.upper()
    
    def test_equality_based_on_id(self):
        """Test that agents are equal if they have same ID"""
        agent1 = Agent(agent_id="john.doe", full_name="John Doe")
        agent2 = Agent(agent_id="john.doe", full_name="John Doe Jr.")
        agent3 = Agent(agent_id="jane.smith", full_name="Jane Smith")
        
        assert agent1 == agent2  # Same ID
        assert agent1 != agent3  # Different ID
    
    def test_hash_for_sets(self):
        """Test that agents can be used in sets"""
        agent1 = Agent(agent_id="john.doe", full_name="John")
        agent2 = Agent(agent_id="jane.smith", full_name="Jane")
        agent3 = Agent(agent_id="john.doe", full_name="John Jr.")  # Same ID as agent1
        
        agent_set = {agent1, agent2, agent3}
        
        # Only 2 agents in set because agent1 and agent3 have same ID
        assert len(agent_set) == 2
    
    def test_hash_for_dict_keys(self):
        """Test that agents can be used as dict keys"""
        agent1 = Agent(agent_id="john.doe", full_name="John")
        agent2 = Agent(agent_id="jane.smith", full_name="Jane")
        
        agent_data = {
            agent1: {"requests": 5},
            agent2: {"requests": 3}
        }
        
        assert agent_data[agent1]["requests"] == 5
        assert agent_data[agent2]["requests"] == 3


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--cov=models.agent'])