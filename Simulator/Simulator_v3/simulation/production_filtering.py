# Path - /Simulator/Simulator_v3/simulation/production_filtering.py

"""
Production filtering logic for STM Routing Simulator v3.0.

This module implements the production FILTERING algorithm:
- Follow-up request filtering (4 priority buckets, returns ALL from highest bucket)
- CMO request filtering (4 equal categories, returns ALL)
- 5-level priority bucketing (returns ALL from highest priority level)
- Time-based mode switching

The filtered requests are then passed to routing.py for prioritization scoring.

Key concepts:
- **sticky_agent_id**: The agent currently assigned to a followup request. Only that agent 
  can work on it (self-assigned followup) unless they are absent.
  
- **Absent agent requests**: When an agent is absent, all their requests (where they are 
  the sticky_agent_id) become CMO requests available to other agents with matching skills.
  
- **Agent-initiated process**: This filtering is called by an available agent actively 
  looking for work. The agent's mode (followup time + pilot status) determines request priority:
  * Mode A (Follow-up time + Pilot): Agent must work on their own followups first, then CMO
  * Mode B (Outside followup time OR Not pilot): Agent works on CMO first, then followups (if pilot)
  
- **CMO (Current Mode of Operations)**: Unassigned requests or requests from absent agents 
  that are available to any agent with matching skills.
"""

from typing import List, Set
from datetime import datetime
from models.request import Request
from models.agent import Agent
from models.request_pool import RequestPool
from config.scenario_config import RoutingConfig


def filter_followup_requests(
    pool: RequestPool,
    agent: Agent,
    current_time: datetime
) -> List[Request]:
    """
    Filter and return ALL follow-up requests from the highest priority bucket for an agent.
    
    Follow-up requests are self-assigned (sticky_agent_id matches agent).
    Only the agent with matching sticky_agent_id can work on these requests.
    
    Priority buckets (highest to lowest):
    1. Self-assigned + (Customer update OR Internal note) + Has ECD
    2. Self-assigned + (Customer update OR Internal note) + NO ECD
    3. Self-assigned + NO updates + Has ECD + followUpDate passed
    4. Self-assigned + NO updates + NO ECD + followUpDate passed
    
    Returns ALL requests from the first non-empty bucket.
    
    Args:
        pool: RequestPool to search
        agent: Agent to find follow-ups for
        current_time: Current simulation time
        
    Returns:
        List of ALL follow-up requests from highest priority bucket, or empty list
    """
    # Get all pending requests with matching skill
    skill_matched = pool.filter_requests(
        status='pending',
        skills=agent.skills
    )
    
    # Filter for self-assigned (sticky) requests only
    self_assigned = [r for r in skill_matched if r.sticky_agent_id == agent.agent_id]
    
    if not self_assigned:
        return []
    
    # Bucket 1: Self-assigned + (Customer update OR Internal note) + Has ECD
    bucket1 = [
        r for r in self_assigned
        if r.has_customer_update_or_internal_note() and r.has_expected_completion_date()
    ]
    if bucket1:
        return bucket1  # Return ALL from bucket 1
    
    # Bucket 2: Self-assigned + (Customer update OR Internal note) + NO ECD
    bucket2 = [
        r for r in self_assigned
        if r.has_customer_update_or_internal_note() and not r.has_expected_completion_date()
    ]
    if bucket2:
        return bucket2  # Return ALL from bucket 2
    
    # Bucket 3: Self-assigned + NO updates + Has ECD + followUpDate passed
    bucket3 = [
        r for r in self_assigned
        if (not r.has_customer_update_or_internal_note() 
            and r.has_expected_completion_date()
            and r.is_followup_due(current_time))
    ]
    if bucket3:
        return bucket3  # Return ALL from bucket 3
    
    # Bucket 4: Self-assigned + NO updates + NO ECD + followUpDate passed
    bucket4 = [
        r for r in self_assigned
        if (not r.has_customer_update_or_internal_note()
            and not r.has_expected_completion_date()
            and r.is_followup_due(current_time))
    ]
    if bucket4:
        return bucket4  # Return ALL from bucket 4
    
    return []


def filter_cmo_requests(
    pool: RequestPool,
    agent: Agent,
    current_time: datetime,
    absent_agent_ids: Set[str]
) -> List[Request]:
    """
    Filter and collect ALL CMO (Common Mailbox Operations) requests from 4 equal categories.
    
    CMO requests are available to any agent with matching skills.
    When an agent is absent, their requests become CMO requests for others.
    
    CMO categories (NO priority order between them):
    1. Unassigned + status='customerreplied'
    2. Absent agent + status='customerreplied'
    3. Absent agent + has 'NEW_INTERNAL_NOTE' tag
    4. Unassigned + status='new' + (no followup date OR followup date passed)
    
    Args:
        pool: RequestPool to search
        agent: Agent to find CMO requests for
        current_time: Current simulation time
        absent_agent_ids: Set of currently absent agent IDs
        
    Returns:
        List of ALL CMO requests from all 4 categories combined
    """
    # Get all pending requests with matching skill
    skill_matched = pool.filter_requests(
        status='pending',
        skills=agent.skills
    )
    
    cmo_requests = []
    
    # Category 1: Unassigned + customerreplied
    cat1 = [
        r for r in skill_matched
        if r.sticky_agent_id is None and r.workorder_status == 'customerreplied'
    ]
    cmo_requests.extend(cat1)
    
    # Category 2: Absent agent + customerreplied
    cat2 = [
        r for r in skill_matched
        if (r.sticky_agent_id in absent_agent_ids 
            and r.workorder_status == 'customerreplied')
    ]
    # Mark as from absent agent
    for r in cat2:
        r.from_absent_agent = True
    cmo_requests.extend(cat2)
    
    # Category 3: Absent agent + internal note
    cat3 = [
        r for r in skill_matched
        if r.sticky_agent_id in absent_agent_ids and r.has_internal_note()
    ]
    # Mark as from absent agent
    for r in cat3:
        r.from_absent_agent = True
    cmo_requests.extend(cat3)
    
    # Category 4: Unassigned + new + (no followup date OR followup date passed)
    cat4 = [
        r for r in skill_matched
        if (r.sticky_agent_id is None 
            and r.workorder_status == 'new'
            and r.is_followup_due(current_time))
    ]
    cmo_requests.extend(cat4)
    
    return cmo_requests


