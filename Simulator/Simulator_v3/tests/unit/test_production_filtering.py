# Path - /Simulator/Simulator_v3/tests/unit/test_production_filtering.py

"""
Unit tests for production filtering logic.

Tests cover:
- Follow-up request filtering (4 priority buckets)
- CMO request filtering (4 equal categories)
- 5-level priority bucketing
- Production filtering mode switching
- Integration with absent agents
"""

import pytest
from datetime import datetime
from models.request import Request
from models.agent import Agent
from models.request_pool import RequestPool
from config.scenario_config import RoutingConfig
from simulation.production_filtering import (
    filter_followup_requests,
    filter_cmo_requests,
    filter_production_requests,
    apply_priority_levels
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
# Test Follow-up Request Filtering
# ============================================================================

def test_followup_no_selfassigned_requests(pool, agent, current_time):
    """Test filter_followup_requests returns empty list when no self-assigned requests."""
    # Add requests but none are self-assigned to this agent
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='OTHER_AGENT'
    )
    pool.add_request(req)
    
    result = filter_followup_requests(pool, agent, current_time)
    assert result == []


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
    
    result = filter_followup_requests(pool, agent, current_time)
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'


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
    
    result = filter_followup_requests(pool, agent, current_time)
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'


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
    
    result = filter_followup_requests(pool, agent, current_time)
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'


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
    
    result = filter_followup_requests(pool, agent, current_time)
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'


def test_followup_bucket_priority_order(pool, agent, current_time):
    """Test that higher priority buckets are selected and all from that bucket returned."""
    past_date = datetime(2024, 1, 10, 10, 0, 0)
    
    # Add 2 requests in bucket 4 (lowest priority)
    req4a = Request(
        request_id='REQ004A',
        customer_id='CUST004A',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_followup_date=past_date
    )
    pool.add_request(req4a)
    
    req4b = Request(
        request_id='REQ004B',
        customer_id='CUST004B',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_followup_date=past_date
    )
    pool.add_request(req4b)
    
    # Add 2 requests in bucket 1 (highest priority)
    req1a = Request(
        request_id='REQ001A',
        customer_id='CUST001A',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0)
    )
    pool.add_request(req1a)
    
    req1b = Request(
        request_id='REQ001B',
        customer_id='CUST001B',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0)
    )
    pool.add_request(req1b)
    
    result = filter_followup_requests(pool, agent, current_time)
    
    # Should return ALL from bucket 1 (2 requests)
    assert len(result) == 2
    assert 'REQ001A' in [r.request_id for r in result]
    assert 'REQ001B' in [r.request_id for r in result]
    # Should NOT return bucket 4 requests
    assert 'REQ004A' not in [r.request_id for r in result]
    assert 'REQ004B' not in [r.request_id for r in result]


# ============================================================================
# Test CMO Request Filtering
# ============================================================================

def test_cmo_category1_unassigned_customer_reply(pool, agent, current_time):
    """Test category 1: Unassigned + customer replied."""
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        workorder_status='customerreplied'
    )
    pool.add_request(req)
    
    result = filter_cmo_requests(pool, agent, current_time, set())
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'
    assert result[0].from_absent_agent is False


def test_cmo_category2_absent_agent_customer_reply(pool, agent, current_time):
    """Test category 2: Absent agent + customer replied."""
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
    result = filter_cmo_requests(pool, agent, current_time, absent_agents)
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'
    assert result[0].from_absent_agent is True


def test_cmo_category3_absent_agent_internal_note(pool, agent, current_time):
    """Test category 3: Absent agent + internal note."""
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
    result = filter_cmo_requests(pool, agent, current_time, absent_agents)
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'
    assert result[0].from_absent_agent is True


def test_cmo_category4_unassigned_new_followup_due(pool, agent, current_time):
    """Test category 4: Unassigned + new + followup due."""
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
    
    result = filter_cmo_requests(pool, agent, current_time, set())
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'


