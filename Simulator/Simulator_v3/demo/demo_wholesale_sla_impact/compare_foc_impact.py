#!/usr/bin/env python3
"""
STM Routing Simulator v3.0 - Wholesale SLA Priority Analysis Tool (Quick Analysis)

**IMPORTANT: This is a QUICK PRIORITY ANALYSIS tool, NOT a full simulation.**

This tool provides fast "what-if" analysis of how changing FOC targets and SLA
assignments affect request priority scores and rankings WITHOUT running a 
discrete event simulation.

═══════════════════════════════════════════════════════════════════════════════
WHAT THIS TOOL DOES:
═══════════════════════════════════════════════════════════════════════════════
✓ Calculates priority scores at simulation start (t=0)
✓ Ranks requests by priority
✓ Shows impact on each customer's average priority and ranking
✓ Analyzes SLA vs. non-SLA customer differences
✓ Provides quick comparative analysis
✓ Runs in seconds

═══════════════════════════════════════════════════════════════════════════════
WHAT THIS TOOL DOES NOT DO:
═══════════════════════════════════════════════════════════════════════════════
✗ Run discrete event simulation
✗ Assign requests to agents
✗ Simulate time progression
✗ Calculate actual wait times, handle times, or throughput
✗ Model agent availability or workload

═══════════════════════════════════════════════════════════════════════════════
SCENARIO:
═══════════════════════════════════════════════════════════════════════════════
Baseline:  13 customers, all foc_target=8.0 days, has_sla=False
Proposed:  7 SLA customers (foc_target=1.0 day, has_sla=True)
           6 non-SLA customers (foc_target=8.0 days, has_sla=False)

Total: 500 requests (200 SLA, 300 non-SLA)

Usage:
    # Use default scenarios (even distribution)
    python compare_foc_impact.py
    
    # Compare even distribution scenarios
    python compare_foc_impact.py --baseline demo/demo_wholesale_sla_impact/scenarios/baseline_even_scenario.yaml --proposed demo/demo_wholesale_sla_impact/scenarios/proposed_even_scenario.yaml
    
    # Compare dedicated agent scenarios
    python compare_foc_impact.py --baseline demo/demo_wholesale_sla_impact/scenarios/baseline_dedicated_scenario.yaml --proposed demo/demo_wholesale_sla_impact/scenarios/proposed_dedicated_scenario.yaml
"""

from collections import defaultdict
import sys
import os
import json
import time
import statistics
import yaml
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Tuple, List

# Add parent directories to path
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# ============================================================================
# DEMO CONFIGURATION
# ============================================================================

# Default scenario file paths (can be overridden via command-line)
BASELINE_SCENARIO = "demo/demo_wholesale_sla_impact/scenarios/baseline_even_scenario.yaml"
PROPOSED_SCENARIO = "demo/demo_wholesale_sla_impact/scenarios/proposed_even_scenario.yaml"

# Output configuration
OUTPUT_DIR = "demo/demo_wholesale_sla_impact/output"
COMPARISON_OUTPUT_FILENAME = "comparison_results_quick.json"

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


def print_metric_row(label: str, baseline: str, proposed: str, change: str):
    """Print a formatted metric comparison row"""
    print(f"{label:<30}  {baseline:>10}  {proposed:>10}  {change:>12}")


def print_progress(message: str):
    """Print a progress message"""
    print(f"  {message}", end='', flush=True)
    pause(0.3)
    print(f" {Colors.GREEN}✓{Colors.END}")


def print_warning_box():
    """Print a warning box about tool limitations"""
    print(f"\n{Colors.YELLOW}{'╔' + '═' * 78 + '╗'}{Colors.END}")
    print(f"{Colors.YELLOW}║{Colors.END} {Colors.BOLD}⚠️  QUICK ANALYSIS MODE{Colors.END}" + " " * 54 + f"{Colors.YELLOW}║{Colors.END}")
    print(f"{Colors.YELLOW}║{Colors.END}" + " " * 78 + f"{Colors.YELLOW}║{Colors.END}")
    print(f"{Colors.YELLOW}║{Colors.END}  This tool shows priority score impact WITHOUT running full simulation.    {Colors.YELLOW}║{Colors.END}")
    print(f"{Colors.YELLOW}║{Colors.END}  For complete metrics (assignments, timing, throughput), use:               {Colors.YELLOW}║{Colors.END}")
    print(f"{Colors.YELLOW}║{Colors.END}    → python run_full_simulation.py                                          {Colors.YELLOW}║{Colors.END}")
    print(f"{Colors.YELLOW}{'╚' + '═' * 78 + '╝'}{Colors.END}\n")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

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


def format_percentage(value: float) -> str:
    """Format a decimal as percentage"""
    return f"{value * 100:.1f}%"


def format_change(baseline: float, proposed: float, as_percentage: bool = False) -> str:
    """Format the change between two values"""
    if as_percentage:
        change = (proposed - baseline) * 100
        return f"{change:+.1f}pp"
    else:
        if baseline == 0:
            return "N/A"
        change_pct = ((proposed - baseline) / baseline * 100)
        return f"{change_pct:+.1f}%"


# ============================================================================
# DATA MODELS
# ============================================================================

