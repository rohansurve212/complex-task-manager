# Executive Summary: FOC Target Impact Analysis

## Objective
Assess the impact of reducing `foc_target` by 30% (from 8.0 to 5.6 days) for 2 clients out of 5 total clients.

## Methodology
- **Baseline Scenario:** All 5 clients have foc_target = 8.0 days (50 requests total)
- **Proposed Scenario:** CLIENT_A and CLIENT_B have foc_target = 5.6 days; others remain at 8.0 days
- **Analysis:** Priority score calculation, request ranking, and metric comparison

---

## Key Findings

### 1. Priority Score Impact
| Metric | Baseline | Proposed | Change |
|--------|----------|----------|--------|
| CLIENT_A Avg Priority Score | 0.305 | 0.436 | **+42.9%** |
| CLIENT_B Avg Priority Score | 0.333 | 0.476 | **+42.9%** |
| Overall Avg Priority Score | 0.359 | 0.414 | **+15.2%** |

**Interpretation:** The 30% reduction in FOC target translates to a 42.9% increase in priority scores for affected clients. This is mathematically expected since priority is inversely proportional to FOC target.

### 2. Request Ranking Impact
- **18 out of 20** affected requests improved their position in the queue
- **Average improvement:** 3.6 positions per request
- **Total positions gained:** 73 across all CLIENT_A and CLIENT_B requests

**Top Improvements:**
- REQ_A009: Moved from rank 11 → 4 (+7 positions)
- REQ_B009: Moved from rank 9 → 3 (+6 positions)
- REQ_A008: Moved from rank 16 → 11 (+5 positions)
- REQ_B008: Moved from rank 14 → 9 (+5 positions)

### 3. Top 20 Queue Composition
**Baseline:** Even distribution across all clients based purely on request age

**Proposed:** CLIENT_A and CLIENT_B dominate the top positions:
- **8 out of top 20 positions** (40%) are CLIENT_A/B requests
- Previously, they had **4 out of top 20 positions** (20%)
- **2x representation** in high-priority queue

### 4. Impact on Other Clients
| Client | FOC Target | Avg Rank (Baseline) | Avg Rank (Proposed) | Change |
|--------|------------|---------------------|---------------------|--------|
| CLIENT_C | 8.0 | 25.5 | 27.9 | -2.4 ↓ |
| CLIENT_D | 8.0 | 24.0 | 26.2 | -2.2 ↓ |
| CLIENT_E | 8.0 | 22.1 | 24.8 | -2.7 ↓ |

**Interpretation:** Other clients experienced an average **2.4 position drop** in the queue to accommodate the prioritization of CLIENT_A and CLIENT_B.

---

## Business Implications

### ✅ Advantages
1. **Differentiated Service Levels**
   - Creates a clear VIP tier for strategic clients
   - Measurable improvement in service speed (42.9% more urgent)

2. **SLA Compliance**
   - Can be used to meet contractual obligations
   - Reduces risk of breaching FOC targets for critical clients

3. **Flexible Prioritization**
   - Can adjust targets temporarily during high-demand periods
   - Scalable to multiple tiers (Platinum, Gold, Standard)

### ⚠️ Considerations
1. **Impact on Standard Clients**
   - 2.4 position average drop may translate to longer wait times
   - Need to monitor if this affects their FOC compliance

2. **System Capacity**
   - Does not increase total throughput
   - Zero-sum game: faster service for some means slower for others

3. **Fairness Perception**
   - Creates two-tier system
   - May need clear communication about service levels

---

## Recommendations

### Immediate Actions
1. **✓ Proceed with Implementation**
   - The 30% reduction provides meaningful prioritization
   - Impact on other clients is moderate and manageable

2. **Monitor Key Metrics**
   - Track FOC compliance rates for all client tiers
   - Measure actual time-to-assignment changes
   - Watch for any deterioration in CLIENT_C/D/E service levels

### Medium-Term Considerations
1. **Establish Multiple Tiers**
   - Consider 3-tier structure: VIP (5.6d), Priority (7.0d), Standard (8.0d)
   - Or 2-tier: Premium (6.0d), Standard (8.0d)

2. **Dynamic Adjustment**
   - Implement rules to adjust FOC targets based on:
     - Time of day / day of week
     - Current backlog size
     - Historical processing times

3. **Capacity Planning**
   - If CLIENT_C/D/E service degrades significantly:
     - Consider adding agent capacity
     - Or limit CLIENT_A/B request volume

### Long-Term Strategy
1. **Data-Driven Optimization**
   - Run A/B tests with different FOC target reductions
   - Find optimal balance between VIP service and standard service
   - Use machine learning to predict optimal targets

2. **Business Alignment**
   - Tie FOC targets to customer lifetime value (CLV)
   - Align with contract terms and SLAs
   - Create transparent service level agreements

---

## Quantified Impact Summary

### For CLIENT_A and CLIENT_B (Affected Clients)
- **Priority Score:** +42.9% increase
- **Queue Position:** +3.6 average improvement
- **Top-20 Representation:** 2x increase (20% → 40%)
- **Requests Improved:** 90% (18/20)

### For CLIENT_C, CLIENT_D, CLIENT_E (Unchanged Clients)
- **Priority Score:** No change (0.0%)
- **Queue Position:** -2.4 average decline
- **Relative Service Level:** Lower priority vs. CLIENT_A/B
- **Expected Impact:** Slightly longer wait times

### System-Wide
- **Avg Priority Score:** +15.2%
- **Priority Distribution:** More concentrated at top
- **FOC Compliance:** Unchanged (2.0%)
- **Total Capacity:** No change

---

## Conclusion

Reducing the FOC target by 30% for CLIENT_A and CLIENT_B successfully creates a **meaningful service differentiation** with **manageable impact** on other clients. The 42.9% increase in priority scores translates to an average 3.6 position improvement in the queue.

**Recommended Next Steps:**
1. ✅ **Approve** the FOC target reduction for CLIENT_A and CLIENT_B
2. 📊 **Monitor** service levels for all client tiers for 30 days
3. 🔄 **Adjust** if needed based on actual performance data
4. 📈 **Scale** to additional client tiers if successful

---

## Appendix: Calculation Example

### Why Does 30% Reduction = 42.9% Priority Increase?

**Formula:** Priority Score = Age / FOC_Target

**Example:** Request that is 3 days old

**Baseline:**
- Age: 3 days = 4,320 minutes
- FOC Target: 8.0 days = 11,520 minutes  
- **Priority Score: 4,320 / 11,520 = 0.375**

**Proposed:**
- Age: 3 days = 4,320 minutes
- FOC Target: 5.6 days = 8,064 minutes
- **Priority Score: 4,320 / 8,064 = 0.536**

**Change:** 0.536 / 0.375 = 1.429 = **+42.9%**

This is because priority is **inversely proportional** to FOC target:
- 30% reduction in FOC target
- = Division by 0.7 instead of 1.0
- = 1 / 0.7 = 1.429
- = **+42.9% increase in priority**

---

**Report Generated:** January 22, 2026  
**Analysis Tool:** FOC Target Impact Comparison Demo  
**Scenarios Compared:** Baseline vs. Proposed (30% FOC reduction for 2/5 clients)
