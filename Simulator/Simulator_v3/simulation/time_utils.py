"""
Time conversion utilities for SimPy simulation.

This module provides functions to convert between SimPy's numeric time (hours since start)
and Python datetime objects for realistic time-based logic.

Convention:
- SimPy time: Hours since simulation start (float)
- Reference datetime: Start datetime (e.g., Monday 8 AM EST = 13:00 UTC)
- Simulation runs for 50 hours (5 business days × 10 hours/day)
- Business hours: 8 AM - 6 PM EST daily (Monday-Friday)
- Each SimPy "day" is 10 hours (not 24)
"""

from datetime import datetime, timedelta
from typing import Optional
import simpy


def simpy_time_to_datetime(simpy_time: float, start_datetime: datetime) -> datetime:
    """
    Convert SimPy time (hours since start) to datetime object.
    
    Args:
        simpy_time: Hours since simulation start
        start_datetime: Reference start datetime
        
    Returns:
        datetime: Corresponding datetime object
        
    Example:
        >>> start = datetime(2024, 1, 15, 0, 0, 0)  # Monday midnight
        >>> simpy_time_to_datetime(24.5, start)
        datetime(2024, 1, 16, 0, 30, 0)  # Tuesday 00:30
    """
    hours = int(simpy_time)
    minutes = int((simpy_time - hours) * 60)
    seconds = int(((simpy_time - hours) * 60 - minutes) * 60)
    
    return start_datetime + timedelta(hours=hours, minutes=minutes, seconds=seconds)


def datetime_to_simpy_time(dt: datetime, start_datetime: datetime) -> float:
    """
    Convert datetime object to SimPy time (hours since start).
    
    Args:
        dt: Target datetime
        start_datetime: Reference start datetime
        
    Returns:
        float: Hours since simulation start
        
    Example:
        >>> start = datetime(2024, 1, 15, 0, 0, 0)
        >>> target = datetime(2024, 1, 16, 12, 30, 0)
        >>> datetime_to_simpy_time(target, start)
        36.5
    """
    delta = dt - start_datetime
    return delta.total_seconds() / 3600.0


def get_current_datetime(env: simpy.Environment, start_datetime: datetime) -> datetime:
    """
    Get current simulation datetime from SimPy environment.
    
    Args:
        env: SimPy environment
        start_datetime: Reference start datetime
        
    Returns:
        datetime: Current simulation datetime
    """
    return simpy_time_to_datetime(env.now, start_datetime)


def get_current_day(env: simpy.Environment, start_datetime: datetime) -> int:
    """
    Get current day of simulation (0=Monday, 1=Tuesday, ..., 4=Friday).
    
    Args:
        env: SimPy environment
        start_datetime: Reference start datetime (should be Monday 00:00:00)
        
    Returns:
        int: Day number (0-4 for 5-day simulation)
    """
    current_dt = get_current_datetime(env, start_datetime)
    return current_dt.weekday()


def get_hours_into_day(env: simpy.Environment, business_hours_per_day: int = 10) -> float:
    """
    Get hours elapsed in current business day (0.0-10.0 by default).
    
    Args:
        env: SimPy environment
        business_hours_per_day: Hours per business day (default: 10)
        
    Returns:
        float: Hours into current business day
        
    Example:
        If env.now = 12.5 (Tuesday 12:30 PM), returns 2.5
    """
    return env.now % business_hours_per_day


def is_same_day(time1: float, time2: float, business_hours_per_day: int = 10) -> bool:
    """
    Check if two SimPy times fall on the same business day.
    
    Args:
        time1: First SimPy time (hours)
        time2: Second SimPy time (hours)
        business_hours_per_day: Hours per business day (default: 10)
        
    Returns:
        bool: True if both times are on the same business day
    """
    return int(time1 / business_hours_per_day) == int(time2 / business_hours_per_day)


def get_day_number(simpy_time: float, business_hours_per_day: int = 10) -> int:
    """
    Get day number (0-based) for a given SimPy time.
    
    Args:
        simpy_time: SimPy time (hours)
        business_hours_per_day: Hours per business day (default: 10)
        
    Returns:
        int: Day number (0=Monday, 1=Tuesday, etc.)
    """
    return int(simpy_time / business_hours_per_day)


def format_simpy_time(simpy_time: float, business_hours_per_day: int = 10, business_start_hour: int = 8) -> str:
    """
    Format SimPy time as human-readable string with business hours.
    
    Args:
        simpy_time: Hours since simulation start
        business_hours_per_day: Hours per business day (default: 10)
        business_start_hour: Daily start hour in local time (default: 8 AM)
        
    Returns:
        str: Formatted string (e.g., "Monday, 10:30:00" for 2.5 hours = 10:30 AM)
    """
    day = int(simpy_time / business_hours_per_day)
    hours_in_day = simpy_time % business_hours_per_day
    
    # Convert to clock time (add business_start_hour)
    clock_hour_decimal = business_start_hour + hours_in_day
    clock_hour = int(clock_hour_decimal)
    minutes = int((clock_hour_decimal - clock_hour) * 60)
    seconds = int(((clock_hour_decimal - clock_hour) * 60 - minutes) * 60)
    
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    day_name = day_names[day] if day < len(day_names) else f'Day {day}'
    
    return f"{day_name}, {clock_hour:02d}:{minutes:02d}:{seconds:02d}"


def get_next_day_start(current_time: float, business_hours_per_day: int = 10) -> float:
    """
    Get SimPy time for start of next business day.
    
    Args:
        current_time: Current SimPy time
        business_hours_per_day: Hours per business day (default: 10)
        
    Returns:
        float: SimPy time for next business day start
    """
    current_day = int(current_time / business_hours_per_day)
    return (current_day + 1) * business_hours_per_day


def get_time_until_next_day(current_time: float, business_hours_per_day: int = 10) -> float:
    """
    Get hours remaining until next business day starts.
    
    Args:
        current_time: Current SimPy time
        business_hours_per_day: Hours per business day (default: 10)
        
    Returns:
        float: Hours until next business day
    """
    return get_next_day_start(current_time, business_hours_per_day) - current_time