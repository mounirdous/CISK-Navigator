# CISK Navigator v1.11 - User Guide

**New Features Guide**: Smart Value Entry & Target Tracking

---

## 🔄 Smart Value Entry

### What is it?

Smart Value Entry helps you distinguish between two common scenarios when entering KPI data:

1. **Time has evolved** - You're entering a new value for a new time period
2. **Building consensus** - You're adding your perspective to the current period

### When to use which mode?

**Use "NEW data (time evolved)" when:**
- A new month/quarter/sprint has started
- You're updating the value because time has passed
- You want to preserve the old value in history
- You're the only contributor and want a clean slate

**Use "Contributing to CURRENT period" when:**
- Multiple people are providing estimates
- You're adding your perspective to existing data
- Time hasn't moved forward yet
- You want normal consensus calculation

### How it works

#### Scenario 1: First Entry (No Existing Data)
- No modal appears
- Value is simply recorded
- No snapshot created

#### Scenario 2: Updating Existing Value
1. Navigate to KPI cell
2. Enter new value
3. Click "Save Contribution"
4. **Modal appears** with two choices:
   - 🆕 NEW data (time evolved)
   - 📊 Contributing to CURRENT period
5. Select your intent
6. Form auto-submits

**What happens with "NEW data":**
1. System creates automatic snapshot: "Auto: Before update by [your name]"
2. Snapshot captures current consensus value
3. All existing contributions are deleted
4. Your new value is recorded as the only contribution
5. Result: Clean new period with historical preservation

**What happens with "Contributing":**
1. Your value is added to existing contributions
2. Consensus calculation runs (average, median, etc.)
3. Multiple values coexist
4. Consensus status shown (strong/weak/conflict)

### Example Workflow

**Monthly Cost Tracking:**

**March 1:**
- Enter: €10,000
- Mode: (no modal - first entry)
- Result: €10,000 displayed

**April 1:**
- Enter: €9,500
- Mode: Select **"NEW data"**
- What happens:
  - Snapshot created: "Auto: Before update by moun" (value: €10,000)
  - March contributions deleted
  - April value: €9,500
- Result: Chart shows March: €10,000, April: €9,500

**April 15 (colleague adds estimate):**
- Enter: €9,800
- Mode: Select **"Contributing"**
- What happens:
  - Contribution added
  - Consensus: (€9,500 + €9,800) / 2 = €9,650
- Result: April value: €9,650 (2 contributors)

---

## 🎯 Target Tracking

### What is it?

Target Tracking allows you to set goals for your KPIs and visualize progress toward those goals.

### Setting a Target

#### When Creating a KPI:
1. Select value types (e.g., "Cost")
2. Configure colors
3. **Check "Set Target Value"** ✅
4. Enter:
   - Target value (e.g., 5000)
   - Target date (e.g., 2026-12-31)
5. Click "Create KPI"

#### When Editing a KPI:
1. Navigate to "Edit KPI" page
2. Scroll to value type section
3. **Check "Set Target Value"** ✅
4. Enter/update:
   - Target value
   - Target date
5. Click "Save Changes"

### Viewing Progress

#### In Workspace Grid:
- Current value displayed in color
- Below: **🎯 45%** (progress indicator)
- Hover for tooltip: "Target: 5000 by 2026-12-31"

**Progress Calculation:**
```
Progress = (Current Value / Target Value) × 100
```

**Example:**
- Current: €2,250
- Target: €5,000
- Progress: (2,250 / 5,000) × 100 = **45%**

#### On Trend Chart:
- Blue line: Actual values over time
- **Red dashed line**: Target value
- Label: "Target (5000 by 2026-12-31)"
- Visual comparison: trajectory vs goal

### Use Cases

**Cost Reduction Goal:**
- Baseline: €10,000/month
- Target: €5,000/month by Dec 31
- Track: Progress toward 50% cost reduction

**License Growth Goal:**
- Current: 150 licenses
- Target: 500 licenses by Q4
- Track: Progress toward expansion milestone

**CO2 Reduction Goal:**
- Baseline: 1000 tCO2e
- Target: 700 tCO2e by Dec 31
- Track: Progress toward 30% reduction

### Understanding the Chart

**Example Chart with Target:**

```
Value
  ^
5000 |--------------------------------- Target Line (dashed red)
4000 |                            ●
3000 |                   ●
2000 |          ●
1000 | ●
     |________________________________> Time
     Jan    Feb    Mar    Apr
```

