# Queue Position Analysis Feature

## Overview

The `compare_foc_impact.py` script now includes a **comprehensive queue position change analysis** that quantifies exactly how much SLA customers improve their position and how much non-SLA customers deteriorate.

This answers the critical business question: **"By how many positions do SLA customers jump ahead, and how far back do non-SLA customers fall?"**

---

## New Analysis Section

### Step 8: Queue Position Changes Analysis

This new section (inserted between Top 30 Rankings and Key Insights) provides:

1. **SLA Customer Position Improvements**
2. **Non-SLA Customer Position Deteriorations**
3. **Statistical Analysis** (mean, median, min, max, std dev)
4. **Percentile Distribution** (top 100, top 200, top 300)
5. **Example Cases** (biggest improvements and deteriorations)
6. **Overall Impact Summary** (position gap calculation)

---

## Metrics Calculated

### For SLA Customers (CUST_A through CUST_G):

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| **Average Position Improvement** | Mean rank change (baseline - proposed) | How many positions SLA customers move up on average |
| **Median Position Improvement** | Median rank change | Middle value (less affected by outliers) |
| **Best Improvement** | Maximum rank change | Best case scenario |
| **Worst Improvement** | Minimum rank change | Worst case scenario (still positive) |
| **Standard Deviation** | Spread of rank changes | Consistency of improvement |
| **Top 100/200/300** | Count in top positions | How many reach elite positions |

### For Non-SLA Customers (CUST_H through CUST_M):

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| **Average Position Deterioration** | Mean rank change (negative value) | How many positions non-SLA customers drop on average |
| **Median Position Deterioration** | Median rank change | Middle value deterioration |
| **Best Case** | Maximum rank change (least negative) | Best case (smallest drop) |
| **Worst Case** | Minimum rank change (most negative) | Worst case (largest drop) |
| **Standard Deviation** | Spread of rank changes | Consistency of deterioration |
| **Dropped from Top X** | Count pushed out of elite positions | How many lose premium positions |

### Overall Impact:

| Metric | Formula | Meaning |
|--------|---------|---------|
| **Position Gap** | SLA avg improvement - Non-SLA avg deterioration | Net advantage for SLA customers |

---

## Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 8: Queue Position Changes Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
  Standard Deviation: 38.7 positions

  Position Distribution:
    Dropped from Top 100: 55 requests
    Dropped from Top 200: 130 requests
    Dropped from Top 300: 85 requests

Examples of Biggest Changes:

Top 5 SLA Position Improvements:
  Request            Customer    Baseline   Proposed   Change    
  ────────────────────────────────────────────────────────────
  REQ_CUST_A_025     CUST_A      #450       #100       +350
  REQ_CUST_B_028     CUST_B      #445       #98        +347
  REQ_CUST_C_030     CUST_C      #440       #95        +345
  REQ_CUST_D_027     CUST_D      #435       #92        +343
  REQ_CUST_E_029     CUST_E      #430       #88        +342

Top 5 Non-SLA Position Deteriorations:
  Request            Customer    Baseline   Proposed   Change    
  ────────────────────────────────────────────────────────────
  REQ_CUST_H_003     CUST_H      #50        #330       -280
  REQ_CUST_I_005     CUST_I      #55        #328       -273
  REQ_CUST_J_007     CUST_J      #60        #325       -265
  REQ_CUST_K_004     CUST_K      #52        #315       -263
  REQ_CUST_L_006     CUST_L      #58        #318       -260

Overall Impact:
  Average position gap between SLA and non-SLA: 363 positions
  SLA customers improve by 218 positions on average
  Non-SLA customers drop by 145 positions on average
  Net effect: 363-position advantage for SLA customers
```

---

## How Position Change is Calculated

### Formula:
```
Position Change = Baseline Rank - Proposed Rank
```

### Interpretation:
- **Positive value** = Improvement (moved up in queue)
- **Negative value** = Deterioration (moved down in queue)
- **Zero** = No change

### Example:
```
Request: REQ_CUST_A_010
Baseline Rank: 250
Proposed Rank: 45
Position Change: 250 - 45 = +205 (improved by 205 positions)
```

---

## Why This Matters

### Business Decision Support:

**Question:** "How much will SLA customers actually benefit?"
**Answer:** "They improve by an average of 218 positions in the queue"

**Question:** "How much will non-SLA customers suffer?"
**Answer:** "They drop by an average of 145 positions in the queue"

**Question:** "What's the net gap?"
**Answer:** "A 363-position advantage for SLA customers"

### Stakeholder Communication:

Instead of saying:
> "SLA customers will get higher priority"

You can now say:
> "SLA customers will move up 218 positions on average, gaining a 363-position advantage over non-SLA customers"

This is **concrete, quantifiable, and actionable**.

---

## Updated Key Insights Section

The Key Insights section (Step 9) now includes position change data:

**Before:**
```
2. Queue Domination
   • Top 30 positions: 27/30 (90%) are SLA requests
   • Top 50 positions: 45/50 (90%) are SLA requests
