"""
STM Routing Simulator v3.0 - Command Line Interface

This is the main entry point for running simulations from the command line.
Users can load scenarios from YAML files and execute them with various options.

Usage:
    # Run a single scenario
    python main.py scenarios/basic_scenario.yaml
    
    # Run with verbose output
    python main.py scenarios/basic_scenario.yaml --verbose
    
    # Run all scenarios in directory
    python main.py scenarios/ --all
    
    # Limit simulation
    python main.py scenarios/basic_scenario.yaml --max-events 1000
    
    # Save results
    python main.py scenarios/basic_scenario.yaml --output results/ --csv

Example:
    $ python main.py scenarios/basic_scenario.yaml --verbose
    
    ============================================================
    Running Scenario: Basic Scenario
    ============================================================
    Description: Simple test scenario with 5 agents
    Start Time: 2024-01-15T09:00:00-05:00
    Agents: 5
    Requests: 20
    ============================================================
    
    ... (simulation runs) ...
    
    ============================================================
    SIMULATION RESULTS: Basic Scenario
    ============================================================
    
    📅 TIMING
      Execution Time: 0.15s
      Simulated Duration: 8.50 hours
      Events Processed: 42
    
    📊 ASSIGNMENTS
      Total: 20
      Followup: 5
      CMO: 15
    ...
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import timedelta
from typing import List

from scenario.scenario_loader import ScenarioLoader, ScenarioLoadError
from scenario.scenario_runner import ScenarioRunner, ScenarioResult


# Version
VERSION = "3.0.0"


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the application.
    
    Args:
        verbose: Enable debug-level logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Suppress noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('dateutil').setLevel(logging.WARNING)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='STM Routing Simulator',
        description='Discrete Event Simulator for STM Request Routing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single scenario
  %(prog)s scenarios/basic_scenario.yaml
  
  # Run with verbose output
  %(prog)s scenarios/basic_scenario.yaml --verbose
  
  # Run all scenarios in directory
  %(prog)s scenarios/ --all
  
  # Limit simulation to 1000 events
  %(prog)s scenarios/complex_scenario.yaml --max-events 1000
  
  # Save results to directory
  %(prog)s scenarios/basic_scenario.yaml --output results/
  
  # Export assignments as CSV
  %(prog)s scenarios/basic_scenario.yaml --csv results/assignments.csv

For more information, see the documentation at:
https://github.com/your-org/stm-routing-simulator
        """
    )
    
    # Version
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {VERSION}'
    )
    
    # Required: scenario path
    parser.add_argument(
        'scenario',
        type=str,
        help='Path to scenario YAML file or directory'
    )
    
    # Scenario selection
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all scenarios in directory (if scenario is a directory)'
    )
    
    # Simulation control
    sim_group = parser.add_argument_group('Simulation Control')
    sim_group.add_argument(
        '--max-events',
        type=int,
        metavar='N',
        help='Maximum number of events to process'
    )
    sim_group.add_argument(
        '--max-time',
        type=float,
        metavar='HOURS',
        help='Maximum simulation time in hours'
    )
    sim_group.add_argument(
        '--no-stop-idle',
        action='store_true',
        help='Do not stop when simulation becomes idle'
    )
    
    # Output control
    output_group = parser.add_argument_group('Output Control')
    output_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    output_group.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress all output except errors'
    )
    output_group.add_argument(
        '--output',
        type=str,
        metavar='DIR',
        help='Directory to save JSON results'
    )
    output_group.add_argument(
        '--csv',
        type=str,
        metavar='FILE',
        help='Export assignments to CSV file'
    )
    output_group.add_argument(
        '--no-summary',
        action='store_true',
        help='Skip printing summary (useful with --output)'
    )
    
    # Analysis
    analysis_group = parser.add_argument_group('Analysis Options')
    analysis_group.add_argument(
        '--workload-analysis',
        action='store_true',
        help='Print detailed agent workload analysis'
    )
    analysis_group.add_argument(
        '--flow-analysis',
        action='store_true',
        help='Print request flow analysis'
    )
    
    return parser.parse_args()


def load_scenarios(scenario_path: str, load_all: bool) -> List:
    """
    Load scenario(s) from path.
    
    Args:
        scenario_path: Path to scenario file or directory
        load_all: Load all scenarios in directory
        
    Returns:
        List: Loaded scenario dictionaries
        
    Raises:
        SystemExit: If loading fails
    """
    loader = ScenarioLoader()
    path = Path(scenario_path)
    
    try:
        if path.is_dir():
            if not load_all:
                print(f"❌ Error: '{scenario_path}' is a directory. Use --all to load all scenarios.")
                sys.exit(1)
            
            print(f"📂 Loading all scenarios from: {scenario_path}")
            scenarios = loader.load_multiple_scenarios(scenario_path)
            print(f"✅ Loaded {len(scenarios)} scenario(s)")
            return scenarios
        
        elif path.is_file():
            print(f"📄 Loading scenario: {scenario_path}")
            scenario = loader.load_scenario(scenario_path)
            print(f"✅ Loaded: {scenario['name']}")
            return [scenario]
        
        else:
            print(f"❌ Error: Path not found: {scenario_path}")
            sys.exit(1)
    
    except ScenarioLoadError as e:
        print(f"❌ Error loading scenario: {e}")
        sys.exit(1)


