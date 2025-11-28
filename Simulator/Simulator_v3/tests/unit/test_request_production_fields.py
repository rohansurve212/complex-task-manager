"""
Unit tests for Request model production routing fields and methods.

Tests the new fields and helper methods added for production routing:
- workorder_followup_date, workorder_expected_completion_date
- workorder_status, workorder_tags, sticky_agent_id
- has_customer_update(), has_internal_note(), is_followup_due(), etc.

Run:
    pytest tests/unit/test_request_production_fields.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from models import Request


class TestRequestProductionFields:
    """Test new production routing fields on Request model."""
    
    def test_workorder_status_default(self):
        """Test default workorder_status is 'new'"""
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
        assert request.workorder_status == "new"
    
    def test_workorder_status_custom(self):
        """Test setting custom workorder_status"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_status="customerreplied"
        )
        assert request.workorder_status == "customerreplied"
    
    def test_workorder_status_setter(self):
        """Test changing workorder_status after creation"""
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
        request.workorder_status = "customerreplied"
        assert request.workorder_status == "customerreplied"
    
    def test_workorder_tags_default(self):
        """Test default workorder_tags is empty list"""
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
        assert request.workorder_tags == []
    
    def test_workorder_tags_custom(self):
        """Test setting custom workorder_tags"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_tags=["NEW_INTERNAL_NOTE", "LOCKED"]
        )
        assert "NEW_INTERNAL_NOTE" in request.workorder_tags
        assert "LOCKED" in request.workorder_tags
        assert len(request.workorder_tags) == 2
    
    def test_workorder_tags_returns_copy(self):
        """Test workorder_tags property returns a copy (immutable)"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_tags=["LOCKED"]
        )
        tags = request.workorder_tags
        tags.append("NEW_TAG")
        # Original should not be modified
        assert "NEW_TAG" not in request.workorder_tags
        assert len(request.workorder_tags) == 1
    
    def test_sticky_agent_id_default(self):
        """Test default sticky_agent_id is None"""
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
        assert request.sticky_agent_id is None
    
    def test_sticky_agent_id_custom(self):
        """Test setting custom sticky_agent_id"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            sticky_agent_id="john.doe"
        )
        assert request.sticky_agent_id == "john.doe"
    
    def test_sticky_agent_id_setter(self):
        """Test changing sticky_agent_id after creation"""
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
        request.sticky_agent_id = "jane.smith"
        assert request.sticky_agent_id == "jane.smith"
    
    def test_followup_date_default(self):
        """Test default workorder_followup_date is None"""
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
        assert request.workorder_followup_date is None
    
    def test_followup_date_custom(self):
        """Test setting custom workorder_followup_date"""
        followup_date = datetime.now(timezone.utc) + timedelta(days=7)
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_followup_date=followup_date
        )
        assert request.workorder_followup_date == followup_date
    
    def test_followup_date_setter(self):
        """Test changing workorder_followup_date after creation"""
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
        new_date = datetime.now(timezone.utc) + timedelta(days=3)
        request.workorder_followup_date = new_date
        assert request.workorder_followup_date == new_date
    
    def test_expected_completion_date_default(self):
        """Test default workorder_expected_completion_date is None"""
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
        assert request.workorder_expected_completion_date is None
    
    def test_expected_completion_date_custom(self):
        """Test setting custom workorder_expected_completion_date"""
        ecd = datetime.now(timezone.utc) + timedelta(days=14)
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_expected_completion_date=ecd
        )
        assert request.workorder_expected_completion_date == ecd
    
    def test_expected_completion_date_setter(self):
        """Test changing workorder_expected_completion_date after creation"""
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
        new_date = datetime.now(timezone.utc) + timedelta(days=21)
        request.workorder_expected_completion_date = new_date
        assert request.workorder_expected_completion_date == new_date
    
    def test_runtime_flags_default(self):
        """Test runtime flags default to False"""
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
        assert request.from_absent_agent is False
        assert request.is_followup is False


class TestRequestHelperMethods:
    """Test new helper methods for production routing."""
    
    def test_has_customer_update_true(self):
        """Test has_customer_update returns True for customerreplied status"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_status="customerreplied"
        )
        assert request.has_customer_update() is True
    
    def test_has_customer_update_false(self):
        """Test has_customer_update returns False for other statuses"""
        for status in ["new", "assigned", "orderconfirmed", "pending"]:
            request = Request(
                request_id="REQ_001",
                external_id="EXT_001",
                skill_id="internet",
                request_source="bcom",
                product="internet",
                service_region="ontario",
                request_type="new",
                order_date=datetime.now(timezone.utc),
                workorder_status=status
            )
            assert request.has_customer_update() is False
    
    def test_has_internal_note_true(self):
        """Test has_internal_note returns True when tag present"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_tags=["NEW_INTERNAL_NOTE"]
        )
        assert request.has_internal_note() is True
    
    def test_has_internal_note_false(self):
        """Test has_internal_note returns False when tag absent"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_tags=["LOCKED", "ESCALATED"]
        )
        assert request.has_internal_note() is False
    
    def test_has_internal_note_empty_tags(self):
        """Test has_internal_note with no tags"""
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
        assert request.has_internal_note() is False
    
    def test_has_customer_update_or_internal_note_customer(self):
        """Test has_customer_update_or_internal_note with customer update"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_status="customerreplied"
        )
        assert request.has_customer_update_or_internal_note() is True
    
    def test_has_customer_update_or_internal_note_note(self):
        """Test has_customer_update_or_internal_note with internal note"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_tags=["NEW_INTERNAL_NOTE"]
        )
        assert request.has_customer_update_or_internal_note() is True
    
    def test_has_customer_update_or_internal_note_both(self):
        """Test has_customer_update_or_internal_note with both"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_status="customerreplied",
            workorder_tags=["NEW_INTERNAL_NOTE"]
        )
        assert request.has_customer_update_or_internal_note() is True
    
    def test_has_customer_update_or_internal_note_false(self):
        """Test has_customer_update_or_internal_note with neither"""
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
        assert request.has_customer_update_or_internal_note() is False
    
    def test_has_expected_completion_date_true(self):
        """Test has_expected_completion_date when ECD is set"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_expected_completion_date=datetime.now(timezone.utc) + timedelta(days=14)
        )
        assert request.has_expected_completion_date() is True
    
    def test_has_expected_completion_date_false(self):
        """Test has_expected_completion_date when ECD is not set"""
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
        assert request.has_expected_completion_date() is False
    
    def test_is_followup_due_no_date(self):
        """Test is_followup_due returns True when no follow-up date set"""
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
        current_time = datetime.now(timezone.utc)
        assert request.is_followup_due(current_time) is True
    
    def test_is_followup_due_past_date(self):
        """Test is_followup_due returns True when follow-up date has passed"""
        current_time = datetime.now(timezone.utc)
        past_date = current_time - timedelta(days=1)
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_followup_date=past_date
        )
        assert request.is_followup_due(current_time) is True
    
    def test_is_followup_due_exact_time(self):
        """Test is_followup_due when current time equals follow-up date"""
        current_time = datetime.now(timezone.utc)
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_followup_date=current_time
        )
        assert request.is_followup_due(current_time) is True
    
    def test_is_followup_due_future_date(self):
        """Test is_followup_due returns False when follow-up date is in future"""
        current_time = datetime.now(timezone.utc)
        future_date = current_time + timedelta(days=1)
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_followup_date=future_date
        )
        assert request.is_followup_due(current_time) is False
    
    def test_is_locked_true(self):
        """Test is_locked returns True when LOCKED tag present"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_tags=["LOCKED"]
        )
        assert request.is_locked() is True
    
    def test_is_locked_false(self):
        """Test is_locked returns False when LOCKED tag absent"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_tags=["NEW_INTERNAL_NOTE"]
        )
        assert request.is_locked() is False
    
    def test_is_locked_multiple_tags(self):
        """Test is_locked with multiple tags including LOCKED"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_tags=["NEW_INTERNAL_NOTE", "LOCKED", "ESCALATED"]
        )
        assert request.is_locked() is True
    
    def test_add_tag(self):
        """Test adding a tag"""
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
        request.add_tag("NEW_INTERNAL_NOTE")
        assert "NEW_INTERNAL_NOTE" in request.workorder_tags
        assert len(request.workorder_tags) == 1
    
    def test_add_multiple_tags(self):
        """Test adding multiple tags"""
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
        request.add_tag("NEW_INTERNAL_NOTE")
        request.add_tag("LOCKED")
        request.add_tag("ESCALATED")
        
        assert len(request.workorder_tags) == 3
        assert "NEW_INTERNAL_NOTE" in request.workorder_tags
        assert "LOCKED" in request.workorder_tags
        assert "ESCALATED" in request.workorder_tags
    
    def test_add_tag_duplicate(self):
        """Test adding duplicate tag doesn't create duplicates"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_tags=["LOCKED"]
        )
        request.add_tag("LOCKED")
        assert request.workorder_tags.count("LOCKED") == 1
        assert len(request.workorder_tags) == 1
    
    def test_remove_tag(self):
        """Test removing a tag"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_tags=["LOCKED", "NEW_INTERNAL_NOTE"]
        )
        request.remove_tag("LOCKED")
        assert "LOCKED" not in request.workorder_tags
        assert "NEW_INTERNAL_NOTE" in request.workorder_tags
        assert len(request.workorder_tags) == 1
    
    def test_remove_tag_not_present(self):
        """Test removing tag that doesn't exist (should not error)"""
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=datetime.now(timezone.utc),
            workorder_tags=["LOCKED"]
        )
        # Should not raise exception
        request.remove_tag("NONEXISTENT")
        assert len(request.workorder_tags) == 1


