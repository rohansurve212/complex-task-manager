"""
Models package for STM Simulator v3.0

This package contains core data models for the simulation.
- Agent: Represents individual agents who process requests
- Request: Represents work requests to be processed
- RequestPool: Manages collection of active requests
- Assignment: Tracks agent-request assignments
"""

# Import core models for easy access
from .agent import Agent, AgentState
from .request import Request, RequestState
from .request_pool import RequestPool

# Define public API
__all__ = [
    'Agent',
    'AgentState',
    'Request',
    'RequestState',
    'RequestPool',
]

# Package metadata
__version__ = '3.0.0'