"""
Utility package for STM Simulator v3.0

Common utilities used across the simulator including logging,
timing, and helper functions.
"""

from .logger import setup_logger, get_logger

__all__ = ['setup_logger', 'get_logger']

__version__ = '3.0.0'