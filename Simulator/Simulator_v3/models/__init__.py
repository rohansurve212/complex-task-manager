"""
Models package for STM Simulator v3.0

This package contains core data models for the simulation.
- Agent: Represents individual agents who process requests
- Request: Represents work requests to be processed
- Assignment: Tracks agent-request assignments
"""

# Import core models for easy access
from .agent import Agent, AgentState

# Define public API
__all__ = [
    'Agent',
    'AgentState',
]

# Package metadata
__version__ = '3.0.0'