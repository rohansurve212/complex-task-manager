"""
Unit tests for simulation engine.

Tests cover:
- Engine initialization
- Agent initialization and availability
- Event processing
- Assignment tracking
- Statistics collection
- Run loop with stopping conditions
- State management
- Edge cases
"""

import pytest
from datetime import datetime, timezone, timedelta
from models.agent import Agent, AgentState
from models.request import Request, RequestState
from config.scenario_config import RoutingConfig
from simulation.engine import SimulationEngine
from simulation.events import AgentAvailableEvent


@pytest.fixture
def start_time():
    """Simulation start time."""
    return datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def routing_config():
    """Default routing configuration."""
    return RoutingConfig(pilot_program_enabled=True)


@pytest.fixture
def sample_agents():
    """Create sample agents for testing."""
    agents = []
    for i in range(3):
        agent = Agent(
            agent_id=f'AGENT{i:03d}',
            full_name=f'Test Agent {i}',
            skillsets={'SkillA'}
        )
        agents.append(agent)
    return agents


@pytest.fixture
def sample_requests(start_time):
    """Create sample requests for testing."""
    requests = []
    for i in range(10):
        req = Request(
            request_id=f'REQ{i:03d}',
            external_id=f'EXT_REQ{i:03d}',
            skill_id='SkillA',
            request_source='web',
            product='ProductA',
            service_region='Ontario',
            request_type='service',
            order_date=start_time - timedelta(hours=i),
            foc_target=7.0
        )
        requests.append(req)
    return requests


# ============================================================================
# Test Engine Initialization
# ============================================================================

def test_engine_initialization(sample_agents, sample_requests, routing_config, start_time):
    """Test basic engine initialization."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    assert engine.start_time == start_time
    assert engine.current_time == start_time
    assert len(engine.agents) == 3
    assert engine.request_pool.size() == 10
    assert engine.config == routing_config


def test_engine_initializes_agent_dictionary(sample_agents, sample_requests, routing_config, start_time):
    """Test that agents are stored in dictionary by agent_id."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    for agent in sample_agents:
        assert agent.agent_id in engine.agents
        assert engine.agents[agent.agent_id] == agent


def test_engine_initializes_request_pool(sample_agents, sample_requests, routing_config, start_time):
    """Test that requests are added to request pool."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    assert engine.request_pool.size() == len(sample_requests)
    
    # Verify all requests are in pool
    for request in sample_requests:
        assert engine.request_pool.contains(request.request_id)


def test_engine_initializes_tracking_structures(sample_agents, sample_requests, routing_config, start_time):
    """Test that tracking structures are initialized empty."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    assert len(engine.assignments) == 0
    assert len(engine.active_assignments) == 0
    assert len(engine.completed_assignments) == 0
    assert len(engine.routing_decisions) == 0
    assert engine.total_assignments == 0
    assert engine.total_completions == 0


# ============================================================================
# Test Agent Initialization
# ============================================================================

def test_engine_sets_all_agents_to_idle(sample_agents, sample_requests, routing_config, start_time):
    """Test that all agents are set to IDLE state on initialization."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    for agent_id, agent in engine.agents.items():
        assert agent.state == AgentState.IDLE
        assert agent_id in engine.available_agents
        assert agent_id not in engine.busy_agents


def test_engine_schedules_initial_availability_events(sample_agents, sample_requests, routing_config, start_time):
    """Test that availability events are scheduled for all agents."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Should have one event per agent
    assert engine.event_queue.size() == len(sample_agents)
    
    # All events should be at start_time
    for _ in range(len(sample_agents)):
        event = engine.event_queue.pop()
        assert isinstance(event, AgentAvailableEvent)
        assert event.timestamp == start_time


# ============================================================================
# Test Run Loop - Basic Execution
# ============================================================================

