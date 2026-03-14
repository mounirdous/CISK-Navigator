# Snapshot Pivot Analysis

## Overview

The Snapshot Pivot Analysis feature provides time-series analysis and visualization of KPI snapshots across multiple time dimensions (daily, monthly, quarterly, yearly).

## Key Features

### 1. Multiple Time Dimensions
- **Daily**: Shows each unique snapshot date as a column
- **Monthly**: Aggregates snapshots by month
- **Quarterly**: Groups snapshots by fiscal quarter (Q1-Q4)
- **Yearly**: Rolls up snapshots by year

### 2. Data Deduplication Logic
When multiple snapshots exist for the same period (especially important for daily view):
- **Primary Sort**: `snapshot_date DESC` - Most recent date first
- **Secondary Sort**: `created_at DESC` - Latest creation timestamp first
- **Selection**: Only the first (most recent) snapshot per period is used

**Example**: If 3 snapshots exist on 2026-03-14:
- Snapshot A: created at 09:00 AM
- Snapshot B: created at 02:00 PM
- Snapshot C: created at 05:00 PM

The system will use **Snapshot C** (latest by created_at).

### 3. Filtering Capabilities
- **Space Filter**: Filter by specific organizational space
- **Challenge Filter**: Filter by specific challenge (automatically filtered by selected space)
- **Value Type Filter**: Show only specific value types (Cost, CO2, Risk, etc.)
- **Time Range**:
  - Simple mode: Select year start/end with quarter/month selection
  - Custom mode: Precise date range with start/end month-year

### 4. Display Options
- **Show Targets**: Display target values alongside actual values
- **Show Status**: Show consensus status indicators (Strong/Medium/Weak/None)

## Architecture

### Files and Components

#### Service Layer
**File**: `app/services/snapshot_pivot_service.py`
- **Class**: `SnapshotPivotService`
- **Key Methods**:
  - `get_available_years(organization_id)`: Returns list of years with snapshot data
  - `get_pivot_data(...)`: Main method that builds pivot table structure
  - `get_chart_data(...)`: Formats data for Chart.js visualization
  - `_month_name(month)`: Helper to convert month number to name

#### Route Layer
**File**: `app/routes/workspace.py`
- **Route**: `/snapshots/pivot` (GET)
- **Function**: `snapshot_pivot()`
- **Responsibilities**:
  - Parse filter parameters from request
  - Call service layer to get pivot data
  - Load entity defaults for branding
  - Render template with data

#### Template Layer
**File**: `app/templates/workspace/snapshot_pivot.html`
- **Purpose**: Renders pivot table UI with filters and data grid
- **Components**:
  - Filter form (view type, space, challenge, value type, time range)
  - Pivot table grid (KPIs as rows, time periods as columns)
  - Export to Excel button
  - Chart visualization section

### Data Model

#### Primary Tables

**KPISnapshot**
```python
class KPISnapshot(db.Model):
    id = Column(Integer, primary_key=True)
    kpi_value_type_config_id = Column(Integer, ForeignKey('kpi_value_type_config.id'))
    snapshot_date = Column(Date, nullable=False)  # The business date
    created_at = Column(DateTime, default=datetime.utcnow)  # When snapshot was created
    year = Column(Integer)  # Extracted from snapshot_date
    quarter = Column(Integer)  # 1-4, calculated from month
    month = Column(Integer)  # 1-12, extracted from snapshot_date
    consensus_status = Column(String(50))  # 'strong', 'medium', 'weak', 'none'
    # ... value fields (numeric_value, text_value, etc.)
```

**KPIValueTypeConfig**
```python
class KPIValueTypeConfig(db.Model):
    id = Column(Integer, primary_key=True)
    kpi_id = Column(Integer, ForeignKey('kpi.id'))
    value_type_id = Column(Integer, ForeignKey('value_type.id'))
    target_value = Column(Numeric(12, 2))  # Optional target
    target_direction = Column(String(20))  # 'maximize', 'minimize', 'exact'
    target_tolerance_pct = Column(Numeric(5, 2))  # For 'exact' targets
    target_date = Column(Date)  # When target should be achieved
```

#### Query Structure

The pivot data query joins:
1. `KPISnapshot` - The snapshot records
2. `KPIValueTypeConfig` - Links KPI to value type with config
3. `KPI` - The KPI being measured
4. `ValueType` - The measurement type (Cost, CO2, etc.)
5. `InitiativeSystemLink` - Links KPI to initiative
6. `Initiative` - The initiative (for org_id filter)
7. `ChallengeInitiativeLink` (optional) - For space/challenge filtering
8. `Challenge` (optional) - For space/challenge filtering

**Sorting**: `ORDER BY snapshot_date DESC, created_at DESC`

This ensures:
- Most recent dates appear first
- Within same date, newest snapshot (by creation time) appears first
- First occurrence wins when building period buckets

### Data Flow

1. **User Request**: User selects filters and view type in UI
2. **Route Handler**: `snapshot_pivot()` parses parameters
3. **Service Call**: `SnapshotPivotService.get_pivot_data()` executes query
4. **Data Processing**:
   - Query returns snapshots ordered by date/time DESC
   - Period labels generated (daily: "2026-03-14", monthly: "March 2026", etc.)
   - Snapshots grouped by KPI config ID
   - For each period, first snapshot encountered is used (due to DESC ordering)
5. **Template Render**: Pivot table displayed with KPIs as rows, periods as columns

## Usage Examples

### Daily View - Latest Snapshot Per Day
```
View Type: Daily
Date Range: 2026-03-01 to 2026-03-31

Result:
KPI Name        | 2026-03-01 | 2026-03-02 | 2026-03-03 | ...
----------------|------------|------------|------------|----
Energy Cost     | 1200.50    | 1185.25    | 1190.00    | ...
CO2 Emissions   | 45.2       | 44.8       | 45.1       | ...

If 3 snapshots exist on 2026-03-01 at 9am, 2pm, 5pm:
→ The 5pm snapshot is used (latest by created_at)
```

### Monthly View with Targets
```
View Type: Monthly
Year: 2026
Show Targets: ON

Result:
KPI Name        | Target | Jan 2026 | Feb 2026 | Mar 2026 | Status
----------------|--------|----------|----------|----------|--------
Energy Cost     | 1000   | 1200     | 1150     | 1100     | 🎯 90%
```

## Export Functionality

**Route**: `/snapshots/pivot/export`
**Format**: Excel (.xlsx)
**Contents**:
- Pivot table data
- Formatting preserved
- Target values included if enabled

## Future Enhancements

- [ ] Add daily view preset date ranges (Last 7 days, Last 30 days, etc.)
- [ ] Add trend indicators (↑↓) for daily view
- [ ] Support multiple snapshot comparison on same day
- [ ] Add annotation/comment display in pivot cells
- [ ] Export to CSV format
- [ ] Scheduled pivot reports via email

## Related Documentation

- [Snapshot Service Documentation](./SNAPSHOT_SERVICE.md) (if exists)
- [Data Dictionary](./DATA-DICTIONARY.md)
- [Architecture Overview](./ARCHITECTURE.md)
