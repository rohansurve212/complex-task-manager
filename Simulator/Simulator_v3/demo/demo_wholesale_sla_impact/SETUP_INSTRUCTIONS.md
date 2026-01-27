# Wholesale SLA Impact Demo - Setup Instructions

## ✅ Files Created and Ready

### 1. Scenario Files (Complete - 500 requests)
- `scenarios/baseline_scenario.yaml` - All customers foc_target=8.0, has_sla=False
- `scenarios/proposed_scenario.yaml` - 7 SLA customers (foc_target=1.0, has_sla=True), 6 non-SLA (foc_target=8.0, has_sla=False)

### 2. Analysis Tool (Complete)
- `compare_foc_impact.py` - Quick priority analysis (runs in <1 second)

### 3. Scenario Generator (Complete)
- `generate_scenarios.py` - Regenerate scenarios if needed

## 📋 What You Need to Do

### Step 1: Copy to Your Repository
Copy this entire folder to:
```
Simulator/Simulator_v3/demo/demo_wholesale_sla_impact/
```

### Step 2: Run Quick Analysis
```bash
cd Simulator_v3/demo/demo_wholesale_sla_impact
python compare_foc_impact.py
```

This will show you the priority impact immediately (<1 second).

### Step 3: Run Full Simulation
You have TWO options:

#### Option A: Use Simulator Directly (Recommended)
```bash
cd Simulator_v3

# Run baseline
python main.py demo/demo_wholesale_sla_impact/scenarios/baseline_scenario.yaml --output demo/demo_wholesale_sla_impact/output/baseline/

# Run proposed
python main.py demo/demo_wholesale_sla_impact/scenarios/proposed_scenario.yaml --output demo/demo_wholesale_sla_impact/output/proposed/
```

#### Option B: Create run_full_simulation.py Wrapper
Copy and adapt from `demo/demo_foc_impact_analysis/run_full_simulation.py`

Update these values:
```python
BASELINE_SCENARIO = "demo/demo_wholesale_sla_impact/scenarios/baseline_scenario.yaml"
PROPOSED_SCENARIO = "demo/demo_wholesale_sla_impact/scenarios/proposed_scenario.yaml"
OUTPUT_DIR = "demo/demo_wholesale_sla_impact/output"
```

## 🎯 Key Differences from Previous Demo

| Aspect | Previous Demo | This Demo |
|--------|---------------|-----------|
| Customers | 5 | 13 |
| Requests | 50 | 500 |
| FOC Change | 8.0 → 5.6 days (30%) | 8.0 → 1.0 day (87.5%) |
| Priority Impact | +42.9% | +700% (8x) |
| has_sla field | Not used | Critical! |

## ⚠️ Expected Results

**This is MUCH more dramatic than the previous demo!**

### Priority Score Math:
```
Request age: 10 days

Baseline (foc_target=8.0):
  Priority = 10 / 8 = 1.25

Proposed SLA (foc_target=1.0):
  Priority = 10 / 1 = 10.0
  
Increase: 8x (700%)!
```

### Queue Impact:
- **Top 200 positions:** Likely ALL SLA requests
- **SLA customers:** Get processed immediately
- **Non-SLA customers:** Face massive delays

### Business Considerations:
1. **Is this acceptable?** 700% priority increase is EXTREME
2. **Alternative:** Try 3-4 days for SLA vs 8 days for non-SLA
3. **Monitor:** Non-SLA service levels may be unacceptable

## 📄 Optional: Create Additional Files

If you want a complete demo package like `demo_foc_impact_analysis`, create:

1. **README.md** - Full documentation
2. **QUICKSTART.md** - 5-minute guide  
3. **EXECUTIVE_SUMMARY.md** - Business summary
4. **run_full_simulation.py** - Simulation wrapper with pretty output

You can adapt these from `demo/demo_foc_impact_analysis/` by:
- Changing customer names (CLIENT_A → CUST_A, etc.)
- Updating request counts (50 → 500)
- Updating FOC values (5.6 → 1.0)
- Adding SLA-specific analysis

## 🚀 Quick Start (TL;DR)

```bash
# 1. Copy folder to your repo
cp -r demo_wholesale_sla_impact Simulator_v3/demo/

# 2. Run quick analysis
cd Simulator_v3/demo/demo_wholesale_sla_impact
python compare_foc_impact.py

# 3. Run full simulation
cd Simulator_v3
python main.py demo/demo_wholesale_sla_impact/scenarios/baseline_scenario.yaml --output demo/demo_wholesale_sla_impact/output/baseline/
python main.py demo/demo_wholesale_sla_impact/scenarios/proposed_scenario.yaml --output demo/demo_wholesale_sla_impact/output/proposed/

# 4. Review results
ls demo/demo_wholesale_sla_impact/output/
```

## ❓ Questions?

- **Regenerate scenarios?** Run `python generate_scenarios.py`
- **Change FOC targets?** Edit `generate_scenarios.py` and regenerate
- **Need help?** Check `demo/demo_foc_impact_analysis/` for complete example

## 📊 What You'll Learn

After running both analyses, you'll know:

1. **Priority Impact:** How much SLA assignment affects urgency
2. **Queue Position:** Where SLA vs non-SLA requests rank
3. **Service Levels:** Real wait times for each customer tier
4. **Capacity:** Whether 10 agents can handle the workload
5. **Trade-offs:** Impact on non-SLA customer experience

Good luck with your analysis! 🎉
