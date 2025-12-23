"""
Unit tests for event system.

Tests cover:
- Event base class behavior
- AgentAvailableEvent functionality
- EventQueue operations and ordering
- Time-based sorting
- Priority tie-breaking
- Edge cases
"""

import pytest
from datetime import datetime, timezone, timedelta
from simulation.events import AgentAvailableEvent, EventQueue


@pytest.fixture
def base_time():
    """Base timestamp for tests."""
    return datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


# ============================================================================
# Test AgentAvailableEvent
# ============================================================================

def test_agent_available_event_creation(base_time):
    """Test creating an AgentAvailableEvent."""
    event = AgentAvailableEvent(
        timestamp=base_time,
        agent_id='AGENT001'
    )
    
    assert event.timestamp == base_time
    assert event.agent_id == 'AGENT001'
    assert event.priority == 0


def test_agent_available_event_custom_priority(base_time):
    """Test creating an AgentAvailableEvent with custom priority."""
    event = AgentAvailableEvent(
        timestamp=base_time,
        agent_id='AGENT001',
        priority=5
    )
    
    assert event.priority == 5


def test_agent_available_event_str_representation(base_time):
    """Test string representation of AgentAvailableEvent."""
    event = AgentAvailableEvent(
        timestamp=base_time,
        agent_id='AGENT001'
    )
    
    str_repr = str(event)
    assert 'AgentAvailableEvent' in str_repr
    assert 'AGENT001' in str_repr
    assert '2024-01-15' in str_repr


def test_agent_available_event_comparison_by_time(base_time):
    """Test that events are compared by timestamp."""
    event1 = AgentAvailableEvent(
        timestamp=base_time,
        agent_id='AGENT001'
    )
    event2 = AgentAvailableEvent(
        timestamp=base_time + timedelta(hours=1),
        agent_id='AGENT002'
    )
    
    # Earlier event should be "less than" later event
    assert event1 < event2
    assert event2 > event1


def test_agent_available_event_comparison_by_priority(base_time):
    """Test that events with same timestamp are compared by priority."""
    event1 = AgentAvailableEvent(
        timestamp=base_time,
        agent_id='AGENT001',
        priority=0
    )
    event2 = AgentAvailableEvent(
        timestamp=base_time,
        agent_id='AGENT002',
        priority=1
    )
    
    # Lower priority value means higher priority (comes first)
    assert event1 < event2
    assert event2 > event1


def test_agent_available_event_equality(base_time):
    """Test event equality (same time and priority)."""
    event1 = AgentAvailableEvent(
        timestamp=base_time,
        agent_id='AGENT001',
        priority=0
    )
    event2 = AgentAvailableEvent(
        timestamp=base_time,
        agent_id='AGENT002',  # Different agent
        priority=0
    )
    
    # Events with same timestamp and priority are equal for sorting
    # (even though agent_id is different - it's in event_data which doesn't compare)
    assert event1 == event2


# ============================================================================
# Test EventQueue - Basic Operations
# ============================================================================

def test_event_queue_creation():
    """Test creating an empty event queue."""
    queue = EventQueue()
    
    assert queue.is_empty()
    assert queue.size() == 0
    assert len(queue) == 0


def test_event_queue_add_single_event(base_time):
    """Test adding a single event to queue."""
    queue = EventQueue()
    event = AgentAvailableEvent(base_time, 'AGENT001')
    
    queue.add(event)
    
    assert not queue.is_empty()
    assert queue.size() == 1
    assert len(queue) == 1


def test_event_queue_add_multiple_events(base_time):
    """Test adding multiple events to queue."""
    queue = EventQueue()
    
    for i in range(5):
        event = AgentAvailableEvent(
            timestamp=base_time + timedelta(hours=i),
            agent_id=f'AGENT{i:03d}'
        )
        queue.add(event)
    
    assert queue.size() == 5