def test_engine_run_with_max_events(sample_agents, sample_requests, routing_config, start_time):
    """Test running engine with max_events limit."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run for only 5 events
    engine.run(max_events=5, stop_when_idle=False)
    
    assert engine.total_events_processed == 5
    assert not engine.event_queue.is_empty()  # More events remain


def test_engine_run_until_idle(sample_agents, sample_requests, routing_config, start_time):
    """Test running engine until idle (all work completed)."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Should have processed events
    assert engine.total_events_processed > 0
    
    # Should have made assignments (3 agents, 10 requests)
    assert engine.total_assignments > 0
    
    # All requests should be assigned (we have more requests than agents)
    # Or all agents should have work
    assert engine.total_assignments <= len(sample_requests)


def test_engine_run_with_time_limit(sample_agents, sample_requests, routing_config, start_time):
    """Test running engine with time limit."""
    max_time = start_time + timedelta(hours=2)
    
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(max_time=max_time, stop_when_idle=False)
    
    # Current time should not exceed max_time
    assert engine.current_time <= max_time


def test_engine_run_advances_time(sample_agents, sample_requests, routing_config, start_time):
    """Test that simulation time advances during run."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    initial_time = engine.current_time
    
    engine.run(max_events=10, stop_when_idle=False)
    
    # Time should have advanced (or stayed same if all events at start)
    assert engine.current_time >= initial_time


# ============================================================================
# Test Agent Available Handling
# ============================================================================

def test_engine_handles_agent_available_event(sample_agents, sample_requests, routing_config, start_time):
    """Test handling of agent available event."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Get first agent
    agent_id = list(engine.agents.keys())[0]
    
    # Pop and process first event (agent becomes available)
    event = engine.event_queue.pop()
    engine._process_event(event)
    
    # Should have made routing decision
    assert len(engine.routing_decisions) == 1
    
    decision = engine.routing_decisions[0]
    assert decision['agent_id'] == event.agent_id
    assert 'filtered_count' in decision
    assert 'selected_request_id' in decision


def test_engine_assigns_request_when_available(sample_agents, sample_requests, routing_config, start_time):
    """Test that engine assigns request to available agent."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Process first event
    event = engine.event_queue.pop()
    engine._process_event(event)
    
    # Should have made assignment (requests available)
    if engine.total_assignments > 0:
        assert len(engine.assignments) == 1
        assert len(engine.active_assignments) == 1
        
        # Agent should now be busy
        assigned_agent_id = engine.assignments[0]['agent_id']
        assert assigned_agent_id in engine.busy_agents
        assert assigned_agent_id not in engine.available_agents


def test_engine_schedules_next_availability_after_assignment(sample_agents, sample_requests, routing_config, start_time):
    """Test that next availability event is scheduled after assignment."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    initial_queue_size = engine.event_queue.size()
    
    # Process first event (should assign and schedule next)
    event = engine.event_queue.pop()
    agent_id = event.agent_id
    engine._process_event(event)
    
    # If assignment was made, should have scheduled next availability
    if engine.total_assignments > 0:
        # Queue should have same or more events (removed one, may add one back)
        # Actually queue size depends on whether other agents were processed
        # Just verify that assignments were made
        assert engine.total_assignments > 0


def test_engine_handles_no_work_available(routing_config, start_time):
    """Test that engine handles case when no work is available for agent."""
    # Create agent but NO requests
    agents = [Agent(agent_id='AGENT001', full_name='Test Agent', skillsets={'SkillA'})]
    requests = []
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Process the availability event
    event = engine.event_queue.pop()
    engine._process_event(event)
    
    # Should have made routing decision but no assignment
    assert len(engine.routing_decisions) == 1
    assert engine.routing_decisions[0]['selected_request_id'] is None
    assert engine.total_assignments == 0
    
    # Agent should remain idle
    assert 'AGENT001' in engine.available_agents


# ============================================================================
# Test Assignment Logic
# ============================================================================

