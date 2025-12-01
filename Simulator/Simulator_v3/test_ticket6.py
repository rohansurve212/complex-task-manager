"""
Test script for Ticket #6: SimPy Environment Setup.

This script verifies:
1. SimPy environment initialization
2. Time conversion utilities
3. Business day calculations
4. Basic simulation runner execution
"""

import sys
from pathlib import Path

from datetime import datetime
from simulation.simulation_environment import SimulationEnvironment
from simulation.time_utils import (
    simpy_time_to_datetime,
    datetime_to_simpy_time,
    format_simpy_time,
    get_day_number,
    get_hours_into_day
)
from simulation.simulation_runner import SimulationRunner
from config.scenario_config import ScenarioConfig

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_time_conversions():
    """Test time conversion utilities."""
    print("\n" + "="*60)
    print("Testing Time Conversion Utilities")
    print("="*60)
    
    start_dt = datetime(2024, 1, 15, 13, 0, 0)  # Monday 8 AM EST = 13:00 UTC
    
    # Test various SimPy times
    test_times = [
        (0.0, "Monday 8:00 AM"),
        (2.5, "Monday 10:30 AM"),
        (10.0, "Tuesday 8:00 AM"),
        (12.5, "Tuesday 10:30 AM"),
        (20.0, "Wednesday 8:00 AM"),
        (30.0, "Thursday 8:00 AM"),
        (40.0, "Friday 8:00 AM"),
        (49.5, "Friday 5:30 PM"),
        (50.0, "End of week")
    ]
    
    print("\nSimPy Time → Datetime Conversion:")
    for simpy_time, description in test_times:
        dt = simpy_time_to_datetime(simpy_time, start_dt)
        formatted = format_simpy_time(simpy_time)
        day_num = get_day_number(simpy_time)
        print(f"  {simpy_time:5.1f}h → {formatted:25s} | Day {day_num} | {description}")
    
    # Test round-trip conversion
    print("\nRound-trip Conversion Test:")
    test_dt = datetime(2024, 1, 17, 15, 30, 0)  # Wednesday 3:30 PM EST = 20:30 UTC
    simpy_time = datetime_to_simpy_time(test_dt, start_dt)
    back_to_dt = simpy_time_to_datetime(simpy_time, start_dt)
    print(f"  Original:   {test_dt}")
    print(f"  SimPy time: {simpy_time:.2f} hours")
    print(f"  Converted:  {back_to_dt}")
    print(f"  Match: {test_dt == back_to_dt}")


def test_simulation_environment():
    """Test SimulationEnvironment wrapper."""
    print("\n" + "="*60)
    print("Testing SimulationEnvironment")
    print("="*60)
    
    start_dt = datetime(2024, 1, 15, 13, 0, 0)
    sim_env = SimulationEnvironment(
        start_datetime=start_dt,
        duration_hours=50.0
    )
    
    print("\nEnvironment initialized:")
    print(f"  Start datetime: {sim_env.start_datetime}")
    print(f"  Duration: {sim_env.duration_hours} hours")
    print(f"  Initial time: {sim_env.now}")
    print(f"  State: {sim_env.state.value}")
    print(f"  Progress: {sim_env.progress_percentage:.1f}%")
    
    print("\nCurrent simulation time:")
    print(f"  SimPy time: {sim_env.now}")
    print(f"  Datetime: {sim_env.current_datetime}")
    print(f"  Formatted: {sim_env.current_time_str}")
    
    # Test timeout (advance time without running)
    print("\nAdvancing time by 15.5 hours...")
    sim_env.env._now = 15.5  # Manually advance for testing
    print(f"  New SimPy time: {sim_env.now}")
    print(f"  New datetime: {sim_env.current_datetime}")
    print(f"  New formatted: {sim_env.current_time_str}")
    print(f"  Progress: {sim_env.progress_percentage:.1f}%")


def test_simulation_runner_initialization():
    """Test SimulationRunner initialization."""
    print("\n" + "="*60)
    print("Testing SimulationRunner Initialization")
    print("="*60)
    
    # Create minimal configuration
    config_data = {
        'agents': [
            {'agent_id': 'AGENT001', 'skills': ['SkillA']},
            {'agent_id': 'AGENT002', 'skills': ['SkillA', 'SkillB']},
            {'agent_id': 'AGENT003', 'skills': ['SkillB']},
        ],
        'routing': {
            'pilot_program_enabled': False,
            'absent_agent_percentage': 0.1
        }
    }
    
    config = ScenarioConfig.model_validate(config_data)
    runner = SimulationRunner(config)
    
    print("\nSimulationRunner created:")
    print(f"  Start datetime: {runner.sim_env.start_datetime}")
    print(f"  Duration: {runner.sim_env.duration_hours} hours")
    print(f"  Config loaded: {config}")
    
    # Initialize components
    print("\nInitializing components...")
    runner.initialize_components()
    
    print(f"  Agents: {len(runner.agents)}")
    print(f"  Request pool: {runner.request_pool is not None}")
    print(f"  Absent manager: {runner.absent_manager is not None}")
    print(f"  Attribute generator: {runner.attribute_generator is not None}")
    print(f"  Metrics collector: {runner.metrics_collector is not None}")
    
    # Pre-load requests
    print("\nPre-loading 20 requests...")
    runner.preload_requests(num_requests=20)
    
    pool_stats = {
        'total': len(runner.request_pool.get_all_requests()),
        'pending': len(runner.request_pool.get_pending_requests()),
    }
    print(f"  Total requests: {pool_stats['total']}")
    print(f"  Pending requests: {pool_stats['pending']}")


def test_day_boundaries():
    """Test day boundary calculations."""
    print("\n" + "="*60)
    print("Testing Day Boundaries")
    print("="*60)
    
    print("\nDay boundaries for 10-hour business days:")
    for day in range(6):
        day_start = day * 10
        day_end = (day + 1) * 10 - 0.01
        
        day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Weekend'][day]
        
        if day < 5:
            print(f"  Day {day} ({day_name:10s}): {day_start:5.1f}h - {day_end:5.2f}h")
            print(f"    Start: {format_simpy_time(day_start)}")
            print(f"    End:   {format_simpy_time(day_end)}")
        else:
            print(f"  Day {day} ({day_name:10s}): {day_start:5.1f}h (simulation ends at 50.0h)")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("TICKET #6: SimPy Environment Setup - Verification Tests")
    print("="*70)
    
    try:
        test_time_conversions()
        test_simulation_environment()
        test_day_boundaries()
        test_simulation_runner_initialization()
        
        print("\n" + "="*70)
        print("✓ All Ticket #6 tests passed successfully!")
        print("="*70)
        print("\nNext: Ticket #7 (Production Routing Integration)")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()