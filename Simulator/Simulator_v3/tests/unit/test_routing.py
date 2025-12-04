"""
Unit tests for routing logic.

Tests cover:
- CMO priority score calculation
- Followup priority score calculation
- Main routing function with various scenarios
- Tie-breaking logic
- Edge cases (empty list, single request)
"""

import pytest
from datetime import datetime, timezone, timedelta
from models.request import Request
from simulation.routing import (
    calculate_cmo_priority_score,
    calculate_followup_priority_score,
    route_request_to_agent,
    MINUTES_IN_A_DAY,
    DEFAULT_FOC_TARGET
)


@pytest.fixture
def current_time():
    """Fixture providing current time for tests."""
    return datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


def create_request(
    request_id='REQ001',
    skill_id='SkillA',
    order_date=None,
    foc_target=7.0,  # days
    workorder_expected_completion_date=None,
    is_followup=False
):
    """Helper to create a request with minimal required fields."""
    if order_date is None:
        order_date = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    
    req = Request(
        request_id=request_id,
        external_id=f'EXT_{request_id}',
        skill_id=skill_id,
        request_source='web',
        product='ProductA',
        service_region='Ontario',
        request_type='service',
        order_date=order_date,
        foc_target=foc_target,
        workorder_expected_completion_date=workorder_expected_completion_date
    )
    
    # Mark as followup if specified
    if is_followup:
        req.is_followup = True
    
    return req


# ============================================================================
# Test CMO Priority Score Calculation
# ============================================================================

def test_cmo_score_basic_calculation(current_time):
    """Test basic CMO score calculation: age_minutes / foc_minutes."""
    # Request that's 2 days old with 7-day FOC
    order_date = current_time - timedelta(days=2)
    req = create_request(
        request_id='REQ001',
        order_date=order_date,
        foc_target=7.0
    )
    
    score = calculate_cmo_priority_score(req, current_time)
    
    # Expected: 2 days = 2880 minutes, 7 days = 10080 minutes
    # Score = 2880 / 10080 = 0.2857...
    expected = 2880.0 / 10080.0
    assert abs(score - expected) < 0.0001


def test_cmo_score_older_request_higher_score(current_time):
    """Test that older requests get higher CMO scores."""
    # 1-day-old request
    req1 = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=1),
        foc_target=7.0
    )
    
    # 5-day-old request
    req2 = create_request(
        request_id='REQ002',
        order_date=current_time - timedelta(days=5),
        foc_target=7.0
    )
    
    score1 = calculate_cmo_priority_score(req1, current_time)
    score2 = calculate_cmo_priority_score(req2, current_time)
    
    assert score2 > score1  # Older request has higher score


def test_cmo_score_shorter_foc_higher_score(current_time):
    """Test that shorter FOC targets boost CMO scores."""
    order_date = current_time - timedelta(days=2)
    
    # Request with 7-day FOC
    req1 = create_request(
        request_id='REQ001',
        order_date=order_date,
        foc_target=7.0
    )
    
    # Request with 3-day FOC (more urgent)
    req2 = create_request(
        request_id='REQ002',
        order_date=order_date,
        foc_target=3.0
    )
    
    score1 = calculate_cmo_priority_score(req1, current_time)
    score2 = calculate_cmo_priority_score(req2, current_time)
    
    assert score2 > score1  # Shorter FOC has higher score


def test_cmo_score_zero_foc_uses_default(current_time):
    """Test that zero/None FOC uses default FOC target."""
    order_date = current_time - timedelta(days=2)
    
    # Request with zero FOC
    req = create_request(
        request_id='REQ001',
        order_date=order_date,
        foc_target=0.0
    )
    
    score = calculate_cmo_priority_score(req, current_time)
    
    # Should use DEFAULT_FOC_TARGET (7 days = 10080 minutes)
    expected = 2880.0 / DEFAULT_FOC_TARGET
    assert abs(score - expected) < 0.0001


def test_cmo_score_none_foc_uses_default(current_time):
    """Test that None FOC uses default FOC target."""
    order_date = current_time - timedelta(days=2)
    
    # Request with None FOC
    req = create_request(
        request_id='REQ001',
        order_date=order_date,
        foc_target=None
    )
    
    score = calculate_cmo_priority_score(req, current_time)
    
    # Should use DEFAULT_FOC_TARGET
    expected = 2880.0 / DEFAULT_FOC_TARGET
    assert abs(score - expected) < 0.0001


# ============================================================================
# Test Followup Priority Score Calculation
# ============================================================================

def test_followup_score_with_ecd(current_time):
    """Test followup score uses ECD when available."""
    # Request with ECD 3 days ago (past due)
    ecd = current_time - timedelta(days=3)
    order_date = current_time - timedelta(days=10)
    
    req = create_request(
        request_id='REQ001',
        order_date=order_date,
        workorder_expected_completion_date=ecd,
        is_followup=True
    )
    
    score = calculate_followup_priority_score(req, current_time)
    
    # Expected: 3 days past ECD
    assert abs(score - 3.0) < 0.0001


