#!/usr/bin/env python3
"""
STM Routing Simulator v3.0 - 8-Hour Shift Demo

This demonstration simulates a realistic 8-hour morning shift showing:
- Real-time progression through the day
- Priority request handling
- Followup vs CMO routing
- Absent agent work redistribution
- Agent workload balancing
- Hourly statistics

Usage:
    python demo_8hour_shift.py
"""

import sys
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path to import simulator modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scenario.scenario_loader import ScenarioLoader
from scenario.scenario_runner import ScenarioRunner


# ============================================================================
# DEMO CONFIGURATION
# ============================================================================

SCENARIO_FILE = "demo/scenarios/morning_shift_demo.yaml"
OUTPUT_DIR = "demo/output"
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


def print_info(label: str, value: str, color=Colors.GREEN):
    """Print formatted info line"""
    print(f"  {Colors.BOLD}{label}:{Colors.END} {color}{value}{Colors.END}")


def print_progress_bar(current: int, total: int, label: str = "Progress"):
    """Print a progress bar"""
    bar_length = 50
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = '█' * filled + '░' * (bar_length - filled)
    percent = 100 * current / total if total > 0 else 0
    print(f"\r  {label}: [{bar}] {percent:.1f}% ({current}/{total})", end='', flush=True)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def safe_get_datetime(obj: Any) -> datetime:
    """
    Safely convert various timestamp formats to datetime object.
    
    Handles:
    - datetime objects (return as-is)
    - ISO format strings
    - Timestamp strings with 'Z'
    - Unix timestamps (float/int)
    """
    if isinstance(obj, datetime):
        return obj
    elif isinstance(obj, str):
        # Handle ISO format with Z
        if obj.endswith('Z'):
            obj = obj.replace('Z', '+00:00')
        try:
            return datetime.fromisoformat(obj)
        except ValueError:
            # Try parsing without timezone
            return datetime.strptime(obj, "%Y-%m-%dT%H:%M:%S")
    elif isinstance(obj, (int, float)):
        # Unix timestamp
        return datetime.fromtimestamp(obj, tz=timezone.utc)
    else:
        raise ValueError(f"Cannot convert {type(obj)} to datetime: {obj}")


