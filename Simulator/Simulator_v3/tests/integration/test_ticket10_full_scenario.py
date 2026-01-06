"""
Integration tests for Ticket #10: Scenario Runner & CLI.

Tests the complete end-to-end workflow:
- Loading scenarios from YAML files
- Running simulations via CLI
- Generating outputs (JSON, CSV)
- Command-line argument handling
- Full integration of all components
"""

import pytest
import tempfile
import os
import json
import subprocess
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from scenario.scenario_loader import ScenarioLoader
from scenario.scenario_runner import ScenarioRunner


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_scenario_yaml():
    """Create a sample scenario YAML for testing."""
    return """
name: Integration Test Scenario
description: Test scenario for integration testing

start_time: "2024-01-15T09:00:00-05:00"

routing_config:
  pilot_program_enabled: true

agents:
  - agent_id: AGENT001
    full_name: Alice Johnson
    skillsets: [SkillA]
  
  - agent_id: AGENT002
    full_name: Bob Smith
    skillsets: [SkillA]
  
  - agent_id: AGENT003
    full_name: Carol Davis
    skillsets: [SkillA]

requests:
  # Priority 5 commons
  - request_id: REQ001
    skill_id: SkillA
    order_date_offset_hours: -24
    foc_target: 7.0
    workorder_status: new
  
  - request_id: REQ002
    skill_id: SkillA
    order_date_offset_hours: -48
    foc_target: 7.0
    workorder_status: new
  
  - request_id: REQ003
    skill_id: SkillA
    order_date_offset_hours: -72
    foc_target: 7.0
    workorder_status: new
  
  - request_id: REQ004
    skill_id: SkillA
    order_date_offset_hours: -96
    foc_target: 7.0
    workorder_status: new
  
  - request_id: REQ005
    skill_id: SkillA
    order_date_offset_hours: -120
    foc_target: 7.0
    workorder_status: new
"""


@pytest.fixture
def second_scenario_yaml():
    """Create a second scenario for multi-scenario testing."""
    return """
name: Second Integration Test Scenario
description: Another test scenario

start_time: "2024-01-15T10:00:00-05:00"

routing_config:
  pilot_program_enabled: false

agents:
  - agent_id: AGENT_A
    full_name: Agent A
    skillsets: [SkillB]
  
  - agent_id: AGENT_B
    full_name: Agent B
    skillsets: [SkillB]

requests:
  - request_id: REQ_A1
    skill_id: SkillB
    order_date_offset_hours: -12
    foc_target: 5.0
    workorder_status: new
  
  - request_id: REQ_A2
    skill_id: SkillB
    order_date_offset_hours: -24
    foc_target: 5.0
    workorder_status: new
  
  - request_id: REQ_A3
    skill_id: SkillB
    order_date_offset_hours: -36
    foc_target: 5.0
    workorder_status: new
"""


# ============================================================================
# Test Scenario Loader Integration
# ============================================================================

def test_loader_integration_load_from_file(temp_dir, sample_scenario_yaml):
    """Test loading a complete scenario from YAML file."""
    # Write scenario to file
    filepath = os.path.join(temp_dir, 'test_scenario.yaml')
    with open(filepath, 'w') as f:
        f.write(sample_scenario_yaml)
    
    # Load scenario
    loader = ScenarioLoader()
    scenario = loader.load_scenario(filepath)
    
    # Verify complete structure
    assert scenario['name'] == 'Integration Test Scenario'
    assert len(scenario['agents']) == 3
    assert len(scenario['requests']) == 5
    assert scenario['routing_config'] is not None
    
    # Verify agents are properly constructed
    for agent in scenario['agents']:
        assert agent.agent_id is not None
        assert agent.full_name is not None
        assert len(agent.skillsets) > 0
    
    # Verify requests are properly constructed
    for request in scenario['requests']:
        assert request.request_id is not None
        assert request.skill_id is not None
        assert request.order_date is not None


def test_loader_integration_multiple_scenarios(temp_dir, sample_scenario_yaml, second_scenario_yaml):
    """Test loading multiple scenarios from directory."""
    # Write both scenarios
    with open(os.path.join(temp_dir, 'scenario1.yaml'), 'w') as f:
        f.write(sample_scenario_yaml)
    
    with open(os.path.join(temp_dir, 'scenario2.yaml'), 'w') as f:
        f.write(second_scenario_yaml)
    
    # Load all scenarios
    loader = ScenarioLoader()
    scenarios = loader.load_multiple_scenarios(temp_dir)
    
    assert len(scenarios) == 2
    assert scenarios[0]['name'] in ['Integration Test Scenario', 'Second Integration Test Scenario']
    assert scenarios[1]['name'] in ['Integration Test Scenario', 'Second Integration Test Scenario']