def test_followup_score_without_ecd_uses_order_date(current_time):
    """Test followup score uses order_date when ECD not available."""
    # Request without ECD, 5 days old
    order_date = current_time - timedelta(days=5)
    
    req = create_request(
        request_id='REQ001',
        order_date=order_date,
        workorder_expected_completion_date=None,
        is_followup=True
    )
    
    score = calculate_followup_priority_score(req, current_time)
    
    # Expected: 5 days since order
    assert abs(score - 5.0) < 0.0001


def test_followup_score_past_due_positive(current_time):
    """Test that past-due followups have positive scores."""
    # ECD was 2 days ago
    ecd = current_time - timedelta(days=2)
    
    req = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=5),
        workorder_expected_completion_date=ecd,
        is_followup=True
    )
    
    score = calculate_followup_priority_score(req, current_time)
    
    assert score > 0  # Past due = positive score


def test_followup_score_not_yet_due_negative(current_time):
    """Test that not-yet-due followups have negative scores."""
    # ECD is 2 days in the future
    ecd = current_time + timedelta(days=2)
    
    req = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=3),
        workorder_expected_completion_date=ecd,
        is_followup=True
    )
    
    score = calculate_followup_priority_score(req, current_time)
    
    assert score < 0  # Not yet due = negative score


def test_followup_score_more_overdue_higher_score(current_time):
    """Test that more overdue followups get higher scores."""
    # Request 1: 1 day past ECD
    req1 = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=5),
        workorder_expected_completion_date=current_time - timedelta(days=1),
        is_followup=True
    )
    
    # Request 2: 5 days past ECD
    req2 = create_request(
        request_id='REQ002',
        order_date=current_time - timedelta(days=10),
        workorder_expected_completion_date=current_time - timedelta(days=5),
        is_followup=True
    )
    
    score1 = calculate_followup_priority_score(req1, current_time)
    score2 = calculate_followup_priority_score(req2, current_time)
    
    assert score2 > score1  # More overdue = higher score


# ============================================================================
# Test Main Routing Function - Edge Cases
# ============================================================================

def test_routing_empty_list(current_time):
    """Test that routing returns None for empty list."""
    result = route_request_to_agent([], current_time)
    assert result is None


def test_routing_single_request(current_time):
    """Test that routing returns the only request (trivial case)."""
    req = create_request(request_id='REQ001', order_date=current_time)
    
    result = route_request_to_agent([req], current_time)
    
    assert result is not None
    assert result.request_id == 'REQ001'


# ============================================================================
# Test Main Routing Function - CMO Requests
# ============================================================================

def test_routing_multiple_cmo_selects_highest_score(current_time):
    """Test that routing selects CMO request with highest score."""
    # Request 1: 1 day old, 7-day FOC (score = 1440/10080 = 0.143)
    req1 = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=1),
        foc_target=7.0
    )
    
    # Request 2: 5 days old, 7-day FOC (score = 7200/10080 = 0.714) <- HIGHEST
    req2 = create_request(
        request_id='REQ002',
        order_date=current_time - timedelta(days=5),
        foc_target=7.0
    )
    
    # Request 3: 3 days old, 7-day FOC (score = 4320/10080 = 0.429)
    req3 = create_request(
        request_id='REQ003',
        order_date=current_time - timedelta(days=3),
        foc_target=7.0
    )
    
    result = route_request_to_agent([req1, req2, req3], current_time)
    
    assert result.request_id == 'REQ002'  # Oldest request wins


def test_routing_cmo_considers_foc_target(current_time):
    """Test that CMO routing considers FOC urgency."""
    order_date = current_time - timedelta(days=2)
    
    # Request 1: 2 days old, 7-day FOC (score = 2880/10080 = 0.286)
    req1 = create_request(
        request_id='REQ001',
        order_date=order_date,
        foc_target=7.0
    )
    
    # Request 2: 2 days old, 3-day FOC (score = 2880/4320 = 0.667) <- HIGHEST
    req2 = create_request(
        request_id='REQ002',
        order_date=order_date,
        foc_target=3.0
    )
    
    result = route_request_to_agent([req1, req2], current_time)
    
    assert result.request_id == 'REQ002'  # Shorter FOC wins


def test_routing_cmo_tie_returns_first(current_time):
    """Test that CMO tie returns first request (pandas idxmax behavior)."""
    order_date = current_time - timedelta(days=2)
    
    # Both requests have identical scores
    req1 = create_request(
        request_id='REQ001',
        order_date=order_date,
        foc_target=7.0
    )
    req2 = create_request(
        request_id='REQ002',
        order_date=order_date,
        foc_target=7.0
    )
    
    result = route_request_to_agent([req1, req2], current_time)
    
    # Should return first request on tie
    assert result.request_id == 'REQ001'


# ============================================================================
# Test Main Routing Function - Followup Requests
# ============================================================================