**Interpretation:**
- **Above target line**: Exceeding goal (good for revenue, bad for costs)
- **Below target line**: Below goal (bad for revenue, good for costs)
- **Trajectory**: Slope indicates if on track to reach goal

### Advanced: Baseline Snapshots

**Coming Soon**: Reference a specific snapshot as your starting point for measuring progress.

**Example:**
- Baseline (Jan 1): €10,000
- Target (Dec 31): €5,000
- Current (Jun 1): €7,500
- **Progress**: 50% from baseline to target

---

## 📊 Working with Charts

### Viewing KPI History

1. Click any KPI cell in workspace
2. Scroll to "Historical Trend" section
3. Chart displays:
   - Historical snapshots (from "NEW data" entries)
   - Current value (most recent point)
   - Target line (if target is set)

### Chart Features

**Hover Tooltips:**
- Hover over any point
- See: exact value, date, label

**Refresh:**
- Click "Refresh" button
- Reloads latest snapshots and current value

**Responsive:**
- Adapts to screen size
- Mobile-friendly

### Understanding Data Points

**Types of Points:**
1. **Snapshots** (historical):
   - Created automatically with "NEW data" mode
   - Created manually via "Create Snapshot" button
   - Labeled: "Auto: Before update" or custom label

2. **Current Value** (latest):
   - Real-time consensus calculation
   - Label: "Current"
   - Updates as contributions change

3. **Target** (goal):
   - Horizontal dashed line
   - Static reference point
   - Shows where you want to be

---

## 💡 Best Practices

### Smart Value Entry

**Do:**
- ✅ Use "NEW data" at start of each period (month, quarter, sprint)
- ✅ Use "Contributing" when multiple people estimate
- ✅ Let chart build naturally over time

**Don't:**
- ❌ Mix modes randomly (be consistent)
- ❌ Use "NEW data" for every single update
- ❌ Forget to check snapshot history

### Target Tracking

**Do:**
- ✅ Set realistic, achievable targets
- ✅ Include target dates for accountability
- ✅ Review progress regularly
- ✅ Update targets if circumstances change

**Don't:**
- ❌ Set targets without team buy-in
- ❌ Forget to communicate target meaning
- ❌ Treat targets as fixed (adjust if needed)

### General Workflow

**Monthly Cycle Example:**

**End of Month:**
1. Review current KPI values
2. Check progress toward targets
3. Create manual snapshot: "End of Q1" (optional)
4. Export to Excel for reporting

**Start of New Month:**
1. Enter new values
2. Select **"NEW data"** mode
3. Previous month preserved automatically
4. Charts update with new data points

---

## 🆘 Troubleshooting

### Modal doesn't appear
- **Cause**: No existing consensus (first entry)
- **Solution**: Normal - modal only shows when updating existing data

### Chart shows fewer points than expected
- **Cause**: Only snapshots + current value displayed
- **Solution**: Use "NEW data" mode to create more historical points

### Progress percentage seems wrong
- **Check**: Target value entered correctly?
- **Check**: Current value calculation (consensus vs single contribution)
- **Check**: Formula: (current / target) × 100

### Target line not showing on chart
- **Check**: Target value set for this specific value type?
- **Check**: Value type is numeric? (targets only work for numeric types)
- **Check**: Page refreshed after setting target?

---

## 📚 Quick Reference

### Smart Value Entry
| Scenario | Mode to Select | Result |
|----------|---------------|--------|
| New month started | NEW data | Snapshot created, clean slate |
| Adding estimate | Contributing | Added to consensus pool |
| Time evolved | NEW data | Historical preservation |
| Building consensus | Contributing | Multiple values coexist |

### Target Tracking
| Field | Required | Purpose |
|-------|----------|---------|
| Target Value | Yes | Goal to achieve |
| Target Date | Optional | Deadline for goal |
| Baseline Snapshot | Optional | Starting reference point |

### Chart Elements
| Element | Appearance | Meaning |
|---------|-----------|----------|
| Blue line | Solid | Actual values |
| Red line | Dashed | Target value |
| Points | Circles | Data points (hover for details) |
| Label | Text | "Current" or snapshot label |

---

**Questions or Issues?**
- Check [CHANGELOG.md](CHANGELOG.md) for recent changes
- Review [README.md](README.md) for general features
- Submit issues on GitHub repository

**Version**: v1.11.7
**Last Updated**: March 8, 2026