def run_simulations(
    scenarios: List,
    args: argparse.Namespace
) -> List[ScenarioResult]:
    """
    Run simulations for all scenarios.
    
    Args:
        scenarios: List of scenario dictionaries
        args: Command-line arguments
        
    Returns:
        List[ScenarioResult]: Results from all simulations
    """
    runner = ScenarioRunner()
    
    # Calculate max_time as datetime if provided
    max_time = None
    if args.max_time:
        # Use first scenario's start time as reference
        start_time = scenarios[0]['start_time']
        max_time = start_time + timedelta(hours=args.max_time)
    
    # Determine verbosity
    verbose = args.verbose and not args.quiet
    
    # Run scenarios
    if len(scenarios) == 1:
        # Single scenario
        result = runner.run_scenario(
            scenario=scenarios[0],
            max_events=args.max_events,
            max_time=max_time,
            stop_when_idle=not args.no_stop_idle,
            verbose=verbose
        )
        return [result]
    else:
        # Multiple scenarios
        results = runner.run_multiple_scenarios(
            scenarios=scenarios,
            max_events=args.max_events,
            max_time=max_time,
            stop_when_idle=not args.no_stop_idle,
            verbose=verbose
        )
        return results


def print_analysis(result: ScenarioResult, args: argparse.Namespace) -> None:
    """
    Print additional analysis if requested.
    
    Args:
        result: ScenarioResult to analyze
        args: Command-line arguments
    """
    runner = ScenarioRunner()
    
    if args.workload_analysis:
        print("\n" + "="*60)
        print("AGENT WORKLOAD ANALYSIS")
        print("="*60)
        
        workload = runner.get_agent_workload_analysis(result)
        
        print(f"\nTotal Agents: {workload['total_agents']}")
        print(f"Agents with Work: {workload['agents_with_work']}")
        print(f"Average Assignments: {workload['average_assignments']:.2f}")
        
        print("\nAssignments per Agent:")
        for agent_id, count in sorted(workload['assignments_per_agent'].items()):
            print(f"  {agent_id}: {count}")
        
        print("\nPriority Distribution per Agent:")
        for agent_id, priorities in sorted(workload['priorities_per_agent'].items()):
            priority_str = ", ".join(f"P{p}={c}" for p, c in sorted(priorities.items()))
            print(f"  {agent_id}: {priority_str}")
    
    if args.flow_analysis:
        print("\n" + "="*60)
        print("REQUEST FLOW ANALYSIS")
        print("="*60)
        
        flow = runner.get_request_flow_analysis(result)
        
        print(f"\nTotal Requests: {flow['total_requests']}")
        print(f"Total Assignments: {flow['total_assignments']}")
        print(f"Pending Requests: {flow['pending_requests']}")
        print(f"Completion Rate: {flow['completion_rate']:.1%}")
        print(f"Throughput: {flow['throughput_per_hour']:.2f} assignments/hour")
        print(f"Followup Ratio: {flow['followup_ratio']:.1%}")
        print(f"CMO Ratio: {flow['cmo_ratio']:.1%}")
        
        if flow['hourly_assignments']:
            print("\nAssignments by Hour:")
            for hour, count in list(flow['hourly_assignments'].items())[:10]:
                print(f"  {hour}: {count}")
            if len(flow['hourly_assignments']) > 10:
                print(f"  ... ({len(flow['hourly_assignments']) - 10} more hours)")


def save_outputs(results: List[ScenarioResult], args: argparse.Namespace) -> None:
    """
    Save results to files if requested.
    
    Args:
        results: List of ScenarioResults
        args: Command-line arguments
    """
    runner = ScenarioRunner()
    
    # Save JSON results
    if args.output:
        try:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            runner.save_results(results, str(output_dir))
            
            if not args.quiet:
                print(f"\n✅ Saved results to: {args.output}")
        except Exception as e:
            print(f"\n❌ Failed to save results: {e}")
    
    # Export CSV (only first result if multiple)
    if args.csv:
        try:
            result = results[0]
            runner.export_assignments_csv(result, args.csv)
            
            if not args.quiet:
                print(f"✅ Exported assignments to: {args.csv}")
        except Exception as e:
            print(f"❌ Failed to export CSV: {e}")


def main() -> None:
    """
    Main entry point for the CLI.
    
    Orchestrates the entire simulation workflow:
    1. Parse arguments
    2. Setup logging
    3. Load scenarios
    4. Run simulations
    5. Print results
    6. Save outputs
    """
    # Parse arguments
    args = parse_arguments()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    # Print header (unless quiet)
    if not args.quiet:
        print("\n" + "="*60)
        print(f"STM Routing Simulator v{VERSION}")
        print("="*60 + "\n")
    
    try:
        # Load scenarios
        scenarios = load_scenarios(args.scenario, args.all)
        
        # Run simulations
        results = run_simulations(scenarios, args)
        
        # Print results (unless --no-summary or --quiet)
        if not args.no_summary and not args.quiet:
            runner = ScenarioRunner()
            for result in results:
                runner.print_summary(result)
                
                # Additional analysis
                print_analysis(result, args)
        
        # Save outputs
        save_outputs(results, args)
        
        # Success message
        if not args.quiet:
            print("\n✅ Simulation completed successfully!\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user\n")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()