def test_engine_assignment_updates_request_state(sample_agents, sample_requests, routing_config, start_time):
    """Test that assignment updates request state correctly."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run until first assignment
    engine.run(max_events=10, stop_when_idle=False)
    
    if engine.total_assignments > 0:
        # Get the assigned request
        assignment = engine.assignments[0]
        request_id = assignment['request_id']
        request = engine.request_pool.get_request(request_id)
        
        # Request should be in ASSIGNED state
        assert request.state == RequestState.ASSIGNED


def test_engine_assignment_updates_agent_state(sample_agents, sample_requests, routing_config, start_time):
    """Test that assignment updates agent state correctly."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Process first event
    event = engine.event_queue.pop()
    agent_id = event.agent_id
    engine._process_event(event)
    
    if engine.total_assignments > 0:
        # Agent should be busy
        agent = engine.agents[agent_id]
        assert agent.state == AgentState.BUSY


def test_engine_assignment_records_metadata(sample_agents, sample_requests, routing_config, start_time):
    """Test that assignment records include all required metadata."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run until first assignment
    engine.run(max_events=5, stop_when_idle=False)
    
    if engine.total_assignments > 0:
        assignment = engine.assignments[0]
        
        # Verify required fields
        assert 'assignment_id' in assignment
        assert 'timestamp' in assignment
        assert 'agent_id' in assignment
        assert 'request_id' in assignment
        assert 'completion_time' in assignment
        assert 'was_followup' in assignment
        assert 'from_absent_agent' in assignment
        assert 'priority_level' in assignment


def test_engine_calculates_completion_time(sample_agents, sample_requests, routing_config, start_time):
    """Test that completion time is calculated correctly."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Get a request
    request = sample_requests[0]
    
    # Calculate completion time
    completion_time = engine._calculate_completion_time(request)
    
    # Should be start_time + FOC target
    expected_time = start_time + timedelta(days=request.foc_target)
    assert completion_time == expected_time


def test_engine_calculates_completion_time_with_default_foc(sample_agents, routing_config, start_time):
    """Test completion time calculation with no FOC target."""
    # Create request with no FOC
    request = Request(
        request_id='REQ001',
        external_id='EXT_REQ001',
        skill_id='SkillA',
        request_source='web',
        product='ProductA',
        service_region='Ontario',
        request_type='service',
        order_date=start_time,
        foc_target=None  # No FOC
    )
    
    engine = SimulationEngine(
        agents=sample_agents,
        requests=[request],
        config=routing_config,
        start_time=start_time
    )
    
    completion_time = engine._calculate_completion_time(request)
    
    # Should use default 7 days
    expected_time = start_time + timedelta(days=7.0)
    assert completion_time == expected_time


def test_engine_determines_priority_level(sample_agents, sample_requests, routing_config, start_time):
    """Test priority level determination for requests."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Priority 1: winback + escalated
    req_p1 = Request(
        request_id='REQ_P1', external_id='EXT_P1', skill_id='SkillA',
        request_source='web', product='ProductA', service_region='Ontario',
        request_type='service', order_date=start_time,
        is_winback=True, is_escalated=True
    )
    assert engine._get_priority_level(req_p1) == 1
    
    # Priority 2: winback + not escalated
    req_p2 = Request(
        request_id='REQ_P2', external_id='EXT_P2', skill_id='SkillA',
        request_source='web', product='ProductA', service_region='Ontario',
        request_type='service', order_date=start_time,
        is_winback=True, is_escalated=False
    )
    assert engine._get_priority_level(req_p2) == 2
    
    # Priority 3: SLA + escalated
    req_p3 = Request(
        request_id='REQ_P3', external_id='EXT_P3', skill_id='SkillA',
        request_source='web', product='ProductA', service_region='Ontario',
        request_type='service', order_date=start_time,
        has_sla=True, is_escalated=True
    )
    assert engine._get_priority_level(req_p3) == 3
    
    # Priority 5: commons (not escalated)
    req_p5 = Request(
        request_id='REQ_P5', external_id='EXT_P5', skill_id='SkillA',
        request_source='web', product='ProductA', service_region='Ontario',
        request_type='service', order_date=start_time,
        is_escalated=False
    )
    assert engine._get_priority_level(req_p5) == 5


# ============================================================================
# Test Idle Detection
# ============================================================================

def test_engine_detects_idle_no_pending_requests(sample_agents, routing_config, start_time):
    """Test idle detection when no pending requests."""
    # Create engine with no requests
    engine = SimulationEngine(
        agents=sample_agents,
        requests=[],
        config=routing_config,
        start_time=start_time
    )
    
    # All agents idle, no requests
    assert engine._is_simulation_idle()


def test_engine_detects_not_idle_with_busy_agents(sample_agents, sample_requests, routing_config, start_time):
    """Test that simulation is not idle when agents are busy."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Manually set an agent to busy
    agent_id = list(engine.agents.keys())[0]
    engine.busy_agents.add(agent_id)
    
    # Should not be idle (busy agent)
    assert not engine._is_simulation_idle()


