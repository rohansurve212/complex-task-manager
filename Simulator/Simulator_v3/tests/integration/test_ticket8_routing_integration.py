"""
Integration test for Ticket #8: Routing Logic & Prioritization.

Tests the complete flow from production filtering through routing to
verify that the system correctly selects the optimal request for an agent.

Integration points tested:
- Production filtering (Ticket #7) → Routing (Ticket #8)
- Agent skillset matching
- Request pool management
- Priority scoring with real scenarios
- Mode switching (followup time vs CMO time)
"""

import pytest
from datetime import datetime, timezone, timedelta
from models.request import Request
from models.agent import Agent
from models.request_pool import RequestPool
from config.scenario_config import RoutingConfig
from simulation.production_filtering import filter_production_requests
from simulation.routing import route_request_to_agent


@pytest.fixture
def current_time():
    """Current time: Monday 10 AM EST (15:00 UTC), within followup window."""
    return datetime(2024, 1, 15, 15, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def outside_followup_time():
    """Time outside followup window: Monday 5 PM EST (22:00 UTC)."""
    return datetime(2024, 1, 15, 22, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def agent():
    """Test agent with single skillset."""
    return Agent(
        agent_id='AGENT001',
        full_name='Test Agent',
        skillsets={'SkillA'}
    )


@pytest.fixture
def pool():
    """Empty request pool."""
    return RequestPool()


@pytest.fixture
def routing_config():
    """Default routing configuration with pilot enabled."""
    return RoutingConfig(pilot_program_enabled=True)


def create_request(
    request_id='REQ001',
    skill_id='SkillA',
    order_date=None,
    foc_target=7.0,
    sticky_agent_id=None,
    workorder_status='new',
    workorder_expected_completion_date=None,
    is_escalated=False,
    is_winback=False,
    has_sla=False
):
    """Helper to create a request."""
    if order_date is None:
        order_date = datetime(2024, 1, 15, 15, 0, 0, tzinfo=timezone.utc)
    
    return Request(
        request_id=request_id,
        external_id=f'EXT_{request_id}',
        skill_id=skill_id,
        request_source='web',
        product='ProductA',
        service_region='Ontario',
        request_type='service',
        order_date=order_date,
        foc_target=foc_target,
        sticky_agent_id=sticky_agent_id,
        workorder_status=workorder_status,
        workorder_expected_completion_date=workorder_expected_completion_date,
        is_escalated=is_escalated,
        is_winback=is_winback,
        has_sla=has_sla
    )


# ============================================================================
# Integration Tests: Filtering → Routing → Selection
# ============================================================================

def test_end_to_end_cmo_routing_selects_oldest(pool, agent, current_time, routing_config):
    """
    Test complete flow: multiple CMO requests → filter → route → select oldest.
    
    Scenario:
    - Outside followup time (CMO primary)
    - 3 unassigned CMO requests with same FOC
    - Should select oldest request
    """
    # Create 3 CMO requests with different ages
    req1 = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=2),
        foc_target=7.0,
        workorder_status='customerreplied'
    )
    req2 = create_request(
        request_id='REQ002',
        order_date=current_time - timedelta(days=5),  # OLDEST
        foc_target=7.0,
        workorder_status='customerreplied'
    )
    req3 = create_request(
        request_id='REQ003',
        order_date=current_time - timedelta(days=3),
        foc_target=7.0,
        workorder_status='customerreplied'
    )
    
    pool.add_request(req1)
    pool.add_request(req2)
    pool.add_request(req3)
    
    # Use outside followup time to ensure CMO is primary
    outside_time = datetime(2024, 1, 15, 22, 0, 0, tzinfo=timezone.utc)
    
    # Step 1: Production filtering
    filtered = filter_production_requests(
        pool, agent, outside_time, set(), routing_config
    )
    
    # Step 2: Routing
    selected = route_request_to_agent(filtered, outside_time)
    
    # Verify: Should select oldest request (REQ002)
    assert selected is not None
    assert selected.request_id == 'REQ002'
    assert selected.is_followup is False


