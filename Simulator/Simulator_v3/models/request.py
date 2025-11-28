"""
Request model for STM Simulator v3.0

This module defines the Request class which represents work requests
that need to be processed by agents in the simulation.

The Request class tracks:
- Request identity and attributes (ID, skill, product, region, etc.)
- Current state (new, assigned, completed)
- Priority calculations (FOC-based scoring matching production)
- Assignment tracking
- SLA and escalation flags
"""

from enum import Enum
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone


# ============================================================================
# REQUEST STATE ENUM
# ============================================================================

class RequestState(str, Enum):
    """
    Possible states for a request in the simulation.
    
    States represent the request's lifecycle:
    - NEW: Request created but not yet assigned
    - ASSIGNED: Request assigned to an agent
    - COMPLETED: Request has been completed
    - CANCELLED: Request was cancelled (optional)
    
    Example:
        >>> request = Request(request_id="REQ_001", ...)
        >>> request.state == RequestState.NEW
        True
        >>> request.assign_to_agent("john.doe", datetime.now())
        >>> request.state == RequestState.ASSIGNED
        True
    """
    NEW = "new"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ============================================================================
# REQUEST CLASS
# ============================================================================

class Request:
    """
    Represents a work request that needs to be processed by an agent.
    
    The Request class encapsulates all request-related data and behavior,
    including priority calculations, FOC compliance, and lifecycle management.
    
    This class matches the data structure from production stm-api code,
    specifically the request format used by GetWorkFlow/service.py.
    
    Attributes:
        request_id (str): Unique identifier for the request
        external_id (str): External system identifier
        skill_id (str): Required skill to process this request
        request_source (str): Source system (e.g., 'bcom', 'residential')
        product (str): Product type (e.g., 'internet', 'voice', 'tv')
        service_region (str): Geographic region
        request_type (str): Type (e.g., 'new', 'move', 'add', 'change')
        order_date (datetime): When request was created
        foc_target (float): Time-to-pickup target in days (FOC = First Out of Compliance)
        has_sla (bool): Whether request has contract SLA
        is_escalated (bool): Whether request is P1 escalated
        is_winback (bool): Whether this is a winback request
        state (RequestState): Current lifecycle state
        assigned_agent_id (Optional[str]): ID of assigned agent
        assignment_date (Optional[datetime]): When assigned
        completion_date (Optional[datetime]): When completed
        
    Example:
        >>> request = Request(
        ...     request_id="REQ_001",
        ...     external_id="EXT_12345",
        ...     skill_id="internet",
        ...     request_source="bcom",
        ...     product="internet",
        ...     service_region="ontario",
        ...     request_type="new",
        ...     order_date=datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
        ...     foc_target=8.0,
        ...     has_sla=True
        ... )
        >>> request.calculate_priority_score(datetime(2024, 5, 2, 10, 0, 0, tzinfo=timezone.utc))
        180.0  # (24 hours * 60 minutes) / 8 days
    """
    
    # Default FOC target if none specified (matches production DEFAULT_TTPU)
    DEFAULT_FOC_TARGET = 8.0
    
    def __init__(
        self,
        request_id: str,
        external_id: str,
        skill_id: str,
        request_source: str,
        product: str,
        service_region: str,
        request_type: str,
        order_date: datetime,
        foc_target: Optional[float] = None,
        has_sla: bool = False,
        is_escalated: bool = False,
        is_winback: bool = False,
        customer_support_model: Optional[str] = None,
        control_desk: Optional[str] = None,
        golden_customer_id: Optional[str] = None,
        customer_market_segment: Optional[str] = None,
        preferred_language: Optional[str] = None,
        skill_priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        # NEW FIELDS for production routing
        workorder_followup_date: Optional[datetime] = None,
        workorder_expected_completion_date: Optional[datetime] = None,
        workorder_status: str = "new",
        workorder_tags: Optional[List[str]] = None,
        sticky_agent_id: Optional[str] = None
    ):
        """
        Initialize a new Request.
        
        Args:
            request_id: Unique identifier
            external_id: External system ID
            skill_id: Required skill
            request_source: Source system
            product: Product type
            service_region: Geographic region
            request_type: Request type
            order_date: When request was created (must be timezone-aware)
            foc_target: FOC target in days (default: 8.0)
            has_sla: Whether request has contract SLA
            is_escalated: Whether request is P1 escalated
            is_winback: Whether this is a winback request
            customer_support_model: Support model (e.g., 'standard', 'non-standard')
            control_desk: Control desk name
            golden_customer_id: Golden customer ID
            customer_market_segment: Market segment
            preferred_language: Preferred language
            skill_priority: P1/P2 priority (1=P1, 2=P2, 0=none)
            metadata: Additional arbitrary data
            workorder_followup_date: Follow-up date for this request
            workorder_expected_completion_date: Expected completion date (ECD)
            workorder_status: Request status (new, customerreplied, orderconfirmed, etc.)
            workorder_tags: Request tags (NEW_INTERNAL_NOTE, LOCKED, etc.)
            sticky_agent_id: Agent this request is 'sticky' assigned to

        Raises:
            ValueError: If required fields are empty or invalid
            
        Example:
            >>> request = Request(
            ...     request_id="REQ_001",
            ...     external_id="EXT_001",
            ...     skill_id="internet",
            ...     request_source="bcom",
            ...     product="internet",
            ...     service_region="ontario",
            ...     request_type="new",
            ...     order_date=datetime.now(timezone.utc),
            ...     foc_target=8.0
            ... )
        """
        # Validation
        if not request_id or not request_id.strip():
            raise ValueError("request_id cannot be empty")
        if not external_id or not external_id.strip():
            raise ValueError("external_id cannot be empty")
        if not skill_id or not skill_id.strip():
            raise ValueError("skill_id cannot be empty")
        
        # Ensure order_date is timezone-aware
        if order_date.tzinfo is None:
            raise ValueError("order_date must be timezone-aware (use timezone.utc)")
        
        # Core identity
        self._request_id = request_id.strip()
        self._external_id = external_id.strip()
        self._skill_id = skill_id.strip()
        
        # Request attributes
        self._request_source = request_source
        self._product = product
        self._service_region = service_region
        self._request_type = request_type
        self._order_date = order_date
        
        # FOC and SLA
        self._foc_target = foc_target if foc_target is not None and foc_target > 0 else self.DEFAULT_FOC_TARGET
        self._has_sla = has_sla
        
        # Flags
        self._is_escalated = is_escalated
        self._is_winback = is_winback
        
        # Additional attributes (matching production data)
        self._customer_support_model = customer_support_model
        self._control_desk = control_desk
        self._golden_customer_id = golden_customer_id
        self._customer_market_segment = customer_market_segment
        self._preferred_language = preferred_language
        self._skill_priority = skill_priority
        
        # State management
        self._state = RequestState.NEW
        self._assigned_agent_id = None
        self._assignment_date = None
        self._completion_date = None
        
        # Metadata
        self._metadata = metadata if metadata is not None else {}
        
        # Computed values (cached for performance)
        self._cached_priority_score = None
        self._cached_priority_score_time = None

        # Production routing fields
        self._workorder_followup_date = workorder_followup_date
        self._workorder_expected_completion_date = workorder_expected_completion_date
        self._workorder_status = workorder_status
        self._workorder_tags = workorder_tags if workorder_tags is not None else []
        self._sticky_agent_id = sticky_agent_id
        
        # Runtime flags (not persisted)
        self.from_absent_agent = False
        self.is_followup = False
    
    # ========================================================================
    # PROPERTIES - Read-only access to attributes
    # ========================================================================
    
    @property
    def request_id(self) -> str:
        """Get request ID (immutable)"""
        return self._request_id
    
    @property
    def external_id(self) -> str:
        """Get external system ID"""
        return self._external_id
    
    @property
    def skill_id(self) -> str:
        """Get required skill ID"""
        return self._skill_id
    
    @property
    def request_source(self) -> str:
        """Get request source system"""
        return self._request_source
    
    @property
    def product(self) -> str:
        """Get product type"""
        return self._product
    
    @property
    def service_region(self) -> str:
        """Get service region"""
        return self._service_region
    
    @property
    def request_type(self) -> str:
        """Get request type"""
        return self._request_type
    
    @property
    def order_date(self) -> datetime:
        """Get order date (timezone-aware)"""
        return self._order_date
    
    @property
    def foc_target(self) -> float:
        """Get FOC target in days"""
        return self._foc_target
    
    @property
    def has_sla(self) -> bool:
        """Check if request has contract SLA"""
        return self._has_sla
    
    @property
    def is_escalated(self) -> bool:
        """Check if request is P1 escalated"""
        return self._is_escalated
    
    @property
    def is_winback(self) -> bool:
        """Check if this is a winback request"""
        return self._is_winback
    
    @property
    def customer_support_model(self) -> Optional[str]:
        """Get customer support model"""
        return self._customer_support_model
    
    @property
    def control_desk(self) -> Optional[str]:
        """Get control desk"""
        return self._control_desk
    
    @property
    def golden_customer_id(self) -> Optional[str]:
        """Get golden customer ID"""
        return self._golden_customer_id
    
    @property
    def skill_priority(self) -> int:
        """Get skill priority (1=P1, 2=P2, 0=none)"""
        return self._skill_priority
    
    @property
    def state(self) -> RequestState:
        """Get current request state"""
        return self._state
    
    @property
    def assigned_agent_id(self) -> Optional[str]:
        """Get ID of assigned agent (None if not assigned)"""
        return self._assigned_agent_id
    
    @property
    def assignment_date(self) -> Optional[datetime]:
        """Get assignment date (None if not assigned)"""
        return self._assignment_date
    
    @property
    def completion_date(self) -> Optional[datetime]:
        """Get completion date (None if not completed)"""
        return self._completion_date
    
    @property
    def is_assigned(self) -> bool:
        """Check if request is assigned to an agent"""
        return self._state in (RequestState.ASSIGNED, RequestState.COMPLETED)
    
    @property
    def is_completed(self) -> bool:
        """Check if request is completed"""
        return self._state == RequestState.COMPLETED
    
    @property
    def is_new(self) -> bool:
        """Check if request is new (not yet assigned)"""
        return self._state == RequestState.NEW
    
    @property
    def workorder_followup_date(self) -> Optional[datetime]:
        """Get follow-up date"""
        return self._workorder_followup_date
    
    @workorder_followup_date.setter
    def workorder_followup_date(self, value: Optional[datetime]) -> None:
        """Set follow-up date"""
        self._workorder_followup_date = value
    
    @property
    def workorder_expected_completion_date(self) -> Optional[datetime]:
        """Get expected completion date (ECD)"""
        return self._workorder_expected_completion_date
    
    @workorder_expected_completion_date.setter
    def workorder_expected_completion_date(self, value: Optional[datetime]) -> None:
        """Set expected completion date"""
        self._workorder_expected_completion_date = value
    
    @property
    def workorder_status(self) -> str:
        """Get workorder status"""
        return self._workorder_status
    
    @workorder_status.setter
    def workorder_status(self, value: str) -> None:
        """Set workorder status"""
        self._workorder_status = value
    
    @property
    def workorder_tags(self) -> List[str]:
        """Get workorder tags (returns copy)"""
        return self._workorder_tags.copy()
    
    @property
    def sticky_agent_id(self) -> Optional[str]:
        """Get sticky agent ID (agent who 'owns' this request for follow-up)"""
        return self._sticky_agent_id
    
    @sticky_agent_id.setter
    def sticky_agent_id(self, value: Optional[str]) -> None:
        """Set sticky agent ID"""
        self._sticky_agent_id = value
    
    # ========================================================================
    # AGE AND TIME CALCULATIONS
    # ========================================================================
    
    def get_age_minutes(self, current_time: datetime) -> float:
        """
        Calculate request age in minutes.
        
        Args:
            current_time: Current simulation time (must be timezone-aware)
            
        Returns:
            float: Age in minutes
            
        Example:
            >>> order_time = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
            >>> current_time = datetime(2024, 5, 1, 11, 30, 0, tzinfo=timezone.utc)
            >>> request = Request(..., order_date=order_time)
            >>> request.get_age_minutes(current_time)
            90.0
        """
        if current_time.tzinfo is None:
            raise ValueError("current_time must be timezone-aware")
        
        age_seconds = (current_time - self._order_date).total_seconds()
        return age_seconds / 60.0
    
    def get_age_days(self, current_time: datetime) -> float:
        """
        Calculate request age in days.
        
        Args:
            current_time: Current simulation time (must be timezone-aware)
            
        Returns:
            float: Age in days
        """
        return self.get_age_minutes(current_time) / (24.0 * 60.0)
    
    def get_age_seconds(self, current_time: datetime) -> float:
        """
        Calculate request age in seconds.
        
        Args:
            current_time: Current simulation time (must be timezone-aware)
            
        Returns:
            float: Age in seconds
        """
        if current_time.tzinfo is None:
            raise ValueError("current_time must be timezone-aware")
        
        return (current_time - self._order_date).total_seconds()
    
    # ========================================================================
    # PRIORITY CALCULATION (matches production routing.py)
    # ========================================================================
    
    def calculate_priority_score(
        self,
        current_time: datetime,
        use_cache: bool = False
    ) -> float:
        """
        Calculate priority score for this request.
        
        This matches the production logic from stm-api/app/GetWorkFlow/routing.py:
        - score = age_in_minutes / foc_target_in_minutes
        - Higher score = higher priority
        - Older requests and shorter FOC targets get higher scores
        
        Args:
            current_time: Current simulation time (must be timezone-aware)
            use_cache: Whether to use cached score if available
            
        Returns:
            float: Priority score (higher = more urgent)
            
        Example:
            >>> # Request is 1 day old with 8-day FOC target
            >>> order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
            >>> current_time = datetime(2024, 5, 2, 0, 0, 0, tzinfo=timezone.utc)
            >>> request = Request(..., order_date=order_time, foc_target=8.0)
            >>> score = request.calculate_priority_score(current_time)
            >>> # score = (24 hours * 60 min) / (8 days * 24 hours * 60 min)
            >>> # score = 1440 / 11520 = 0.125
        """
        # Check cache
        if use_cache and self._cached_priority_score_time == current_time:
            return self._cached_priority_score
        
        # Calculate age in minutes
        age_minutes = self.get_age_minutes(current_time)
        
        # Convert FOC target from days to minutes
        foc_target_minutes = self._foc_target * 24.0 * 60.0
        
        # Calculate score (matches production logic)
        if foc_target_minutes > 0:
            score = age_minutes / foc_target_minutes
        else:
            # Fallback to default if FOC target is invalid
            default_foc_minutes = self.DEFAULT_FOC_TARGET * 24.0 * 60.0
            score = age_minutes / default_foc_minutes
        
        # Cache the result
        if use_cache:
            self._cached_priority_score = score
            self._cached_priority_score_time = current_time
        
        return score

    def has_customer_update(self) -> bool:
        """
        Check if request has customer update (status is customerreplied).
        
        Returns:
            bool: True if status is 'customerreplied'
        """
        return self._workorder_status == "customerreplied"
    
    def has_internal_note(self) -> bool:
        """
        Check if request has new internal note tag.
        
        Returns:
            bool: True if 'NEW_INTERNAL_NOTE' tag is present
        """
        return "NEW_INTERNAL_NOTE" in self._workorder_tags
    
    def has_customer_update_or_internal_note(self) -> bool:
        """
        Check if request has either customer update or internal note.
        
        Returns:
            bool: True if either condition is met
        """
        return self.has_customer_update() or self.has_internal_note()
    
    def has_expected_completion_date(self) -> bool:
        """
        Check if expected completion date is set.
        
        Returns:
            bool: True if ECD is set
        """
        return self._workorder_expected_completion_date is not None
    
    def is_followup_due(self, current_time: datetime) -> bool:
        """
        Check if follow-up date has passed.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            bool: True if no follow-up date set OR follow-up date has passed
            
        Example:
            >>> # Request with no follow-up date is available immediately
            >>> request.is_followup_due(current_time)
            True
            >>> # Request with future follow-up date is not available yet
            >>> request.workorder_followup_date = current_time + timedelta(days=1)
            >>> request.is_followup_due(current_time)
            False
        """
        if self._workorder_followup_date is None:
            return True  # No follow-up date = available now
        return current_time >= self._workorder_followup_date
    
    def is_locked(self) -> bool:
        """
        Check if request has LOCKED tag.
        
        Returns:
            bool: True if 'LOCKED' tag is present
        """
        return "LOCKED" in self._workorder_tags
    
    def add_tag(self, tag: str) -> None:
        """
        Add a tag if not already present.
        
        Args:
            tag: Tag to add (e.g., 'NEW_INTERNAL_NOTE', 'LOCKED')
            
        Example:
            >>> request.add_tag('NEW_INTERNAL_NOTE')
            >>> 'NEW_INTERNAL_NOTE' in request.workorder_tags
            True
        """
        if tag not in self._workorder_tags:
            self._workorder_tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """
        Remove a tag if present.
        
        Args:
            tag: Tag to remove
            
        Example:
            >>> request.remove_tag('LOCKED')
        """
        if tag in self._workorder_tags:
            self._workorder_tags.remove(tag)

    # ========================================================================
    # FOC COMPLIANCE TRACKING
    # ========================================================================
    
    def is_foc_compliant(self, current_time: datetime) -> bool:
        """
        Check if request is within FOC target.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            bool: True if age <= FOC target, False otherwise
            
        Example:
            >>> order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
            >>> current_time = datetime(2024, 5, 5, 0, 0, 0, tzinfo=timezone.utc)
            >>> request = Request(..., order_date=order_time, foc_target=8.0)
            >>> request.is_foc_compliant(current_time)
            True  # 4 days old, 8-day target
        """
        age_days = self.get_age_days(current_time)
        return age_days <= self._foc_target
    
    def time_until_foc_breach(self, current_time: datetime) -> float:
        """
        Calculate time remaining until FOC breach.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            float: Days remaining (negative if already breached)
            
        Example:
            >>> order_time = datetime(2024, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
            >>> current_time = datetime(2024, 5, 5, 0, 0, 0, tzinfo=timezone.utc)
            >>> request = Request(..., order_date=order_time, foc_target=8.0)
            >>> request.time_until_foc_breach(current_time)
            4.0  # 4 days remaining
        """
        age_days = self.get_age_days(current_time)
        return self._foc_target - age_days
    
    def get_foc_compliance_percentage(self, current_time: datetime) -> float:
        """
        Calculate how much of FOC target has been consumed.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            float: Percentage (0.0 to 100.0+)
            
        Example:
            >>> # Request is 4 days old with 8-day target
            >>> request.get_foc_compliance_percentage(current_time)
            50.0  # 50% of FOC target consumed
        """
        age_days = self.get_age_days(current_time)
        if self._foc_target > 0:
            return (age_days / self._foc_target) * 100.0
        return 0.0
    
    # ========================================================================
    # STATE MANAGEMENT
    # ========================================================================
    
    def assign_to_agent(
        self,
        agent_id: str,
        assignment_time: datetime
    ) -> None:
        """
        Assign this request to an agent.
        
        Args:
            agent_id: ID of the agent
            assignment_time: When the assignment occurred
            
        Raises:
            ValueError: If request is already assigned or completed
            
        Example:
            >>> request = Request(...)
            >>> request.assign_to_agent("john.doe", datetime.now(timezone.utc))
            >>> request.is_assigned
            True
        """
        if self._state != RequestState.NEW:
            raise ValueError(
                f"Cannot assign request in state {self._state}. "
                f"Request must be in NEW state."
            )
        
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id cannot be empty")
        
        if assignment_time.tzinfo is None:
            raise ValueError("assignment_time must be timezone-aware")
        
        self._assigned_agent_id = agent_id.strip()
        self._assignment_date = assignment_time
        self._state = RequestState.ASSIGNED
        
        # Clear cache
        self._cached_priority_score = None
        self._cached_priority_score_time = None
    
    def mark_completed(self, completion_time: datetime) -> None:
        """
        Mark request as completed.
        
        Args:
            completion_time: When the request was completed
            
        Raises:
            ValueError: If request is not assigned
            
        Example:
            >>> request = Request(...)
            >>> request.assign_to_agent("john.doe", datetime.now(timezone.utc))
            >>> request.mark_completed(datetime.now(timezone.utc))
            >>> request.is_completed
            True
        """
        if self._state != RequestState.ASSIGNED:
            raise ValueError(
                f"Cannot complete request in state {self._state}. "
                f"Request must be ASSIGNED first."
            )
        
        if completion_time.tzinfo is None:
            raise ValueError("completion_time must be timezone-aware")
        
        self._completion_date = completion_time
        self._state = RequestState.COMPLETED
    
    def get_handle_time_seconds(self) -> Optional[float]:
        """
        Calculate time between assignment and completion.
        
        Returns:
            Optional[float]: Handle time in seconds, or None if not completed
        """
        if self._assignment_date and self._completion_date:
            return (self._completion_date - self._assignment_date).total_seconds()
        return None
    
    # ========================================================================
    # DATA CONVERSION
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert request to dictionary representation.
        
        Returns:
            Dict: Dictionary containing all request attributes
        """
        return {
            'request_id': self.request_id,
            'external_id': self.external_id,
            'skill_id': self.skill_id,
            'request_source': self.request_source,
            'product': self.product,
            'service_region': self.service_region,
            'request_type': self.request_type,
            'order_date': self.order_date.isoformat(),
            'foc_target': self.foc_target,
            'has_sla': self.has_sla,
            'is_escalated': self.is_escalated,
            'is_winback': self.is_winback,
            'customer_support_model': self.customer_support_model,
            'control_desk': self.control_desk,
            'golden_customer_id': self.golden_customer_id,
            'skill_priority': self.skill_priority,
            'state': self.state.value,
            'assigned_agent_id': self.assigned_agent_id,
            'assignment_date': self.assignment_date.isoformat() if self.assignment_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            # NEW FIELDS
            'workorder_followup_date': self.workorder_followup_date.isoformat() if self.workorder_followup_date else None,
            'workorder_expected_completion_date': self.workorder_expected_completion_date.isoformat() if self.workorder_expected_completion_date else None,
            'workorder_status': self.workorder_status,
            'workorder_tags': self.workorder_tags,
            'sticky_agent_id': self.sticky_agent_id,
            'metadata': self._metadata.copy()
        }

    def to_production_format(self) -> Dict[str, Any]:
        """
        Convert request data to format expected by production routing code.
        
        This matches the format from ElasticRequests in production code.
        
        Returns:
            Dict: Request data in production format
        """
        return {
            'requestId': self.request_id,
            'source_externalId': self.external_id,
            'skillId': self.skill_id,
            'requestSource': self.request_source,
            'product': self.product,
            'serviceRegion': self.service_region,
            'requestType': self.request_type,
            'requestOrderDate': self.order_date,
            'focTarget': self.foc_target,
            'has_sla': self.has_sla,
            'is_escalated': self.is_escalated,
            'is_winback': self.is_winback,
            'customerSupportModel': self.customer_support_model,
            'workOrder_controlDesk': self.control_desk,
            'source_goldenCustomer_id': self.golden_customer_id,
            'skillPriority': self.skill_priority,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Request':
        """
        Create a Request from a dictionary.
        
        Args:
            data: Dictionary containing request attributes
            
        Returns:
            Request: New request instance
        """
        # Parse order_date if it's a string
        order_date = data['order_date']
        if isinstance(order_date, str):
            order_date = datetime.fromisoformat(order_date)
        
        # Ensure timezone-aware
        if order_date.tzinfo is None:
            order_date = order_date.replace(tzinfo=timezone.utc)
        
        # Parse assignment_date if present
        assignment_date = data.get('assignment_date')
        if assignment_date and isinstance(assignment_date, str):
            assignment_date = datetime.fromisoformat(assignment_date)
        
        # Parse completion_date if present
        completion_date = data.get('completion_date')
        if completion_date and isinstance(completion_date, str):
            completion_date = datetime.fromisoformat(completion_date)
        
        # NEW: Parse follow-up date if present
        workorder_followup_date = data.get('workorder_followup_date')
        if workorder_followup_date and isinstance(workorder_followup_date, str):
            workorder_followup_date = datetime.fromisoformat(workorder_followup_date)
        
        # NEW: Parse expected completion date if present
        workorder_expected_completion_date = data.get('workorder_expected_completion_date')
        if workorder_expected_completion_date and isinstance(workorder_expected_completion_date, str):
            workorder_expected_completion_date = datetime.fromisoformat(workorder_expected_completion_date)
        
        request = cls(
            request_id=data['request_id'],
            external_id=data['external_id'],
            skill_id=data['skill_id'],
            request_source=data['request_source'],
            product=data['product'],
            service_region=data['service_region'],
            request_type=data['request_type'],
            order_date=order_date,
            foc_target=data.get('foc_target'),
            has_sla=data.get('has_sla', False),
            is_escalated=data.get('is_escalated', False),
            is_winback=data.get('is_winback', False),
            customer_support_model=data.get('customer_support_model'),
            control_desk=data.get('control_desk'),
            golden_customer_id=data.get('golden_customer_id'),
            skill_priority=data.get('skill_priority', 0),
            metadata=data.get('metadata'),
            # NEW FIELDS
            workorder_followup_date=workorder_followup_date,
            workorder_expected_completion_date=workorder_expected_completion_date,
            workorder_status=data.get('workorder_status', 'new'),
            workorder_tags=data.get('workorder_tags', []),
            sticky_agent_id=data.get('sticky_agent_id')
        )
        
        # Restore state if provided
        if 'assigned_agent_id' in data and data['assigned_agent_id']:
            request._assigned_agent_id = data['assigned_agent_id']
            request._assignment_date = assignment_date
            request._state = RequestState.ASSIGNED
        
        if 'completion_date' in data and data['completion_date']:
            request._completion_date = completion_date
            request._state = RequestState.COMPLETED
        
        return request

    # ========================================================================
    # SPECIAL METHODS
    # ========================================================================
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"Request(request_id='{self.request_id}', "
            f"skill='{self.skill_id}', "
            f"state={self.state}, "
            f"foc_target={self.foc_target}d)"
        )
    
    def __str__(self) -> str:
        """Human-readable string representation"""
        return f"Request {self.request_id} ({self.skill_id}) - {self.state.value.upper()}"
    
    def __eq__(self, other) -> bool:
        """Check equality based on request_id"""
        if not isinstance(other, Request):
            return False
        return self.request_id == other.request_id
    
    def __hash__(self) -> int:
        """Hash based on request_id"""
        return hash(self.request_id)