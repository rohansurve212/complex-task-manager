"""
Unit tests for RequestPool class.

Run with: pytest tests/unit/test_request_pool.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta

# Import components to test
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.request import Request, RequestState
from models.request_pool import RequestPool


# ============================================================================
# HELPER FUNCTIONS FOR TESTS
# ============================================================================

def create_test_request(
    request_id: str,
    skill_id: str = "internet",
    order_date: datetime = None,
    foc_target: float = 8.0,
    has_sla: bool = False,
    is_escalated: bool = False,
    is_winback: bool = False
) -> Request:
    """Helper function to create test requests"""
    if order_date is None:
        order_date = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    return Request(
        request_id=request_id,
        external_id=f"EXT_{request_id}",
        skill_id=skill_id,
        request_source="bcom",
        product=skill_id,
        service_region="ontario",
        request_type="new",
        order_date=order_date,
        foc_target=foc_target,
        has_sla=has_sla,
        is_escalated=is_escalated,
        is_winback=is_winback
    )


# ============================================================================
# TEST: Pool Creation and Basic Operations
# ============================================================================

class TestPoolCreation:
    """Test suite for pool initialization and basic operations"""
    
    def test_create_empty_pool(self):
        """Test creating an empty pool"""
        pool = RequestPool()
        
        assert pool.size() == 0
        assert pool.is_empty()
        assert len(pool) == 0
    
    def test_add_single_request(self):
        """Test adding a single request"""
        pool = RequestPool()
        request = create_test_request("REQ_001")
        
        added = pool.add_request(request)
        
        assert added is True
        assert pool.size() == 1
        assert not pool.is_empty()
        assert "REQ_001" in pool
    
    def test_add_duplicate_request(self):
        """Test that adding duplicate request returns False"""
        pool = RequestPool()
        request = create_test_request("REQ_001")
        
        added1 = pool.add_request(request)
        added2 = pool.add_request(request)
        
        assert added1 is True
        assert added2 is False
        assert pool.size() == 1
    
    def test_add_multiple_requests(self):
        """Test adding multiple requests"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001"),
            create_test_request("REQ_002"),
            create_test_request("REQ_003")
        ]
        
        count = pool.add_requests(requests)
        
        assert count == 3
        assert pool.size() == 3
    
    def test_add_requests_with_duplicates(self):
        """Test adding requests when some are duplicates"""
        pool = RequestPool()
        request1 = create_test_request("REQ_001")
        pool.add_request(request1)
        
        requests = [
            create_test_request("REQ_001"),  # Duplicate
            create_test_request("REQ_002"),  # New
            create_test_request("REQ_003")   # New
        ]
        
        count = pool.add_requests(requests)
        
        assert count == 2  # Only 2 new requests added
        assert pool.size() == 3
    
    def test_get_request(self):
        """Test getting a request by ID"""
        pool = RequestPool()
        request = create_test_request("REQ_001", skill_id="internet")
        pool.add_request(request)
        
        retrieved = pool.get_request("REQ_001")
        
        assert retrieved is not None
        assert retrieved.request_id == "REQ_001"
        assert retrieved.skill_id == "internet"
    
    def test_get_nonexistent_request(self):
        """Test getting request that doesn't exist"""
        pool = RequestPool()
        
        retrieved = pool.get_request("REQ_999")
        
        assert retrieved is None
    
    def test_contains(self):
        """Test checking if pool contains request"""
        pool = RequestPool()
        request = create_test_request("REQ_001")
        pool.add_request(request)
        
        assert pool.contains("REQ_001")
        assert not pool.contains("REQ_999")
        
        # Test 'in' operator
        assert "REQ_001" in pool
        assert "REQ_999" not in pool
    
    def test_remove_request(self):
        """Test removing a request"""
        pool = RequestPool()
        request = create_test_request("REQ_001")
        pool.add_request(request)
        
        removed = pool.remove_request("REQ_001")
        
        assert removed is not None
        assert removed.request_id == "REQ_001"
        assert pool.size() == 0
        assert "REQ_001" not in pool
    
    def test_remove_nonexistent_request(self):
        """Test removing request that doesn't exist"""
        pool = RequestPool()
        
        removed = pool.remove_request("REQ_999")
        
        assert removed is None
    
    def test_clear_pool(self):
        """Test clearing all requests"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001"),
            create_test_request("REQ_002"),
            create_test_request("REQ_003")
        ]
        pool.add_requests(requests)
        
        count = pool.clear()
        
        assert count == 3
        assert pool.size() == 0
        assert pool.is_empty()


# ============================================================================
# TEST: Filtering Operations
# ============================================================================

class TestFiltering:
    """Test suite for filtering requests"""
    
    def test_get_all_requests(self):
        """Test getting all requests"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001", skill_id="internet"),
            create_test_request("REQ_002", skill_id="voice"),
            create_test_request("REQ_003", skill_id="tv")
        ]
        pool.add_requests(requests)
        
        all_requests = pool.get_all_requests()
        
        assert len(all_requests) == 3
    
    def test_get_requests_by_skill(self):
        """Test filtering by skill"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001", skill_id="internet"),
            create_test_request("REQ_002", skill_id="internet"),
            create_test_request("REQ_003", skill_id="voice"),
            create_test_request("REQ_004", skill_id="tv")
        ]
        pool.add_requests(requests)
        
        internet_requests = pool.get_requests_by_skill("internet")
        
        assert len(internet_requests) == 2
        assert all(r.skill_id == "internet" for r in internet_requests)
    
    def test_get_requests_by_nonexistent_skill(self):
        """Test filtering by skill that doesn't exist"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001", skill_id="internet")
        ]
        pool.add_requests(requests)
        
        phone_requests = pool.get_requests_by_skill("phone")
        
        assert len(phone_requests) == 0
    
    def test_get_requests_by_state(self):
        """Test filtering by state"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001"),
            create_test_request("REQ_002"),
            create_test_request("REQ_003")
        ]
        pool.add_requests(requests)
        
        # All should be NEW initially
        new_requests = pool.get_requests_by_state(RequestState.NEW)
        assert len(new_requests) == 3
        
        # Assign one request
        pool.assign_request_to_agent("REQ_001", "john.doe", datetime.now(timezone.utc))
        
        # Check states
        new_requests = pool.get_requests_by_state(RequestState.NEW)
        assigned_requests = pool.get_requests_by_state(RequestState.ASSIGNED)
        
        assert len(new_requests) == 2
        assert len(assigned_requests) == 1
    
    def test_get_available_requests_all(self):
        """Test getting all available requests"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001", skill_id="internet"),
            create_test_request("REQ_002", skill_id="voice"),
            create_test_request("REQ_003", skill_id="internet")
        ]
        pool.add_requests(requests)
        
        # Assign one
        pool.assign_request_to_agent("REQ_001", "john.doe", datetime.now(timezone.utc))
        
        available = pool.get_available_requests()
        
        assert len(available) == 2  # 2 unassigned
        assert all(r.state == RequestState.NEW for r in available)
    
    def test_get_available_requests_by_skill(self):
        """Test getting available requests for specific skill"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001", skill_id="internet"),
            create_test_request("REQ_002", skill_id="voice"),
            create_test_request("REQ_003", skill_id="internet")
        ]
        pool.add_requests(requests)
        
        # Assign one internet request
        pool.assign_request_to_agent("REQ_001", "john.doe", datetime.now(timezone.utc))
        
        available_internet = pool.get_available_requests(skill_id="internet")
        
        assert len(available_internet) == 1
        assert available_internet[0].request_id == "REQ_003"
    
    def test_filter_by_flags(self):
        """Test filtering by SLA, escalated, winback flags"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001", has_sla=True, is_escalated=False),
            create_test_request("REQ_002", has_sla=True, is_escalated=True),
            create_test_request("REQ_003", has_sla=False, is_escalated=False),
            create_test_request("REQ_004", is_winback=True)
        ]
        pool.add_requests(requests)
        
        # Filter by SLA
        sla_requests = pool.filter_requests(has_sla=True)
        assert len(sla_requests) == 2
        
        # Filter by escalated
        escalated = pool.filter_requests(is_escalated=True)
        assert len(escalated) == 1
        
        # Filter by winback
        winback = pool.filter_requests(is_winback=True)
        assert len(winback) == 1
        
        # Combine filters
        sla_escalated = pool.filter_requests(has_sla=True, is_escalated=True)
        assert len(sla_escalated) == 1
        assert sla_escalated[0].request_id == "REQ_002"
    
    def test_filter_by_age(self):
        """Test filtering by request age"""
        pool = RequestPool()
        
        # Create requests with different ages
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        requests = [
            create_test_request("REQ_001", order_date=base_time),  # 3 days old
            create_test_request("REQ_002", order_date=base_time + timedelta(days=1)),  # 2 days old
            create_test_request("REQ_003", order_date=base_time + timedelta(days=2))   # 1 day old
        ]
        pool.add_requests(requests)
        
        current_time = datetime(2024, 5, 4, 0, 0, 0, tzinfo=timezone.utc)
        
        # Filter: older than 2 days
        old_requests = pool.filter_requests(
            min_age_days=2.0,
            current_time=current_time
        )
        assert len(old_requests) == 2
        
        # Filter: younger than 2 days
        young_requests = pool.filter_requests(
            max_age_days=2.0,
            current_time=current_time
        )
        assert len(young_requests) == 2
        
        # Filter: exactly in range
        mid_requests = pool.filter_requests(
            min_age_days=1.5,
            max_age_days=2.5,
            current_time=current_time
        )
        assert len(mid_requests) == 1
    
    def test_filter_with_custom_function(self):
        """Test filtering with custom filter function"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001", foc_target=5.0),
            create_test_request("REQ_002", foc_target=8.0),
            create_test_request("REQ_003", foc_target=10.0)
        ]
        pool.add_requests(requests)
        
        # Custom filter: FOC target > 7
        def short_foc(request):
            return request.foc_target > 7.0
        
        filtered = pool.filter_requests(custom_filter=short_foc)
        
        assert len(filtered) == 2
        assert all(r.foc_target > 7.0 for r in filtered)
    
    def test_filter_combined_criteria(self):
        """Test filtering with multiple criteria"""
        pool = RequestPool()
        
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        requests = [
            create_test_request("REQ_001", skill_id="internet", has_sla=True, 
                              is_escalated=True, order_date=base_time),
            create_test_request("REQ_002", skill_id="internet", has_sla=True,
                              is_escalated=False, order_date=base_time),
            create_test_request("REQ_003", skill_id="voice", has_sla=True,
                              is_escalated=True, order_date=base_time),
            create_test_request("REQ_004", skill_id="internet", has_sla=False,
                              is_escalated=True, order_date=base_time)
        ]
        pool.add_requests(requests)
        
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # Filter: internet + SLA + escalated
        filtered = pool.filter_requests(
            skill_id="internet",
            has_sla=True,
            is_escalated=True,
            current_time=current_time
        )
        
        assert len(filtered) == 1
        assert filtered[0].request_id == "REQ_001"


# ============================================================================
# TEST: Sorting Operations
# ============================================================================

class TestSorting:
    """Test suite for sorting requests"""
    
    def test_sort_by_priority(self):
        """Test sorting by priority score"""
        pool = RequestPool()
        
        # Create requests with different ages (same FOC target)
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        requests = [
            create_test_request("REQ_001", order_date=base_time),  # Oldest
            create_test_request("REQ_002", order_date=base_time + timedelta(hours=12)),
            create_test_request("REQ_003", order_date=base_time + timedelta(days=1))  # Newest
        ]
        pool.add_requests(requests)
        
        current_time = datetime(2024, 5, 3, 0, 0, 0, tzinfo=timezone.utc)
        
        # Sort descending (highest priority first)
        sorted_desc = pool.sort_by_priority(requests, current_time, descending=True)
        
        # Oldest should be first (highest priority)
        assert sorted_desc[0].request_id == "REQ_001"
        assert sorted_desc[-1].request_id == "REQ_003"
        
        # Sort ascending (lowest priority first)
        sorted_asc = pool.sort_by_priority(requests, current_time, descending=False)
        
        assert sorted_asc[0].request_id == "REQ_003"
        assert sorted_asc[-1].request_id == "REQ_001"
    
    def test_sort_by_priority_different_foc(self):
        """Test sorting by priority with different FOC targets"""
        pool = RequestPool()
        
        # Same age, different FOC targets
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        requests = [
            create_test_request("REQ_001", order_date=order_time, foc_target=8.0),
            create_test_request("REQ_002", order_date=order_time, foc_target=5.0),  # Shorter FOC
            create_test_request("REQ_003", order_date=order_time, foc_target=10.0)
        ]
        pool.add_requests(requests)
        
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        sorted_requests = pool.sort_by_priority(requests, current_time, descending=True)
        
        # Shorter FOC target = higher priority
        assert sorted_requests[0].request_id == "REQ_002"
        assert sorted_requests[-1].request_id == "REQ_003"
    
    def test_sort_by_age(self):
        """Test sorting by age"""
        pool = RequestPool()
        
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        requests = [
            create_test_request("REQ_001", order_date=base_time + timedelta(days=1)),
            create_test_request("REQ_002", order_date=base_time),  # Oldest
            create_test_request("REQ_003", order_date=base_time + timedelta(days=2))  # Newest
        ]
        pool.add_requests(requests)
        
        current_time = datetime(2024, 5, 4, 0, 0, 0, tzinfo=timezone.utc)
        
        # Sort descending (oldest first)
        sorted_desc = pool.sort_by_age(requests, current_time, descending=True)
        assert sorted_desc[0].request_id == "REQ_002"
        
        # Sort ascending (newest first)
        sorted_asc = pool.sort_by_age(requests, current_time, descending=False)
        assert sorted_asc[0].request_id == "REQ_003"
    
    def test_sort_by_foc_target(self):
        """Test sorting by FOC target"""
        pool = RequestPool()
        
        requests = [
            create_test_request("REQ_001", foc_target=8.0),
            create_test_request("REQ_002", foc_target=5.0),  # Shortest
            create_test_request("REQ_003", foc_target=10.0)  # Longest
        ]
        pool.add_requests(requests)
        
        # Sort ascending (shortest first)
        sorted_asc = pool.sort_by_foc_target(requests, ascending=True)
        assert sorted_asc[0].request_id == "REQ_002"
        assert sorted_asc[-1].request_id == "REQ_003"
        
        # Sort descending (longest first)
        sorted_desc = pool.sort_by_foc_target(requests, ascending=False)
        assert sorted_desc[0].request_id == "REQ_003"
        assert sorted_desc[-1].request_id == "REQ_002"


# ============================================================================
# TEST: Assignment Operations
# ============================================================================

class TestAssignmentOperations:
    """Test suite for request assignment operations"""
    
    def test_assign_request_to_agent(self):
        """Test assigning request to agent"""
        pool = RequestPool()
        request = create_test_request("REQ_001")
        pool.add_request(request)
        
        assignment_time = datetime.now(timezone.utc)
        success = pool.assign_request_to_agent("REQ_001", "john.doe", assignment_time)
        
        assert success is True
        
        # Check request state changed
        assigned_request = pool.get_request("REQ_001")
        assert assigned_request.state == RequestState.ASSIGNED
        assert assigned_request.assigned_agent_id == "john.doe"
        
        # Check indexes updated
        new_requests = pool.get_requests_by_state(RequestState.NEW)
        assigned_requests = pool.get_requests_by_state(RequestState.ASSIGNED)
        assert len(new_requests) == 0
        assert len(assigned_requests) == 1
    
    def test_assign_nonexistent_request(self):
        """Test assigning request that doesn't exist"""
        pool = RequestPool()
        
        success = pool.assign_request_to_agent("REQ_999", "john.doe", datetime.now(timezone.utc))
        
        assert success is False
    
    def test_assign_already_assigned_request(self):
        """Test assigning request that's already assigned"""
        pool = RequestPool()
        request = create_test_request("REQ_001")
        pool.add_request(request)
        
        assignment_time = datetime.now(timezone.utc)
        
        # First assignment succeeds
        success1 = pool.assign_request_to_agent("REQ_001", "john.doe", assignment_time)
        assert success1 is True
        
        # Second assignment should fail
        success2 = pool.assign_request_to_agent("REQ_001", "jane.smith", assignment_time)
        assert success2 is False
        
        # Original assignment should remain
        request = pool.get_request("REQ_001")
        assert request.assigned_agent_id == "john.doe"
    
    def test_complete_request(self):
        """Test completing a request"""
        pool = RequestPool()
        request = create_test_request("REQ_001")
        pool.add_request(request)
        
        assignment_time = datetime.now(timezone.utc)
        completion_time = assignment_time + timedelta(hours=2)
        
        # Assign first
        pool.assign_request_to_agent("REQ_001", "john.doe", assignment_time)
        
        # Then complete
        success = pool.complete_request("REQ_001", completion_time)
        
        assert success is True
        
        # Check request state
        completed_request = pool.get_request("REQ_001")
        assert completed_request.state == RequestState.COMPLETED
        assert completed_request.completion_date == completion_time
        
        # Check indexes
        completed_requests = pool.get_requests_by_state(RequestState.COMPLETED)
        assert len(completed_requests) == 1
    
    def test_complete_unassigned_request(self):
        """Test completing request that hasn't been assigned"""
        pool = RequestPool()
        request = create_test_request("REQ_001")
        pool.add_request(request)
        
        success = pool.complete_request("REQ_001", datetime.now(timezone.utc))
        
        assert success is False
        
        # Request should still be NEW
        request = pool.get_request("REQ_001")
        assert request.state == RequestState.NEW


