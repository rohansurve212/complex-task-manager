# FOC Target Impact Analysis Demo

## Overview

This demo assesses the impact of changing the `foc_target` (Firm Order Completion target) for specific clients in the STM Routing Simulator. It compares two scenarios to help you understand how adjusting FOC targets affects request prioritization and processing order.

## What is FOC Target?

The `foc_target` is a time-based target (measured in days) that determines how "urgent" a request becomes over time. The simulator uses this to calculate priority scores:

```
Priority Score = (Request Age in Minutes) / (FOC Target in Minutes)
```

**Key Points:**
- **Lower FOC target** = Request becomes urgent faster = **Higher priority**
- **Higher FOC target** = Request stays non-urgent longer = **Lower priority**
- Older requests naturally have higher priority scores

## Demo Setup

### Baseline Scenario
- **File:** `baseline_scenario.yaml`
- **Configuration:**
  - 5 clients (CLIENT_A, CLIENT_B, CLIENT_C, CLIENT_D, CLIENT_E)
  - 10 requests per client (50 total)
  - 10 agents with various skillsets
  - **All clients have foc_target = 8.0 days**

### Proposed Scenario
- **File:** `proposed_scenario.yaml`
- **Configuration:**
  - Same 5 clients and 50 requests
  - Same 10 agents
  - **CLIENT_A and CLIENT_B have foc_target = 5.6 days (30% lower)**
  - CLIENT_C, CLIENT_D, CLIENT_E keep foc_target = 8.0 days

## Key Findings

### 1. Priority Score Impact
When we reduced the FOC target by 30% for CLIENT_A and CLIENT_B:
- Their average priority scores **increased by 42.9%**
- This makes their requests significantly more urgent in the system

### 2. Request Ranking Changes
- **18 out of 20** requests from CLIENT_A and CLIENT_B improved their ranking
- **Average improvement: 3.6 positions** in the queue
- **Total rank positions gained: 73** across all affected requests

### 3. Examples of Rank Changes

| Request ID | Client | Baseline Rank | Proposed Rank | Change |
|------------|--------|---------------|---------------|--------|
| REQ_A009   | CLIENT_A | 11 | 4 | +7 ↑ |
| REQ_B009   | CLIENT_B | 9 | 3 | +6 ↑ |
| REQ_A008   | CLIENT_A | 16 | 11 | +5 ↑ |
| REQ_B008   | CLIENT_B | 14 | 9 | +5 ↑ |

### 4. Impact on Other Clients
- CLIENT_C, CLIENT_D, and CLIENT_E requests **did not change** their priority scores
- However, they are now **relatively lower priority** compared to CLIENT_A and CLIENT_B
- On average, their requests moved down by **~2.4 positions** to make room for CLIENT_A/B

### 5. System-Wide Effects
- Overall average priority score increased by **15.2%**
- FOC compliance rate remained unchanged (both scenarios at 2.0%)
- This is a **prioritization change**, not a capacity change

## Business Implications

### Strategic Use Cases
1. **VIP Clients:** Give preferential treatment to high-value customers
2. **SLA Requirements:** Meet contractual obligations by adjusting FOC targets
3. **Temporary Prioritization:** Adjust targets during critical periods
4. **Workload Management:** Balance demand across different client segments

### Trade-offs to Consider
- **Winners:** Clients with lower FOC targets get faster service
- **Impact:** Other clients experience slightly longer wait times
- **System Capacity:** Total throughput remains the same
- **Fairness:** Creates a two-tier service level

## Running the Demo

### Prerequisites
```bash
pip install pyyaml
```

### Execute
```bash
cd /Simulator/Simulator_v3/simulator_demo
python3 compare_foc_impact.py
```

### Output Files
- **Console Output:** Detailed comparison report
- **comparison_results.json:** Complete analysis data in JSON format

## Understanding the Results

### Priority Score Comparison Table
Shows how each client's average priority score changes:

```
Client    FOC Target   Avg Priority Score   Avg Rank   FOC Compliance
          Base→Prop    Base     Prop    Δ%   Base Prop  Base    Prop
--------------------------------------------------------------------------------
CLIENT_A     8.0→5.6   0.305  0.436   42.9  28.9 25.4   10.0%  10.0%
CLIENT_B     8.0→5.6   0.333  0.476   42.9  27.0 23.2    0.0%   0.0%
CLIENT_C     8.0→8.0   0.356  0.356    0.0  25.5 27.9    0.0%   0.0%
CLIENT_D     8.0→8.0   0.385  0.385    0.0  24.0 26.2    0.0%   0.0%
CLIENT_E     8.0→8.0   0.417  0.417    0.0  22.1 24.8    0.0%   0.0%
```