def test_event_queue_pop_single_event(base_time):
    """Test popping a single event from queue."""
    queue = EventQueue()
    event = AgentAvailableEvent(base_time, 'AGENT001')
    queue.add(event)
    
    popped = queue.pop()
    
    assert popped is not None
    assert popped.agent_id == 'AGENT001'
    assert queue.is_empty()


def test_event_queue_pop_from_empty():
    """Test popping from empty queue returns None."""
    queue = EventQueue()
    
    popped = queue.pop()
    
    assert popped is None


def test_event_queue_peek_without_removing(base_time):
    """Test peeking at next event without removing it."""
    queue = EventQueue()
    event = AgentAvailableEvent(base_time, 'AGENT001')
    queue.add(event)
    
    peeked = queue.peek()
    
    assert peeked is not None
    assert peeked.agent_id == 'AGENT001'
    assert queue.size() == 1  # Event still in queue


def test_event_queue_peek_from_empty():
    """Test peeking at empty queue returns None."""
    queue = EventQueue()
    
    peeked = queue.peek()
    
    assert peeked is None


# ============================================================================
# Test EventQueue - Time-Based Ordering
# ============================================================================

def test_event_queue_orders_by_time(base_time):
    """Test that events are popped in chronological order."""
    queue = EventQueue()
    
    # Add events out of order
    times = [
        base_time + timedelta(hours=3),
        base_time + timedelta(hours=1),
        base_time + timedelta(hours=5),
        base_time + timedelta(hours=2),
        base_time + timedelta(hours=4)
    ]
    
    for i, time in enumerate(times):
        event = AgentAvailableEvent(time, f'AGENT{i:03d}')
        queue.add(event)
    
    # Pop events - should come out in chronological order
    prev_time = None
    while not queue.is_empty():
        event = queue.pop()
        if prev_time:
            assert event.timestamp >= prev_time
        prev_time = event.timestamp


def test_event_queue_earliest_event_first(base_time):
    """Test that earliest event is always popped first."""
    queue = EventQueue()
    
    # Add events in reverse chronological order
    for i in range(10, 0, -1):
        event = AgentAvailableEvent(
            timestamp=base_time + timedelta(hours=i),
            agent_id=f'AGENT{i:03d}'
        )
        queue.add(event)
    
    # First pop should be the earliest (hour 1)
    first = queue.pop()
    assert first.timestamp == base_time + timedelta(hours=1)


def test_event_queue_handles_same_timestamp(base_time):
    """Test that queue handles multiple events at same timestamp."""
    queue = EventQueue()
    
    # Add 5 events at the same time
    for i in range(5):
        event = AgentAvailableEvent(
            timestamp=base_time,
            agent_id=f'AGENT{i:03d}'
        )
        queue.add(event)
    
    # All should be poppable
    for i in range(5):
        event = queue.pop()
        assert event is not None
        assert event.timestamp == base_time
    
    assert queue.is_empty()


# ============================================================================
# Test EventQueue - Priority Ordering
# ============================================================================

def test_event_queue_priority_tiebreaker(base_time):
    """Test that priority breaks ties when timestamps are equal."""
    queue = EventQueue()
    
    # Add events at same time with different priorities
    priorities = [5, 2, 8, 1, 3]
    for priority in priorities:
        event = AgentAvailableEvent(
            timestamp=base_time,
            agent_id=f'AGENT_P{priority}',
            priority=priority
        )
        queue.add(event)
    
    # Should pop in priority order (lowest priority value first)
    prev_priority = -1
    while not queue.is_empty():
        event = queue.pop()
        assert event.priority >= prev_priority
        prev_priority = event.priority


def test_event_queue_time_takes_precedence_over_priority(base_time):
    """Test that time ordering takes precedence over priority."""
    queue = EventQueue()
    
    # Add low-priority event at early time
    early_event = AgentAvailableEvent(
        timestamp=base_time,
        agent_id='EARLY',
        priority=100  # Very low priority
    )
    
    # Add high-priority event at later time
    late_event = AgentAvailableEvent(
        timestamp=base_time + timedelta(hours=1),
        agent_id='LATE',
        priority=0  # High priority
    )
    
    queue.add(late_event)
    queue.add(early_event)
    
    # Early event should pop first, despite lower priority
    first = queue.pop()
    assert first.agent_id == 'EARLY'


