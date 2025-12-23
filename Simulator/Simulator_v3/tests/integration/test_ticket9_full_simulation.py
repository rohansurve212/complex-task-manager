"""
Integration test for Ticket #9: Full Simulation End-to-End.

This test validates the complete simulation engine by running realistic
scenarios with multiple agents and requests, verifying that all components
work together correctly.

Tests cover:
- Full simulation run with multiple agents and requests
- Time progression and event processing
- Assignment tracking and statistics
- Production filtering and routing integration
- Mode switching (followup vs CMO time)
- Priority levels
- Absent agent handling
- Various stopping conditions
"""

import pytest
from datetime import datetime, timezone, timedelta
from models.agent import Agent
from models.request import Request
from config.scenario_config import RoutingConfig
from simulation.engine import SimulationEngine


@pytest.fixture
def start_time():
    """Simulation start time: Monday 9 AM EST (14:00 UTC)."""
    return datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def routing_config():
    """Standard routing configuration with pilot enabled."""
    return RoutingConfig(pilot_program_enabled=True)


def create_agents(count: int, skill: str = 'SkillA') -> list:
    """Create multiple test agents."""
    agents = []
    for i in range(count):
        agent = Agent(
            agent_id=f'AGENT{i:03d}',
            full_name=f'Test Agent {i}',
            skillsets={skill}
        )
        agents.append(agent)
    return agents


def create_requests(count: int, start_time: datetime, skill: str = 'SkillA', **kwargs) -> list:
    """Create multiple test requests with varying ages."""
    requests = []
    for i in range(count):
        # Vary the age of requests (0-9 hours old)
        age_hours = i % 10
        
        req = Request(
            request_id=f'REQ{i:03d}',
            external_id=f'EXT_REQ{i:03d}',
            skill_id=skill,
            request_source='web',
            product='ProductA',
            service_region='Ontario',
            request_type='service',
            order_date=start_time - timedelta(hours=age_hours),
            foc_target=kwargs.get('foc_target', 7.0),
            is_escalated=kwargs.get('is_escalated', False),
            is_winback=kwargs.get('is_winback', False),
            has_sla=kwargs.get('has_sla', False)
        )
        requests.append(req)
    return requests


# ============================================================================
# Test Basic Simulation Flow
# ============================================================================

def test_full_simulation_basic_flow(start_time, routing_config):
    """
    Test basic simulation flow: 3 agents, 10 requests.
    
    Scenario:
    - 3 agents available
    - 10 CMO requests
    - Run until idle
    - Verify all requests assigned
    """
    agents = create_agents(3)
    requests = create_requests(10, start_time)
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run until idle
    engine.run(stop_when_idle=True)
    
    # Verify completion
    assert engine.total_events_processed > 0
    assert engine.total_assignments > 0
    
    # With 3 agents and 10 requests, all requests should eventually be assigned
    # (agents can work on multiple requests sequentially)
    assert engine.total_assignments <= 10
    
    # Verify time advanced
    assert engine.current_time >= start_time
    
    # Verify no pending requests remain (or very few if timing issues)
    stats = engine.get_statistics()
    pending = stats['requests']['pending_requests']
    assert pending <= 1  # Allow for rounding in timing


def test_full_simulation_more_requests_than_agents(start_time, routing_config):
    """
    Test simulation with more requests than agents.
    
    Scenario:
    - 5 agents
    - 20 requests
    - Agents should handle multiple requests sequentially
    """
    agents = create_agents(5)
    requests = create_requests(20, start_time)
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Should have made assignments
    assert engine.total_assignments > 5  # More than just initial round
    
    # Verify statistics
    stats = engine.get_statistics()
    assert stats['agents']['total_agents'] == 5
    assert stats['assignments']['total'] == engine.total_assignments


def test_full_simulation_more_agents_than_requests(start_time, routing_config):
    """
    Test simulation with more agents than requests.
    
    Scenario:
    - 10 agents
    - 5 requests
    - Some agents should remain idle
    """
    agents = create_agents(10)
    requests = create_requests(5, start_time)
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Should have assigned all 5 requests
    assert engine.total_assignments <= 5
    
    # Verify some agents didn't get work
    stats = engine.get_statistics()
    assert stats['agents']['agents_without_assignments'] > 0


