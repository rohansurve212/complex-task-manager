"""
Unit tests for scenario runner.

Tests cover:
- ScenarioResult class
- Single scenario execution
- Multiple scenario execution
- Result formatting and printing
- Result persistence (JSON, CSV)
- Analysis methods
- Error handling
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from io import StringIO
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from scenario.scenario_runner import ScenarioRunner, ScenarioResult
from scenario.scenario_loader import ScenarioLoader
from models.agent import Agent
from models.request import Request
from config.scenario_config import RoutingConfig


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def runner():
    """Create scenario runner instance."""
    return ScenarioRunner()


@pytest.fixture
def sample_scenario():
    """Create a minimal test scenario."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    
    agents = [
        Agent(agent_id='AGENT001', full_name='Test Agent 1', skillsets={'SkillA'}),
        Agent(agent_id='AGENT002', full_name='Test Agent 2', skillsets={'SkillA'})
    ]
    
    requests = [
        Request(
            request_id='REQ001',
            external_id='EXT_REQ001',
            skill_id='SkillA',
            request_source='web',
            product='ProductA',
            service_region='Ontario',
            request_type='service',
            order_date=start_time - timedelta(hours=24),
            foc_target=7.0
        ),
        Request(
            request_id='REQ002',
            external_id='EXT_REQ002',
            skill_id='SkillA',
            request_source='web',
            product='ProductA',
            service_region='Ontario',
            request_type='service',
            order_date=start_time - timedelta(hours=48),
            foc_target=7.0
        )
    ]
    
    return {
        'name': 'Test Scenario',
        'description': 'Simple test scenario',
        'filepath': 'test_scenario.yaml',
        'start_time': start_time,
        'agents': agents,
        'requests': requests,
        'routing_config': RoutingConfig(pilot_program_enabled=True)
    }


