# STM Routing Simulator v3.0 - 8-Hour Shift Demo

## Quick Start

### Prerequisites
- Python 3.9+
- STM Simulator v3.0 installed

### Running the Demo
```bash
# From the simulator root directory
cd demo
python demo_8hour_shift.py
```

## What the Demo Shows

### 1. Team Setup
- 6 agents total
- 5 agents working (Alice, Bob, Carol, Dave, Eve)
- 1 agent absent (Frank - on vacation)

### 2. Request Backlog
- 31 total requests
- 23 new CMO requests
- 8 followup requests (5 for present agents, 3 for Frank)
- All 5 priority levels represented

### 3. Simulation Progression
- Real-time visualization of 8-hour shift
- Hourly assignment breakdown
- Agent workload tracking
- Priority request handling

### 4. Key Behaviors Demonstrated

#### Priority Handling
- **Priority 1 (Highest)**: Winback + Escalated customers processed first
- **Priority 5 (Lowest)**: Common requests processed last

#### Absent Agent Handling
- Frank's 3 followup requests redistributed as CMO
- Other agents with matching skills pick up the work
- System marks these as "from absent agent"

#### Followup vs CMO Routing
- **During followup windows** (10-11:30 AM, 3:30-4 PM EST):
  - Agents prioritize their own followups
  - Then take CMO work if available
- **Outside followup windows**:
  - Agents prioritize CMO work
  - Then take their own followups

### 5. Generated Reports

After the demo completes, check `demo/output/` for:
- `shift_results.json` - Complete simulation data
- `assignments.csv` - Assignment details (Excel-friendly)
- `shift_timeline.txt` - Chronological event log

## Customizing the Demo

### Change Demo Speed

Edit `demo_8hour_shift.py`:
```python
DEMO_SPEED = "fast"   # Quick demo (30 seconds)
DEMO_SPEED = "normal" # Standard demo (2-3 minutes)
DEMO_SPEED = "slow"   # Detailed demo (5 minutes)
```

### Modify the Scenario

Edit `scenarios/morning_shift_demo.yaml`:

- Add/remove agents
- Change agent availability (is_absent flag)
- Add/remove requests
- Adjust priorities (is_escalated, is_winback flags)
- Change FOC targets

### Run with Different Data
```bash
# Create your own scenario
cp scenarios/morning_shift_demo.yaml scenarios/my_scenario.yaml

# Edit my_scenario.yaml with your data

# Run the demo
python demo_8hour_shift.py
# (Update SCENARIO_FILE variable in script)
```

## Expected Output

### Console Output
- Colored, formatted progress through simulation
- Real-time statistics
- Visual charts and bars
- Step-by-step narration

### Performance Metrics
- ~30-35 assignments in 8 hours (realistic rate)
- 100% of high-priority requests completed
- Balanced workload across agents
- ~95% routing success rate

## Troubleshooting

### Demo Won't Start
```bash
# Ensure you're in the correct directory
cd demo

# Check Python path
python --version  # Should be 3.9+

# Verify simulator installation
cd ..
python -m pytest tests/ -v
```

### Missing Output Directory
The demo creates `demo/output/` automatically.
If it fails, create it manually:
```bash
mkdir -p demo/output
```

### Scenario Not Found
Ensure `scenarios/morning_shift_demo.yaml` exists:
```bash
ls scenarios/morning_shift_demo.yaml
```

## Next Steps

1. **Review the Reports**: Open files in `demo/output/`
2. **Modify the Scenario**: Try different agent counts, priorities
3. **Run Custom Data**: Import your production data
4. **Analyze Results**: Use CSV in Excel for custom analysis

## Questions?

- Documentation: See main README.md
- Issues: GitHub Issues page
- Team: Contact simulator development team