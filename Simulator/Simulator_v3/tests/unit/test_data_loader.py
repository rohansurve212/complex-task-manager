"""
Unit tests for data loading utilities.

Run with: pytest tests/unit/test_data_loader.py -v
"""

import pytest
from pathlib import Path
import pandas as pd
import tempfile

# Import components to test
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.agent import Agent, AgentState
from models.data_loader import (
    load_agents_from_csv,
    load_agents_from_dataframe,
    create_agent_lookup,
    filter_agents_by_skill,
    filter_agents_by_skills,
    get_agent_statistics,
    validate_agent_data,
    _parse_skillsets,
    _parse_permissions,
    _get_optional_string
)


# ============================================================================
# TEST: CSV Loading
# ============================================================================

class TestCSVLoading:
    """Test suite for loading agents from CSV files"""
    
    def test_load_from_sample_csv(self):
        """Test loading agents from sample CSV file"""
        # Path to sample CSV (created earlier)
        csv_path = Path(__file__).parent.parent / "fixtures" / "sample_agents.csv"
        
        # Skip test if file doesn't exist
        if not csv_path.exists():
            pytest.skip("Sample CSV file not found")
        
        agents = load_agents_from_csv(csv_path)
        
        assert len(agents) > 0
        assert all(isinstance(agent, Agent) for agent in agents)
        
        # Check first agent
        first_agent = agents[0]
        assert first_agent.agent_id is not None
        assert first_agent.full_name is not None
    
    def test_load_from_nonexistent_file(self):
        """Test that loading nonexistent file raises error"""
        with pytest.raises(FileNotFoundError):
            load_agents_from_csv(Path("nonexistent.csv"))
    
    def test_load_csv_missing_required_columns(self):
        """Test that CSV missing required columns raises error"""
        # Create temp CSV without required columns
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("wrong_column,another_column\n")
            f.write("value1,value2\n")
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="missing required columns"):
                load_agents_from_csv(temp_path)
        finally:
            temp_path.unlink()
    
    def test_load_csv_with_custom_required_columns(self):
        """Test loading CSV with custom required columns"""
        # Create temp CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("agent_id,full_name,custom_field\n")
            f.write("john.doe,John Doe,value1\n")
            temp_path = Path(f.name)
        
        try:
            # This should succeed (has all default required columns)
            agents = load_agents_from_csv(
                temp_path,
                required_columns=['agent_id', 'full_name']
            )
            assert len(agents) == 1
            
            # This should fail (missing custom_field2)
            with pytest.raises(ValueError, match="missing required columns"):
                load_agents_from_csv(
                    temp_path,
                    required_columns=['agent_id', 'full_name', 'custom_field2']
                )
        finally:
            temp_path.unlink()


# ============================================================================
# TEST: DataFrame Loading
# ============================================================================

