"""
Unit tests for configuration loading and validation.

Run with: pytest test_config.py -v
"""

import pytest
from pathlib import Path
import tempfile
import yaml

# Import our configuration classes
import sys
sys.path.append('..')  # Add parent directory to path

from config.scenario_config import (
    ScenarioConfig,
    SimulationParameters,
    DataSourceConfig,
    AgentBehaviorConfig,
    OutputConfig,
    PrioritizationAlgorithm,
    AgentBehaviorType,
    load_scenario_from_yaml,
    validate_scenario,
    create_sample_config
)


# ============================================================================
# TEST: SimulationParameters
# ============================================================================

class TestSimulationParameters:
    """Test suite for SimulationParameters model"""
    
    def test_valid_parameters(self):
        """Test creating valid simulation parameters"""
        params = SimulationParameters(
            start_date="2024-05-01",
            end_date="2024-06-01",
            default_ttpu=8.0,
            prioritization_algorithm=PrioritizationAlgorithm.FOC
        )
        
        # Check values are set correctly
        assert params.start_date == "2024-05-01"
        assert params.end_date == "2024-06-01"
        assert params.default_ttpu == 8.0
        assert params.prioritization_algorithm == PrioritizationAlgorithm.FOC
    
    def test_duration_calculation(self):
        """Test that duration is calculated correctly"""
        params = SimulationParameters(
            start_date="2024-05-01",
            end_date="2024-05-08"
        )
        
        assert params.duration_days == 7
        assert params.duration_seconds == 7 * 24 * 60 * 60
    
    def test_invalid_date_format(self):
        """Test that invalid date formats are rejected"""
        with pytest.raises(ValueError, match="Date must be in YYYY-MM-DD format"):
            SimulationParameters(
                start_date="05/01/2024",  # Wrong format
                end_date="2024-06-01"
            )
    
    def test_end_before_start(self):
        """Test that end_date must be after start_date"""
        with pytest.raises(ValueError, match="must be after"):
            SimulationParameters(
                start_date="2024-06-01",
                end_date="2024-05-01"  # Before start!
            )
    
    def test_negative_ttpu(self):
        """Test that negative TTPU is rejected"""
        with pytest.raises(ValueError):
            SimulationParameters(
                start_date="2024-05-01",
                end_date="2024-06-01",
                default_ttpu=-5.0  # Negative!
            )


# ============================================================================
# TEST: AgentBehaviorConfig
# ============================================================================

class TestAgentBehaviorConfig:
    """Test suite for AgentBehaviorConfig model"""
    
    def test_deterministic_behavior(self):
        """Test deterministic behavior config"""
        config = AgentBehaviorConfig(
            behavior_type=AgentBehaviorType.DETERMINISTIC
        )
        
        assert config.behavior_type == AgentBehaviorType.DETERMINISTIC
    
    def test_stochastic_requires_parameters(self):
        """Test that stochastic behavior requires mean and std_dev"""
        # Should fail without mean_click_interval_seconds
        with pytest.raises(ValueError, match="mean_click_interval_seconds required"):
            AgentBehaviorConfig(
                behavior_type=AgentBehaviorType.STOCHASTIC
                # Missing mean and std_dev!
            )
    
    def test_stochastic_with_parameters(self):
        """Test valid stochastic configuration"""
        config = AgentBehaviorConfig(
            behavior_type=AgentBehaviorType.STOCHASTIC,
            mean_click_interval_seconds=300.0,
            std_dev_seconds=60.0
        )
        
        assert config.mean_click_interval_seconds == 300.0
        assert config.std_dev_seconds == 60.0


# ============================================================================
# TEST: ScenarioConfig (Full Configuration)
# ============================================================================

class TestScenarioConfig:
    """Test suite for complete scenario configuration"""
    
    def test_create_sample_config(self):
        """Test that sample config is valid"""
        config = create_sample_config()
        
        assert config.scenario_name == "sample_scenario"
        assert config.simulation.duration_days == 7
        assert isinstance(config, ScenarioConfig)
    
    def test_minimal_config(self):
        """Test creating minimal valid configuration"""
        config = ScenarioConfig(
            scenario_name="test",
            simulation=SimulationParameters(
                start_date="2024-05-01",
                end_date="2024-05-08"
            ),
            data_sources=DataSourceConfig(use_database=False),
            agent_behavior=AgentBehaviorConfig(
                behavior_type=AgentBehaviorType.DETERMINISTIC
            ),
            output=OutputConfig()
        )
        
        assert config.scenario_name == "test"


# ============================================================================
# TEST: YAML Loading
# ============================================================================

class TestYAMLLoading:
    """Test suite for loading configurations from YAML files"""
    
    def test_load_valid_yaml(self):
        """Test loading a valid YAML configuration"""
        # Create a temporary YAML file
        yaml_content = {
            'scenario_name': 'test_scenario',
            'description': 'Test description',
            'simulation': {
                'start_date': '2024-05-01',
                'end_date': '2024-05-08',
                'default_ttpu': 8.0,
                'prioritization_algorithm': 'foc'
            },
            'data_sources': {
                'use_database': False
            },
            'agent_behavior': {
                'behavior_type': 'deterministic'
            },
            'output': {
                'output_directory': './test_results'
            }
        }
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_path = Path(f.name)
        
        try:
            # Load configuration
            config = load_scenario_from_yaml(temp_path)
            
            # Verify it loaded correctly
            assert config.scenario_name == 'test_scenario'
            assert config.simulation.start_date == '2024-05-01'
            
        finally:
            # Clean up temp file
            temp_path.unlink()
    
    def test_load_nonexistent_file(self):
        """Test that loading nonexistent file raises error"""
        with pytest.raises(FileNotFoundError):
            load_scenario_from_yaml(Path('nonexistent.yaml'))
    
    def test_load_invalid_yaml(self):
        """Test that invalid YAML raises error"""
        # Create invalid YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")  # Malformed YAML
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                load_scenario_from_yaml(temp_path)
        finally:
            temp_path.unlink()


# ============================================================================
# TEST: Validation
# ============================================================================

class TestValidation:
    """Test suite for additional validation checks"""
    
    def test_validate_normal_scenario(self):
        """Test that normal scenarios pass validation"""
        config = create_sample_config()
        warnings = validate_scenario(config)
        
        # Should have no warnings for a 7-day simulation
        assert len(warnings) == 0
    
    def test_warn_long_simulation(self):
        """Test that very long simulations generate warning"""
        config = create_sample_config()
        # Modify to be very long
        config.simulation.end_date = "2025-05-01"  # 1 year
        
        warnings = validate_scenario(config)
        
        # Should warn about long duration
        assert any("365 days" in w for w in warnings)


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '--tb=short'])