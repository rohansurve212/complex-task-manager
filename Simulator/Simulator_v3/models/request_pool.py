"""
Request Pool management for STM Simulator v3.0

This module defines the RequestPool class which manages the collection
of active requests waiting to be assigned to agents.

The RequestPool acts as a queue/cache similar to production's ElasticSearch
request cache, providing efficient filtering, sorting, and retrieval.
"""

from typing import Dict, List, Optional, Set, Callable
from datetime import datetime
from collections import defaultdict

from .request import Request, RequestState


# ============================================================================
# REQUEST POOL CLASS
# ============================================================================

class RequestPool:
    """
    Manages a pool of active requests available for assignment.
    
    The RequestPool provides efficient storage, filtering, and retrieval
    of requests. It acts as the "work queue" that routing algorithms
    pull from to assign work to agents.
    
    Key features:
    - Fast lookup by request_id (O(1))
    - Filter by skill, state, flags
    - Sort by priority
    - Track pool statistics
    - Simulate production request cache behavior
    
    Attributes:
        requests (Dict[str, Request]): All requests indexed by request_id
        
    Example:
        >>> pool = RequestPool()
        >>> pool.add_request(request1)
        >>> pool.add_request(request2)
        >>> available = pool.get_available_requests(skill_id="internet")
        >>> len(available)
        2
    """
    
    def __init__(self):
        """
        Initialize an empty request pool.
        
        Example:
            >>> pool = RequestPool()
            >>> pool.size()
            0
        """
        # Primary storage: request_id -> Request
        self._requests: Dict[str, Request] = {}
        
        # Indexes for fast filtering (optional optimization)
        self._by_skill: Dict[str, Set[str]] = defaultdict(set)  # skill_id -> set of request_ids
        self._by_state: Dict[RequestState, Set[str]] = defaultdict(set)  # state -> set of request_ids
        
        # Statistics
        self._total_added = 0
        self._total_removed = 0
        self._total_assigned = 0
    
    # ========================================================================
    # BASIC OPERATIONS - Add, Remove, Get
    # ========================================================================
    
    def add_request(self, request: Request) -> bool:
        """
        Add a request to the pool.
        
        Args:
            request: The request to add
            
        Returns:
            bool: True if added, False if already exists
            
        Example:
            >>> pool = RequestPool()
            >>> request = Request(...)
            >>> pool.add_request(request)
            True
            >>> pool.add_request(request)  # Already exists
            False
        """
        request_id = request.request_id
        
        # Check if already exists
        if request_id in self._requests:
            return False
        
        # Add to primary storage
        self._requests[request_id] = request
        
        # Update indexes
        self._by_skill[request.skill_id].add(request_id)
        self._by_state[request.state].add(request_id)
        
        # Update statistics
        self._total_added += 1
        
        return True
    
    def add_requests(self, requests: List[Request]) -> int:
        """
        Add multiple requests to the pool.
        
        Args:
            requests: List of requests to add
            
        Returns:
            int: Number of requests successfully added
            
        Example:
            >>> pool = RequestPool()
            >>> added = pool.add_requests([req1, req2, req3])
            >>> added
            3
        """
        count = 0
        for request in requests:
            if self.add_request(request):
                count += 1
        return count
    
    def remove_request(self, request_id: str) -> Optional[Request]:
        """
        Remove a request from the pool.
        
        Args:
            request_id: ID of the request to remove
            
        Returns:
            Optional[Request]: The removed request, or None if not found
            
        Example:
            >>> pool = RequestPool()
            >>> pool.add_request(request)
            >>> removed = pool.remove_request("REQ_001")
            >>> removed.request_id
            'REQ_001'
        """
        if request_id not in self._requests:
            return None
        
        # Get the request
        request = self._requests[request_id]
        
        # Remove from primary storage
        del self._requests[request_id]
        
        # Update indexes
        self._by_skill[request.skill_id].discard(request_id)
        self._by_state[request.state].discard(request_id)
        
        # Update statistics
        self._total_removed += 1
        
        return request
    
    def get_request(self, request_id: str) -> Optional[Request]:
        """
        Get a request by ID without removing it.
        
        Args:
            request_id: ID of the request
            
        Returns:
            Optional[Request]: The request, or None if not found
            
        Example:
            >>> request = pool.get_request("REQ_001")
            >>> request.skill_id
            'internet'
        """
        return self._requests.get(request_id)
    
    def contains(self, request_id: str) -> bool:
        """
        Check if pool contains a request.
        
        Args:
            request_id: ID of the request
            
        Returns:
            bool: True if request is in pool
        """
        return request_id in self._requests
    
    def size(self) -> int:
        """
        Get the total number of requests in the pool.
        
        Returns:
            int: Number of requests
            
        Example:
            >>> pool.size()
            25
        """
        return len(self._requests)
    
    def is_empty(self) -> bool:
        """
        Check if pool is empty.
        
        Returns:
            bool: True if pool has no requests
        """
        return len(self._requests) == 0
    
    def clear(self) -> int:
        """
        Remove all requests from the pool.
        
        Returns:
            int: Number of requests that were cleared
            
        Example:
            >>> count = pool.clear()
            >>> pool.is_empty()
            True
        """
        count = len(self._requests)
        self._requests.clear()
        self._by_skill.clear()
        self._by_state.clear()
        return count
    
    # ========================================================================
    # FILTERING OPERATIONS
    # ========================================================================
    
    def get_all_requests(self) -> List[Request]:
        """
        Get all requests in the pool.
        
        Returns:
            List[Request]: All requests (unordered)
            
        Example:
            >>> all_requests = pool.get_all_requests()
            >>> len(all_requests)
            100
        """
        return list(self._requests.values())
    
    def get_requests_by_skill(self, skill_id: str) -> List[Request]:
        """
        Get all requests requiring a specific skill.
        
        Uses index for O(1) lookup of request IDs, then O(n) to fetch requests.
        
        Args:
            skill_id: The skill ID to filter by
            
        Returns:
            List[Request]: Requests requiring the skill
            
        Example:
            >>> internet_requests = pool.get_requests_by_skill("internet")
            >>> all(r.skill_id == "internet" for r in internet_requests)
            True
        """
        request_ids = self._by_skill.get(skill_id, set())
        return [self._requests[rid] for rid in request_ids if rid in self._requests]
    
    def get_requests_by_state(self, state: RequestState) -> List[Request]:
        """
        Get all requests in a specific state.
        
        Args:
            state: The state to filter by
            
        Returns:
            List[Request]: Requests in the specified state
            
        Example:
            >>> new_requests = pool.get_requests_by_state(RequestState.NEW)
            >>> all(r.state == RequestState.NEW for r in new_requests)
            True
        """
        request_ids = self._by_state.get(state, set())
        return [self._requests[rid] for rid in request_ids if rid in self._requests]
    
    def get_available_requests(
        self,
        skill_id: Optional[str] = None,
        current_time: Optional[datetime] = None
    ) -> List[Request]:
        """
        Get all available (unassigned) requests, optionally filtered by skill.
        
        This is the primary method used by routing algorithms to find
        requests that can be assigned to agents.
        
        Args:
            skill_id: Optional skill filter
            current_time: Optional time for priority calculation
            
        Returns:
            List[Request]: Available requests (NEW state)
            
        Example:
            >>> # Get all available requests
            >>> available = pool.get_available_requests()
            >>> 
            >>> # Get available internet requests
            >>> internet = pool.get_available_requests(skill_id="internet")
        """
        # Start with NEW requests
        if skill_id:
            # Filter by skill first (more selective)
            skill_requests = self.get_requests_by_skill(skill_id)
            available = [r for r in skill_requests if r.state == RequestState.NEW]
        else:
            # Get all NEW requests
            available = self.get_requests_by_state(RequestState.NEW)
        
        return available
    
    def filter_requests(
        self,
        skill_id: Optional[str] = None,
        state: Optional[RequestState] = None,
        has_sla: Optional[bool] = None,
        is_escalated: Optional[bool] = None,
        is_winback: Optional[bool] = None,
        min_age_days: Optional[float] = None,
        max_age_days: Optional[float] = None,
        current_time: Optional[datetime] = None,
        sticky_agent_id: Optional[str] = None,  # NEW parameter
        custom_filter: Optional[Callable[[Request], bool]] = None
    ) -> List[Request]:
        """
        Filter requests by multiple criteria.
        
        This is a flexible filtering method that supports various filters.
        For performance, apply the most selective filters first.
        
        Args:
            skill_id: Filter by skill
            state: Filter by state
            has_sla: Filter by SLA flag
            is_escalated: Filter by escalation flag
            is_winback: Filter by winback flag
            min_age_days: Minimum age in days
            max_age_days: Maximum age in days
            current_time: Current time for age calculations
            sticky_agent_id: Filter by sticky agent assignment
            custom_filter: Custom filter function
            
        Returns:
            List[Request]: Filtered requests
            
        Example:
            >>> # Get escalated internet requests older than 5 days
            >>> requests = pool.filter_requests(
            ...     skill_id="internet",
            ...     is_escalated=True,
            ...     min_age_days=5.0,
            ...     current_time=datetime.now(timezone.utc)
            ... )
        """
        # Start with all requests or filtered subset
        if skill_id and state:
            # Both filters - use intersection
            skill_set = self._by_skill.get(skill_id, set())
            state_set = self._by_state.get(state, set())
            request_ids = skill_set & state_set
            results = [self._requests[rid] for rid in request_ids if rid in self._requests]
        elif skill_id:
            results = self.get_requests_by_skill(skill_id)
        elif state:
            results = self.get_requests_by_state(state)
        else:
            results = list(self._requests.values())
        
        # Apply flag filters
        if has_sla is not None:
            results = [r for r in results if r.has_sla == has_sla]
        
        if is_escalated is not None:
            results = [r for r in results if r.is_escalated == is_escalated]
        
        if is_winback is not None:
            results = [r for r in results if r.is_winback == is_winback]
        
        # Apply age filters
        if (min_age_days is not None or max_age_days is not None) and current_time:
            if min_age_days is not None:
                results = [r for r in results if r.get_age_days(current_time) >= min_age_days]
            if max_age_days is not None:
                results = [r for r in results if r.get_age_days(current_time) <= max_age_days]
        
        # Apply sticky agent filter
        if sticky_agent_id is not None:
            results = [r for r in results if r.sticky_agent_id == sticky_agent_id]
        
        # Apply custom filter
        if custom_filter:
            results = [r for r in results if custom_filter(r)]
        
        return results
    
    # ========================================================================
    # SORTING OPERATIONS
    # ========================================================================
    
    def sort_by_priority(
        self,
        requests: List[Request],
        current_time: datetime,
        descending: bool = True
    ) -> List[Request]:
        """
        Sort requests by priority score.
        
        Args:
            requests: List of requests to sort
            current_time: Current time for priority calculation
            descending: If True, highest priority first (default)
            
        Returns:
            List[Request]: Sorted requests
            
        Example:
            >>> available = pool.get_available_requests(skill_id="internet")
            >>> sorted_requests = pool.sort_by_priority(
            ...     available,
            ...     current_time=datetime.now(timezone.utc)
            ... )
            >>> # First request has highest priority
            >>> sorted_requests[0].calculate_priority_score(current_time)
            2.5
        """
        return sorted(
            requests,
            key=lambda r: r.calculate_priority_score(current_time),
            reverse=descending
        )
    
    def sort_by_age(
        self,
        requests: List[Request],
        current_time: datetime,
        descending: bool = True
    ) -> List[Request]:
        """
        Sort requests by age.
        
        Args:
            requests: List of requests to sort
            current_time: Current time for age calculation
            descending: If True, oldest first (default)
            
        Returns:
            List[Request]: Sorted requests
        """
        return sorted(
            requests,
            key=lambda r: r.get_age_days(current_time),
            reverse=descending
        )
    
    def sort_by_foc_target(
        self,
        requests: List[Request],
        ascending: bool = True
    ) -> List[Request]:
        """
        Sort requests by FOC target.
        
        Args:
            requests: List of requests to sort
            ascending: If True, shortest FOC target first (default)
            
        Returns:
            List[Request]: Sorted requests
        """
        return sorted(
            requests,
            key=lambda r: r.foc_target,
            reverse=not ascending
        )
    
    # ========================================================================
    # ASSIGNMENT OPERATIONS
    # ========================================================================
    
    def assign_request_to_agent(
        self,
        request_id: str,
        agent_id: str,
        assignment_time: datetime
    ) -> bool:
        """
        Assign a request to an agent.
        
        This updates the request state and indexes.
        
        Args:
            request_id: ID of the request to assign
            agent_id: ID of the agent
            assignment_time: When assignment occurs
            
        Returns:
            bool: True if successful, False if request not found
            
        Example:
            >>> pool.assign_request_to_agent(
            ...     "REQ_001",
            ...     "john.doe",
            ...     datetime.now(timezone.utc)
            ... )
            True
        """
        request = self.get_request(request_id)
        if not request:
            return False
        
        # Update indexes (remove from old state, add to new)
        self._by_state[request.state].discard(request_id)
        
        # Assign the request
        try:
            request.assign_to_agent(agent_id, assignment_time)
        except ValueError:
            # Re-add to old state index if assignment fails
            self._by_state[request.state].add(request_id)
            return False
        
        # Update state index
        self._by_state[request.state].add(request_id)
        
        # Update statistics
        self._total_assigned += 1
        
        return True
    
    def complete_request(
        self,
        request_id: str,
        completion_time: datetime
    ) -> bool:
        """
        Mark a request as completed.
        
        Args:
            request_id: ID of the request
            completion_time: When completion occurs
            
        Returns:
            bool: True if successful, False if request not found
        """
        request = self.get_request(request_id)
        if not request:
            return False
        
        # Update indexes
        self._by_state[request.state].discard(request_id)
        
        # Complete the request
        try:
            request.mark_completed(completion_time)
        except ValueError:
            # Re-add to old state index if completion fails
            self._by_state[request.state].add(request_id)
            return False
        
        # Update state index
        self._by_state[request.state].add(request_id)
        
        return True
    
    # ========================================================================
    # STATISTICS AND MONITORING
    # ========================================================================
    
    def get_statistics(self, current_time: Optional[datetime] = None) -> Dict[str, any]:
        """
        Get comprehensive pool statistics.
        
        Args:
            current_time: Current time for age/priority calculations
            
        Returns:
            Dict: Statistics dictionary
            
        Example:
            >>> stats = pool.get_statistics(datetime.now(timezone.utc))
            >>> stats['total_requests']
            100
            >>> stats['by_state']['new']
            75
            >>> stats['by_skill']['internet']
            40
        """
        stats = {
            'total_requests': self.size(),
            'total_added': self._total_added,
            'total_removed': self._total_removed,
            'total_assigned': self._total_assigned,
            'by_state': {},
            'by_skill': {},
            'flags': {
                'sla_count': 0,
                'escalated_count': 0,
                'winback_count': 0
            }
        }
        
        # Count by state
        for state, request_ids in self._by_state.items():
            stats['by_state'][state.value] = len(request_ids)
        
        # Count by skill
        for skill, request_ids in self._by_skill.items():
            stats['by_skill'][skill] = len(request_ids)
        
        # Count flags
        for request in self._requests.values():
            if request.has_sla:
                stats['flags']['sla_count'] += 1
            if request.is_escalated:
                stats['flags']['escalated_count'] += 1
            if request.is_winback:
                stats['flags']['winback_count'] += 1
        
        # Age statistics (if current_time provided)
        if current_time and self.size() > 0:
            ages = [r.get_age_days(current_time) for r in self._requests.values()]
            stats['age'] = {
                'min_days': min(ages),
                'max_days': max(ages),
                'avg_days': sum(ages) / len(ages)
            }
            
            # FOC compliance
            compliant = sum(1 for r in self._requests.values() if r.is_foc_compliant(current_time))
            stats['foc_compliance'] = {
                'compliant_count': compliant,
                'breached_count': self.size() - compliant,
                'compliance_rate': compliant / self.size() if self.size() > 0 else 0.0
            }
        
        return stats
    
    def get_skills(self) -> List[str]:
        """
        Get list of all unique skills in the pool.
        
        Returns:
            List[str]: Sorted list of skill IDs
        """
        return sorted(list(self._by_skill.keys()))
    
    def get_skill_distribution(self) -> Dict[str, int]:
        """
        Get distribution of requests by skill.
        
        Returns:
            Dict[str, int]: Mapping of skill_id to count
        """
        return {skill: len(request_ids) for skill, request_ids in self._by_skill.items()}
    
    # ========================================================================
    # BULK OPERATIONS
    # ========================================================================
    
    def snapshot(self) -> 'RequestPool':
        """
        Create a deep copy snapshot of the pool.
        
        Useful for what-if analysis or rollback scenarios.
        
        Returns:
            RequestPool: New pool with copied requests
            
        Example:
            >>> snapshot = pool.snapshot()
            >>> # Make changes to original
            >>> pool.clear()
            >>> # Snapshot is unchanged
            >>> snapshot.size()
            100
        """
        new_pool = RequestPool()
        
        # Deep copy all requests
        for request_id, request in self._requests.items():
            # Create new request from dict (deep copy)
            request_copy = Request.from_dict(request.to_dict())
            new_pool.add_request(request_copy)
        
        # Copy statistics
        new_pool._total_added = self._total_added
        new_pool._total_removed = self._total_removed
        new_pool._total_assigned = self._total_assigned
        
        return new_pool
    
    # ========================================================================
    # SPECIAL METHODS
    # ========================================================================
    
    def __len__(self) -> int:
        """Allow len(pool) syntax"""
        return self.size()
    
    def __contains__(self, request_id: str) -> bool:
        """Allow 'request_id in pool' syntax"""
        return self.contains(request_id)
    
    def __iter__(self):
        """Allow iteration over requests"""
        return iter(self._requests.values())
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"RequestPool(size={self.size()}, skills={len(self._by_skill)})"
    
    def __str__(self) -> str:
        """Human-readable string representation"""
        return f"Request Pool: {self.size()} requests across {len(self._by_skill)} skills"