class TestDataFrameLoading:
    """Test suite for loading agents from DataFrames"""
    
    def test_load_from_simple_dataframe(self):
        """Test loading from minimal DataFrame"""
        df = pd.DataFrame({
            'agent_id': ['john.doe', 'jane.smith'],
            'full_name': ['John Doe', 'Jane Smith']
        })
        
        agents = load_agents_from_dataframe(df)
        
        assert len(agents) == 2
        assert agents[0].agent_id == 'john.doe'
        assert agents[1].agent_id == 'jane.smith'
    
    def test_load_from_complete_dataframe(self):
        """Test loading from DataFrame with all columns"""
        df = pd.DataFrame({
            'agent_id': ['john.doe'],
            'full_name': ['John Doe'],
            'skillsets': ['internet,voice,tv'],
            'manager_name': ['Sarah Johnson'],
            'cp2_name': ['Toronto Team'],
            'cp3_name': ['Ontario Region']
        })
        
        agents = load_agents_from_dataframe(df)
        
        assert len(agents) == 1
        agent = agents[0]
        assert agent.has_skill('internet')
        assert agent.has_skill('voice')
        assert agent.has_skill('tv')
        assert agent.manager_name == 'Sarah Johnson'
        assert agent.cp2_name == 'Toronto Team'
    
    def test_load_dataframe_missing_required_columns(self):
        """Test that DataFrame missing required columns raises error"""
        df = pd.DataFrame({
            'wrong_column': ['value1', 'value2']
        })
        
        with pytest.raises(ValueError, match="missing required columns"):
            load_agents_from_dataframe(df)
    
    def test_load_dataframe_with_missing_values(self):
        """Test loading DataFrame with NaN values"""
        df = pd.DataFrame({
            'agent_id': ['john.doe', 'jane.smith'],
            'full_name': ['John Doe', 'Jane Smith'],
            'skillsets': ['internet,voice', None],  # Second agent has no skills
            'manager_name': ['Sarah Johnson', None]  # Second agent has no manager
        })
        
        agents = load_agents_from_dataframe(df)
        
        assert len(agents) == 2
        assert len(agents[0].skillsets) == 2
        assert len(agents[1].skillsets) == 0  # No skills for second agent
        assert agents[1].manager_name is None
    
    def test_load_dataframe_with_errors(self):
        """Test that individual row errors don't stop entire load"""
        df = pd.DataFrame({
            'agent_id': ['john.doe', '', 'jane.smith'],  # Middle row has empty ID
            'full_name': ['John Doe', 'Bad Agent', 'Jane Smith']
        })
        
        # Should load 2 agents (skipping the bad one)
        agents = load_agents_from_dataframe(df)
        
        assert len(agents) == 2
        assert agents[0].agent_id == 'john.doe'
        assert agents[1].agent_id == 'jane.smith'
    
    def test_load_dataframe_all_rows_fail(self):
        """Test that all failing rows raises error"""
        df = pd.DataFrame({
            'agent_id': ['', ''],  # Both rows have empty IDs
            'full_name': ['Agent 1', 'Agent 2']
        })
        
        with pytest.raises(ValueError, match="Failed to create any agents"):
            load_agents_from_dataframe(df)


# ============================================================================
# TEST: Parsing Functions
# ============================================================================

class TestParsingFunctions:
    """Test suite for data parsing helper functions"""
    
    def test_parse_skillsets_from_string(self):
        """Test parsing skillsets from comma-separated string"""
        skills = _parse_skillsets("internet,voice,tv")
        
        assert isinstance(skills, set)
        assert len(skills) == 3
        assert "internet" in skills
        assert "voice" in skills
        assert "tv" in skills
    
    def test_parse_skillsets_from_string_with_whitespace(self):
        """Test parsing skillsets with extra whitespace"""
        skills = _parse_skillsets("  internet , voice  , tv  ")
        
        assert len(skills) == 3
        assert "internet" in skills  # Whitespace should be stripped
    
    def test_parse_skillsets_from_list(self):
        """Test parsing skillsets from list"""
        skills = _parse_skillsets(["internet", "voice", "tv"])
        
        assert isinstance(skills, set)
        assert len(skills) == 3
    
    def test_parse_skillsets_from_set(self):
        """Test parsing skillsets from set"""
        input_set = {"internet", "voice"}
        skills = _parse_skillsets(input_set)
        
        assert isinstance(skills, set)
        assert skills == input_set
    
    def test_parse_skillsets_none(self):
        """Test parsing None returns empty set"""
        skills = _parse_skillsets(None)
        assert skills == set()
    
    def test_parse_skillsets_nan(self):
        """Test parsing NaN returns empty set"""
        skills = _parse_skillsets(pd.NA)
        assert skills == set()
    
    def test_parse_permissions_from_dict(self):
        """Test parsing permissions from dictionary"""
        perms = _parse_permissions({"region": "ontario", "product": "internet"})
        
        assert isinstance(perms, dict)
        assert perms["region"] == "ontario"
    
    def test_parse_permissions_from_json_string(self):
        """Test parsing permissions from JSON string"""
        json_str = '{"region": "ontario", "product": "internet"}'
        perms = _parse_permissions(json_str)
        
        assert isinstance(perms, dict)
        assert perms["region"] == "ontario"
        assert perms["product"] == "internet"
    
    def test_parse_permissions_invalid_json(self):
        """Test parsing invalid JSON returns empty dict"""
        perms = _parse_permissions("not valid json")
        assert perms == {}
    
    def test_parse_permissions_none(self):
        """Test parsing None returns empty dict"""
        perms = _parse_permissions(None)
        assert perms == {}
    
    def test_get_optional_string_first_column(self):
        """Test getting optional string from first matching column"""
        row = pd.Series({
            'cp2_name': 'Toronto Team',
            'CP2_name': 'Montreal Team'
        })
        
        value = _get_optional_string(row, 'cp2_name', 'CP2_name')
        assert value == 'Toronto Team'  # First match wins
    
    def test_get_optional_string_second_column(self):
        """Test getting optional string from second column"""
        row = pd.Series({
            'cp2_name': None,
            'CP2_name': 'Montreal Team'
        })
        
        value = _get_optional_string(row, 'cp2_name', 'CP2_name')
        assert value == 'Montreal Team'
    
    def test_get_optional_string_no_match(self):
        """Test getting optional string with no matches"""
        row = pd.Series({'other_column': 'value'})
        
        value = _get_optional_string(row, 'cp2_name', 'CP2_name')
        assert value is None