@pytest.fixture
def sample_result():
    """Create a sample ScenarioResult for testing."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2024, 1, 15, 9, 0, 5, tzinfo=timezone.utc)
    
    statistics = {
        'timing': {
            'start_time': start_time,
            'end_time': end_time,
            'duration_seconds': 5.0,
            'duration_hours': 0.001389
        },
        'events': {
            'total_processed': 10
        },
        'assignments': {
            'total': 2,
            'by_priority': {1: 0, 2: 0, 3: 0, 4: 0, 5: 2},
            'followup_count': 0,
            'cmo_count': 2,
            'from_absent_agent_count': 0
        },
        'agents': {
            'total_agents': 2,
            'agents_with_assignments': 2,
            'agents_without_assignments': 0,
            'avg_assignments_per_agent': 1.0,
            'max_assignments_per_agent': 1,
            'min_assignments_per_agent': 1,
            'assignments_per_agent': {'AGENT001': 1, 'AGENT002': 1}
        },
        'requests': {
            'total_requests': 2,
            'assigned_requests': 2,
            'pending_requests': 0,
            'pool_statistics': {}
        },
        'routing': {
            'total_decisions': 10,
            'successful_routings': 2,
            'failed_routings': 8,
            'success_rate': 0.2,
            'avg_filtered_per_decision': 1.5
        }
    }
    
    assignments = [
        {
            'assignment_id': 'ASSIGN_0',
            'timestamp': start_time,
            'agent_id': 'AGENT001',
            'request_id': 'REQ001',
            'completion_time': start_time + timedelta(days=7),
            'was_followup': False,
            'from_absent_agent': False,
            'priority_level': 5
        },
        {
            'assignment_id': 'ASSIGN_1',
            'timestamp': start_time + timedelta(seconds=1),
            'agent_id': 'AGENT002',
            'request_id': 'REQ002',
            'completion_time': start_time + timedelta(days=7),
            'was_followup': False,
            'from_absent_agent': False,
            'priority_level': 5
        }
    ]
    
    routing_decisions = [
        {
            'timestamp': start_time,
            'agent_id': 'AGENT001',
            'filtered_count': 2,
            'selected_request_id': 'REQ001',
            'was_followup': False
        },
        {
            'timestamp': start_time + timedelta(seconds=1),
            'agent_id': 'AGENT002',
            'filtered_count': 1,
            'selected_request_id': 'REQ002',
            'was_followup': False
        }
    ]
    
    return ScenarioResult(
        scenario_name='Test Scenario',
        start_time=start_time,
        end_time=end_time,
        statistics=statistics,
        assignments=assignments,
        routing_decisions=routing_decisions,
        metadata={'description': 'Test scenario', 'filepath': 'test.yaml'}
    )


# ============================================================================
# Test ScenarioResult Class
# ============================================================================

def test_scenario_result_initialization(sample_result):
    """Test that ScenarioResult initializes correctly."""
    assert sample_result.scenario_name == 'Test Scenario'
    assert isinstance(sample_result.start_time, datetime)
    assert isinstance(sample_result.end_time, datetime)
    assert isinstance(sample_result.statistics, dict)
    assert isinstance(sample_result.assignments, list)
    assert isinstance(sample_result.routing_decisions, list)
    assert isinstance(sample_result.metadata, dict)


def test_scenario_result_to_dict(sample_result):
    """Test converting result to dictionary."""
    result_dict = sample_result.to_dict()
    
    assert isinstance(result_dict, dict)
    assert 'scenario_name' in result_dict
    assert 'start_time' in result_dict
    assert 'end_time' in result_dict
    assert 'statistics' in result_dict
    assert 'assignments' in result_dict
    assert 'routing_decisions' in result_dict
    assert 'metadata' in result_dict


def test_scenario_result_to_json(sample_result):
    """Test converting result to JSON string."""
    json_str = sample_result.to_json()
    
    assert isinstance(json_str, str)
    
    # Verify it's valid JSON
    parsed = json.loads(json_str)
    assert parsed['scenario_name'] == 'Test Scenario'


def test_scenario_result_to_json_with_indent(sample_result):
    """Test JSON with custom indentation."""
    json_str = sample_result.to_json(indent=4)
    
    # Should be pretty-printed with 4-space indent
    assert '    ' in json_str  # 4 spaces


def test_scenario_result_get_summary(sample_result):
    """Test getting concise summary."""
    summary = sample_result.get_summary()
    
    assert isinstance(summary, dict)
    assert 'scenario_name' in summary
    assert 'duration_hours' in summary
    assert 'total_agents' in summary
    assert 'total_requests' in summary
    assert 'total_assignments' in summary
    assert 'followup_count' in summary
    assert 'cmo_count' in summary
    assert 'routing_success_rate' in summary
    
    # Verify values
    assert summary['total_assignments'] == 2
    assert summary['total_agents'] == 2


# ============================================================================
# Test Single Scenario Execution
# ============================================================================

def test_run_scenario_basic(runner, sample_scenario):
    """Test running a basic scenario."""
    result = runner.run_scenario(
        scenario=sample_scenario,
        stop_when_idle=True,
        verbose=False
    )
    
    assert isinstance(result, ScenarioResult)
    assert result.scenario_name == 'Test Scenario'
    assert result.start_time is not None
    assert result.end_time is not None
    assert result.statistics is not None


def test_run_scenario_with_max_events(runner, sample_scenario):
    """Test running scenario with max_events limit."""
    result = runner.run_scenario(
        scenario=sample_scenario,
        max_events=5,
        stop_when_idle=False,
        verbose=False
    )
    
    assert isinstance(result, ScenarioResult)
    # Should have stopped at or before 5 events (may stop earlier if naturally complete)
    assert result.statistics['events']['total_processed'] <= 5


def test_run_scenario_returns_statistics(runner, sample_scenario):
    """Test that result contains statistics."""
    result = runner.run_scenario(
        scenario=sample_scenario,
        stop_when_idle=True,
        verbose=False
    )
    
    stats = result.statistics
    
    # Verify structure
    assert 'timing' in stats
    assert 'events' in stats
    assert 'assignments' in stats
    assert 'agents' in stats
    assert 'requests' in stats
    assert 'routing' in stats


def test_run_scenario_returns_assignments(runner, sample_scenario):
    """Test that result contains assignments."""
    result = runner.run_scenario(
        scenario=sample_scenario,
        stop_when_idle=True,
        verbose=False
    )
    
    assert isinstance(result.assignments, list)
    # Should have made some assignments
    assert len(result.assignments) > 0


def test_run_scenario_returns_routing_decisions(runner, sample_scenario):
    """Test that result contains routing decisions."""
    result = runner.run_scenario(
        scenario=sample_scenario,
        stop_when_idle=True,
        verbose=False
    )
    
    assert isinstance(result.routing_decisions, list)
    assert len(result.routing_decisions) > 0


def test_run_scenario_metadata(runner, sample_scenario):
    """Test that result includes metadata."""
    result = runner.run_scenario(
        scenario=sample_scenario,
        stop_when_idle=True,
        verbose=False
    )
    
    metadata = result.metadata
    
    assert 'description' in metadata
    assert 'filepath' in metadata
    assert 'sim_start_time' in metadata
    assert 'stop_when_idle' in metadata


def test_run_scenario_verbose_output(runner, sample_scenario, capsys):
    """Test that verbose mode produces output."""
    result = runner.run_scenario(
        scenario=sample_scenario,
        stop_when_idle=True,
        verbose=True
    )
    
    captured = capsys.readouterr()
    
    # Should have printed scenario info
    assert 'Test Scenario' in captured.out
    assert 'Agents:' in captured.out
    assert 'Requests:' in captured.out


# ============================================================================
# Test Multiple Scenario Execution
# ============================================================================

def test_run_multiple_scenarios(runner, sample_scenario):
    """Test running multiple scenarios."""
    # Create two slightly different scenarios
    scenario1 = sample_scenario.copy()
    scenario1['name'] = 'Scenario 1'
    
    scenario2 = sample_scenario.copy()
    scenario2['name'] = 'Scenario 2'
    
    results = runner.run_multiple_scenarios(
        scenarios=[scenario1, scenario2],
        stop_when_idle=True,
        verbose=False
    )
    
    assert len(results) == 2
    assert all(isinstance(r, ScenarioResult) for r in results)
    assert results[0].scenario_name == 'Scenario 1'
    assert results[1].scenario_name == 'Scenario 2'


def test_run_multiple_scenarios_with_failure(runner, sample_scenario):
    """Test that one failure doesn't stop other scenarios."""
    # Create valid and invalid scenarios
    valid_scenario = sample_scenario.copy()
    valid_scenario['name'] = 'Valid Scenario'
    
    invalid_scenario = sample_scenario.copy()
    invalid_scenario['name'] = 'Invalid Scenario'
    invalid_scenario['agents'] = []  # No agents - will cause issues
    
    # Should handle error gracefully
    results = runner.run_multiple_scenarios(
        scenarios=[valid_scenario, invalid_scenario],
        stop_when_idle=True,
        verbose=False
    )
    
    # Should have at least the valid scenario result
    assert len(results) >= 1