# ============================================================================
# Test EventQueue - Statistics and Utilities
# ============================================================================

def test_event_queue_total_events_processed(base_time):
    """Test that total events processed is tracked correctly."""
    queue = EventQueue()
    
    # Add 10 events
    for i in range(10):
        event = AgentAvailableEvent(base_time + timedelta(hours=i), f'AGENT{i:03d}')
        queue.add(event)
    
    assert queue.total_events_processed() == 10
    
    # Pop 5 events
    for _ in range(5):
        queue.pop()
    
    # Total should still be 10 (counts all added, not just remaining)
    assert queue.total_events_processed() == 10
    assert queue.size() == 5


def test_event_queue_clear(base_time):
    """Test clearing all events from queue."""
    queue = EventQueue()
    
    # Add events
    for i in range(5):
        event = AgentAvailableEvent(base_time + timedelta(hours=i), f'AGENT{i:03d}')
        queue.add(event)
    
    assert queue.size() == 5
    
    queue.clear()
    
    assert queue.is_empty()
    assert queue.size() == 0


def test_event_queue_bool_conversion():
    """Test that queue can be used in boolean context."""
    queue = EventQueue()
    
    # Empty queue is falsy
    assert not queue
    
    # Non-empty queue is truthy
    queue.add(AgentAvailableEvent(datetime.now(timezone.utc), 'AGENT001'))
    assert queue


def test_event_queue_str_representation(base_time):
    """Test string representation of queue."""
    queue = EventQueue()
    
    for i in range(3):
        queue.add(AgentAvailableEvent(base_time + timedelta(hours=i), f'AGENT{i:03d}'))
    
    str_repr = str(queue)
    assert 'EventQueue' in str_repr
    assert 'size=3' in str_repr


# ============================================================================
# Test EventQueue - Edge Cases
# ============================================================================

def test_event_queue_large_number_of_events(base_time):
    """Test queue performance with large number of events."""
    queue = EventQueue()
    
    # Add 1000 events in random order
    import random
    hours = list(range(1000))
    random.shuffle(hours)
    
    for hour in hours:
        event = AgentAvailableEvent(
            timestamp=base_time + timedelta(hours=hour),
            agent_id=f'AGENT{hour:04d}'
        )
        queue.add(event)
    
    assert queue.size() == 1000
    
    # Verify they come out in chronological order
    prev_hour = -1
    count = 0
    while not queue.is_empty():
        event = queue.pop()
        hour = (event.timestamp - base_time).total_seconds() / 3600
        assert hour > prev_hour
        prev_hour = hour
        count += 1
    
    assert count == 1000


def test_event_queue_interleaved_add_pop(base_time):
    """Test adding and popping events in interleaved fashion."""
    queue = EventQueue()
    
    # Add 3 events
    for i in range(3):
        queue.add(AgentAvailableEvent(base_time + timedelta(hours=i), f'AGENT{i:03d}'))
    
    # Pop 2
    queue.pop()
    queue.pop()
    
    assert queue.size() == 1
    
    # Add 2 more
    for i in range(3, 5):
        queue.add(AgentAvailableEvent(base_time + timedelta(hours=i), f'AGENT{i:03d}'))
    
    assert queue.size() == 3
    
    # Verify ordering still works
    prev_time = None
    while not queue.is_empty():
        event = queue.pop()
        if prev_time:
            assert event.timestamp >= prev_time
        prev_time = event.timestamp


def test_event_queue_identical_events(base_time):
    """Test queue with multiple identical events."""
    queue = EventQueue()
    
    # Add 5 identical events (same time, priority, agent)
    for _ in range(5):
        event = AgentAvailableEvent(
            timestamp=base_time,
            agent_id='AGENT001',
            priority=0
        )
        queue.add(event)
    
    # All should be retrievable
    assert queue.size() == 5
    
    for _ in range(5):
        event = queue.pop()
        assert event is not None
        assert event.agent_id == 'AGENT001'
    
    assert queue.is_empty()