# ============================================================================
# TEST: Bulk Operations
# ============================================================================

class TestBulkOperations:
    """Test suite for bulk agent operations"""
    
    def test_create_agent_lookup(self):
        """Test creating agent lookup dictionary"""
        agents = [
            Agent(agent_id="john.doe", full_name="John Doe"),
            Agent(agent_id="jane.smith", full_name="Jane Smith"),
            Agent(agent_id="bob.wilson", full_name="Bob Wilson")
        ]
        
        lookup = create_agent_lookup(agents)
        
        assert len(lookup) == 3
        assert "john.doe" in lookup
        assert lookup["john.doe"].full_name == "John Doe"
        assert lookup["jane.smith"].full_name == "Jane Smith"
    
    def test_filter_agents_by_skill(self):
        """Test filtering agents by single skill"""
        agents = [
            Agent(agent_id="john", full_name="John", skillsets={"internet", "voice"}),
            Agent(agent_id="jane", full_name="Jane", skillsets={"tv", "internet"}),
            Agent(agent_id="bob", full_name="Bob", skillsets={"voice"})
        ]
        
        internet_agents = filter_agents_by_skill(agents, "internet")
        
        assert len(internet_agents) == 2
        assert all(agent.has_skill("internet") for agent in internet_agents)
    
    def test_filter_agents_by_skills_any(self):
        """Test filtering agents by any of multiple skills"""
        agents = [
            Agent(agent_id="john", full_name="John", skillsets={"internet"}),
            Agent(agent_id="jane", full_name="Jane", skillsets={"voice"}),
            Agent(agent_id="bob", full_name="Bob", skillsets={"tv"})
        ]
        
        # Find agents with internet OR voice
        filtered = filter_agents_by_skills(
            agents,
            ["internet", "voice"],
            require_all=False
        )
        
        assert len(filtered) == 2
        assert filtered[0].agent_id == "john"
        assert filtered[1].agent_id == "jane"
    
    def test_filter_agents_by_skills_all(self):
        """Test filtering agents by all of multiple skills"""
        agents = [
            Agent(agent_id="john", full_name="John", skillsets={"internet", "voice"}),
            Agent(agent_id="jane", full_name="Jane", skillsets={"internet"}),
            Agent(agent_id="bob", full_name="Bob", skillsets={"internet", "voice", "tv"})
        ]
        
        # Find agents with BOTH internet AND voice
        filtered = filter_agents_by_skills(
            agents,
            ["internet", "voice"],
            require_all=True
        )
        
        assert len(filtered) == 2
        assert all(agent.has_skill("internet") for agent in filtered)
        assert all(agent.has_skill("voice") for agent in filtered)
    
    def test_get_agent_statistics_empty(self):
        """Test statistics for empty agent list"""
        stats = get_agent_statistics([])
        
        assert stats['total_agents'] == 0
        assert stats['unique_skills'] == []
    
    def test_get_agent_statistics_with_agents(self):
        """Test statistics for agent list"""
        agents = [
            Agent(agent_id="john", full_name="John", skillsets={"internet", "voice"}),
            Agent(agent_id="jane", full_name="Jane", skillsets={"internet", "tv"}),
            Agent(agent_id="bob", full_name="Bob", skillsets={"voice"})
        ]
        
        stats = get_agent_statistics(agents)
        
        assert stats['total_agents'] == 3
        assert len(stats['unique_skills']) == 3
        assert set(stats['unique_skills']) == {"internet", "voice", "tv"}
        assert stats['agents_with_skills'] == 3
        assert stats['avg_skills_per_agent'] == (2 + 2 + 1) / 3
    
    def test_get_agent_statistics_state_distribution(self):
        """Test statistics include state distribution"""
        agents = [
            Agent(agent_id="john", full_name="John"),
            Agent(agent_id="jane", full_name="Jane"),
            Agent(agent_id="bob", full_name="Bob")
        ]
        
        # Set different states
        agents[1].set_state(AgentState.WORKING, timestamp=100.0)
        agents[2].set_state(AgentState.UNAVAILABLE, timestamp=100.0)
        
        stats = get_agent_statistics(agents)
        
        assert stats['state_distribution']['idle'] == 1
        assert stats['state_distribution']['working'] == 1
        assert stats['state_distribution']['unavailable'] == 1


