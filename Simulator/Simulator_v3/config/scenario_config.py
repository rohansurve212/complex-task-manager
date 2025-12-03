"""
Scenario configuration loader and validator.

This module defines the configuration structure for simulation scenarios
using Pydantic models for automatic validation and type checking.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

# ============================================================================
# ENUMS - Define allowed values for configuration fields
# ============================================================================

class PrioritizationAlgorithm(str, Enum):
    """Available prioritization algorithms"""
    FOC = "foc"          # First-out-of-compliance (production default)
    FIFO = "fifo"        # First-in-first-out
    CUSTOM = "custom"    # Custom algorithm (for future extensions)

class AgentBehaviorType(str, Enum):
    """Types of agent behavior models"""
    HISTORICAL = "historical"      # Replay from historical data
    STOCHASTIC = "stochastic"      # Statistical model with randomness
    DETERMINISTIC = "deterministic" # Fixed intervals (for testing)

# ============================================================================
# CONFIGURATION MODELS - Define structure using Pydantic
# ============================================================================

class SimulationParameters(BaseModel):
    """
    Core simulation parameters that control the simulation execution.

    Attributes:
        start_date: When the simulation begins 
        end_date: When the simulation ends
        default_ttpu: Default time-to-pickup in days
        prioritization_algorithm: Which algorithm to use for routing
    """
    start_date: str = Field(
        ...,  # ... means required field
        description="Simulation start date in YYYY-MM-DD format",
        json_schema_extra={"example": "2024-05-01"}
    )
    
    end_date: str = Field(
        ...,
        description="Simulation end date in YYYY-MM-DD format",
        json_schema_extra={"example": "2024-06-01"}
    )
    
    default_ttpu: float = Field(
        default=8.0,
        gt=0,  # Must be greater than 0
        description="Default time-to-pickup target in days",
        json_schema_extra={"example": 8.0}
    )
    
    prioritization_algorithm: PrioritizationAlgorithm = Field(
        default=PrioritizationAlgorithm.FOC,
        description="Routing prioritization algorithm to use"
    )

    # Validators ensure data integrity
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v):
        """
        Ensure dates are in the correct format and valid.
        
        This validator runs automatically when creating a SimulationParameters object.
        If validation fails, it raises a ValueError with a clear message.
        """
        try:
            # Try to parse the date string
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError(f"Date must be in YYYY-MM-DD format, got: {v}")

    @model_validator(mode='after')
    def validate_date_range(self):
        """
        Ensure end_date is after start_date.
        
        Root validators run after all field validators and can access multiple fields.
        In Pydantic v2, model_validator with mode='after' receives self instead of values dict.
        """
        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
        
        if end <= start:
            raise ValueError(
                f"end_date ({self.end_date}) must be after "
                f"start_date ({self.start_date})"
            )
        
        return self

    @property
    def duration_days(self) -> int:
        """Calculate simulation duration in days"""
        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
        return (end - start).days
    
    @property
    def duration_seconds(self) -> float:
        """Calculate simulation duration in seconds (for SimPy)"""
        return self.duration_days * 24 * 60 * 60
        

class DataSourceConfig(BaseModel):
    """
    Configuration for data sources (databases, files, etc.)
    
    Defines where the simulator gets historical data for agents, requests, etc.
    """
    # Historical data files
    agents_csv: Optional[Path] = Field(
        None,
        description="Path to CSV file with agent data"
    )
    
    requests_csv: Optional[Path] = Field(
        None,
        description="Path to CSV file with historical requests"
    )
    
    skillsets_csv: Optional[Path] = Field(
        None,
        description="Path to CSV file with agent skillsets"
    )
    
    # Database connection (for production integration)
    use_database: bool = Field(
        default=False,
        description="Whether to load data from database instead of files"
    )
    
    database_connection_string: Optional[str] = Field(
        None,
        description="Connection string for database (if use_database=True)"
    )
    
    @field_validator('agents_csv', 'requests_csv', 'skillsets_csv')
    def validate_file_exists(cls, v):
        """Check that file paths exist if provided"""
        if v is not None:
            path = Path(v)
            if not path.exists():
                raise ValueError(f"File not found: {v}")
        return v


class AgentBehaviorConfig(BaseModel):
    """
    Configuration for how agents behave in the simulation.
    
    Agents need to simulate realistic clicking patterns and handle times.
    """
    behavior_type: AgentBehaviorType = Field(
        default=AgentBehaviorType.HISTORICAL,
        description="Type of agent behavior model"
    )
    
    # For stochastic behavior
    mean_click_interval_seconds: Optional[float] = Field(
        None,
        gt=0,
        description="Mean time between agent clicks (stochastic mode)"
    )
    
    std_dev_seconds: Optional[float] = Field(
        None,
        gt=0,
        description="Standard deviation of click intervals (stochastic mode)"
    )
    
    # For historical behavior
    historical_data_path: Optional[Path] = Field(
        None,
        description="Path to historical agent behavior data"
    )
    
    @model_validator(mode='after')
    def validate_behavior_config(self):
        """Ensure required fields are present for chosen behavior type"""
        behavior = self.behavior_type
        
        if behavior == AgentBehaviorType.STOCHASTIC:
            # Stochastic mode requires mean and std_dev
            if self.mean_click_interval_seconds is None:
                raise ValueError(
                    "mean_click_interval_seconds required for stochastic behavior"
                )
            if self.std_dev_seconds is None:
                raise ValueError(
                    "std_dev_seconds required for stochastic behavior"
                )
        
        elif behavior == AgentBehaviorType.HISTORICAL:
            # Historical mode requires data file
            if self.historical_data_path is None:
                raise ValueError(
                    "historical_data_path required for historical behavior"
                )
        
        return self


class OutputConfig(BaseModel):
    """
    Configuration for simulation outputs and reporting.
    """
    output_directory: Path = Field(
        default=Path("./simulation_results"),
        description="Directory to save simulation results"
    )
    
    save_detailed_logs: bool = Field(
        default=True,
        description="Whether to save detailed event logs"
    )
    
    generate_report: bool = Field(
        default=True,
        description="Whether to generate HTML report after simulation"
    )
    
    save_metrics_csv: bool = Field(
        default=True,
        description="Whether to save metrics as CSV files"
    )


class SimulationConfig(BaseModel):
    """Configuration for simulation timing and random seed."""
    start_date: Optional[datetime] = None
    random_seed: Optional[int] = None

class RoutingConfig(BaseModel):
    """
    Configuration for production routing behavior.

    Controls follow-up routing, pilot program, and request attribute generation.
    """

    # Pilot Program
    pilot_program_enabled: bool = Field(
        default=False,
        description="Enable follow-up routing for all agents (True) or none (False)"
    )

    # Follow-up time windows (UTC hours)
    followup_window_1_start: float = Field(default=14.0, description="First window start (hour, UTC)")
    followup_window_1_end: float = Field(default=15.5, description="First window end (hour, UTC)")
    followup_window_2_start: float = Field(default=19.5, description="Second window start (hour, UTC)")
    followup_window_2_end: float = Field(default=20.0, description="Second window end (hour, UTC)")

    # Absent agents
    absent_agent_percentage: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Percentage of agents to mark as absent each day (0.0-1.0)"
    )

    # Random request attribute generation
    customer_reply_probability: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Probability a request has status 'customerreplied'"
    )

    internal_note_probability: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Probability a request has 'NEW_INTERNAL_NOTE' tag"
    )

    locked_tag_probability: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Probability a request has 'LOCKED' tag"
    )
    
    followup_date_probability: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Probability a request has a follow-up date set"
    )
    
    expected_completion_date_probability: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Probability a request has expected completion date set"
    )

    sticky_assignment_probability: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Probability a request is sticky-assigned to an agent"
    )

    escalated_probability: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Probability a request is escalated by the internal exception tool"
    )

    winback_probability: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Probability a request is a winback request"
    )

    atlantic_routing_filter_probability: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Probability a request is an Atlantic Routing Filter request"
    )

    sla_probability: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Probability a request is an SLA request"
    )
    
    # Random seed for reproducibility
    random_seed: Optional[int] = Field(
        default=None,
        description="Random seed for request attribute generation (None = random)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "pilot_program_enabled": True,
                "absent_agent_percentage": 0.1,
                "customer_reply_probability": 0.15,
                "internal_note_probability": 0.20,
                "random_seed": 42
            }
        }
    }


class ScenarioConfig(BaseModel):
    """
    Complete configuration for a simulation scenario.
    
    This is the top-level configuration object that contains all
    parameters needed to run a simulation.
    """
    # Scenario metadata
    scenario_name: str = Field(
        ...,
        description="Unique name for this scenario",
        json_schema_extra={"example": "baseline_may_2024"}
    )
    
    description: str = Field(
        default="",
        description="Human-readable description of the scenario"
    )
    
    # Core configuration sections
    simulation: SimulationParameters
    data_sources: DataSourceConfig
    agent_behavior: AgentBehaviorConfig
    output: OutputConfig
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    
    # Optional: What-if changes to test
    what_if_changes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional changes to test (e.g., new FOC targets)"
    )
    
    model_config = {
        "arbitrary_types_allowed": True,
        "use_enum_values": True
    }


# ============================================================================
# UTILITY FUNCTIONS - Load and validate configurations
# ============================================================================

def load_scenario_from_yaml(yaml_path: Path) -> ScenarioConfig:
    """
    Load and validate a scenario configuration from a YAML file.
    
    Args:
        yaml_path: Path to the YAML configuration file
        
    Returns:
        ScenarioConfig: Validated configuration object
        
    Raises:
        FileNotFoundError: If YAML file doesn't exist
        yaml.YAMLError: If YAML is malformed
        pydantic.ValidationError: If configuration is invalid
        
    Example:
        >>> config = load_scenario_from_yaml(Path("my_scenario.yaml"))
        >>> print(config.scenario_name)
        baseline_may_2024
    """
    # Check file exists
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
    
    # Load YAML file
    with open(yaml_path, 'r') as f:
        try:
            raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
    
    # Validate and create config object
    # Pydantic will automatically validate all fields
    try:
        config = ScenarioConfig(**raw_config)
        return config
    except Exception as e:
        # Re-raise with more context
        raise ValueError(f"Configuration validation failed: {e}")


def validate_scenario(config: ScenarioConfig) -> List[str]:
    """
    Perform additional validation checks beyond Pydantic's automatic validation.
    
    Args:
        config: The scenario configuration to validate
        
    Returns:
        List of warning messages (empty if all good)
    """
    warnings = []
    
    # Check simulation duration
    if config.simulation.duration_days > 365:
        warnings.append(
            f"Simulation duration is {config.simulation.duration_days} days. "
            "Very long simulations may take hours to complete."
        )
    
    # Check output directory
    if not config.output.output_directory.parent.exists():
        warnings.append(
            f"Parent directory for output does not exist: "
            f"{config.output.output_directory.parent}"
        )
    
    # Check data sources
    if not config.data_sources.use_database:
        required_files = [
            config.data_sources.agents_csv,
            config.data_sources.requests_csv,
            config.data_sources.skillsets_csv
        ]
        missing = [f for f in required_files if f is None]
        if missing:
            warnings.append(
                "Some data source files are not configured. "
                "Simulation may fail if data is not available."
            )
    
    return warnings


def create_sample_config() -> ScenarioConfig:
    """
    Create a sample configuration object for testing.
    
    Returns:
        ScenarioConfig: A valid sample configuration
    """
    return ScenarioConfig(
        scenario_name="sample_scenario",
        description="Sample configuration for testing",
        simulation=SimulationParameters(
            start_date="2024-05-01",
            end_date="2024-05-08",
            default_ttpu=8.0,
            prioritization_algorithm=PrioritizationAlgorithm.FOC
        ),
        data_sources=DataSourceConfig(
            use_database=True  # Use database to avoid missing file warnings in tests
        ),
        agent_behavior=AgentBehaviorConfig(
            behavior_type=AgentBehaviorType.DETERMINISTIC
        ),
        output=OutputConfig(
            output_directory=Path("./test_results")
        )
    )