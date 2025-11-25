"""
Unit tests for Request model.

Run with: pytest tests/unit/test_request.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta

# Import components to test
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.request import Request, RequestState


# ============================================================================
# TEST: Request Creation
# ============================================================================

class TestRequestCreation:
    """Test suite for creating Request objects"""
    
    def test_create_minimal_request(self):
        """Test creating request with only required fields"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        )
        
        assert request.request_id == "REQ_001"
        assert request.external_id == "EXT_001"
        assert request.skill_id == "internet"
        assert request.state == RequestState.NEW
        assert request.foc_target == Request.DEFAULT_FOC_TARGET  # 8.0
        assert not request.has_sla
        assert not request.is_escalated
    
    def test_create_request_with_all_fields(self):
        """Test creating request with all fields"""
        request = Request(
            request_id="REQ_002",
            external_id="EXT_002",
            skill_id="voice",
            request_source="residential",
            product="voice",
            service_region="quebec",
            request_type="change",
            order_date=datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
            foc_target=5.0,
            has_sla=True,
            is_escalated=True,
            is_winback=False,
            customer_support_model="non-standard",
            control_desk="montreal_desk",
            golden_customer_id="GC_12345",
            skill_priority=1,
            metadata={"custom_field": "value"}
        )
        
        assert request.foc_target == 5.0
        assert request.has_sla
        assert request.is_escalated
        assert not request.is_winback
        assert request.customer_support_model == "non-standard"
        assert request.skill_priority == 1
    
    def test_create_request_empty_id_fails(self):
        """Test that empty request_id raises error"""
        with pytest.raises(ValueError, match="request_id cannot be empty"):
            Request(
                request_id="",
                external_id="EXT_001",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=datetime.now(timezone.utc)
            )
    
    def test_create_request_empty_external_id_fails(self):
        """Test that empty external_id raises error"""
        with pytest.raises(ValueError, match="external_id cannot be empty"):
            Request(
                request_id="REQ_001",
                external_id="",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=datetime.now(timezone.utc)
            )
    
    def test_create_request_naive_datetime_fails(self):
        """Test that naive datetime raises error"""
        with pytest.raises(ValueError, match="must be timezone-aware"):
            Request(
                request_id="REQ_001",
                external_id="EXT_001",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=datetime(2024, 5, 1, 10, 0, 0)  # No timezone!
            )
    
    def test_request_id_whitespace_stripped(self):
        """Test that whitespace is stripped from IDs"""
        request = Request(
            request_id="  REQ_001  ",
            external_id="  EXT_001  ",
            skill_id="  internet  ",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        assert request.request_id == "REQ_001"
        assert request.external_id == "EXT_001"
        assert request.skill_id == "internet"
    
    def test_default_foc_target_when_invalid(self):
        """Test that invalid FOC target uses default"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            foc_target=0.0  # Invalid!
        )
        
        assert request.foc_target == Request.DEFAULT_FOC_TARGET


# ============================================================================
# TEST: Age Calculations
# ============================================================================

class TestAgeCalculations:
    """Test suite for age calculation methods"""
    
    def test_age_minutes_one_hour(self):
        """Test age calculation for 1 hour"""
        order_time = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 1, 11, 0, 0, tzinfo=timezone.utc)
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time
        )
        
        age = request.get_age_minutes(current_time)
        assert age == 60.0
    
    def test_age_minutes_fractional(self):
        """Test age calculation with fractional minutes"""
        order_time = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 1, 10, 30, 30, tzinfo=timezone.utc)  # 30.5 minutes
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time
        )
        
        age = request.get_age_minutes(current_time)
        assert age == 30.5
    
    def test_age_days_one_day(self):
        """Test age calculation for 1 day"""
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time
        )
        
        age = request.get_age_days(current_time)
        assert age == 1.0
    
    def test_age_days_fractional(self):
        """Test age calculation with fractional days"""
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 1, 12, 0, 0, tzinfo=timezone.utc)  # 0.5 days
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time
        )
        
        age = request.get_age_days(current_time)
        assert age == 0.5
    
    def test_age_seconds(self):
        """Test age calculation in seconds"""
        order_time = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 1, 10, 5, 30, tzinfo=timezone.utc)  # 330 seconds
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time
        )
        
        age = request.get_age_seconds(current_time)
        assert age == 330.0
    
    def test_age_calculation_naive_datetime_fails(self):
        """Test that naive datetime in age calculation raises error"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        with pytest.raises(ValueError, match="must be timezone-aware"):
            request.get_age_minutes(datetime(2024, 5, 1, 10, 0, 0))  # No timezone!


# ============================================================================
# TEST: Priority Score Calculation
# ============================================================================

class TestPriorityCalculation:
    """Test suite for priority score calculations"""
    
    def test_priority_score_basic(self):
        """Test basic priority score calculation"""
        # Request is 1 day old with 8-day FOC target
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time,
            foc_target=8.0
        )
        
        score = request.calculate_priority_score(current_time)
        
        # score = 1440 minutes / (8 days * 1440 minutes/day) = 1440 / 11520 = 0.125
        assert abs(score - 0.125) < 0.001
    
    def test_priority_score_increases_with_age(self):
        """Test that priority score increases as request ages"""
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time,
            foc_target=8.0
        )
        
        # Calculate score at different times
        time_1day = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        time_2days = datetime(2024, 5, 3, 0, 0, 0, tzinfo=timezone.utc)
        time_4days = datetime(2024, 5, 5, 0, 0, 0, tzinfo=timezone.utc)
        
        score_1 = request.calculate_priority_score(time_1day)
        score_2 = request.calculate_priority_score(time_2days)
        score_4 = request.calculate_priority_score(time_4days)
        
        # Scores should increase with age
        assert score_2 > score_1
        assert score_4 > score_2
        assert score_4 == score_1 * 4  # Linear relationship
    
    def test_priority_score_higher_for_shorter_foc(self):
        """Test that shorter FOC targets have higher priority"""
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)  # 1 day old
        
        request_8day = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time,
            foc_target=8.0
        )
        
        request_4day = Request(
            request_id="REQ_002",
            external_id="EXT_002",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time,
            foc_target=4.0
        )
        
        score_8 = request_8day.calculate_priority_score(current_time)
        score_4 = request_4day.calculate_priority_score(current_time)
        
        # Shorter FOC target should have higher score
        assert score_4 > score_8
        assert score_4 == score_8 * 2  # Inverse relationship
    
    def test_priority_score_caching(self):
        """Test that priority score caching works"""
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time,
            foc_target=8.0
        )
        
        # Calculate with cache
        score1 = request.calculate_priority_score(current_time, use_cache=True)
        score2 = request.calculate_priority_score(current_time, use_cache=True)
        
        # Should be same (from cache)
        assert score1 == score2
        
        # Different time should recalculate
        later_time = datetime(2024, 5, 3, 0, 0, 0, tzinfo=timezone.utc)
        score3 = request.calculate_priority_score(later_time, use_cache=True)
        
        assert score3 > score1