# ============================================================================
# TEST: Statistics
# ============================================================================

class TestStatistics:
    """Test suite for pool statistics"""
    
    def test_get_statistics_empty_pool(self):
        """Test statistics for empty pool"""
        pool = RequestPool()
        
        stats = pool.get_statistics()
        
        assert stats['total_requests'] == 0
        assert stats['by_state'] == {}
        assert stats['by_skill'] == {}
    
    def test_get_statistics_basic(self):
        """Test basic statistics"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001", skill_id="internet", has_sla=True),
            create_test_request("REQ_002", skill_id="internet", is_escalated=True),
            create_test_request("REQ_003", skill_id="voice", is_winback=True)
        ]
        pool.add_requests(requests)
        
        stats = pool.get_statistics()
        
        assert stats['total_requests'] == 3
        assert stats['total_added'] == 3
        assert stats['by_state']['new'] == 3
        assert stats['by_skill']['internet'] == 2
        assert stats['by_skill']['voice'] == 1
        assert stats['flags']['sla_count'] == 1
        assert stats['flags']['escalated_count'] == 1
        assert stats['flags']['winback_count'] == 1
    
    def test_get_statistics_with_time(self):
        """Test statistics with age and FOC compliance"""
        pool = RequestPool()
        
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        requests = [
            create_test_request("REQ_001", order_date=base_time, foc_target=5.0),  # Breached
            create_test_request("REQ_002", order_date=base_time + timedelta(days=4), foc_target=8.0),  # OK
            create_test_request("REQ_003", order_date=base_time + timedelta(days=6), foc_target=8.0)   # OK
        ]
        pool.add_requests(requests)
        
        current_time = datetime(2024, 5, 10, 0, 0, 0, tzinfo=timezone.utc)
        
        stats = pool.get_statistics(current_time)
        
        # Age statistics
        assert 'age' in stats
        assert stats['age']['min_days'] == 4.0
        assert stats['age']['max_days'] == 9.0
        
        # FOC compliance
        assert 'foc_compliance' in stats
        assert stats['foc_compliance']['compliant_count'] == 2
        assert stats['foc_compliance']['breached_count'] == 1
        assert abs(stats['foc_compliance']['compliance_rate'] - (2/3)) < 0.01
    
    def test_get_skills(self):
        """Test getting unique skills"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001", skill_id="internet"),
            create_test_request("REQ_002", skill_id="voice"),
            create_test_request("REQ_003", skill_id="internet"),
            create_test_request("REQ_004", skill_id="tv")
        ]
        pool.add_requests(requests)
        
        skills = pool.get_skills()
        
        assert len(skills) == 3
        assert set(skills) == {"internet", "voice", "tv"}
        assert skills == sorted(skills)  # Should be sorted
    
    def test_get_skill_distribution(self):
        """Test getting skill distribution"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001", skill_id="internet"),
            create_test_request("REQ_002", skill_id="internet"),
            create_test_request("REQ_003", skill_id="voice"),
            create_test_request("REQ_004", skill_id="tv"),
            create_test_request("REQ_005", skill_id="tv"),
            create_test_request("REQ_006", skill_id="tv")
        ]
        pool.add_requests(requests)
        
        distribution = pool.get_skill_distribution()
        
        assert distribution['internet'] == 2
        assert distribution['voice'] == 1
        assert distribution['tv'] == 3


# ============================================================================
# TEST: Bulk Operations
# ============================================================================

class TestBulkOperations:
    """Test suite for bulk operations"""
    
    def test_snapshot(self):
        """Test creating a snapshot of the pool"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001", skill_id="internet"),
            create_test_request("REQ_002", skill_id="voice")
        ]
        pool.add_requests(requests)
        
        # Create snapshot
        snapshot = pool.snapshot()
        
        # Snapshot should have same data
        assert snapshot.size() == pool.size()
        assert snapshot.get_request("REQ_001") is not None
        assert snapshot.get_request("REQ_002") is not None
        
        # Modify original
        pool.remove_request("REQ_001")
        pool.add_request(create_test_request("REQ_003"))
        
        # Snapshot should be unchanged
        assert snapshot.size() == 2
        assert snapshot.get_request("REQ_001") is not None
        assert snapshot.get_request("REQ_003") is None
    
    def test_iteration(self):
        """Test iterating over pool"""
        pool = RequestPool()
        requests = [
            create_test_request("REQ_001"),
            create_test_request("REQ_002"),
            create_test_request("REQ_003")
        ]
        pool.add_requests(requests)
        
        # Iterate using for loop
        request_ids = []
        for request in pool:
            request_ids.append(request.request_id)
        
        assert len(request_ids) == 3
        assert set(request_ids) == {"REQ_001", "REQ_002", "REQ_003"}


