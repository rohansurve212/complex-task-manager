"""
Unit tests for production routing logic.

Tests cover:
- Follow-up priority filter (4 buckets)
- CMO request routing (4 priority levels)
- Production routing mode switching
- Integration with absent agents
"""

import pytest
from datetime import datetime
from models.request import Request
from models.agent import Agent
from models.request_pool import RequestPool
from config.scenario_config import RoutingConfig
from simulation.production_routing import (
    followup_priority_filter,
    get_cmo_request,
    get_production_routed_request
)


@pytest.fixture
def agent():
    """Fixture providing a test agent."""
    return Agent(agent_id='AGENT001', skills=['SkillA'])


@pytest.fixture
def pool():
    """Fixture providing an empty request pool."""
    return RequestPool()


@pytest.fixture
def current_time():
    """Fixture providing current time (Monday 10 AM EST = 15:00 UTC)."""
    return datetime(2024, 1, 15, 15, 0, 0)


@pytest.fixture
def routing_config():
    """Fixture providing default routing configuration."""
    return RoutingConfig(pilot_program_enabled=True)


# ============================================================================
# Test Follow-up Priority Filter
# ============================================================================

def test_followup_no_selfassigned_requests(pool, agent, current_time):
    """Test followup_priority_filter returns None when no self-assigned requests."""
    # Add requests but none are self-assigned to this agent
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='OTHER_AGENT'
    )
    pool.add_request(req)
    
    result = followup_priority_filter(pool, agent, current_time)
    assert result is None


def test_followup_bucket1_customer_update_with_ecd(pool, agent, current_time):
    """Test bucket 1: Self-assigned + customer update + ECD."""
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0)
    )
    pool.add_request(req)
    
    result = followup_priority_filter(pool, agent, current_time)
    assert result is not None
    assert result.request_id == 'REQ001'


def test_followup_bucket2_internal_note_no_ecd(pool, agent, current_time):
    """Test bucket 2: Self-assigned + internal note + NO ECD."""
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_tags=['NEW_INTERNAL_NOTE']
    )
    pool.add_request(req)
    
    result = followup_priority_filter(pool, agent, current_time)
    assert result is not None
    assert result.request_id == 'REQ001'


def test_followup_bucket3_no_updates_with_ecd_due(pool, agent, current_time):
    """Test bucket 3: Self-assigned + NO updates + ECD + followup due."""
    past_date = datetime(2024, 1, 10, 10, 0, 0)  # Past date
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0),
        workorder_followup_date=past_date
    )
    pool.add_request(req)
    
    result = followup_priority_filter(pool, agent, current_time)
    assert result is not None
    assert result.request_id == 'REQ001'


def test_followup_bucket4_no_updates_no_ecd_due(pool, agent, current_time):
    """Test bucket 4: Self-assigned + NO updates + NO ECD + followup due."""
    past_date = datetime(2024, 1, 10, 10, 0, 0)
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_followup_date=past_date
    )
    pool.add_request(req)
    
    result = followup_priority_filter(pool, agent, current_time)
    assert result is not None
    assert result.request_id == 'REQ001'


def test_followup_bucket_priority_order(pool, agent, current_time):
    """Test that higher priority buckets are selected first."""
    past_date = datetime(2024, 1, 10, 10, 0, 0)
    
    # Add bucket 4 request (lowest priority)
    req4 = Request(
        request_id='REQ004',
        customer_id='CUST004',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_followup_date=past_date
    )
    pool.add_request(req4)
    
    # Add bucket 1 request (highest priority)
    req1 = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0)
    )
    pool.add_request(req1)
    
    result = followup_priority_filter(pool, agent, current_time)
    # Should return bucket 1 even though bucket 4 was added first
    assert result.request_id == 'REQ001'


# ============================================================================
# Test CMO Request Routing
# ============================================================================

def test_cmo_priority1_unassigned_customer_reply(pool, agent, current_time):
    """Test priority 1: Unassigned + customer replied."""
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        workorder_status='customerreplied'
    )
    pool.add_request(req)
    
    result = get_cmo_request(pool, agent, current_time, set())
    assert result is not None
    assert result.request_id == 'REQ001'
    assert result.from_absent_agent is False


def test_cmo_priority2_absent_agent_customer_reply(pool, agent, current_time):
    """Test priority 2: Absent agent + customer replied."""
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_status='customerreplied'
    )
    pool.add_request(req)
    
    absent_agents = {'ABSENT_AGENT'}
    result = get_cmo_request(pool, agent, current_time, absent_agents)
    assert result is not None
    assert result.request_id == 'REQ001'
    assert result.from_absent_agent is True


def test_cmo_priority3_absent_agent_internal_note(pool, agent, current_time):
    """Test priority 3: Absent agent + internal note."""
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_tags=['NEW_INTERNAL_NOTE']
    )
    pool.add_request(req)
    
    absent_agents = {'ABSENT_AGENT'}
    result = get_cmo_request(pool, agent, current_time, absent_agents)
    assert result is not None
    assert result.request_id == 'REQ001'
    assert result.from_absent_agent is True


def test_cmo_priority4_unassigned_new_followup_due(pool, agent, current_time):
    """Test priority 4: Unassigned + new + followup due."""
    past_date = datetime(2024, 1, 10, 10, 0, 0)
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        workorder_status='new',
        workorder_followup_date=past_date
    )
    pool.add_request(req)
    
    result = get_cmo_request(pool, agent, current_time, set())
    assert result is not None
    assert result.request_id == 'REQ001'


