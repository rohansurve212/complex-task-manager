"""
Production routing logic for STM Routing Simulator v3.0.

This module implements the production routing algorithm from search_requests_utils.py:
- Follow-up priority filter (4 buckets)
- CMO (Common Mailbox Operations) routing (4 priority levels)
- Time-based routing mode switching

Key concepts:
- "Sticky assignment": sticky_agent_id is the agent who "owns" the request for follow-up
- "Assigned": assigned_agent_id is the agent currently working on it
- Requests can be in the pool (unassigned) but still have a sticky_agent_id
"""

from typing import Optional, List, Set
from datetime import datetime
from models.request import Request
from models.agent import Agent
from models.request_pool import RequestPool
from config.scenario_config import RoutingConfig


def followup_priority_filter(
    pool: RequestPool,
    agent: Agent,
    current_time: datetime
) -> Optional[Request]:
    """
    Get highest priority follow-up request for an agent.
    
    Follow-up requests are self-assigned (sticky_agent_id matches agent).
    Priority buckets (highest to lowest):
    1. Self-assigned + (Customer update OR Internal note) + Has ECD
    2. Self-assigned + (Customer update OR Internal note) + NO ECD
    3. Self-assigned + NO updates + Has ECD + followUpDate passed
    4. Self-assigned + NO updates + NO ECD + followUpDate passed
    
    Args:
        pool: RequestPool to search
        agent: Agent to find follow-up for
        current_time: Current simulation time
        
    Returns:
        Highest priority follow-up request, or None if no follow-ups
    """
    # Get all pending requests with matching skill
    skill_matched = pool.filter_requests(
        status='pending',
        skills=agent.skills
    )
    
    # Filter for self-assigned (sticky) requests only
    self_assigned = [r for r in skill_matched if r.sticky_agent_id == agent.agent_id]
    
    if not self_assigned:
        return None
    
    # Bucket 1: Self-assigned + (Customer update OR Internal note) + Has ECD
    bucket1 = [
        r for r in self_assigned
        if r.has_customer_update_or_internal_note() and r.has_expected_completion_date()
    ]
    if bucket1:
        return bucket1[0]  # Return first match
    
    # Bucket 2: Self-assigned + (Customer update OR Internal note) + NO ECD
    bucket2 = [
        r for r in self_assigned
        if r.has_customer_update_or_internal_note() and not r.has_expected_completion_date()
    ]
    if bucket2:
        return bucket2[0]
    
    # Bucket 3: Self-assigned + NO updates + Has ECD + followUpDate passed
    bucket3 = [
        r for r in self_assigned
        if (not r.has_customer_update_or_internal_note() 
            and r.has_expected_completion_date()
            and r.is_followup_due(current_time))
    ]
    if bucket3:
        return bucket3[0]
    
    # Bucket 4: Self-assigned + NO updates + NO ECD + followUpDate passed
    bucket4 = [
        r for r in self_assigned
        if (not r.has_customer_update_or_internal_note()
            and not r.has_expected_completion_date()
            and r.is_followup_due(current_time))
    ]
    if bucket4:
        return bucket4[0]
    
    # No follow-up requests match any bucket
    return None


def get_cmo_request(
    pool: RequestPool,
    agent: Agent,
    current_time: datetime,
    absent_agent_ids: Set[str]
) -> Optional[Request]:
    """
    Get highest priority CMO (Common Mailbox Operations) request.
    
    CMO priority levels (highest to lowest):
    1. Unassigned + status='customerreplied'
    2. Absent agent + status='customerreplied'
    3. Absent agent + has 'NEW_INTERNAL_NOTE' tag
    4. Unassigned + status='new' + followUpDate passed
    
    Args:
        pool: RequestPool to search
        agent: Agent to find CMO request for
        current_time: Current simulation time
        absent_agent_ids: Set of currently absent agent IDs
        
    Returns:
        Highest priority CMO request, or None if no CMO requests
    """
    # Get all pending requests with matching skill
    skill_matched = pool.filter_requests(
        status='pending',
        skills=agent.skills
    )
    
    # Priority 1: Unassigned + status='customerreplied'
    priority1 = [
        r for r in skill_matched
        if r.sticky_agent_id is None and r.workorder_status == 'customerreplied'
    ]
    if priority1:
        return priority1[0]
    
    # Priority 2: Absent agent + status='customerreplied'
    priority2 = [
        r for r in skill_matched
        if (r.sticky_agent_id in absent_agent_ids 
            and r.workorder_status == 'customerreplied')
    ]
    if priority2:
        # Mark as from absent agent (for metrics/tracking)
        request = priority2[0]
        request.from_absent_agent = True
        return request
    
    # Priority 3: Absent agent + has 'NEW_INTERNAL_NOTE' tag
    priority3 = [
        r for r in skill_matched
        if r.sticky_agent_id in absent_agent_ids and r.has_internal_note()
    ]
    if priority3:
        request = priority3[0]
        request.from_absent_agent = True
        return request
    
    # Priority 4: Unassigned + status='new' + followUpDate passed
    priority4 = [
        r for r in skill_matched
        if (r.sticky_agent_id is None 
            and r.workorder_status == 'new'
            and r.is_followup_due(current_time))
    ]
    if priority4:
        return priority4[0]
    
    # No CMO requests found
    return None


def get_production_routed_request(
    pool: RequestPool,
    agent: Agent,
    current_time: datetime,
    absent_agent_ids: Set[str],
    routing_config: RoutingConfig
) -> Optional[Request]:
    """
    Get next request for agent using production routing logic.
    
    This implements the filter_static() logic from search_requests_utils.py:
    
    Mode A (Follow-up Time + Pilot Enabled):
        PRIMARY: Follow-up requests (4 priority buckets)
        FALLBACK: CMO requests (if no follow-ups)
    
    Mode B (Outside Follow-up Time OR Pilot Disabled):
        PRIMARY: CMO requests (4 priority levels)
        FALLBACK: Follow-up requests (if pilot enabled AND no CMO)
    
    Args:
        pool: RequestPool to search
        agent: Agent requesting work
        current_time: Current simulation time
        absent_agent_ids: Set of currently absent agent IDs
        routing_config: Routing configuration
        
    Returns:
        Next request to assign, or None if no requests available
    """
    # Check if we're in follow-up time window
    is_followup_time = agent.is_in_followup_window(
        current_time,
        window_1_start=routing_config.followup_window_1_start,
        window_1_end=routing_config.followup_window_1_end,
        window_2_start=routing_config.followup_window_2_start,
        window_2_end=routing_config.followup_window_2_end
    )
    
    pilot_enabled = routing_config.pilot_program_enabled
    
    # Mode A: Follow-up time AND pilot enabled
    if is_followup_time and pilot_enabled:
        # PRIMARY: Try follow-up requests first
        request = followup_priority_filter(pool, agent, current_time)
        if request:
            request.is_followup = True
            return request
        
        # FALLBACK: Try CMO requests
        request = get_cmo_request(pool, agent, current_time, absent_agent_ids)
        if request:
            request.is_followup = False
            return request
        
        return None
    
    # Mode B: Outside follow-up time OR pilot disabled
    else:
        # PRIMARY: Try CMO requests first
        request = get_cmo_request(pool, agent, current_time, absent_agent_ids)
        if request:
            request.is_followup = False
            return request
        
        # FALLBACK: Try follow-up requests (only if pilot enabled)
        if pilot_enabled:
            request = followup_priority_filter(pool, agent, current_time)
            if request:
                request.is_followup = True
                return request
        
        return None