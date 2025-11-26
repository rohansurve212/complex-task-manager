"""
Phase 1 Integration Tests

Tests that verify all Phase 1 components work together:
- Configuration System (Task #1)
- Agent Model (Task #2)
- Request Model (Task #3)
- Request Pool (Task #4)

Run with: pytest tests/integration/test_phase1_integration.py -v
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
import tempfile
import yaml

# Import all Phase 1 components
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from config.scenario_config import (
    ScenarioConfig,
    SimulationParameters,
    DataSourceConfig,
    AgentBehaviorConfig,
    OutputConfig,
    load_scenario_from_yaml
)
from models.agent import Agent
from models.request import Request, RequestState
from models.request_pool import RequestPool
from models.data_loader import (
    load_agents_from_csv,
    load_requests_from_csv,
)


# ============================================================================
# TEST: Configuration + Data Loading Integration
# ============================================================================

class TestConfigurationDataIntegration:
    """Test configuration system with data loading"""
    
    def test_load_config_and_data(self):
        """Test loading configuration and then loading data based on config"""
        # Create temporary config
        config_data = {
            'scenario_name': 'integration_test',
            'description': 'Integration test scenario',
            'simulation': {
                'start_date': '2024-05-01',
                'end_date': '2024-05-08',
                'default_ttpu': 8.0,
                'prioritization_algorithm': 'foc'
            },
            'data_sources': {
                'use_database': False,
                'agents_csv': str(Path('tests/fixtures/sample_agents.csv')),
                'requests_csv': str(Path('tests/fixtures/sample_requests.csv'))
            },
            'agent_behavior': {
                'behavior_type': 'deterministic'
            },
            'output': {
                'output_directory': './test_results'
            }
        }
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            # Load configuration
            config = load_scenario_from_yaml(temp_path)
            assert config.scenario_name == 'integration_test'
            
            # Load data based on config
            if Path(config.data_sources.agents_csv).exists():
                agents = load_agents_from_csv(Path(config.data_sources.agents_csv))
                assert len(agents) > 0
                
            if Path(config.data_sources.requests_csv).exists():
                requests = load_requests_from_csv(Path(config.data_sources.requests_csv))
                assert len(requests) > 0
                
        finally:
            temp_path.unlink()
    
    def test_simulation_parameters_with_requests(self):
        """Test using simulation parameters for request aging"""
        # Create config
        config = ScenarioConfig(
            scenario_name="test",
            simulation=SimulationParameters(
                start_date="2024-05-01",
                end_date="2024-05-08"
            ),
            data_sources=DataSourceConfig(use_database=False),
            agent_behavior=AgentBehaviorConfig(behavior_type='deterministic'),
            output=OutputConfig()
        )
        
        # Create request at simulation start
        start_time = datetime.fromisoformat(config.simulation.start_date).replace(tzinfo=timezone.utc)
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=start_time
        )
        
        # Calculate age at simulation end
        end_time = datetime.fromisoformat(config.simulation.end_date).replace(tzinfo=timezone.utc)
        age_days = request.get_age_days(end_time)
        
        # Should be 7 days (May 1 to May 8)
        assert age_days == 7.0


# ============================================================================
# TEST: Agent + Request Integration
# ============================================================================

class TestAgentRequestIntegration:
    """Test Agent and Request models working together"""
    
    def test_agent_request_assignment(self):
        """Test assigning request to agent"""
        # Create agent
        agent = Agent(
            agent_id="john.doe",
            full_name="John Doe",
            skillsets={"internet", "voice"}
        )
        
        # Create request
        current_time = datetime.now(timezone.utc)
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=current_time - timedelta(hours=2)
        )
        
        # Both should start available/new
        assert agent.is_available
        assert request.is_new
        
        # Assign request to agent
        agent.assign_request(request.request_id, current_time)
        request.assign_to_agent(agent.agent_id, current_time)
        
        # Verify both updated correctly
        assert agent.is_working
        assert agent.current_request == request.request_id
        assert request.is_assigned
        assert request.assigned_agent_id == agent.agent_id
        
        # Complete the request
        completion_time = current_time + timedelta(hours=1)
        agent.complete_request(completion_time)
        request.mark_completed(completion_time)
        
        # Both should be complete/idle
        assert agent.is_available
        assert agent.current_request is None
        assert request.is_completed
        assert request.get_handle_time_seconds() == 3600.0
    
    def test_skill_matching(self):
        """Test that agent skills match request requirements"""
        # Create agent with specific skills
        agent = Agent(
            agent_id="jane.smith",
            full_name="Jane Smith",
            skillsets={"internet", "tv"}
        )
        
        # Create requests with different skills
        internet_req = Request(
            request_id="REQ_INT",
            external_id="EXT_INT",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        voice_req = Request(
            request_id="REQ_VOICE",
            external_id="EXT_VOICE",
            skill_id="voice",
            request_source="bcom",
            product="voice",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        # Agent should have internet skill but not voice
        assert agent.has_skill(internet_req.skill_id)
        assert not agent.has_skill(voice_req.skill_id)
    
    def test_multiple_agents_multiple_requests(self):
        """Test managing multiple agents and requests"""
        # Create agents
        agents = [
            Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}", 
                  skillsets={"internet", "voice"})
            for i in range(3)
        ]
        
        # Create requests
        base_time = datetime.now(timezone.utc)
        requests = [
            Request(
                request_id=f"REQ_{i:03d}",
                external_id=f"EXT_{i:03d}",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=base_time - timedelta(hours=i)
            )
            for i in range(5)
        ]
        
        # Assign requests to agents (round-robin)
        assignment_time = datetime.now(timezone.utc)
        for i, request in enumerate(requests[:3]):  # Only assign 3
            agent = agents[i]
            agent.assign_request(request.request_id, assignment_time)
            request.assign_to_agent(agent.agent_id, assignment_time)
        
        # Verify assignments
        working_agents = [a for a in agents if a.is_working]
        idle_agents = [a for a in agents if a.is_available]
        assigned_requests = [r for r in requests if r.is_assigned]
        new_requests = [r for r in requests if r.is_new]
        
        assert len(working_agents) == 3
        assert len(idle_agents) == 0
        assert len(assigned_requests) == 3
        assert len(new_requests) == 2


# ============================================================================
# TEST: RequestPool + Agent + Request Integration
# ============================================================================

class TestPoolAgentRequestIntegration:
    """Test complete integration of all three models"""
    
    def test_complete_routing_workflow(self):
        """Test complete workflow: pool → filter → sort → assign"""
        # Create pool
        pool = RequestPool()
        
        # Add requests with different priorities
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        requests = [
            Request(
                request_id=f"REQ_{i:03d}",
                external_id=f"EXT_{i:03d}",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=base_time - timedelta(hours=i*2),  # Different ages
                foc_target=8.0
            )
            for i in range(5)
        ]
        pool.add_requests(requests)
        
        # Create agents
        agents = [
            Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}",
                  skillsets={"internet", "voice"})
            for i in range(2)
        ]
        
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # Routing workflow
        # 1. Get available requests for skill
        available = pool.get_available_requests(skill_id="internet")
        assert len(available) == 5
        
        # 2. Sort by priority
        sorted_requests = pool.sort_by_priority(available, current_time, descending=True)
        
        # 3. Assign to available agents
        for agent in agents:
            if sorted_requests and agent.is_available:
                request = sorted_requests.pop(0)
                
                # Update pool
                pool.assign_request_to_agent(request.request_id, agent.agent_id, current_time)
                
                # Update agent
                agent.assign_request(request.request_id, current_time)
                
                # Verify
                assert agent.is_working
                assert pool.get_request(request.request_id).is_assigned
        
        # Check results
        assert len([a for a in agents if a.is_working]) == 2
        assert len(pool.get_requests_by_state(RequestState.ASSIGNED)) == 2
        assert len(pool.get_available_requests(skill_id="internet")) == 3
    
    def test_multi_skill_routing(self):
        """Test routing with multiple skills"""
        pool = RequestPool()
        
        # Add requests with different skills
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        for skill in ["internet", "voice", "tv"]:
            for i in range(3):
                request = Request(
                    request_id=f"REQ_{skill}_{i}",
                    external_id=f"EXT_{skill}_{i}",
                    skill_id=skill,
                    request_source="bcom",
                    product=skill,
                    service_region="ontario",
                    request_type="new",
                    order_date=base_time
                )
                pool.add_request(request)
        
        # Create agents with different skills
        agents = [
            Agent(agent_id="agent_1", full_name="Agent 1", skillsets={"internet"}),
            Agent(agent_id="agent_2", full_name="Agent 2", skillsets={"voice", "tv"}),
            Agent(agent_id="agent_3", full_name="Agent 3", skillsets={"internet", "voice", "tv"})
        ]
        
        current_time = datetime.now(timezone.utc)
        
        # Route for each agent
        for agent in agents:
            for skill in agent.skillsets:
                available = pool.get_available_requests(skill_id=skill)
                if available and agent.is_available:
                    request = available[0]
                    pool.assign_request_to_agent(request.request_id, agent.agent_id, current_time)
                    agent.assign_request(request.request_id, current_time)
                    break
        
        # All agents should be working
        assert all(agent.is_working for agent in agents)
        assert len(pool.get_requests_by_state(RequestState.ASSIGNED)) == 3
        assert len(pool.get_requests_by_state(RequestState.NEW)) == 6
    
    def test_priority_based_assignment(self):
        """Test that highest priority requests are assigned first"""
        pool = RequestPool()
        
        # Create requests with known priorities
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Old request (high priority)
        old_req = Request(
            request_id="REQ_OLD",
            external_id="EXT_OLD",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=base_time - timedelta(days=7),  # 7 days old
            foc_target=8.0
        )
        
        # New request (low priority)
        new_req = Request(
            request_id="REQ_NEW",
            external_id="EXT_NEW",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=base_time - timedelta(hours=1),  # 1 hour old
            foc_target=8.0
        )
        
        pool.add_request(old_req)
        pool.add_request(new_req)
        
        # Create agent
        agent = Agent(agent_id="john.doe", full_name="John Doe", skillsets={"internet"})
        
        current_time = datetime(2024, 5, 8, 0, 0, 0, tzinfo=timezone.utc)
        
        # Get and sort requests
        available = pool.get_available_requests(skill_id="internet")
        sorted_requests = pool.sort_by_priority(available, current_time, descending=True)
        
        # Highest priority should be the old request
        top_request = sorted_requests[0]
        assert top_request.request_id == "REQ_OLD"
        
        # Assign top priority request
        pool.assign_request_to_agent(top_request.request_id, agent.agent_id, current_time)
        agent.assign_request(top_request.request_id, current_time)
        
        # Verify correct request was assigned
        assert agent.current_request == "REQ_OLD"
        assert pool.get_request("REQ_OLD").is_assigned
        assert pool.get_request("REQ_NEW").is_new


# ============================================================================
# TEST: End-to-End Scenarios
# ============================================================================

class TestEndToEndScenarios:
    """Test realistic end-to-end scenarios"""
    
    def test_full_day_simulation(self):
        """Simulate a full day of operations"""
        # Setup
        pool = RequestPool()
        agents = [
            Agent(agent_id=f"agent_{i}", full_name=f"Agent {i}",
                  skillsets={"internet", "voice"})
            for i in range(5)
        ]
        
        # Start of day
        day_start = datetime(2024, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
        
        # Add initial requests
        for i in range(20):
            request = Request(
                request_id=f"REQ_{i:03d}",
                external_id=f"EXT_{i:03d}",
                skill_id=["internet", "voice"][i % 2],
                request_source="bcom",
                product=["internet", "voice"][i % 2],
                service_region="ontario",
                request_type="new",
                order_date=day_start - timedelta(hours=i),
                foc_target=8.0
            )
            pool.add_request(request)
        
        assignments = []
        completions = []
        
        # Simulate work throughout the day
        for hour in range(8):  # 9 AM to 5 PM
            current_time = day_start + timedelta(hours=hour)
            
            # New requests arrive
            for i in range(2):
                request = Request(
                    request_id=f"REQ_NEW_{hour}_{i}",
                    external_id=f"EXT_NEW_{hour}_{i}",
                    skill_id="internet",
                    request_source="bcom",
                    product="internet",
                    service_region="ontario",
                    request_type="new",
                    order_date=current_time,
                    foc_target=8.0
                )
                pool.add_request(request)
            
            # Assign work to idle agents
            for agent in agents:
                if agent.is_available:
                    # Get agent's skills
                    for skill in agent.skillsets:
                        available = pool.get_available_requests(skill_id=skill)
                        if available:
                            sorted_reqs = pool.sort_by_priority(available, current_time, descending=True)
                            request = sorted_reqs[0]
                            
                            pool.assign_request_to_agent(request.request_id, agent.agent_id, current_time)
                            agent.assign_request(request.request_id, current_time)
                            assignments.append((current_time, agent.agent_id, request.request_id))
                            break
            
            # Complete some work (simulate 2-hour handle time)
            completion_time = current_time
            for agent in agents:
                if agent.is_working:
                    # Check if work started more than 2 hours ago
                    work_history = agent.work_history
                    if work_history:
                        last_assignment = work_history[-1]
                        if last_assignment['completed_at'] is None:
                            time_working = completion_time - last_assignment['assigned_at']
                            if time_working.total_seconds() >= 7200:  # 2 hours
                                request_id = agent.current_request
                                agent.complete_request(completion_time)
                                pool.complete_request(request_id, completion_time)
                                completions.append((completion_time, agent.agent_id, request_id))
        
        # End of day statistics
        stats = pool.get_statistics(day_start + timedelta(hours=8))
        
        print("\n=== End of Day Statistics ===")
        print(f"Total requests in pool: {stats['total_requests']}")
        print(f"Total assigned: {stats['total_assigned']}")
        print(f"Completed: {stats['by_state'].get('completed', 0)}")
        print(f"Still assigned: {stats['by_state'].get('assigned', 0)}")
        print(f"Still new: {stats['by_state'].get('new', 0)}")
        print(f"Assignments made: {len(assignments)}")
        print(f"Completions: {len(completions)}")
        
        # Assertions
        assert stats['total_requests'] > 20  # Original + arrivals
        assert len(assignments) > 0
        assert len(completions) > 0
    
    def test_escalated_winback_priority(self):
        """Test that escalated winback requests get highest priority"""
        pool = RequestPool()
        
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Create different types of requests
        regular = Request(
            request_id="REQ_REGULAR",
            external_id="EXT_REGULAR",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=base_time - timedelta(days=10),  # Very old
            foc_target=8.0
        )
        
        escalated_winback = Request(
            request_id="REQ_ESC_WIN",
            external_id="EXT_ESC_WIN",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=base_time - timedelta(hours=1),  # Very new
            foc_target=8.0,
            is_escalated=True,
            is_winback=True
        )
        
        pool.add_request(regular)
        pool.add_request(escalated_winback)
        
        # Create agent
        agent = Agent(agent_id="john.doe", full_name="John Doe", skillsets={"internet"})
        
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # Filter by tier (escalated winback tier)
        tier1 = pool.filter_requests(
            skill_id="internet",
            is_escalated=True,
            is_winback=True,
            state=RequestState.NEW
        )
        
        # Should get escalated winback even though regular is much older
        assert len(tier1) == 1
        assert tier1[0].request_id == "REQ_ESC_WIN"
        
        # Assign it
        pool.assign_request_to_agent(tier1[0].request_id, agent.agent_id, current_time)
        agent.assign_request(tier1[0].request_id, current_time)
        
        # Verify escalated winback was assigned despite being newer
        assert agent.current_request == "REQ_ESC_WIN"


# ============================================================================
# TEST: Data Consistency
# ============================================================================

class TestDataConsistency:
    """Test data consistency across operations"""
    
    def test_pool_agent_state_consistency(self):
        """Test that pool and agent states stay in sync"""
        pool = RequestPool()
        agent = Agent(agent_id="john.doe", full_name="John Doe", skillsets={"internet"})
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        pool.add_request(request)
        
        current_time = datetime.now(timezone.utc)
        
        # Before assignment
        assert agent.is_available
        assert pool.get_request("REQ_001").is_new
        
        # Assign
        pool.assign_request_to_agent("REQ_001", agent.agent_id, current_time)
        agent.assign_request("REQ_001", current_time)
        
        # After assignment - both should reflect assignment
        assert agent.is_working
        assert agent.current_request == "REQ_001"
        assert pool.get_request("REQ_001").is_assigned
        assert pool.get_request("REQ_001").assigned_agent_id == agent.agent_id
        
        # Complete
        completion_time = current_time + timedelta(hours=1)
        agent.complete_request(completion_time)
        pool.complete_request("REQ_001", completion_time)
        
        # After completion - both should reflect completion
        assert agent.is_available
        assert agent.current_request is None
        assert pool.get_request("REQ_001").is_completed
    
    def test_metrics_consistency(self):
        """Test that metrics stay consistent"""
        pool = RequestPool()
        agent = Agent(agent_id="john.doe", full_name="John Doe", skillsets={"internet"})
        
        # Add and assign multiple requests
        base_time = datetime.now(timezone.utc)
        for i in range(5):
            request = Request(
                request_id=f"REQ_{i}",
                external_id=f"EXT_{i}",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=base_time
            )
            pool.add_request(request)
            
            # Assign and complete
            assignment_time = base_time + timedelta(hours=i)
            completion_time = assignment_time + timedelta(hours=1)
            
            pool.assign_request_to_agent(request.request_id, agent.agent_id, assignment_time)
            agent.assign_request(request.request_id, assignment_time)
            
            agent.complete_request(completion_time)
            pool.complete_request(request.request_id, completion_time)
        
        # Check consistency
        assert agent.work_count == 5
        assert len(pool.get_requests_by_state(RequestState.COMPLETED)) == 5
        
        # Pool statistics should match
        stats = pool.get_statistics()
        assert stats['total_assigned'] == 5
        assert stats['by_state']['completed'] == 5


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])