class SimplifiedRequest:
    """
    Simplified Request class for quick priority analysis.
    """
    
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
        return (current_time - self.order_date).total_seconds() / (24.0 * 60.0 * 60)
    
    def is_foc_compliant(self, current_time: datetime) -> bool:
        """Check if request is within FOC target"""
        return self.get_age_days(current_time) <= self.foc_target


class ScenarioAnalyzer:
    """Analyzes scenarios for quick priority comparison."""
    
    def __init__(self, scenario_path: str):
        self.scenario_path = scenario_path
        self.scenario_data = self._load_scenario()
        self.requests = []
        self.start_time = None
        self._setup()
    
    def _load_scenario(self) -> Dict:
        """Load scenario from YAML file"""
        with open(self.scenario_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup(self):
        """Set up scenario data and create request objects"""
        start_time_str = self.scenario_data['start_time']
        self.start_time = datetime.fromisoformat(start_time_str)
        
        for req_data in self.scenario_data['requests']:
            req = SimplifiedRequest(req_data)
            offset_hours = req.order_date_offset_hours
            req.order_date = self.start_time + timedelta(hours=offset_hours)
            self.requests.append(req)
    
    def analyze_at_time(self, hours_after_start: float = 0.0) -> Dict[str, Any]:
        """Analyze scenario at a specific time"""
        current_time = self.start_time + timedelta(hours=hours_after_start)
        
        # Calculate priority scores for all requests
        request_data = []
        for req in self.requests:
            score = req.calculate_priority_score(current_time)
            age_days = req.get_age_days(current_time)
            is_compliant = req.is_foc_compliant(current_time)
            
            request_data.append({
                'request_id': req.request_id,
                'client_id': req.golden_customer_id,
                'skill_id': req.skill_id,
                'foc_target': req.foc_target,
                'has_sla': req.has_sla,
                'age_days': age_days,
                'priority_score': score,
                'is_foc_compliant': is_compliant,
                'rank': None
            })
        
        # Sort by priority score (descending)
        request_data.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Assign ranks
        for i, req in enumerate(request_data):
            req['rank'] = i + 1
        
        # Calculate metrics
        client_metrics = self._calculate_client_metrics(request_data)
        overall_metrics = self._calculate_overall_metrics(request_data)
        sla_metrics = self._calculate_sla_metrics(request_data)
        
        return {
            'analysis_time': current_time.isoformat(),
            'hours_after_start': hours_after_start,
            'overall_metrics': overall_metrics,
            'client_metrics': client_metrics,
            'sla_metrics': sla_metrics,
            'request_details': request_data
        }
    
    def _calculate_client_metrics(self, request_data: List[Dict]) -> Dict:
        """Calculate per-client metrics"""
        client_metrics = defaultdict(lambda: {
            'total_requests': 0,
            'foc_compliant': 0,
            'average_priority_score': 0.0,
            'average_rank': 0.0,
            'foc_target': None,
            'has_sla': False,
            'average_age_days': 0.0
        })
        
        for req in request_data:
            client_id = req['client_id']
            client_metrics[client_id]['total_requests'] += 1
            if req['is_foc_compliant']:
                client_metrics[client_id]['foc_compliant'] += 1
            client_metrics[client_id]['foc_target'] = req['foc_target']
            client_metrics[client_id]['has_sla'] = req['has_sla']
            client_metrics[client_id]['average_priority_score'] += req['priority_score']
            client_metrics[client_id]['average_rank'] += req['rank']
            client_metrics[client_id]['average_age_days'] += req['age_days']
        
        for client_id in client_metrics:
            count = client_metrics[client_id]['total_requests']
            if count > 0:
                client_metrics[client_id]['average_priority_score'] /= count
                client_metrics[client_id]['average_rank'] /= count
                client_metrics[client_id]['average_age_days'] /= count
                client_metrics[client_id]['foc_compliance_rate'] = (
                    client_metrics[client_id]['foc_compliant'] / count
                )
        
        return dict(client_metrics)
    
    def _calculate_overall_metrics(self, request_data: List[Dict]) -> Dict:
        """Calculate system-wide metrics"""
        total_requests = len(request_data)
        foc_compliant = sum(1 for req in request_data if req['is_foc_compliant'])
        
        return {
            'total_requests': total_requests,
            'foc_compliant': foc_compliant,
            'foc_compliance_rate': foc_compliant / total_requests if total_requests > 0 else 0,
            'average_priority_score': statistics.mean([req['priority_score'] for req in request_data]),
            'median_priority_score': statistics.median([req['priority_score'] for req in request_data]),
            'average_age_days': statistics.mean([req['age_days'] for req in request_data]),
        }
    
    def _calculate_sla_metrics(self, request_data: List[Dict]) -> Dict:
        """Calculate SLA vs non-SLA metrics"""
        sla_requests = [req for req in request_data if req['has_sla']]
        non_sla_requests = [req for req in request_data if not req['has_sla']]
        
        def calc_stats(requests):
            if not requests:
                return {'count': 0}
            return {
                'count': len(requests),
                'avg_priority': statistics.mean([r['priority_score'] for r in requests]),
                'avg_rank': statistics.mean([r['rank'] for r in requests]),
                'avg_age_days': statistics.mean([r['age_days'] for r in requests]),
            }
        
        return {
            'sla_customers': calc_stats(sla_requests),
            'non_sla_customers': calc_stats(non_sla_requests)
        }


# ============================================================================
# DEMO ORCHESTRATION
# ============================================================================

def demo_introduction(baseline_path: str, proposed_path: str):
    """Display demo introduction"""
    clear_screen()
    print_header("STM ROUTING SIMULATOR v3.0")
    print_header("WHOLESALE SLA QUICK PRIORITY ANALYSIS")
    
    print(f"\n{Colors.BOLD}Welcome to the Wholesale SLA Quick Priority Analysis!{Colors.END}\n")
    
    print("This tool provides QUICK metrics by calculating priority scores at time t=0.")
    print("It does NOT run full discrete event simulation with agent assignments.\n")
    
    print(f"{Colors.BOLD}Analysis Type:{Colors.END}")
    print("  • Calculates priority scores for all requests")
    print("  • Ranks requests by priority (queue positions)")
    print("  • Predicts position changes between scenarios")
    print("  • Provides quick insights without full simulation\n")
    
    print(f"{Colors.BOLD}Scenarios Being Compared:{Colors.END}")
    print(f"  Baseline: {baseline_path}")
    print(f"  Proposed: {proposed_path}\n")
    
    print(f"{Colors.BOLD}What You'll Learn:{Colors.END}")
    print("  • Predicted queue position changes")
    print("  • Priority score distributions")
    print("  • FOC compliance rates (at t=0)")
    print("  • Customer tier impact preview\n")
    
    print(f"{Colors.YELLOW}⚡ Note: This is a QUICK analysis (< 5 seconds).{Colors.END}")
    print(f"{Colors.YELLOW}   For actual wait times, use run_full_simulation.py{Colors.END}\n")
    
    input(f"{Colors.BOLD}Press Enter to begin analysis...{Colors.END}")


def load_scenarios():
    """Load both baseline and proposed scenarios"""
    print_section("STEP 1: Loading Scenarios")
    
    print_progress("Loading baseline scenario")
    baseline = ScenarioAnalyzer(BASELINE_SCENARIO)
    print_info("Baseline Loaded", f"{len(baseline.requests)} requests from {len(baseline.scenario_data['agents'])} agents")
    
    pause(0.5)
    
    print_progress("Loading proposed scenario")
    proposed = ScenarioAnalyzer(PROPOSED_SCENARIO)
    print_info("Proposed Loaded", f"{len(proposed.requests)} requests from {len(proposed.scenario_data['agents'])} agents")
    
    pause(1.0)
    
    return baseline, proposed


def display_scenario_overview(baseline: ScenarioAnalyzer, proposed: ScenarioAnalyzer):
    """Display overview of both scenarios"""
    print_section("STEP 2: Scenario Overview")
    
    print(f"\n{Colors.BOLD}Configuration:{Colors.END}")
    print(f"  Start Time: {baseline.start_time.strftime('%Y-%m-%d %I:%M %p %Z')}")
    print(f"  Total Requests: {len(baseline.requests)}")
    print(f"  Agents: {len(baseline.scenario_data['agents'])}")
    print("  Customers: 13 (CUST_A through CUST_M)")
    
    # Count customers by category
    sla_customers = [c for c in baseline.scenario_data['requests'] if 'CUST_A' <= c['golden_customer_id'] <= 'CUST_G']
    print(f"  SLA Customers (A-G): 7 customers, {len(sla_customers)} requests")
    print(f"  Non-SLA Customers (H-M): 6 customers, {len(baseline.requests) - len(sla_customers)} requests")
    
    print(f"\n{Colors.BOLD}FOC Target Configuration:{Colors.END}")
    print("\n  Baseline Scenario:")
    print("    • All 13 customers: foc_target = 8.0 days, has_sla = False")
    
    print("\n  Proposed Scenario:")
    print(f"    • CUST_A-G (7 customers): foc_target = 1.0 day, has_sla = True {Colors.YELLOW}(87.5% reduction!){Colors.END}")
    print("    • CUST_H-M (6 customers): foc_target = 8.0 days, has_sla = False (unchanged)")
    
    pause(2.0)


def run_analysis(baseline: ScenarioAnalyzer, proposed: ScenarioAnalyzer) -> Tuple[Dict, Dict]:
    """Run the priority analysis"""
    print_section("STEP 3: Running Quick Analysis")
    
    print(f"\n{Colors.BOLD}Calculating priority scores at t=0...{Colors.END}\n")
    
    print_progress("Calculating baseline priority scores")
    baseline_analysis = baseline.analyze_at_time(0.0)
    
    print_progress("Calculating proposed priority scores")
    proposed_analysis = proposed.analyze_at_time(0.0)
    
    print_progress("Computing comparative metrics")
    
    pause(1.0)
    
    return baseline_analysis, proposed_analysis


def display_overall_metrics(baseline_analysis: Dict, proposed_analysis: Dict):
    """Display overall metrics comparison"""
    print_section("STEP 4: Overall Metrics Comparison")
    
    print(f"\n{Colors.BOLD}📊 SYSTEM-WIDE PRIORITY METRICS{Colors.END}\n")
    print(f"{'Metric':<30}  {'Baseline':>10}  {'Proposed':>10}  {'Change':>12}")
    print("-" * 70)
    
    baseline_overall = baseline_analysis['overall_metrics']
    proposed_overall = proposed_analysis['overall_metrics']
    
    metrics_to_compare = [
        ('Total Requests', 'total_requests', ''),
        ('FOC Compliance Rate', 'foc_compliance_rate', '%'),
        ('Avg Priority Score', 'average_priority_score', ''),
        ('Median Priority Score', 'median_priority_score', ''),
        ('Avg Age (days)', 'average_age_days', 'd'),
    ]
    
    for label, key, unit in metrics_to_compare:
        baseline_val = baseline_overall[key]
        proposed_val = proposed_overall[key]
        
        if unit == '%':
            baseline_str = format_percentage(baseline_val)
            proposed_str = format_percentage(proposed_val)
            change_str = format_change(baseline_val, proposed_val, as_percentage=True)
        elif unit == '':
            baseline_str = f"{baseline_val:.3f}" if isinstance(baseline_val, float) else str(baseline_val)
            proposed_str = f"{proposed_val:.3f}" if isinstance(proposed_val, float) else str(proposed_val)
            if isinstance(baseline_val, (int, float)) and baseline_val != 0:
                change_str = format_change(baseline_val, proposed_val)
            else:
                change_str = "—"
        else:
            baseline_str = f"{baseline_val:.3f}{unit}"
            proposed_str = f"{proposed_val:.3f}{unit}"
            change_str = format_change(baseline_val, proposed_val)
        
        print_metric_row(label, baseline_str, proposed_str, change_str)
    
    pause(2.0)


def display_sla_comparison(baseline_analysis: Dict, proposed_analysis: Dict):
    """Display SLA vs non-SLA comparison"""
    print_section("STEP 5: SLA vs Non-SLA Analysis")
    
    proposed_sla = proposed_analysis['sla_metrics']
    
    print(f"\n{Colors.BOLD}📋 PROPOSED SCENARIO - SLA IMPACT{Colors.END}\n")
    print(f"{'Category':<20} {'Count':>8} {'Avg Priority':>15} {'Avg Rank':>12} {'Avg Age (d)':>12}")
    print("-" * 70)
    
    if proposed_sla['sla_customers']['count'] > 0:
        sla = proposed_sla['sla_customers']
        print(f"{Colors.GREEN}SLA Customers{Colors.END}       {sla['count']:>8}      {sla['avg_priority']:>12.3f}    {sla['avg_rank']:>10.1f}    {sla['avg_age_days']:>10.1f}")
    
    if proposed_sla['non_sla_customers']['count'] > 0:
        non_sla = proposed_sla['non_sla_customers']
        print(f"{Colors.YELLOW}Non-SLA Customers{Colors.END}   {non_sla['count']:>8}      {non_sla['avg_priority']:>12.3f}    {non_sla['avg_rank']:>10.1f}    {non_sla['avg_age_days']:>10.1f}")
    
    # Calculate difference
    if proposed_sla['sla_customers']['count'] > 0 and proposed_sla['non_sla_customers']['count'] > 0:
        priority_ratio = proposed_sla['sla_customers']['avg_priority'] / proposed_sla['non_sla_customers']['avg_priority']
        rank_diff = proposed_sla['non_sla_customers']['avg_rank'] - proposed_sla['sla_customers']['avg_rank']
        
        print(f"\n{Colors.BOLD}Key Differences:{Colors.END}")
        print(f"  • SLA customers have {Colors.GREEN}{priority_ratio:.1f}x higher{Colors.END} average priority")
        print(f"  • SLA customers rank {Colors.GREEN}{rank_diff:.0f} positions higher{Colors.END} on average")
    
    pause(2.0)


def display_customer_comparison(baseline_analysis: Dict, proposed_analysis: Dict):
    """Display customer-level comparison"""
    print_section("STEP 6: Customer-Level Analysis")
    
    print(f"\n{Colors.BOLD}📋 PRIORITY IMPACT BY CUSTOMER{Colors.END}\n")
    print(f"{'Customer':<10} {'SLA':>5} {'FOC Tgt':>9}   {'Avg Priority':>16}   {'Avg Rank':>11}")
    print(f"{'':10} {'':5} {'B→P':>9}   {'Base':>6} {'Prop':>6} {'Δ%':>6}   {'Base':>4} {'Prop':>4}")
    print("-" * 78)
    
    all_customers = sorted(set(
        list(baseline_analysis['client_metrics'].keys()) + 
        list(proposed_analysis['client_metrics'].keys())
    ))
    
    for customer_id in all_customers:
        baseline_client = baseline_analysis['client_metrics'].get(customer_id, {})
        proposed_client = proposed_analysis['client_metrics'].get(customer_id, {})
        
        if not baseline_client or not proposed_client:
            continue
        
        has_sla = "Yes" if proposed_client.get('has_sla', False) else "No"
        baseline_foc = baseline_client['foc_target']
        proposed_foc = proposed_client['foc_target']
        foc_str = f"{baseline_foc:.1f}→{proposed_foc:.1f}"
        
        baseline_score = baseline_client['average_priority_score']
        proposed_score = proposed_client['average_priority_score']
        score_change = ((proposed_score - baseline_score) / baseline_score * 100) if baseline_score != 0 else 0
        
        baseline_rank = baseline_client['average_rank']
        proposed_rank = proposed_client['average_rank']
        
        # Color code SLA customers
        customer_color = Colors.GREEN if has_sla == "Yes" else Colors.END
        
        print(f"{customer_color}{customer_id:<10}{Colors.END} {has_sla:>5} {foc_str:>9}   "
              f"{baseline_score:>6.3f} {proposed_score:>6.3f} {score_change:>6.0f}   "
              f"{baseline_rank:>4.0f} {proposed_rank:>4.0f}")
    
    print(f"\n{Colors.GREEN}Green{Colors.END} = SLA customers")
    
    pause(2.0)


def display_top_requests(baseline_analysis: Dict, proposed_analysis: Dict):
    """Display top 30 requests in each scenario"""
    print_section("STEP 7: Top 30 Request Rankings")
    
    print(f"\n{Colors.BOLD}BASELINE SCENARIO (Top 30){Colors.END}")
    print(f"{'Rank':>4}  {'Request':<16} {'Customer':<10} {'FOC':>5}  {'Priority':>8}")
    print("-" * 60)
    for req in baseline_analysis['request_details'][:30]:
        print(f"{req['rank']:>4}  {req['request_id']:<16} {req['client_id']:<10} "
              f"{req['foc_target']:>4.1f}d  {req['priority_score']:>8.3f}")
    
    print(f"\n{Colors.BOLD}PROPOSED SCENARIO (Top 30){Colors.END}")
    print(f"{'Rank':>4}  {'Request':<16} {'Customer':<10} {'FOC':>5}  {'Priority':>8}")
    print("-" * 60)
    
    sla_count_in_top30 = 0
    for req in proposed_analysis['request_details'][:30]:
        marker = f" {Colors.GREEN}⭐{Colors.END}" if req['has_sla'] else ""
        if req['has_sla']:
            sla_count_in_top30 += 1
        print(f"{req['rank']:>4}  {req['request_id']:<16} {req['client_id']:<10} "
              f"{req['foc_target']:>4.1f}d  {req['priority_score']:>8.3f}{marker}")
    
    print(f"\n{Colors.GREEN}⭐{Colors.END} = SLA customer request (foc_target=1.0 day)")
    print(f"\n{Colors.BOLD}Top 30 Composition:{Colors.END} {sla_count_in_top30}/30 are SLA requests ({sla_count_in_top30/30*100:.0f}%)")
    
    pause(2.0)


def display_rank_changes(baseline_analysis: Dict, proposed_analysis: Dict):
    """Display detailed rank change analysis for SLA vs non-SLA customers"""
    print_section("STEP 8: Queue Position Changes Analysis")
    
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
        rank_change = baseline_rank - proposed_rank  # Positive = improvement (moved up)
        
        if req['has_sla']:
            sla_rank_changes.append({
                'request_id': req_id,
                'customer': req['client_id'],
                'baseline_rank': baseline_rank,
                'proposed_rank': proposed_rank,
                'change': rank_change
            })
        else:
            non_sla_rank_changes.append({
                'request_id': req_id,
                'customer': req['client_id'],
                'baseline_rank': baseline_rank,
                'proposed_rank': proposed_rank,
                'change': rank_change
            })
    
    # Calculate statistics
    sla_changes = [r['change'] for r in sla_rank_changes]
    non_sla_changes = [r['change'] for r in non_sla_rank_changes]
    
    print(f"\n{Colors.BOLD}📈 QUEUE POSITION ANALYSIS{Colors.END}\n")
    
    print(f"{Colors.GREEN}SLA Customers (CUST_A-G) - Position Improvement:{Colors.END}")
    print(f"  Total SLA Requests: {len(sla_rank_changes)}")
    print(f"  Average Position Improvement: {Colors.GREEN}{statistics.mean(sla_changes):+.0f} positions{Colors.END}")
    print(f"  Median Position Improvement: {statistics.median(sla_changes):+.0f} positions")
    print(f"  Best Improvement: {max(sla_changes):+.0f} positions")
    print(f"  Worst Improvement: {min(sla_changes):+.0f} positions")
    print(f"  Standard Deviation: {statistics.stdev(sla_changes):.1f} positions")
    
    # Percentile analysis for SLA
    improved_to_top_100 = sum(1 for r in sla_rank_changes if r['proposed_rank'] <= 100)
    improved_to_top_200 = sum(1 for r in sla_rank_changes if r['proposed_rank'] <= 200)
    improved_to_top_300 = sum(1 for r in sla_rank_changes if r['proposed_rank'] <= 300)
    
    print(f"\n  {Colors.BOLD}Position Distribution:{Colors.END}")
    print(f"    Moved to Top 100: {improved_to_top_100}/{len(sla_rank_changes)} ({improved_to_top_100/len(sla_rank_changes)*100:.1f}%)")
    print(f"    Moved to Top 200: {improved_to_top_200}/{len(sla_rank_changes)} ({improved_to_top_200/len(sla_rank_changes)*100:.1f}%)")
    print(f"    Moved to Top 300: {improved_to_top_300}/{len(sla_rank_changes)} ({improved_to_top_300/len(sla_rank_changes)*100:.1f}%)")
    
    print(f"\n{Colors.YELLOW}Non-SLA Customers (CUST_H-M) - Position Deterioration:{Colors.END}")
    print(f"  Total Non-SLA Requests: {len(non_sla_rank_changes)}")
    print(f"  Average Position Deterioration: {Colors.RED}{statistics.mean(non_sla_changes):+.0f} positions{Colors.END}")
    print(f"  Median Position Deterioration: {statistics.median(non_sla_changes):+.0f} positions")
    print(f"  Best Case: {max(non_sla_changes):+.0f} positions")
    print(f"  Worst Case: {min(non_sla_changes):+.0f} positions")
    print(f"  Standard Deviation: {statistics.stdev(non_sla_changes):.1f} positions")
    
    # Percentile analysis for non-SLA
    dropped_from_top_100 = sum(1 for r in non_sla_rank_changes if r['baseline_rank'] <= 100 and r['proposed_rank'] > 100)
    dropped_from_top_200 = sum(1 for r in non_sla_rank_changes if r['baseline_rank'] <= 200 and r['proposed_rank'] > 200)
    dropped_from_top_300 = sum(1 for r in non_sla_rank_changes if r['baseline_rank'] <= 300 and r['proposed_rank'] > 300)
    
    print(f"\n  {Colors.BOLD}Position Distribution:{Colors.END}")
    print(f"    Dropped from Top 100: {dropped_from_top_100} requests")
    print(f"    Dropped from Top 200: {dropped_from_top_200} requests")
    print(f"    Dropped from Top 300: {dropped_from_top_300} requests")
    
    # Show example requests with biggest changes
    print(f"\n{Colors.BOLD}Examples of Biggest Changes:{Colors.END}\n")
    
    # Top 5 SLA improvements
    top_sla_improvements = sorted(sla_rank_changes, key=lambda x: x['change'], reverse=True)[:5]
    print(f"{Colors.GREEN}Top 5 SLA Position Improvements:{Colors.END}")
    print(f"  {'Request':<18} {'Customer':<10} {'Baseline':<10} {'Proposed':<10} {'Change':<10}")
    print(f"  {'-'*60}")
    for req in top_sla_improvements:
        print(f"  {req['request_id']:<18} {req['customer']:<10} #{req['baseline_rank']:<9} #{req['proposed_rank']:<9} {Colors.GREEN}{req['change']:+d}{Colors.END}")
    
    # Top 5 non-SLA deteriorations
    top_non_sla_deteriorations = sorted(non_sla_rank_changes, key=lambda x: x['change'])[:5]
    print(f"\n{Colors.YELLOW}Top 5 Non-SLA Position Deteriorations:{Colors.END}")
    print(f"  {'Request':<18} {'Customer':<10} {'Baseline':<10} {'Proposed':<10} {'Change':<10}")
    print(f"  {'-'*60}")
    for req in top_non_sla_deteriorations:
        print(f"  {req['request_id']:<18} {req['customer']:<10} #{req['baseline_rank']:<9} #{req['proposed_rank']:<9} {Colors.RED}{req['change']:+d}{Colors.END}")
    
    # Calculate the gap
    avg_gap = statistics.mean(sla_changes) - statistics.mean(non_sla_changes)
    
    print(f"\n{Colors.BOLD}Overall Impact:{Colors.END}")
    print(f"  Average position gap between SLA and non-SLA: {Colors.RED}{abs(avg_gap):.0f} positions{Colors.END}")
    print(f"  SLA customers improve by {abs(statistics.mean(sla_changes)):.0f} positions on average")
    print(f"  Non-SLA customers drop by {abs(statistics.mean(non_sla_changes)):.0f} positions on average")
    print(f"  Net effect: {Colors.BOLD}{abs(avg_gap):.0f}-position advantage{Colors.END} for SLA customers")
    
    pause(3.0)
    
    return {
        'sla_avg_improvement': statistics.mean(sla_changes),
        'non_sla_avg_deterioration': statistics.mean(non_sla_changes),
        'position_gap': avg_gap,
        'sla_to_top_200': improved_to_top_200
    }


def display_key_insights(baseline_analysis: Dict, proposed_analysis: Dict, rank_changes: Dict):
    """Display key insights from the analysis"""
    print_section("STEP 9: Key Insights")
    
    baseline_overall = baseline_analysis['overall_metrics']
    proposed_overall = proposed_analysis['overall_metrics']
    
    proposed_sla = proposed_analysis['sla_metrics']
    
    overall_score_change = ((proposed_overall['average_priority_score'] - 
                            baseline_overall['average_priority_score']) / 
                           baseline_overall['average_priority_score'] * 100)
    
    print(f"\n{Colors.BOLD}Impact of SLA Assignment (8d → 1d FOC for 7 customers):{Colors.END}\n")
    
    print(f"{Colors.BOLD}1. Dramatic Priority Shift{Colors.END}")
    if proposed_sla['sla_customers']['count'] > 0:
        sla_avg = proposed_sla['sla_customers']['avg_priority']
        print(f"   • SLA customer average priority: {Colors.GREEN}{sla_avg:.2f}{Colors.END}")
        print(f"   • This represents an ~{Colors.RED}700% (8x) increase{Colors.END} from baseline")
        print("   • FOC reduction: 8 days → 1 day (87.5%)")
    
    print(f"\n{Colors.BOLD}2. Queue Position Changes{Colors.END}")
    print(f"   • SLA customers improve by {Colors.GREEN}{rank_changes['sla_avg_improvement']:+.0f} positions{Colors.END} on average")
    print(f"   • Non-SLA customers drop by {Colors.RED}{rank_changes['non_sla_avg_deterioration']:+.0f} positions{Colors.END} on average")
    print(f"   • Position gap: {Colors.BOLD}{abs(rank_changes['position_gap']):.0f} positions{Colors.END}")
    print(f"   • {rank_changes['sla_to_top_200']}/200 SLA requests moved to top 200 positions")
    
    print(f"\n{Colors.BOLD}3. Queue Domination{Colors.END}")
    top30_sla = sum(1 for req in proposed_analysis['request_details'][:30] if req['has_sla'])
    top50_sla = sum(1 for req in proposed_analysis['request_details'][:50] if req['has_sla'])
    top100_sla = sum(1 for req in proposed_analysis['request_details'][:100] if req['has_sla'])
    
    print(f"   • Top 30 positions: {Colors.GREEN}{top30_sla}/30 ({top30_sla/30*100:.0f}%){Colors.END} are SLA requests")
    print(f"   • Top 50 positions: {Colors.GREEN}{top50_sla}/50 ({top50_sla/50*100:.0f}%){Colors.END} are SLA requests")
    print(f"   • Top 100 positions: {Colors.GREEN}{top100_sla}/100 ({top100_sla/100*100:.0f}%){Colors.END} are SLA requests")
    
    print(f"\n{Colors.BOLD}4. Impact on Non-SLA Customers{Colors.END}")
    if proposed_sla['non_sla_customers']['count'] > 0:
        non_sla_avg_rank = proposed_sla['non_sla_customers']['avg_rank']
        print(f"   • Non-SLA customers now average rank {Colors.YELLOW}{non_sla_avg_rank:.0f}{Colors.END}")
        print("   • They are significantly deprioritized relative to SLA customers")
        print("   • Will experience much longer wait times")
        print(f"   • Average deterioration: {Colors.RED}{abs(rank_changes['non_sla_avg_deterioration']):.0f} positions{Colors.END}")
    
    print(f"\n{Colors.BOLD}5. System-Wide Effects{Colors.END}")
    print(f"   • Overall average priority score changed by {overall_score_change:+.1f}%")
    print("   • Priority distribution heavily skewed toward SLA customers")
    print("   • Creates a very strong two-tier service system")
    print(f"   • Position advantage for SLA: {Colors.BOLD}{abs(rank_changes['position_gap']):.0f} positions{Colors.END}")
    
    print(f"\n{Colors.BOLD}6. Business Implications{Colors.END}")
    print(f"   • {Colors.GREEN}SLA customers get extremely fast service{Colors.END}")
    print(f"   • {Colors.YELLOW}Non-SLA customers may face unacceptable delays{Colors.END}")
    print(f"   • Consider: Is {abs(rank_changes['position_gap']):.0f}-position gap appropriate?")
    print("   • Alternative: Smaller FOC gap (e.g., 3 days vs 8 days)")
    
    print(f"\n{Colors.YELLOW}⚠️  Note: These are priority scores only. For actual assignment times,")
    print(f"   run the full simulation with run_full_simulation.py{Colors.END}")
    
    pause(3.0)


def save_results(baseline_analysis: Dict, proposed_analysis: Dict, rank_changes: Dict):
    """Save detailed results to JSON file"""
    print_section("STEP 10: Saving Results")
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    print_progress("Creating output directory")
    
    baseline_overall = baseline_analysis['overall_metrics']
    proposed_overall = proposed_analysis['overall_metrics']
    
    results = {
        'metadata': {
            'analysis_type': 'quick_priority_analysis',
            'demo_version': VERSION,
            'analysis_date': datetime.now(timezone.utc).isoformat(),
            'baseline_scenario': BASELINE_SCENARIO,
            'proposed_scenario': PROPOSED_SCENARIO,
            'note': 'Wholesale SLA impact - quick priority analysis (not full simulation)'
        },
        'baseline': baseline_analysis,
        'proposed': proposed_analysis,
        'comparison': {
            'overall_metrics_change': {
                key: {
                    'baseline': baseline_overall[key],
                    'proposed': proposed_overall[key],
                    'change': proposed_overall[key] - baseline_overall[key],
                    'change_percent': format_change(baseline_overall[key], proposed_overall[key])
                }
                for key in baseline_overall.keys()
            },
            'rank_changes': {
                'sla_avg_improvement': rank_changes['sla_avg_improvement'],
                'non_sla_avg_deterioration': rank_changes['non_sla_avg_deterioration'],
                'position_gap': rank_changes['position_gap'],
                'sla_to_top_200': rank_changes['sla_to_top_200']
            }
        }
    }
    
    output_path = Path(OUTPUT_DIR) / COMPARISON_OUTPUT_FILENAME
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print_progress(f"Saved results to {output_path}")
    
    print(f"\n  {Colors.GREEN}✓{Colors.END} Results file: {Colors.CYAN}{output_path}{Colors.END}")
    print(f"  {Colors.GREEN}✓{Colors.END} Format: JSON with full analysis data")
    print(f"  {Colors.GREEN}✓{Colors.END} Size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"  {Colors.GREEN}✓{Colors.END} Includes: Priority scores, rankings, and position changes")
    
    pause(1.0)


def demo_conclusion(rank_changes: Dict):
    """Display conclusion and next steps"""
    print_section("QUICK ANALYSIS COMPLETE")
    
    print(f"\n{Colors.BOLD}Summary of Findings:{Colors.END}\n")
    print(f"  {Colors.RED}⚠{Colors.END} Priority Score Impact: {Colors.BOLD}~700% (8x){Colors.END} for SLA customers")
    print(f"  {Colors.GREEN}✓{Colors.END} SLA customers improve by {Colors.BOLD}{abs(rank_changes['sla_avg_improvement']):.0f} positions{Colors.END} on average")
    print(f"  {Colors.YELLOW}⚠{Colors.END} Non-SLA customers drop by {Colors.BOLD}{abs(rank_changes['non_sla_avg_deterioration']):.0f} positions{Colors.END} on average")
    print(f"  {Colors.BLUE}ℹ{Colors.END} Queue position gap: {Colors.BOLD}{abs(rank_changes['position_gap']):.0f} positions{Colors.END}")
    print(f"  {Colors.GREEN}✓{Colors.END} {rank_changes['sla_to_top_200']}/200 SLA requests in top 200 positions")
    
    print(f"\n{Colors.BOLD}Critical Considerations:{Colors.END}")
    print("  ⚠️  87.5% FOC reduction (8d → 1d) is EXTREMELY aggressive")
    print(f"  ⚠️  Non-SLA customers drop ~{abs(rank_changes['non_sla_avg_deterioration']):.0f} positions on average")
    print("  ⚠️  Consider smaller gap: 3-4 days for SLA vs 8 days for non-SLA")
    
    print(f"\n{Colors.BOLD}For Complete Simulation Results:{Colors.END}")
    print(f"  Run: {Colors.CYAN}python run_full_simulation.py{Colors.END}")
    print("  This will:")
    print("    • Run full discrete event simulation")
    print("    • Show actual agent assignments")
    print("    • Calculate real wait times and throughput")
    print("    • Provide comprehensive metrics")
    
    print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
    print("  1. Review detailed results in output/comparison_results_quick.json")
    print("  2. Run full simulation for complete metrics")
    print("  3. Consider testing smaller FOC gap (e.g., 3 days vs 8 days)")
    print("  4. Share findings with stakeholders")


# ============================================================================
# COMMAND-LINE ARGUMENT PARSING
# ============================================================================

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Quick priority analysis comparing baseline and proposed scenarios',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        # Use default scenarios (even distribution)
        python compare_foc_impact.py

        # Compare even distribution scenarios
        python compare_foc_impact.py --baseline scenarios/baseline_even_scenario.yaml --proposed scenarios/proposed_even_scenario.yaml

        # Compare dedicated agent scenarios
        python compare_foc_impact.py --baseline scenarios/baseline_dedicated_scenario.yaml --proposed scenarios/proposed_dedicated_scenario.yaml

        # Custom output directory
        python compare_foc_impact.py --baseline scenarios/baseline_even_scenario.yaml --proposed scenarios/proposed_even_scenario.yaml --output output/even_comparison
                """
    )
    
    parser.add_argument(
        '--baseline',
        type=str,
        default=BASELINE_SCENARIO,
        help=f'Path to baseline scenario YAML file (default: {BASELINE_SCENARIO})'
    )
    
    parser.add_argument(
        '--proposed',
        type=str,
        default=PROPOSED_SCENARIO,
        help=f'Path to proposed scenario YAML file (default: {PROPOSED_SCENARIO})'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=OUTPUT_DIR,
        help=f'Output directory for results (default: {OUTPUT_DIR})'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'STM Routing Simulator Quick Analysis v{VERSION}'
    )
    
    return parser.parse_args()


# ============================================================================
# MAIN ANALYSIS FLOW
# ============================================================================

def main() -> int:
    """Main entry point for quick priority analysis"""
    
    # Parse command-line arguments
    args = parse_arguments()
    
    # Update global configuration with command-line arguments
    global BASELINE_SCENARIO, PROPOSED_SCENARIO, OUTPUT_DIR
    BASELINE_SCENARIO = args.baseline
    PROPOSED_SCENARIO = args.proposed
    OUTPUT_DIR = args.output
    
    try:
        demo_introduction(BASELINE_SCENARIO, PROPOSED_SCENARIO)
        baseline, proposed = load_scenarios()
        display_scenario_overview(baseline, proposed)
        baseline_analysis, proposed_analysis = run_analysis(baseline, proposed)
        display_overall_metrics(baseline_analysis, proposed_analysis)
        display_sla_comparison(baseline_analysis, proposed_analysis)
        display_customer_comparison(baseline_analysis, proposed_analysis)
        display_top_requests(baseline_analysis, proposed_analysis)
        rank_changes = display_rank_changes(baseline_analysis, proposed_analysis)
        display_key_insights(baseline_analysis, proposed_analysis, rank_changes)
        save_results(baseline_analysis, proposed_analysis, rank_changes)
        demo_conclusion(rank_changes)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n{Colors.RED}❌ Error: Scenario file not found{Colors.END}")
        print(f"   {e}")
        print("\n   Make sure the scenario files exist:")
        print(f"   - Baseline: {BASELINE_SCENARIO}")
        print(f"   - Proposed: {PROPOSED_SCENARIO}")
        print("\n   Run from: Simulator_v3/demo/demo_wholesale_sla_impact/")
        return 1
        
    except Exception as e:
        print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.END}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
