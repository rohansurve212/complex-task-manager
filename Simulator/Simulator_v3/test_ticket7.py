# Path - /Simulator/Simulator_v3/test_ticket7.py

"""
Test script for Ticket #7: Production Filtering Integration.

This script verifies:
1. Production filtering functions work correctly
2. Follow-up priority buckets are respected
3. CMO categories collect all requests
4. 5-level priority bucketing works
5. Mode switching works (follow-up time vs outside)
6. Integration with absent agents
"""

import sys
from pathlib import Path

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

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_followup_priority_buckets():
    """Test follow-up priority bucket ordering."""
    print("\n" + "="*60)
    print("Testing Follow-up Priority Buckets")
    print("="*60)
    
    agent = Agent(agent_id='AGENT001', skills=['SkillA'])
    pool = RequestPool()
    current_time = datetime(2024, 1, 15, 15, 0, 0)
    past_date = datetime(2024, 1, 10, 10, 0, 0)
    
    # Add requests in reverse priority order
    print("\nAdding requests in reverse priority order:")
    
    # Bucket 4 (lowest) - 2 requests
    req4a = Request(
        request_id='REQ_BUCKET4A',
        customer_id='CUST004A',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_followup_date=past_date
    )
    pool.add_request(req4a)
    
    req4b = Request(
        request_id='REQ_BUCKET4B',
        customer_id='CUST004B',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_followup_date=past_date
    )
    pool.add_request(req4b)
    print("  ✓ Added 2 requests to Bucket 4: No updates + No ECD + Due")
    
    # Bucket 3 - 1 request
    req3 = Request(
        request_id='REQ_BUCKET3',
        customer_id='CUST003',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0),
        workorder_followup_date=past_date
    )
    pool.add_request(req3)
    print("  ✓ Added 1 request to Bucket 3: No updates + ECD + Due")
    
    # Bucket 2 - 1 request
    req2 = Request(
        request_id='REQ_BUCKET2',
        customer_id='CUST002',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_tags=['NEW_INTERNAL_NOTE']
    )
    pool.add_request(req2)
    print("  ✓ Added 1 request to Bucket 2: Internal note + No ECD")
    
    # Bucket 1 (highest) - 2 requests
    req1a = Request(
        request_id='REQ_BUCKET1A',
        customer_id='CUST001A',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0)
    )
    pool.add_request(req1a)
    
    req1b = Request(
        request_id='REQ_BUCKET1B',
        customer_id='CUST001B',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0)
    )
    pool.add_request(req1b)
    print("  ✓ Added 2 requests to Bucket 1: Customer reply + ECD")
    
    # Get follow-up requests
    result = filter_followup_requests(pool, agent, current_time)
    
    print("\nFiltering result:")
    print(f"  Requests returned: {len(result)}")
    print(f"  Request IDs: {[r.request_id for r in result]}")
    print("  Expected: 2 requests from Bucket 1 (REQ_BUCKET1A, REQ_BUCKET1B)")
    
    assert len(result) == 2
    assert 'REQ_BUCKET1A' in [r.request_id for r in result]
    assert 'REQ_BUCKET1B' in [r.request_id for r in result]
    print("\n✓ Bucket 1 (highest priority) correctly selected with ALL requests!")


