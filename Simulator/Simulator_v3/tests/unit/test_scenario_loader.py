"""
Unit tests for scenario loader.

Tests cover:
- YAML loading and parsing
- Structure validation
- Start time parsing
- Routing config building
- Agent building
- Request building
- Date handling (relative and absolute)
- Error handling
- Multiple scenario loading
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from datetime import datetime, timezone, timedelta

from scenario.scenario_loader import ScenarioLoader, ScenarioLoadError
from models.agent import Agent
from models.request import Request
from config.scenario_config import RoutingConfig


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def loader():
    """Create scenario loader instance."""
    return ScenarioLoader()


@pytest.fixture
def minimal_scenario_yaml():
    """Minimal valid scenario YAML."""
    return """
name: Test Scenario
start_time: "2024-01-15T09:00:00-05:00"

agents:
  - agent_id: AGENT001
    full_name: Test Agent
    skillsets: [SkillA]

requests:
  - request_id: REQ001
    skill_id: SkillA
"""


@pytest.fixture
def complete_scenario_yaml():
    """Complete scenario with all features."""
    return """
name: Complete Scenario
description: Full-featured test scenario
start_time: "2024-01-15T09:00:00-05:00"

routing_config:
  pilot_program_enabled: true

agents:
  - agent_id: AGENT001
    full_name: Alice Johnson
    skillsets: [SkillA, SkillB]
  
  - agent_id: AGENT002
    full_name: Bob Smith
    skillsets: [SkillA]
    is_absent: true

requests:
  - request_id: REQ001
    skill_id: SkillA
    order_date_offset_hours: -24
    foc_target: 7.0
    is_escalated: true
  
  - request_id: REQ002
    skill_id: SkillB
    order_date: "2024-01-14T10:00:00-05:00"
    sticky_agent_id: AGENT001
    workorder_status: customerreplied
    workorder_expected_completion_date_offset_hours: -12
    is_winback: true
    has_sla: true
"""


# ============================================================================
# Test Basic Loading
# ============================================================================

def test_loader_initialization(loader):
    """Test that loader initializes correctly."""
    assert loader is not None
    assert loader.required_scenario_keys == ['name', 'start_time', 'agents', 'requests']
    assert loader.required_agent_keys == ['agent_id', 'full_name', 'skillsets']
    assert loader.required_request_keys == ['request_id', 'skill_id']


def test_load_minimal_scenario(loader, temp_dir, minimal_scenario_yaml):
    """Test loading minimal valid scenario."""
    # Write scenario to file
    filepath = os.path.join(temp_dir, 'test_scenario.yaml')
    with open(filepath, 'w') as f:
        f.write(minimal_scenario_yaml)
    
    # Load scenario
    scenario = loader.load_scenario(filepath)
    
    # Verify structure
    assert scenario['name'] == 'Test Scenario'
    assert 'start_time' in scenario
    assert isinstance(scenario['start_time'], datetime)
    assert len(scenario['agents']) == 1
    assert len(scenario['requests']) == 1
    assert isinstance(scenario['routing_config'], RoutingConfig)


def test_load_complete_scenario(loader, temp_dir, complete_scenario_yaml):
    """Test loading complete scenario with all features."""
    filepath = os.path.join(temp_dir, 'complete_scenario.yaml')
    with open(filepath, 'w') as f:
        f.write(complete_scenario_yaml)
    
    scenario = loader.load_scenario(filepath)
    
    # Verify metadata
    assert scenario['name'] == 'Complete Scenario'
    assert scenario['description'] == 'Full-featured test scenario'
    assert scenario['filepath'] == filepath
    
    # Verify agents
    assert len(scenario['agents']) == 2
    assert all(isinstance(agent, Agent) for agent in scenario['agents'])
    
    # Verify requests
    assert len(scenario['requests']) == 2
    assert all(isinstance(req, Request) for req in scenario['requests'])
    
    # Verify routing config
    assert isinstance(scenario['routing_config'], RoutingConfig)
    assert scenario['routing_config'].pilot_program_enabled is True


def test_load_nonexistent_file(loader):
    """Test loading from nonexistent file raises error."""
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader.load_scenario('nonexistent_file.yaml')
    
    assert 'not found' in str(exc_info.value).lower()


def test_load_empty_file(loader, temp_dir):
    """Test loading empty file raises error."""
    filepath = os.path.join(temp_dir, 'empty.yaml')
    with open(filepath, 'w') as f:
        f.write('')
    
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader.load_scenario(filepath)
    
    assert 'empty' in str(exc_info.value).lower()


def test_load_invalid_yaml(loader, temp_dir):
    """Test loading invalid YAML raises error."""
    filepath = os.path.join(temp_dir, 'invalid.yaml')
    with open(filepath, 'w') as f:
        f.write('invalid: yaml: content:')
    
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader.load_scenario(filepath)
    
    assert 'yaml' in str(exc_info.value).lower()


# ============================================================================
# Test Structure Validation
# ============================================================================

def test_validate_missing_name(loader, temp_dir):
    """Test validation catches missing 'name' field."""
    yaml_content = """