# ============================================================================
# TEST: Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test suite for realistic integration scenarios"""
    
    def test_routing_workflow(self):
        """Test typical routing workflow"""
        pool = RequestPool()
        
        # Add requests
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        requests = [
            create_test_request("REQ_001", skill_id="internet", order_date=base_time),
            create_test_request("REQ_002", skill_id="internet", order_date=base_time + timedelta(hours=2)),
            create_test_request("REQ_003", skill_id="voice", order_date=base_time),
            create_test_request("REQ_004", skill_id="internet", order_date=base_time + timedelta(hours=1))
        ]
        pool.add_requests(requests)
        
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # Get available internet requests
        available = pool.get_available_requests(skill_id="internet")
        assert len(available) == 3
        
        # Sort by priority
        sorted_requests = pool.sort_by_priority(available, current_time, descending=True)
        
        # Assign highest priority request
        top_request = sorted_requests[0]
        pool.assign_request_to_agent(top_request.request_id, "john.doe", current_time)
        
        # Verify assignment
        assert pool.get_request(top_request.request_id).state == RequestState.ASSIGNED
        
        # Check remaining available
        available_now = pool.get_available_requests(skill_id="internet")
        assert len(available_now) == 2
    
    def test_multi_tier_bucketing(self):
        """Test organizing requests into tiers (like production)"""
        pool = RequestPool()
        
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        requests = [
            # Tier 1: Escalated winback
            create_test_request("REQ_001", is_escalated=True, is_winback=True, 
                              order_date=base_time, foc_target=5.0),
            # Tier 2: Winback (not escalated)
            create_test_request("REQ_002", is_winback=True, 
                              order_date=base_time + timedelta(hours=1), foc_target=5.0),
            # Tier 3: Escalated SLA
            create_test_request("REQ_003", is_escalated=True, has_sla=True, 
                              order_date=base_time + timedelta(hours=2), foc_target=8.0),
            # Tier 4: Escalated non-SLA
            create_test_request("REQ_004", is_escalated=True, 
                              order_date=base_time + timedelta(hours=3), foc_target=8.0),
            # Tier 5: Regular (commons)
            create_test_request("REQ_005", 
                              order_date=base_time + timedelta(hours=4), foc_target=8.0)
        ]
        pool.add_requests(requests)
        
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # Tier 1: Escalated winback
        tier1 = pool.filter_requests(
            is_escalated=True,
            is_winback=True,
            state=RequestState.NEW
        )
        assert len(tier1) == 1
        assert tier1[0].request_id == "REQ_001"
        
        # Tier 2: Winback (not escalated)
        tier2 = pool.filter_requests(
            is_winback=True,
            is_escalated=False,
            state=RequestState.NEW
        )
        assert len(tier2) == 1
        assert tier2[0].request_id == "REQ_002"
        
        # Tier 3: Escalated with SLA
        tier3 = pool.filter_requests(
            is_escalated=True,
            has_sla=True,
            is_winback=False,
            state=RequestState.NEW
        )
        assert len(tier3) == 1
        assert tier3[0].request_id == "REQ_003"
        
        # Tier 4: Escalated non-SLA
        tier4 = pool.filter_requests(
            is_escalated=True,
            has_sla=False,
            is_winback=False,
            state=RequestState.NEW
        )
        assert len(tier4) == 1
        assert tier4[0].request_id == "REQ_004"
        
        # Tier 5: Commons (no special flags)
        tier5 = pool.filter_requests(
            is_escalated=False,
            has_sla=False,
            is_winback=False,
            state=RequestState.NEW
        )
        assert len(tier5) == 1
        assert tier5[0].request_id == "REQ_005"
        
        # Sort each tier by priority
        sorted_tier1 = pool.sort_by_priority(tier1, current_time, descending=True)
        sorted_tier2 = pool.sort_by_priority(tier2, current_time, descending=True)
        sorted_tier3 = pool.sort_by_priority(tier3, current_time, descending=True)
        
        # Verify sorting worked (oldest should have highest priority within tier)
        if sorted_tier1:
            priority1 = sorted_tier1[0].calculate_priority_score(current_time)
            assert priority1 > 0
        
        if sorted_tier2:
            priority2 = sorted_tier2[0].calculate_priority_score(current_time)
            assert priority2 > 0

        if sorted_tier3:
            priority3 = sorted_tier3[0].calculate_priority_score(current_time)
            assert priority3 > 0
        
        # Simulate routing: take from tier 1 first, then tier 2, etc.
        all_tiers = [tier1, tier2, tier3, tier4, tier5]
        routing_order = []
        for tier in all_tiers:
            if tier:
                sorted_tier = pool.sort_by_priority(tier, current_time, descending=True)
                routing_order.extend([r.request_id for r in sorted_tier])
        
        # Verify routing order matches tier priority
        assert routing_order[0] == "REQ_001"  # Tier 1
        assert routing_order[1] == "REQ_002"  # Tier 2
        assert routing_order[2] == "REQ_003"  # Tier 3
        assert routing_order[3] == "REQ_004"  # Tier 4
        assert routing_order[4] == "REQ_005"  # Tier 5
    
    def test_foc_breach_scenario(self):
        """Test handling requests approaching FOC breach"""
        pool = RequestPool()
        
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        requests = [
            create_test_request("REQ_001", order_date=base_time, foc_target=5.0),  # Will breach
            create_test_request("REQ_002", order_date=base_time + timedelta(days=2), foc_target=5.0),  # Close
            create_test_request("REQ_003", order_date=base_time + timedelta(days=4), foc_target=5.0)   # Safe
        ]
        pool.add_requests(requests)
        
        current_time = datetime(2024, 5, 6, 0, 0, 0, tzinfo=timezone.utc)
        
        # Find requests that have breached FOC
        def is_breached(request):
            return not request.is_foc_compliant(current_time)
        
        breached = pool.filter_requests(
            state=RequestState.NEW,
            custom_filter=is_breached
        )
        
        assert len(breached) == 1
        assert breached[0].request_id == "REQ_001"
        
        # Find requests within 1 day of breach
        def near_breach(request):
            time_remaining = request.time_until_foc_breach(current_time)
            return 0 < time_remaining <= 1.0
        
        near_breach_requests = pool.filter_requests(
            state=RequestState.NEW,
            custom_filter=near_breach
        )
        
        assert len(near_breach_requests) == 1
        assert near_breach_requests[0].request_id == "REQ_002"
    
    def test_pool_lifecycle(self):
        """Test complete lifecycle of requests in pool"""
        pool = RequestPool()
        
        # Initial state
        assert pool.size() == 0
        assert pool.is_empty()
        
        # Add requests
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        requests = [
            create_test_request(f"REQ_{i:03d}", skill_id="internet", order_date=base_time)
            for i in range(1, 11)
        ]
        added = pool.add_requests(requests)
        assert added == 10
        assert pool.size() == 10
        
        # All should be NEW
        new_requests = pool.get_requests_by_state(RequestState.NEW)
        assert len(new_requests) == 10
        
        # Assign some requests
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        for i in range(1, 6):
            pool.assign_request_to_agent(f"REQ_{i:03d}", f"agent_{i}", current_time)
        
        # Check state distribution
        new_requests = pool.get_requests_by_state(RequestState.NEW)
        assigned_requests = pool.get_requests_by_state(RequestState.ASSIGNED)
        assert len(new_requests) == 5
        assert len(assigned_requests) == 5
        
        # Complete some requests
        completion_time = current_time + timedelta(hours=2)
        for i in range(1, 4):
            pool.complete_request(f"REQ_{i:03d}", completion_time)
        
        # Check final state
        new_requests = pool.get_requests_by_state(RequestState.NEW)
        assigned_requests = pool.get_requests_by_state(RequestState.ASSIGNED)
        completed_requests = pool.get_requests_by_state(RequestState.COMPLETED)
        
        assert len(new_requests) == 5
        assert len(assigned_requests) == 2
        assert len(completed_requests) == 3
        
        # Get statistics
        stats = pool.get_statistics(current_time)
        assert stats['total_requests'] == 10
        assert stats['total_added'] == 10
        assert stats['total_assigned'] == 5
        assert stats['by_state']['new'] == 5
        assert stats['by_state']['assigned'] == 2
        assert stats['by_state']['completed'] == 3
    
    def test_dynamic_pool_operations(self):
        """Test dynamic addition and removal during simulation"""
        pool = RequestPool()
        
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # Simulate arrivals over time
        for hour in range(10):
            request = create_test_request(
                f"REQ_{hour:03d}",
                skill_id="internet",
                order_date=base_time + timedelta(hours=hour)
            )
            pool.add_request(request)
        
        assert pool.size() == 10
        
        # Simulate assignments and completions
        current_time = base_time + timedelta(hours=5)
        
        # Assign and immediately complete first 3
        for i in range(3):
            pool.assign_request_to_agent(f"REQ_{i:03d}", f"agent_{i}", current_time)
            pool.complete_request(f"REQ_{i:03d}", current_time + timedelta(minutes=30))
        
        # Remove completed requests from pool (simulate cleanup)
        completed = pool.get_requests_by_state(RequestState.COMPLETED)
        for request in completed:
            pool.remove_request(request.request_id)
        
        # Pool should now have 7 requests
        assert pool.size() == 7
        
        # All remaining should be NEW
        new_requests = pool.get_requests_by_state(RequestState.NEW)
        assert len(new_requests) == 7
        
        # Add more requests (new arrivals)
        for hour in range(10, 15):
            request = create_test_request(
                f"REQ_{hour:03d}",
                skill_id="voice",
                order_date=base_time + timedelta(hours=hour)
            )
            pool.add_request(request)
        
        assert pool.size() == 12
        
        # Check skill distribution
        internet_count = len(pool.get_requests_by_skill("internet"))
        voice_count = len(pool.get_requests_by_skill("voice"))
        
        assert internet_count == 7  # 10 - 3 removed
        assert voice_count == 5
    
    def test_priority_changes_over_time(self):
        """Test that priority scores change as time progresses"""
        pool = RequestPool()
        
        base_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        request = create_test_request("REQ_001", order_date=base_time, foc_target=8.0)
        pool.add_request(request)
        
        # Calculate priority at different times
        time_1day = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        time_4days = datetime(2024, 5, 5, 0, 0, 0, tzinfo=timezone.utc)
        time_8days = datetime(2024, 5, 9, 0, 0, 0, tzinfo=timezone.utc)
        
        priority_1d = request.calculate_priority_score(time_1day)
        priority_4d = request.calculate_priority_score(time_4days)
        priority_8d = request.calculate_priority_score(time_8days)
        
        # Priority should increase over time
        assert priority_4d > priority_1d
        assert priority_8d > priority_4d
        
        # At 8 days, should be at FOC target (priority = 1.0)
        assert abs(priority_8d - 1.0) < 0.01
        
        # After 8 days, should be breached
        time_10days = datetime(2024, 5, 11, 0, 0, 0, tzinfo=timezone.utc)
        priority_10d = request.calculate_priority_score(time_10days)
        assert priority_10d > 1.0
        assert not request.is_foc_compliant(time_10days)


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--cov=models.request_pool'])