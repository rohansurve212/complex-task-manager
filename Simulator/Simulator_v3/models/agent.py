"""
Agent model for STM Simulator v3.0

This module defines the Agent class which represents individual agents
who process work requests in the simulation.

The Agent class tracks:
- Agent identity and attributes (ID, name, skills, permissions)
- Current state (idle, working, unavailable)
- Work history and assignments
- Performance metrics (utilization, work count)
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Union
import copy


# ============================================================================
# AGENT STATE ENUM
# ============================================================================

class AgentState(str, Enum):
    """
    Possible states for an agent in the simulation.
    
    States represent what the agent is currently doing:
    - IDLE: Agent is available and waiting for work
    - WORKING: Agent is currently processing a request
    - UNAVAILABLE: Agent is offline, on break, or otherwise unavailable
    
    Example:
        >>> agent = Agent(agent_id="john.doe", full_name="John Doe")
        >>> agent.state == AgentState.IDLE
        True
        >>> agent.set_state(AgentState.WORKING)
        >>> agent.is_available
        False
    """
    IDLE = "idle"
    WORKING = "working"
    UNAVAILABLE = "unavailable"


# ============================================================================
# AGENT CLASS
# ============================================================================

class Agent:
    """
    Represents an individual agent who processes work requests.
    
    The Agent class encapsulates all agent-related data and behavior,
    including state management, work tracking, and metrics calculation.
    
    Attributes:
        agent_id (str): Unique identifier for the agent (e.g., "john.doe")
        full_name (str): Agent's full name (e.g., "John Doe")
        skillsets (Set[str]): Set of skill IDs the agent possesses
        permissions (Dict[str, Any]): Permission attributes (e.g., regions, products)
        state (AgentState): Current state of the agent
        current_request (Optional[str]): ID of request currently being worked on
        work_history (List[Dict]): History of all work assignments
        
    Example:
        >>> agent = Agent(
        ...     agent_id="john.doe",
        ...     full_name="John Doe",
        ...     skillsets={"internet", "voice"},
        ...     permissions={"region": "ontario", "product": "internet"}
        ... )
        >>> agent.assign_request("REQ_001", timestamp=100.0)
        >>> agent.state
        <AgentState.WORKING: 'working'>
    """
    
    def __init__(
        self,
        agent_id: str,
        full_name: str,
        skillsets: Optional[Set[str]] = None,
        permissions: Optional[Dict[str, Any]] = None,
        manager_name: Optional[str] = None,
        cp2_name: Optional[str] = None,
        cp3_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_absent: bool = False  # NEW PARAMETER
    ):
        """
        Initialize a new Agent.
        
        Args:
            agent_id: Unique identifier for the agent
            full_name: Agent's full name
            skillsets: Set of skill IDs (default: empty set)
            permissions: Dictionary of permission attributes (default: empty dict)
            manager_name: Agent's manager name (optional)
            cp2_name: CP2 (level 2) organizational unit name (optional)
            cp3_name: CP3 (level 3) organizational unit name (optional)
            metadata: Additional arbitrary data (default: empty dict)
            is_absent: Whether agent is marked as absent (default: False)
            
        Raises:
            ValueError: If agent_id or full_name is empty
            
        Example:
            >>> agent = Agent(
            ...     agent_id="jane.smith",
            ...     full_name="Jane Smith",
            ...     skillsets={"tv", "internet"},
            ...     cp2_name="Toronto Team",
            ...     cp3_name="Ontario Region"
            ... )
        """
        # Validation
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id cannot be empty")
        if not full_name or not full_name.strip():
            raise ValueError("full_name cannot be empty")
        
        # Core identity attributes
        self._agent_id = agent_id.strip()
        self._full_name = full_name.strip()
        
        # Skills and permissions (use Set for O(1) lookup)
        self._skillsets = skillsets if skillsets is not None else set()
        self._permissions = permissions if permissions is not None else {}
        
        # Organizational hierarchy (matching your production data)
        self._manager_name = manager_name
        self._cp2_name = cp2_name
        self._cp3_name = cp3_name
        
        # Additional metadata
        self._metadata = metadata if metadata is not None else {}

        # Production routing fields
        self._is_absent = is_absent
        
        # State management
        self._state = AgentState.IDLE
        self._current_request = None
        
        # Work tracking
        self._work_history: List[Dict[str, Any]] = []
        
        # Time tracking Metrics (accumulated over time, can be float or datetime)
        self._total_work_time: float = 0.0  # Total seconds spent working
        self._total_idle_time: float = 0.0  # Total seconds spent idle
        self._last_state_change: Optional[Union[float, datetime]] = None
    
    # ========================================================================
    # PROPERTIES - Read-only access to attributes
    # ========================================================================
    
    @property
    def agent_id(self) -> str:
        """Get agent ID (immutable)"""
        return self._agent_id
    
    @property
    def full_name(self) -> str:
        """Get agent full name"""
        return self._full_name
    
    @property
    def skillsets(self) -> Set[str]:
        """
        Get agent skillsets as a set.
        
        Returns a copy to prevent external modification.
        """
        return self._skillsets.copy()
    
    @property
    def skills_list(self) -> List[str]:
        """
        Get agent skillsets as a sorted list.
        
        Useful for serialization and display.
        """
        return sorted(list(self._skillsets))
    
    @property
    def permissions(self) -> Dict[str, Any]:
        """Get agent permissions (returns copy)"""
        return self._permissions.copy()
    
    @property
    def manager_name(self) -> Optional[str]:
        """Get agent's manager name"""
        return self._manager_name
    
    @property
    def cp2_name(self) -> Optional[str]:
        """Get CP2 (level 2) organizational unit name"""
        return self._cp2_name
    
    @property
    def cp3_name(self) -> Optional[str]:
        """Get CP3 (level 3) organizational unit name"""
        return self._cp3_name
    
    @property
    def state(self) -> AgentState:
        """Get current agent state"""
        return self._state
    
    @property
    def current_request(self) -> Optional[str]:
        """Get ID of currently assigned request (None if idle)"""
        return self._current_request
    
    @property
    def work_history(self) -> List[Dict[str, Any]]:
        """
        Get work history (returns copy).
        
        Each entry is a dictionary with:
        - request_id: ID of the request
        - assigned_at: Timestamp when assigned
        - completed_at: Timestamp when completed (None if in progress)
        - duration: Duration in seconds (None if in progress)
        """
        return copy.deepcopy(self._work_history)
    
    @property
    def is_available(self) -> bool:
        """
        Check if agent is available for new work.
        
        Returns:
            bool: True if agent is IDLE, False otherwise
        """
        return self._state == AgentState.IDLE
    
    @property
    def is_working(self) -> bool:
        """Check if agent is currently working"""
        return self._state == AgentState.WORKING
    
    @property
    def work_count(self) -> int:
        """Get total number of completed work items"""
        return len([w for w in self._work_history if w.get('completed_at') is not None])

    @property
    def is_absent(self) -> bool:
        """Check if agent is marked as absent"""
        return self._is_absent
    
    @is_absent.setter
    def is_absent(self, value: bool) -> None:
        """Set agent absence status"""
        self._is_absent = value
    
    # ========================================================================
    # STATE MANAGEMENT METHODS
    # ========================================================================
    
    def set_state(self, new_state: AgentState, timestamp: Optional[float] = None) -> None:
        """
        Change agent's state.
        
        Updates state and tracks timing for metrics calculation.
        
        Args:
            new_state: The new state to transition to
            timestamp: Simulation time (float) or datetime (optional, for metrics tracking)
            
        Raises:
            ValueError: If new_state is not a valid AgentState
            
        Example:
            >>> agent = Agent(agent_id="john", full_name="John")
            >>> agent.set_state(AgentState.WORKING, timestamp=100.0)
            >>> agent.is_working
            True
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}. Must be AgentState enum.")
        
        old_state = self._state
        
        # Track time spent in previous state (if timestamp provided)
        if timestamp is not None and self._last_state_change is not None:
            time_in_state = self._calculate_time_delta(self._last_state_change, timestamp)
            
            if old_state == AgentState.WORKING:
                self._total_work_time += time_in_state
            elif old_state == AgentState.IDLE:
                self._total_idle_time += time_in_state
        
        # Update state
        self._state = new_state
        self._last_state_change = timestamp
    
    def _calculate_time_delta(self, start: Union[float, datetime], end: Union[float, datetime]) -> float:
        """
        Calculate time difference in seconds, handling both float and datetime types.
        
        Args:
            start: Start time (float or datetime)
            end: End time (float or datetime)
        
        Returns:
            float: Time difference in seconds
        
        Raises:
            ValueError: If mixing float and datetime types.
        """
        # Both are floats (simulation time)
        if isinstance(start, (int,float)) and isinstance(end, (int,float)):
            return float(end - start)
        
        # Both are datetime objects
        elif isinstance(start, datetime) and isinstance(end, datetime):
            delta = end - start
            return delta.total_seconds()
        
        # Mixed types - error
        else:
            raise ValueError(
                f"Cannot mix timestamp types: start is {type(start)._name_}, "
                f"end is {type(end)._name_}. Both must be float or both must be datetime."
            )

    def make_available(self, timestamp: Optional[float] = None) -> None:
        """
        Make agent available (set to IDLE state).
        
        Convenience method equivalent to set_state(AgentState.IDLE).
        """
        self.set_state(AgentState.IDLE, timestamp)
    
    def make_unavailable(self, timestamp: Optional[float] = None) -> None:
        """
        Make agent unavailable (offline, on break, etc).
        
        Convenience method equivalent to set_state(AgentState.UNAVAILABLE).
        """
        self.set_state(AgentState.UNAVAILABLE, timestamp)
    
    # ========================================================================
    # WORK ASSIGNMENT METHODS
    # ========================================================================
    
    def assign_request(
        self,
        request_id: str,
        timestamp: Optional[Union[float, datetime]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Assign a request to this agent.
        
        Changes agent state to WORKING and records the assignment in work history.
        
        Args:
            request_id: ID of the request being assigned
            timestamp: Simulation time when assignment occurs
            metadata: Optional additional data about the assignment
            
        Raises:
            ValueError: If agent is not available or request_id is empty
            RuntimeError: If agent already has a current request
            
        Example:
            >>> agent = Agent(agent_id="john", full_name="John")
            >>> agent.assign_request("REQ_001", timestamp=100.0)
            >>> agent.current_request
            'REQ_001'
            >>> agent.is_working
            True
        """
        # Validation
        if not request_id or not request_id.strip():
            raise ValueError("request_id cannot be empty")
        
        if not self.is_available:
            raise ValueError(
                f"Agent {self.agent_id} is not available (current state: {self.state})"
            )
        
        if self._current_request is not None:
            raise RuntimeError(
                f"Agent {self.agent_id} already has assigned request: {self._current_request}"
            )
        
        # Assign request
        self._current_request = request_id
        self.set_state(AgentState.WORKING, timestamp)
        
        # Record in history
        assignment_record = {
            'request_id': request_id,
            'assigned_at': timestamp,
            'completed_at': None,
            'duration': None,
        }
        
        # Add any additional metadata
        if metadata:
            assignment_record.update(metadata)
        
        self._work_history.append(assignment_record)
    
    def complete_request(
        self,
        timestamp: Optional[Union[float, datetime]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Mark current request as completed.
        
        Changes agent state back to IDLE and updates work history.
        
        Args:
            timestamp: Simulation time when request is completed
            metadata: Optional additional data (e.g., completion status)
            
        Returns:
            str: The ID of the completed request
            
        Raises:
            RuntimeError: If agent has no current request
            
        Example:
            >>> agent = Agent(agent_id="john", full_name="John")
            >>> agent.assign_request("REQ_001", timestamp=100.0)
            >>> completed_id = agent.complete_request(timestamp=250.0)
            >>> completed_id
            'REQ_001'
            >>> agent.is_available
            True
        """
        if self._current_request is None:
            raise RuntimeError(f"Agent {self.agent_id} has no current request to complete")
        
        completed_request_id = self._current_request
        
        # Find the assignment in history and update it
        for record in reversed(self._work_history):
            if (record['request_id'] == completed_request_id and 
                record['completed_at'] is None):
                record['completed_at'] = timestamp
                record['duration'] = timestamp - record['assigned_at']
                
                # Add any additional metadata
                if metadata:
                    record.update(metadata)
                break
        
        # Clear current request and return to idle
        self._current_request = None
        self.set_state(AgentState.IDLE, timestamp)
        
        return completed_request_id
    
    # ========================================================================
    # ROUTING METHODS
    # ========================================================================

    def is_in_followup_window(
        self,
        current_time: datetime,
        window_1_start: float = 14.0,
        window_1_end: float = 15.5,
        window_2_start: float = 19.5,
        window_2_end: float = 20.0
    ) -> bool:
        """
        Check if current time is in a follow-up routing window.
        
        Default windows (UTC):
        - Window 1: 14:00-15:30 (10:00-11:30 AM EST)
        - Window 2: 19:30-20:00 (3:30-4:00 PM EST)
        
        Args:
            current_time: Current time to check
            window_1_start: First window start hour (default 14.0)
            window_1_end: First window end hour (default 15.5)
            window_2_start: Second window start hour (default 19.5)
            window_2_end: Second window end hour (default 20.0)
            
        Returns:
            bool: True if in follow-up window
            
        Example:
            >>> from datetime import datetime, timezone
            >>> # 2:30 PM UTC (in first window)
            >>> current_time = datetime(2024, 5, 1, 14, 30, 0, tzinfo=timezone.utc)
            >>> agent.is_in_followup_window(current_time)
            True
            >>> # 3:00 PM UTC (outside windows)
            >>> current_time = datetime(2024, 5, 1, 15, 0, 0, tzinfo=timezone.utc)
            >>> agent.is_in_followup_window(current_time)
            False
        """
        hour = current_time.hour
        minute = current_time.minute
        time_decimal = hour + (minute / 60.0)
        
        in_window_1 = window_1_start <= time_decimal <= window_1_end
        in_window_2 = window_2_start <= time_decimal <= window_2_end
        
        return in_window_1 or in_window_2

    # ========================================================================
    # SKILLS MANAGEMENT
    # ========================================================================
    
    def has_skill(self, skill_id: str) -> bool:
        """
        Check if agent has a specific skill.
        
        Args:
            skill_id: The skill ID to check
            
        Returns:
            bool: True if agent has the skill, False otherwise
            
        Example:
            >>> agent = Agent(
            ...     agent_id="john",
            ...     full_name="John",
            ...     skillsets={"internet", "voice"}
            ... )
            >>> agent.has_skill("internet")
            True
            >>> agent.has_skill("tv")
            False
        """
        return skill_id in self._skillsets
    
    def has_any_skill(self, skill_ids: List[str]) -> bool:
        """
        Check if agent has any of the specified skills.
        
        Args:
            skill_ids: List of skill IDs to check
            
        Returns:
            bool: True if agent has at least one of the skills
        """
        return any(skill in self._skillsets for skill in skill_ids)
    
    def has_all_skills(self, skill_ids: List[str]) -> bool:
        """
        Check if agent has all of the specified skills.
        
        Args:
            skill_ids: List of skill IDs to check
            
        Returns:
            bool: True if agent has all the skills
        """
        return all(skill in self._skillsets for skill in skill_ids)
    
    def add_skill(self, skill_id: str) -> None:
        """
        Add a skill to the agent's skillset.
        
        Args:
            skill_id: The skill ID to add
        """
        self._skillsets.add(skill_id)
    
    def remove_skill(self, skill_id: str) -> bool:
        """
        Remove a skill from the agent's skillset.
        
        Args:
            skill_id: The skill ID to remove
            
        Returns:
            bool: True if skill was removed, False if it wasn't present
        """
        if skill_id in self._skillsets:
            self._skillsets.remove(skill_id)
            return True
        return False
    
    # ========================================================================
    # METRICS CALCULATION
    # ========================================================================
    
    def calculate_utilization(
            self, 
            total_simulation_time: Optional[Union[float, datetime]] = None, start_time: Optional[Union[float, datetime]] = None
        ) -> float:
        """
        Calculate agent utilization as percentage of time spent working.
        
        Utilization = (time spent working) / (total time available)
        
        Args:
            total_simulation_time: Total simulation time in seconds
            start_time: Start time (optional, for datetime calculations)
            
        Returns:
            float: Utilization rate between 0.0 and 1.0
            
        Example:
            >>> agent = Agent(agent_id="john", full_name="John")
            >>> agent.assign_request("REQ_001", timestamp=0.0)
            >>> agent.complete_request(timestamp=100.0)
            >>> agent.calculate_utilization(total_simulation_time=200.0)
            0.5
        """
        if total_simulation_time is None:
            return 0.0
        
         # Convert to seconds if datetime
        if isinstance(total_simulation_time, datetime):
            if start_time is None:
                raise ValueError("start_time required when total_time is datetime")
            if not isinstance(start_time, datetime):
                raise ValueError("start_time must be datetime when total_time is datetime")
            total_seconds = (total_simulation_time - start_time).total_seconds()
        else:
            total_seconds = float(total_simulation_time)
        
        if total_seconds <= 0:
            return 0.0
        
        return self._total_work_time / total_seconds
    
    def get_average_handle_time(self) -> Optional[float]:
        """
        Calculate average time to complete requests.
        
        Returns:
            Optional[float]: Average handle time in seconds, or None if no completed work
            
        Example:
            >>> agent = Agent(agent_id="john", full_name="John")
            >>> agent.assign_request("REQ_001", timestamp=0.0)
            >>> agent.complete_request(timestamp=100.0)
            >>> agent.get_average_handle_time()
            100.0
        """
        completed_work = [
            w for w in self._work_history 
            if w.get('completed_at') is not None and w.get('duration') is not None
        ]
        
        if not completed_work:
            return None
        
        total_duration = sum(w['duration'] for w in completed_work)
        return total_duration / len(completed_work)
    
    # ========================================================================
    # DATA CONVERSION METHODS
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert agent to dictionary representation.
        
        Returns:
            Dict: Dictionary containing all agent attributes
            
        Example:
            >>> agent = Agent(agent_id="john", full_name="John Doe")
            >>> data = agent.to_dict()
            >>> data['agent_id']
            'john'
        """
        return {
            'agent_id': self.agent_id,
            'full_name': self.full_name,
            'skillsets': self.skills_list,  # Convert to list for serialization
            'permissions': self.permissions,
            'manager_name': self.manager_name,
            'cp2_name': self.cp2_name,
            'cp3_name': self.cp3_name,
            'state': self.state.value,  # Convert enum to string
            'current_request': self.current_request,
            'work_count': self.work_count,
            'is_absent': self.is_absent,  # NEW FIELD
            'metadata': self._metadata.copy()
        }
    
    def to_production_format(self) -> Dict[str, Any]:
        """
        Convert agent data to format expected by production routing code.
        
        This matches the format that stm-api GetWorkFlow functions expect.
        
        Returns:
            Dict: Agent data in production format
        """
        return {
            'agent_id': self.agent_id,
            'full_name': self.full_name,
            'skillsets': self.skills_list,  # Production code expects list
            'permissions': self.permissions,
            # Optional fields that production code may use
            'person_manager_name': self.manager_name,
            'CP2_name': self.cp2_name,
            'CP3_name': self.cp3_name,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Agent':
        """
        Create an Agent from a dictionary.
        
        Args:
            data: Dictionary containing agent attributes
            
        Returns:
            Agent: New agent instance
            
        Example:
            >>> data = {
            ...     'agent_id': 'john.doe',
            ...     'full_name': 'John Doe',
            ...     'skillsets': ['internet', 'voice']
            ... }
            >>> agent = Agent.from_dict(data)
            >>> agent.agent_id
            'john.doe'
        """
        # Convert skillsets from list to set if needed
        skillsets = data.get('skillsets', [])
        if isinstance(skillsets, list):
            skillsets = set(skillsets)
        
        return cls(
            agent_id=data['agent_id'],
            full_name=data['full_name'],
            skillsets=skillsets,
            permissions=data.get('permissions'),
            manager_name=data.get('manager_name') or data.get('person_manager_name'),
            cp2_name=data.get('cp2_name') or data.get('CP2_name'),
            cp3_name=data.get('cp3_name') or data.get('CP3_name'),
            metadata=data.get('metadata'),
            is_absent=data.get('is_absent', False)  # NEW FIELD
        )
    
    # ========================================================================
    # SPECIAL METHODS
    # ========================================================================
    
    def __repr__(self) -> str:
        """
        String representation for debugging.
        
        Example:
            >>> agent = Agent(agent_id="john", full_name="John Doe")
            >>> repr(agent)
            "Agent(agent_id='john', full_name='John Doe', state=IDLE, skills=0)"
        """
        return (
            f"Agent(agent_id='{self.agent_id}', "
            f"full_name='{self.full_name}', "
            f"state={self.state.name}, "
            f"skills={len(self._skillsets)})"
        )
    
    def __str__(self) -> str:
        """
        Human-readable string representation.
        
        Example:
            >>> agent = Agent(agent_id="john", full_name="John Doe")
            >>> str(agent)
            'John Doe (john) - IDLE'
        """
        return f"{self.full_name} ({self.agent_id}) - {self.state.value.upper()}"
    
    def __eq__(self, other) -> bool:
        """
        Check equality based on agent_id.
        
        Two agents are equal if they have the same agent_id.
        """
        if not isinstance(other, Agent):
            return False
        return self.agent_id == other.agent_id
    
    def __hash__(self) -> int:
        """
        Hash based on agent_id.
        
        Allows agents to be used in sets and as dict keys.
        """
        return hash(self.agent_id)