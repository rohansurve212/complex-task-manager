"""
Simulation package for STM Simulator v3.0

This package contains simulation-related components:
- AbsentAgentManager: Manages agent absence rotation
- RequestAttributeGenerator: Generates random request attributes
- Production routing logic: Implements filter_static() behavior
"""

from simulation.absent_agent_manager import AbsentAgentManager

__all__ = [
    'AbsentAgentManager',
]