start_time: "2024-01-15T09:00:00-05:00"
agents:
  - agent_id: AGENT001
    full_name: Test
    skillsets: [SkillA]
requests:
  - request_id: REQ001
    skill_id: SkillA
"""
    filepath = os.path.join(temp_dir, 'no_name.yaml')
    with open(filepath, 'w') as f:
        f.write(yaml_content)
    
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader.load_scenario(filepath)
    
    assert 'missing required keys' in str(exc_info.value).lower()
    assert 'name' in str(exc_info.value).lower()


def test_validate_missing_start_time(loader, temp_dir):
    """Test validation catches missing 'start_time' field."""
    yaml_content = """
name: Test
agents:
  - agent_id: AGENT001
    full_name: Test
    skillsets: [SkillA]
requests:
  - request_id: REQ001
    skill_id: SkillA
"""
    filepath = os.path.join(temp_dir, 'no_start_time.yaml')
    with open(filepath, 'w') as f:
        f.write(yaml_content)
    
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader.load_scenario(filepath)
    
    assert 'missing required keys' in str(exc_info.value).lower()
    assert 'start_time' in str(exc_info.value).lower()


def test_validate_agents_not_list(loader, temp_dir):
    """Test validation catches non-list agents field."""
    yaml_content = """
name: Test
start_time: "2024-01-15T09:00:00-05:00"
agents: not_a_list
requests:
  - request_id: REQ001
    skill_id: SkillA
"""
    filepath = os.path.join(temp_dir, 'agents_not_list.yaml')
    with open(filepath, 'w') as f:
        f.write(yaml_content)
    
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader.load_scenario(filepath)
    
    assert 'agents' in str(exc_info.value).lower()
    assert 'must be a list' in str(exc_info.value).lower()


def test_validate_requests_not_list(loader, temp_dir):
    """Test validation catches non-list requests field."""
    yaml_content = """
name: Test
start_time: "2024-01-15T09:00:00-05:00"
agents:
  - agent_id: AGENT001
    full_name: Test
    skillsets: [SkillA]
