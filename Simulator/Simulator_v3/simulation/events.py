"""
Event system for STM Routing Simulator v3.0.

This module defines the event-driven architecture for the simulation.
Events represent things that happen at specific times (agent becomes available,
request arrives, etc.) and are processed in chronological order.

The event queue maintains events sorted by time, allowing the simulation
to advance from one event to the next efficiently.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, field
import heapq


@dataclass(order=True)
class Event(ABC):
    """
    Base class for all simulation events.
    
    Events represent things that happen at a specific time in the simulation.
    They are comparable by timestamp to enable priority queue ordering.
    
    Attributes:
        timestamp: When the event occurs
        priority: Tie-breaker for events at same timestamp (lower = higher priority)
        event_data: The actual event data (not used for comparison)
    
    Example:
        >>> event = AgentAvailableEvent(
        ...     timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        ...     agent_id='AGENT001'
        ... )
    """
    timestamp: datetime
    priority: int = field(default=0)
    event_data: Any = field(default=None, compare=False)
    
    @abstractmethod
    def __str__(self) -> str:
        """String representation of the event."""
        pass


@dataclass(order=True)
class AgentAvailableEvent(Event):
    """
    Event triggered when an agent becomes available for work.
    
    This is the primary event type that drives the simulation.
    When an agent becomes available, the simulation:
    1. Checks for eligible requests
    2. Routes the best request to the agent
    3. Assigns the request
    4. Schedules the next availability event for that agent
    
    Attributes:
        timestamp: When the agent becomes available
        agent_id: ID of the agent (stored in event_data)
        priority: Always 0 (highest priority)
    
    Example:
        >>> event = AgentAvailableEvent(
        ...     timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        ...     agent_id='AGENT001'
        ... )
        >>> event.agent_id
        'AGENT001'
    """
    
    def __init__(self, timestamp: datetime, agent_id: str, priority: int = 0):
        """
        Create an agent available event.
        
        Args:
            timestamp: When the agent becomes available
            agent_id: ID of the agent
            priority: Event priority (default 0 = highest)
        """
        super().__init__(timestamp=timestamp, priority=priority, event_data=agent_id)
    
    @property
    def agent_id(self) -> str:
        """Get the agent ID from event data."""
        return self.event_data
    
    def __str__(self) -> str:
        """String representation."""
        return f"AgentAvailableEvent(time={self.timestamp.isoformat()}, agent={self.agent_id})"


class EventQueue:
    """
    Priority queue for managing simulation events in chronological order.
    
    Uses a min-heap to efficiently retrieve the next event to process.
    Events are ordered by timestamp, with priority as tie-breaker.
    
    This is the "clock" that drives the simulation forward in time.
    
    Attributes:
        _heap: Internal heap storing events
        _event_count: Total events added (for statistics)
    
    Example:
        >>> queue = EventQueue()
        >>> queue.add(AgentAvailableEvent(time1, 'AGENT001'))
        >>> queue.add(AgentAvailableEvent(time2, 'AGENT002'))
        >>> next_event = queue.pop()  # Gets earliest event
    """
    
    def __init__(self):
        """Initialize an empty event queue."""
        self._heap: list[Event] = []
        self._event_count = 0
    
    def add(self, event: Event) -> None:
        """
        Add an event to the queue.
        
        Events are automatically ordered by timestamp and priority.
        
        Args:
            event: The event to add
            
        Example:
            >>> queue.add(AgentAvailableEvent(
            ...     timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            ...     agent_id='AGENT001'
            ... ))
        """
        heapq.heappush(self._heap, event)
        self._event_count += 1
    
    def pop(self) -> Optional[Event]:
        """
        Remove and return the next event (earliest timestamp).
        
        Returns:
            Optional[Event]: The next event, or None if queue is empty
            
        Example:
            >>> event = queue.pop()
            >>> if event:
            ...     print(f"Processing: {event}")
        """
        if self._heap:
            return heapq.heappop(self._heap)
        return None
    
    def peek(self) -> Optional[Event]:
        """
        View the next event without removing it.
        
        Returns:
            Optional[Event]: The next event, or None if queue is empty
        """
        if self._heap:
            return self._heap[0]
        return None
    
    def is_empty(self) -> bool:
        """
        Check if the queue is empty.
        
        Returns:
            bool: True if no events in queue
        """
        return len(self._heap) == 0
    
    def size(self) -> int:
        """
        Get the number of events currently in the queue.
        
        Returns:
            int: Number of pending events
        """
        return len(self._heap)
    
    def clear(self) -> None:
        """Remove all events from the queue."""
        self._heap.clear()
    
    def total_events_processed(self) -> int:
        """
        Get the total number of events that have been added.
        
        This includes both processed and pending events.
        
        Returns:
            int: Total event count
        """
        return self._event_count
    
    def __len__(self) -> int:
        """Allow len(queue) syntax."""
        return len(self._heap)
    
    def __bool__(self) -> bool:
        """Allow if queue: syntax."""
        return len(self._heap) > 0
    
    def __str__(self) -> str:
        """String representation."""
        return f"EventQueue(size={len(self._heap)}, total_processed={self._event_count})"