def test_end_to_end_cmo_routing_considers_foc_urgency(pool, agent, outside_followup_time, routing_config):
    """
    Test that routing considers FOC urgency for CMO requests.
    
    Scenario:
    - 2 requests same age, different FOC targets
    - Should select request with shorter FOC (more urgent)
    """
    order_date = outside_followup_time - timedelta(days=2)
    
    # Request 1: 7-day FOC
    req1 = create_request(
        request_id='REQ001',
        order_date=order_date,
        foc_target=7.0,
        workorder_status='customerreplied'
    )
    
    # Request 2: 3-day FOC (more urgent)
    req2 = create_request(
        request_id='REQ002',
        order_date=order_date,
        foc_target=3.0,
        workorder_status='customerreplied'
    )
    
    pool.add_request(req1)
    pool.add_request(req2)
    
    # Filter and route
    filtered = filter_production_requests(
        pool, agent, outside_followup_time, set(), routing_config
    )
    selected = route_request_to_agent(filtered, outside_followup_time)
    
    # Should select shorter FOC
    assert selected.request_id == 'REQ002'


def test_end_to_end_followup_routing_selects_most_overdue(pool, agent, current_time, routing_config):
    """
    Test complete flow: multiple followup requests → filter → route → select most overdue.
    
    Scenario:
    - Inside followup time (followup primary)
    - 3 self-assigned followup requests with different ECD overdue amounts
    - Should select most overdue
    """
    # Request 1: 1 day past ECD
    req1 = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=5),
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=current_time - timedelta(days=1)
    )
    
    # Request 2: 5 days past ECD (MOST OVERDUE)
    req2 = create_request(
        request_id='REQ002',
        order_date=current_time - timedelta(days=10),
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=current_time - timedelta(days=5)
    )
    
    # Request 3: 3 days past ECD
    req3 = create_request(
        request_id='REQ003',
        order_date=current_time - timedelta(days=8),
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=current_time - timedelta(days=3)
    )
    
    pool.add_request(req1)
    pool.add_request(req2)
    pool.add_request(req3)
    
    # Filter and route
    filtered = filter_production_requests(
        pool, agent, current_time, set(), routing_config
    )
    selected = route_request_to_agent(filtered, current_time)
    
    # Should select most overdue (REQ002)
    assert selected is not None
    assert selected.request_id == 'REQ002'
    assert selected.is_followup is True


def test_end_to_end_followup_tie_breaking(pool, agent, current_time, routing_config):
    """
    Test followup tie-breaking: same ECD → earliest order_date wins.
    
    Scenario:
    - 3 followup requests with same ECD (same score)
    - Should apply tie-breaking and select earliest order_date
    """
    ecd = current_time - timedelta(days=2)
    
    # Request 1: Ordered 10 days ago (EARLIEST)
    req1 = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=10),
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=ecd
    )
    
    # Request 2: Ordered 7 days ago
    req2 = create_request(
        request_id='REQ002',
        order_date=current_time - timedelta(days=7),
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=ecd
    )
    
    # Request 3: Ordered 5 days ago
    req3 = create_request(
        request_id='REQ003',
        order_date=current_time - timedelta(days=5),
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=ecd
    )
    
    pool.add_request(req1)
    pool.add_request(req2)
    pool.add_request(req3)
    
    # Filter and route
    filtered = filter_production_requests(
        pool, agent, current_time, set(), routing_config
    )
    selected = route_request_to_agent(filtered, current_time)
    
    # Should select earliest order_date
    assert selected.request_id == 'REQ001'