def test_run_multiple_scenarios_verbose(runner, sample_scenario, capsys):
    """Test verbose output for multiple scenarios."""
    scenario1 = sample_scenario.copy()
    scenario1['name'] = 'Scenario 1'
    
    scenario2 = sample_scenario.copy()
    scenario2['name'] = 'Scenario 2'
    
    results = runner.run_multiple_scenarios(
        scenarios=[scenario1, scenario2],
        stop_when_idle=True,
        verbose=True
    )
    
    captured = capsys.readouterr()
    
    # Should show progress
    assert 'Scenario 1' in captured.out or 'Scenario 2' in captured.out


# ============================================================================
# Test Print Methods
# ============================================================================

def test_print_summary(runner, sample_result, capsys):
    """Test printing scenario summary."""
    runner.print_summary(sample_result)
    
    captured = capsys.readouterr()
    
    # Verify key sections are printed
    assert 'SIMULATION RESULTS' in captured.out
    assert 'Test Scenario' in captured.out
    assert 'TIMING' in captured.out
    assert 'ASSIGNMENTS' in captured.out
    assert 'PRIORITY DISTRIBUTION' in captured.out
    assert 'AGENTS' in captured.out
    assert 'REQUESTS' in captured.out
    assert 'ROUTING' in captured.out


def test_print_comparison_multiple_results(runner, sample_result, capsys):
    """Test printing comparison of multiple results."""
    # Create second result with different stats
    result2 = ScenarioResult(
        scenario_name='Scenario 2',
        start_time=sample_result.start_time,
        end_time=sample_result.end_time,
        statistics=sample_result.statistics.copy(),
        assignments=sample_result.assignments.copy(),
        routing_decisions=sample_result.routing_decisions.copy()
    )
    
    runner.print_comparison([sample_result, result2])
    
    captured = capsys.readouterr()
    
    # Verify comparison table
    assert 'SCENARIO COMPARISON' in captured.out
    assert 'Test Scenario' in captured.out
    assert 'Scenario 2' in captured.out
    assert 'Duration' in captured.out
    assert 'Total Assignments' in captured.out


