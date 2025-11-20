"""
Configuration package for STM Simulator v3.0

This package handles loading, validating, and managing simulation configurations.
All simulation scenarios are driven by YAML configuration files.
"""

# Make key classes available at package level for easier imports
from .scenario_config import (
    ScenarioConfig,
    SimulationParameters,
    load_scenario_from_yaml,
    validate_scenario
)

# Define what gets imported with "from config import *"
__all__ = [
    'ScenarioConfig',
    'SimulationParameters',
    'load_scenario_from_yaml',
    'validate_scenario'
]

# Package metadata
__version__ = '3.0.0'
__author__ = 'Rohan Surve'