"""
Scenario Runner for STM Routing Simulator v3.0.

This module executes simulation scenarios using the SimulationEngine and
collects results. It provides high-level interfaces for running single
or multiple scenarios and comparing results.

Example usage:
    >>> from scenario.scenario_loader import ScenarioLoader
    >>> from scenario.scenario_runner import ScenarioRunner
    >>> 
    >>> # Load scenario
    >>> loader = ScenarioLoader()
    >>> scenario = loader.load_scenario('scenarios/basic_scenario.yaml')
    >>> 
    >>> # Run scenario
    >>> runner = ScenarioRunner()
    >>> result = runner.run_scenario(scenario)
    >>> 
    >>> # Display results
    >>> runner.print_summary(result)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging

from simulation.engine import SimulationEngine
# from models.agent import Agent
# from models.request import Request
# from config.scenario_config import RoutingConfig


# Configure logging
logger = logging.getLogger(__name__)


class ScenarioResult:
    """
    Container for scenario execution results.
    
    Holds all data from a completed simulation including statistics,
    assignments, and metadata.
    
    Attributes:
        scenario_name: Name of the scenario
        start_time: When simulation started
        end_time: When simulation ended
        statistics: Complete statistics dictionary
        assignments: List of all assignments made
        routing_decisions: List of all routing decisions
        metadata: Additional scenario metadata
    """
    
    def __init__(
        self,
        scenario_name: str,
        start_time: datetime,
        end_time: datetime,
        statistics: Dict[str, Any],
        assignments: List[Dict[str, Any]],
        routing_decisions: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize scenario result."""
        self.scenario_name = scenario_name
        self.start_time = start_time
        self.end_time = end_time
        self.statistics = statistics
        self.assignments = assignments
        self.routing_decisions = routing_decisions
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary for serialization.
        
        Returns:
            Dict: Complete result data
        """
        return {
            'scenario_name': self.scenario_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'statistics': self.statistics,
            'assignments': self.assignments,
            'routing_decisions': self.routing_decisions,
            'metadata': self.metadata
        }
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convert result to JSON string.
        
        Args:
            indent: JSON indentation level
            
        Returns:
            str: JSON representation
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get concise summary of results.
        
        Returns:
            Dict: Key metrics summary
        """
        stats = self.statistics
        
        return {
            'scenario_name': self.scenario_name,
            'duration_hours': stats['timing']['duration_hours'],
            'total_agents': stats['agents']['total_agents'],
            'total_requests': stats['requests']['total_requests'],
            'total_assignments': stats['assignments']['total'],
            'followup_count': stats['assignments']['followup_count'],
            'cmo_count': stats['assignments']['cmo_count'],
            'agents_with_work': stats['agents']['agents_with_assignments'],
            'routing_success_rate': stats['routing']['success_rate'],
            'events_processed': stats['events']['total_processed']
        }