### Top 20 Requests
The report shows the top 20 highest priority requests in each scenario:
- **Baseline:** Requests are ordered purely by age (all have same FOC target)
- **Proposed:** CLIENT_A and CLIENT_B requests jump to the front (marked with ⭐)

## Customizing the Demo

### Adjusting FOC Targets
Edit the YAML files to test different FOC target values:

```yaml
# In proposed_scenario.yaml
- request_id: REQ_A001
  foc_target: 5.6  # Change this value
```

### Adding More Clients
Add new client sections to the YAML files:

```yaml
# Add CLIENT_F requests
- request_id: REQ_F001
  golden_customer_id: CLIENT_F
  foc_target: 6.5
  # ... other fields
```

### Testing Different Reductions
Try different percentage reductions:
- **50% reduction:** 8.0 → 4.0 days (more aggressive)
- **20% reduction:** 8.0 → 6.4 days (more conservative)
- **Multiple tiers:** Different FOC targets for different client groups

## Code Structure

### Main Components

1. **SimplifiedRequest Class**
   - Represents a request with FOC target
   - Calculates priority scores
   - Tracks FOC compliance

2. **ScenarioAnalyzer Class**
   - Loads scenarios from YAML
   - Analyzes priority distributions
   - Calculates client-level metrics

3. **compare_scenarios() Function**
   - Orchestrates the comparison
   - Generates reports
   - Saves results to JSON

## Extending the Demo

### Running Full Simulations
To run with the actual STM Routing Simulator:

```bash
# Install simulator requirements
cd /path/to/Simulator_v3
pip install -r requirements_v3.txt

# Run baseline
python main.py /path/to/baseline_scenario.yaml --output results/baseline/

# Run proposed
python main.py /path/to/proposed_scenario.yaml --output results/proposed/

# Compare results
# (Use the simulator's built-in comparison tools)
```

### Additional Metrics to Track
With the full simulator, you can also measure:
- **Time-to-assignment:** How long each request waits before being assigned
- **Agent utilization:** How busy each agent is
- **Throughput:** Total requests processed per hour
- **FOC breach rate:** Percentage of requests that exceed their target

## Mathematical Background

### Priority Score Formula
```
score = age_minutes / (foc_target_days × 24 × 60)
```

**Example:**
- Request is 2 days old (2,880 minutes)
- FOC target = 8.0 days (11,520 minutes)
- Priority score = 2,880 / 11,520 = 0.25

**Same request with reduced FOC target:**
- Request is 2 days old (2,880 minutes)
- FOC target = 5.6 days (8,064 minutes)
- Priority score = 2,880 / 8,064 = 0.357 (**42.9% higher!**)

### Why 30% Reduction?
The demo uses 30% reduction as an example:
- **8.0 days × 0.7 = 5.6 days**
- This is significant enough to show impact
- Not so extreme that it dominates all other requests
- Realistic for a VIP tier differentiation

## Interpretation Guide

### What Does "Good" Look Like?
- **For priority clients:** Should see significant rank improvements
- **For other clients:** Minimal disruption to their service
- **System-wide:** Balanced distribution, no extreme outliers

### Red Flags to Watch For
- **Too aggressive:** Priority clients dominate top 80% of queue
- **Unintended consequences:** Other clients fall below acceptable SLAs
- **System instability:** Wide swings in priority distributions

## Questions & Answers

**Q: Why do only 18/20 requests improve their ranking?**
A: The 2 newest requests (REQ_A001, REQ_B001) are so young that even with a lower FOC target, they don't gain priority over much older requests.

**Q: Does this affect total capacity?**
A: No. The same number of agents process the same number of requests. This only changes the *order* in which requests are processed.

**Q: Can I have more than 2 tiers of FOC targets?**
A: Yes! You can create as many tiers as needed. Common patterns:
- Platinum: 4.0 days
- Gold: 6.0 days  
- Standard: 8.0 days

**Q: What's the optimal FOC target reduction?**
A: It depends on your business goals. Start with 20-30% and measure the impact on service levels for all client segments.

## Next Steps

1. **Review the comparison results** in detail
2. **Adjust FOC targets** in the YAML files based on your requirements
3. **Re-run the comparison** to see updated impacts
4. **Run full simulations** with the actual simulator for complete metrics
5. **Monitor real-world results** if implementing in production

## Support & Documentation

- **Simulator Documentation:** See `/Simulator/Simulator_v3/docs/`
- **YAML Configuration Guide:** See example scenarios in `/Simulator/Simulator_v3/scenarios/`

## Conclusion

This demo clearly shows that reducing the FOC target for specific clients creates a **preferential service tier** that processes their requests faster. The 30% reduction resulted in a **42.9% increase in priority scores** and an average **3.6 position improvement** in the queue for CLIENT_A and CLIENT_B.

Use this analysis to make informed decisions about FOC target adjustments and understand their impact on your request routing system.