def test_cmo_all_categories():
    """Test that CMO collects ALL requests from all 4 categories."""
    print("\n" + "="*60)
    print("Testing CMO Request Collection")
    print("="*60)
    
    agent = Agent(agent_id='AGENT001', skills=['SkillA'])
    pool = RequestPool()
    current_time = datetime(2024, 1, 15, 15, 0, 0)
    past_date = datetime(2024, 1, 10, 10, 0, 0)
    absent_agents = {'ABSENT_AGENT'}
    
    print("\nAdding requests from all 4 CMO categories:")
    
    # Category 1: Unassigned + customerreplied
    req1 = Request(
        request_id='REQ_CAT1',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        workorder_status='customerreplied'
    )
    pool.add_request(req1)
    print("  ✓ Added Category 1: Unassigned + Customer reply")
    
    # Category 2: Absent agent + customerreplied
    req2 = Request(
        request_id='REQ_CAT2',
        customer_id='CUST002',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_status='customerreplied'
    )
    pool.add_request(req2)
    print("  ✓ Added Category 2: Absent agent + Customer reply")
    
    # Category 3: Absent agent + internal note
    req3 = Request(
        request_id='REQ_CAT3',
        customer_id='CUST003',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_tags=['NEW_INTERNAL_NOTE']
    )
    pool.add_request(req3)
    print("  ✓ Added Category 3: Absent agent + Internal note")
    
    # Category 4: Unassigned + new + followup due
    req4 = Request(
        request_id='REQ_CAT4',
        customer_id='CUST004',
        product='SkillA',
        created_at=current_time,
        workorder_status='new',
        workorder_followup_date=past_date
    )
    pool.add_request(req4)
    print("  ✓ Added Category 4: Unassigned + New + Due")
    
    # Get CMO requests
    result = filter_cmo_requests(pool, agent, current_time, absent_agents)
    
    print("\nFiltering result:")
    print(f"  Total requests returned: {len(result)}")
    print(f"  Request IDs: {[r.request_id for r in result]}")
    print("  Expected: ALL 4 requests from all categories")
    
    assert len(result) == 4
    request_ids = [r.request_id for r in result]
    assert 'REQ_CAT1' in request_ids
    assert 'REQ_CAT2' in request_ids
    assert 'REQ_CAT3' in request_ids
    assert 'REQ_CAT4' in request_ids
    print("\n✓ All 4 CMO categories correctly collected!")


def test_5level_priority_bucketing():
    """Test 5-level priority bucketing returns all from highest level."""
    print("\n" + "="*60)
    print("Testing 5-Level Priority Bucketing")
    print("="*60)
    
    current_time = datetime(2024, 1, 15, 15, 0, 0)
    
    print("\nAdding requests across different priority levels:")
    
    # Priority 5 (lowest) - 2 requests
    req5a = Request(
        request_id='REQ_P5A',
        customer_id='CUST5A',
        product='SkillA',
        created_at=current_time,
        is_escalated=False
    )
    req5b = Request(
        request_id='REQ_P5B',
        customer_id='CUST5B',
        product='SkillA',
        created_at=current_time,
        is_escalated=False
    )
    print("  ✓ Added 2 requests to Priority 5: Commons (not escalated)")
    
    # Priority 1 (highest) - 3 requests
    req1a = Request(
        request_id='REQ_P1A',
        customer_id='CUST1A',
        product='SkillA',
        created_at=current_time,
        is_winback=True,
        is_escalated=True
    )
    req1b = Request(
        request_id='REQ_P1B',
        customer_id='CUST1B',
        product='SkillA',
        created_at=current_time,
        is_atl_rf=True,
        is_escalated=True
    )
    req1c = Request(
        request_id='REQ_P1C',
        customer_id='CUST1C',
        product='SkillA',
        created_at=current_time,
        is_winback=True,
        is_escalated=True
    )
    print("  ✓ Added 3 requests to Priority 1: (Winback/ATL_RF) + Escalated")
    
    requests = [req5a, req5b, req1a, req1b, req1c]
    
    # Apply 5-level priority
    result = apply_priority_levels(requests)
    
    print("\nPriority bucketing result:")
    print(f"  Requests returned: {len(result)}")
    print(f"  Request IDs: {[r.request_id for r in result]}")
    print("  Expected: ALL 3 requests from Priority 1")
    
    assert len(result) == 3
    assert 'REQ_P1A' in [r.request_id for r in result]
    assert 'REQ_P1B' in [r.request_id for r in result]
    assert 'REQ_P1C' in [r.request_id for r in result]
    assert 'REQ_P5A' not in [r.request_id for r in result]
    assert 'REQ_P5B' not in [r.request_id for r in result]
    print("\n✓ Priority 1 (highest) correctly selected with ALL requests!")


