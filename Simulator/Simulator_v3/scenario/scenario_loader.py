"""
Scenario Loader for STM Routing Simulator v3.0.

This module handles loading simulation scenarios from YAML configuration files.
It parses the YAML, validates the structure, and constructs the necessary
objects (Agents, Requests, RoutingConfig) for the simulation.

Example YAML structure:
    name: Basic Scenario
    description: Simple test scenario
    start_time: "2024-01-15T09:00:00-05:00"
    
    routing_config:
      pilot_program_enabled: true
      followup_time_start: "08:00"
      followup_time_end: "17:00"
    
    agents:
      - agent_id: AGENT001
        full_name: John Doe
        skillsets: [SkillA, SkillB]
      - agent_id: AGENT002
        full_name: Jane Smith
        skillsets: [SkillA]
        is_absent: true
    
    requests:
      - request_id: REQ001
        skill_id: SkillA
        order_date_offset_hours: -24
        is_escalated: true
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from pathlib import Path
import yaml
from dateutil import parser as date_parser

from models.agent import Agent
from models.request import Request
from config.scenario_config import RoutingConfig


class ScenarioLoadError(Exception):
    """Exception raised when scenario loading fails."""
    pass


class ScenarioLoader:
    """
    Loads simulation scenarios from YAML configuration files.
    
    The loader parses YAML files and constructs Agent, Request, and
    RoutingConfig objects ready for simulation.
    
    Example:
        >>> loader = ScenarioLoader()
        >>> scenario = loader.load_scenario('scenarios/basic_scenario.yaml')
        >>> print(f"Loaded: {scenario['name']}")
        >>> print(f"Agents: {len(scenario['agents'])}")
        >>> print(f"Requests: {len(scenario['requests'])}")
    """
    
    def __init__(self):
        """Initialize the scenario loader."""
        self.required_scenario_keys = ['name', 'start_time', 'agents', 'requests']
        self.required_agent_keys = ['agent_id', 'full_name', 'skillsets']
        self.required_request_keys = ['request_id', 'skill_id']
    
    def load_scenario(self, filepath: str) -> Dict[str, Any]:
        """
        Load a scenario from a YAML file.
        
        Args:
            filepath: Path to the YAML scenario file
            
        Returns:
            Dict containing:
                - name: Scenario name
                - description: Scenario description (optional)
                - start_time: Simulation start time (datetime)
                - agents: List of Agent objects
                - requests: List of Request objects
                - routing_config: RoutingConfig object
                
        Raises:
            ScenarioLoadError: If file not found or invalid format
            
        Example:
            >>> scenario = loader.load_scenario('scenarios/basic_scenario.yaml')
        """
        # Load YAML file
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise ScenarioLoadError(f"Scenario file not found: {filepath}")
        except yaml.YAMLError as e:
            raise ScenarioLoadError(f"Invalid YAML format: {e}")
        
        if not data:
            raise ScenarioLoadError(f"Empty scenario file: {filepath}")
        
        # Validate structure
        self._validate_scenario_structure(data)
        
        # Parse start time
        start_time = self._parse_start_time(data['start_time'])
        
        # Build routing config
        routing_config = self._build_routing_config(data.get('routing_config', {}))
        
        # Build agents
        agents = self._build_agents(data['agents'])
        
        # Build requests
        requests = self._build_requests(data['requests'], start_time)
        
        return {
            'name': data['name'],
            'description': data.get('description', ''),
            'filepath': filepath,
            'start_time': start_time,
            'agents': agents,
            'requests': requests,
            'routing_config': routing_config
        }
    
    def _validate_scenario_structure(self, data: Dict[str, Any]) -> None:
        """
        Validate that scenario has required keys.
        
        Args:
            data: Parsed YAML data
            
        Raises:
            ScenarioLoadError: If required keys are missing
        """
        missing_keys = [key for key in self.required_scenario_keys if key not in data]
        if missing_keys:
            raise ScenarioLoadError(f"Missing required keys: {missing_keys}")
        
        # Validate agents is a list
        if not isinstance(data['agents'], list):
            raise ScenarioLoadError("'agents' must be a list")
        
        # Validate requests is a list
        if not isinstance(data['requests'], list):
            raise ScenarioLoadError("'requests' must be a list")
    
    def _parse_start_time(self, start_time_str: str) -> datetime:
        """
        Parse start time string to datetime object.
        
        Supports multiple formats:
        - ISO format: "2024-01-15T09:00:00-05:00"
        - Date only: "2024-01-15" (assumes 09:00:00 EST)
        
        Args:
            start_time_str: Time string from YAML
            
        Returns:
            datetime: Parsed datetime with timezone
            
        Raises:
            ScenarioLoadError: If parsing fails
        """
        try:
            dt = date_parser.parse(start_time_str)
            
            # If no timezone, assume EST (UTC-5)
            if dt.tzinfo is None:
                # EST is UTC-5
                from datetime import timezone as tz
                est = tz(timedelta(hours=-5))
                dt = dt.replace(tzinfo=est)
            
            return dt
        except (ValueError, TypeError) as e:
            raise ScenarioLoadError(f"Invalid start_time format: {start_time_str}. Error: {e}")
    
    def _build_routing_config(self, config_data: Dict[str, Any]) -> RoutingConfig:
        """
        Build RoutingConfig from YAML data.
        
        Args:
            config_data: Routing config section from YAML
            
        Returns:
            RoutingConfig: Configuration object
        """
        return RoutingConfig(
            pilot_program_enabled=config_data.get('pilot_program_enabled', True)
        )
    
    def _build_agents(self, agents_data: List[Dict[str, Any]]) -> List[Agent]:
        """
        Build list of Agent objects from YAML data.
        
        Args:
            agents_data: List of agent definitions from YAML
            
        Returns:
            List[Agent]: Constructed agent objects
            
        Raises:
            ScenarioLoadError: If agent data is invalid
        """
        agents = []
        
        for i, agent_data in enumerate(agents_data):
            # Validate required keys
            missing_keys = [key for key in self.required_agent_keys if key not in agent_data]
            if missing_keys:
                raise ScenarioLoadError(f"Agent {i}: Missing required keys: {missing_keys}")
            
            # Convert skillsets to set
            skillsets = agent_data['skillsets']
            if isinstance(skillsets, str):
                skillsets = {skillsets}
            elif isinstance(skillsets, list):
                skillsets = set(skillsets)
            else:
                raise ScenarioLoadError(f"Agent {i}: skillsets must be string or list")
            
            # Create agent
            try:
                agent = Agent(
                    agent_id=agent_data['agent_id'],
                    full_name=agent_data['full_name'],
                    skillsets=skillsets,
                    is_absent=agent_data.get('is_absent', False)
                    # Note: is_in_pilot_program is not a constructor parameter
                    # It should be set separately if needed in the future
                )
                agents.append(agent)
            except Exception as e:
                raise ScenarioLoadError(f"Agent {i} ({agent_data.get('agent_id', 'unknown')}): {e}")
        
        return agents

    def _build_requests(
        self, 
        requests_data: List[Dict[str, Any]], 
        start_time: datetime
    ) -> List[Request]:
        """
        Build list of Request objects from YAML data.
        
        Requests can specify order_date in two ways:
        1. Absolute: order_date: "2024-01-15T08:00:00-05:00"
        2. Relative: order_date_offset_hours: -24 (24 hours before start_time)
        
        Args:
            requests_data: List of request definitions from YAML
            start_time: Simulation start time (for relative dates)
            
        Returns:
            List[Request]: Constructed request objects
            
        Raises:
            ScenarioLoadError: If request data is invalid
        """
        requests = []
        
        for i, req_data in enumerate(requests_data):
            # Validate required keys
            missing_keys = [key for key in self.required_request_keys if key not in req_data]
            if missing_keys:
                raise ScenarioLoadError(f"Request {i}: Missing required keys: {missing_keys}")
            
            # Parse order_date
            order_date = self._parse_request_date(req_data, start_time, i)
            
            # Parse optional dates
            workorder_ecd = None
            if 'workorder_expected_completion_date_offset_hours' in req_data:
                offset = req_data['workorder_expected_completion_date_offset_hours']
                workorder_ecd = start_time + timedelta(hours=offset)
            elif 'workorder_expected_completion_date' in req_data:
                workorder_ecd = date_parser.parse(req_data['workorder_expected_completion_date'])
            
            # Create request
            try:
                request = Request(
                    request_id=req_data['request_id'],
                    external_id=req_data.get('external_id', req_data['request_id']),
                    skill_id=req_data['skill_id'],
                    request_source=req_data.get('request_source', 'web'),
                    product=req_data.get('product', 'ProductA'),
                    service_region=req_data.get('service_region', 'Ontario'),
                    request_type=req_data.get('request_type', 'service'),
                    order_date=order_date,
                    foc_target=req_data.get('foc_target'),
                    sticky_agent_id=req_data.get('sticky_agent_id'),
                    workorder_status=req_data.get('workorder_status'),
                    workorder_expected_completion_date=workorder_ecd,
                    is_escalated=req_data.get('is_escalated', False),
                    is_winback=req_data.get('is_winback', False),
                    is_atl_rf=req_data.get('is_atl_rf', False),
                    has_sla=req_data.get('has_sla', False)
                )
                requests.append(request)
            except Exception as e:
                raise ScenarioLoadError(f"Request {i} ({req_data.get('request_id', 'unknown')}): {e}")
        
        return requests
    
    def _parse_request_date(
        self, 
        req_data: Dict[str, Any], 
        start_time: datetime, 
        index: int
    ) -> datetime:
        """
        Parse request order_date from absolute or relative format.
        
        Args:
            req_data: Request data dictionary
            start_time: Simulation start time
            index: Request index (for error messages)
            
        Returns:
            datetime: Parsed order date
            
        Raises:
            ScenarioLoadError: If date parsing fails
        """
        # Try relative offset first (most common)
        if 'order_date_offset_hours' in req_data:
            offset_hours = req_data['order_date_offset_hours']
            return start_time + timedelta(hours=offset_hours)
        
        # Try absolute date
        if 'order_date' in req_data:
            try:
                return date_parser.parse(req_data['order_date'])
            except (ValueError, TypeError) as e:
                raise ScenarioLoadError(f"Request {index}: Invalid order_date format: {e}")
        
        # Default to start_time if neither provided
        return start_time
    
    def load_multiple_scenarios(self, directory: str) -> List[Dict[str, Any]]:
        """
        Load all scenario files from a directory.
        
        Args:
            directory: Path to directory containing .yaml files
            
        Returns:
            List[Dict]: List of loaded scenarios
            
        Example:
            >>> scenarios = loader.load_multiple_scenarios('scenarios/')
            >>> for scenario in scenarios:
            ...     print(f"Loaded: {scenario['name']}")
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise ScenarioLoadError(f"Directory not found: {directory}")
        
        yaml_files = list(dir_path.glob('*.yaml')) + list(dir_path.glob('*.yml'))
        
        if not yaml_files:
            raise ScenarioLoadError(f"No YAML files found in: {directory}")
        
        scenarios = []
        errors = []
        
        for filepath in yaml_files:
            try:
                scenario = self.load_scenario(str(filepath))
                scenarios.append(scenario)
            except ScenarioLoadError as e:
                errors.append(f"{filepath.name}: {e}")
        
        if errors and not scenarios:
            # All scenarios failed
            raise ScenarioLoadError("Failed to load any scenarios:\n" + "\n".join(errors))
        
        if errors:
            # Some scenarios failed - log warnings
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Some scenarios failed to load:\n" + "\n".join(errors))
        
        return scenarios