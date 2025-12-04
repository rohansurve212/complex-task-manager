"""
Routing logic for STM Routing Simulator v3.0.

This module implements the core routing algorithm that selects the optimal
request to assign to an available agent from a filtered set of requests.

The routing process:
1. Receives filtered requests from production_filtering.py
2. Calculates priority scores based on request characteristics
3. Applies tie-breaking logic
4. Returns the single highest-priority request

Scoring rules (matching production):
- CMO requests: (age_minutes / foc_target) - older + shorter FOC = higher
- Followup requests: age_days from ECD or order_date - older = higher
- Tie-breaking: For followups, earliest order_date wins
"""

from typing import List, Optional
from datetime import datetime
from models.request import Request


# Constants
MINUTES_IN_A_DAY = 1440.0
DEFAULT_FOC_TARGET = 11520.0  # Default FOC in minutes (8 days)


def calculate_cmo_priority_score(request: Request, current_time: datetime) -> float:
    """
    Calculate priority score for a CMO (non-followup) request.
    
    Production logic from priority_score_new():
    - Base score = age of request in minutes
    - Normalize by FOC target to prioritize urgent requests
    - Formula: score = age_minutes / foc_target
    
    This means:
    - Older requests get higher scores (more minutes elapsed)
    - Shorter FOC targets boost the score (dividing by smaller number)
    
    Args:
        request: The CMO request to score
        current_time: Current simulation time
        
    Returns:
        float: Priority score for the request
        
    Example:
        >>> # Request that's 2 days old with 7-day FOC
        >>> score = calculate_cmo_priority_score(request, current_time)
        >>> # score = 2880 minutes / 10080 minutes = 0.286
    """
    # Calculate age in minutes
    age_minutes = (current_time - request.order_date).total_seconds() / 60.0
    
    # Get FOC target in minutes (convert days to minutes)
    if request.foc_target and request.foc_target > 0:
        foc_minutes = request.foc_target * MINUTES_IN_A_DAY
    else:
        foc_minutes = DEFAULT_FOC_TARGET
    
    # Calculate score: older requests and shorter FOC targets = higher score
    score = age_minutes / foc_minutes
    
    return score


def calculate_followup_priority_score(request: Request, current_time: datetime) -> float:
    """
    Calculate priority score for a followup (self-assigned) request.
    
    Production logic from priority_score_followup():
    - Use expectedCompletionDate if available, otherwise requestOrderDate
    - Score = time difference in days
    - Requests past their due date get higher scores
    
    Args:
        request: The followup request to score
        current_time: Current simulation time
        
    Returns:
        float: Priority score in days
        
    Example:
        >>> # Request with ECD 3 days ago
        >>> score = calculate_followup_priority_score(request, current_time)
        >>> # score = 3.0 days (past due)
        >>>
        >>> # Request with ECD 2 days from now
        >>> score = calculate_followup_priority_score(request, current_time)
        >>> # score = -2.0 days (not yet due)
    """
    # Check if request has expected completion date
    if request.workorder_expected_completion_date:
        reference_date = request.workorder_expected_completion_date
    else:
        reference_date = request.order_date
    
    # Calculate time difference in days
    age_days = (current_time - reference_date).total_seconds() / (60.0 * MINUTES_IN_A_DAY)
    
    return age_days


def route_request_to_agent(
    filtered_requests: List[Request],
    current_time: datetime
) -> Optional[Request]:
    """
    Select the highest-priority request from filtered requests using production routing logic.
    
    This implements the top_priority_request() logic from production:
    1. Calculate scores based on request type (followup vs CMO)
    2. Find the request(s) with highest score
    3. Apply tie-breaking: for followups, earliest order_date wins
    4. Return the selected request
    
    Args:
        filtered_requests: List of requests after production filtering
        current_time: Current simulation time
        
    Returns:
        Optional[Request]: The selected request, or None if list is empty
        
    Example:
        >>> # Get filtered requests from production filtering
        >>> filtered = filter_production_requests(pool, agent, current_time, absent_agents, config)
        >>> 
        >>> # Route to find best request
        >>> selected = route_request_to_agent(filtered, current_time)
        >>> 
        >>> if selected:
        >>>     pool.assign_request_to_agent(selected.request_id, agent.agent_id, current_time)
    """
    # Handle empty list
    if not filtered_requests:
        return None
    
    # Handle single request (trivial case)
    if len(filtered_requests) == 1:
        return filtered_requests[0]
    
    # Check if we have any followup requests
    has_followups = any(getattr(r, 'is_followup', False) for r in filtered_requests)
    
    # Calculate scores for each request
    scored_requests = []
    for request in filtered_requests:
        if has_followups and getattr(request, 'is_followup', False):
            # Use followup scoring
            score = calculate_followup_priority_score(request, current_time)
        else:
            # Use CMO scoring
            score = calculate_cmo_priority_score(request, current_time)
        
        scored_requests.append((request, score))
    
    # Find maximum score
    max_score = max(score for _, score in scored_requests)
    
    # Get all requests with maximum score
    top_requests = [req for req, score in scored_requests if score == max_score]
    
    # If only one request has max score, return it
    if len(top_requests) == 1:
        return top_requests[0]
    
    # Tie-breaking: for followups, pick earliest order_date
    # For CMO, just return first (production uses idxmax which picks first on tie)
    if has_followups:
        # Return the request with earliest order_date
        return min(top_requests, key=lambda r: r.order_date)
    else:
        # For CMO, just return first (matches production idxmax behavior)
        return top_requests[0]