# ============================================================================
# TEST: FOC Compliance
# ============================================================================

class TestFOCCompliance:
    """Test suite for FOC compliance tracking"""
    
    def test_is_foc_compliant_within_target(self):
        """Test FOC compliance when within target"""
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 5, 0, 0, 0, tzinfo=timezone.utc)  # 4 days old
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time,
            foc_target=8.0
        )
        
        assert request.is_foc_compliant(current_time)
    
    def test_is_foc_compliant_exactly_at_target(self):
        """Test FOC compliance exactly at target"""
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 9, 0, 0, 0, tzinfo=timezone.utc)  # Exactly 8 days
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time,
            foc_target=8.0
        )
        
        assert request.is_foc_compliant(current_time)
    
    def test_is_foc_compliant_breached(self):
        """Test FOC compliance when breached"""
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 10, 0, 0, 0, tzinfo=timezone.utc)  # 9 days old
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time,
            foc_target=8.0
        )
        
        assert not request.is_foc_compliant(current_time)
    
    def test_time_until_foc_breach_positive(self):
        """Test time until breach when positive"""
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 5, 0, 0, 0, tzinfo=timezone.utc)  # 4 days old
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time,
            foc_target=8.0
        )
        
        time_remaining = request.time_until_foc_breach(current_time)
        assert time_remaining == 4.0  # 8 - 4 = 4 days remaining
    
    def test_time_until_foc_breach_negative(self):
        """Test time until breach when already breached"""
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 10, 0, 0, 0, tzinfo=timezone.utc)  # 9 days old
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time,
            foc_target=8.0
        )
        
        time_remaining = request.time_until_foc_breach(current_time)
        assert time_remaining == -1.0  # 8 - 9 = -1 day (breached by 1 day)
    
    def test_foc_compliance_percentage(self):
        """Test FOC compliance percentage calculation"""
        order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 5, 5, 0, 0, 0, tzinfo=timezone.utc)  # 4 days old
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_time,
            foc_target=8.0
        )
        
        percentage = request.get_foc_compliance_percentage(current_time)
        assert percentage == 50.0  # 4/8 = 50%