def test_cmo_priority_order(pool, agent, current_time):
    """Test that CMO priorities are respected."""
    past_date = datetime(2024, 1, 10, 10, 0, 0)
    
    # Add priority 4 (lowest)
    req4 = Request(
        request_id='REQ004',
        customer_id='CUST004',
        product='SkillA',
        created_at=current_time,
        workorder_status='new',
        workorder_followup_date=past_date
    )
    pool.add_request(req4)
    
    # Add priority 1 (highest)
    req1 = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        workorder_status='customerreplied'
    )
    pool.add_request(req1)
    
    result = get_cmo_request(pool, agent, current_time, set())
    assert result.request_id == 'REQ001'


# ============================================================================
# Test Production Routing Mode Switching
# ============================================================================

def test_production_routing_followup_time_pilot_enabled(pool, agent, routing_config):
    """Test Mode A: Follow-up time + pilot enabled → followup first, CMO fallback."""
    # Time is Monday 10 AM EST = 15:00 UTC (within first follow-up window 14:00-15:30)
    followup_time = datetime(2024, 1, 15, 15, 0, 0)
    
    # Add both types of requests
    followup_req = Request(
        request_id='REQ_FOLLOWUP',
        customer_id='CUST001',
        product='SkillA',
        created_at=followup_time,
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0)
    )
    pool.add_request(followup_req)
    
    cmo_req = Request(
        request_id='REQ_CMO',
        customer_id='CUST002',
        product='SkillA',
        created_at=followup_time,
        workorder_status='customerreplied'
    )
    pool.add_request(cmo_req)
    
    result = get_production_routed_request(
        pool, agent, followup_time, set(), routing_config
    )
    
    # Should get follow-up request (Mode A primary)
    assert result is not None
    assert result.request_id == 'REQ_FOLLOWUP'
    assert result.is_followup is True


def test_production_routing_outside_followup_time(pool, agent, routing_config):
    """Test Mode B: Outside follow-up time → CMO first, followup fallback."""
    # Time is Monday 12 PM EST = 17:00 UTC (outside follow-up windows)
    outside_time = datetime(2024, 1, 15, 17, 0, 0)
    
    # Add both types of requests
    followup_req = Request(
        request_id='REQ_FOLLOWUP',
        customer_id='CUST001',
        product='SkillA',
        created_at=outside_time,
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0)
    )
    pool.add_request(followup_req)
    
    cmo_req = Request(
        request_id='REQ_CMO',
        customer_id='CUST002',
        product='SkillA',
        created_at=outside_time,
        workorder_status='customerreplied'
    )
    pool.add_request(cmo_req)
    
    result = get_production_routed_request(
        pool, agent, outside_time, set(), routing_config
    )
    
    # Should get CMO request (Mode B primary)
    assert result is not None
    assert result.request_id == 'REQ_CMO'
    assert result.is_followup is False


def test_production_routing_pilot_disabled(pool, agent):
    """Test that pilot disabled means no follow-ups even in follow-up time."""
    config = RoutingConfig(pilot_program_enabled=False)
    followup_time = datetime(2024, 1, 15, 15, 0, 0)
    
    # Add only follow-up request
    followup_req = Request(
        request_id='REQ_FOLLOWUP',
        customer_id='CUST001',
        product='SkillA',
        created_at=followup_time,
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0)
    )
    pool.add_request(followup_req)
    
    result = get_production_routed_request(
        pool, agent, followup_time, set(), config
    )
    
    # Should return None (pilot disabled, so no follow-ups)
    assert result is None


def test_production_routing_fallback_to_cmo(pool, agent, routing_config):
    """Test fallback from follow-up to CMO when no follow-ups available."""
    followup_time = datetime(2024, 1, 15, 15, 0, 0)
    
    # Add only CMO request (no follow-ups)
    cmo_req = Request(
        request_id='REQ_CMO',
        customer_id='CUST001',
        product='SkillA',
        created_at=followup_time,
        workorder_status='customerreplied'
    )
    pool.add_request(cmo_req)
    
    result = get_production_routed_request(
        pool, agent, followup_time, set(), routing_config
    )
    
    # Should get CMO as fallback
    assert result is not None
    assert result.request_id == 'REQ_CMO'
    assert result.is_followup is False


def test_production_routing_fallback_to_followup(pool, agent, routing_config):
    """Test fallback from CMO to follow-up when no CMO available."""
    outside_time = datetime(2024, 1, 15, 17, 0, 0)
    
    # Add only follow-up request (no CMO)
    followup_req = Request(
        request_id='REQ_FOLLOWUP',
        customer_id='CUST001',
        product='SkillA',
        created_at=outside_time,
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0)
    )
    pool.add_request(followup_req)
    
    result = get_production_routed_request(
        pool, agent, outside_time, set(), routing_config
    )
    
    # Should get follow-up as fallback
    assert result is not None
    assert result.request_id == 'REQ_FOLLOWUP'
    assert result.is_followup is True


def test_production_routing_no_requests(pool, agent, current_time, routing_config):
    """Test that None is returned when no requests are available."""
    result = get_production_routed_request(
        pool, agent, current_time, set(), routing_config
    )
    assert result is None


# ============================================================================
# Test Integration with Absent Agents
# ============================================================================

def test_absent_agent_requests_available_to_present_agents(pool, agent, current_time):
    """Test that requests from absent agents are available to present agents."""
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_status='customerreplied'
    )
    pool.add_request(req)
    
    absent_agents = {'ABSENT_AGENT'}
    result = get_cmo_request(pool, agent, current_time, absent_agents)
    
    assert result is not None
    assert result.from_absent_agent is True