def test_routing_mode_switching():
    """Test routing mode switching based on time and pilot setting."""
    print("\n" + "="*60)
    print("Testing Routing Mode Switching")
    print("="*60)
    
    agent = Agent(agent_id='AGENT001', skills=['SkillA'])
    pool = RequestPool()
    config = RoutingConfig(pilot_program_enabled=True)
    
    # Add follow-up request
    followup_req = Request(
        request_id='REQ_FOLLOWUP',
        customer_id='CUST001',
        product='SkillA',
        created_at=datetime(2024, 1, 15, 15, 0, 0),
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
        created_at=datetime(2024, 1, 15, 15, 0, 0),
        workorder_status='customerreplied'
    )
    pool.add_request(cmo_req)
    
    # Test 1: During follow-up time (14:30 UTC)
    print("\n1. Testing during follow-up window (14:30 UTC):")
    followup_time = datetime(2024, 1, 15, 14, 30, 0)
    result = filter_production_requests(pool, agent, followup_time, set(), config)
    print(f"   Requests returned: {len(result)}")
    print(f"   Selected: {[r.request_id for r in result]}")
    print("   Expected: [REQ_FOLLOWUP] (Mode A: follow-up primary)")
    print(f"   is_followup flags: {[r.is_followup for r in result]}")
    assert len(result) == 1
    assert result[0].request_id == 'REQ_FOLLOWUP'
    assert result[0].is_followup is True
    print("   ✓ Mode A working correctly!")
    
    # Mark as assigned to allow re-selection
    pool.assign_request(result[0].request_id, 'AGENT001')
    pool.complete_request(result[0].request_id)
    
    # Re-add for next test
    pool.add_request(followup_req)
    pool.add_request(cmo_req)
    
    # Test 2: Outside follow-up time (17:00 UTC)
    print("\n2. Testing outside follow-up window (17:00 UTC):")
    outside_time = datetime(2024, 1, 15, 17, 0, 0)
    result = filter_production_requests(pool, agent, outside_time, set(), config)
    print(f"   Requests returned: {len(result)}")
    print(f"   Selected: {[r.request_id for r in result]}")
    print("   Expected: [REQ_CMO] (Mode B: CMO primary)")
    print(f"   is_followup flags: {[r.is_followup for r in result]}")
    assert len(result) == 1
    assert result[0].request_id == 'REQ_CMO'
    assert result[0].is_followup is False
    print("   ✓ Mode B working correctly!")


def test_absent_agent_integration():
    """Test integration with absent agents."""
    print("\n" + "="*60)
    print("Testing Absent Agent Integration")
    print("="*60)
    
    agent = Agent(agent_id='AGENT001', skills=['SkillA'])
    pool = RequestPool()
    current_time = datetime(2024, 1, 15, 15, 0, 0)
    absent_agents = {'ABSENT_AGENT'}
    
    # Add request from absent agent
    req = Request(
        request_id='REQ001',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_status='customerreplied'
    )
    pool.add_request(req)
    
    print("\nRequest details:")
    print(f"  Request ID: {req.request_id}")
    print(f"  Sticky agent: {req.sticky_agent_id}")
    print(f"  Absent agents: {absent_agents}")
    
    result = filter_cmo_requests(pool, agent, current_time, absent_agents)
    
    print("\nFiltering result:")
    print(f"  Requests returned: {len(result)}")
    print(f"  Selected: {[r.request_id for r in result]}")
    print(f"  from_absent_agent flags: {[r.from_absent_agent for r in result]}")
    
    assert len(result) == 1
    assert result[0].from_absent_agent is True
    print("\n✓ Absent agent request correctly filtered and flagged!")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("TICKET #7: Production Filtering Integration - Verification Tests")
    print("="*70)
    
    try:
        test_followup_priority_buckets()
        test_cmo_all_categories()
        test_5level_priority_bucketing()
        test_routing_mode_switching()
        test_absent_agent_integration()
        
        print("\n" + "="*70)
        print("✓ All Ticket #7 tests passed successfully!")
        print("="*70)
        print("\nProduction filtering is ready for integration in Ticket #8!")
        print("Next: Implement agent processes that call filter_production_requests()")
        print("      and pass results to routing/scoring algorithm.")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()