requests: not_a_list
"""
    filepath = os.path.join(temp_dir, 'requests_not_list.yaml')
    with open(filepath, 'w') as f:
        f.write(yaml_content)
    
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader.load_scenario(filepath)
    
    assert 'requests' in str(exc_info.value).lower()
    assert 'must be a list' in str(exc_info.value).lower()


# ============================================================================
# Test Start Time Parsing
# ============================================================================

def test_parse_start_time_iso_format(loader):
    """Test parsing ISO format datetime."""
    dt = loader._parse_start_time("2024-01-15T09:00:00-05:00")
    
    assert isinstance(dt, datetime)
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 15
    assert dt.hour == 9
    assert dt.tzinfo is not None


def test_parse_start_time_date_only(loader):
    """Test parsing date-only format (assumes EST)."""
    dt = loader._parse_start_time("2024-01-15")
    
    assert isinstance(dt, datetime)
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 15
    assert dt.tzinfo is not None


def test_parse_start_time_no_timezone_adds_est(loader):
    """Test that datetime without timezone gets EST added."""
    dt = loader._parse_start_time("2024-01-15T09:00:00")
    
    assert dt.tzinfo is not None
    # EST is UTC-5
    assert dt.utcoffset() == timedelta(hours=-5)


def test_parse_start_time_invalid_format(loader):
    """Test parsing invalid format raises error."""
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader._parse_start_time("not-a-date")
    
    assert 'invalid start_time format' in str(exc_info.value).lower()


# ============================================================================
# Test Routing Config Building
# ============================================================================

def test_build_routing_config_with_all_fields(loader):
    """Test building routing config with all fields specified."""
    config_data = {
        'pilot_program_enabled': False
    }
    
    config = loader._build_routing_config(config_data)
    
    assert isinstance(config, RoutingConfig)
    assert config.pilot_program_enabled is False


def test_build_routing_config_with_defaults(loader):
    """Test building routing config with empty dict uses defaults."""
    config = loader._build_routing_config({})
    
    assert isinstance(config, RoutingConfig)
    assert config.pilot_program_enabled is True  # Default


def test_build_routing_config_partial(loader):
    """Test building routing config with some fields specified."""
    config_data = {
        'pilot_program_enabled': False
        # Other fields should use defaults
    }
    
    config = loader._build_routing_config(config_data)
    
    assert config.pilot_program_enabled is False


# ============================================================================
# Test Agent Building
# ============================================================================

def test_build_agents_basic(loader):
    """Test building agents with required fields only."""
    agents_data = [
        {
            'agent_id': 'AGENT001',
            'full_name': 'Test Agent',
            'skillsets': ['SkillA']
        }
    ]
    
    agents = loader._build_agents(agents_data)
    
    assert len(agents) == 1
    assert isinstance(agents[0], Agent)
    assert agents[0].agent_id == 'AGENT001'
    assert agents[0].full_name == 'Test Agent'
    assert 'SkillA' in agents[0].skillsets


def test_build_agents_with_optional_fields(loader):
    """Test building agents with optional fields."""
    agents_data = [
        {
            'agent_id': 'AGENT001',
            'full_name': 'Test Agent',
            'skillsets': ['SkillA'],
            'is_absent': True,
        }
    ]
    
    agents = loader._build_agents(agents_data)
    
    assert agents[0].is_absent is True


def test_build_agents_skillsets_as_string(loader):
    """Test that skillsets as string is converted to set."""
    agents_data = [
        {
            'agent_id': 'AGENT001',
            'full_name': 'Test Agent',
            'skillsets': 'SkillA'  # String, not list
        }
    ]
    
    agents = loader._build_agents(agents_data)
    
    assert isinstance(agents[0].skillsets, set)
    assert 'SkillA' in agents[0].skillsets


def test_build_agents_skillsets_as_list(loader):
    """Test that skillsets as list is converted to set."""
    agents_data = [
        {
            'agent_id': 'AGENT001',
            'full_name': 'Test Agent',
            'skillsets': ['SkillA', 'SkillB']
        }
    ]
    
    agents = loader._build_agents(agents_data)
    
    assert isinstance(agents[0].skillsets, set)
    assert 'SkillA' in agents[0].skillsets
    assert 'SkillB' in agents[0].skillsets


def test_build_agents_missing_required_field(loader):
    """Test that missing required field raises error."""
    agents_data = [
        {
            'agent_id': 'AGENT001',
            'full_name': 'Test Agent'
            # Missing skillsets
        }
    ]
    
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader._build_agents(agents_data)
    
    assert 'agent 0' in str(exc_info.value).lower()
    assert 'missing required keys' in str(exc_info.value).lower()


def test_build_agents_multiple(loader):
    """Test building multiple agents."""
    agents_data = [
        {
            'agent_id': 'AGENT001',
            'full_name': 'Agent 1',
            'skillsets': ['SkillA']
        },
        {
            'agent_id': 'AGENT002',
            'full_name': 'Agent 2',
            'skillsets': ['SkillB']
        },
        {
            'agent_id': 'AGENT003',
            'full_name': 'Agent 3',
            'skillsets': ['SkillA', 'SkillB']
        }
    ]
    
    agents = loader._build_agents(agents_data)
    
    assert len(agents) == 3
    assert all(isinstance(agent, Agent) for agent in agents)
    assert agents[0].agent_id == 'AGENT001'
    assert agents[1].agent_id == 'AGENT002'
    assert agents[2].agent_id == 'AGENT003'


# ============================================================================
# Test Request Building - Date Handling
# ============================================================================

def test_parse_request_date_relative_offset(loader):
    """Test parsing relative date offset."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    req_data = {'order_date_offset_hours': -24}
    
    order_date = loader._parse_request_date(req_data, start_time, 0)
    
    expected = start_time - timedelta(hours=24)
    assert order_date == expected