def test_print_comparison_single_result_does_nothing(runner, sample_result, capsys):
    """Test that comparison with single result doesn't print."""
    runner.print_comparison([sample_result])
    
    captured = capsys.readouterr()
    
    # Should not print comparison for single result
    assert 'COMPARISON' not in captured.out


# ============================================================================
# Test Result Persistence
# ============================================================================

def test_save_result_json(runner, sample_result, temp_dir):
    """Test saving result to JSON file."""
    filepath = os.path.join(temp_dir, 'result.json')
    
    runner.save_result(sample_result, filepath)
    
    # Verify file exists
    assert os.path.exists(filepath)
    
    # Verify content
    with open(filepath, 'r') as f:
        loaded = json.load(f)
    
    assert loaded['scenario_name'] == 'Test Scenario'
    assert loaded['statistics']['assignments']['total'] == 2


def test_save_results_multiple(runner, sample_result, temp_dir):
    """Test saving multiple results to directory."""
    result2 = ScenarioResult(
        scenario_name='Scenario Two',
        start_time=sample_result.start_time,
        end_time=sample_result.end_time,
        statistics=sample_result.statistics,
        assignments=sample_result.assignments,
        routing_decisions=sample_result.routing_decisions
    )
    
    runner.save_results([sample_result, result2], temp_dir)
    
    # Verify files exist
    file1 = os.path.join(temp_dir, 'test_scenario.json')
    file2 = os.path.join(temp_dir, 'scenario_two.json')
    
    assert os.path.exists(file1)
    assert os.path.exists(file2)


def test_save_results_creates_directory(runner, sample_result, temp_dir):
    """Test that save_results creates directory if needed."""
    output_dir = os.path.join(temp_dir, 'new_dir', 'nested')
    
    runner.save_results([sample_result], output_dir)
    
    # Directory should be created
    assert os.path.exists(output_dir)
    
    # File should exist
    filepath = os.path.join(output_dir, 'test_scenario.json')
    assert os.path.exists(filepath)


def test_export_assignments_csv(runner, sample_result, temp_dir):
    """Test exporting assignments to CSV."""
    filepath = os.path.join(temp_dir, 'assignments.csv')
    
    runner.export_assignments_csv(sample_result, filepath)
    
    # Verify file exists
    assert os.path.exists(filepath)
    
    # Verify content
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Should have header
    assert 'assignment_id' in content
    assert 'agent_id' in content
    assert 'request_id' in content
    
    # Should have data
    assert 'AGENT001' in content
    assert 'REQ001' in content


def test_export_assignments_csv_no_assignments(runner, temp_dir):
    """Test exporting with no assignments."""
    result = ScenarioResult(
        scenario_name='Empty',
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        statistics={},
        assignments=[],  # Empty
        routing_decisions=[]
    )
    
    filepath = os.path.join(temp_dir, 'empty.csv')
    
    # Should handle gracefully
    runner.export_assignments_csv(result, filepath)
    
    # File should not be created (no data to write)
    # Or if created, should be empty or header-only


# ============================================================================
# Test Analysis Methods
# ============================================================================

def test_get_agent_workload_analysis(runner, sample_result):
    """Test agent workload analysis."""
    workload = runner.get_agent_workload_analysis(sample_result)
    
    assert isinstance(workload, dict)
    assert 'total_agents' in workload
    assert 'agents_with_work' in workload
    assert 'average_assignments' in workload
    assert 'assignments_per_agent' in workload
    assert 'priorities_per_agent' in workload
    
    # Verify values
    assert workload['total_agents'] == 2
    assert workload['agents_with_work'] == 2


def test_get_agent_workload_analysis_per_agent(runner, sample_result):
    """Test per-agent workload details."""
    workload = runner.get_agent_workload_analysis(sample_result)
    
    assignments_per_agent = workload['assignments_per_agent']
    
    assert 'AGENT001' in assignments_per_agent
    assert 'AGENT002' in assignments_per_agent
    assert assignments_per_agent['AGENT001'] == 1
    assert assignments_per_agent['AGENT002'] == 1


def test_get_agent_workload_analysis_priorities(runner, sample_result):
    """Test priority distribution per agent."""
    workload = runner.get_agent_workload_analysis(sample_result)
    
    priorities = workload['priorities_per_agent']
    
    assert 'AGENT001' in priorities
    assert 'AGENT002' in priorities
    
    # Both agents got priority 5 requests
    assert priorities['AGENT001'][5] == 1
    assert priorities['AGENT002'][5] == 1