def test_end_to_end_priority_levels_applied(pool, agent, outside_followup_time, routing_config):
    """
    Test that 5-level priority is applied before routing.
    
    Scenario:
    - Multiple CMO requests with different priority levels
    - Should filter to highest priority level first, then route within that level
    """
    # Priority 5 (commons): 3 days old
    req_p5 = create_request(
        request_id='REQ_P5',
        order_date=outside_followup_time - timedelta(days=3),
        workorder_status='customerreplied',
        is_escalated=False
    )
    
    # Priority 1 (winback + escalated): 1 day old (HIGHEST PRIORITY)
    req_p1 = create_request(
        request_id='REQ_P1',
        order_date=outside_followup_time - timedelta(days=1),
        workorder_status='customerreplied',
        is_winback=True,
        is_escalated=True
    )
    
    # Priority 3 (SLA + escalated): 5 days old
    req_p3 = create_request(
        request_id='REQ_P3',
        order_date=outside_followup_time - timedelta(days=5),
        workorder_status='customerreplied',
        has_sla=True,
        is_escalated=True
    )
    
    pool.add_request(req_p5)
    pool.add_request(req_p1)
    pool.add_request(req_p3)
    
    # Filter and route
    filtered = filter_production_requests(
        pool, agent, outside_followup_time, set(), routing_config
    )
    selected = route_request_to_agent(filtered, outside_followup_time)
    
    # Should select priority 1 request (even though it's youngest)
    assert selected.request_id == 'REQ_P1'


def test_end_to_end_mode_switching_followup_to_cmo_fallback(pool, agent, current_time, routing_config):
    """
    Test Mode A fallback: no followup available → falls back to CMO.
    
    Scenario:
    - Inside followup time (followup primary)
    - No followup requests available
    - Should fall back to CMO requests
    """
    # Only CMO request (no followups)
    cmo_req = create_request(
        request_id='CMO001',
        order_date=current_time - timedelta(days=2),
        workorder_status='customerreplied'
    )
    
    pool.add_request(cmo_req)
    
    # Filter and route (inside followup time)
    filtered = filter_production_requests(
        pool, agent, current_time, set(), routing_config
    )
    selected = route_request_to_agent(filtered, current_time)
    
    # Should get CMO as fallback
    assert selected is not None
    assert selected.request_id == 'CMO001'
    assert selected.is_followup is False


def test_end_to_end_mode_switching_cmo_to_followup_fallback(pool, agent, outside_followup_time, routing_config):
    """
    Test Mode B fallback: no CMO available → falls back to followup.
    
    Scenario:
    - Outside followup time (CMO primary)
    - No CMO requests available
    - Should fall back to followup requests (if pilot enabled)
    """
    # Only followup request (no CMO)
    followup_req = create_request(
        request_id='FOLLOWUP001',
        order_date=outside_followup_time - timedelta(days=5),
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=outside_followup_time - timedelta(days=2)
    )
    
    pool.add_request(followup_req)
    
    # Filter and route (outside followup time)
    filtered = filter_production_requests(
        pool, agent, outside_followup_time, set(), routing_config
    )
    selected = route_request_to_agent(filtered, outside_followup_time)
    
    # Should get followup as fallback (pilot enabled)
    assert selected is not None
    assert selected.request_id == 'FOLLOWUP001'
    assert selected.is_followup is True


def test_end_to_end_absent_agent_requests_routed_correctly(pool, agent, outside_followup_time, routing_config):
    """
    Test that requests from absent agents are routed correctly.
    
    Scenario:
    - Absent agent has multiple requests
    - Present agent should get oldest/highest priority from absent agent's queue
    """
    absent_agents = {'ABSENT_AGENT'}
    
    # Absent agent request 1: 2 days old
    req1 = create_request(
        request_id='REQ001',
        order_date=outside_followup_time - timedelta(days=2),
        sticky_agent_id='ABSENT_AGENT',
        workorder_status='customerreplied'
    )
    
    # Absent agent request 2: 5 days old (OLDEST)
    req2 = create_request(
        request_id='REQ002',
        order_date=outside_followup_time - timedelta(days=5),
        sticky_agent_id='ABSENT_AGENT',
        workorder_status='customerreplied'
    )
    
    pool.add_request(req1)
    pool.add_request(req2)
    
    # Filter and route
    filtered = filter_production_requests(
        pool, agent, outside_followup_time, absent_agents, routing_config
    )
    selected = route_request_to_agent(filtered, outside_followup_time)
    
    # Should select oldest absent agent request
    assert selected is not None
    assert selected.request_id == 'REQ002'
    assert getattr(selected, 'from_absent_agent', False) is True