# ============================================================================
# Test Scenario Runner Integration
# ============================================================================

def test_runner_integration_single_scenario(temp_dir, sample_scenario_yaml):
    """Test running a complete scenario end-to-end."""
    # Setup
    filepath = os.path.join(temp_dir, 'test_scenario.yaml')
    with open(filepath, 'w') as f:
        f.write(sample_scenario_yaml)
    
    loader = ScenarioLoader()
    scenario = loader.load_scenario(filepath)
    
    # Run scenario
    runner = ScenarioRunner()
    result = runner.run_scenario(
        scenario=scenario,
        stop_when_idle=True,
        verbose=False
    )
    
    # Verify results
    assert result.scenario_name == 'Integration Test Scenario'
    assert result.statistics is not None
    assert result.assignments is not None
    
    # Verify assignments were made (3 agents, 5 requests)
    assert result.statistics['assignments']['total'] > 0
    assert result.statistics['agents']['agents_with_assignments'] > 0


def test_runner_integration_multiple_scenarios(temp_dir, sample_scenario_yaml, second_scenario_yaml):
    """Test running multiple scenarios in sequence."""
    # Setup
    with open(os.path.join(temp_dir, 'scenario1.yaml'), 'w') as f:
        f.write(sample_scenario_yaml)
    
    with open(os.path.join(temp_dir, 'scenario2.yaml'), 'w') as f:
        f.write(second_scenario_yaml)
    
    # Load and run
    loader = ScenarioLoader()
    scenarios = loader.load_multiple_scenarios(temp_dir)
    
    runner = ScenarioRunner()
    results = runner.run_multiple_scenarios(
        scenarios=scenarios,
        stop_when_idle=True,
        verbose=False
    )
    
    # Verify both completed
    assert len(results) == 2
    assert all(r.statistics['assignments']['total'] > 0 for r in results)


def test_runner_integration_output_json(temp_dir, sample_scenario_yaml):
    """Test generating JSON output."""
    # Setup and run
    filepath = os.path.join(temp_dir, 'test_scenario.yaml')
    with open(filepath, 'w') as f:
        f.write(sample_scenario_yaml)
    
    loader = ScenarioLoader()
    scenario = loader.load_scenario(filepath)
    
    runner = ScenarioRunner()
    result = runner.run_scenario(scenario, stop_when_idle=True, verbose=False)
    
    # Save JSON
    output_file = os.path.join(temp_dir, 'result.json')
    runner.save_result(result, output_file)
    
    # Verify file exists and is valid JSON
    assert os.path.exists(output_file)
    
    with open(output_file, 'r') as f:
        loaded = json.load(f)
    
    assert loaded['scenario_name'] == 'Integration Test Scenario'
    assert 'statistics' in loaded
    assert 'assignments' in loaded


def test_runner_integration_output_csv(temp_dir, sample_scenario_yaml):
    """Test generating CSV output."""
    # Setup and run
    filepath = os.path.join(temp_dir, 'test_scenario.yaml')
    with open(filepath, 'w') as f:
        f.write(sample_scenario_yaml)
    
    loader = ScenarioLoader()
    scenario = loader.load_scenario(filepath)
    
    runner = ScenarioRunner()
    result = runner.run_scenario(scenario, stop_when_idle=True, verbose=False)
    
    # Save CSV
    output_file = os.path.join(temp_dir, 'assignments.csv')
    runner.export_assignments_csv(result, output_file)
    
    # Verify file exists and has content
    assert os.path.exists(output_file)
    
    with open(output_file, 'r') as f:
        content = f.read()
    
    # Should have header and data
    assert 'assignment_id' in content
    assert 'agent_id' in content
    assert 'request_id' in content
    
    # Should have actual assignments
    lines = content.strip().split('\n')
    assert len(lines) > 1  # Header + at least one data row


# ============================================================================
# Test CLI Integration (subprocess)
# ============================================================================

