"""
Data loading utilities for STM Simulator v3.0

This module provides functions to load agent data from various sources
(CSV files, DataFrames, databases) and convert them into Agent objects.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import logging

from .agent import Agent
from .request import Request, RequestState

# Set up logger
logger = logging.getLogger(__name__)


# ============================================================================
# CSV LOADING FUNCTIONS
# ============================================================================

def load_agents_from_csv(
    csv_path: Path,
    required_columns: Optional[List[str]] = None
) -> List[Agent]:
    """
    Load agents from a CSV file.
    
    The CSV file should have columns matching agent attributes:
    - agent_id (required)
    - full_name (required)
    - skillsets (comma-separated skill IDs, optional)
    - manager_name (optional)
    - cp2_name (optional)
    - cp3_name (optional)
    
    Args:
        csv_path: Path to the CSV file
        required_columns: List of columns that must be present (default: ['agent_id', 'full_name'])
        
    Returns:
        List[Agent]: List of Agent objects
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If required columns are missing
        
    Example:
        >>> agents = load_agents_from_csv(Path("agents.csv"))
        >>> len(agents)
        50
        >>> agents[0].agent_id
        'john.doe'
    """
    # Validate file exists
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    logger.info(f"Loading agents from CSV: {csv_path}")
    
    # Read CSV
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}")
    
    # Validate required columns
    if required_columns is None:
        required_columns = ['agent_id', 'full_name']
    
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"CSV missing required columns: {missing_columns}. "
            f"Found columns: {list(df.columns)}"
        )
    
    # Convert DataFrame to agents
    agents = load_agents_from_dataframe(df)
    
    logger.info(f"Successfully loaded {len(agents)} agents from CSV")
    
    return agents


def load_agents_from_dataframe(df: pd.DataFrame) -> List[Agent]:
    """
    Convert a pandas DataFrame to a list of Agent objects.
    
    Args:
        df: DataFrame with agent data
        
    Returns:
        List[Agent]: List of Agent objects
        
    Raises:
        ValueError: If required columns are missing or data is invalid
        
    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     'agent_id': ['john.doe', 'jane.smith'],
        ...     'full_name': ['John Doe', 'Jane Smith'],
        ...     'skillsets': ['internet,voice', 'tv,internet']
        ... })
        >>> agents = load_agents_from_dataframe(df)
        >>> len(agents)
        2
    """
    # Validate required columns
    required_columns = ['agent_id', 'full_name']
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"DataFrame missing required columns: {missing_columns}")
    
    agents = []
    errors = []
    
    # Process each row
    for idx, row in df.iterrows():
        try:
            agent = _create_agent_from_row(row, row_index=idx)
            agents.append(agent)
        except Exception as e:
            error_msg = f"Row {idx}: {e}"
            errors.append(error_msg)
            logger.warning(f"Failed to create agent from row {idx}: {e}")
    
    # Report errors if any
    if errors:
        logger.warning(f"Failed to create {len(errors)} agents out of {len(df)} rows")
        if len(errors) == len(df):
            # All rows failed - this is a critical error
            raise ValueError(
                "Failed to create any agents. Errors:\n" + "\n".join(errors[:5])
            )
    
    return agents


def _create_agent_from_row(row: pd.Series, row_index: int) -> Agent:
    """
    Create an Agent from a DataFrame row.
    
    Internal helper function that handles data type conversions and parsing.
    
    Args:
        row: pandas Series representing one row
        row_index: Index of the row (for error messages)
        
    Returns:
        Agent: New agent instance
        
    Raises:
        ValueError: If required data is missing or invalid
    """
    # Extract required fields
    agent_id = row.get('agent_id')
    full_name = row.get('full_name')
    
    # Validate required fields
    if pd.isna(agent_id) or not str(agent_id).strip():
        raise ValueError("agent_id is missing or empty")
    if pd.isna(full_name) or not str(full_name).strip():
        raise ValueError("full_name is missing or empty")
    
    # Convert to strings and strip whitespace
    agent_id = str(agent_id).strip()
    full_name = str(full_name).strip()
    
    # Parse skillsets (can be comma-separated string or list)
    skillsets = _parse_skillsets(row.get('skillsets'))
    
    # Parse permissions (can be JSON string or dict)
    permissions = _parse_permissions(row.get('permissions'))
    
    # Extract optional fields
    manager_name = _get_optional_string(row, 'manager_name', 'person_manager_name')
    cp2_name = _get_optional_string(row, 'cp2_name', 'CP2_name')
    cp3_name = _get_optional_string(row, 'cp3_name', 'CP3_name')
    
    # Create agent
    try:
        agent = Agent(
            agent_id=agent_id,
            full_name=full_name,
            skillsets=skillsets,
            permissions=permissions,
            manager_name=manager_name,
            cp2_name=cp2_name,
            cp3_name=cp3_name
        )
        return agent
    except Exception as e:
        raise ValueError(f"Failed to create Agent: {e}")


def _parse_skillsets(value: Any) -> set:
    """
    Parse skillsets from various formats.
    
    Handles:
    - Comma-separated string: "internet,voice,tv"
    - List: ["internet", "voice", "tv"]
    - NaN/None: returns empty set
    
    Args:
        value: Raw skillsets value from data source
        
    Returns:
        set: Set of skill IDs
    """
    # Check for None first, then check type before using pd.isna()
    if value is None:
        return set()
    
    # For scalar values (not list/set), check for Nan
    if not isinstance(value, (list, set)):
        if pd.isna(value):
            return set()
    
    if isinstance(value, str):
        # Split by comma and strip whitespace
        skills = [s.strip() for s in value.split(',') if s.strip()]
        return set(skills)
    
    if isinstance(value, (list, set)):
        # Already a collection
        return set(str(s).strip() for s in value if not pd.isna(s))
    
    # Unknown format - return empty set
    logger.warning(f"Unknown skillsets format: {type(value)}")
    return set()


def _parse_permissions(value: Any) -> Dict[str, Any]:
    """
    Parse permissions from various formats.
    
    Handles:
    - JSON string: '{"region": "ontario", "product": "internet"}'
    - Dict: {"region": "ontario", "product": "internet"}
    - NaN/None: returns empty dict
    
    Args:
        value: Raw permissions value from data source
        
    Returns:
        Dict: Permissions dictionary
    """
    if pd.isna(value) or value is None:
        return {}
    
    if isinstance(value, dict):
        return value
    
    if isinstance(value, str):
        # Try to parse as JSON
        import json
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse permissions as JSON: {value}")
            return {}
    
    # Unknown format
    logger.warning(f"Unknown permissions format: {type(value)}")
    return {}


def _get_optional_string(row: pd.Series, *column_names: str) -> Optional[str]:
    """
    Get optional string value from row, trying multiple column names.
    
    This helps handle different naming conventions in data sources.
    
    Args:
        row: pandas Series
        column_names: Column names to try (in order)
        
    Returns:
        Optional[str]: The first non-null value found, or None
        
    Example:
        >>> row = pd.Series({'CP2_name': 'Toronto', 'cp2_name': None})
        >>> _get_optional_string(row, 'cp2_name', 'CP2_name')
        'Toronto'
    """
    for col_name in column_names:
        if col_name in row:
            value = row[col_name]
            if not pd.isna(value):
                return str(value).strip()
    return None


# ============================================================================
# BULK OPERATIONS
# ============================================================================

def create_agent_lookup(agents: List[Agent]) -> Dict[str, Agent]:
    """
    Create a lookup dictionary for fast agent retrieval by ID.
    
    Args:
        agents: List of agents
        
    Returns:
        Dict[str, Agent]: Dictionary mapping agent_id to Agent object
        
    Example:
        >>> agents = load_agents_from_csv(Path("agents.csv"))
        >>> lookup = create_agent_lookup(agents)
        >>> agent = lookup['john.doe']
        >>> agent.full_name
        'John Doe'
    """
    return {agent.agent_id: agent for agent in agents}


def filter_agents_by_skill(
    agents: List[Agent],
    skill_id: str
) -> List[Agent]:
    """
    Filter agents who have a specific skill.
    
    Args:
        agents: List of agents to filter
        skill_id: The skill ID to filter by
        
    Returns:
        List[Agent]: Agents with the specified skill
        
    Example:
        >>> agents = load_agents_from_csv(Path("agents.csv"))
        >>> internet_agents = filter_agents_by_skill(agents, "internet")
        >>> len(internet_agents)
        25
    """
    return [agent for agent in agents if agent.has_skill(skill_id)]


def filter_agents_by_skills(
    agents: List[Agent],
    skill_ids: List[str],
    require_all: bool = False
) -> List[Agent]:
    """
    Filter agents who have specific skills.
    
    Args:
        agents: List of agents to filter
        skill_ids: List of skill IDs
        require_all: If True, agent must have ALL skills. If False, agent needs ANY skill.
        
    Returns:
        List[Agent]: Filtered agents
        
    Example:
        >>> agents = load_agents_from_csv(Path("agents.csv"))
        >>> # Agents with EITHER internet OR voice
        >>> versatile = filter_agents_by_skills(agents, ["internet", "voice"], require_all=False)
        >>> # Agents with BOTH internet AND voice
        >>> specialists = filter_agents_by_skills(agents, ["internet", "voice"], require_all=True)
    """
    if require_all:
        return [agent for agent in agents if agent.has_all_skills(skill_ids)]
    else:
        return [agent for agent in agents if agent.has_any_skill(skill_ids)]


def get_agent_statistics(agents: List[Agent]) -> Dict[str, Any]:
    """
    Calculate statistics about a list of agents.
    
    Args:
        agents: List of agents
        
    Returns:
        Dict: Statistics including total count, unique skills, state distribution
        
    Example:
        >>> agents = load_agents_from_csv(Path("agents.csv"))
        >>> stats = get_agent_statistics(agents)
        >>> stats['total_agents']
        50
        >>> stats['unique_skills']
        ['internet', 'voice', 'tv']
    """
    if not agents:
        return {
            'total_agents': 0,
            'unique_skills': [],
            'state_distribution': {},
            'agents_with_skills': 0
        }
    
    # Collect all skills
    all_skills = set()
    for agent in agents:
        all_skills.update(agent.skillsets)
    
    # Count states
    state_counts = {}
    for agent in agents:
        state = agent.state.value
        state_counts[state] = state_counts.get(state, 0) + 1
    
    # Count agents with at least one skill
    agents_with_skills = sum(1 for agent in agents if len(agent.skillsets) > 0)
    
    return {
        'total_agents': len(agents),
        'unique_skills': sorted(list(all_skills)),
        'state_distribution': state_counts,
        'agents_with_skills': agents_with_skills,
        'avg_skills_per_agent': sum(len(a.skillsets) for a in agents) / len(agents)
    }


# ============================================================================
# VALIDATION
# ============================================================================

def validate_agent_data(agents: List[Agent]) -> Dict[str, Any]:
    """
    Validate a list of agents and return validation report.
    
    Checks for:
    - Duplicate agent IDs
    - Agents without skills
    - Agents without required attributes
    
    Args:
        agents: List of agents to validate
        
    Returns:
        Dict: Validation report with warnings and errors
        
    Example:
        >>> agents = load_agents_from_csv(Path("agents.csv"))
        >>> report = validate_agent_data(agents)
        >>> if report['errors']:
        ...     print("Validation failed!")
    """
    errors = []
    warnings = []
    
    # Check for duplicates
    agent_ids = [agent.agent_id for agent in agents]
    duplicates = [aid for aid in agent_ids if agent_ids.count(aid) > 1]
    if duplicates:
        errors.append(f"Duplicate agent IDs found: {set(duplicates)}")
    
    # Check for agents without skills
    no_skills = [agent.agent_id for agent in agents if len(agent.skillsets) == 0]
    if no_skills:
        warnings.append(
            f"{len(no_skills)} agents have no skills. "
            f"Examples: {no_skills[:3]}"
        )
    
    # Check for missing names
    no_name = [agent.agent_id for agent in agents if not agent.full_name]
    if no_name:
        errors.append(f"Agents without names: {no_name}")
    
    return {
        'valid': len(errors) == 0,
        'agent_count': len(agents),
        'errors': errors,
        'warnings': warnings
    }


# ============================================================================
# REQUEST LOADING FUNCTIONS (for Ticket #3)
# ============================================================================


def load_requests_from_csv(
    csv_path: Path,
    required_columns: Optional[List[str]] = None
) -> List[Request]:
    """
    Load requests from a CSV file.
    
    The CSV file should have columns matching request attributes:
    - request_id (required)
    - external_id (required)
    - skill_id (required)
    - request_source (required)
    - product (required)
    - service_region (required)
    - request_type (required)
    - order_date (required, ISO format with timezone)
    - foc_target (optional, default: 8.0)
    - has_sla (optional, default: false)
    - is_escalated (optional, default: false)
    - is_winback (optional, default: false)
    - And other optional fields...
    
    Args:
        csv_path: Path to the CSV file
        required_columns: List of columns that must be present
        
    Returns:
        List[Request]: List of Request objects
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If required columns are missing
        
    Example:
        >>> requests = load_requests_from_csv(Path("requests.csv"))
        >>> len(requests)
        100
        >>> requests[0].request_id
        'REQ_001'
    """
    # Validate file exists
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    logger.info(f"Loading requests from CSV: {csv_path}")
    
    # Read CSV
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}")
    
    # Validate required columns
    if required_columns is None:
        required_columns = [
            'request_id', 'external_id', 'skill_id', 'request_source',
            'product', 'service_region', 'request_type', 'order_date'
        ]
    
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"CSV missing required columns: {missing_columns}. "
            f"Found columns: {list(df.columns)}"
        )
    
    # Convert DataFrame to requests
    requests = load_requests_from_dataframe(df)
    
    logger.info(f"Successfully loaded {len(requests)} requests from CSV")
    
    return requests


def load_requests_from_dataframe(df: pd.DataFrame) -> List[Request]:
    """
    Convert a pandas DataFrame to a list of Request objects.
    
    Args:
        df: DataFrame with request data
        
    Returns:
        List[Request]: List of Request objects
        
    Raises:
        ValueError: If required columns are missing or data is invalid
        
    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     'request_id': ['REQ_001', 'REQ_002'],
        ...     'external_id': ['EXT_001', 'EXT_002'],
        ...     'skill_id': ['internet', 'voice'],
        ...     'request_source': ['bcom', 'residential'],
        ...     'product': ['internet', 'voice'],
        ...     'service_region': ['ontario', 'quebec'],
        ...     'request_type': ['new', 'change'],
        ...     'order_date': ['2024-05-01T10:00:00+00:00', '2024-05-01T11:00:00+00:00']
        ... })
        >>> requests = load_requests_from_dataframe(df)
        >>> len(requests)
        2
    """
    # Validate required columns
    required_columns = [
        'request_id', 'external_id', 'skill_id', 'request_source',
        'product', 'service_region', 'request_type', 'order_date'
    ]
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"DataFrame missing required columns: {missing_columns}")
    
    requests = []
    errors = []
    
    # Process each row
    for idx, row in df.iterrows():
        try:
            request = _create_request_from_row(row, row_index=idx)
            requests.append(request)
        except Exception as e:
            error_msg = f"Row {idx}: {e}"
            errors.append(error_msg)
            logger.warning(f"Failed to create request from row {idx}: {e}")
    
    # Report errors if any
    if errors:
        logger.warning(f"Failed to create {len(errors)} requests out of {len(df)} rows")
        if len(errors) == len(df):
            # All rows failed - this is a critical error
            raise ValueError(
                "Failed to create any requests. Errors:\n" + "\n".join(errors[:5])
            )
    
    return requests


def _create_request_from_row(row: pd.Series, row_index: int) -> Request:
    """
    Create a Request from a DataFrame row.
    
    Internal helper function that handles data type conversions and parsing.
    
    Args:
        row: pandas Series representing one row
        row_index: Index of the row (for error messages)
        
    Returns:
        Request: New request instance
        
    Raises:
        ValueError: If required data is missing or invalid
    """
    from datetime import datetime, timezone
    
    # Extract required fields
    request_id = row.get('request_id')
    external_id = row.get('external_id')
    skill_id = row.get('skill_id')
    request_source = row.get('request_source')
    product = row.get('product')
    service_region = row.get('service_region')
    request_type = row.get('request_type')
    order_date = row.get('order_date')
    
    # Validate required fields
    if pd.isna(request_id) or not str(request_id).strip():
        raise ValueError("request_id is missing or empty")
    if pd.isna(external_id) or not str(external_id).strip():
        raise ValueError("external_id is missing or empty")
    if pd.isna(skill_id) or not str(skill_id).strip():
        raise ValueError("skill_id is missing or empty")
    if pd.isna(order_date):
        raise ValueError("order_date is missing")
    
    # Convert to strings and strip whitespace
    request_id = str(request_id).strip()
    external_id = str(external_id).strip()
    skill_id = str(skill_id).strip()
    request_source = str(request_source).strip() if not pd.isna(request_source) else "unknown"
    product = str(product).strip() if not pd.isna(product) else "unknown"
    service_region = str(service_region).strip() if not pd.isna(service_region) else "unknown"
    request_type = str(request_type).strip() if not pd.isna(request_type) else "unknown"
    
    # Parse order_date
    if isinstance(order_date, str):
        try:
            order_date = datetime.fromisoformat(order_date)
        except ValueError as e:
            raise ValueError(f"Invalid order_date format: {order_date}. Expected ISO format. {e}")
    elif isinstance(order_date, pd.Timestamp):
        order_date = order_date.to_pydatetime()
    
    # Ensure timezone-aware
    if order_date.tzinfo is None:
        order_date = order_date.replace(tzinfo=timezone.utc)
    
    # Parse optional fields
    foc_target = _parse_float(row.get('foc_target'), default=8.0)
    has_sla = _parse_bool(row.get('has_sla'), default=False)
    is_escalated = _parse_bool(row.get('is_escalated'), default=False)
    is_winback = _parse_bool(row.get('is_winback'), default=False)
    skill_priority = _parse_int(row.get('skill_priority'), default=0)
    
    # Extract other optional fields
    customer_support_model = _get_optional_string_simple(row, 'customer_support_model')
    control_desk = _get_optional_string_simple(row, 'control_desk')
    golden_customer_id = _get_optional_string_simple(row, 'golden_customer_id')
    
    # Create request
    try:
        request = Request(
            request_id=request_id,
            external_id=external_id,
            skill_id=skill_id,
            request_source=request_source,
            product=product,
            service_region=service_region,
            request_type=request_type,
            order_date=order_date,
            foc_target=foc_target,
            has_sla=has_sla,
            is_escalated=is_escalated,
            is_winback=is_winback,
            customer_support_model=customer_support_model,
            control_desk=control_desk,
            golden_customer_id=golden_customer_id,
            skill_priority=skill_priority
        )
        return request
    except Exception as e:
        raise ValueError(f"Failed to create Request: {e}")


def _parse_float(value: Any, default: float = 0.0) -> float:
    """Parse float value from various formats"""
    if pd.isna(value) or value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _parse_bool(value: Any, default: bool = False) -> bool:
    """Parse boolean value from various formats"""
    if pd.isna(value) or value is None:
        return default
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ('true', '1', 'yes', 't', 'y'):
            return True
        elif value_lower in ('false', '0', 'no', 'f', 'n'):
            return False
    
    if isinstance(value, (int, float)):
        return bool(value)
    
    return default


def _parse_int(value: Any, default: int = 0) -> int:
    """Parse integer value from various formats"""
    if pd.isna(value) or value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _get_optional_string_simple(row: pd.Series, column_name: str) -> Optional[str]:
    """Get optional string value from row"""
    if column_name in row:
        value = row[column_name]
        if not pd.isna(value):
            return str(value).strip()
    return None


def filter_requests_by_skill(
    requests: List[Request],
    skill_id: str
) -> List[Request]:
    """
    Filter requests that require a specific skill.
    
    Args:
        requests: List of requests to filter
        skill_id: The skill ID to filter by
        
    Returns:
        List[Request]: Requests requiring the specified skill
        
    Example:
        >>> requests = load_requests_from_csv(Path("requests.csv"))
        >>> internet_requests = filter_requests_by_skill(requests, "internet")
        >>> len(internet_requests)
        25
    """
    return [req for req in requests if req.skill_id == skill_id]


def filter_requests_by_state(
    requests: List[Request],
    state: RequestState
) -> List[Request]:
    """
    Filter requests by state.
    
    Args:
        requests: List of requests to filter
        state: The state to filter by
        
    Returns:
        List[Request]: Requests in the specified state
    """
    return [req for req in requests if req.state == state]


def get_request_statistics(requests: List[Request]) -> Dict[str, Any]:
    """
    Calculate statistics about a list of requests.
    
    Args:
        requests: List of requests
        
    Returns:
        Dict: Statistics including total count, unique skills, state distribution
        
    Example:
        >>> requests = load_requests_from_csv(Path("requests.csv"))
        >>> stats = get_request_statistics(requests)
        >>> stats['total_requests']
        100
        >>> stats['unique_skills']
        ['internet', 'voice', 'tv']
    """
    if not requests:
        return {
            'total_requests': 0,
            'unique_skills': [],
            'state_distribution': {},
            'sla_count': 0,
            'escalated_count': 0,
            'winback_count': 0
        }
    
    # Collect all skills
    all_skills = set(req.skill_id for req in requests)
    
    # Count states
    state_counts = {}
    for req in requests:
        state = req.state.value
        state_counts[state] = state_counts.get(state, 0) + 1
    
    # Count flags
    sla_count = sum(1 for req in requests if req.has_sla)
    escalated_count = sum(1 for req in requests if req.is_escalated)
    winback_count = sum(1 for req in requests if req.is_winback)
    
    return {
        'total_requests': len(requests),
        'unique_skills': sorted(list(all_skills)),
        'state_distribution': state_counts,
        'sla_count': sla_count,
        'escalated_count': escalated_count,
        'winback_count': winback_count,
        'avg_foc_target': sum(req.foc_target for req in requests) / len(requests)
    }