def test_parse_request_date_absolute(loader):
    """Test parsing absolute date."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    req_data = {'order_date': '2024-01-14T10:00:00-05:00'}
    
    order_date = loader._parse_request_date(req_data, start_time, 0)
    
    assert order_date.year == 2024
    assert order_date.month == 1
    assert order_date.day == 14
    assert order_date.hour == 10


def test_parse_request_date_default_to_start_time(loader):
    """Test that missing date defaults to start_time."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    req_data = {}  # No date specified
    
    order_date = loader._parse_request_date(req_data, start_time, 0)
    
    assert order_date == start_time


def test_parse_request_date_relative_takes_precedence(loader):
    """Test that relative offset takes precedence over absolute."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    req_data = {
        'order_date_offset_hours': -24,
        'order_date': '2024-01-14T10:00:00-05:00'
    }
    
    order_date = loader._parse_request_date(req_data, start_time, 0)
    
    # Should use offset, not absolute
    expected = start_time - timedelta(hours=24)
    assert order_date == expected


# ============================================================================
# Test Request Building
# ============================================================================

def test_build_requests_basic(loader):
    """Test building requests with required fields only."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    requests_data = [
        {
            'request_id': 'REQ001',
            'skill_id': 'SkillA'
        }
    ]
    
    requests = loader._build_requests(requests_data, start_time)
    
    assert len(requests) == 1
    assert isinstance(requests[0], Request)
    assert requests[0].request_id == 'REQ001'
    assert requests[0].skill_id == 'SkillA'
    assert requests[0].order_date == start_time  # Default


def test_build_requests_with_all_optional_fields(loader):
    """Test building request with all optional fields."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    requests_data = [
        {
            'request_id': 'REQ001',
            'skill_id': 'SkillA',
            'external_id': 'EXT_REQ001',
            'request_source': 'email',
            'product': 'ProductB',
            'service_region': 'Quebec',
            'request_type': 'support',
            'order_date_offset_hours': -24,
            'foc_target': 5.0,
            'sticky_agent_id': 'AGENT001',
            'workorder_status': 'customerreplied',
            'workorder_expected_completion_date_offset_hours': -12,
            'is_escalated': True,
            'is_winback': True,
            'is_atl_rf': True,
            'has_sla': True
        }
    ]
    
    requests = loader._build_requests(requests_data, start_time)
    
    req = requests[0]
    assert req.external_id == 'EXT_REQ001'
    assert req.request_source == 'email'
    assert req.product == 'ProductB'
    assert req.service_region == 'Quebec'
    assert req.request_type == 'support'
    assert req.foc_target == 5.0
    assert req.sticky_agent_id == 'AGENT001'
    assert req.workorder_status == 'customerreplied'
    assert req.workorder_expected_completion_date is not None
    assert req.is_escalated is True
    assert req.is_winback is True
    assert req.is_atl_rf is True
    assert req.has_sla is True


def test_build_requests_defaults(loader):
    """Test that optional fields use proper defaults."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    requests_data = [
        {
            'request_id': 'REQ001',
            'skill_id': 'SkillA'
        }
    ]
    
    requests = loader._build_requests(requests_data, start_time)
    
    req = requests[0]
    assert req.external_id == 'REQ001'  # Defaults to request_id
    assert req.request_source == 'web'  # Default
    assert req.product == 'ProductA'  # Default
    assert req.service_region == 'Ontario'  # Default
    assert req.request_type == 'service'  # Default
    assert req.is_escalated is False  # Default
    assert req.is_winback is False  # Default