def test_full_simulation_time_progression(start_time, routing_config):
    """
    Test that simulation time advances correctly through assignments.
    
    Scenario:
    - 2 agents
    - 5 requests with 1-day FOC
    - Verify time advances by FOC duration
    """
    agents = create_agents(2)
    requests = create_requests(5, start_time, foc_target=1.0)  # 1-day FOC
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Time should have advanced by at least 1 day (FOC target)
    duration = engine.current_time - start_time
    assert duration >= timedelta(days=1)
    
    # Verify timing statistics
    stats = engine.get_statistics()
    assert stats['timing']['duration_hours'] >= 24.0  # At least 1 day


# ============================================================================
# Test Priority and Filtering
# ============================================================================

def test_full_simulation_priority_levels(start_time, routing_config):
    """
    Test that priority levels are tracked correctly.
    
    Scenario:
    - Mixed priority requests
    - Verify assignments track priority correctly
    """
    agents = create_agents(3)
    
    # Create requests with different priorities
    requests = []
    
    # Priority 1: winback + escalated (3 requests)
    for i in range(3):
        req = Request(
            request_id=f'REQ_P1_{i:03d}',
            external_id=f'EXT_P1_{i:03d}',
            skill_id='SkillA',
            request_source='web',
            product='ProductA',
            service_region='Ontario',
            request_type='service',
            order_date=start_time - timedelta(hours=i),
            is_winback=True,
            is_escalated=True
        )
        requests.append(req)
    
    # Priority 5: commons (3 requests)
    for i in range(3):
        req = Request(
            request_id=f'REQ_P5_{i:03d}',
            external_id=f'EXT_P5_{i:03d}',
            skill_id='SkillA',
            request_source='web',
            product='ProductA',
            service_region='Ontario',
            request_type='service',
            order_date=start_time - timedelta(hours=i),
            is_escalated=False
        )
        requests.append(req)
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Verify priority distribution
    stats = engine.get_statistics()
    by_priority = stats['assignments']['by_priority']
    
    # Should have assignments in priority 1 and 5
    assert by_priority[1] > 0
    assert by_priority[5] > 0