def test_cli_integration_basic_run(temp_dir, sample_scenario_yaml):
    """Test running simulation via CLI."""
    # Setup
    filepath = os.path.join(temp_dir, 'test_scenario.yaml')
    with open(filepath, 'w') as f:
        f.write(sample_scenario_yaml)
    
    # Run via CLI
    result = subprocess.run(
        [sys.executable, 'main.py', filepath, '--quiet'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should complete successfully
    assert result.returncode == 0


def test_cli_integration_with_output(temp_dir, sample_scenario_yaml):
    """Test CLI with output directory."""
    # Setup
    scenario_file = os.path.join(temp_dir, 'test_scenario.yaml')
    with open(scenario_file, 'w') as f:
        f.write(sample_scenario_yaml)
    
    output_dir = os.path.join(temp_dir, 'results')
    
    # Run via CLI
    result = subprocess.run(
        [sys.executable, 'main.py', scenario_file, '--output', output_dir, '--quiet'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should complete successfully
    assert result.returncode == 0
    
    # Output file should exist
    expected_file = os.path.join(output_dir, 'integration_test_scenario.json')
    assert os.path.exists(expected_file)


def test_cli_integration_with_csv(temp_dir, sample_scenario_yaml):
    """Test CLI with CSV export."""
    # Setup
    scenario_file = os.path.join(temp_dir, 'test_scenario.yaml')
    with open(scenario_file, 'w') as f:
        f.write(sample_scenario_yaml)
    
    csv_file = os.path.join(temp_dir, 'assignments.csv')
    
    # Run via CLI
    result = subprocess.run(
        [sys.executable, 'main.py', scenario_file, '--csv', csv_file, '--quiet'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should complete successfully
    assert result.returncode == 0
    
    # CSV file should exist
    assert os.path.exists(csv_file)


def test_cli_integration_verbose_mode(temp_dir, sample_scenario_yaml):
    """Test CLI with verbose output."""
    # Setup
    filepath = os.path.join(temp_dir, 'test_scenario.yaml')
    with open(filepath, 'w') as f:
        f.write(sample_scenario_yaml)
    
    # Run via CLI with verbose
    result = subprocess.run(
        [sys.executable, 'main.py', filepath, '--verbose'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should complete successfully
    assert result.returncode == 0
    
    # Should have verbose output
    assert 'Integration Test Scenario' in result.stdout
    assert 'SIMULATION RESULTS' in result.stdout


def test_cli_integration_multiple_scenarios(temp_dir, sample_scenario_yaml, second_scenario_yaml):
    """Test CLI with multiple scenarios."""
    # Setup
    with open(os.path.join(temp_dir, 'scenario1.yaml'), 'w') as f:
        f.write(sample_scenario_yaml)
    
    with open(os.path.join(temp_dir, 'scenario2.yaml'), 'w') as f:
        f.write(second_scenario_yaml)
    
    # Run via CLI
    result = subprocess.run(
        [sys.executable, 'main.py', temp_dir, '--all', '--quiet'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should complete successfully
    assert result.returncode == 0


def test_cli_integration_max_events(temp_dir, sample_scenario_yaml):
    """Test CLI with max_events limit."""
    # Setup
    filepath = os.path.join(temp_dir, 'test_scenario.yaml')
    with open(filepath, 'w') as f:
        f.write(sample_scenario_yaml)
    
    # Run via CLI with max_events
    result = subprocess.run(
        [sys.executable, 'main.py', filepath, '--max-events', '10', '--quiet'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should complete successfully
    assert result.returncode == 0


def test_cli_integration_help(temp_dir):
    """Test CLI help output."""
    # Run help
    result = subprocess.run(
        [sys.executable, 'main.py', '--help'],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # Should show help and exit successfully
    assert result.returncode == 0
    assert 'STM Routing Simulator' in result.stdout
    assert 'usage:' in result.stdout.lower()


def test_cli_integration_version(temp_dir):
    """Test CLI version output."""
    # Run version
    result = subprocess.run(
        [sys.executable, 'main.py', '--version'],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # Should show version
    assert result.returncode == 0
    assert '3.0' in result.stdout or '3.0' in result.stderr


# ============================================================================
# Test Full Workflow Integration
# ============================================================================

def test_full_workflow_integration(temp_dir, sample_scenario_yaml):
    """Test complete workflow: YAML → Loader → Runner → Output."""
    # Step 1: Create YAML file
    scenario_file = os.path.join(temp_dir, 'workflow_test.yaml')
    with open(scenario_file, 'w') as f:
        f.write(sample_scenario_yaml)
    
    # Step 2: Load scenario
    loader = ScenarioLoader()
    scenario = loader.load_scenario(scenario_file)
    
    assert scenario is not None
    assert len(scenario['agents']) == 3
    assert len(scenario['requests']) == 5
    
    # Step 3: Run simulation
    runner = ScenarioRunner()
    result = runner.run_scenario(
        scenario=scenario,
        stop_when_idle=True,
        verbose=False
    )
    
    assert result is not None
    assert result.statistics['assignments']['total'] > 0
    
    # Step 4: Generate outputs
    json_file = os.path.join(temp_dir, 'workflow_result.json')
    csv_file = os.path.join(temp_dir, 'workflow_assignments.csv')
    
    runner.save_result(result, json_file)
    runner.export_assignments_csv(result, csv_file)
    
    # Step 5: Verify outputs
    assert os.path.exists(json_file)
    assert os.path.exists(csv_file)
    
    # Verify JSON content
    with open(json_file, 'r') as f:
        json_data = json.load(f)
    
    assert json_data['scenario_name'] == 'Integration Test Scenario'
    assert json_data['statistics']['assignments']['total'] > 0
    
    # Verify CSV content
    with open(csv_file, 'r') as f:
        csv_content = f.read()
    
    assert 'agent_id' in csv_content
    assert 'AGENT' in csv_content  # Should have agent IDs


def test_workflow_with_analysis(temp_dir, sample_scenario_yaml):
    """Test workflow with analysis methods."""
    # Setup and run
    filepath = os.path.join(temp_dir, 'test_scenario.yaml')
    with open(filepath, 'w') as f:
        f.write(sample_scenario_yaml)
    
    loader = ScenarioLoader()
    scenario = loader.load_scenario(filepath)
    
    runner = ScenarioRunner()
    result = runner.run_scenario(scenario, stop_when_idle=True, verbose=False)
    
    # Run analyses
    workload = runner.get_agent_workload_analysis(result)
    flow = runner.get_request_flow_analysis(result)
    
    # Verify analysis results
    assert workload is not None
    assert 'total_agents' in workload
    assert 'assignments_per_agent' in workload
    
    assert flow is not None
    assert 'throughput_per_hour' in flow
    assert 'completion_rate' in flow


# ============================================================================
# Test Error Handling Integration
# ============================================================================

def test_integration_invalid_yaml(temp_dir):
    """Test handling of invalid YAML file."""
    # Create invalid YAML
    filepath = os.path.join(temp_dir, 'invalid.yaml')
    with open(filepath, 'w') as f:
        f.write('invalid: yaml: content:')
    
    # Should raise error
    loader = ScenarioLoader()
    with pytest.raises(Exception):  # ScenarioLoadError
        loader.load_scenario(filepath)


def test_integration_missing_file():
    """Test handling of missing file."""
    loader = ScenarioLoader()
    
    with pytest.raises(Exception):  # ScenarioLoadError
        loader.load_scenario('nonexistent_file.yaml')


def test_cli_integration_invalid_scenario(temp_dir):
    """Test CLI with invalid scenario."""
    # Create invalid scenario
    filepath = os.path.join(temp_dir, 'invalid.yaml')
    with open(filepath, 'w') as f:
        f.write('name: Invalid\n')  # Missing required fields
    
    # Run via CLI
    result = subprocess.run(
        [sys.executable, 'main.py', filepath],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # Should fail with non-zero exit code
    assert result.returncode != 0


# ============================================================================
# Test Performance Integration
# ============================================================================

def test_integration_performance_large_scenario(temp_dir):
    """Test performance with larger scenario."""
    # Create larger scenario
    scenario_yaml = """
name: Large Performance Test
start_time: "2024-01-15T09:00:00-05:00"

routing_config:
  pilot_program_enabled: true

agents:
"""
    
    # Add 10 agents
    for i in range(10):
        scenario_yaml += f"""  - agent_id: AGENT{i:03d}
    full_name: Agent {i}
    skillsets: [SkillA]
"""
    
    scenario_yaml += "\nrequests:\n"
    
    # Add 50 requests
    for i in range(50):
        scenario_yaml += f"""  - request_id: REQ{i:03d}
    skill_id: SkillA
    order_date_offset_hours: -{(i+1)*12}
    foc_target: 7.0
    workorder_status: new
"""
    
    # Write and run
    filepath = os.path.join(temp_dir, 'large_scenario.yaml')
    with open(filepath, 'w') as f:
        f.write(scenario_yaml)
    
    loader = ScenarioLoader()
    scenario = loader.load_scenario(filepath)
    
    runner = ScenarioRunner()
    
    # Time the execution
    import time
    start = time.time()
    result = runner.run_scenario(scenario, stop_when_idle=True, verbose=False)
    duration = time.time() - start
    
    # Should complete in reasonable time (< 5 seconds for 10 agents, 50 requests)
    assert duration < 5.0
    
    # Should have processed all requests
    assert result.statistics['requests']['total_requests'] == 50
    assert result.statistics['agents']['total_agents'] == 10