def test_routing_followup_selects_most_overdue(current_time):
    """Test that routing selects most overdue followup request."""
    # Request 1: 1 day past ECD
    req1 = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=5),
        workorder_expected_completion_date=current_time - timedelta(days=1),
        is_followup=True
    )
    
    # Request 2: 5 days past ECD <- HIGHEST
    req2 = create_request(
        request_id='REQ002',
        order_date=current_time - timedelta(days=10),
        workorder_expected_completion_date=current_time - timedelta(days=5),
        is_followup=True
    )
    
    # Request 3: 3 days past ECD
    req3 = create_request(
        request_id='REQ003',
        order_date=current_time - timedelta(days=8),
        workorder_expected_completion_date=current_time - timedelta(days=3),
        is_followup=True
    )
    
    result = route_request_to_agent([req1, req2, req3], current_time)
    
    assert result.request_id == 'REQ002'  # Most overdue wins


def test_routing_followup_tie_earliest_order_date_wins(current_time):
    """Test that followup ties are broken by earliest order_date."""
    # Both requests have same ECD (same score)
    ecd = current_time - timedelta(days=2)
    
    # Request 1: Ordered 10 days ago <- EARLIEST order_date
    req1 = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=10),
        workorder_expected_completion_date=ecd,
        is_followup=True
    )
    
    # Request 2: Ordered 7 days ago
    req2 = create_request(
        request_id='REQ002',
        order_date=current_time - timedelta(days=7),
        workorder_expected_completion_date=ecd,
        is_followup=True
    )
    
    # Request 3: Ordered 5 days ago
    req3 = create_request(
        request_id='REQ003',
        order_date=current_time - timedelta(days=5),
        workorder_expected_completion_date=ecd,
        is_followup=True
    )
    
    result = route_request_to_agent([req1, req2, req3], current_time)
    
    # Tie-breaking: earliest order_date wins
    assert result.request_id == 'REQ001'


def test_routing_followup_without_ecd_uses_order_date(current_time):
    """Test that followup without ECD uses order_date for scoring."""
    # Request 1: 3 days old, no ECD
    req1 = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=3),
        workorder_expected_completion_date=None,
        is_followup=True
    )
    
    # Request 2: 7 days old, no ECD <- HIGHEST
    req2 = create_request(
        request_id='REQ002',
        order_date=current_time - timedelta(days=7),
        workorder_expected_completion_date=None,
        is_followup=True
    )
    
    result = route_request_to_agent([req1, req2], current_time)
    
    assert result.request_id == 'REQ002'  # Older order_date wins


# ============================================================================
# Test Main Routing Function - Mixed Scenarios
# ============================================================================

def test_routing_mixed_followup_and_cmo_uses_followup_scoring(current_time):
    """Test that when followups are present, followup scoring is used for all."""
    # CMO request: would have high score with CMO logic
    cmo_req = create_request(
        request_id='CMO001',
        order_date=current_time - timedelta(days=5),
        foc_target=3.0,
        is_followup=False
    )
    
    # Followup request: 2 days past ECD
    followup_req = create_request(
        request_id='FOLLOWUP001',
        order_date=current_time - timedelta(days=10),
        workorder_expected_completion_date=current_time - timedelta(days=2),
        is_followup=True
    )
    
    result = route_request_to_agent([cmo_req, followup_req], current_time)
    
    # When followups are present, followup scoring is used
    # The followup with highest score should be selected
    assert result.request_id == 'FOLLOWUP001'


def test_routing_preserves_request_attributes(current_time):
    """Test that routing preserves request attributes and doesn't modify original."""
    req = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=2),
        foc_target=7.0
    )
    
    original_order_date = req.order_date
    original_foc = req.foc_target
    
    result = route_request_to_agent([req], current_time)
    
    # Verify attributes unchanged
    assert result.order_date == original_order_date
    assert result.foc_target == original_foc


# ============================================================================
# Test Production Accuracy
# ============================================================================

def test_routing_matches_production_cmo_formula(current_time):
    """Test that CMO scoring matches production formula exactly."""
    # Production: score = age_minutes / foc_minutes
    # 3 days old, 7-day FOC
    req = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=3),
        foc_target=7.0
    )
    
    score = calculate_cmo_priority_score(req, current_time)
    
    # Production calculation
    age_minutes = 3.0 * MINUTES_IN_A_DAY  # 4320 minutes
    foc_minutes = 7.0 * MINUTES_IN_A_DAY  # 10080 minutes
    expected_score = age_minutes / foc_minutes
    
    assert abs(score - expected_score) < 0.0001


def test_routing_matches_production_followup_formula(current_time):
    """Test that followup scoring matches production formula exactly."""
    # Production: score = (current_time - ECD) in days
    ecd = current_time - timedelta(days=4, hours=12)  # 4.5 days ago
    
    req = create_request(
        request_id='REQ001',
        order_date=current_time - timedelta(days=10),
        workorder_expected_completion_date=ecd,
        is_followup=True
    )
    
    score = calculate_followup_priority_score(req, current_time)
    
    # Production calculation: 4.5 days
    expected_score = 4.5
    
    assert abs(score - expected_score) < 0.01  # Allow small floating point diff