def test_cmo_all_categories_combined(pool, agent, current_time):
    """Test that CMO returns ALL requests from all 4 categories combined."""
    past_date = datetime(2024, 1, 10, 10, 0, 0)
    absent_agents = {'ABSENT_AGENT'}
    
    # Category 1: Unassigned + customerreplied
    req1 = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        workorder_status='customerreplied'
    )
    pool.add_request(req1)
    
    # Category 2: Absent agent + customerreplied
    req2 = Request(
        request_id='REQ002',
        customer_id='CUST002',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_status='customerreplied'
    )
    pool.add_request(req2)
    
    # Category 3: Absent agent + internal note
    req3 = Request(
        request_id='REQ003',
        customer_id='CUST003',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_tags=['NEW_INTERNAL_NOTE']
    )
    pool.add_request(req3)
    
    # Category 4: Unassigned + new + followup due
    req4 = Request(
        request_id='REQ004',
        customer_id='CUST004',
        product='SkillA',
        created_at=current_time,
        workorder_status='new',
        workorder_followup_date=past_date
    )
    pool.add_request(req4)
    
    result = filter_cmo_requests(pool, agent, current_time, absent_agents)
    
    # Should return ALL 4 requests (all categories combined)
    assert len(result) == 4
    request_ids = [r.request_id for r in result]
    assert 'REQ001' in request_ids
    assert 'REQ002' in request_ids
    assert 'REQ003' in request_ids
    assert 'REQ004' in request_ids


# ============================================================================
# Test 5-Level Priority Bucketing
# ============================================================================

def test_priority_level1_winback_escalated(current_time):
    """Test priority 1: (winback OR atl_rf) AND escalated."""
    requests = [
        Request(
            request_id='REQ001',
            customer_id='CUST001',
            product='SkillA',
            created_at=current_time,
            is_winback=True,
            is_escalated=True
        ),
        Request(
            request_id='REQ002',
            customer_id='CUST002',
            product='SkillA',
            created_at=current_time,
            is_escalated=False
        )
    ]
    
    result = apply_priority_levels(requests)
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'


def test_priority_level2_winback_not_escalated(current_time):
    """Test priority 2: (winback OR atl_rf) AND NOT escalated."""
    requests = [
        Request(
            request_id='REQ001',
            customer_id='CUST001',
            product='SkillA',
            created_at=current_time,
            is_winback=True,
            is_escalated=False
        ),
        Request(
            request_id='REQ002',
            customer_id='CUST002',
            product='SkillA',
            created_at=current_time,
            has_sla=True,
            is_escalated=True
        )
    ]
    
    # Add priority 1 to ensure priority 2 is not selected
    requests.insert(0, Request(
        request_id='REQ_P1',
        customer_id='CUST_P1',
        product='SkillA',
        created_at=current_time,
        is_winback=True,
        is_escalated=True
    ))
    
    result = apply_priority_levels(requests)
    # Should return priority 1
    assert len(result) == 1
    assert result[0].request_id == 'REQ_P1'
    
    # Now test with only priority 2
    requests_p2_only = [
        Request(
            request_id='REQ001',
            customer_id='CUST001',
            product='SkillA',
            created_at=current_time,
            is_winback=True,
            is_escalated=False
        )
    ]
    result = apply_priority_levels(requests_p2_only)
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'


def test_priority_level3_sla_escalated(current_time):
    """Test priority 3: has_sla AND escalated."""
    requests = [
        Request(
            request_id='REQ001',
            customer_id='CUST001',
            product='SkillA',
            created_at=current_time,
            has_sla=True,
            is_escalated=True
        )
    ]
    
    result = apply_priority_levels(requests)
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'


def test_priority_level4_non_sla_escalated(current_time):
    """Test priority 4: NOT has_sla AND escalated."""
    requests = [
        Request(
            request_id='REQ001',
            customer_id='CUST001',
            product='SkillA',
            created_at=current_time,
            has_sla=False,
            is_escalated=True
        )
    ]
    
    result = apply_priority_levels(requests)
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'


def test_priority_level5_commons(current_time):
    """Test priority 5: NOT escalated (commons)."""
    requests = [
        Request(
            request_id='REQ001',
            customer_id='CUST001',
            product='SkillA',
            created_at=current_time,
            is_escalated=False
        )
    ]
    
    result = apply_priority_levels(requests)
    assert len(result) == 1
    assert result[0].request_id == 'REQ001'


def test_priority_levels_returns_all_from_highest(current_time):
    """Test that apply_priority_levels returns ALL from highest level."""
    requests = [
        # 2 priority 1 requests
        Request(
            request_id='REQ001',
            customer_id='CUST001',
            product='SkillA',
            created_at=current_time,
            is_winback=True,
            is_escalated=True
        ),
        Request(
            request_id='REQ002',
            customer_id='CUST002',
            product='SkillA',
            created_at=current_time,
            is_atl_rf=True,
            is_escalated=True
        ),
        # 1 priority 2 request
        Request(
            request_id='REQ003',
            customer_id='CUST003',
            product='SkillA',
            created_at=current_time,
            is_winback=True,
            is_escalated=False
        )
    ]
    
    result = apply_priority_levels(requests)
    
    # Should return both priority 1 requests
    assert len(result) == 2
    assert 'REQ001' in [r.request_id for r in result]
    assert 'REQ002' in [r.request_id for r in result]
    assert 'REQ003' not in [r.request_id for r in result]


