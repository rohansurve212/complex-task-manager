# Quick Start Guide

## What's in This Demo

This demo assesses the impact of changing FOC targets for specific clients in the STM Routing Simulator.

### Files Included

1. **baseline_scenario.yaml** - All clients have foc_target = 8.0 days
2. **proposed_scenario.yaml** - CLIENT_A & CLIENT_B have foc_target = 5.6 days (30% lower)
3. **compare_foc_impact.py** - Analysis script that compares both scenarios
4. **comparison_results.json** - Detailed analysis results (generated after running)
5. **README.md** - Comprehensive documentation
6. **EXECUTIVE_SUMMARY.md** - Key findings and recommendations
7. **QUICKSTART.md** - This file

## How to Run the Demo

### Prerequisites
```bash
pip install pyyaml
```

### Run the Comparison
```bash
python3 compare_foc_impact.py
```

### Expected Output
The script will display:
1. Overall metrics comparison
2. Client-level breakdown
3. Top 20 requests ranking
4. Rank changes for affected clients
5. Key insights and recommendations

## What You'll Learn

After running the demo, you'll understand:

✅ **Priority Score Impact** - How much the reduction affects urgency (Answer: +42.9%)

✅ **Queue Position Changes** - How many positions clients move up (Answer: +3.6 avg)

✅ **Relative Impact** - How other clients are affected (Answer: -2.4 positions)

✅ **System-Wide Effect** - Overall priority distribution changes (Answer: +15.2%)

## Key Findings at a Glance

| Metric | Value |
|--------|-------|
| CLIENT_A/B Priority Increase | **+42.9%** |
| Average Rank Improvement | **+3.6 positions** |
| Requests That Improved | **18/20 (90%)** |
| Impact on Other Clients | **-2.4 positions** |
| System-Wide Priority Change | **+15.2%** |

## Understanding the Scenario Files

### Baseline (baseline_scenario.yaml)
```yaml
name: Baseline Scenario - Uniform FOC Target
description: All 5 clients have foc_target=8.0 days

agents: 10 agents with various skillsets
requests: 50 total (10 per client)
  - CLIENT_A: 10 requests, foc_target=8.0
  - CLIENT_B: 10 requests, foc_target=8.0
  - CLIENT_C: 10 requests, foc_target=8.0
  - CLIENT_D: 10 requests, foc_target=8.0
  - CLIENT_E: 10 requests, foc_target=8.0
```

### Proposed (proposed_scenario.yaml)
```yaml
name: Proposed Scenario - Lower FOC Target for Client A and B
description: CLIENT_A and CLIENT_B have foc_target=5.6 days (30% lower)

agents: 10 agents (same as baseline)
requests: 50 total (same as baseline)
  - CLIENT_A: 10 requests, foc_target=5.6 ⭐
  - CLIENT_B: 10 requests, foc_target=5.6 ⭐
  - CLIENT_C: 10 requests, foc_target=8.0
  - CLIENT_D: 10 requests, foc_target=8.0
  - CLIENT_E: 10 requests, foc_target=8.0
```

## Customizing the Demo

### Change FOC Target Reduction
Edit `proposed_scenario.yaml` and change all CLIENT_A and CLIENT_B `foc_target` values:

```yaml
# Try 50% reduction (8.0 → 4.0)
foc_target: 4.0

# Try 20% reduction (8.0 → 6.4)  
foc_target: 6.4

# Try 40% reduction (8.0 → 4.8)
foc_target: 4.8
```

Then re-run: `python3 compare_foc_impact.py`

### Add More Clients
1. Copy CLIENT_E requests as template
2. Rename to CLIENT_F, CLIENT_G, etc.
3. Adjust `foc_target` as needed
4. Re-run the comparison

### Test Different Client Combinations
Instead of CLIENT_A and CLIENT_B, try:
- Only CLIENT_A (10 requests)
- CLIENT_A, CLIENT_B, CLIENT_C (30 requests)
- Just 5 specific requests (cherry-pick)

