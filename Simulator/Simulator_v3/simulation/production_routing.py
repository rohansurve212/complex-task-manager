"""
Production Routing Logic

Implements filter_static() from search_requests_utils.py

Routing strategy depends on time of day and pilot program setting:
- During follow-up windows (if pilot enabled): Follow-up requests first, CMO fallback
- Outside follow-up windows: CMO requests first, Follow-up fallback (if pilot enabled)
"""

from typing import List, Optional
from datetime import datetime
import logging

from models import Request, RequestState, Agent, RequestPool
from config.scenario_config import RoutingConfig

logger = logging.getLogger("simulation")


def followup_priority_filter(
    pool: RequestPool,
    agent: Agent,
    current_time: datetime
) -> Optional[Request]:
    """
    Get highest priority follow-up request for this agent.
    
    Priority buckets (matching production):
    1. Self-assigned + (Customer update OR Internal note) + Has ECD
    2. Self-assigned + (Customer update OR Internal note) + NO ECD
    3. Self-assigned + NO updates + Has ECD + followUpDate passed
    4. Self-assigned + NO updates + NO ECD + followUpDate passed
    
    Args:
        pool: RequestPool to search
        agent: Agent requesting work
        current_time: Current simulation time
        
    Returns:
        Highest priority follow-up request, or None
    """
    # Get all self-assigned followups
    all_followups = pool.filter_requests(
        sticky_agent_id=agent.agent_id,
        state=RequestState.NEW,
        custom_filter=lambda r: r.workorder_followup_date is not None
    )
    
    if not all_followups:
        return None
    
    # Bucket 1: Customer update/Internal note + Has ECD
    bucket_1 = [
        r for r in all_followups
        if r.has_customer_update_or_internal_note() and r.has_expected_completion_date()
    ]
    
    # Bucket 2: Customer update/Internal note + NO ECD
    bucket_2 = [
        r for r in all_followups
        if r.has_customer_update_or_internal_note() and not r.has_expected_completion_date()
    ]
    
    # Bucket 3: NO updates + Has ECD + followUpDate passed
    bucket_3 = [
        r for r in all_followups
        if (not r.has_customer_update_or_internal_note() and 
            r.has_expected_completion_date() and
            r.is_followup_due(current_time))
    ]
    
    # Bucket 4: NO updates + NO ECD + followUpDate passed
    bucket_4 = [
        r for r in all_followups
        if (not r.has_customer_update_or_internal_note() and 
            not r.has_expected_completion_date() and
            r.is_followup_due(current_time))
    ]
    
    # Return first non-empty bucket
    for bucket_num, bucket in enumerate([bucket_1, bucket_2, bucket_3, bucket_4], 1):
        if bucket:
            # Sort by priority within bucket
            sorted_bucket = pool.sort_by_priority(bucket, current_time, descending=True)
            logger.debug(f"Agent {agent.agent_id}: Follow-up Bucket {bucket_num} - {len(bucket)} requests")
            return sorted_bucket[0]
    
    return None


def get_cmo_request(
    pool: RequestPool,
    agent: Agent,
    current_time: datetime,
    absent_agent_ids: List[str]
) -> Optional[Request]:
    """
    Get highest priority CMO (Common Mailbox Operations) request.
    
    CMO Priority (matching production):
    1. Unassigned + status='customerreplied'
    2. Absent agent + status='customerreplied'
    3. Absent agent + has 'NEW_INTERNAL_NOTE' tag
    4. Unassigned + status='new' + followUpDate passed
    
    Args:
        pool: RequestPool to search
        agent: Agent requesting work
        current_time: Current simulation time
        absent_agent_ids: List of absent agent IDs
        
    Returns:
        Highest priority CMO request, or None
    """
    # Get available requests for agent's skills
    available = []
    for skill in agent.skillsets:
        skill_requests = pool.get_available_requests(skill_id=skill)
        available.extend(skill_requests)
    
    if not available:
        return None
    
    # Priority 1: Unassigned + status='customerreplied'
    priority_1 = [
        r for r in available
        if r.sticky_agent_id is None and r.workorder_status == 'customerreplied'
    ]
    
    # Priority 2: Absent agent + status='customerreplied'
    priority_2 = [
        r for r in available
        if (r.sticky_agent_id in absent_agent_ids and 
            r.workorder_status == 'customerreplied' and
            not (r.workorder_status != 'orderconfirmed' and r.is_locked()))
    ]
    
    # Priority 3: Absent agent + has 'NEW_INTERNAL_NOTE'
    priority_3 = [
        r for r in available
        if (r.sticky_agent_id in absent_agent_ids and 
            r.workorder_status != 'customerreplied' and
            r.has_internal_note() and
            not (r.workorder_status != 'orderconfirmed' and r.is_locked()))
    ]
    
    # Priority 4: Unassigned + status='new' + followUpDate passed
    priority_4 = [
        r for r in available
        if (r.sticky_agent_id is None and 
            r.workorder_status == 'new' and
            r.is_followup_due(current_time))
    ]
    
    # Return first non-empty priority level
    for priority_num, priority_list in enumerate([priority_1, priority_2, priority_3, priority_4], 1):
        if priority_list:
            # Sort by priority score within priority level
            sorted_priority = pool.sort_by_priority(priority_list, current_time, descending=True)
            logger.debug(f"Agent {agent.agent_id}: CMO Priority {priority_num} - {len(priority_list)} requests")
            return sorted_priority[0]
    
    return None