def test_priority_atl_rf_same_as_winback(current_time):
    """Test that is_atl_rf is treated same as is_winback in priorities."""
    # Priority 1: atl_rf + escalated
    req_atl = Request(
        request_id='REQ_ATL',
        customer_id='CUST_ATL',
        product='SkillA',
        created_at=current_time,
        is_atl_rf=True,
        is_escalated=True
    )
    
    result = apply_priority_levels([req_atl])
    assert len(result) == 1
    assert result[0].request_id == 'REQ_ATL'


# ============================================================================
# Test Production Filtering Mode Switching
# ============================================================================

def test_production_filtering_mode_a_followup_primary(pool, agent, routing_config):
    """Test Mode A: Follow-up time + pilot enabled → followup first."""
    # Time is Monday 10 AM EST = 15:00 UTC (within first follow-up window 14:00-15:30)
    followup_time = datetime(2024, 1, 15, 15, 0, 0)
    
    # Add followup request
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
    
    # Add CMO request
    cmo_req = Request(
        request_id='REQ_CMO',
        customer_id='CUST002',
        product='SkillA',
        created_at=followup_time,
        workorder_status='customerreplied'
    )
    pool.add_request(cmo_req)
    
    result = filter_production_requests(
        pool, agent, followup_time, set(), routing_config
    )
    
    # Should get follow-up request (Mode A primary)
    assert len(result) == 1
    assert result[0].request_id == 'REQ_FOLLOWUP'
    assert result[0].is_followup is True


def test_production_filtering_mode_b_cmo_primary(pool, agent, routing_config):
    """Test Mode B: Outside follow-up time → CMO first."""
    # Time is Monday 12 PM EST = 17:00 UTC (outside follow-up windows)
    outside_time = datetime(2024, 1, 15, 17, 0, 0)
    
    # Add followup request
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
    
    # Add CMO request
    cmo_req = Request(
        request_id='REQ_CMO',
        customer_id='CUST002',
        product='SkillA',
        created_at=outside_time,
        workorder_status='customerreplied'
    )
    pool.add_request(cmo_req)
    
    result = filter_production_requests(
        pool, agent, outside_time, set(), routing_config
    )
    
    # Should get CMO request (Mode B primary)
    assert len(result) == 1
    assert result[0].request_id == 'REQ_CMO'
    assert result[0].is_followup is False


def test_production_filtering_pilot_disabled(pool, agent):
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
    
    result = filter_production_requests(
        pool, agent, followup_time, set(), config
    )
    
    # Should return empty (pilot disabled, so no follow-ups)
    assert result == []


def test_production_filtering_fallback_to_cmo(pool, agent, routing_config):
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
    
    result = filter_production_requests(
        pool, agent, followup_time, set(), routing_config
    )
    
    # Should get CMO as fallback
    assert len(result) == 1
    assert result[0].request_id == 'REQ_CMO'
    assert result[0].is_followup is False


def test_production_filtering_fallback_to_followup(pool, agent, routing_config):
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
    
    result = filter_production_requests(
        pool, agent, outside_time, set(), routing_config
    )
    
    # Should get follow-up as fallback
    assert len(result) == 1
    assert result[0].request_id == 'REQ_FOLLOWUP'
    assert result[0].is_followup is True


def test_production_filtering_no_requests(pool, agent, current_time, routing_config):
    """Test that empty list is returned when no requests are available."""
    result = filter_production_requests(
        pool, agent, current_time, set(), routing_config
    )
    assert result == []


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
    result = filter_cmo_requests(pool, agent, current_time, absent_agents)
    
    assert len(result) == 1
    assert result[0].from_absent_agent is True


def test_5level_priority_applied_to_absent_agent_requests(pool, agent, current_time, routing_config):
    """Test that 5-level priority is applied to requests from absent agents."""
    absent_agents = {'ABSENT_AGENT'}
    
    # Add lower priority absent agent request
    req_low = Request(
        request_id='REQ_LOW',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_status='customerreplied',
        is_escalated=False  # Priority 5
    )
    pool.add_request(req_low)
    
    # Add higher priority absent agent request
    req_high = Request(
        request_id='REQ_HIGH',
        customer_id='CUST002',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_status='customerreplied',
        is_winback=True,
        is_escalated=True  # Priority 1
    )
    pool.add_request(req_high)
    
    result = filter_production_requests(
        pool, agent, current_time, absent_agents, routing_config
    )
    
    # Should return only priority 1 request
    assert len(result) == 1
    assert result[0].request_id == 'REQ_HIGH'