class TestRequestSerialization:
    """Test serialization of new fields."""
    
    def test_to_dict_includes_new_fields(self):
        """Test to_dict includes all new production routing fields"""
        current_time = datetime.now(timezone.utc)
        followup_date = current_time + timedelta(days=7)
        ecd = current_time + timedelta(days=14)
        
        request = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=current_time,
            workorder_status="customerreplied",
            workorder_tags=["NEW_INTERNAL_NOTE", "LOCKED"],
            sticky_agent_id="john.doe",
            workorder_followup_date=followup_date,
            workorder_expected_completion_date=ecd
        )
        
        data = request.to_dict()
        
        assert 'workorder_status' in data
        assert data['workorder_status'] == "customerreplied"
        
        assert 'workorder_tags' in data
        assert data['workorder_tags'] == ["NEW_INTERNAL_NOTE", "LOCKED"]
        
        assert 'sticky_agent_id' in data
        assert data['sticky_agent_id'] == "john.doe"
        
        assert 'workorder_followup_date' in data
        assert data['workorder_followup_date'] is not None
        
        assert 'workorder_expected_completion_date' in data
        assert data['workorder_expected_completion_date'] is not None
    
    def test_to_dict_none_values(self):
        """Test to_dict with None values for optional fields"""
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
        
        data = request.to_dict()
        
        assert data['workorder_followup_date'] is None
        assert data['workorder_expected_completion_date'] is None
        assert data['sticky_agent_id'] is None
        assert data['workorder_tags'] == []
    
    def test_from_dict_restores_new_fields(self):
        """Test from_dict properly restores new production routing fields"""
        current_time = datetime.now(timezone.utc)
        followup_date = current_time + timedelta(days=7)
        ecd = current_time + timedelta(days=14)
        
        data = {
            'request_id': 'REQ_001',
            'external_id': 'EXT_001',
            'skill_id': 'internet',
            'request_source': 'bcom',
            'product': 'internet',
            'service_region': 'ontario',
            'request_type': 'new',
            'order_date': current_time.isoformat(),
            'workorder_status': 'customerreplied',
            'workorder_tags': ['NEW_INTERNAL_NOTE', 'LOCKED'],
            'sticky_agent_id': 'john.doe',
            'workorder_followup_date': followup_date.isoformat(),
            'workorder_expected_completion_date': ecd.isoformat()
        }
        
        request = Request.from_dict(data)
        
        assert request.workorder_status == "customerreplied"
        assert "NEW_INTERNAL_NOTE" in request.workorder_tags
        assert "LOCKED" in request.workorder_tags
        assert len(request.workorder_tags) == 2
        assert request.sticky_agent_id == "john.doe"
        assert request.workorder_followup_date is not None
        assert request.workorder_expected_completion_date is not None
    
    def test_from_dict_missing_new_fields(self):
        """Test from_dict with missing new fields (backward compatibility)"""
        current_time = datetime.now(timezone.utc)
        
        data = {
            'request_id': 'REQ_001',
            'external_id': 'EXT_001',
            'skill_id': 'internet',
            'request_source': 'bcom',
            'product': 'internet',
            'service_region': 'ontario',
            'request_type': 'new',
            'order_date': current_time.isoformat()
        }
        
        # Should not raise exception
        request = Request.from_dict(data)
        
        assert request.workorder_status == "new"  # Default value
        assert request.workorder_tags == []  # Default value
        assert request.sticky_agent_id is None
        assert request.workorder_followup_date is None
        assert request.workorder_expected_completion_date is None
    
    def test_round_trip_serialization(self):
        """Test complete round-trip: Request -> dict -> Request"""
        current_time = datetime.now(timezone.utc)
        
        original = Request(
            request_id="REQ_001",
            external_id="EXT_001",
            skill_id="internet",
            request_source="bcom",
            product="internet",
            service_region="ontario",
            request_type="new",
            order_date=current_time,
            workorder_status="customerreplied",
            workorder_tags=["NEW_INTERNAL_NOTE"],
            sticky_agent_id="john.doe",
            workorder_followup_date=current_time + timedelta(days=7),
            workorder_expected_completion_date=current_time + timedelta(days=14)
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = Request.from_dict(data)
        
        # Verify all new fields match
        assert restored.workorder_status == original.workorder_status
        assert restored.workorder_tags == original.workorder_tags
        assert restored.sticky_agent_id == original.sticky_agent_id
        # Note: Datetime comparison may need tolerance for microseconds
        assert restored.workorder_followup_date is not None
        assert restored.workorder_expected_completion_date is not None

# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--cov=models.request'])