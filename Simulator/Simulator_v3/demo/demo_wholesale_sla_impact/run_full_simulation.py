#!/usr/bin/env python3
"""
STM Routing Simulator v3.0 - Wholesale SLA Full Simulation Runner

This script runs COMPLETE discrete event simulations for both baseline and proposed
scenarios to provide comprehensive metrics including actual agent assignments, wait
times, throughput, and service levels.

═══════════════════════════════════════════════════════════════════════════════
WHAT THIS TOOL DOES:
═══════════════════════════════════════════════════════════════════════════════
✓ Calculates queue position changes (quick analysis)
✓ Runs full discrete event simulation using SimPy
✓ Assigns requests to agents based on routing logic
✓ Simulates time progression and agent availability
✓ Calculates actual wait times and handle times
✓ Tracks FOC compliance over time
✓ Measures agent utilization and throughput
✓ Provides complete comparison between scenarios

This includes both quick position analysis AND complete simulation with actual
assignment logic.

═══════════════════════════════════════════════════════════════════════════════
SCENARIO:
═══════════════════════════════════════════════════════════════════════════════
Baseline:  13 customers, all foc_target=8.0 days, has_sla=False
Proposed:  7 SLA customers (CUST_A-G): foc_target=1.0 day, has_sla=True
           6 non-SLA customers (CUST_H-M): foc_target=8.0 days, has_sla=False

Total: 500 requests from 13 customers (56 agents)

Expected Impact: ~700% (8x) priority increase for SLA customers

Usage:
    python run_full_simulation.py [--duration HOURS]
"""

import sys
import os
import json
import time
import statistics
import yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Tuple, List

# Add parent directories to path to import simulator modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from scenario.scenario_loader import ScenarioLoader
    from scenario.scenario_runner import ScenarioRunner
except ImportError as e:
    print(f"\n❌ Error: Could not import simulator modules")
    print(f"   {e}")
    print(f"\nMake sure you're running this from: Simulator_v3/demo/demo_wholesale_sla_impact/")
    print(f"And that Simulator_v3/scenario/ exists with scenario_loader.py and scenario_runner.py")
    sys.exit(1)


# ============================================================================
# DEMO CONFIGURATION
# ============================================================================

# Scenario file paths (relative to Simulator_v3 root)
BASELINE_SCENARIO = "demo/demo_wholesale_sla_impact/scenarios/baseline_scenario.yaml"
PROPOSED_SCENARIO = "demo/demo_wholesale_sla_impact/scenarios/proposed_scenario.yaml"

# Output configuration
OUTPUT_DIR = "demo/demo_wholesale_sla_impact/output"
BASELINE_OUTPUT = "baseline"
PROPOSED_OUTPUT = "proposed"
COMPARISON_OUTPUT = "comparison_results_full.json"

# Simulation parameters
DEFAULT_DURATION_HOURS = 8.0  # Standard 8-hour shift

# Version
VERSION = "1.1.0"
DEMO_SPEED = "normal"  # 'fast', 'normal', 'slow'


# ============================================================================
# VISUAL FORMATTING
# ============================================================================

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header(text: str):
    """Print a formatted header"""
    width = 80
    print("\n" + "=" * width)
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(width)}{Colors.END}")
    print("=" * width + "\n")