def test_build_requests_missing_required_field(loader):
    """Test that missing required field raises error."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    requests_data = [
        {
            'request_id': 'REQ001'
            # Missing skill_id
        }
    ]
    
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader._build_requests(requests_data, start_time)
    
    assert 'request 0' in str(exc_info.value).lower()
    assert 'missing required keys' in str(exc_info.value).lower()


def test_build_requests_multiple(loader):
    """Test building multiple requests."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    requests_data = [
        {
            'request_id': 'REQ001',
            'skill_id': 'SkillA',
            'order_date_offset_hours': -24
        },
        {
            'request_id': 'REQ002',
            'skill_id': 'SkillB',
            'order_date_offset_hours': -48
        },
        {
            'request_id': 'REQ003',
            'skill_id': 'SkillA',
            'order_date_offset_hours': -72
        }
    ]
    
    requests = loader._build_requests(requests_data, start_time)
    
    assert len(requests) == 3
    assert all(isinstance(req, Request) for req in requests)
    assert requests[0].request_id == 'REQ001'
    assert requests[1].request_id == 'REQ002'
    assert requests[2].request_id == 'REQ003'


def test_build_requests_workorder_ecd_relative(loader):
    """Test workorder_expected_completion_date with relative offset."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    requests_data = [
        {
            'request_id': 'REQ001',
            'skill_id': 'SkillA',
            'workorder_expected_completion_date_offset_hours': -24
        }
    ]
    
    requests = loader._build_requests(requests_data, start_time)
    
    req = requests[0]
    expected_ecd = start_time - timedelta(hours=24)
    assert req.workorder_expected_completion_date == expected_ecd


def test_build_requests_workorder_ecd_absolute(loader):
    """Test workorder_expected_completion_date with absolute date."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    requests_data = [
        {
            'request_id': 'REQ001',
            'skill_id': 'SkillA',
            'workorder_expected_completion_date': '2024-01-14T10:00:00-05:00'
        }
    ]
    
    requests = loader._build_requests(requests_data, start_time)
    
    req = requests[0]
    assert req.workorder_expected_completion_date.day == 14
    assert req.workorder_expected_completion_date.hour == 10


# ============================================================================
# Test Multiple Scenario Loading
# ============================================================================

def test_load_multiple_scenarios_from_directory(loader, temp_dir):
    """Test loading all scenarios from directory."""
    # Create multiple scenario files
    scenario1 = """
name: Scenario 1
start_time: "2024-01-15T09:00:00-05:00"
agents:
  - agent_id: AGENT001
    full_name: Test
    skillsets: [SkillA]
requests:
  - request_id: REQ001
    skill_id: SkillA
"""
    
    scenario2 = """
name: Scenario 2
start_time: "2024-01-15T10:00:00-05:00"
agents:
  - agent_id: AGENT002
    full_name: Test
    skillsets: [SkillB]
requests:
  - request_id: REQ002
    skill_id: SkillB
"""
    
    with open(os.path.join(temp_dir, 'scenario1.yaml'), 'w') as f:
        f.write(scenario1)
    
    with open(os.path.join(temp_dir, 'scenario2.yaml'), 'w') as f:
        f.write(scenario2)
    
    # Load all scenarios
    scenarios = loader.load_multiple_scenarios(temp_dir)
    
    assert len(scenarios) == 2
    assert scenarios[0]['name'] in ['Scenario 1', 'Scenario 2']
    assert scenarios[1]['name'] in ['Scenario 1', 'Scenario 2']