def test_end_to_end_no_eligible_requests(pool, agent, current_time, routing_config):
    """
    Test that system handles no eligible requests gracefully.
    
    Scenario:
    - Pool has requests, but none match agent's skills
    - Should return None
    """
    # Add request with different skill
    req = create_request(
        request_id='REQ001',
        skill_id='SkillB',  # Agent has SkillA
        workorder_status='customerreplied'
    )
    
    pool.add_request(req)
    
    # Filter and route
    filtered = filter_production_requests(
        pool, agent, current_time, set(), routing_config
    )
    selected = route_request_to_agent(filtered, current_time)
    
    # Should return None (no matching skills)
    assert selected is None


def test_end_to_end_complex_scenario(pool, agent, current_time, routing_config):
    """
    Test complex real-world scenario with multiple request types.
    
    Scenario:
    - Inside followup time
    - Mix of followups, CMO requests, different priorities
    - Should select highest priority followup
    """
    # Self-assigned followup: 3 days past ECD, priority 1 (winback + escalated)
    followup_p1 = create_request(
        request_id='FOLLOWUP_P1',
        order_date=current_time - timedelta(days=10),
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=current_time - timedelta(days=3),
        is_winback=True,
        is_escalated=True
    )
    
    # Self-assigned followup: 1 day past ECD, priority 5 (commons)
    followup_p5 = create_request(
        request_id='FOLLOWUP_P5',
        order_date=current_time - timedelta(days=5),
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=current_time - timedelta(days=1),
        is_escalated=False
    )
    
    # CMO request: Very old, priority 1 (should not be selected - followup primary)
    cmo_p1 = create_request(
        request_id='CMO_P1',
        order_date=current_time - timedelta(days=20),
        workorder_status='customerreplied',
        is_winback=True,
        is_escalated=True
    )
    
    pool.add_request(followup_p1)
    pool.add_request(followup_p5)
    pool.add_request(cmo_p1)
    
    # Filter and route (inside followup time)
    filtered = filter_production_requests(
        pool, agent, current_time, set(), routing_config
    )
    selected = route_request_to_agent(filtered, current_time)
    
    # Should select highest priority followup (P1, most overdue)
    assert selected is not None
    assert selected.request_id == 'FOLLOWUP_P1'
    assert selected.is_followup is True


# ============================================================================
# Verification Tests
# ============================================================================

def test_integration_preserves_request_state(pool, agent, current_time, routing_config):
    """Verify that filtering and routing don't modify request state."""
    req = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=2),
        workorder_status='customerreplied'
    )
    
    pool.add_request(req)
    
    original_state = req.state
    original_order_date = req.order_date
    
    # Filter and route
    filtered = filter_production_requests(
        pool, agent, current_time, set(), routing_config
    )
    selected = route_request_to_agent(filtered, current_time)
    
    # Verify state unchanged
    assert selected.state == original_state
    assert selected.order_date == original_order_date


def test_integration_scoring_consistency(pool, agent, outside_followup_time, routing_config):
    """Verify that running multiple times produces consistent results."""
    req1 = create_request(
        request_id='REQ001',
        order_date=outside_followup_time - timedelta(days=5),
        workorder_status='customerreplied'
    )
    req2 = create_request(
        request_id='REQ002',
        order_date=outside_followup_time - timedelta(days=3),
        workorder_status='customerreplied'
    )
    
    pool.add_request(req1)
    pool.add_request(req2)
    
    # Run multiple times
    results = []
    for _ in range(5):
        filtered = filter_production_requests(
            pool, agent, outside_followup_time, set(), routing_config
        )
        selected = route_request_to_agent(filtered, outside_followup_time)
        results.append(selected.request_id)
    
    # All results should be the same
    assert all(r == 'REQ001' for r in results)  # Oldest request should always win