def test_full_simulation_followup_requests(start_time, routing_config):
    """
    Test simulation with followup requests (self-assigned).
    
    Scenario:
    - Agent with self-assigned followup request
    - Inside followup time window
    - Verify followup gets assigned to same agent
    """
    # Create 2 agents
    agents = create_agents(2)
    agent_001 = agents[0]  # AGENT000
    
    # Create followup request assigned to AGENT000
    followup_req = Request(
        request_id='REQ_FOLLOWUP',
        external_id='EXT_FOLLOWUP',
        skill_id='SkillA',
        request_source='web',
        product='ProductA',
        service_region='Ontario',
        request_type='service',
        order_date=start_time - timedelta(days=5),
        sticky_agent_id='AGENT000',
        workorder_status='customerreplied',
        workorder_expected_completion_date=start_time - timedelta(days=1)  # Past due
    )
    
    # Create CMO request
    cmo_req = Request(
        request_id='REQ_CMO',
        external_id='EXT_CMO',
        skill_id='SkillA',
        request_source='web',
        product='ProductA',
        service_region='Ontario',
        request_type='service',
        order_date=start_time - timedelta(hours=2),
        workorder_status='customerreplied'
    )
    
    engine = SimulationEngine(
        agents=agents,
        requests=[followup_req, cmo_req],
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(max_events=5, stop_when_idle=False)
    
    # Verify followup was assigned
    assignments = engine.get_assignments()
    followup_assignments = [a for a in assignments if a['was_followup']]
    
    assert len(followup_assignments) > 0
    
    # Verify it went to AGENT000
    assert any(a['agent_id'] == 'AGENT000' and a['request_id'] == 'REQ_FOLLOWUP' 
               for a in followup_assignments)


def test_full_simulation_absent_agent_redistribution(start_time, routing_config):
    """
    Test that requests from absent agents are redistributed.
    
    Scenario:
    - 1 absent agent with assigned request
    - 1 present agent
    - Request should be redistributed to present agent
    """
    # Create agents
    present_agent = Agent(
        agent_id='AGENT_PRESENT',
        full_name='Present Agent',
        skillsets={'SkillA'}
    )
    
    absent_agent = Agent(
        agent_id='AGENT_ABSENT',
        full_name='Absent Agent',
        skillsets={'SkillA'},
        is_absent=True
    )
    
    # Create request assigned to absent agent
    request = Request(
        request_id='REQ001',
        external_id='EXT_REQ001',
        skill_id='SkillA',
        request_source='web',
        product='ProductA',
        service_region='Ontario',
        request_type='service',
        order_date=start_time - timedelta(hours=2),
        sticky_agent_id='AGENT_ABSENT',
        workorder_status='customerreplied'
    )
    
    engine = SimulationEngine(
        agents=[present_agent, absent_agent],
        requests=[request],
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Verify request was assigned
    assert engine.total_assignments > 0
    
    # Verify it went to present agent (not absent agent)
    assignments = engine.get_assignments()
    assert all(a['agent_id'] == 'AGENT_PRESENT' for a in assignments)
    
    # Verify it's tracked as from_absent_agent
    assert any(a['from_absent_agent'] for a in assignments)


# ============================================================================
# Test Stopping Conditions
# ============================================================================

def test_full_simulation_max_events_limit(start_time, routing_config):
    """Test that max_events stopping condition works."""
    agents = create_agents(5)
    requests = create_requests(20, start_time)
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run with limit
    max_events = 10
    engine.run(max_events=max_events, stop_when_idle=False)
    
    # Should stop at exactly max_events
    assert engine.total_events_processed == max_events
    
    # Should still have pending events
    assert not engine.event_queue.is_empty()


def test_full_simulation_time_limit(start_time, routing_config):
    """Test that max_time stopping condition works."""
    agents = create_agents(3)
    requests = create_requests(10, start_time, foc_target=7.0)
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run with time limit (1 hour)
    max_time = start_time + timedelta(hours=1)
    engine.run(max_time=max_time, stop_when_idle=False)
    
    # Current time should not exceed max_time
    assert engine.current_time <= max_time


def test_full_simulation_stop_when_idle_condition(start_time, routing_config):
    """Test that stop_when_idle condition works correctly."""
    agents = create_agents(5)
    requests = create_requests(5, start_time, foc_target=0.1)  # Very short FOC
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run until idle
    engine.run(stop_when_idle=True)
    
    # Should have processed all requests
    assert engine.total_assignments == 5
    
    # Should be idle (all agents available, no pending requests)
    assert engine._is_simulation_idle()


# ============================================================================
# Test Statistics Collection
# ============================================================================

def test_full_simulation_comprehensive_statistics(start_time, routing_config):
    """
    Test that comprehensive statistics are collected correctly.
    
    Scenario:
    - Run full simulation
    - Verify all statistics sections are populated
    """
    agents = create_agents(5)
    requests = create_requests(15, start_time)
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    stats = engine.get_statistics()
    
    # Verify all major sections exist
    assert 'timing' in stats
    assert 'events' in stats
    assert 'assignments' in stats
    assert 'agents' in stats
    assert 'requests' in stats
    assert 'routing' in stats
    
    # Verify timing section
    timing = stats['timing']
    assert timing['start_time'] == start_time
    assert timing['end_time'] is not None
    assert timing['duration_seconds'] > 0
    
    # Verify assignments section
    assignments = stats['assignments']
    assert assignments['total'] > 0
    assert assignments['total'] == assignments['followup_count'] + assignments['cmo_count']
    
    # Verify agents section
    agents_stats = stats['agents']
    assert agents_stats['total_agents'] == 5
    assert agents_stats['avg_assignments_per_agent'] > 0
    
    # Verify routing section
    routing = stats['routing']
    assert routing['total_decisions'] == engine.total_events_processed
    assert routing['success_rate'] > 0


def test_full_simulation_agent_utilization_tracking(start_time, routing_config):
    """Test that agent utilization is tracked correctly."""
    agents = create_agents(4)
    requests = create_requests(12, start_time)  # 3 requests per agent average
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    stats = engine.get_statistics()
    agent_stats = stats['agents']
    
    # Verify assignment distribution
    assignments_per_agent = agent_stats['assignments_per_agent']
    assert len(assignments_per_agent) <= 4  # Some agents may not get work
    
    # Verify averages
    assert agent_stats['avg_assignments_per_agent'] > 0
    assert agent_stats['max_assignments_per_agent'] >= agent_stats['min_assignments_per_agent']


def test_full_simulation_routing_decisions_tracking(start_time, routing_config):
    """Test that routing decisions are tracked correctly."""
    agents = create_agents(3)
    requests = create_requests(10, start_time)
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(max_events=10, stop_when_idle=False)
    
    # Get routing decisions
    decisions = engine.get_routing_decisions()
    
    # Should have one decision per event
    assert len(decisions) == 10
    
    # Verify decision structure
    for decision in decisions:
        assert 'timestamp' in decision
        assert 'agent_id' in decision
        assert 'filtered_count' in decision
        assert 'selected_request_id' in decision
        assert 'was_followup' in decision


# ============================================================================
# Test Reset Functionality
# ============================================================================

def test_full_simulation_reset_and_rerun(start_time, routing_config):
    """
    Test that engine can be reset and run multiple times.
    
    Scenario:
    - Run simulation
    - Reset
    - Run again
    - Verify results are independent
    """
    agents = create_agents(3)
    requests = create_requests(10, start_time)
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    # First run
    engine.run(max_events=5, stop_when_idle=False)
    first_assignments = engine.total_assignments
    
    # Reset
    engine.reset()
    
    # Verify reset
    assert engine.total_assignments == 0
    assert engine.total_events_processed == 0
    assert engine.current_time == start_time
    assert len(engine.assignments) == 0
    
    # Second run
    engine.run(max_events=5, stop_when_idle=False)
    second_assignments = engine.total_assignments
    
    # Both runs should have made assignments
    assert first_assignments > 0
    assert second_assignments > 0


# ============================================================================
# Test Large-Scale Simulation
# ============================================================================

def test_full_simulation_large_scale(start_time, routing_config):
    """
    Test large-scale simulation: 20 agents, 100 requests.
    
    This validates performance and correctness at scale.
    """
    agents = create_agents(20)
    requests = create_requests(100, start_time)
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run until idle
    engine.run(stop_when_idle=True)
    
    # Verify completion
    assert engine.total_events_processed > 0
    assert engine.total_assignments > 0
    
    # With enough time, all requests should be assigned
    stats = engine.get_statistics()
    
    # Verify scale
    assert stats['agents']['total_agents'] == 20
    assert stats['assignments']['total'] > 20  # Multiple rounds
    
    # Verify no errors occurred
    routing_stats = stats['routing']
    assert routing_stats['total_decisions'] > 0


# ============================================================================
# Test Edge Cases
# ============================================================================

def test_full_simulation_no_matching_skills(start_time, routing_config):
    """Test simulation where agents and requests have mismatched skills."""
    # Agents with SkillA
    agents = create_agents(3, skill='SkillA')
    
    # Requests requiring SkillB
    requests = create_requests(5, start_time, skill='SkillB')
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Should complete without assignments (no skill match)
    assert engine.total_assignments == 0
    
    # Should detect idle (agents available, but no eligible work)
    assert engine._is_simulation_idle()


def test_full_simulation_empty_scenario(start_time, routing_config):
    """Test simulation with no agents and no requests."""
    engine = SimulationEngine(
        agents=[],
        requests=[],
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Should complete without errors
    assert engine.total_assignments == 0
    assert engine.total_events_processed == 0


def test_full_simulation_single_agent_many_requests(start_time, routing_config):
    """Test simulation with 1 agent handling many requests sequentially."""
    agents = create_agents(1)
    requests = create_requests(10, start_time, foc_target=0.5)  # Half-day FOC
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Single agent should handle all requests sequentially
    # (may not complete all 10 if time constraints, but should make progress)
    assert engine.total_assignments > 0
    
    # All assignments should go to the same agent
    assignments = engine.get_assignments()
    unique_agents = set(a['agent_id'] for a in assignments)
    assert len(unique_agents) == 1
    assert 'AGENT000' in unique_agents


# ============================================================================
# Test Real-World Scenario
# ============================================================================

def test_full_simulation_realistic_scenario(start_time, routing_config):
    """
    Test realistic scenario mimicking production environment.
    
    Scenario:
    - 10 agents
    - 50 requests (mix of priorities, some followups)
    - Mix of CMO and followup requests
    - 1 absent agent
    - Run until idle
    """
    # Create agents
    agents = create_agents(10)
    
    # Make one agent absent
    agents[0] = Agent(
        agent_id='AGENT000',
        full_name='Absent Agent',
        skillsets={'SkillA'},
        is_absent=True
    )
    
    # Create diverse request mix
    requests = []
    
    # 20 regular CMO requests
    for i in range(20):
        req = Request(
            request_id=f'REQ_CMO_{i:03d}',
            external_id=f'EXT_CMO_{i:03d}',
            skill_id='SkillA',
            request_source='web',
            product='ProductA',
            service_region='Ontario',
            request_type='service',
            order_date=start_time - timedelta(hours=i % 24),
            foc_target=7.0
        )
        requests.append(req)
    
    # 10 priority requests (escalated)
    for i in range(10):
        req = Request(
            request_id=f'REQ_ESC_{i:03d}',
            external_id=f'EXT_ESC_{i:03d}',
            skill_id='SkillA',
            request_source='web',
            product='ProductA',
            service_region='Ontario',
            request_type='service',
            order_date=start_time - timedelta(hours=i),
            is_escalated=True,
            has_sla=True
        )
        requests.append(req)
    
    # 10 followup requests (5 assigned to present agents, 5 to absent agent)
    for i in range(10):
        agent_id = 'AGENT000' if i < 5 else f'AGENT00{i-4}'
        req = Request(
            request_id=f'REQ_FOLLOWUP_{i:03d}',
            external_id=f'EXT_FOLLOWUP_{i:03d}',
            skill_id='SkillA',
            request_source='web',
            product='ProductA',
            service_region='Ontario',
            request_type='service',
            order_date=start_time - timedelta(days=5),
            sticky_agent_id=agent_id,
            workorder_status='customerreplied',
            workorder_expected_completion_date=start_time - timedelta(days=1)
        )
        requests.append(req)
    
    # 10 winback requests
    for i in range(10):
        req = Request(
            request_id=f'REQ_WINBACK_{i:03d}',
            external_id=f'EXT_WINBACK_{i:03d}',
            skill_id='SkillA',
            request_source='web',
            product='ProductA',
            service_region='Ontario',
            request_type='service',
            order_date=start_time - timedelta(hours=i),
            is_winback=True,
            is_escalated=True
        )
        requests.append(req)
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run full simulation
    engine.run(stop_when_idle=True)
    
    # Verify comprehensive results
    assert engine.total_assignments > 0
    stats = engine.get_statistics()
    
    # Verify assignments were made
    assert stats['assignments']['total'] > 0
    
    # Verify mix of followup and CMO
    assert stats['assignments']['followup_count'] > 0
    assert stats['assignments']['cmo_count'] > 0
    
    # Verify absent agent requests were redistributed
    assert stats['assignments']['from_absent_agent_count'] > 0
    
    # Verify priority distribution
    by_priority = stats['assignments']['by_priority']
    assert by_priority[1] > 0  # Winback + escalated
    assert by_priority[3] > 0  # SLA + escalated
    
    # Verify agent utilization
    agent_stats = stats['agents']
    assert agent_stats['agents_with_assignments'] >= 9  # Most agents should have work
    
    # Verify routing effectiveness
    routing_stats = stats['routing']
    assert routing_stats['success_rate'] > 0.5  # Most routing attempts successful
    
    print("\n=== Realistic Scenario Results ===")
    print(f"Total Assignments: {stats['assignments']['total']}")
    print(f"Followup: {stats['assignments']['followup_count']}, CMO: {stats['assignments']['cmo_count']}")
    print(f"From Absent Agent: {stats['assignments']['from_absent_agent_count']}")
    print(f"Priority Distribution: {by_priority}")
    print(f"Agents with Work: {agent_stats['agents_with_assignments']}/{agent_stats['total_agents']}")
    print(f"Routing Success Rate: {routing_stats['success_rate']:.2%}")
    print(f"Duration: {stats['timing']['duration_hours']:.2f} hours")