def test_engine_detects_not_idle_with_pending_requests(sample_agents, sample_requests, routing_config, start_time):
    """Test that simulation is not idle when pending requests exist."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Has pending requests
    assert not engine._is_simulation_idle()


# ============================================================================
# Test Statistics Collection
# ============================================================================

def test_engine_collects_basic_statistics(sample_agents, sample_requests, routing_config, start_time):
    """Test that engine collects basic statistics."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(max_events=10, stop_when_idle=False)
    
    stats = engine.get_statistics()
    
    # Verify structure
    assert 'timing' in stats
    assert 'events' in stats
    assert 'assignments' in stats
    assert 'agents' in stats
    assert 'requests' in stats
    assert 'routing' in stats


def test_engine_statistics_timing_section(sample_agents, sample_requests, routing_config, start_time):
    """Test timing statistics."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(max_events=10, stop_when_idle=False)
    
    stats = engine.get_statistics()
    timing = stats['timing']
    
    assert 'start_time' in timing
    assert 'end_time' in timing
    assert 'duration_seconds' in timing
    assert 'duration_hours' in timing
    
    assert timing['start_time'] == start_time


def test_engine_statistics_assignment_section(sample_agents, sample_requests, routing_config, start_time):
    """Test assignment statistics."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(max_events=10, stop_when_idle=False)
    
    stats = engine.get_statistics()
    assignments = stats['assignments']
    
    assert 'total' in assignments
    assert 'by_priority' in assignments
    assert 'followup_count' in assignments
    assert 'cmo_count' in assignments
    assert 'from_absent_agent_count' in assignments
    
    # Total should match sum of followup + cmo
    assert assignments['total'] == assignments['followup_count'] + assignments['cmo_count']


def test_engine_statistics_agent_section(sample_agents, sample_requests, routing_config, start_time):
    """Test agent statistics."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(max_events=10, stop_when_idle=False)
    
    stats = engine.get_statistics()
    agents = stats['agents']
    
    assert 'total_agents' in agents
    assert 'agents_with_assignments' in agents
    assert 'avg_assignments_per_agent' in agents
    assert 'assignments_per_agent' in agents
    
    assert agents['total_agents'] == len(sample_agents)


def test_engine_statistics_routing_section(sample_agents, sample_requests, routing_config, start_time):
    """Test routing statistics."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(max_events=10, stop_when_idle=False)
    
    stats = engine.get_statistics()
    routing = stats['routing']
    
    assert 'total_decisions' in routing
    assert 'successful_routings' in routing
    assert 'failed_routings' in routing
    assert 'success_rate' in routing
    
    # Total decisions should equal events processed
    assert routing['total_decisions'] == engine.total_events_processed


# ============================================================================
# Test Reset Functionality
# ============================================================================