def test_load_multiple_scenarios_empty_directory(loader, temp_dir):
    """Test loading from empty directory raises error."""
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader.load_multiple_scenarios(temp_dir)
    
    assert 'no yaml files found' in str(exc_info.value).lower()


def test_load_multiple_scenarios_nonexistent_directory(loader):
    """Test loading from nonexistent directory raises error."""
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader.load_multiple_scenarios('nonexistent_directory')
    
    assert 'directory not found' in str(exc_info.value).lower()


def test_load_multiple_scenarios_with_failures(loader, temp_dir):
    """Test loading multiple scenarios when some fail."""
    # Valid scenario
    valid = """
name: Valid Scenario
start_time: "2024-01-15T09:00:00-05:00"
agents:
  - agent_id: AGENT001
    full_name: Test
    skillsets: [SkillA]
requests:
  - request_id: REQ001
    skill_id: SkillA
"""
    
    # Invalid scenario (missing required field)
    invalid = """
name: Invalid Scenario
agents:
  - agent_id: AGENT002
    full_name: Test
    skillsets: [SkillA]
requests:
  - request_id: REQ002
    skill_id: SkillA
"""
    
    with open(os.path.join(temp_dir, 'valid.yaml'), 'w') as f:
        f.write(valid)
    
    with open(os.path.join(temp_dir, 'invalid.yaml'), 'w') as f:
        f.write(invalid)
    
    # Should load valid scenario and log warning about invalid
    scenarios = loader.load_multiple_scenarios(temp_dir)
    
    assert len(scenarios) == 1
    assert scenarios[0]['name'] == 'Valid Scenario'


def test_load_multiple_scenarios_all_fail(loader, temp_dir):
    """Test loading when all scenarios fail."""
    # Invalid scenario
    invalid = """
name: Invalid
agents: not_a_list
requests: not_a_list
"""
    
    with open(os.path.join(temp_dir, 'invalid.yaml'), 'w') as f:
        f.write(invalid)
    
    # Should raise error when all fail
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader.load_multiple_scenarios(temp_dir)
    
    assert 'failed to load any scenarios' in str(exc_info.value).lower()


# ============================================================================
# Test Edge Cases
# ============================================================================

def test_build_agents_empty_list(loader):
    """Test building agents from empty list."""
    agents = loader._build_agents([])
    
    assert len(agents) == 0


def test_build_requests_empty_list(loader):
    """Test building requests from empty list."""
    start_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    requests = loader._build_requests([], start_time)
    
    assert len(requests) == 0


def test_load_scenario_with_yml_extension(loader, temp_dir):
    """Test loading scenario with .yml extension."""
    scenario = """
name: Test Scenario
start_time: "2024-01-15T09:00:00-05:00"
agents:
  - agent_id: AGENT001
    full_name: Test
    skillsets: [SkillA]
requests:
  - request_id: REQ001
    skill_id: SkillA
"""
    
    filepath = os.path.join(temp_dir, 'test.yml')
    with open(filepath, 'w') as f:
        f.write(scenario)
    
    loaded = loader.load_scenario(filepath)
    
    assert loaded['name'] == 'Test Scenario'


def test_build_agents_skillsets_invalid_type(loader):
    """Test that invalid skillsets type raises error."""
    agents_data = [
        {
            'agent_id': 'AGENT001',
            'full_name': 'Test',
            'skillsets': 123  # Invalid: not string or list
        }
    ]
    
    with pytest.raises(ScenarioLoadError) as exc_info:
        loader._build_agents(agents_data)
    
    assert 'skillsets must be string or list' in str(exc_info.value).lower()


def test_scenario_includes_filepath(loader, temp_dir, minimal_scenario_yaml):
    """Test that loaded scenario includes filepath."""
    filepath = os.path.join(temp_dir, 'test.yaml')
    with open(filepath, 'w') as f:
        f.write(minimal_scenario_yaml)
    
    scenario = loader.load_scenario(filepath)
    
    assert 'filepath' in scenario
    assert scenario['filepath'] == filepath