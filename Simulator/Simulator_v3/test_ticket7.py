"""
Test script for Ticket #7: Production Routing Integration.

This script verifies:
1. Production routing functions work correctly
2. Follow-up priority buckets are respected
3. CMO priority levels are respected
4. Mode switching works (follow-up time vs outside)
5. Integration with absent agents
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

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
    
    # Bucket 4 (lowest)
    req4 = Request(
        request_id='REQ_BUCKET4',
        customer_id='CUST004',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_followup_date=past_date
    )
    pool.add_request(req4)
    print("  ✓ Added Bucket 4: No updates + No ECD + Due")
    
    # Bucket 3
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
    print("  ✓ Added Bucket 3: No updates + ECD + Due")
    
    # Bucket 2
    req2 = Request(
        request_id='REQ_BUCKET2',
        customer_id='CUST002',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_tags=['NEW_INTERNAL_NOTE']
    )
    pool.add_request(req2)
    print("  ✓ Added Bucket 2: Internal note + No ECD")
    
    # Bucket 1 (highest)
    req1 = Request(
        request_id='REQ_BUCKET1',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='AGENT001',
        workorder_status='customerreplied',
        workorder_expected_completion_date=datetime(2024, 1, 20, 17, 0, 0)
    )
    pool.add_request(req1)
    print("  ✓ Added Bucket 1: Customer reply + ECD")
    
    # Get follow-up request
    result = followup_priority_filter(pool, agent, current_time)
    
    print(f"\nRouting result:")
    print(f"  Selected: {result.request_id if result else 'None'}")
    print(f"  Expected: REQ_BUCKET1")
    print(f"  Match: {result.request_id == 'REQ_BUCKET1' if result else False}")
    
    assert result is not None and result.request_id == 'REQ_BUCKET1'
    print("\n✓ Bucket 1 (highest priority) correctly selected!")


def test_cmo_priority_levels():
    """Test CMO priority level ordering."""
    print("\n" + "="*60)
    print("Testing CMO Priority Levels")
    print("="*60)
    
    agent = Agent(agent_id='AGENT001', skills=['SkillA'])
    pool = RequestPool()
    current_time = datetime(2024, 1, 15, 15, 0, 0)
    past_date = datetime(2024, 1, 10, 10, 0, 0)
    absent_agents = {'ABSENT_AGENT'}
    
    print("\nAdding requests in reverse priority order:")
    
    # Priority 4 (lowest)
    req4 = Request(
        request_id='REQ_PRIORITY4',
        customer_id='CUST004',
        product='SkillA',
        created_at=current_time,
        workorder_status='new',
        workorder_followup_date=past_date
    )
    pool.add_request(req4)
    print("  ✓ Added Priority 4: Unassigned + New + Due")
    
    # Priority 3
    req3 = Request(
        request_id='REQ_PRIORITY3',
        customer_id='CUST003',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_tags=['NEW_INTERNAL_NOTE']
    )
    pool.add_request(req3)
    print("  ✓ Added Priority 3: Absent agent + Internal note")
    
    # Priority 2
    req2 = Request(
        request_id='REQ_PRIORITY2',
        customer_id='CUST002',
        product='SkillA',
        created_at=current_time,
        sticky_agent_id='ABSENT_AGENT',
        workorder_status='customerreplied'
    )
    pool.add_request(req2)
    print("  ✓ Added Priority 2: Absent agent + Customer reply")
    
    # Priority 1 (highest)
    req1 = Request(
        request_id='REQ_PRIORITY1',
        customer_id='CUST001',
        product='SkillA',
        created_at=current_time,
        workorder_status='customerreplied'
    )
    pool.add_request(req1)
    print("  ✓ Added Priority 1: Unassigned + Customer reply")
    
    # Get CMO request
    result = get_cmo_request(pool, agent, current_time, absent_agents)
    
    print(f"\nRouting result:")
    print(f"  Selected: {result.request_id if result else 'None'}")
    print(f"  Expected: REQ_PRIORITY1")
    print(f"  Match: {result.request_id == 'REQ_PRIORITY1' if result else False}")
    
    assert result is not None and result.request_id == 'REQ_PRIORITY1'
    print("\n✓ Priority 1 (highest) correctly selected!")


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
    
    # Test 1: During follow-up time (14:00-15:30 UTC)
    print("\n1. Testing during follow-up window (14:30 UTC):")
    followup_time = datetime(2024, 1, 15, 14, 30, 0)
    result = get_production_routed_request(pool, agent, followup_time, set(), config)
    print(f"   Selected: {result.request_id if result else 'None'}")
    print(f"   Expected: REQ_FOLLOWUP (Mode A: follow-up primary)")
    print(f"   is_followup flag: {result.is_followup if result else 'N/A'}")
    assert result and result.request_id == 'REQ_FOLLOWUP'
    print("   ✓ Mode A working correctly!")
    
    # Mark as assigned to allow re-selection
    pool.assign_request(result.request_id, 'AGENT001')
    pool.complete_request(result.request_id)
    
    # Re-add for next test
    pool.add_request(followup_req)
    pool.add_request(cmo_req)
    
    # Test 2: Outside follow-up time (17:00 UTC)
    print("\n2. Testing outside follow-up window (17:00 UTC):")
    outside_time = datetime(2024, 1, 15, 17, 0, 0)
    result = get_production_routed_request(pool, agent, outside_time, set(), config)
    print(f"   Selected: {result.request_id if result else 'None'}")
    print(f"   Expected: REQ_CMO (Mode B: CMO primary)")
    print(f"   is_followup flag: {result.is_followup if result else 'N/A'}")
    assert result and result.request_id == 'REQ_CMO'
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
    
    result = get_cmo_request(pool, agent, current_time, absent_agents)
    
    print(f"\nRouting result:")
    print(f"  Selected: {result.request_id if result else 'None'}")
    print(f"  from_absent_agent flag: {result.from_absent_agent if result else 'N/A'}")
    
    assert result is not None
    assert result.from_absent_agent is True
    print("\n✓ Absent agent request correctly routed and flagged!")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("TICKET #7: Production Routing Integration - Verification Tests")
    print("="*70)
    
    try:
        test_followup_priority_buckets()
        test_cmo_priority_levels()
        test_routing_mode_switching()
        test_absent_agent_integration()
        
        print("\n" + "="*70)
        print("✓ All Ticket #7 tests passed successfully!")
        print("="*70)
        print("\nProduction routing is now ready for integration in Ticket #8!")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()