```

**After:**
```
2. Queue Position Changes
   • SLA customers improve by +218 positions on average
   • Non-SLA customers drop by -145 positions on average
   • Position gap: 363 positions
   • 195/200 SLA requests moved to top 200 positions

3. Queue Domination
   • Top 30 positions: 27/30 (90%) are SLA requests
   • Top 50 positions: 45/50 (90%) are SLA requests
```

---

## JSON Output Updated

The `comparison_results_quick.json` file now includes:

```json
{
  "comparison": {
    "overall_metrics_change": { ... },
    "rank_changes": {
      "sla_avg_improvement": 218.3,
      "non_sla_avg_deterioration": -145.2,
      "position_gap": 363.5,
      "sla_to_top_200": 195
    }
  }
}
```

This data can be used for:
- Custom reporting
- Charts and visualizations
- Further analysis
- Stakeholder presentations

---

## Usage

No changes to how you run the script:

```bash
cd Simulator_v3/demo/demo_wholesale_sla_impact
python compare_foc_impact.py
```

The new queue position analysis is automatically included in the output!

---

## Interpreting Results

### High Position Gap (300+):
- **Interpretation:** Very strong two-tier system
- **Implication:** Significant service differentiation
- **Risk:** Non-SLA customer dissatisfaction

### Medium Position Gap (150-300):
- **Interpretation:** Moderate two-tier system
- **Implication:** Noticeable but manageable difference
- **Risk:** Moderate customer impact

### Low Position Gap (< 150):
- **Interpretation:** Subtle differentiation
- **Implication:** Modest priority advantage
- **Risk:** SLA value proposition may be weak

### SLA Improvement vs Non-SLA Deterioration:

If SLA improvement >> Non-SLA deterioration:
- **Good:** SLA customers gain significantly
- **Good:** Non-SLA impact is limited
- **Example:** +300 SLA, -100 Non-SLA

If SLA improvement ≈ Non-SLA deterioration:
- **Balanced:** Both sides affected equally
- **Neutral:** Zero-sum game
- **Example:** +200 SLA, -200 Non-SLA

If SLA improvement < Non-SLA deterioration:
- **Concerning:** Non-SLA suffers more than SLA gains
- **Check:** May indicate capacity issues
- **Example:** +150 SLA, -250 Non-SLA (unusual)

---

## Advanced Usage: Testing Different FOC Targets

Want to see how position changes vary with different FOC targets?

### Test 3-day FOC (instead of 1-day):

```python
# In generate_scenarios.py
foc_target=3.0  # Instead of 1.0
```

**Expected position gap:**
- 1-day FOC: ~360 positions (8x priority)
- 3-day FOC: ~180 positions (2.67x priority)
- 4-day FOC: ~120 positions (2x priority)

### Compare Multiple Scenarios:

```bash
# Test 1-day FOC
python generate_scenarios.py  # with foc_target=1.0
python compare_foc_impact.py
# Note position gap: ~360

# Test 3-day FOC  
# Edit generate_scenarios.py: foc_target=3.0
python generate_scenarios.py
python compare_foc_impact.py
# Note position gap: ~180

# Test 4-day FOC
# Edit generate_scenarios.py: foc_target=4.0
python generate_scenarios.py
python compare_foc_impact.py
# Note position gap: ~120
```

**Conclusion:** Choose FOC target that produces acceptable position gap!

---

## Summary

✅ **New Metrics:** Position improvement/deterioration quantified
✅ **Statistical Analysis:** Mean, median, min, max, std dev
✅ **Percentile Tracking:** Top 100/200/300 distribution
✅ **Example Cases:** Biggest changes highlighted
✅ **Overall Impact:** Position gap calculation
✅ **JSON Export:** Data available for further analysis
✅ **Actionable Insights:** Clear business implications

**Bottom Line:** You now have precise, quantifiable data on how SLA assignments affect queue positions for both customer tiers!

---

## Questions?

**Q: Why are position changes important?**
A: They translate abstract "priority scores" into concrete queue movements that business stakeholders can understand.

**Q: What's a "good" position gap?**
A: Depends on business goals. 100-200 positions = moderate differentiation, 200-400 = strong differentiation, 400+ = extreme differentiation.

**Q: Can I export this data?**
A: Yes! Check `output/comparison_results_quick.json` for all metrics in JSON format.

**Q: How does this relate to wait time?**
A: Position in queue correlates with wait time. Higher position = processed sooner = lower wait time. For actual wait times, run `run_full_simulation.py`.

---

**Happy analyzing! 📊**