# ============================================================================
# TEST: Validation
# ============================================================================

class TestValidation:
    """Test suite for agent data validation"""
    
    def test_validate_valid_agents(self):
        """Test validation of valid agent list"""
        agents = [
            Agent(agent_id="john", full_name="John", skillsets={"internet"}),
            Agent(agent_id="jane", full_name="Jane", skillsets={"voice"})
        ]
        
        report = validate_agent_data(agents)
        
        assert report['valid'] is True
        assert len(report['errors']) == 0
        assert report['agent_count'] == 2
    
    def test_validate_duplicate_ids(self):
        """Test validation detects duplicate agent IDs"""
        agents = [
            Agent(agent_id="john", full_name="John Doe"),
            Agent(agent_id="john", full_name="John Smith")  # Duplicate ID!
        ]
        
        report = validate_agent_data(agents)
        
        assert report['valid'] is False
        assert len(report['errors']) > 0
        assert any("Duplicate" in error for error in report['errors'])
    
    def test_validate_agents_without_skills(self):
        """Test validation warns about agents without skills"""
        agents = [
            Agent(agent_id="john", full_name="John", skillsets={"internet"}),
            Agent(agent_id="jane", full_name="Jane", skillsets=set())  # No skills
        ]
        
        report = validate_agent_data(agents)
        
        # Should be valid but with warning
        assert report['valid'] is True
        assert len(report['warnings']) > 0
        assert any("no skills" in warning.lower() for warning in report['warnings'])
    
    def test_validate_multiple_agents_without_skills(self):
        """Test validation with multiple agents without skills"""
        agents = [
            Agent(agent_id=f"agent{i}", full_name=f"Agent {i}", skillsets=set())
            for i in range(5)
        ]
        
        report = validate_agent_data(agents)
        
        assert len(report['warnings']) > 0
        # Should mention count in warning
        assert "5 agents" in report['warnings'][0]


# ============================================================================
# TEST: Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test suite for realistic integration scenarios"""
    
    def test_load_filter_and_lookup(self):
        """Test complete workflow: load -> filter -> lookup"""
        # Create test data
        df = pd.DataFrame({
            'agent_id': ['john', 'jane', 'bob', 'alice'],
            'full_name': ['John', 'Jane', 'Bob', 'Alice'],
            'skillsets': ['internet,voice', 'internet,tv', 'voice', 'tv,voice']
        })
        
        # Load agents
        agents = load_agents_from_dataframe(df)
        assert len(agents) == 4
        
        # Filter by skill
        voice_agents = filter_agents_by_skill(agents, "voice")
        assert len(voice_agents) == 3
        
        # Create lookup
        lookup = create_agent_lookup(voice_agents)
        assert len(lookup) == 3
        assert "john" in lookup
        assert "bob" in lookup
        assert "alice" in lookup
    
    def test_load_validate_and_report(self):
        """Test workflow: load -> validate -> report statistics"""
        # Create test data with some issues
        df = pd.DataFrame({
            'agent_id': ['john', 'jane', 'bob', 'alice', 'john'],  # Duplicate!
            'full_name': ['John', 'Jane', 'Bob', 'Alice', 'John Jr'],
            'skillsets': ['internet', 'voice', '', 'tv', 'internet']  # Bob has no skills
        })
        
        # Load agents
        agents = load_agents_from_dataframe(df)
        
        # Validate
        validation_report = validate_agent_data(agents)
        assert not validation_report['valid']  # Should fail due to duplicates
        assert len(validation_report['errors']) > 0
        
        # Get statistics anyway
        stats = get_agent_statistics(agents)
        assert stats['total_agents'] == 5


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--cov=models.data_loader'])