# ============================================================================
# TEST: State Management
# ============================================================================

class TestStateManagement:
    """Test suite for request state transitions"""
    
    def test_initial_state_is_new(self):
        """Test that new requests start in NEW state"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        assert request.state == RequestState.NEW
        assert request.is_new
        assert not request.is_assigned
        assert not request.is_completed
    
    def test_assign_to_agent(self):
        """Test assigning request to agent"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        assignment_time = datetime.now(timezone.utc)
        request.assign_to_agent("john.doe", assignment_time)
        
        assert request.state == RequestState.ASSIGNED
        assert request.assigned_agent_id == "john.doe"
        assert request.assignment_date == assignment_time
        assert request.is_assigned
        assert not request.is_completed
    
    def test_cannot_assign_already_assigned_request(self):
        """Test that assigning already-assigned request raises error"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        request.assign_to_agent("john.doe", datetime.now(timezone.utc))
        
        with pytest.raises(ValueError, match="Cannot assign request in state"):
            request.assign_to_agent("jane.smith", datetime.now(timezone.utc))
    
    def test_mark_completed(self):
        """Test marking request as completed"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        assignment_time = datetime.now(timezone.utc)
        completion_time = assignment_time + timedelta(hours=2)
        
        request.assign_to_agent("john.doe", assignment_time)
        request.mark_completed(completion_time)
        
        assert request.state == RequestState.COMPLETED
        assert request.completion_date == completion_time
        assert request.is_completed
    
    def test_cannot_complete_unassigned_request(self):
        """Test that completing unassigned request raises error"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        with pytest.raises(ValueError, match="Cannot complete request in state"):
            request.mark_completed(datetime.now(timezone.utc))
    
    def test_get_handle_time(self):
        """Test calculating handle time"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        assignment_time = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        completion_time = datetime(2024, 5, 1, 12, 30, 0, tzinfo=timezone.utc)  # 2.5 hours = 9000 seconds
        
        request.assign_to_agent("john.doe", assignment_time)
        request.mark_completed(completion_time)
        
        handle_time = request.get_handle_time_seconds()
        assert handle_time == 9000.0
    
    def test_get_handle_time_none_when_not_completed(self):
        """Test that handle time is None when not completed"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        assert request.get_handle_time_seconds() is None
        
        request.assign_to_agent("john.doe", datetime.now(timezone.utc))
        assert request.get_handle_time_seconds() is None  # Still not completed


# ============================================================================
# TEST: Data Conversion
# ============================================================================

class TestDataConversion:
    """Test suite for data conversion methods"""
    
    def test_to_dict(self):
        """Test converting request to dictionary"""
        order_date = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_date,
            foc_target=8.0,
            has_sla=True,
            is_escalated=False
        )
        
        data = request.to_dict()
        
        assert data['request_id'] == "REQ_001"
        assert data['external_id'] == "EXT_001"
        assert data['skill_id'] == "internet"
        assert data['state'] == "new"
        assert data['foc_target'] == 8.0
        assert data['has_sla'] is True
        assert isinstance(data['order_date'], str)  # ISO format
    
    def test_to_production_format(self):
        """Test converting to production format"""
        order_date = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=order_date,
            foc_target=8.0,
            has_sla=True
        )
        
        prod_data = request.to_production_format()
        
        # Check camelCase naming (production format)
        assert prod_data['requestId'] == "REQ_001"
        assert prod_data['source_externalId'] == "EXT_001"
        assert prod_data['skillId'] == "internet"
        assert prod_data['requestSource'] == "bcom"
        assert prod_data['focTarget'] == 8.0
        assert prod_data['has_sla'] is True
    
    def test_from_dict(self):
        """Test creating request from dictionary"""
        data = {
            'request_id': 'REQ_001',
            'external_id': 'EXT_001',
            'skill_id': 'internet',
            'request_source': 'bcom',
            'product': 'internet',
            'service_region': 'ontario',
            'request_type': 'new',
            'order_date': '2024-05-01T10:00:00+00:00',
            'foc_target': 8.0,
            'has_sla': True,
            'is_escalated': False,
            'is_winback': False,
            'skill_priority': 1
        }
        
        request = Request.from_dict(data)
        
        assert request.request_id == 'REQ_001'
        assert request.skill_id == 'internet'
        assert request.foc_target == 8.0
        assert request.has_sla is True
        assert request.skill_priority == 1
    
    def test_round_trip_conversion(self):
        """Test converting to dict and back"""
        original = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
            foc_target=8.0,
            has_sla=True,
            is_escalated=True
        )
        
        data = original.to_dict()
        reconstructed = Request.from_dict(data)
        
        assert reconstructed.request_id == original.request_id
        assert reconstructed.external_id == original.external_id
        assert reconstructed.skill_id == original.skill_id
        assert reconstructed.foc_target == original.foc_target
        assert reconstructed.has_sla == original.has_sla
        assert reconstructed.is_escalated == original.is_escalated
    
    def test_from_dict_with_assignment(self):
        """Test creating request from dict with assignment data"""
        data = {
            'request_id': 'REQ_001',
            'external_id': 'EXT_001',
            'skill_id': 'internet',
            'request_source': 'bcom',
            'product': 'internet',
            'service_region': 'ontario',
            'request_type': 'new',
            'order_date': '2024-05-01T10:00:00+00:00',
            'assigned_agent_id': 'john.doe',
            'assignment_date': '2024-05-01T11:00:00+00:00',
            'completion_date': '2024-05-01T13:00:00+00:00'
        }
        
        request = Request.from_dict(data)
        
        assert request.assigned_agent_id == 'john.doe'
        assert request.state == RequestState.COMPLETED
        assert request.assignment_date is not None
        assert request.completion_date is not None


# ============================================================================
# TEST: Special Methods
# ============================================================================

class TestSpecialMethods:
    """Test suite for __repr__, __str__, __eq__, __hash__"""
    
    def test_repr(self):
        """Test __repr__ for debugging"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            foc_target=8.0
        )
        
        repr_str = repr(request)
        assert "REQ_001" in repr_str
        assert "internet" in repr_str
        assert "8.0d" in repr_str
    
    def test_str(self):
        """Test __str__ for display"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        str_representation = str(request)
        assert "REQ_001" in str_representation
        assert "internet" in str_representation
        assert "NEW" in str_representation.upper()
    
    def test_equality_based_on_id(self):
        """Test that requests are equal if they have same ID"""
        request1 = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        request2 = Request(
            request_id="REQ_001",
            external_id="EXT_002",  # Different external ID
            skill_id="voice",       # Different skill
            request_source="bcom",
            product="voice",
            service_region="quebec",
            request_type="change",
            order_date=datetime.now(timezone.utc)
        )
        
        request3 = Request(
            request_id="REQ_002",  # Different ID
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        assert request1 == request2  # Same request_id
        assert request1 != request3  # Different request_id
    
    def test_hash_for_sets(self):
        """Test that requests can be used in sets"""
        request1 = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        request2 = Request(
            request_id="REQ_002",
            external_id="EXT_002",
            skill_id="voice",
            request_source="bcom",
            product="voice",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        request3 = Request(
            request_id="REQ_001",  # Same ID as request1
            external_id="EXT_003",
            skill_id="tv",
            request_source="bcom",
            product="tv",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc)
        )
        
        request_set = {request1, request2, request3}
        
        # Only 2 requests in set because request1 and request3 have same ID
        assert len(request_set) == 2


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--cov=models.request'])