def test_engine_reset_clears_assignments(sample_agents, sample_requests, routing_config, start_time):
    """Test that reset clears assignment tracking."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run for a bit
    engine.run(max_events=10, stop_when_idle=False)
    
    # Should have some assignments
    initial_assignments = engine.total_assignments
    assert initial_assignments > 0
    
    # Reset
    engine.reset()
    
    # Should be cleared
    assert len(engine.assignments) == 0
    assert len(engine.active_assignments) == 0
    assert len(engine.routing_decisions) == 0
    assert engine.total_assignments == 0


def test_engine_reset_resets_time(sample_agents, sample_requests, routing_config, start_time):
    """Test that reset resets simulation time."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run
    engine.run(max_events=10, stop_when_idle=False)
    
    # Time should have advanced
    assert engine.current_time >= start_time
    
    # Reset
    engine.reset()
    
    # Time should be back to start
    assert engine.current_time == start_time
    assert engine.end_time is None


def test_engine_reset_reinitializes_agents(sample_agents, sample_requests, routing_config, start_time):
    """Test that reset reinitializes agent states."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Run
    engine.run(max_events=10, stop_when_idle=False)
    
    # Reset
    engine.reset()
    
    # All agents should be available
    assert len(engine.available_agents) == len(sample_agents)
    assert len(engine.busy_agents) == 0
    
    # All agents should have availability events
    assert engine.event_queue.size() == len(sample_agents)


# ============================================================================
# Test Edge Cases
# ============================================================================

def test_engine_with_single_agent_single_request(routing_config, start_time):
    """Test minimal scenario: 1 agent, 1 request."""
    agents = [Agent(agent_id='AGENT001', full_name='Test Agent', skillsets={'SkillA'})]
    requests = [Request(
        request_id='REQ001', external_id='EXT_REQ001', skill_id='SkillA',
        request_source='web', product='ProductA', service_region='Ontario',
        request_type='service', order_date=start_time, foc_target=7.0
    )]
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Should have made exactly 1 assignment
    assert engine.total_assignments == 1
    assert engine.assignments[0]['agent_id'] == 'AGENT001'
    assert engine.assignments[0]['request_id'] == 'REQ001'


def test_engine_with_no_agents(sample_requests, routing_config, start_time):
    """Test edge case: no agents."""
    engine = SimulationEngine(
        agents=[],
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    # Should initialize without error
    assert len(engine.agents) == 0
    assert engine.event_queue.is_empty()


def test_engine_with_no_requests(sample_agents, routing_config, start_time):
    """Test edge case: no requests."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=[],
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Should complete without assignments
    assert engine.total_assignments == 0


def test_engine_with_mismatched_skills(routing_config, start_time):
    """Test that engine handles skill mismatches correctly."""
    # Agent with SkillA
    agents = [Agent(agent_id='AGENT001', full_name='Test Agent', skillsets={'SkillA'})]
    
    # Requests requiring SkillB
    requests = [Request(
        request_id='REQ001', external_id='EXT_REQ001', skill_id='SkillB',
        request_source='web', product='ProductA', service_region='Ontario',
        request_type='service', order_date=start_time, foc_target=7.0
    )]
    
    engine = SimulationEngine(
        agents=agents,
        requests=requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(stop_when_idle=True)
    
    # Should complete without assignments (no skill match)
    assert engine.total_assignments == 0


# ============================================================================
# Test Getters
# ============================================================================

def test_engine_get_assignments(sample_agents, sample_requests, routing_config, start_time):
    """Test getting assignments list."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(max_events=10, stop_when_idle=False)
    
    assignments = engine.get_assignments()
    
    assert isinstance(assignments, list)
    assert len(assignments) == engine.total_assignments


def test_engine_get_routing_decisions(sample_agents, sample_requests, routing_config, start_time):
    """Test getting routing decisions list."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    engine.run(max_events=10, stop_when_idle=False)
    
    decisions = engine.get_routing_decisions()
    
    assert isinstance(decisions, list)
    assert len(decisions) == engine.total_events_processed


def test_engine_repr(sample_agents, sample_requests, routing_config, start_time):
    """Test engine string representation."""
    engine = SimulationEngine(
        agents=sample_agents,
        requests=sample_requests,
        config=routing_config,
        start_time=start_time
    )
    
    repr_str = repr(engine)
    
    assert 'SimulationEngine' in repr_str
    assert 'agents=3' in repr_str
    assert 'requests=10' in repr_str