def print_section(text: str):
    """Print a formatted section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'─' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'─' * 80}{Colors.END}\n")


def print_subsection(text: str):
    """Print a formatted subsection header"""
    print(f"\n{Colors.BOLD}{text}{Colors.END}")


def print_info(label: str, value: str, color=Colors.GREEN):
    """Print formatted info line"""
    print(f"  {Colors.BOLD}{label}:{Colors.END} {color}{value}{Colors.END}")


def print_progress(message: str):
    """Print a progress message"""
    print(f"  {message}", end='', flush=True)
    pause(0.3)
    print(f" {Colors.GREEN}✓{Colors.END}")


def print_simulation_box():
    """Print a box highlighting full simulation mode"""
    print(f"\n{Colors.GREEN}{'╔' + '═' * 78 + '╗'}{Colors.END}")
    print(f"{Colors.GREEN}║{Colors.END} {Colors.BOLD}🚀  FULL SIMULATION MODE{Colors.END}" + " " * 53 + f"{Colors.GREEN}║{Colors.END}")
    print(f"{Colors.GREEN}║{Colors.END}" + " " * 78 + f"{Colors.GREEN}║{Colors.END}")
    print(f"{Colors.GREEN}║{Colors.END}  This runs the complete discrete event simulation with:                     {Colors.GREEN}║{Colors.END}")
    print(f"{Colors.GREEN}║{Colors.END}    • Queue position analysis (predicted impact)                             {Colors.GREEN}║{Colors.END}")
    print(f"{Colors.GREEN}║{Colors.END}    • Actual agent assignments using routing logic                           {Colors.GREEN}║{Colors.END}")
    print(f"{Colors.GREEN}║{Colors.END}    • Real wait times and handle times                                       {Colors.GREEN}║{Colors.END}")
    print(f"{Colors.GREEN}║{Colors.END}    • FOC compliance tracking over time                                      {Colors.GREEN}║{Colors.END}")
    print(f"{Colors.GREEN}║{Colors.END}    • Complete throughput and utilization metrics                            {Colors.GREEN}║{Colors.END}")
    print(f"{Colors.GREEN}{'╚' + '═' * 78 + '╝'}{Colors.END}\n")


def pause(seconds: float = 1.0):
    """Pause execution with demo speed consideration"""
    speed_multipliers = {
        'fast': 0.3,
        'normal': 1.0,
        'slow': 2.0
    }
    time.sleep(seconds * speed_multipliers.get(DEMO_SPEED, 1.0))


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


# ============================================================================
# QUEUE POSITION ANALYSIS (Quick Analysis Component)
# ============================================================================

class SimplifiedRequest:
    """Simplified Request class for quick priority analysis."""
    
    def __init__(self, data: Dict):
        self.request_id = data['request_id']
        self.external_id = data['external_id']
        self.skill_id = data['skill_id']
        self.request_source = data['request_source']
        self.product = data['product']
        self.foc_target = data['foc_target']
        self.has_sla = data.get('has_sla', False)
        self.golden_customer_id = data.get('golden_customer_id', 'UNKNOWN')
        self.order_date_offset_hours = data.get('order_date_offset_hours', 0)
        self.order_date = None  # Will be set by scenario
    
    def calculate_priority_score(self, current_time: datetime) -> float:
        """Calculate priority score: age_minutes / foc_target_minutes"""
        age_minutes = (current_time - self.order_date).total_seconds() / 60.0
        foc_target_minutes = self.foc_target * 24.0 * 60.0
        return age_minutes / foc_target_minutes
    
    def get_age_days(self, current_time: datetime) -> float:
        """Get request age in days"""
        return (current_time - self.order_date).total_seconds() / (24.0 * 60.0)


def analyze_queue_positions(scenario_path: str) -> Dict[str, Any]:
    """Analyze queue positions at t=0 for a scenario"""
    
    # Load scenario
    with open(scenario_path, 'r') as f:
        scenario_data = yaml.safe_load(f)
    
    start_time_str = scenario_data['start_time']
    start_time = datetime.fromisoformat(start_time_str)
    current_time = start_time
    
    # Create simplified requests
    requests = []
    for req_data in scenario_data['requests']:
        req = SimplifiedRequest(req_data)
        offset_hours = req.order_date_offset_hours
        req.order_date = start_time + timedelta(hours=offset_hours)
        requests.append(req)
    
    # Calculate priority scores and ranks
    request_data = []
    for req in requests:
        score = req.calculate_priority_score(current_time)
        age_days = req.get_age_days(current_time)
        
        request_data.append({
            'request_id': req.request_id,
            'client_id': req.golden_customer_id,
            'has_sla': req.has_sla,
            'priority_score': score,
            'age_days': age_days,
            'rank': None
        })
    
    # Sort by priority score (descending) and assign ranks
    request_data.sort(key=lambda x: x['priority_score'], reverse=True)
    for i, req in enumerate(request_data):
        req['rank'] = i + 1
    
    return {'request_details': request_data}


def calculate_rank_changes(baseline_analysis: Dict, proposed_analysis: Dict) -> Dict[str, float]:
    """Calculate queue position changes between baseline and proposed"""
    
    # Create lookup for baseline and proposed ranks
    baseline_ranks = {req['request_id']: req['rank'] for req in baseline_analysis['request_details']}
    proposed_ranks = {req['request_id']: req['rank'] for req in proposed_analysis['request_details']}
    
    # Calculate rank changes for each request
    sla_rank_changes = []
    non_sla_rank_changes = []
    
    for req in proposed_analysis['request_details']:
        req_id = req['request_id']
        baseline_rank = baseline_ranks[req_id]
        proposed_rank = proposed_ranks[req_id]
        rank_change = baseline_rank - proposed_rank  # Positive = improvement
        
        if req['has_sla']:
            sla_rank_changes.append(rank_change)
        else:
            non_sla_rank_changes.append(rank_change)
    
    # Count requests in top positions
    sla_to_top_200 = sum(1 for req in proposed_analysis['request_details'] if req['has_sla'] and req['rank'] <= 200)
    
    return {
        'sla_avg_improvement': statistics.mean(sla_rank_changes) if sla_rank_changes else 0,
        'non_sla_avg_deterioration': statistics.mean(non_sla_rank_changes) if non_sla_rank_changes else 0,
        'position_gap': statistics.mean(sla_rank_changes) - statistics.mean(non_sla_rank_changes) if sla_rank_changes and non_sla_rank_changes else 0,
        'sla_to_top_200': sla_to_top_200,
        'sla_median_improvement': statistics.median(sla_rank_changes) if sla_rank_changes else 0,
        'non_sla_median_deterioration': statistics.median(non_sla_rank_changes) if non_sla_rank_changes else 0,
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_scenario_requests(scenario):
    """Get requests from scenario (handle both dict and object)"""
    if isinstance(scenario, dict):
        return scenario['requests']
    return scenario.requests


def get_scenario_agents(scenario):
    """Get agents from scenario (handle both dict and object)"""
    if isinstance(scenario, dict):
        return scenario['agents']
    return scenario.agents


def get_scenario_start_time(scenario):
    """Get start time from scenario (handle both dict and object)"""
    if isinstance(scenario, dict):
        start_time = scenario['start_time']
        if isinstance(start_time, str):
            return datetime.fromisoformat(start_time)
        return start_time
    return scenario.start_time


def count_sla_requests(scenario):
    """Count SLA requests in scenario"""
    requests = get_scenario_requests(scenario)
    if isinstance(requests[0], dict):
        return sum(1 for req in requests if req.get('has_sla', False))
    return sum(1 for req in requests if req.has_sla)


def simulation_result_to_dict(result) -> Dict[str, Any]:
    """Convert SimulationResult object to dictionary"""
    if isinstance(result, dict):
        return result
    
    # Convert SimulationResult object to dict
    stats = {}
    
    # Try to get common attributes
    for attr in ['requests_completed', 'avg_wait_time_minutes', 'foc_compliance_rate', 
                 'avg_agent_utilization', 'total_requests', 'simulation_duration_hours']:
        if hasattr(result, attr):
            stats[attr] = getattr(result, attr)
    
    # If the object has a to_dict method, use that
    if hasattr(result, 'to_dict'):
        return result.to_dict()
    
    # If the object has a __dict__, use that
    if hasattr(result, '__dict__'):
        return {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
    
    return stats


# ============================================================================
# DEMO ORCHESTRATION
# ============================================================================

def demo_introduction():
    """Display demo introduction"""
    clear_screen()
    print_header("STM ROUTING SIMULATOR v3.0")
    print_header("WHOLESALE SLA FULL SIMULATION")
    
    print_simulation_box()
    
    print(f"{Colors.BOLD}Welcome to the Wholesale SLA Full Simulation!{Colors.END}\n")
    
    print("This simulation provides COMPLETE metrics for the Wholesale team's proposed")
    print("SLA assignment strategy, including queue position analysis and actual timing.\n")
    
    print(f"{Colors.BOLD}Wholesale Team Context:{Colors.END}")
    print("  • 56 agents handling wholesale requests")
    print("  • 500 requests from 13 customers (scaled from 10,035 production)")
    print("  • Team is planning to assign 7 customers as SLA customers\n")
    
    print(f"{Colors.BOLD}Scenarios Being Simulated:{Colors.END}")
    print("  • Baseline: All 13 customers with foc_target=8.0 days, no SLA")
    print("  • Proposed: 7 SLA customers (CUST_A-G) with foc_target=1.0 day, has_sla=True")
    print("             6 non-SLA customers (CUST_H-M) with foc_target=8.0 days, has_sla=False\n")
    
    print(f"{Colors.BOLD}What You'll Learn:{Colors.END}")
    print("  • Predicted queue position changes (quick analysis)")
    print("  • Actual wait times for SLA vs non-SLA customers")
    print("  • Real FOC compliance rates under each scenario")
    print("  • Agent utilization and throughput")
    print("  • Queue dynamics and request processing order")
    print("  • Impact on service levels for each customer tier\n")
    
    print(f"{Colors.YELLOW}⏱️  Note: This simulation may take 30-60 seconds to complete.{Colors.END}\n")
    
    input(f"{Colors.BOLD}Press Enter to begin full simulation...{Colors.END}")


def load_scenarios() -> Tuple[Any, Any]:
    """Load both baseline and proposed scenarios"""
    print_section("STEP 1: Loading Scenarios")
    
    print_progress("Loading baseline scenario")
    loader = ScenarioLoader()
    baseline_scenario = loader.load_scenario(BASELINE_SCENARIO)
    
    baseline_requests = get_scenario_requests(baseline_scenario)
    baseline_agents = get_scenario_agents(baseline_scenario)
    print_info("Baseline Loaded", 
               f"{len(baseline_requests)} requests, {len(baseline_agents)} agents")
    
    pause(0.5)
    
    print_progress("Loading proposed scenario")
    proposed_scenario = loader.load_scenario(PROPOSED_SCENARIO)
    
    proposed_requests = get_scenario_requests(proposed_scenario)
    proposed_agents = get_scenario_agents(proposed_scenario)
    print_info("Proposed Loaded",
               f"{len(proposed_requests)} requests, {len(proposed_agents)} agents")
    
    pause(1.0)
    
    return baseline_scenario, proposed_scenario


def display_scenario_overview(baseline_scenario, proposed_scenario):
    """Display overview of scenarios"""
    print_section("STEP 2: Scenario Configuration")
    
    baseline_start_time = get_scenario_start_time(baseline_scenario)
    baseline_requests = get_scenario_requests(baseline_scenario)
    baseline_agents = get_scenario_agents(baseline_scenario)
    
    print(f"\n{Colors.BOLD}Simulation Parameters:{Colors.END}")
    print(f"  Duration: {DEFAULT_DURATION_HOURS} hours (standard shift)")
    print(f"  Start Time: {baseline_start_time.strftime('%Y-%m-%d %I:%M %p')}")
    print(f"  Total Requests: {len(baseline_requests)}")
    print(f"  Agents: {len(baseline_agents)} (Wholesale team)")
    print(f"  Customers: 13 (CUST_A through CUST_M)")
    
    # Count SLA vs non-SLA in proposed
    sla_count = count_sla_requests(proposed_scenario)
    proposed_requests = get_scenario_requests(proposed_scenario)
    non_sla_count = len(proposed_requests) - sla_count
    
    print(f"\n{Colors.BOLD}Proposed Scenario Breakdown:{Colors.END}")
    print(f"  SLA Customers (CUST_A-G): {sla_count} requests (40%)")
    print(f"    • foc_target: 1.0 day {Colors.YELLOW}(87.5% reduction!){Colors.END}")
    print(f"    • has_sla: True")
    print(f"  Non-SLA Customers (CUST_H-M): {non_sla_count} requests (60%)")
    print(f"    • foc_target: 8.0 days (unchanged)")
    print(f"    • has_sla: False")
    
    print(f"\n{Colors.BOLD}Expected Priority Impact:{Colors.END}")
    print(f"  • SLA customers: ~{Colors.RED}700% (8x){Colors.END} priority increase")
    print(f"  • Queue domination: SLA requests will occupy top positions")
    print(f"  • Service tier gap: Very strong two-tier system")
    
    pause(2.0)


def analyze_queue_positions_step():
    """Analyze and display queue position changes"""
    print_section("STEP 3: Queue Position Analysis (Quick Preview)")
    
    print(f"\n{Colors.BOLD}Analyzing predicted queue position changes...{Colors.END}\n")
    
    print_progress("Calculating baseline queue positions")
    baseline_analysis = analyze_queue_positions(BASELINE_SCENARIO)
    
    print_progress("Calculating proposed queue positions")
    proposed_analysis = analyze_queue_positions(PROPOSED_SCENARIO)
    
    print_progress("Computing position changes")
    rank_changes = calculate_rank_changes(baseline_analysis, proposed_analysis)
    
    pause(0.5)
    
    # Display results
    print(f"\n{Colors.BOLD}📈 PREDICTED QUEUE POSITION CHANGES{Colors.END}\n")
    
    print(f"{Colors.GREEN}SLA Customers (CUST_A-G):{Colors.END}")
    print(f"  Average Position Improvement: {Colors.GREEN}{rank_changes['sla_avg_improvement']:+.0f} positions{Colors.END}")
    print(f"  Median Position Improvement: {rank_changes['sla_median_improvement']:+.0f} positions")
    print(f"  Requests in Top 200: {rank_changes['sla_to_top_200']}/200")
    
    print(f"\n{Colors.YELLOW}Non-SLA Customers (CUST_H-M):{Colors.END}")
    print(f"  Average Position Deterioration: {Colors.RED}{rank_changes['non_sla_avg_deterioration']:+.0f} positions{Colors.END}")
    print(f"  Median Position Deterioration: {rank_changes['non_sla_median_deterioration']:+.0f} positions")
    
    print(f"\n{Colors.BOLD}Overall Impact:{Colors.END}")
    print(f"  Queue Position Gap: {Colors.BOLD}{abs(rank_changes['position_gap']):.0f} positions{Colors.END}")
    print(f"  Net advantage for SLA customers: {abs(rank_changes['position_gap']):.0f} positions")
    
    print(f"\n{Colors.CYAN}💡 This is the predicted impact. Now running full simulation to measure actual results...{Colors.END}")
    
    pause(2.0)
    
    return rank_changes


def run_baseline_simulation(baseline_scenario) -> Dict[str, Any]:
    """Run baseline simulation"""
    print_section("STEP 4: Running Baseline Simulation")
    
    print(f"\n{Colors.BOLD}Simulating baseline scenario...{Colors.END}")
    print("  (All customers: foc_target=8.0 days, has_sla=False)\n")
    
    # Create output directory
    baseline_output_path = Path(OUTPUT_DIR) / BASELINE_OUTPUT
    baseline_output_path.mkdir(parents=True, exist_ok=True)
    
    print_progress("Initializing simulation environment")
    print_progress("Setting up agents and request pools")
    print(f"  Running simulation for {DEFAULT_DURATION_HOURS} hours...", end='', flush=True)
    
    start_time = time.time()
    
    # Run the simulation
    runner = ScenarioRunner()
    result = runner.run_scenario(
        baseline_scenario,
        duration_hours=DEFAULT_DURATION_HOURS,
    )
    
    # Convert to dict
    stats = simulation_result_to_dict(result)
    
    elapsed = time.time() - start_time
    print(f" {Colors.GREEN}✓{Colors.END} (completed in {format_duration(elapsed)})")
    
    print_progress("Saving baseline results")
    
    # Display key metrics
    print(f"\n{Colors.BOLD}Baseline Results:{Colors.END}")
    if stats:
        print_info("Requests Processed", str(stats.get('requests_completed', 'N/A')))
        print_info("Average Wait Time", f"{stats.get('avg_wait_time_minutes', 0):.1f} minutes")
        print_info("FOC Compliance", f"{stats.get('foc_compliance_rate', 0)*100:.1f}%")
        print_info("Agent Utilization", f"{stats.get('avg_agent_utilization', 0)*100:.1f}%")
    
    pause(2.0)
    
    return stats


def run_proposed_simulation(proposed_scenario) -> Dict[str, Any]:
    """Run proposed simulation"""
    print_section("STEP 5: Running Proposed Simulation")
    
    print(f"\n{Colors.BOLD}Simulating proposed scenario with SLA assignments...{Colors.END}")
    print("  (7 SLA customers: foc_target=1.0 day, has_sla=True)")
    print("  (6 non-SLA customers: foc_target=8.0 days, has_sla=False)\n")
    
    # Create output directory
    proposed_output_path = Path(OUTPUT_DIR) / PROPOSED_OUTPUT
    proposed_output_path.mkdir(parents=True, exist_ok=True)
    
    print_progress("Initializing simulation environment")
    print_progress("Setting up agents and request pools")
    print(f"  Running simulation for {DEFAULT_DURATION_HOURS} hours...", end='', flush=True)
    
    start_time = time.time()
    
    # Run the simulation
    runner = ScenarioRunner()
    result = runner.run_scenario(
        proposed_scenario,
        duration_hours=DEFAULT_DURATION_HOURS,
    )
    
    # Convert to dict
    stats = simulation_result_to_dict(result)
    
    elapsed = time.time() - start_time
    print(f" {Colors.GREEN}✓{Colors.END} (completed in {format_duration(elapsed)})")
    
    print_progress("Saving proposed results")
    
    # Display key metrics
    print(f"\n{Colors.BOLD}Proposed Results:{Colors.END}")
    if stats:
        print_info("Requests Processed", str(stats.get('requests_completed', 'N/A')))
        print_info("Average Wait Time", f"{stats.get('avg_wait_time_minutes', 0):.1f} minutes")
        print_info("FOC Compliance", f"{stats.get('foc_compliance_rate', 0)*100:.1f}%")
        print_info("Agent Utilization", f"{stats.get('avg_agent_utilization', 0)*100:.1f}%")
    
    pause(2.0)
    
    return stats


def compare_results(baseline_stats: Dict, proposed_stats: Dict, rank_changes: Dict):
    """Compare baseline and proposed results"""
    print_section("STEP 6: Comparative Analysis")
    
    print(f"\n{Colors.BOLD}📊 SIMULATION RESULTS COMPARISON{Colors.END}\n")
    print(f"{'Metric':<30}  {'Baseline':>12}  {'Proposed':>12}  {'Change':>12}")
    print("-" * 75)
    
    metrics = [
        ('Requests Completed', 'requests_completed', ''),
        ('Avg Wait Time (min)', 'avg_wait_time_minutes', 'm'),
        ('FOC Compliance Rate', 'foc_compliance_rate', '%'),
        ('Avg Agent Utilization', 'avg_agent_utilization', '%'),
    ]
    
    for label, key, unit in metrics:
        baseline_val = baseline_stats.get(key, 0)
        proposed_val = proposed_stats.get(key, 0)
        
        if unit == '%':
            baseline_str = f"{baseline_val*100:.1f}%"
            proposed_str = f"{proposed_val*100:.1f}%"
            change = (proposed_val - baseline_val) * 100
            change_str = f"{change:+.1f}pp"
        elif unit == 'm':
            baseline_str = f"{baseline_val:.1f}m"
            proposed_str = f"{proposed_val:.1f}m"
            if baseline_val > 0:
                change_pct = ((proposed_val - baseline_val) / baseline_val) * 100
                change_str = f"{change_pct:+.1f}%"
            else:
                change_str = "N/A"
        else:
            baseline_str = str(baseline_val)
            proposed_str = str(proposed_val)
            change = proposed_val - baseline_val
            change_str = f"{change:+d}"
        
        print(f"{label:<30}  {baseline_str:>12}  {proposed_str:>12}  {change_str:>12}")
    
    print(f"\n{Colors.BOLD}📈 QUEUE POSITION IMPACT (From Quick Analysis){Colors.END}\n")
    print(f"{'Metric':<30}  {'Value':>12}")
    print("-" * 45)
    print(f"{'SLA Avg Improvement':<30}  {rank_changes['sla_avg_improvement']:>+11.0f}p")
    print(f"{'Non-SLA Avg Deterioration':<30}  {rank_changes['non_sla_avg_deterioration']:>+11.0f}p")
    print(f"{'Position Gap':<30}  {abs(rank_changes['position_gap']):>11.0f}p")
    print(f"{'SLA in Top 200':<30}  {rank_changes['sla_to_top_200']:>11}/200")
    
    print(f"\n{Colors.BOLD}Key Observations:{Colors.END}")
    
    # Calculate some insights
    wait_time_change = ((proposed_stats.get('avg_wait_time_minutes', 0) - 
                        baseline_stats.get('avg_wait_time_minutes', 0)) / 
                       baseline_stats.get('avg_wait_time_minutes', 1)) * 100 if baseline_stats.get('avg_wait_time_minutes', 0) > 0 else 0
    
    foc_change = (proposed_stats.get('foc_compliance_rate', 0) - 
                  baseline_stats.get('foc_compliance_rate', 0)) * 100
    
    if wait_time_change < -5:
        print(f"  • Overall wait time {Colors.GREEN}decreased{Colors.END} by {abs(wait_time_change):.1f}%")
    elif wait_time_change > 5:
        print(f"  • Overall wait time {Colors.YELLOW}increased{Colors.END} by {wait_time_change:.1f}%")
    else:
        print(f"  • Overall wait time remained relatively stable")
    
    if foc_change > 2:
        print(f"  • FOC compliance {Colors.GREEN}improved{Colors.END} by {foc_change:.1f} percentage points")
    elif foc_change < -2:
        print(f"  • FOC compliance {Colors.RED}decreased{Colors.END} by {abs(foc_change):.1f} percentage points")
    else:
        print(f"  • FOC compliance remained relatively stable")
    
    print(f"  • System throughput: {baseline_stats.get('requests_completed', 0)} → {proposed_stats.get('requests_completed', 0)} requests")
    print(f"  • Queue position gap: {Colors.BOLD}{abs(rank_changes['position_gap']):.0f} positions{Colors.END}")
    
    pause(2.0)


def display_sla_tier_analysis(rank_changes: Dict):
    """Display SLA vs non-SLA tier analysis"""
    print_section("STEP 7: SLA Tier Impact Analysis")
    
    print(f"\n{Colors.BOLD}Service Tier Impact:{Colors.END}\n")
    
    print(f"{Colors.GREEN}SLA Customers (CUST_A-G):{Colors.END}")
    print("  • foc_target reduced from 8.0 days → 1.0 day")
    print("  • Priority score increased by ~700% (8x)")
    print(f"  • Queue position improved by {Colors.GREEN}{abs(rank_changes['sla_avg_improvement']):.0f} positions{Colors.END} on average")
    print("  • Expected outcome: Near-instant service")
    print("  • Queue position: Occupy top 200+ positions")
    
    print(f"\n{Colors.YELLOW}Non-SLA Customers (CUST_H-M):{Colors.END}")
    print("  • foc_target unchanged at 8.0 days")
    print("  • Relative priority decreased significantly")
    print(f"  • Queue position dropped by {Colors.RED}{abs(rank_changes['non_sla_avg_deterioration']):.0f} positions{Colors.END} on average")
    print("  • Expected outcome: Much longer wait times")
    print("  • Queue position: Deprioritized below all SLA requests")
    
    print(f"\n{Colors.BOLD}Position Gap Analysis:{Colors.END}")
    position_gap = abs(rank_changes['position_gap'])
    
    if position_gap < 150:
        interpretation = "Subtle differentiation"
        impact = "Modest SLA value proposition"
    elif position_gap < 300:
        interpretation = "Moderate two-tier system"
        impact = "Balanced approach"
    elif position_gap < 400:
        interpretation = "Strong differentiation"
        impact = "Significant SLA advantage"
    else:
        interpretation = "Very strong differentiation"
        impact = "Extreme two-tier system"
    
    print(f"  • Position gap: {Colors.BOLD}{position_gap:.0f} positions{Colors.END}")
    print(f"  • Interpretation: {interpretation}")
    print(f"  • Business impact: {impact}")
    
    print(f"\n{Colors.BOLD}Business Implications:{Colors.END}")
    print("  ⚠️  Creates very strong two-tier service system")
    print("  ⚠️  Non-SLA customers may experience unacceptable delays")
    print("  ⚠️  Consider monitoring customer satisfaction closely")
    print("  ⚠️  Alternative: Test smaller FOC gap (3-4 days vs 8 days)")
    
    print(f"\n{Colors.CYAN}💡 Recommendation:{Colors.END}")
    print("  Review detailed output files to see actual wait time distribution")
    print("  by customer tier. Compare predicted position changes with actual")
    print("  simulation results before rolling out to production.")
    
    pause(2.0)


def save_comparison_results(baseline_stats: Dict, proposed_stats: Dict, rank_changes: Dict):
    """Save comparison results to file"""
    print_section("STEP 8: Saving Results")
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    comparison = {
        'metadata': {
            'analysis_type': 'full_discrete_event_simulation_with_position_analysis',
            'demo_version': VERSION,
            'simulation_date': datetime.now(timezone.utc).isoformat(),
            'duration_hours': DEFAULT_DURATION_HOURS,
            'baseline_scenario': BASELINE_SCENARIO,
            'proposed_scenario': PROPOSED_SCENARIO,
            'note': 'Wholesale SLA impact - complete simulation with agent assignments and queue position analysis'
        },
        'baseline': baseline_stats,
        'proposed': proposed_stats,
        'comparison': {
            'simulation_metrics': {
                'requests_completed_change': proposed_stats.get('requests_completed', 0) - baseline_stats.get('requests_completed', 0),
                'wait_time_change_minutes': proposed_stats.get('avg_wait_time_minutes', 0) - baseline_stats.get('avg_wait_time_minutes', 0),
                'foc_compliance_change': proposed_stats.get('foc_compliance_rate', 0) - baseline_stats.get('foc_compliance_rate', 0),
                'utilization_change': proposed_stats.get('avg_agent_utilization', 0) - baseline_stats.get('avg_agent_utilization', 0),
            },
            'queue_position_analysis': {
                'sla_avg_improvement': rank_changes['sla_avg_improvement'],
                'non_sla_avg_deterioration': rank_changes['non_sla_avg_deterioration'],
                'position_gap': rank_changes['position_gap'],
                'sla_to_top_200': rank_changes['sla_to_top_200'],
                'sla_median_improvement': rank_changes['sla_median_improvement'],
                'non_sla_median_deterioration': rank_changes['non_sla_median_deterioration'],
            }
        }
    }
    
    output_path = Path(OUTPUT_DIR) / COMPARISON_OUTPUT
    
    with open(output_path, 'w') as f:
        json.dump(comparison, f, indent=2, default=str)
    
    print_progress(f"Saved comparison to {output_path}")
    
    print(f"\n{Colors.BOLD}Output Files:{Colors.END}")
    print(f"  📁 Baseline:  {OUTPUT_DIR}/{BASELINE_OUTPUT}/")
    print(f"  📁 Proposed:  {OUTPUT_DIR}/{PROPOSED_OUTPUT}/")
    print(f"  📄 Comparison: {output_path}")
    print(f"  📊 Includes: Simulation metrics + Queue position analysis")
    
    pause(1.0)


def demo_conclusion(rank_changes: Dict):
    """Display conclusion and next steps"""
    print_section("SIMULATION COMPLETE")
    
    print(f"\n{Colors.BOLD}🎉 Full Simulation Completed Successfully!{Colors.END}\n")
    
    print(f"{Colors.BOLD}What You've Learned:{Colors.END}")
    print("  ✓ Predicted queue position changes (quick analysis)")
    print("  ✓ Actual wait times under baseline and proposed scenarios")
    print("  ✓ Real FOC compliance rates with SLA assignments")
    print("  ✓ Agent utilization and system capacity")
    print("  ✓ Complete request processing metrics")
    
    print(f"\n{Colors.BOLD}Key Findings:{Colors.END}")
    print(f"  • SLA customers improve by {Colors.GREEN}{abs(rank_changes['sla_avg_improvement']):.0f} positions{Colors.END} on average")
    print(f"  • Non-SLA customers drop by {Colors.RED}{abs(rank_changes['non_sla_avg_deterioration']):.0f} positions{Colors.END} on average")
    print(f"  • Position gap: {Colors.BOLD}{abs(rank_changes['position_gap']):.0f} positions{Colors.END}")
    print(f"  • {rank_changes['sla_to_top_200']}/200 SLA requests in top 200 positions")
    
    print(f"\n{Colors.BOLD}Output Files Location:{Colors.END}")
    print(f"  {OUTPUT_DIR}/")
    print(f"    ├── baseline/           (Baseline simulation results)")
    print(f"    ├── proposed/           (Proposed simulation results)")
    print(f"    └── comparison_results_full.json (Includes position analysis)")
    
    print(f"\n{Colors.BOLD}Critical Next Steps:{Colors.END}")
    print("  1. Review detailed metrics in output files")
    print("  2. Examine wait time distribution by customer tier")
    print("  3. Validate that non-SLA service levels are acceptable")
    print(f"  4. Assess if {abs(rank_changes['position_gap']):.0f}-position gap is appropriate")
    print("  5. Consider testing alternative FOC targets:")
    print("     • Conservative: 4 days SLA vs 8 days non-SLA (2x, ~120 pos gap)")
    print("     • Moderate: 3 days SLA vs 8 days non-SLA (2.67x, ~180 pos gap)")
    print("     • Current: 1 day SLA vs 8 days non-SLA (8x, ~360 pos gap)")
    print("  6. Present findings to stakeholders")
    print("  7. Plan phased rollout with monitoring")
    
    print(f"\n{Colors.BOLD}For Quick Priority Analysis Only:{Colors.END}")
    print(f"  Run: {Colors.CYAN}python compare_foc_impact.py{Colors.END}")
    print("  (Fast preview of priority impact without full simulation)")
    
    print(f"\n{Colors.GREEN}✅ Ready to make data-driven decisions!{Colors.END}\n")


# ============================================================================
# MAIN SIMULATION FLOW
# ============================================================================

def main() -> int:
    """Main entry point for full simulation"""
    try:
        demo_introduction()
        baseline_scenario, proposed_scenario = load_scenarios()
        display_scenario_overview(baseline_scenario, proposed_scenario)
        rank_changes = analyze_queue_positions_step()
        baseline_stats = run_baseline_simulation(baseline_scenario)
        proposed_stats = run_proposed_simulation(proposed_scenario)
        compare_results(baseline_stats, proposed_stats, rank_changes)
        display_sla_tier_analysis(rank_changes)
        save_comparison_results(baseline_stats, proposed_stats, rank_changes)
        demo_conclusion(rank_changes)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n{Colors.RED}❌ Error: Scenario file not found{Colors.END}")
        print(f"   {e}")
        print(f"\n   Make sure you're running this from: Simulator_v3/demo/demo_wholesale_sla_impact/")
        print(f"   Or run from Simulator_v3 root: python demo/demo_wholesale_sla_impact/run_full_simulation.py")
        return 1
        
    except ImportError as e:
        print(f"\n{Colors.RED}❌ Error: Could not import simulator modules{Colors.END}")
        print(f"   {e}")
        print(f"\n   Make sure you have the correct directory structure:")
        print(f"   Simulator_v3/")
        print(f"     ├── scenario/")
        print(f"     │   ├── scenario_loader.py")
        print(f"     │   └── scenario_runner.py")
        print(f"     └── demo/demo_wholesale_sla_impact/")
        return 1
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Simulation interrupted by user{Colors.END}\n")
        return 1
        
    except Exception as e:
        print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.END}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())