def safe_get_value(obj: Any, key: str, default: Any = None) -> Any:
    """Safely get a value from dict or object attribute"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    else:
        return getattr(obj, key, default)


def calculate_handle_time(request, simulation_config):
    """
    Calculate handle time for a request based on priority and config.
    
    Args:
        request: Request object
        simulation_config: Dict with handle time configuration
        
    Returns:
        float: Handle time in minutes
    """
    import random
    
    # Check if request is a followup
    is_followup = safe_get_value(request, 'sticky_agent_id') is not None
    
    if is_followup:
        # Followups are typically faster
        base_time = simulation_config.get('followup_handle_time', 12)
    else:
        # Get priority-based handle time
        priority_times = simulation_config.get('priority_handle_times', {})
        
        # Determine priority
        is_winback = safe_get_value(request, 'is_winback', False)
        is_atl_rf = safe_get_value(request, 'is_atl_rf', False)
        is_escalated = safe_get_value(request, 'is_escalated', False)
        has_sla = safe_get_value(request, 'has_sla', False)
        
        if (is_winback or is_atl_rf) and is_escalated:
            priority = 1
        elif (is_winback or is_atl_rf) and not is_escalated:
            priority = 2
        elif has_sla and is_escalated:
            priority = 3
        elif not has_sla and is_escalated:
            priority = 4
        else:
            priority = 5
        
        # Get handle time for this priority
        base_time = priority_times.get(priority, simulation_config.get('default_handle_time', 15))
    
    # Add variation
    std_dev = simulation_config.get('handle_time_std_dev', 4)
    handle_time = max(5, random.gauss(base_time, std_dev))  # Minimum 5 minutes
    
    return handle_time


# ============================================================================
# DEMO ORCHESTRATION
# ============================================================================

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def pause(seconds: float = 1.0):
    """Pause execution with demo speed consideration"""
    speed_multipliers = {
        'fast': 0.3,
        'normal': 1.0,
        'slow': 2.0
    }
    time.sleep(seconds * speed_multipliers.get(DEMO_SPEED, 1.0))


def demo_introduction():
    """Display demo introduction"""
    clear_screen()
    print_header("STM ROUTING SIMULATOR v3.0")
    print_header("8-HOUR SHIFT DEMONSTRATION")
    
    print(f"\n{Colors.BOLD}Welcome to the STM Routing Simulator Demo!{Colors.END}\n")
    
    print("This demonstration will simulate a realistic 8-hour morning shift")
    print("(9:00 AM - 5:00 PM EST) showing how the system routes customer")
    print("service requests to available agents.\n")
    
    print(f"{Colors.BOLD}What you'll see:{Colors.END}")
    print("  • Real-time progression through the work day")
    print("  • Priority request handling (Winback, Escalated, SLA)")
    print("  • Followup vs CMO (Common Mailbox) routing")
    print("  • Work redistribution from absent agents")
    print("  • Agent workload balancing")
    print("  • Hourly statistics and metrics\n")
    
    print(f"{Colors.BOLD}Scenario Setup:{Colors.END}")
    print("  • 6 agents (5 working, 1 absent on vacation)")
    print("  • 33 total requests (25 new + 8 followups)")
    print("  • Mix of all 5 priority levels")
    print("  • Shift duration: 8 hours\n")
    
    input(f"{Colors.BOLD}Press Enter to begin the simulation...{Colors.END}")


def load_and_validate_scenario():
    """Load scenario and display initial state"""
    print_section("STEP 1: Loading Scenario")
    
    print(f"  Loading scenario from: {SCENARIO_FILE}")
    pause(0.5)
    
    loader = ScenarioLoader()
    scenario = loader.load_scenario(SCENARIO_FILE)
    
    print(f"  {Colors.GREEN}✓{Colors.END} Scenario loaded successfully")
    pause(0.5)
    
    # Display scenario summary
    print(f"\n{Colors.BOLD}Scenario Details:{Colors.END}")
    print_info("Name", scenario['name'])
    
    start_time = scenario['start_time']
    if isinstance(start_time, datetime):
        print_info("Start Time", start_time.strftime("%Y-%m-%d %I:%M %p %Z"))
    else:
        print_info("Start Time", str(start_time))
    
    print_info("Total Agents", str(len(scenario['agents'])))
    print_info("Total Requests", str(len(scenario['requests'])))
    
    # Count absent agents
    absent_count = sum(1 for a in scenario['agents'] if safe_get_value(a, 'is_absent', False))
    present_count = len(scenario['agents']) - absent_count
    print_info("Working Agents", f"{present_count} (+ {absent_count} absent)")
    
    # Count followups
    followup_count = sum(1 for r in scenario['requests'] if safe_get_value(r, 'sticky_agent_id') is not None)
    cmo_count = len(scenario['requests']) - followup_count
    print_info("Request Mix", f"{cmo_count} CMO + {followup_count} Followups")
    
    pause(1.0)
    
    return scenario


def display_team_roster(scenario: Dict):
    """Display team roster with status"""
    print_section("STEP 2: Team Roster")
    
    agents = scenario['agents']
    
    print(f"\n{Colors.BOLD}Agent Status:{Colors.END}\n")
    print(f"  {'Agent ID':<20} {'Name':<25} {'Skills':<30} {'Status':<10}")
    print("  " + "─" * 95)
    
    for agent in agents:
        agent_id = safe_get_value(agent, 'agent_id', 'unknown')
        name = safe_get_value(agent, 'full_name', 'Unknown')
        
        skillsets = safe_get_value(agent, 'skillsets', set())
        if isinstance(skillsets, set):
            skills = ", ".join(sorted(list(skillsets)))
        else:
            skills = str(skillsets)
        
        is_absent = safe_get_value(agent, 'is_absent', False)
        
        if is_absent:
            status = f"{Colors.RED}ABSENT{Colors.END}"
        else:
            status = f"{Colors.GREEN}AVAILABLE{Colors.END}"
        
        print(f"  {agent_id:<20} {name:<25} {skills:<30} {status}")
    
    pause(2.0)


def display_request_summary(scenario: Dict):
    """Display request backlog summary"""
    print_section("STEP 3: Request Backlog")
    
    requests = scenario['requests']
    
    # Categorize requests
    priority_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    followup_count = 0
    from_absent_count = 0
    
    for req in requests:
        # Simplified priority calculation for display
        is_winback = safe_get_value(req, 'is_winback', False)
        is_atl_rf = safe_get_value(req, 'is_atl_rf', False)
        is_escalated = safe_get_value(req, 'is_escalated', False)
        has_sla = safe_get_value(req, 'has_sla', False)
        
        if (is_winback or is_atl_rf) and is_escalated:
            priority_counts[1] += 1
        elif (is_winback or is_atl_rf) and not is_escalated:
            priority_counts[2] += 1
        elif has_sla and is_escalated:
            priority_counts[3] += 1
        elif not has_sla and is_escalated:
            priority_counts[4] += 1
        else:
            priority_counts[5] += 1
        
        sticky_agent_id = safe_get_value(req, 'sticky_agent_id')
        if sticky_agent_id:
            followup_count += 1
            # Check if assigned to absent agent
            absent_agents = [safe_get_value(a, 'agent_id') for a in scenario['agents'] 
                           if safe_get_value(a, 'is_absent', False)]
            if sticky_agent_id in absent_agents:
                from_absent_count += 1
    
    print(f"\n{Colors.BOLD}Backlog Composition:{Colors.END}\n")
    print(f"  Total Requests: {Colors.BOLD}{len(requests)}{Colors.END}")
    print(f"  CMO Requests: {len(requests) - followup_count}")
    print(f"  Followup Requests: {followup_count}")
    
    if from_absent_count > 0:
        print(f"  {Colors.YELLOW}⚠ Followups from absent agents: {from_absent_count}{Colors.END}")
        print(f"    (These will be redistributed as CMO requests)")
    
    print(f"\n{Colors.BOLD}Priority Distribution:{Colors.END}\n")
    priority_labels = {
        1: "Priority 1 - Winback/ATL + Escalated",
        2: "Priority 2 - Winback/ATL (not escalated)",
        3: "Priority 3 - SLA + Escalated",
        4: "Priority 4 - Escalated (no SLA)",
        5: "Priority 5 - Commons"
    }
    
    for priority, count in priority_counts.items():
        if count > 0:
            bar_length = int(30 * count / len(requests)) if len(requests) > 0 else 0
            bar = '█' * bar_length
            print(f"  {priority_labels[priority]:<45} {bar} ({count})")
    
    pause(2.0)


def run_simulation_with_progress(scenario: Dict):
    """Run simulation with progress updates"""
    print_section("STEP 4: Running Simulation")
    
    print(f"\n{Colors.BOLD}Starting 8-hour shift simulation...{Colors.END}\n")
    pause(1.0)
    
    # Create runner
    runner = ScenarioRunner()
    
    print("  Initializing simulation engine...")
    pause(0.5)
    print(f"  {Colors.GREEN}✓{Colors.END} Engine initialized")
    
    print("  Processing events...")
    pause(0.5)
    
    # Run simulation with 8-hour duration
    result = runner.run_scenario(
        scenario=scenario,
        duration_hours=8.0,  # Stop after 8 hours
        stop_when_idle=False,  # Don't stop early if agents idle
        verbose=False
    )
    
    # Get total events processed
    total_events = safe_get_value(safe_get_value(result.statistics, 'events', {}), 'total_processed', 0)
    
    if total_events == 0:
        total_events = len(result.assignments) if hasattr(result, 'assignments') else 100
    
    # Simulate progress for demo effect
    for i in range(1, total_events + 1):
        print_progress_bar(i, total_events, "Simulating")
        pause(0.02)
    
    print()  # New line after progress bar
    print(f"  {Colors.GREEN}✓{Colors.END} Simulation complete!")
    
    # Display simulation summary
    duration = safe_get_value(safe_get_value(result.statistics, 'timing', {}), 'duration_hours', 0)
    assignments = safe_get_value(safe_get_value(result.statistics, 'assignments', {}), 'total', 0)
    
    print(f"\n  {Colors.CYAN}Simulation ran for {duration:.1f} hours{Colors.END}")
    print(f"  {Colors.CYAN}Processed {assignments} assignments{Colors.END}")
    
    pause(1.0)
    
    return result


def display_shift_timeline(result):
    """Display timeline of assignments throughout the shift"""
    print_section("STEP 5: Shift Timeline")
    
    # Get assignments - handle both dict and object attributes
    if hasattr(result, 'assignments'):
        assignments = result.assignments
    else:
        assignments = result.get('assignments', [])
    
    if not assignments:
        print(f"  {Colors.YELLOW}No assignments to display.{Colors.END}")
        return
    
    # Group assignments by hour
    hourly_assignments = {}
    
    for assignment in assignments:
        try:
            # Get timestamp - try multiple methods
            timestamp_raw = safe_get_value(assignment, 'timestamp')
            timestamp = safe_get_datetime(timestamp_raw)
            
            # Round to hour
            hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
            
            if hour_key not in hourly_assignments:
                hourly_assignments[hour_key] = []
            hourly_assignments[hour_key].append(assignment)
            
        except Exception as e:
            # Skip this assignment if we can't parse it
            print(f"  {Colors.YELLOW}Warning: Could not parse timestamp for assignment{Colors.END}")
            continue
    
    if not hourly_assignments:
        print(f"  {Colors.YELLOW}Could not group assignments by hour.{Colors.END}")
        return
    
    # Display timeline
    print(f"\n{Colors.BOLD}Assignment Timeline:{Colors.END}\n")
    
    sorted_hours = sorted(hourly_assignments.keys())
    for hour in sorted_hours:
        hour_str = hour.strftime("%I:%M %p")
        count = len(hourly_assignments[hour])
        
        # Create visual bar
        bar_length = min(50, count * 2)
        bar = '█' * bar_length
        
        print(f"  {hour_str:<12} {bar} {Colors.BOLD}{count}{Colors.END} assignments")
        
        # Show sample assignments for first hour only
        if hour == sorted_hours[0]:
            print(f"    {Colors.CYAN}Sample assignments:{Colors.END}")
            sample_count = min(3, len(hourly_assignments[hour]))
            
            for i in range(sample_count):
                assignment = hourly_assignments[hour][i]
                
                agent_id = safe_get_value(assignment, 'agent_id', 'unknown')
                if '.' in str(agent_id):
                    agent_id = str(agent_id).split('.')[0]  # Just first name
                
                request_id = safe_get_value(assignment, 'request_id', 'unknown')
                priority = safe_get_value(assignment, 'priority_level', 5)
                
                priority_str = f"P{priority}"
                if priority <= 2:
                    priority_color = Colors.RED
                elif priority <= 4:
                    priority_color = Colors.YELLOW
                else:
                    priority_color = Colors.GREEN
                
                print(f"      • {agent_id.title()} ← {request_id} ({priority_color}{priority_str}{Colors.END})")
            
            if len(hourly_assignments[hour]) > sample_count:
                remaining = len(hourly_assignments[hour]) - sample_count
                print(f"      ... and {remaining} more")
    
    pause(2.0)


def display_agent_performance(result):
    """Display agent performance metrics"""
    print_section("STEP 6: Agent Performance")
    
    # Get workload analysis
    runner = ScenarioRunner()
    
    try:
        workload = runner.get_agent_workload_analysis(result)
    except Exception as e:
        print(f"  {Colors.YELLOW}Could not generate workload analysis: {e}{Colors.END}")
        return
    
    print(f"\n{Colors.BOLD}Agent Workload:{Colors.END}\n")
    print(f"  {'Agent':<20} {'Assignments':<15} {'Workload Bar':<40} {'P1-P2':<10}")
    print("  " + "─" * 85)
    
    assignments_per_agent = workload.get('assignments_per_agent', {})
    priority_per_agent = workload.get('priority_distribution_per_agent', {})
    
    if not assignments_per_agent:
        print(f"  {Colors.YELLOW}No agent assignments to display.{Colors.END}")
        return
    
    max_assignments = max(assignments_per_agent.values()) if assignments_per_agent else 1
    
    for agent_id in sorted(assignments_per_agent.keys()):
        count = assignments_per_agent[agent_id]
        
        # Create workload bar
        if max_assignments > 0:
            bar_length = int(30 * count / max_assignments)
        else:
            bar_length = 0
        bar = '█' * bar_length + '░' * (30 - bar_length)
        
        # Count high-priority assignments
        priorities = priority_per_agent.get(agent_id, {})
        high_priority = priorities.get(1, 0) + priorities.get(2, 0)
        
        # Color based on workload
        avg_assignments = workload.get('average_assignments', 0)
        if count == 0:
            count_color = Colors.RED
        elif count < avg_assignments:
            count_color = Colors.YELLOW
        else:
            count_color = Colors.GREEN
        
        print(f"  {agent_id:<20} {count_color}{count:<15}{Colors.END} {bar:<40} {high_priority}")
    
    # Summary statistics
    print(f"\n{Colors.BOLD}Statistics:{Colors.END}")
    print_info("Average Assignments", f"{workload.get('average_assignments', 0):.1f}")
    print_info("Max Assignments", str(workload.get('max_assignments', 0)))
    print_info("Min Assignments", str(workload.get('min_assignments', 0)))
    print_info("Agents with Work", f"{workload.get('agents_with_work', 0)}/{workload.get('total_agents', 0)}")
    
    pause(2.0)


def display_priority_breakdown(result):
    """Display priority distribution breakdown"""
    print_section("STEP 7: Priority Analysis")
    
    # Get assignments
    if hasattr(result, 'assignments'):
        assignments = result.assignments
    else:
        assignments = result.get('assignments', [])
    
    # Get statistics
    if hasattr(result, 'statistics'):
        statistics = result.statistics
    else:
        statistics = result.get('statistics', {})
    
    assignment_stats = safe_get_value(statistics, 'assignments', {})
    priority_dist = safe_get_value(assignment_stats, 'by_priority', {})
    total_assignments = safe_get_value(assignment_stats, 'total', len(assignments))
    
    print(f"\n{Colors.BOLD}Requests Processed by Priority:{Colors.END}\n")
    
    priority_labels = {
        1: ("Priority 1", "Winback/ATL + Escalated", Colors.RED),
        2: ("Priority 2", "Winback/ATL", Colors.YELLOW),
        3: ("Priority 3", "SLA + Escalated", Colors.YELLOW),
        4: ("Priority 4", "Escalated", Colors.YELLOW),
        5: ("Priority 5", "Commons", Colors.GREEN)
    }
    
    for priority in [1, 2, 3, 4, 5]:
        count = priority_dist.get(priority, 0)
        if count > 0:
            label, description, color = priority_labels[priority]
            percentage = (count / total_assignments * 100) if total_assignments > 0 else 0
            
            bar_length = int(40 * percentage / 100)
            bar = '█' * bar_length
            
            print(f"  {label:<12} {description:<30} {color}{bar:<40}{Colors.END} {count} ({percentage:.1f}%)")
    
    # Followup vs CMO
    followup_count = safe_get_value(assignment_stats, 'followup_count', 0)
    cmo_count = safe_get_value(assignment_stats, 'cmo_count', 0)
    from_absent = safe_get_value(assignment_stats, 'from_absent_agent_count', 0)
    
    print(f"\n{Colors.BOLD}Request Types:{Colors.END}")
    print_info("CMO Requests", str(cmo_count))
    print_info("Followup Requests", str(followup_count))
    
    if from_absent > 0:
        print_info("Redistributed from Absent", f"{Colors.YELLOW}{from_absent}{Colors.END}")
    
    pause(2.0)


def display_final_summary(result):
    """Display final summary statistics"""
    print_section("STEP 8: Final Summary")
    
    # Get statistics
    if hasattr(result, 'statistics'):
        statistics = result.statistics
    else:
        statistics = result.get('statistics', {})
    
    print(f"\n{Colors.BOLD}Shift Summary:{Colors.END}\n")
    
    # Timing
    timing_stats = safe_get_value(statistics, 'timing', {})
    duration_hours = safe_get_value(timing_stats, 'duration_hours', 8.0)
    print(f"  {Colors.BOLD}Shift Duration:{Colors.END} {duration_hours:.1f} hours (9 AM - 5 PM EST)")
    
    # Assignments
    assignment_stats = safe_get_value(statistics, 'assignments', {})
    total = safe_get_value(assignment_stats, 'total', 0)
    print(f"  {Colors.BOLD}Total Assignments:{Colors.END} {Colors.GREEN}{total}{Colors.END}")
    
    # Requests
    request_stats = safe_get_value(statistics, 'requests', {})
    total_requests = safe_get_value(request_stats, 'total_requests', 0)
    assigned = safe_get_value(request_stats, 'assigned_requests', 0)
    pending = safe_get_value(request_stats, 'pending_requests', 0)
    
    completion_rate = (assigned / total_requests * 100) if total_requests > 0 else 0
    
    print(f"  {Colors.BOLD}Completion Rate:{Colors.END} {Colors.GREEN}{completion_rate:.1f}%{Colors.END} ({assigned}/{total_requests})")
    
    if pending > 0:
        print(f"  {Colors.YELLOW}Pending Requests:{Colors.END} {pending} (will be processed next shift)")
    
    # Routing efficiency
    routing_stats = safe_get_value(statistics, 'routing', {})
    routing_success = safe_get_value(routing_stats, 'success_rate', 0.0)
    print(f"  {Colors.BOLD}Routing Success Rate:{Colors.END} {routing_success:.1%}")
    
    # Agent utilization
    agent_stats = safe_get_value(statistics, 'agents', {})
    agents_with_work = safe_get_value(agent_stats, 'agents_with_assignments', 0)
    total_agents = safe_get_value(agent_stats, 'total_agents', 0)
    print(f"  {Colors.BOLD}Agent Utilization:{Colors.END} {agents_with_work}/{total_agents} agents active")
    
    pause(2.0)


def save_detailed_report(result):
    """Save detailed report to file"""
    print_section("STEP 9: Generating Reports")
    
    # Create output directory
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    print("\n  Generating reports...")
    pause(0.5)
    
    runner = ScenarioRunner()
    
    try:
        # Save JSON
        json_path = os.path.join(OUTPUT_DIR, "shift_results.json")
        runner.save_result(result, json_path)
        print(f"  {Colors.GREEN}✓{Colors.END} JSON report: {json_path}")
        pause(0.3)
    except Exception as e:
        print(f"  {Colors.YELLOW}⚠{Colors.END} Could not save JSON: {e}")
    
    try:
        # Save CSV
        csv_path = os.path.join(OUTPUT_DIR, "assignments.csv")
        runner.export_assignments_csv(result, csv_path)
        print(f"  {Colors.GREEN}✓{Colors.END} CSV export: {csv_path}")
        pause(0.3)
    except Exception as e:
        print(f"  {Colors.YELLOW}⚠{Colors.END} Could not save CSV: {e}")
    
    try:
        # Save timeline
        timeline_path = os.path.join(OUTPUT_DIR, "shift_timeline.txt")
        
        # Get assignments
        if hasattr(result, 'assignments'):
            assignments = result.assignments
        else:
            assignments = result.get('assignments', [])
        
        with open(timeline_path, 'w') as f:
            f.write("STM Routing Simulator - Shift Timeline\n")
            f.write("=" * 80 + "\n\n")
            
            for assignment in assignments:
                timestamp = safe_get_value(assignment, 'timestamp', 'unknown')
                agent = safe_get_value(assignment, 'agent_id', 'unknown')
                request = safe_get_value(assignment, 'request_id', 'unknown')
                priority = safe_get_value(assignment, 'priority_level', 'N/A')
                
                f.write(f"{timestamp} - Agent {agent} ← Request {request} (Priority {priority})\n")
        
        print(f"  {Colors.GREEN}✓{Colors.END} Timeline: {timeline_path}")
        pause(0.3)
    except Exception as e:
        print(f"  {Colors.YELLOW}⚠{Colors.END} Could not save timeline: {e}")
    
    print(f"\n  {Colors.BOLD}Reports saved to: {OUTPUT_DIR}/{Colors.END}")
    pause(1.0)


def demo_conclusion():
    """Display conclusion and next steps"""
    print_header("DEMONSTRATION COMPLETE")
    
    print(f"\n{Colors.BOLD}Thank you for watching the STM Routing Simulator demo!{Colors.END}\n")
    
    print("Key Takeaways:")
    print("  ✓ Simulated 8-hour shift with realistic routing behavior")
    print("  ✓ Handled requests across 5 priority levels")
    print("  ✓ Properly redistributed work from absent agent")
    print("  ✓ Balanced workload across active agents")
    print("  ✓ Followed production filtering and routing logic\n")
    
    print(f"{Colors.BOLD}What's Next?{Colors.END}")
    print("  • Review detailed reports in demo/output/")
    print("  • Try modifying the scenario YAML")
    print("  • Run custom scenarios with your own data")
    print("  • Use for capacity planning and what-if analysis\n")
    
    print(f"{Colors.BOLD}Questions?{Colors.END}")
    print("  • Documentation: See README.md")
    print("  • Support: Contact the development team")
    print("  • Feedback: Submit via GitHub issues\n")


# ============================================================================
# MAIN DEMO FLOW
# ============================================================================

def main():
    """Run the complete demo"""
    try:
        # Introduction
        demo_introduction()
        
        # Step 1: Load scenario
        scenario = load_and_validate_scenario()
        
        # Step 2: Display team
        display_team_roster(scenario)
        
        # Step 3: Display requests
        display_request_summary(scenario)
        
        # Step 4: Run simulation
        result = run_simulation_with_progress(scenario)
        
        # Step 5: Timeline
        display_shift_timeline(result)
        
        # Step 6: Agent performance
        display_agent_performance(result)
        
        # Step 7: Priority breakdown
        display_priority_breakdown(result)
        
        # Step 8: Final summary
        display_final_summary(result)
        
        # Step 9: Save reports
        save_detailed_report(result)
        
        # Conclusion
        demo_conclusion()
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Demo interrupted by user.{Colors.END}")
        return 1
    except Exception as e:
        print(f"\n\n{Colors.RED}Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())