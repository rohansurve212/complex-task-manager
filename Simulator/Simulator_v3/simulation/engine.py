"""
Simulation Engine for STM Routing Simulator v3.0.

This module implements the core simulation engine that orchestrates the entire
simulation by managing time progression, event processing, agent availability,
request routing, and assignment tracking.

The engine is the "conductor" that brings together all components:
- Event queue for time management
- Agent pool for availability tracking
- Request pool for work queue
- Production filtering for request selection
- Routing logic for prioritization
- Assignment tracking for statistics

Example usage:
    >>> from simulation.engine import SimulationEngine
    >>> 
    >>> engine = SimulationEngine(
    ...     agents=agent_list,
    ...     requests=request_list,
    ...     config=routing_config,
    ...     start_time=start_time
    ... )
    >>> 
    >>> engine.run()
    >>> stats = engine.get_statistics()
"""

from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
import logging

from models.agent import Agent
from models.request import Request, RequestState
from models.request_pool import RequestPool
from config.scenario_config import RoutingConfig
from simulation.events import EventQueue, AgentAvailableEvent
from simulation.production_filtering import filter_production_requests
from simulation.routing import route_request_to_agent


# Configure logging
logger = logging.getLogger(__name__)


class SimulationEngine:
    """
    Core simulation engine that orchestrates the STM routing simulation.
    
    The engine manages:
    1. Time progression through event processing
    2. Agent availability and work assignment
    3. Request pool and filtering
    4. Routing decisions and assignments
    5. Statistics and state tracking
    
    Architecture:
    - Event-driven: Processes events in chronological order
    - Agent-initiated: Agents request work when available
    - Production-accurate: Uses production filtering and routing logic
    
    Attributes:
        current_time: Current simulation time
        event_queue: Priority queue of pending events
        request_pool: Pool of active requests
        agents: Dictionary of agents by ID
        config: Routing configuration
        
    Example:
        >>> engine = SimulationEngine(
        ...     agents=agents,
        ...     requests=requests,
        ...     config=config,
        ...     start_time=datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        ... )
        >>> 
        >>> # Run simulation
        >>> engine.run(max_events=1000)
        >>> 
        >>> # Get results
        >>> stats = engine.get_statistics()
        >>> print(f"Assignments: {stats['total_assignments']}")
    """
    
    def __init__(
        self,
        agents: List[Agent],
        requests: List[Request],
        config: RoutingConfig,
        start_time: datetime
    ):
        """
        Initialize the simulation engine.
        
        Args:
            agents: List of agents to simulate
            requests: List of requests to process
            config: Routing configuration
            start_time: Simulation start time
            
        Example:
            >>> engine = SimulationEngine(
            ...     agents=[agent1, agent2, agent3],
            ...     requests=[req1, req2, req3, ...],
            ...     config=RoutingConfig(pilot_program_enabled=True),
            ...     start_time=datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
            ... )
        """
        # Time management
        self.start_time = start_time
        self.current_time = start_time
        self.end_time: Optional[datetime] = None
        
        # Event system
        self.event_queue = EventQueue()
        
        # Agent management
        self.agents: Dict[str, Agent] = {agent.agent_id: agent for agent in agents}
        self.available_agents: Set[str] = set()  # Currently available agent IDs
        self.busy_agents: Set[str] = set()  # Currently busy agent IDs
        
        # Request management
        self.request_pool = RequestPool()
        self.request_pool.add_requests(requests)
        
        # Configuration
        self.config = config
        
        # Assignment tracking
        self.assignments: List[Dict] = []  # History of all assignments
        self.active_assignments: Dict[str, Dict] = {}  # agent_id -> assignment details
        self.completed_assignments: List[Dict] = []  # History of completed assignments
        
        # Statistics
        self.total_events_processed = 0
        self.total_assignments = 0
        self.total_completions = 0
        self.routing_decisions: List[Dict] = []  # Track routing decisions for analysis
        
        # Initialize simulation
        self._initialize_agents()
        
        logger.info(f"SimulationEngine initialized: {len(agents)} agents, "
                   f"{len(requests)} requests, start_time={start_time}")
    
    def _initialize_agents(self) -> None:
        """
        Initialize all agents and schedule their first availability events.
        
        All agents start as available at the simulation start time.
        This creates the initial events that drive the simulation.
        
        Note: Agent state is managed internally by the Agent class.
        We only track availability in the engine's available_agents set.
        """
        for agent_id, agent in self.agents.items():
            # Mark agent as available in engine tracking
            self.available_agents.add(agent_id)
            
            # Schedule immediate availability event
            event = AgentAvailableEvent(
                timestamp=self.start_time,
                agent_id=agent_id
            )
            self.event_queue.add(event)
            
        logger.info(f"Initialized {len(self.agents)} agents with availability events")
    
    def run(
        self,
        max_events: Optional[int] = None,
        max_time: Optional[datetime] = None,
        stop_when_idle: bool = True
    ) -> None:
        """
        Run the simulation until completion.
        
        The simulation processes events in chronological order until:
        - max_events is reached, OR
        - max_time is reached, OR
        - stop_when_idle=True and all agents are idle with no pending work
        
        Args:
            max_events: Maximum number of events to process (None = unlimited)
            max_time: Maximum simulation time (None = unlimited)
            stop_when_idle: Stop when all agents idle and no pending requests
            
        Example:
            >>> # Run until all work completed
            >>> engine.run(stop_when_idle=True)
            >>> 
            >>> # Run for specific duration
            >>> engine.run(max_time=start_time + timedelta(hours=8))
            >>> 
            >>> # Run limited number of events
            >>> engine.run(max_events=1000)
        """
        logger.info("Starting simulation run")
        
        events_processed = 0
        
        while not self.event_queue.is_empty():
            # Check stopping conditions
            if max_events and events_processed >= max_events:
                logger.info(f"Reached max_events limit: {max_events}")
                break
            
            # Get next event
            event = self.event_queue.pop()
            if event is None:
                break
            
            # Check time limit
            if max_time and event.timestamp > max_time:
                logger.info(f"Reached max_time: {max_time}")
                break
            
            # Advance simulation time
            self.current_time = event.timestamp
            
            # Process event
            self._process_event(event)
            events_processed += 1
            self.total_events_processed += 1
            
            # Check idle condition
            if stop_when_idle and self._is_simulation_idle():
                logger.info("Simulation idle: all agents available, no pending requests")
                break
            
            # Periodic logging
            if events_processed % 100 == 0:
                logger.debug(f"Processed {events_processed} events, "
                           f"time={self.current_time.isoformat()}")
        
        self.end_time = self.current_time
        logger.info(f"Simulation completed: processed {events_processed} events, "
                   f"duration={self.end_time - self.start_time}")
    
    def _process_event(self, event: AgentAvailableEvent) -> None:
        """
        Process a single event.
        
        Currently only handles AgentAvailableEvent:
        1. Get the agent
        2. Filter eligible requests
        3. Route to find best request
        4. Assign if found
        5. Schedule next availability (if assigned)
        
        Args:
            event: The event to process
        """
        if isinstance(event, AgentAvailableEvent):
            self._handle_agent_available(event)
        else:
            logger.warning(f"Unknown event type: {type(event)}")
    
    def _handle_agent_available(self, event: AgentAvailableEvent) -> None:
        """
        Handle an agent becoming available for work.
        
        This is the core of the simulation:
        1. Get absent agents (for CMO filtering)
        2. Filter eligible requests using production filtering
        3. Route to select best request
        4. Assign request to agent
        5. Schedule next availability event
        
        Args:
            event: The agent availability event
        """
        agent_id = event.agent_id
        agent = self.agents.get(agent_id)
        
        if not agent:
            logger.error(f"Agent not found: {agent_id}")
            return
        
        # Mark agent as available in engine tracking
        self.available_agents.add(agent_id)
        self.busy_agents.discard(agent_id)
        
        # Get absent agents for CMO filtering
        absent_agent_ids = self._get_absent_agent_ids()
        
        # Step 1: Production filtering
        filtered_requests = filter_production_requests(
            pool=self.request_pool,
            agent=agent,
            current_time=self.current_time,
            absent_agent_ids=absent_agent_ids,
            routing_config=self.config
        )
        
        # Step 2: Routing
        selected_request = route_request_to_agent(
            filtered_requests=filtered_requests,
            current_time=self.current_time
        )
        
        # Track routing decision
        self.routing_decisions.append({
            'timestamp': self.current_time,
            'agent_id': agent_id,
            'filtered_count': len(filtered_requests),
            'selected_request_id': selected_request.request_id if selected_request else None,
            'was_followup': getattr(selected_request, 'is_followup', None) if selected_request else None
        })
        
        # Step 3: Assignment
        if selected_request:
            self._assign_request_to_agent(agent, selected_request)
        else:
            # No work available - agent remains idle
            logger.debug(f"No work available for agent {agent_id} at {self.current_time}")
    
    def _assign_request_to_agent(self, agent: Agent, request: Request) -> None:
        """
        Assign a request to an agent.
        
        This:
        1. Updates request state to ASSIGNED
        2. Marks agent as busy in engine tracking
        3. Records the assignment
        4. Schedules the agent's next availability
        
        Args:
            agent: The agent receiving the assignment
            request: The request being assigned
        """
        # Assign in request pool
        success = self.request_pool.assign_request_to_agent(
            request_id=request.request_id,
            agent_id=agent.agent_id,
            assignment_time=self.current_time
        )
        
        if not success:
            logger.error(f"Failed to assign request {request.request_id} to agent {agent.agent_id}")
            return
        
        # Update engine's agent tracking (not agent's internal state)
        self.available_agents.discard(agent.agent_id)
        self.busy_agents.add(agent.agent_id)
        
        # Calculate completion time (use FOC target)
        completion_time = self._calculate_completion_time(request)
        
        # Record assignment
        assignment = {
            'assignment_id': f"ASSIGN_{self.total_assignments}",
            'timestamp': self.current_time,
            'agent_id': agent.agent_id,
            'request_id': request.request_id,
            'completion_time': completion_time,
            'was_followup': getattr(request, 'is_followup', False),
            'from_absent_agent': getattr(request, 'from_absent_agent', False),
            'priority_level': self._get_priority_level(request)
        }
        
        self.assignments.append(assignment)
        self.active_assignments[agent.agent_id] = assignment
        self.total_assignments += 1
        
        # Schedule agent's next availability (when they complete this request)
        next_event = AgentAvailableEvent(
            timestamp=completion_time,
            agent_id=agent.agent_id
        )
        self.event_queue.add(next_event)
        
        logger.info(f"Assigned {request.request_id} to {agent.agent_id}, "
                   f"completion={completion_time.isoformat()}")
    
    def _calculate_completion_time(self, request: Request) -> datetime:
        """
        Calculate when a request will be completed.
        
        For now, uses FOC target as estimated completion time.
        Future: Could add variability, skill-based multipliers, etc.
        
        Args:
            request: The request being worked on
            
        Returns:
            datetime: Expected completion time
        """
        # Use FOC target (in days) as completion time estimate
        if request.foc_target and request.foc_target > 0:
            completion_delta = timedelta(days=request.foc_target)
        else:
            # Default: 7 days
            completion_delta = timedelta(days=7.0)
        
        return self.current_time + completion_delta
    
    def _get_priority_level(self, request: Request) -> int:
        """
        Determine priority level of a request (1-5).
        
        Matches the 5-level priority system from production_filtering.
        
        Args:
            request: The request
            
        Returns:
            int: Priority level (1=highest, 5=lowest)
        """
        # Priority 1: (winback OR atl_rf) AND escalated
        if (request.is_winback or request.is_atl_rf) and request.is_escalated:
            return 1
        
        # Priority 2: (winback OR atl_rf) AND NOT escalated
        if (request.is_winback or request.is_atl_rf) and not request.is_escalated:
            return 2
        
        # Priority 3: has_sla AND escalated
        if request.has_sla and request.is_escalated:
            return 3
        
        # Priority 4: NOT has_sla AND escalated
        if not request.has_sla and request.is_escalated:
            return 4
        
        # Priority 5: NOT escalated (commons)
        return 5
    
    def _get_absent_agent_ids(self) -> Set[str]:
        """
        Get set of currently absent agent IDs.
        
        For now, uses Agent.is_absent flag.
        Future: Could track absences dynamically during simulation.
        
        Returns:
            Set[str]: Agent IDs of absent agents
        """
        return {
            agent_id for agent_id, agent in self.agents.items()
            if agent.is_absent
        }
    
    def _is_simulation_idle(self) -> bool:
        """
        Check if simulation is idle (no pending work).
        
        Simulation is idle when:
        - All agents are available (none busy), AND
        - Either:
        - No pending requests in pool, OR
        - Event queue is empty (no more events to process)
        
        Returns:
            bool: True if simulation is idle
        """
        # If event queue is empty and no agents are busy, we're done
        # (even if there are unassignable requests remaining)
        if self.event_queue.is_empty() and not self.busy_agents:
            return True
        
        # Check if any agents are busy
        if self.busy_agents:
            return False
        
        # Check if any requests are pending
        pending_requests = self.request_pool.get_requests_by_state(RequestState.NEW)
        if pending_requests:
            return False
        
        return True
    
    def get_statistics(self) -> Dict:
        """
        Get comprehensive simulation statistics.
        
        Returns:
            Dict: Statistics including:
                - Timing: start, end, duration
                - Events: total processed
                - Assignments: total, by priority, by type
                - Agents: utilization, assignments per agent
                - Requests: total, assigned, pending, by state
                - Routing: decisions, success rate
                
        Example:
            >>> stats = engine.get_statistics()
            >>> print(f"Total assignments: {stats['assignments']['total']}")
            >>> print(f"Average per agent: {stats['agents']['avg_assignments_per_agent']:.2f}")
        """
        duration = (self.end_time - self.start_time) if self.end_time else timedelta(0)
        
        # Calculate agent utilization
        agent_stats = self._calculate_agent_statistics()
        
        # Calculate request statistics
        request_stats = self._calculate_request_statistics()
        
        # Calculate routing statistics
        routing_stats = self._calculate_routing_statistics()
        
        stats = {
            'timing': {
                'start_time': self.start_time,
                'end_time': self.end_time,
                'duration_seconds': duration.total_seconds(),
                'duration_hours': duration.total_seconds() / 3600.0
            },
            'events': {
                'total_processed': self.total_events_processed
            },
            'assignments': {
                'total': self.total_assignments,
                'by_priority': self._count_by_priority(),
                'followup_count': sum(1 for a in self.assignments if a['was_followup']),
                'cmo_count': sum(1 for a in self.assignments if not a['was_followup']),
                'from_absent_agent_count': sum(1 for a in self.assignments if a['from_absent_agent'])
            },
            'agents': agent_stats,
            'requests': request_stats,
            'routing': routing_stats
        }
        
        return stats
    
    def _calculate_agent_statistics(self) -> Dict:
        """Calculate agent-related statistics."""
        assignments_per_agent = {}
        for assignment in self.assignments:
            agent_id = assignment['agent_id']
            assignments_per_agent[agent_id] = assignments_per_agent.get(agent_id, 0) + 1
        
        total_agents = len(self.agents)
        agents_with_work = len(assignments_per_agent)
        
        return {
            'total_agents': total_agents,
            'agents_with_assignments': agents_with_work,
            'agents_without_assignments': total_agents - agents_with_work,
            'avg_assignments_per_agent': self.total_assignments / total_agents if total_agents > 0 else 0,
            'max_assignments_per_agent': max(assignments_per_agent.values()) if assignments_per_agent else 0,
            'min_assignments_per_agent': min(assignments_per_agent.values()) if assignments_per_agent else 0,
            'assignments_per_agent': assignments_per_agent
        }
    
    def _calculate_request_statistics(self) -> Dict:
        """Calculate request-related statistics."""
        pool_stats = self.request_pool.get_statistics(self.current_time)
        
        return {
            'total_requests': self.request_pool.size(),
            'assigned_requests': self.total_assignments,
            'pending_requests': pool_stats['by_state'].get('new', 0),
            'pool_statistics': pool_stats
        }
    
    def _calculate_routing_statistics(self) -> Dict:
        """Calculate routing-related statistics."""
        total_decisions = len(self.routing_decisions)
        successful_routings = sum(1 for d in self.routing_decisions if d['selected_request_id'] is not None)
        
        return {
            'total_decisions': total_decisions,
            'successful_routings': successful_routings,
            'failed_routings': total_decisions - successful_routings,
            'success_rate': successful_routings / total_decisions if total_decisions > 0 else 0,
            'avg_filtered_per_decision': sum(d['filtered_count'] for d in self.routing_decisions) / total_decisions if total_decisions > 0 else 0
        }
    
    def _count_by_priority(self) -> Dict[int, int]:
        """Count assignments by priority level."""
        counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for assignment in self.assignments:
            priority = assignment['priority_level']
            counts[priority] = counts.get(priority, 0) + 1
        return counts
    
    def get_assignments(self) -> List[Dict]:
        """
        Get list of all assignments made during simulation.
        
        Returns:
            List[Dict]: Assignment records
        """
        return self.assignments.copy()
    
    def get_routing_decisions(self) -> List[Dict]:
        """
        Get list of all routing decisions made during simulation.
        
        Returns:
            List[Dict]: Routing decision records
        """
        return self.routing_decisions.copy()
    
    def reset(self) -> None:
        """
        Reset the simulation to initial state.
        
        Clears all assignments, resets time, and reinitializes agents.
        Useful for running multiple simulation scenarios.
        """
        # Reset time
        self.current_time = self.start_time
        self.end_time = None
        
        # Clear event queue
        self.event_queue.clear()
        
        # Reset agent tracking (not agent internal state)
        self.available_agents.clear()
        self.busy_agents.clear()
        
        # Clear tracking
        self.assignments.clear()
        self.active_assignments.clear()
        self.completed_assignments.clear()
        self.routing_decisions.clear()
        
        # Reset statistics
        self.total_events_processed = 0
        self.total_assignments = 0
        self.total_completions = 0
        
        # Reinitialize
        self._initialize_agents()
        
        logger.info("Simulation reset to initial state")
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"SimulationEngine(agents={len(self.agents)}, "
                f"requests={self.request_pool.size()}, "
                f"time={self.current_time.isoformat()})")