def test_event_queue_microsecond_precision(base_time):
    """Test that queue handles microsecond-level time differences."""
    queue = EventQueue()
    
    # Add events 1 microsecond apart
    for i in range(5):
        event = AgentAvailableEvent(
            timestamp=base_time + timedelta(microseconds=i),
            agent_id=f'AGENT{i:03d}'
        )
        queue.add(event)
    
    # Should maintain ordering
    for i in range(5):
        event = queue.pop()
        expected_time = base_time + timedelta(microseconds=i)
        assert event.timestamp == expected_time


# ============================================================================
# Test Event System Integration
# ============================================================================

def test_event_queue_maintains_heap_property(base_time):
    """Test that internal heap property is maintained after operations."""
    queue = EventQueue()
    
    # Add many events in random order
    import random
    times = [base_time + timedelta(hours=i) for i in range(100)]
    random.shuffle(times)
    
    for i, time in enumerate(times):
        queue.add(AgentAvailableEvent(time, f'AGENT{i:03d}'))
    
    # Pop all and verify chronological order
    prev_time = None
    while not queue.is_empty():
        event = queue.pop()
        if prev_time:
            assert event.timestamp >= prev_time, \
                f"Heap property violated: {event.timestamp} came after {prev_time}"
        prev_time = event.timestamp


def test_multiple_event_types_in_queue(base_time):
    """Test queue with different event priorities."""
    queue = EventQueue()
    
    # Add events with different priorities at same time
    for priority in [0, 5, 2, 8, 1]:
        event = AgentAvailableEvent(
            timestamp=base_time,
            agent_id=f'AGENT_P{priority}',
            priority=priority
        )
        queue.add(event)
    
    # Add events at different times
    for hour in [1, 3, 2]:
        event = AgentAvailableEvent(
            timestamp=base_time + timedelta(hours=hour),
            agent_id=f'AGENT_H{hour}',
            priority=0
        )
        queue.add(event)
    
    # All base_time events should come first (sorted by priority)
    # Then time-ordered events
    
    # First 5 should all be at base_time
    for i in range(5):
        event = queue.pop()
        assert event.timestamp == base_time
    
    # Next 3 should be time-ordered
    event1 = queue.pop()
    event2 = queue.pop()
    event3 = queue.pop()
    
    assert event1.timestamp < event2.timestamp < event3.timestamp
    assert queue.is_empty()


def test_event_queue_stress_test(base_time):
    """Stress test with many operations."""
    queue = EventQueue()
    import random
    
    # Add 500 random events
    for i in range(500):
        event = AgentAvailableEvent(
            timestamp=base_time + timedelta(seconds=random.randint(0, 10000)),
            agent_id=f'AGENT{i:04d}',
            priority=random.randint(0, 10)
        )
        queue.add(event)
    
    # Pop half
    for _ in range(250):
        queue.pop()
    
    # Add 250 more
    for i in range(500, 750):
        event = AgentAvailableEvent(
            timestamp=base_time + timedelta(seconds=random.randint(0, 10000)),
            agent_id=f'AGENT{i:04d}',
            priority=random.randint(0, 10)
        )
        queue.add(event)
    
    # Verify all remaining events maintain ordering
    prev_time = None
    prev_priority = None
    count = 0
    
    while not queue.is_empty():
        event = queue.pop()
        
        if prev_time:
            if event.timestamp == prev_time:
                # Same time - check priority
                if prev_priority is not None:
                    assert event.priority >= prev_priority
            else:
                # Different time - must be later or equal
                assert event.timestamp >= prev_time
        
        prev_time = event.timestamp
        prev_priority = event.priority
        count += 1
    
    assert count == 500  # 500 - 250 + 250