class ScenarioRunner:
    """
    Executes simulation scenarios and collects results.
    
    The runner takes loaded scenario data, creates a SimulationEngine,
    executes the simulation, and packages the results.
    
    Example:
        >>> runner = ScenarioRunner()
        >>> result = runner.run_scenario(scenario)
        >>> runner.print_summary(result)
    """
    
    def __init__(self):
        """Initialize the scenario runner."""
        pass
    
    def run_scenario(
        self,
        scenario: Dict[str, Any],
        max_events: Optional[int] = None,
        max_time: Optional[datetime] = None,
        stop_when_idle: bool = True,
        verbose: bool = False
    ) -> ScenarioResult:
        """
        Run a single scenario.
        
        Args:
            scenario: Loaded scenario dictionary from ScenarioLoader
            max_events: Maximum events to process (None = unlimited)
            max_time: Maximum simulation time (None = unlimited)
            stop_when_idle: Stop when all work completed
            verbose: Print progress messages
            
        Returns:
            ScenarioResult: Complete execution results
            
        Example:
            >>> result = runner.run_scenario(
            ...     scenario=scenario,
            ...     stop_when_idle=True,
            ...     verbose=True
            ... )
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"Running Scenario: {scenario['name']}")
            print(f"{'='*60}")
            print(f"Description: {scenario.get('description', 'N/A')}")
            print(f"Start Time: {scenario['start_time'].isoformat()}")
            print(f"Agents: {len(scenario['agents'])}")
            print(f"Requests: {len(scenario['requests'])}")
            print(f"{'='*60}\n")
        
        # Create simulation engine
        engine = SimulationEngine(
            agents=scenario['agents'],
            requests=scenario['requests'],
            config=scenario['routing_config'],
            start_time=scenario['start_time']
        )
        
        # Run simulation
        logger.info(f"Starting simulation: {scenario['name']}")
        start_time = datetime.now()
        
        engine.run(
            max_events=max_events,
            max_time=max_time,
            stop_when_idle=stop_when_idle
        )
        
        end_time = datetime.now()
        logger.info(f"Simulation completed: {scenario['name']}")
        
        # Collect results
        statistics = engine.get_statistics()
        assignments = engine.get_assignments()
        routing_decisions = engine.get_routing_decisions()
        
        # Create result object
        result = ScenarioResult(
            scenario_name=scenario['name'],
            start_time=start_time,
            end_time=end_time,
            statistics=statistics,
            assignments=assignments,
            routing_decisions=routing_decisions,
            metadata={
                'description': scenario.get('description', ''),
                'filepath': scenario.get('filepath', ''),
                'sim_start_time': scenario['start_time'].isoformat(),
                'max_events': max_events,
                'max_time': max_time.isoformat() if max_time else None,
                'stop_when_idle': stop_when_idle
            }
        )
        
        if verbose:
            self.print_summary(result)
        
        return result
    
    def run_multiple_scenarios(
        self,
        scenarios: List[Dict[str, Any]],
        max_events: Optional[int] = None,
        max_time: Optional[datetime] = None,
        stop_when_idle: bool = True,
        verbose: bool = False
    ) -> List[ScenarioResult]:
        """
        Run multiple scenarios sequentially.
        
        Args:
            scenarios: List of loaded scenario dictionaries
            max_events: Maximum events per scenario
            max_time: Maximum time per scenario
            stop_when_idle: Stop each when work completed
            verbose: Print progress messages
            
        Returns:
            List[ScenarioResult]: Results for all scenarios
            
        Example:
            >>> results = runner.run_multiple_scenarios(
            ...     scenarios=[scenario1, scenario2, scenario3],
            ...     stop_when_idle=True,
            ...     verbose=True
            ... )
        """
        results = []
        
        for i, scenario in enumerate(scenarios, 1):
            if verbose:
                print(f"\n{'#'*60}")
                print(f"# Scenario {i}/{len(scenarios)}")
                print(f"{'#'*60}")
            
            try:
                result = self.run_scenario(
                    scenario=scenario,
                    max_events=max_events,
                    max_time=max_time,
                    stop_when_idle=stop_when_idle,
                    verbose=verbose
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to run scenario '{scenario['name']}': {e}")
                if verbose:
                    print(f"\n❌ ERROR: Failed to run scenario: {e}\n")
        
        if verbose and len(results) > 1:
            self.print_comparison(results)
        
        return results
    
    def print_summary(self, result: ScenarioResult) -> None:
        """
        Print formatted summary of a single scenario result.
        
        Args:
            result: ScenarioResult to summarize
        """
        summary = result.get_summary()
        stats = result.statistics
        
        print(f"\n{'='*60}")
        print(f"SIMULATION RESULTS: {result.scenario_name}")
        print(f"{'='*60}")
        
        # Timing
        print("\n📅 TIMING")
        print(f"  Execution Time: {(result.end_time - result.start_time).total_seconds():.2f}s")
        print(f"  Simulated Duration: {summary['duration_hours']:.2f} hours")
        print(f"  Events Processed: {summary['events_processed']}")
        
        # Assignments
        print("\n📊 ASSIGNMENTS")
        print(f"  Total: {summary['total_assignments']}")
        print(f"  Followup: {summary['followup_count']}")
        print(f"  CMO: {summary['cmo_count']}")
        print(f"  From Absent Agent: {stats['assignments']['from_absent_agent_count']}")
        
        # Priority Distribution
        print("\n🎯 PRIORITY DISTRIBUTION")
        by_priority = stats['assignments']['by_priority']
        for priority in range(1, 6):
            count = by_priority.get(priority, 0)
            if count > 0:
                percentage = (count / summary['total_assignments'] * 100) if summary['total_assignments'] > 0 else 0
                print(f"  Priority {priority}: {count} ({percentage:.1f}%)")
        
        # Agent Utilization
        print("\n👥 AGENTS")
        print(f"  Total Agents: {summary['total_agents']}")
        print(f"  Agents with Work: {summary['agents_with_work']}")
        print(f"  Agents Idle: {summary['total_agents'] - summary['agents_with_work']}")
        print(f"  Avg Assignments/Agent: {stats['agents']['avg_assignments_per_agent']:.2f}")
        print(f"  Max Assignments (one agent): {stats['agents']['max_assignments_per_agent']}")
        
        # Requests
        print("\n📋 REQUESTS")
        print(f"  Total Requests: {summary['total_requests']}")
        print(f"  Assigned: {summary['total_assignments']}")
        print(f"  Pending: {stats['requests']['pending_requests']}")
        
        # Routing
        print("\n🔀 ROUTING")
        print(f"  Total Decisions: {stats['routing']['total_decisions']}")
        print(f"  Successful: {stats['routing']['successful_routings']}")
        print(f"  Failed: {stats['routing']['failed_routings']}")
        print(f"  Success Rate: {summary['routing_success_rate']:.1%}")
        print(f"  Avg Filtered/Decision: {stats['routing']['avg_filtered_per_decision']:.1f}")
        
        print(f"\n{'='*60}\n")
    
    def print_comparison(self, results: List[ScenarioResult]) -> None:
        """
        Print comparison table for multiple scenario results.
        
        Args:
            results: List of ScenarioResults to compare
        """
        if len(results) < 2:
            return
        
        print(f"\n{'='*80}")
        print(f"SCENARIO COMPARISON ({len(results)} scenarios)")
        print(f"{'='*80}")
        
        # Table header
        print(f"\n{'Metric':<30} ", end="")
        for result in results:
            # Truncate long scenario names
            name = result.scenario_name[:15]
            print(f"{name:>15} ", end="")
        print()
        print("-" * 80)
        
        # Extract summaries
        summaries = [r.get_summary() for r in results]
        
        # Comparison rows
        rows = [
            ("Duration (hours)", 'duration_hours', "{:.2f}"),
            ("Total Agents", 'total_agents', "{}"),
            ("Total Requests", 'total_requests', "{}"),
            ("Total Assignments", 'total_assignments', "{}"),
            ("Followup Count", 'followup_count', "{}"),
            ("CMO Count", 'cmo_count', "{}"),
            ("Agents with Work", 'agents_with_work', "{}"),
            ("Routing Success Rate", 'routing_success_rate', "{:.1%}"),
            ("Events Processed", 'events_processed', "{}"),
        ]
        
        for label, key, fmt in rows:
            print(f"{label:<30} ", end="")
            for summary in summaries:
                value = summary.get(key, 0)
                formatted = fmt.format(value)
                print(f"{formatted:>15} ", end="")
            print()
        
        print(f"{'='*80}\n")
    
    def save_result(self, result: ScenarioResult, filepath: str) -> None:
        """
        Save result to JSON file.
        
        Args:
            result: ScenarioResult to save
            filepath: Output file path
            
        Example:
            >>> runner.save_result(result, 'results/basic_scenario_result.json')
        """
        try:
            with open(filepath, 'w') as f:
                f.write(result.to_json())
            logger.info(f"Saved result to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save result: {e}")
            raise
    
    def save_results(self, results: List[ScenarioResult], directory: str) -> None:
        """
        Save multiple results to directory.
        
        Each result is saved as a separate JSON file named after the scenario.
        
        Args:
            results: List of ScenarioResults to save
            directory: Output directory path
            
        Example:
            >>> runner.save_results(results, 'results/')
        """
        from pathlib import Path
        
        # Create directory if it doesn't exist
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        for result in results:
            # Create filename from scenario name
            filename = result.scenario_name.lower().replace(' ', '_') + '.json'
            filepath = dir_path / filename
            
            self.save_result(result, str(filepath))
        
        logger.info(f"Saved {len(results)} results to: {directory}")
    
    def export_assignments_csv(self, result: ScenarioResult, filepath: str) -> None:
        """
        Export assignments to CSV file.
        
        Args:
            result: ScenarioResult containing assignments
            filepath: Output CSV file path
            
        Example:
            >>> runner.export_assignments_csv(result, 'results/assignments.csv')
        """
        import csv
        
        if not result.assignments:
            logger.warning("No assignments to export")
            return
        
        # Get all keys from first assignment
        fieldnames = list(result.assignments[0].keys())
        
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for assignment in result.assignments:
                    # Convert datetime objects to strings
                    row = {}
                    for key, value in assignment.items():
                        if isinstance(value, datetime):
                            row[key] = value.isoformat()
                        else:
                            row[key] = value
                    writer.writerow(row)
            
            logger.info(f"Exported {len(result.assignments)} assignments to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export assignments: {e}")
            raise
    
    def get_agent_workload_analysis(self, result: ScenarioResult) -> Dict[str, Any]:
        """
        Analyze workload distribution across agents.
        
        Args:
            result: ScenarioResult to analyze
            
        Returns:
            Dict: Workload analysis with per-agent statistics
        """
        from collections import Counter, defaultdict
        
        # Count assignments per agent
        agent_counts = Counter(a['agent_id'] for a in result.assignments)
        
        # Analyze by priority for each agent
        agent_priorities = defaultdict(lambda: Counter())
        for assignment in result.assignments:
            agent_id = assignment['agent_id']
            priority = assignment['priority_level']
            agent_priorities[agent_id][priority] += 1
        
        # Calculate statistics
        stats = result.statistics['agents']
        
        return {
            'total_agents': stats['total_agents'],
            'agents_with_work': stats['agents_with_assignments'],
            'agents_idle': stats['agents_without_assignments'],
            'average_assignments': stats['avg_assignments_per_agent'],
            'max_assignments': stats['max_assignments_per_agent'],
            'min_assignments': stats['min_assignments_per_agent'],
            'assignments_per_agent': dict(agent_counts),
            'priorities_per_agent': {
                agent: dict(priorities)
                for agent, priorities in agent_priorities.items()
            }
        }
    
    def get_request_flow_analysis(self, result: ScenarioResult) -> Dict[str, Any]:
        """
        Analyze request flow through the system.
        
        Args:
            result: ScenarioResult to analyze
            
        Returns:
            Dict: Request flow analysis
        """
        # Group assignments by time buckets (e.g., hourly)
        from collections import defaultdict
        
        hourly_assignments = defaultdict(int)
        
        for assignment in result.assignments:
            timestamp = assignment['timestamp']
            # Round to hour
            hour = timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_assignments[hour.isoformat()] += 1
        
        # Calculate throughput
        stats = result.statistics
        total_time_hours = stats['timing']['duration_hours']
        total_assignments = stats['assignments']['total']
        
        throughput = total_assignments / total_time_hours if total_time_hours > 0 else 0
        
        return {
            'total_requests': stats['requests']['total_requests'],
            'total_assignments': total_assignments,
            'pending_requests': stats['requests']['pending_requests'],
            'completion_rate': total_assignments / stats['requests']['total_requests'] if stats['requests']['total_requests'] > 0 else 0,
            'throughput_per_hour': throughput,
            'hourly_assignments': dict(sorted(hourly_assignments.items())),
            'followup_ratio': stats['assignments']['followup_count'] / total_assignments if total_assignments > 0 else 0,
            'cmo_ratio': stats['assignments']['cmo_count'] / total_assignments if total_assignments > 0 else 0
        }