def get_production_routed_request(
    pool: RequestPool,
    agent: Agent,
    current_time: datetime,
    absent_agent_ids: List[str],
    routing_config: RoutingConfig
) -> Optional[Request]:
    """
    Get next request using production routing logic.
    
    Implements filter_static() from search_requests_utils.py
    
    Routing strategy:
    - During follow-up time (if pilot enabled):
      PRIMARY: Follow-up requests
      FALLBACK: CMO requests
      
    - During non-follow-up time:
      PRIMARY: CMO requests
      FALLBACK (if pilot enabled): Follow-up requests
    
    Args:
        pool: RequestPool to search
        agent: Agent requesting work
        current_time: Current simulation time
        absent_agent_ids: List of absent agent IDs
        routing_config: Routing configuration
        
    Returns:
        Next request to assign, or None
    """
    is_followup_time = agent.is_in_followup_window(
        current_time,
        window_1_start=routing_config.followup_window_1_start,
        window_1_end=routing_config.followup_window_1_end,
        window_2_start=routing_config.followup_window_2_start,
        window_2_end=routing_config.followup_window_2_end
    )
    pilot_enabled = routing_config.pilot_program_enabled
    
    logger.debug(f"Agent {agent.agent_id}: followup_time={is_followup_time}, pilot={pilot_enabled}")
    
    # DURING FOLLOW-UP TIME (if pilot enabled)
    if is_followup_time and pilot_enabled:
        # PRIMARY: Follow-up requests
        followup_request = followup_priority_filter(pool, agent, current_time)
        if followup_request:
            followup_request.is_followup = True
            logger.info(f"Agent {agent.agent_id}: Assigned follow-up {followup_request.request_id}")
            return followup_request
        
        # FALLBACK: CMO requests
        logger.debug(f"Agent {agent.agent_id}: No follow-ups, trying CMO")
        cmo_request = get_cmo_request(pool, agent, current_time, absent_agent_ids)
        if cmo_request:
            cmo_request.is_followup = False
            logger.info(f"Agent {agent.agent_id}: Assigned CMO {cmo_request.request_id}")
            return cmo_request
    
    # DURING NON-FOLLOW-UP TIME
    else:
        # PRIMARY: CMO requests
        cmo_request = get_cmo_request(pool, agent, current_time, absent_agent_ids)
        if cmo_request:
            cmo_request.is_followup = False
            logger.info(f"Agent {agent.agent_id}: Assigned CMO {cmo_request.request_id}")
            return cmo_request
        
        # FALLBACK (if pilot enabled): Follow-up requests
        if pilot_enabled:
            logger.debug(f"Agent {agent.agent_id}: No CMO, trying follow-ups")
            followup_request = followup_priority_filter(pool, agent, current_time)
            if followup_request:
                followup_request.is_followup = True
                logger.info(f"Agent {agent.agent_id}: Assigned follow-up {followup_request.request_id}")
                return followup_request
    
    logger.debug(f"Agent {agent.agent_id}: No requests available")
    
    return None