def apply_priority_levels(requests: List[Request]) -> List[Request]:
    """
    Apply 5-level priority system and return ALL requests from highest non-empty level.
    
    This bucketing is applied to both followup and CMO requests after initial filtering.
    
    Priority levels (highest to lowest):
    1. (is_winback OR is_atl_rf) AND is_escalated
    2. (is_winback OR is_atl_rf) AND NOT is_escalated
    3. has_sla AND is_escalated
    4. NOT has_sla AND is_escalated
    5. NOT is_escalated (commons)
    
    Args:
        requests: List of requests to prioritize
        
    Returns:
        List of ALL requests from highest non-empty priority level, or empty list
    """
    if not requests:
        return []
    
    # Priority 1: (winback OR atl_rf) AND escalated
    priority1 = [
        r for r in requests
        if (r.is_winback or r.is_atl_rf) and r.is_escalated
    ]
    if priority1:
        return priority1  # Return ALL from priority 1
    
    # Priority 2: (winback OR atl_rf) AND NOT escalated
    priority2 = [
        r for r in requests
        if (r.is_winback or r.is_atl_rf) and not r.is_escalated
    ]
    if priority2:
        return priority2  # Return ALL from priority 2
    
    # Priority 3: has_sla AND escalated
    priority3 = [
        r for r in requests
        if r.has_sla and r.is_escalated
    ]
    if priority3:
        return priority3  # Return ALL from priority 3
    
    # Priority 4: NOT has_sla AND escalated
    priority4 = [
        r for r in requests
        if not r.has_sla and r.is_escalated
    ]
    if priority4:
        return priority4  # Return ALL from priority 4
    
    # Priority 5: NOT escalated (commons)
    priority5 = [
        r for r in requests
        if not r.is_escalated
    ]
    if priority5:
        return priority5  # Return ALL from priority 5
    
    return []


def filter_production_requests(
    pool: RequestPool,
    agent: Agent,
    current_time: datetime,
    absent_agent_ids: Set[str],
    routing_config: RoutingConfig
) -> List[Request]:
    """
    Filter and return ALL eligible requests for an available agent.
    
    This implements the complete FILTERING algorithm (not final prioritization).
    The returned requests will be passed to routing.py for scoring-based selection.
    
    The agent is assumed to be available and actively looking for work.
    
    Mode A (Follow-up Time + Agent in Pilot):
        PRIMARY: Follow-up requests (4-bucket priority) → 5-level priority
        FALLBACK: CMO requests (all 4 categories) → 5-level priority
        
        Agent MUST work on their own followups first before taking CMO work.
    
    Mode B (Outside Follow-up Time OR Agent Not in Pilot):
        PRIMARY: CMO requests (all 4 categories) → 5-level priority
        FALLBACK: Follow-up requests (4-bucket priority) → 5-level priority (if pilot)
        
        Agent works on CMO requests first, then followups if pilot enabled.
    
    Args:
        pool: RequestPool to search
        agent: Agent requesting work (assumed available)
        current_time: Current simulation time
        absent_agent_ids: Set of currently absent agent IDs
        routing_config: Routing configuration
        
    Returns:
        List of ALL eligible requests from highest priority level, or empty list
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
        # PRIMARY: Try follow-up requests first (returns all from highest bucket)
        followup_requests = filter_followup_requests(pool, agent, current_time)
        if followup_requests:
            # Mark all as follow-up
            for r in followup_requests:
                r.is_followup = True
            # Apply 5-level priority and return ALL from highest level
            return apply_priority_levels(followup_requests)
        
        # FALLBACK: Collect all CMO requests and apply 5-level priority
        cmo_requests = filter_cmo_requests(pool, agent, current_time, absent_agent_ids)
        if cmo_requests:
            # Mark all as not follow-up
            for r in cmo_requests:
                r.is_followup = False
            # Apply 5-level priority and return ALL from highest level
            return apply_priority_levels(cmo_requests)
        
        return []
    
    # Mode B: Outside follow-up time OR pilot disabled
    else:
        # PRIMARY: Collect all CMO requests and apply 5-level priority
        cmo_requests = filter_cmo_requests(pool, agent, current_time, absent_agent_ids)
        if cmo_requests:
            # Mark all as not follow-up
            for r in cmo_requests:
                r.is_followup = False
            # Apply 5-level priority and return ALL from highest level
            return apply_priority_levels(cmo_requests)
        
        # FALLBACK: Try follow-up requests (only if pilot enabled)
        if pilot_enabled:
            followup_requests = filter_followup_requests(pool, agent, current_time)
            if followup_requests:
                # Mark all as follow-up
                for r in followup_requests:
                    r.is_followup = True
                # Apply 5-level priority and return ALL from highest level
                return apply_priority_levels(followup_requests)
        
        return []