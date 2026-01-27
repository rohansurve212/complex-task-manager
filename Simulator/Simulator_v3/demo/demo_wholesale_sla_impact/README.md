# Wholesale SLA Impact Analysis Demo

## Overview

This demo analyzes the impact of introducing Service Level Agreement (SLA) assignments and dramatically reduced First Order Completion (FOC) targets for a subset of wholesale customers. The analysis simulates a proposed two-tier service system where 7 out of 13 customers receive preferential treatment through aggressive FOC target reduction (8 days → 1 day, an 87.5% reduction).

**Key Question:** What happens when we give 7 customers an 8x priority boost while maintaining standard service for the remaining 6 customers?

---

## Table of Contents

- [Business Context](#business-context)
- [Scenario Description](#scenario-description)
- [Demo Components](#demo-components)
- [Queue Position Analysis](#queue-position-analysis)
- [Installation & Setup](#installation--setup)
- [Usage Guide](#usage-guide)
- [Understanding the Results](#understanding-the-results)
- [Technical Details](#technical-details)
- [Files Reference](#files-reference)
- [Interpreting Metrics](#interpreting-metrics)
- [Recommendations](#recommendations)
- [FAQ](#faq)

---

## Business Context

### Current State (Baseline)

The Wholesale team currently operates with:
- **56 agents** handling wholesale service requests
- **~10,000 requests** in production (scaled to 500 for simulation)
- **13 customers** all receiving equal priority
- **Uniform FOC target:** 8.0 days for all customers
- **No SLA differentiation:** All requests treated equally

### Proposed Change

The team is considering implementing a two-tier service model:

| Customer Tier | Customers | FOC Target | has_sla | Requests | Impact |
|--------------|-----------|------------|---------|----------|--------|
| **SLA Tier** | CUST_A through CUST_G (7) | 1.0 day | True | 200 (40%) | 87.5% reduction |
| **Standard Tier** | CUST_H through CUST_M (6) | 8.0 days | False | 300 (60%) | No change |

### Why This Matters

**Priority Score Formula:**
```
Priority Score = Request Age (minutes) / FOC Target (minutes)
```

**For a 10-day old request:**
- Baseline (FOC=8.0): Priority = 10/8 = **1.25**
- SLA (FOC=1.0): Priority = 10/1 = **10.0**
- **Impact: 8x (700%) priority increase!**

This is an **extremely aggressive** change that will fundamentally alter the queue dynamics and service delivery.

---

## Scenario Description

### Baseline Scenario

**File:** `scenarios/baseline_scenario.yaml`

- **Name:** Baseline - Wholesale Team (No SLA Assignments)
- **Configuration:**
  - 56 agents with varied skillsets
  - 500 requests from 13 customers
  - All customers: `foc_target = 8.0 days`, `has_sla = false`
  - Requests distributed across 30 days of age
  - 8-hour simulation duration

**Purpose:** Establish current-state metrics for comparison

### Proposed Scenario

**File:** `scenarios/proposed_scenario.yaml`

- **Name:** Proposed - Wholesale Team with SLA Assignments
- **Configuration:**
  - Same 56 agents with identical skillsets
  - Same 500 requests from 13 customers
  - **SLA Customers (CUST_A-G):** `foc_target = 1.0 day`, `has_sla = true` (200 requests)
  - **Non-SLA Customers (CUST_H-M):** `foc_target = 8.0 days`, `has_sla = false` (300 requests)
  - Same request age distribution
  - Same 8-hour simulation duration

**Purpose:** Measure impact of SLA assignments on service delivery

### Request Distribution

| Customer ID | Customer Type | Requests | % of Total | FOC Target (Proposed) |
|-------------|--------------|----------|------------|-----------------------|
| CUST_A | SLA | 30 | 6% | 1.0 day |
| CUST_B | SLA | 30 | 6% | 1.0 day |
| CUST_C | SLA | 30 | 6% | 1.0 day |
| CUST_D | SLA | 30 | 6% | 1.0 day |
| CUST_E | SLA | 30 | 6% | 1.0 day |
| CUST_F | SLA | 25 | 5% | 1.0 day |
| CUST_G | SLA | 25 | 5% | 1.0 day |
| **SLA Subtotal** | | **200** | **40%** | |
| CUST_H | Non-SLA | 50 | 10% | 8.0 days |
| CUST_I | Non-SLA | 50 | 10% | 8.0 days |
| CUST_J | Non-SLA | 50 | 10% | 8.0 days |
| CUST_K | Non-SLA | 50 | 10% | 8.0 days |
| CUST_L | Non-SLA | 50 | 10% | 8.0 days |
| CUST_M | Non-SLA | 50 | 10% | 8.0 days |
| **Non-SLA Subtotal** | | **300** | **60%** | |
| **TOTAL** | | **500** | **100%** | |

### Agent Configuration

**56 Wholesale Team Agents:**

| Skillset Combination | Count | Percentage |
|---------------------|-------|------------|
| WholesaleBasic + WholesaleAdvanced | 22 | 40% |
| WholesaleBasic + WholesaleExpert | 11 | 20% |
| WholesaleAdvanced + WholesaleExpert | 11 | 20% |
| WholesaleBasic + WholesaleAdvanced + WholesaleExpert | 12 | 20% |

**Agent:Request Ratio:** 1:8.9 (realistic production capacity)

---

## Demo Components

This demo provides two complementary analysis tools:

### 1. Quick Priority Analysis (`compare_foc_impact.py`)

**What it does:**
- Calculates priority scores at simulation start (t=0)
- Ranks all 500 requests by priority
- Shows comparative metrics between scenarios
- Provides instant impact assessment
- **NEW:** Quantifies queue position changes for both customer tiers

**What it does NOT do:**
- Run discrete event simulation
- Assign requests to agents
- Calculate actual wait times
- Model time progression

**Runtime:** < 1 second

**Use case:** Fast "what-if" analysis to understand priority impact before running full simulation

**Key Output Sections:**
1. Overall metrics comparison
2. SLA vs non-SLA analysis
3. Customer-level comparison
4. Top 30 request rankings
5. **Queue position changes analysis** ⭐ NEW
6. Key insights

### 2. Full Discrete Event Simulation (`run_full_simulation.py`)

**What it does:**
- Runs complete STM Routing Simulator v3.0
- Assigns requests to agents using production routing logic
- Simulates 8-hour shift with time progression
- Tracks actual wait times, handle times, and throughput
- Measures FOC compliance over time
- Calculates agent utilization metrics

**What it includes:**
- Two-stage routing (filtration → assignment)
- Production-accurate priority scoring
- `has_sla` field evaluation in filtering logic
- Skill-based agent matching
- Complete metric collection

**Runtime:** 30-60 seconds

**Use case:** Complete production-ready simulation with real operational metrics

### 3. Scenario Generator (`generate_scenarios.py`)

**Purpose:** Generate or regenerate scenario files programmatically

**Capabilities:**
- Create 500 requests across 13 customers
- Generate 56 agents with varied skillsets
- Distribute request ages across 30 days
- Configure FOC targets and SLA assignments
- Maintain realistic production distributions

**Use case:** Modify scenarios to test different configurations (e.g., FOC targets, customer distributions)

---

## Queue Position Analysis

### Overview

The Quick Priority Analysis tool includes a **comprehensive queue position change analysis** that answers the critical business question:

> **"By how many positions do SLA customers jump ahead, and how far back do non-SLA customers fall?"**

This feature translates abstract priority scores into concrete queue position movements that stakeholders can easily understand.

### What It Calculates

#### For SLA Customers (CUST_A through CUST_G):

| Metric | Description |
|--------|-------------|
| **Average Position Improvement** | Mean number of positions SLA customers move up |
| **Median Position Improvement** | Middle value (less affected by outliers) |
| **Best Improvement** | Maximum positions gained |
| **Worst Improvement** | Minimum positions gained |
| **Standard Deviation** | Consistency of improvement across requests |
| **Top 100/200/300 Distribution** | How many SLA requests reach elite queue positions |

#### For Non-SLA Customers (CUST_H through CUST_M):

| Metric | Description |
|--------|-------------|
| **Average Position Deterioration** | Mean number of positions non-SLA customers drop |
| **Median Position Deterioration** | Middle value deterioration |
| **Best Case** | Smallest position drop |
| **Worst Case** | Largest position drop |
| **Standard Deviation** | Consistency of deterioration |
| **Dropped from Top X** | How many non-SLA requests lose premium positions |

#### Overall Impact:

| Metric | Formula | Meaning |
|--------|---------|---------|
| **Position Gap** | SLA avg improvement - Non-SLA avg deterioration | Net advantage for SLA customers |

### Example Output
```
📈 QUEUE POSITION ANALYSIS

SLA Customers (CUST_A-G) - Position Improvement:
  Total SLA Requests: 200
  Average Position Improvement: +218 positions
  Median Position Improvement: +215 positions
  Best Improvement: +350 positions
  Worst Improvement: +85 positions
  Standard Deviation: 45.2 positions

  Position Distribution:
    Moved to Top 100: 75/200 (37.5%)
    Moved to Top 200: 195/200 (97.5%)
    Moved to Top 300: 200/200 (100.0%)

Non-SLA Customers (CUST_H-M) - Position Deterioration:
  Total Non-SLA Requests: 300
  Average Position Deterioration: -145 positions
  Median Position Deterioration: -148 positions
  Best Case: -50 positions
  Worst Case: -280 positions

Overall Impact:
  Average position gap: 363 positions
  SLA customers improve by 218 positions on average
  Non-SLA customers drop by 145 positions on average
  Net effect: 363-position advantage for SLA customers
```

### How Position Change Is Calculated
```
Position Change = Baseline Rank - Proposed Rank

Example:
  Request: REQ_CUST_A_010
  Baseline Rank: 250
  Proposed Rank: 32
  Position Change: 250 - 32 = +218 positions (improvement)
```

**Interpretation:**
- **Positive value** = Improvement (moved up in queue)
- **Negative value** = Deterioration (moved down in queue)
- **Zero** = No change

### Why This Matters

#### Business Communication

**Instead of saying:**
> "SLA customers will get higher priority"

**You can now say:**
> "SLA customers will move up 218 positions on average, while non-SLA customers drop 145 positions, creating a 363-position gap"

#### Decision Support

The position gap metric provides actionable guidance:

| Position Gap | Interpretation | Recommended Action |
|--------------|----------------|-------------------|
| **< 150** | Subtle differentiation | SLA value may be weak |
| **150-300** | Moderate two-tier system | Balanced approach |
| **300+** | Very strong differentiation | Monitor non-SLA satisfaction |

**Current scenario:** ~360 position gap = **Very strong differentiation**

### Using Position Analysis for Testing

Test different FOC targets to find the optimal position gap:
```python
# In generate_scenarios.py, modify:
foc_target = 3.0  # Instead of 1.0

# Expected results:
# 1-day FOC: ~360 position gap (8x priority)
# 3-day FOC: ~180 position gap (2.67x priority)
# 4-day FOC: ~120 position gap (2x priority)
```

Run quick analysis after each change to compare position gaps and choose the configuration that balances SLA value with non-SLA service levels.

### JSON Output

Position change data is exported to `output/comparison_results_quick.json`:
```json
{
  "comparison": {
    "rank_changes": {
      "sla_avg_improvement": 218.3,
      "non_sla_avg_deterioration": -145.2,
      "position_gap": 363.5,
      "sla_to_top_200": 195
    }
  }
}
```

This enables:
- Custom reporting and dashboards
- Charts and visualizations
- Further statistical analysis
- Stakeholder presentations

**For complete documentation, see:** `QUEUE_POSITION_ANALYSIS.md`

---

## Installation & Setup

### Prerequisites

- Python 3.8+
- Access to STM Routing Simulator v3.0
- Required Python packages:
  - `pyyaml`
  - `simpy` (for full simulation)
  - Standard library: `datetime`, `json`, `pathlib`, `statistics`

### Directory Structure
```
Simulator_v3/
├── demo/
│   └── demo_wholesale_sla_impact/          ← Place demo here
│       ├── scenarios/
│       │   ├── baseline_scenario.yaml       (500 requests, 56 agents)
│       │   └── proposed_scenario.yaml       (500 requests, 56 agents)
│       ├── output/                          (created automatically)
│       │   ├── baseline/
│       │   ├── proposed/
│       │   └── comparison_results_*.json
│       ├── compare_foc_impact.py           (Quick analysis)
│       ├── run_full_simulation.py          (Full simulation)
│       ├── generate_scenarios.py           (Scenario generator)
│       ├── README.md                       (This file)
│       ├── SETUP_INSTRUCTIONS.md
│       ├── UPDATE_NOTES.md
│       └── QUEUE_POSITION_ANALYSIS.md      (Position analysis docs)
├── scenario/
│   ├── scenario_loader.py
│   └── scenario_runner.py
└── (other simulator files)
```

### Installation Steps

1. **Download the demo package:**
```bash
   # Download demo_wholesale_sla_impact.zip
   unzip demo_wholesale_sla_impact.zip
```

2. **Copy to your repository:**
```bash
   cp -r demo_wholesale_sla_impact /path/to/Simulator_v3/demo/
```

3. **Verify installation:**
```bash
   cd Simulator_v3/demo/demo_wholesale_sla_impact
   ls -la scenarios/
   # Should see: baseline_scenario.yaml, proposed_scenario.yaml
```

4. **Test setup:**
```bash
   # Quick test
   python compare_foc_impact.py
```

---

## Usage Guide

### Quick Start (Recommended Workflow)

**Step 1: Quick Priority Analysis**
```bash
cd Simulator_v3/demo/demo_wholesale_sla_impact
python compare_foc_impact.py
```

This shows you:
- Priority score changes
- Request ranking shifts
- Per-customer impact
- SLA vs non-SLA comparison
- **Queue position changes** (how many positions each tier moves)

**Review output, then decide if you want to run full simulation.**

**Step 2: Full Simulation**
```bash
python run_full_simulation.py
```

This provides:
- Complete operational metrics
- Actual wait times and throughput
- Agent utilization statistics
- Detailed output files

### Alternative: Direct Simulator Execution

You can also run the simulator directly without the wrapper scripts:
```bash
cd Simulator_v3

# Run baseline
python main.py demo/demo_wholesale_sla_impact/scenarios/baseline_scenario.yaml \
  --output demo/demo_wholesale_sla_impact/output/baseline/

# Run proposed
python main.py demo/demo_wholesale_sla_impact/scenarios/proposed_scenario.yaml \
  --output demo/demo_wholesale_sla_impact/output/proposed/
```

### Modifying Scenarios

To test different FOC targets or customer distributions:

1. **Edit `generate_scenarios.py`:**
```python
   # Example: Test 3-day FOC instead of 1-day
   # In generate_proposed_scenario():
   requests = generate_requests(customer_id, num_requests, 
                                foc_target=3.0,  # Changed from 1.0
                                has_sla=True, 
                                start_offset=start_offset)
```

2. **Regenerate scenarios:**
```bash
   python generate_scenarios.py
```

3. **Run analysis with new scenarios:**
```bash
   python compare_foc_impact.py
   python run_full_simulation.py
```

---

## Understanding the Results

### Quick Analysis Output

**Example Output Sections:**

1. **Overall Metrics Comparison**
```
   Metric                         Baseline    Proposed     Change
   ─────────────────────────────────────────────────────────────
   Total Requests                      500         500          0
   FOC Compliance Rate               45.2%       52.8%    +7.6pp
   Avg Priority Score                0.875       1.234    +41.0%
   Median Priority Score             0.625       0.875    +40.0%
   Avg Age (days)                    15.2d       15.2d        0%
```

2. **SLA vs Non-SLA Analysis**
```
   Category              Count  Avg Priority  Avg Rank  Avg Age (d)
   ─────────────────────────────────────────────────────────────────
   SLA Customers          200         2.456       125      15.1
   Non-SLA Customers      300         0.312       320      15.3
```

3. **Customer-Level Impact**
```
   Customer   SLA  FOC Tgt     Avg Priority        Avg Rank
                    B→P      Base  Prop   Δ%    Base  Prop
   ────────────────────────────────────────────────────────
   CUST_A     Yes  8.0→1.0   0.875 7.001  +700    250    32
   CUST_H     No   8.0→8.0   0.875 0.875    +0    250   390
```

4. **Queue Position Changes** ⭐ NEW
```
   SLA Customers:
     Average Position Improvement: +218 positions
     Moved to Top 200: 195/200 (97.5%)
   
   Non-SLA Customers:
     Average Position Deterioration: -145 positions
     Dropped from Top 200: 130 requests
   
   Overall Position Gap: 363 positions
```

**Key Insights from Quick Analysis:**
- Priority score increase for SLA customers (~700%)
- **Position improvement for SLA customers (~220 positions)**
- **Position deterioration for non-SLA customers (~145 positions)**
- **Net position gap (~360 positions)**
- Queue domination: 70-90% of top positions occupied by SLA requests

### Full Simulation Output

**Example Metrics:**
```
Metric                         Baseline    Proposed     Change
─────────────────────────────────────────────────────────────
Requests Completed                  487         489         +2
Avg Wait Time (min)                45.3        42.1      -7.1%
FOC Compliance Rate               44.8%       51.2%    +6.4pp
Avg Agent Utilization             87.3%       88.1%    +0.8pp
```

**Output Files Generated:**

1. **`output/baseline/`**
   - `requests.json` - Per-request metrics (assignment time, wait time, etc.)
   - `agents.json` - Per-agent metrics (utilization, requests handled)
   - `simulation_stats.json` - System-wide statistics

2. **`output/proposed/`**
   - Same structure as baseline
   - Includes SLA tier breakdowns

3. **`output/comparison_results_full.json`**
   - Side-by-side comparison
   - Change calculations
   - Metadata and timestamps

---

## Technical Details

### Priority Score Calculation

The routing system uses FOC-based priority scoring:
```python
priority_score = age_in_minutes / (foc_target_days * 24 * 60)
```

**Examples:**

| Request Age | FOC Target | Priority Score | Relative Priority |
|-------------|------------|----------------|-------------------|
| 10 days | 8.0 days | 1.25 | Baseline |
| 10 days | 1.0 day | 10.0 | 8x higher |
| 5 days | 8.0 days | 0.625 | 0.5x baseline |
| 5 days | 1.0 day | 5.0 | 8x higher |

**Key Insight:** The priority multiplier is constant regardless of request age:
```
Priority Multiplier = Old FOC / New FOC = 8.0 / 1.0 = 8x
```

### Routing Logic

The simulator implements a two-stage routing process:

**Stage 1: Filtration (Production Filtering)**
```python
def apply_priority_levels(request_pool):
    """
    Applies priority tiers based on has_sla and FOC compliance
    Returns filtered buckets: followup vs CMO handling
    """
    if request.has_sla and not request.is_foc_compliant():
        priority = "HIGH_PRIORITY"
    elif request.is_foc_compliant():
        priority = "STANDARD"
    else:
        priority = "LOW_PRIORITY"
```

**Stage 2: Assignment (Optimal Matching)**
```python
def assign_request_to_agent(eligible_requests, available_agents):
    """
    Assigns highest-priority eligible request to best-matched agent
    Uses FOC-based scoring for prioritization
    """
    # Sort requests by priority score (descending)
    sorted_requests = sort_by_priority(eligible_requests)
    
    # Find best agent match based on skills
    for request in sorted_requests:
        agent = find_best_agent_match(request, available_agents)
        if agent:
            return assign(request, agent)
```

### has_sla Field Importance

The `has_sla` boolean field is **critical** for production routing:

**In Baseline:**
- All requests: `has_sla = false`
- No preferential treatment in filtration stage
- Priority determined solely by FOC score

**In Proposed:**
- SLA requests: `has_sla = true`
- Affects bucket assignment in filtration
- Combined with low FOC target (1.0 day) for maximum priority

**Impact on Routing:**
```
SLA Request (has_sla=true, foc_target=1.0):
  → High priority bucket (if not FOC compliant)
  → 8x priority score
  → Assigned first among eligible requests

Non-SLA Request (has_sla=false, foc_target=8.0):
  → Standard/low priority bucket
  → 1x priority score
  → Assigned after all higher-priority requests
```

### Simulation Parameters

**Fixed Parameters:**
- **Simulation Duration:** 8 hours (480 minutes)
- **Agents:** 56 with defined skillsets
- **Requests:** 500 total
- **Start Time:** 2024-01-15 09:00:00 EST

**Variable Parameters (by scenario):**
- FOC targets (8.0 vs 1.0 days)
- has_sla flags (false vs true)

**Handle Time Ranges:**
```python
# Production-calibrated handle times
handle_time_ranges = {
    'priority_1': (112, 176),  # High priority: 1.9-2.9 hours
    'priority_2': (112, 176),  # Medium priority: 1.9-2.9 hours
    'priority_3': (112, 176),  # Low priority: 1.9-2.9 hours
}
```

---

## Files Reference

### Scenario Files

#### `scenarios/baseline_scenario.yaml` (154 KB, 6,060 lines)

Complete scenario definition including:
- 56 agent definitions with skillsets
- 500 request definitions with all attributes
- Routing configuration
- Start time and simulation parameters

**Key Fields:**
```yaml
agents:
  - agent_id: AGENT001
    full_name: Alex Thompson
    skillsets: [WholesaleBasic, WholesaleAdvanced]

requests:
  - request_id: REQ_CUST_A_001
    foc_target: 8.0
    has_sla: false
    golden_customer_id: CUST_A
    order_date_offset_hours: -24
```

#### `scenarios/proposed_scenario.yaml` (153 KB, 6,060 lines)

Identical structure to baseline with updated:
- `foc_target: 1.0` for CUST_A through CUST_G
- `has_sla: true` for CUST_A through CUST_G
- All other fields identical

### Analysis Scripts

#### `compare_foc_impact.py` (850+ lines)

**Components:**
- `SimplifiedRequest` class - Lightweight request model for quick analysis
- `ScenarioAnalyzer` class - Loads and analyzes scenarios
- Demo orchestration functions - Step-by-step analysis flow
- Visual formatting - Color-coded terminal output
- **Queue position change calculation** - New feature

**Key Functions:**
```python
def calculate_priority_score(request, current_time):
    """Calculate FOC-based priority score"""
    
def analyze_at_time(scenario, hours_after_start):
    """Analyze scenario at specific time point"""
    
def display_rank_changes(baseline, proposed):
    """Calculate and display queue position changes"""
    
def compare_scenarios(baseline, proposed):
    """Generate comparative analysis"""
```

#### `run_full_simulation.py` (650+ lines)

**Components:**
- Imports simulator modules (`ScenarioLoader`, `ScenarioRunner`)
- Demo orchestration - Step-by-step simulation workflow
- Results comparison - Side-by-side metric analysis
- Output generation - JSON files and formatted displays

**Key Functions:**
```python
def run_baseline_simulation(scenario):
    """Execute baseline simulation"""
    
def run_proposed_simulation(scenario):
    """Execute proposed simulation"""
    
def compare_results(baseline_stats, proposed_stats):
    """Compare simulation results"""
```

#### `generate_scenarios.py` (350+ lines)

**Components:**
- `generate_agents()` - Creates 56 agent definitions
- `generate_requests()` - Creates request definitions for each customer
- `generate_baseline_scenario()` - Builds baseline YAML
- `generate_proposed_scenario()` - Builds proposed YAML

**Configuration:**
```python
SLA_CUSTOMERS = {
    'CUST_A': 30, 'CUST_B': 30, 'CUST_C': 30,
    'CUST_D': 30, 'CUST_E': 30, 'CUST_F': 25, 'CUST_G': 25
}

NON_SLA_CUSTOMERS = {
    'CUST_H': 50, 'CUST_I': 50, 'CUST_J': 50,
    'CUST_K': 50, 'CUST_L': 50, 'CUST_M': 50
}
```

### Documentation Files

- **README.md** (this file) - Comprehensive documentation
- **SETUP_INSTRUCTIONS.md** - Quick setup and usage guide
- **UPDATE_NOTES.md** - Agent count update documentation
- **DEMO_FILES_SUMMARY.md** - Overview and context
- **QUEUE_POSITION_ANALYSIS.md** - Queue position feature documentation

---

## Interpreting Metrics

### Priority Score Metrics

**What it means:**
- Higher score = Higher urgency = Processed sooner
- Proportional to request age
- Inversely proportional to FOC target

**How to interpret:**
```
Score < 1.0  →  Request age < FOC target (on track)
Score = 1.0  →  Request age = FOC target (at deadline)
Score > 1.0  →  Request age > FOC target (overdue)
```

**Example:**
- Request with priority score 10.0 is **10x more urgent** than one with score 1.0
- Will be assigned first if both are skill-eligible

### Queue Position Metrics ⭐ NEW

**What it means:**
- Position in queue (1 = first, 500 = last)
- Lower number = Higher priority = Processed sooner
- Position change = Baseline rank - Proposed rank

**How to interpret:**
```
Positive change  →  Moved up (improved position)
Negative change  →  Moved down (worse position)
Zero change      →  No movement
```

**Example:**
- Request at position 250 (baseline) moves to position 45 (proposed)
- Position change: 250 - 45 = +205 positions improvement

**Position Gap Interpretation:**

| Gap Value | Service Differentiation | Business Impact |
|-----------|------------------------|-----------------|
| < 150 | Subtle | Modest SLA value |
| 150-300 | Moderate | Balanced approach |
| 300-400 | Strong | Significant advantage |
| > 400 | Very Strong | Extreme differentiation |

**Current Scenario:** ~360 position gap = Strong differentiation with potential non-SLA impact

### Wait Time Metrics

**Definition:** Time from request creation to agent assignment

**Interpretation:**
```
Low wait time (< 30 min)   →  Good capacity, high priority
Medium wait time (30-120 min) →  Standard processing
High wait time (> 120 min)  →  Capacity constraint or low priority
```

**SLA vs Non-SLA:**
- SLA customers: Expect dramatically lower wait times
- Non-SLA customers: Expect significantly higher wait times

### FOC Compliance Rate

**Definition:** Percentage of requests completed within FOC target

**Calculation:**
```
FOC Compliance = (Requests within FOC / Total Requests) × 100%
```

**Interpretation:**
```
> 90%  →  Excellent performance
80-90% →  Good performance
70-80% →  Acceptable performance
< 70%  →  Performance concern
```

**Expected Changes:**
- **SLA customers:** Compliance should increase significantly (easier 1-day target)
- **Non-SLA customers:** Compliance may decrease (deprioritized)
- **Overall:** May increase (more SLA requests meeting tighter targets)

### Agent Utilization

**Definition:** Percentage of time agents are handling requests (vs idle)

**Calculation:**
```
Utilization = (Active Time / Total Time) × 100%
```

**Interpretation:**
```
> 95%  →  Overloaded (risk of burnout)
85-95% →  Optimal utilization
70-85% →  Good utilization
< 70%  →  Underutilized capacity
```

**With 56 agents handling 500 requests:**
- Expected range: 80-90%
- Balanced workload across agents

---

## Recommendations

### Before Running in Production

1. **Run Both Analysis Tools:**
   - Quick analysis first (1 second) to see priority impact and position changes
   - Full simulation next (60 seconds) for complete metrics
   - Compare results to expectations

2. **Review Queue Position Changes:**
   - Check average position improvement for SLA customers
   - Check average position deterioration for non-SLA customers
   - Evaluate if the position gap is acceptable to the business
   - Consider: Is ~360 position advantage appropriate?

3. **Validate Service Level Expectations:**
   - Are non-SLA customer wait times acceptable?
   - Can the business tolerate the service gap?
   - Have stakeholders approved the two-tier system?

4. **Test Alternative Configurations:**

   **Conservative Approach (Recommended):**
```python
   # In generate_scenarios.py
   SLA_FOC_TARGET = 4.0  # Instead of 1.0
   # Priority increase: 8/4 = 2x (instead of 8x)
   # Expected position gap: ~120 positions
```

   **Moderate Approach:**
```python
   SLA_FOC_TARGET = 3.0  # Instead of 1.0
   # Priority increase: 8/3 = 2.67x (instead of 8x)
   # Expected position gap: ~180 positions
```

   **Aggressive Approach (Current):**
```python
   SLA_FOC_TARGET = 1.0
   # Priority increase: 8/1 = 8x
   # Expected position gap: ~360 positions
```

5. **Review Customer Contracts:**
   - Ensure SLA commitments are achievable
   - Document service level expectations for non-SLA customers
   - Prepare communication about service tier differences

### During Rollout

1. **Phased Implementation:**
   - Start with 2-3 SLA customers
   - Monitor for 2 weeks
   - Gradually add remaining SLA customers

2. **Monitoring Plan:**
```
   Daily:
   - Wait time distributions by customer tier
   - FOC compliance rates
   - Customer complaints/escalations
   - Queue position distributions
   
   Weekly:
   - Agent utilization trends
   - Request volume by tier
   - Service level achievement
   - Average position gap stability
   
   Monthly:
   - Customer satisfaction surveys
   - SLA vs non-SLA performance gap
   - Business impact assessment
```

3. **Adjustment Triggers:**
```
   IF non-SLA wait times > 4 hours:
     → Consider increasing FOC target for SLA (e.g., 1.0 → 2.0 days)
   
   IF SLA compliance < 95%:
     → Review capacity or adjust FOC target
   
   IF customer complaints increase > 50%:
     → Pause and reassess strategy
   
   IF position gap > 400:
     → Consider reducing SLA priority advantage
```

### After 30 Days

1. **Performance Review:**
   - Compare actual vs predicted metrics
   - Assess customer satisfaction impact
   - Evaluate business value delivered
   - Measure actual position gap in production

2. **Decision Points:**
   - Continue as-is
   - Adjust FOC targets
   - Modify customer tier assignments
   - Revert to uniform service

---

## FAQ

### Q: Why 56 agents instead of 10?

**A:** 56 agents provides realistic production capacity:
- Agent:Request ratio of 1:8.9 (industry standard)
- More accurate utilization metrics
- Better reflects actual Wholesale team size
- Previous 10 agents = unrealistic 50:1 ratio

### Q: Can I test different FOC targets?

**A:** Yes! Edit `generate_scenarios.py`:
```python
# In generate_proposed_scenario()
# Change this line:
foc_target=1.0  # Try 2.0, 3.0, or 4.0 instead

# Then regenerate:
python generate_scenarios.py
```

### Q: What if I want to test different customer distributions?

**A:** Modify the customer configuration in `generate_scenarios.py`:
```python
SLA_CUSTOMERS = {
    'CUST_A': 50,  # Increase CUST_A requests
    'CUST_B': 20,  # Decrease CUST_B requests
    # ... adjust as needed
}
```

### Q: How long does the full simulation take?

**A:** 30-60 seconds typically, depending on:
- Hardware (CPU speed)
- Request complexity
- Number of agents and requests

### Q: Can I run this on production data?

**A:** Yes, but:
1. Export production requests to YAML format
2. Include all required fields (foc_target, has_sla, etc.)
3. Ensure agent definitions match production
4. Consider privacy/security of production data

### Q: What does "has_sla: true" actually do?

**A:** The `has_sla` field affects:
1. **Production filtering logic** - Determines request bucket assignment
2. **Priority calculation** - Combined with FOC target for scoring
3. **Compliance tracking** - Separate metrics for SLA vs non-SLA

### Q: How do I know if results are realistic?

**A:** Validate against production data:
- Compare baseline simulation to current production metrics
- If baseline matches production, proposed simulation is reliable
- If baseline doesn't match, adjust scenario parameters

### Q: Can I test more than 2 tiers?

**A:** Current simulator supports binary SLA (true/false). For multi-tier:
1. Run multiple simulations with different FOC targets
2. Compare results across tiers
3. Or extend simulator to support tier levels

### Q: What's the difference between priority score and rank?

**A:**
- **Priority Score:** Calculated value based on age/FOC (0-50+)
- **Rank:** Position in queue (1 = highest, 500 = lowest)
- Rank is derived from sorting by priority score

### Q: What's a good position gap?

**A:** Depends on business goals:
- **100-200 positions:** Moderate differentiation, balanced approach
- **200-400 positions:** Strong differentiation, clear SLA value
- **400+ positions:** Extreme differentiation, monitor non-SLA satisfaction

### Q: Should I use quick analysis or full simulation?

**A:** Use both!
1. **Quick analysis** - Fast preview of priority impact and position changes
2. **Full simulation** - Complete metrics for decision-making

Quick analysis tells you "what might happen," full simulation tells you "what will happen."

### Q: How do I share results with stakeholders?

**A:** Multiple options:
1. **Visual output** - Screenshot the terminal output (color-coded)
2. **JSON files** - Share `comparison_results_*.json` files
3. **Position gap metric** - Use concrete numbers (e.g., "218 position improvement")
4. **Custom reports** - Parse JSON and create presentations
5. **This README** - Share complete documentation

### Q: Why is position analysis important?

**A:** It translates abstract priority scores into concrete queue movements:
- **Abstract:** "Priority score increases by 700%"
- **Concrete:** "SLA customers move up 218 positions on average"

Stakeholders understand positions better than mathematical formulas.

### Q: Can I export position change data?

**A:** Yes! Check `output/comparison_results_quick.json`:
```json
{
  "comparison": {
    "rank_changes": {
      "sla_avg_improvement": 218.3,
      "non_sla_avg_deterioration": -145.2,
      "position_gap": 363.5,
      "sla_to_top_200": 195
    }
  }
}
```

Use this data for charts, dashboards, or further analysis.

---

## Conclusion

This demo provides comprehensive analysis of a proposed two-tier service system for the Wholesale team. The 87.5% FOC reduction (8 days → 1 day) for SLA customers represents an **extremely aggressive** prioritization strategy that will fundamentally alter queue dynamics.

**Key Takeaways:**

✅ **Tools:** Two complementary analysis tools (quick + full simulation)
✅ **Realism:** Production-scale simulation (56 agents, 500 requests)
✅ **Flexibility:** Easy to modify and test alternative configurations
✅ **Completeness:** Detailed metrics for data-driven decision-making
✅ **Position Analysis:** Concrete queue position changes for both tiers

⚠️ **Critical Considerations:**

- 8x priority increase is unprecedented
- **SLA customers improve by ~220 positions on average**
- **Non-SLA customers drop by ~145 positions on average**
- **Net position gap of ~360 positions is very significant**
- Consider testing more moderate FOC targets (3-4 days)
- Monitor customer satisfaction closely after implementation

**Next Steps:**

1. Run both analysis tools
2. Review position gap and overall impact
3. Test alternative FOC targets if gap is too large
4. Present findings to stakeholders with concrete numbers
5. Plan phased rollout with monitoring

---

## Version History

- **v1.0.0** (2024-01-23)
  - Initial release
  - 56 agents, 500 requests
  - 13 customers (7 SLA, 6 non-SLA)
  - Complete analysis tools

- **v1.1.0** (2024-01-26)
  - Added queue position change analysis
  - Added QUEUE_POSITION_ANALYSIS.md documentation
  - Enhanced quick analysis output with position metrics
  - Updated JSON export with rank change data

---

## Support & Contact

For questions or issues:
1. Review this README thoroughly
2. Check SETUP_INSTRUCTIONS.md for setup issues
3. Review UPDATE_NOTES.md for recent changes
4. Check QUEUE_POSITION_ANALYSIS.md for position analysis details
5. Consult STM Routing Simulator v3.0 documentation

---

**Happy simulating! 🚀**