## Reading the Output

### Section 1: Overall Metrics
```
Metric                          Baseline    Proposed    Change
----------------------------------------------------------------------
FOC Compliance Rate                   2.0%        2.0%        +0.0pp
Avg Priority Score                   0.359       0.414        +15.2%
```
**Interpretation:** System-wide average priority increased by 15.2%

### Section 2: Client-Level Comparison
```
Client    FOC Target   Avg Priority Score   Avg Rank
          Base→Prop    Base     Prop    Δ%   Base Prop
-------------------------------------------------------
CLIENT_A     8.0→5.6   0.305  0.436   42.9  28.9 25.4
```
**Interpretation:** CLIENT_A's average priority score increased 42.9%, and their average rank improved from 28.9 to 25.4

### Section 3: Top 20 Requests
```
PROPOSED (Top 20)
Rank  Request     Client    FOC Tgt  Priority Score
------------------------------------------------------
   1  REQ_B010   CLIENT_B    5.6d    1.1161 ⭐
   2  REQ_A010   CLIENT_A    5.6d    1.0714 ⭐
```
**Interpretation:** CLIENT_A and CLIENT_B requests (marked ⭐) now dominate the top of the queue

### Section 4: Rank Changes
```
Request     Client    Baseline Rank  Proposed Rank  Change
------------------------------------------------------------
REQ_A009   CLIENT_A      11             4          +7 ↑
REQ_B009   CLIENT_B       9             3          +6 ↑
```
**Interpretation:** Shows specific position improvements for each affected request

## Next Steps

1. **Review README.md** for comprehensive documentation
2. **Review EXECUTIVE_SUMMARY.md** for business implications
3. **Examine comparison_results.json** for detailed data
4. **Modify scenarios** and re-run to test different configurations
5. **Run full simulations** with the actual simulator for complete metrics

## Common Questions

**Q: How do I run this with the actual simulator?**
A: First, install the full simulator from the GitHub repository, then:
```bash
cd /path/to/Simulator_v3
python main.py /path/to/baseline_scenario.yaml --output results/baseline/
python main.py /path/to/proposed_scenario.yaml --output results/proposed/
```

**Q: Can I test different FOC target values?**
A: Yes! Edit the `foc_target` values in `proposed_scenario.yaml` and re-run the comparison.

**Q: What if I want to prioritize different clients?**
A: Edit `proposed_scenario.yaml` and change the `foc_target` for whichever clients you want to prioritize.

**Q: Does this demo run the full simulation?**
A: No, this is a simplified analysis that calculates priority scores and rankings. For full simulation including agent assignments and time progression, use the actual simulator.

**Q: What's the optimal FOC target reduction?**
A: It depends on your business goals. The demo uses 30% as an example. Try different values:
- Conservative: 10-20% (smaller impact)
- Moderate: 25-35% (balanced)  
- Aggressive: 40-50% (strong differentiation)

## Troubleshooting

### Error: "No module named 'yaml'"
```bash
pip install pyyaml
```

### Error: "File not found"
Make sure you're in the correct directory:
```bash
cd /Simulator/Simulator_v3/simulator_demo
ls  # Should show baseline_scenario.yaml, proposed_scenario.yaml, etc.
```

### Output looks different
Make sure you have the correct Python version:
```bash
python3 --version  # Should be 3.7+
```

## Support

- **Full Documentation:** See README.md
- **Business Analysis:** See EXECUTIVE_SUMMARY.md

## Summary

This demo provides a clear, quantitative analysis of how reducing FOC targets for specific clients affects request prioritization. The key finding is that a **30% FOC target reduction results in a 42.9% priority increase** and **3.6 position average improvement** in the queue.

**Ready to go?**
```bash
python3 compare_foc_impact.py
```

Enjoy the demo! 🚀