def test_get_request_flow_analysis(runner, sample_result):
    """Test request flow analysis."""
    flow = runner.get_request_flow_analysis(sample_result)
    
    assert isinstance(flow, dict)
    assert 'total_requests' in flow
    assert 'total_assignments' in flow
    assert 'pending_requests' in flow
    assert 'completion_rate' in flow
    assert 'throughput_per_hour' in flow
    assert 'followup_ratio' in flow
    assert 'cmo_ratio' in flow
    assert 'hourly_assignments' in flow


def test_get_request_flow_analysis_ratios(runner, sample_result):
    """Test flow analysis ratio calculations."""
    flow = runner.get_request_flow_analysis(sample_result)
    
    # All assignments are CMO (not followup)
    assert flow['followup_ratio'] == 0.0
    assert flow['cmo_ratio'] == 1.0
    
    # Completion rate (all assigned)
    assert flow['completion_rate'] == 1.0


def test_get_request_flow_analysis_hourly(runner, sample_result):
    """Test hourly assignments grouping."""
    flow = runner.get_request_flow_analysis(sample_result)
    
    hourly = flow['hourly_assignments']
    
    assert isinstance(hourly, dict)
    # Should have at least one hour with assignments
    assert len(hourly) > 0


# ============================================================================
# Test Edge Cases
# ============================================================================

def test_run_scenario_empty_agents(runner):
    """Test running scenario with no agents."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    
    scenario = {
        'name': 'Empty Agents',
        'description': 'No agents',
        'filepath': 'test.yaml',
        'start_time': start_time,
        'agents': [],  # Empty
        'requests': [
            Request(
                request_id='REQ001',
                external_id='EXT_REQ001',
                skill_id='SkillA',
                request_source='web',
                product='ProductA',
                service_region='Ontario',
                request_type='service',
                order_date=start_time,
                foc_target=7.0
            )
        ],
        'routing_config': RoutingConfig()
    }
    
    result = runner.run_scenario(scenario, stop_when_idle=True, verbose=False)
    
    # Should complete without error
    assert result.statistics['assignments']['total'] == 0


def test_run_scenario_empty_requests(runner):
    """Test running scenario with no requests."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    
    scenario = {
        'name': 'Empty Requests',
        'description': 'No requests',
        'filepath': 'test.yaml',
        'start_time': start_time,
        'agents': [
            Agent(agent_id='AGENT001', full_name='Test', skillsets={'SkillA'})
        ],
        'requests': [],  # Empty
        'routing_config': RoutingConfig()
    }
    
    result = runner.run_scenario(scenario, stop_when_idle=True, verbose=False)
    
    # Should complete without error
    assert result.statistics['assignments']['total'] == 0


def test_scenario_result_with_no_metadata(sample_result):
    """Test ScenarioResult without metadata."""
    result = ScenarioResult(
        scenario_name='Test',
        start_time=sample_result.start_time,
        end_time=sample_result.end_time,
        statistics=sample_result.statistics,
        assignments=sample_result.assignments,
        routing_decisions=sample_result.routing_decisions
        # No metadata parameter
    )
    
    # Should default to empty dict
    assert result.metadata == {}


def test_get_workload_analysis_no_assignments(runner):
    """Test workload analysis with no assignments."""
    result = ScenarioResult(
        scenario_name='Empty',
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        statistics={
            'agents': {
                'total_agents': 2,
                'agents_with_assignments': 0,
                'agents_without_assignments': 2,
                'avg_assignments_per_agent': 0,
                'max_assignments_per_agent': 0,
                'min_assignments_per_agent': 0
            }
        },
        assignments=[],
        routing_decisions=[]
    )
    
    workload = runner.get_agent_workload_analysis(result)
    
    # Should handle empty gracefully
    assert workload['agents_with_work'] == 0
    assert workload['assignments_per_agent'] == {}


def test_get_flow_analysis_no_assignments(runner):
    """Test flow analysis with no assignments."""
    result = ScenarioResult(
        scenario_name='Empty',
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        statistics={
            'timing': {'duration_hours': 0.0},
            'assignments': {'total': 0, 'followup_count': 0, 'cmo_count': 0},
            'requests': {'total_requests': 5, 'pending_requests': 5}
        },
        assignments=[],
        routing_decisions=[]
    )
    
    flow = runner.get_request_flow_analysis(result)
    
    # Should handle empty gracefully
    assert flow['total_assignments'] == 0
    assert flow['completion_rate'] == 0.0