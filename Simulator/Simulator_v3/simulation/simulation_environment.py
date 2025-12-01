"""
SimPy environment wrapper for STM Routing Simulator.

This module provides a wrapper around SimPy's Environment with additional
functionality for time management, state tracking, and simulation control.

Time units: SimPy time is in HOURS since simulation start.
"""

import simpy
from datetime import datetime
from typing import Optional
from enum import Enum
from simulation.time_utils import (
    simpy_time_to_datetime,
    datetime_to_simpy_time,
    get_current_datetime,
    format_simpy_time
)


class SimulationState(Enum):
    """Simulation state enumeration."""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationEnvironment:
    """
    Wrapper around SimPy Environment with time management and state tracking.
    
    This class provides:
    - SimPy environment management (time in HOURS)
    - Time conversion between SimPy time and datetime
    - Simulation state tracking
    - Convenience methods for common operations
    
    Attributes:
        env (simpy.Environment): The underlying SimPy environment
        start_datetime (datetime): Reference start datetime (Monday 8 AM EST = 13:00 UTC)
        duration_hours (float): Total simulation duration in hours (default: 50 for 5 business days)
        state (SimulationState): Current simulation state
    """
    
    def __init__(
        self,
        start_datetime: datetime,
        duration_hours: float = 50.0,
        initial_time: float = 0.0
    ):
        """
        Initialize simulation environment.
        
        Args:
            start_datetime: Reference start datetime (Monday 8 AM EST = 13:00 UTC)
            duration_hours: Simulation duration in hours (default: 50 = 5 business days × 10 hours)
            initial_time: Initial SimPy time (default: 0.0)
        """
        self.env = simpy.Environment(initial_time=initial_time)
        self.start_datetime = start_datetime
        self.duration_hours = duration_hours
        self.state = SimulationState.INITIALIZED
        
        # Track simulation progress
        self._start_real_time: Optional[datetime] = None
        self._end_real_time: Optional[datetime] = None
    
    @property
    def now(self) -> float:
        """Get current SimPy time (hours since start)."""
        return self.env.now
    
    @property
    def current_datetime(self) -> datetime:
        """Get current simulation datetime."""
        return get_current_datetime(self.env, self.start_datetime)
    
    @property
    def current_time_str(self) -> str:
        """Get current time as formatted string."""
        return format_simpy_time(self.env.now)
    
    @property
    def is_complete(self) -> bool:
        """Check if simulation has reached completion."""
        return self.env.now >= self.duration_hours
    
    @property
    def progress_percentage(self) -> float:
        """Get simulation progress as percentage (0-100)."""
        if self.duration_hours == 0:
            return 100.0
        return min(100.0, (self.env.now / self.duration_hours) * 100.0)
    
    def convert_to_datetime(self, simpy_time: float) -> datetime:
        """
        Convert SimPy time to datetime.
        
        Args:
            simpy_time: SimPy time in hours
            
        Returns:
            datetime: Corresponding datetime object
        """
        return simpy_time_to_datetime(simpy_time, self.start_datetime)
    
    def convert_from_datetime(self, dt: datetime) -> float:
        """
        Convert datetime to SimPy time.
        
        Args:
            dt: Datetime object
            
        Returns:
            float: SimPy time in hours
        """
        return datetime_to_simpy_time(dt, self.start_datetime)
    
    def timeout(self, delay: float):
        """
        Create a timeout event (convenience method).
        
        Args:
            delay: Delay in hours
            
        Returns:
            simpy.Timeout: Timeout event
        """
        return self.env.timeout(delay)
    
    def process(self, generator):
        """
        Create a process (convenience method).
        
        Args:
            generator: Generator function for the process
            
        Returns:
            simpy.Process: Process object
        """
        return self.env.process(generator)
    
    def event(self):
        """
        Create an event (convenience method).
        
        Returns:
            simpy.Event: Event object
        """
        return self.env.event()
    
    def run(self, until: Optional[float] = None):
        """
        Run the simulation.
        
        Args:
            until: Run until this SimPy time (default: duration_hours)
        """
        if self.state == SimulationState.INITIALIZED:
            self._start_real_time = datetime.now()
        
        self.state = SimulationState.RUNNING
        
        try:
            if until is None:
                until = self.duration_hours
            
            self.env.run(until=until)
            
            if self.is_complete:
                self.state = SimulationState.COMPLETED
                self._end_real_time = datetime.now()
        except Exception as e:
            self.state = SimulationState.FAILED
            self._end_real_time = datetime.now()
            raise e
    
    def peek(self) -> float:
        """
        Peek at the time of the next scheduled event.
        
        Returns:
            float: Time of next event, or infinity if no events scheduled
        """
        return self.env.peek()
    
    def get_statistics(self) -> dict:
        """
        Get simulation statistics.
        
        Returns:
            dict: Dictionary with simulation statistics
        """
        stats = {
            'current_time': self.env.now,
            'current_datetime': self.current_datetime.isoformat(),
            'current_time_str': self.current_time_str,
            'duration_hours': self.duration_hours,
            'progress_percentage': self.progress_percentage,
            'state': self.state.value,
            'is_complete': self.is_complete
        }
        
        if self._start_real_time:
            stats['start_real_time'] = self._start_real_time.isoformat()
        
        if self._end_real_time:
            stats['end_real_time'] = self._end_real_time.isoformat()
            stats['real_time_duration_seconds'] = (
                self._end_real_time - self._start_real_time
            ).total_seconds()
        
        return stats
    
    def __repr__(self) -> str:
        """String representation of simulation environment."""
        return (
            f"SimulationEnvironment("
            f"now={self.env.now:.2f}h, "
            f"state={self.state.value}, "
            f"progress={self.progress_percentage:.1f}%)"
        )