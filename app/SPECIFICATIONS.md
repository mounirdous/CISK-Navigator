# CISK Navigator - Functional Specifications

**Version 2.1.0**
**Date: March 7, 2026**

## Table of Contents

1. [Overview](#overview)
2. [User Roles](#user-roles)
3. [Core Features](#core-features)
4. [Hierarchical Data Model](#hierarchical-data-model)
5. [Authentication & Access Control](#authentication--access-control)
6. [Dashboard](#dashboard)
7. [Workspace & Tree/Grid Navigation](#workspace--treegrid-navigation)
8. [Data Entry & Consensus Model](#data-entry--consensus-model)
9. [Value Types](#value-types)
10. [Roll-up Aggregation](#roll-up-aggregation)
11. [Time-Series Tracking](#time-series-tracking)
12. [Comments & Collaboration](#comments--collaboration)
13. [Charts & Visualization](#charts--visualization)
14. [Administration Features](#administration-features)

## Overview

CISK Navigator is a web-based collaborative data collection and aggregation system for tracking KPIs across a hierarchical organization structure. It enables teams to:

- Define organizational hierarchies (Spaces → Challenges → Initiatives → Systems → KPIs)
- Collect data from multiple contributors for each KPI
- Calculate consensus automatically based on contributions
- Roll up aggregated values through the hierarchy
- Support multiple value types (numeric, risk, impact)
- Manage everything through a user-friendly web interface

**Key Design Principles:**
- **Consensus-driven**: Multiple contributors provide input, system calculates consensus
- **Hierarchical aggregation**: Values roll up from KPIs → Systems → Initiatives → Challenges → Spaces
- **Flexible reusability**: Initiatives can address multiple challenges, systems can support multiple initiatives
- **Context-specific KPIs**: KPIs belong to initiative-system pairs, not master systems
- **Organization isolation**: Each organization has completely separate data

## What's New in v1.19 (March 2026)

### Three Calculation Types
**Revolutionary expansion of how KPI values are determined:**

1. **Manual Entry** (traditional contribution-based consensus)
   - Multiple contributors provide values
   - System calculates consensus automatically
   - Perfect for collaborative data collection

2. **Linked KPI** (cross-organizational data sharing)
   - Pull values from another organization's KPI
   - Auto-sync when source changes
   - Enables shared services and dependencies

3. **Formula Calculation** (automatic computation)
   - **Simple Mode**: Basic operations (sum, avg, min, max, multiply, subtract)
   - **Advanced Mode**: Full Python expressions with functions
   - Auto-updates when source KPIs change

### Advanced Formula Engine
**Powerful Python expression support:**
- Mathematical operators: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- Functions: `abs()`, `round()`, `max()`, `min()`, `sum()`
- Click-to-insert variable badges
- Real-time preview with current values
- Comprehensive in-app help documentation with examples

**Real-World Use Cases:**
```python
# Percentage calculation
round((kpi_actual / kpi_target) * 100, 1)

# ROI calculation
round((kpi_revenue - kpi_cost) / kpi_cost * 100)

# Weighted average
(kpi_1 * 0.7 + kpi_2 * 0.3)

# Complex formula
(kpi_1 + kpi_2) / (kpi_3 + kpi_4)
```

### Context-Aware Interface Redesign
**Major UX improvements focusing user attention:**
- **Prominent Value Display**: Large, centered value cards (3rem font) with color-coded badges
- **Adaptive UI**: Interface shows only relevant sections based on calculation type
  - Manual: Contribution form, consensus status, trend charts, contributions table
  - Formula: Source KPIs, expression display, auto-update indicator
  - Linked: Sync status, source configuration, read-only display
- **Smart Action Buttons**: Context-aware buttons adapt to KPI type
  - Manual: "Configure Calculation" → modal with formula builder
  - Formula: "Edit Formula" → direct to formula configuration
  - Linked: "Configure Link Source" → settings page
- **Reduced Clutter**: Hides irrelevant UI (no trend charts for formulas, no contribution forms for linked KPIs)

### Developer Experience
- **Python 3.14 Compatibility**: Upgraded simpleeval library (0.9.13 → 1.0.4)
- **Better Error Handling**: Division by zero, invalid expressions gracefully handled
- **Safe Execution**: Sandboxed Python evaluation with limited function set
- **Debug Logging**: Comprehensive logging for formula calculation troubleshooting

## What's New in v2.1

### Dashboard & Overview
- **Central Hub**: Dashboard replaces workspace as home page
- **Statistics at a Glance**: See counts of all entities in color-coded cards
- **Quick Actions**: One-click access to common tasks (create snapshot, export, view mentions)
- **Recent Activity**: Widgets showing last 5 snapshots and last 10 comments
- **Unread Alerts**: Button appears when you have unread mentions

### Time-Series Tracking
- **Snapshots**: Capture current state with custom labels for tracking progress
- **Historical View**: View workspace as it was on any snapshot date
- **Trend Indicators**: Automatic ↗️↘️→ arrows showing value changes
- **Comparison**: Side-by-side comparison of any two snapshots with % change
- **Charts**: Interactive line charts (Chart.js) showing KPI history

### Collaboration Features
- **Comments**: Discussion threads on any KPI cell
- **@Mentions**: Notify users with autocomplete dropdown (keyboard navigation!)
- **Threading**: Full reply nesting with visual indentation
- **Notifications**: Bell icon (🔔) shows unread mention count
- **Real-time**: See latest discussions on dashboard widget

### Enhanced UX
- **Three-Tier Navigation**: Dashboard → Workspace → Administration
- **Bootstrap Icons**: Visual cues throughout interface
- **Keyboard Shortcuts**: Arrow keys + Enter in mention dropdown
- **Auto-refresh**: Charts and widgets update automatically

## What's in v2.0

### Database Migration: PostgreSQL
- **Data Persistence**: Data now survives deployments and restarts
- **Production Ready**: PostgreSQL for reliable, concurrent access
- **Automatic Migrations**: Schema updates deploy automatically
- **Performance**: Better query performance for complex aggregations

### Flexible Color Configuration
- **KPI-Level Colors**: Sign-based colors (positive/negative/zero) configured per KPI, not per value type
- **Context-Specific Meaning**: Same value type (e.g., "Cost") can have different color interpretations:
  - Expense KPI: Negative (savings) = green, Positive (cost) = red
  - Revenue KPI: Positive (income) = green, Negative (loss) = red
- **Color Propagation**: Colors automatically inherit through all rollup levels (System → Initiative → Challenge → Space)
- **UI Integration**: Color pickers in KPI creation and editing forms

### Technical Improvements
- **psycopg3**: Modern PostgreSQL driver with Python 3.13+ compatibility
- **Flask-Migrate**: Proper database migration management
- **Render Deployment**: Production hosting with managed PostgreSQL
- **Version Tags**: Git tags for release tracking

## User Roles

### Global Administrator
- Manages users across all organizations
- Creates and manages organizations
- Assigns users to organizations
- Cannot access organization business data

### Organization User
- Views and navigates organization structure
- Enters data for KPIs (as a contributor)
- Views consensus status and rolled-up values
- Has access to assigned organizations only

### Organization Administrator
- All organization user capabilities, plus:
- Creates and manages organization structure (Spaces, Challenges, Initiatives, Systems, KPIs)
- Configures value types
- Manages display order and metadata

**Note**: In the current implementation, all organization users have admin capabilities. Granular permissions are planned for future versions.

## Core Features

### Two-Step Login
1. **Step 1**: Username and password authentication
2. **Step 2**: Organization selection (filtered to user's accessible organizations)
   - Admin users see "Log in as Administrator" checkbox for global admin access
   - Regular users only see organizations they have access to

### Interactive Tree/Grid Workspace
- Expandable/collapsible hierarchical view
- Expand All / Collapse All buttons
- Color-coded levels:
  - **Spaces** (blue): Top-level groupings
  - **Challenges** (light gray): Business challenges
  - **Initiatives** (gray): Strategic initiatives
  - **Systems** (light blue): Technical systems
  - **KPIs** (yellow): Measurable indicators
- Value columns show consensus values with status badges
- Click any KPI cell to enter/view data

### Consensus-Based Data Entry
- Multiple contributors can provide values for each KPI
- System automatically calculates consensus status:
  - **No Data** (gray): No contributions yet
  - **Strong Consensus** (green): Single contribution OR all contributors agree - eligible for roll-up
  - **Weak Consensus** (yellow): Majority agrees but not unanimous
  - **No Consensus** (red): Conflicting values, no agreement
- Edit existing contributions by clicking "Edit" button
- Values display in workspace with status badges

### Value Types
- **Numeric**: Cost, CO2 emissions, licenses, people, etc.
  - Integer or decimal format
  - Configurable decimal places
  - Unit labels (€, tCO2e, licenses, etc.)
  - **v2.0: Sign-based colors configured per KPI** (not on value type)
- **Qualitative**:
  - **Risk**: Levels 1-3 (!, !!, !!!)
  - **Positive Impact**: Levels 1-3 (★, ★★, ★★★)
  - **Negative Impact**: Levels 1-3 (▼, ▼▼, ▼▼▼)
- Dynamic form fields: numeric-specific fields only show for numeric types
- Organization-specific: each organization defines its own value types

### Color Configuration (v2.0)

**Sign-Based Colors for Numeric Values:**
- Configured at KPI level when creating/editing KPIs
- Three color pickers per numeric value type:
  - **Positive Values**: Color for values > 0 (default: green #28a745)
  - **Zero/Null Values**: Color for values = 0 or null (default: gray #6c757d)
  - **Negative Values**: Color for values < 0 (default: red #dc3545)

**Why KPI-Level (not Value Type-Level)?**

Same value type can have opposite meanings in different KPIs:

| Example | Value Type | KPI: "Reduce Expenses" | KPI: "Increase Revenue" |
|---------|-----------|------------------------|-------------------------|
| +100€ | Cost (€) | Red (bad - cost increase) | Green (good - income) |
| -100€ | Cost (€) | Green (good - savings) | Red (bad - loss) |
| 0€ | Cost (€) | Gray (neutral) | Gray (neutral) |

**Color Propagation:**
- Colors configured on KPI automatically apply to all rollup levels
- System level: Inherits from first KPI with this value type
- Initiative level: Inherits from descendant KPIs
- Challenge level: Inherits from descendant KPIs
- Space level: Inherits from descendant KPIs
- If no KPI configuration found: Falls back to default colors

**UI Location:**
- **KPI Creation**: Checkbox list of value types with color pickers
- **KPI Editing**: Color configuration section showing current colors
- **Workspace Display**: Values colored according to KPI configuration

### Hierarchical Administration
- Create entities in context with nested buttons:
  - **Space** → + Challenge button
  - **Challenge** → + Initiative button
  - **Initiative** → + System button
  - **System** → + KPI button
- Full tree view in administration with all levels visible
- Edit any entity at any level
- Color-coded and indented for clarity

## Hierarchical Data Model

### Organizational Hierarchy

```
Organization
    └── Space (e.g., Season 1, Site A, Customer X)
        └── Challenge (business problem to solve)
            └─┬─ ChallengeInitiativeLink
              └── Initiative (strategic program)
                  └─┬─ InitiativeSystemLink
                    └── System (technical system)
                        └── KPI (at context level)
                            └─┬─ KPIValueTypeConfig
                              ├── ValueType (Cost, Risk, Impact, etc.)
                              └── Contribution (from individual contributors)
```

### Key Relationships

**Many-to-Many Reusability:**
- One Initiative can address multiple Challenges (via `ChallengeInitiativeLink`)
- One System can support multiple Initiatives (via `InitiativeSystemLink`)
- One KPI can track multiple Value Types (via `KPIValueTypeConfig`)

**Context-Specific KPIs:**
- KPIs belong to `InitiativeSystemLink`, not to the master System
- The same system in different initiatives can have completely different KPIs
- Example: "SAP" system under "Digital Transformation" initiative might track "License Cost" and "User Adoption", while "SAP" under "Finance Optimization" tracks "Processing Time" and "Error Rate"

## Authentication & Access Control

### Bootstrap Admin
On first startup, system creates:
- Login: `cisk`
- Password: `Zurich20`
- Role: Global Administrator
- Must change password on first login

### User Management
- Global admins manage all users
- Users can be assigned to multiple organizations
- User accounts are global, organization access is controlled via `UserOrganizationMembership`
- Password requirements: minimum 8 characters
- Passwords are hashed using Werkzeug security

### Session Management
- Flask-Login for user sessions
- Organization context stored in session:
  - `session['organization_id']`: Current organization or None for global admin
  - `session['organization_name']`: Display name
- Organization context enforced via `@organization_required` decorator

### Protection Rules
- Last active global admin cannot be deleted
- Users can only access organizations they're assigned to
- Regular users cannot access Global Administration
- CSRF protection on all forms (Flask-WTF)

## Workspace & Tree/Grid Navigation

### Tree Structure Display
- **Expand/Collapse**: Click arrow icons (▶/▼) to expand/collapse levels
- **Expand All**: Expand entire tree with one click
- **Collapse All**: Collapse entire tree with one click
- **Smart Collapse**: Collapsing a level automatically collapses all children

### Visual Hierarchy
- Progressive indentation: 2rem, 4rem, 6rem, 8rem
- Arrow symbols: → ⮕ ⇨ ⟹ for different levels
- Color coding by level for easy scanning
- Sticky header with value type columns

### Value Display
- **No Data**: "Click to enter" badge (gray)
- **Has Consensus**: Shows value + unit + status badge
- **No Consensus**: Shows "X conflicting values" + red badge
- Click any cell to view details and enter/edit data

### KPI Cell Detail View
Shows:
- Breadcrumb navigation (Org → Space → Challenge → Initiative → System → KPI)
- Value type information
- Consensus status card with:
  - Status badge
  - Consensus value (if exists)
  - Contribution count
  - Roll-up eligibility
- Contributions table with:
  - Contributor name
  - Value (with unit)
  - Comment
  - Timestamp
  - Edit button
- Add/Update contribution form

## Data Entry & Consensus Model

### Three Calculation Types

Every KPI can be configured with one of three calculation types:

#### 1. Manual Entry (Contribution-Based)
The default mode where team members provide input and the system calculates consensus.

**Process:**
1. User navigates to KPI cell
2. Enters contributor name (free text, no account required)
3. Provides value:
   - Numeric types: decimal value
   - Qualitative types: level 1, 2, or 3
4. Optional comment
5. Submits

**Contribution Rules:**
- One contribution per contributor name per KPI cell
- Subsequent submissions with same name update existing contribution
- No user account binding - allows flexible contributor identification
- Contributors can be teams, roles, or individuals

**Consensus Calculation Algorithm:**
```
IF no contributions:
    status = NO_DATA
    is_rollup_eligible = false

ELSE IF only 1 contribution:
    status = STRONG_CONSENSUS
    value = contribution value
    is_rollup_eligible = TRUE  ← Single contribution is valid!

ELSE IF all contributions agree (same value):
    status = STRONG_CONSENSUS
    value = agreed value
    is_rollup_eligible = TRUE  ← Only strong consensus rolls up!

ELSE IF majority exists (>50%):
    status = WEAK_CONSENSUS
    value = majority value
    is_rollup_eligible = false

ELSE:
    status = NO_CONSENSUS
    value = null
    is_rollup_eligible = false
```

**Key Rule**: Strong Consensus (single contribution OR unanimous agreement) participates in upward roll-ups.

**Editing Contributions:**
- Click "Edit" button next to any contribution
- Form pre-populates with existing values
- Change values and submit to update
- Uses same contributor name to identify which contribution to update

#### 2. Linked KPI
Pull values from another organization's KPI, enabling data sharing across organizational boundaries.

**Configuration:**
- Set via KPI Advanced Settings page
- Select source organization and source KPI
- Values sync automatically from source
- Read-only in destination organization

**Use Cases:**
- Shared services consuming data from provider organizations
- Cross-organizational dependencies
- Central data sources feeding multiple consumers

**Display:**
- Large centered value card with "LINKED KPI" badge (info blue)
- Shows current synced value
- "Configure Link Source" button for changing source
- No contribution form (read-only)

#### 3. Formula Calculation
Auto-calculate values from other KPIs using mathematical operations or Python expressions.

**Two Formula Modes:**

**Simple Mode** - Basic operations:
- **Sum**: Add all source KPI values
- **Average**: Calculate mean of source values
- **Minimum**: Take lowest value
- **Maximum**: Take highest value
- **Multiply**: Multiply all values together
- **Subtract**: Subtract subsequent values from first

**Advanced Mode** - Python expressions:
- Write custom formulas using Python syntax
- Use variable names like `kpi_123` for each source KPI
- Supports operators: `+`, `-`, `*`, `/`, `//`, `%`, `**`, `()`
- Available functions:
  - `abs(x)` - Absolute value
  - `round(x)` or `round(x, decimals)` - Rounding
  - `max(a, b, c)` - Maximum
  - `min(a, b, c)` - Minimum
  - `sum([a, b, c])` - Sum of list

**Example Formulas:**
```python
# Percentage calculation
round((kpi_1 / kpi_2) * 100, 1)

# ROI calculation
round((kpi_revenue - kpi_cost) / kpi_cost * 100)

# Weighted average
(kpi_1 * 0.7 + kpi_2 * 0.3)

# Absolute difference
abs(kpi_target - kpi_actual)

# Best case scenario
max(kpi_1, kpi_2, kpi_3)

# Complex calculation
(kpi_1 + kpi_2) / (kpi_3 + kpi_4)
```

**Configuration Interface:**
- Search and select source KPIs from any organization
- Click variable badges to insert into expression
- Real-time preview of current values
- Comprehensive help documentation with examples
- Formula details displayed on KPI cell page

**Auto-Update:**
- Formulas recalculate automatically when source KPIs change
- No manual intervention required
- Always shows current calculated value

**Display:**
- Large centered value card with "FORMULA" badge (success green)
- Shows mode (Simple or Advanced Python)
- Lists source KPIs with current values
- Displays Python expression for advanced mode
- "Edit Formula" button for modifications

### Context-Aware Interface

The KPI detail page adapts based on calculation type:

**Manual KPIs show:**
- Current consensus value (large, centered)
- Consensus status badge (strong/weak/no consensus)
- Contribution count
- Add/Update contribution form
- Historical trend chart
- Contributions table with edit/delete actions
- Value type and consensus status cards

**Formula KPIs show:**
- Current calculated value (large, centered)
- Formula mode badge
- Source KPIs list with current values
- Python expression (advanced mode)
- Formula configuration details
- "Edit Formula" button
- Hides: contribution form, trend charts, contributions table

**Linked KPIs show:**
- Current synced value (large, centered)
- "Linked KPI" badge
- Sync status
- Link configuration info
- "Configure Link Source" button
- Hides: contribution form, trend charts, contributions table

**Design Principle**: Show only relevant information for each calculation type, reducing cognitive load and focusing user attention on what matters.

## Value Types

### Creation
- Organization-specific
- Name, kind, display order
- Active/inactive flag

### Numeric Value Types
Fields displayed:
- Numeric format: Integer or Decimal
- Decimal places: 0-4
- Unit label: €, tCO2e, licenses, people, etc.
- Default aggregation formula: Sum, Min, Max, Avg

### Qualitative Value Types
Fields hidden:
- No numeric format
- No decimal places
- No unit label (symbols used instead)

Display symbols:
- Risk: !, !!, !!!
- Impact: ★, ★★, ★★★
- Negative Impact: ▼, ▼▼, ▼▼▼

### Dynamic Form Behavior
- Kind dropdown triggers show/hide of numeric fields
- JavaScript controls visibility based on selection
- Clean UX - only relevant fields shown

## Roll-up Aggregation

### Aggregation Flow
```
KPI (leaf level, contributions)
    ↓ [Value Type default formula]
System (first aggregation)
    ↓ [Configurable via InitiativeSystemLink RollupRule]
Initiative
    ↓ [Configurable via ChallengeInitiativeLink RollupRule]
Challenge
    ↓ [Configurable via Challenge RollupRule]
Space (root level)
```

### Aggregation Formulas
- **Sum**: Add all eligible values (most common for costs, emissions)
- **Min**: Minimum value (e.g., best-case scenario)
- **Max**: Maximum value (e.g., worst-case risk)
- **Avg**: Average value (e.g., mean impact)

### Partial Data Handling
If some child rows lack strong consensus:
- Ignore those rows in aggregation
- Compute parent value if at least one valid child exists
- Mark parent cell as "computed from partial data"
- Display indicator showing data completeness

### Roll-up Rules (Future Enhancement)
Location: `app/models/rollup_rule.py`
Current status: Data model exists, UI configuration pending
Enables per-context formula overrides

## Dashboard

### Overview Page
The Dashboard is the home page after login, providing quick access and overview of the organization.

**Statistics Cards:**
- Display counts for: Spaces, Challenges, Initiatives, Systems, KPIs, Value Types
- Color-coded cards with hover effects
- Real-time data from database

**Quick Actions Bar:**
- Open Workspace
- Create Snapshot
- View Snapshots
- Export to Excel
- Unread Mentions Alert (appears only when mentions exist)

**Recent Snapshots Widget:**
- Shows last 5 snapshots
- Each snapshot displays date and label
- Action buttons: View (historical state), Compare (vs. current)
- Link to full snapshots list

**Recent Comments Widget:**
- Shows last 10 comments across entire organization
- Displays: user name, comment text (truncated), timestamp, KPI context
- Scrollable container for easy browsing
- Updates automatically when new comments posted

**Getting Started Guide:**
- Tips for new users
- Explains core features (Workspace, Snapshots, Comments, Mentions, Trends)
- Dismissible info panel

### Navigation
- **Logo**: Clicking "CISK Navigator" returns to Dashboard
- **Navbar**: Dashboard, Workspace, Administration links with icons
- **Breadcrumbs**: Context-aware navigation on all pages

## Time-Series Tracking

### Snapshots
Capture the current state of all KPI values at a specific point in time for historical tracking.

**Creating Snapshots:**
1. Click "Quick Snapshot" button (available on Dashboard and Workspace)
2. Enter snapshot date (defaults to today)
3. Optional: Add label (e.g., "Q1 2026", "Sprint 5", "Baseline")
4. System captures consensus values for all KPIs
5. System captures rollup values at all hierarchy levels

**Data Captured:**
- KPI consensus values (only strong consensus)
- Rollup values (System, Initiative, Challenge, Space levels)
- Snapshot date and label
- Organization context

**Database Tables:**
- `kpi_snapshots`: Individual KPI values
- `rollup_snapshots`: Aggregated values at each level

**Viewing Snapshots:**
- **Snapshots List**: View all available snapshots with dates and labels
- **Historical View**: Click "View" to see workspace as it was on that date
- **Yellow Banner**: Indicates historical view mode with "Return to Current" button

### Trend Indicators
Automatic calculation and display of trends when multiple snapshots exist.

**Calculation:**
- Compares current value vs. most recent snapshot
- Direction: ↗️ (increasing), ↘️ (decreasing), → (stable)
- Change: Absolute difference
- Percent Change: Percentage of change relative to previous value

**Display:**
- Small trend icon appears next to KPI cell values
- Hover tooltip shows exact change amount and percentage
- Only shown when at least 2 snapshots exist
- Calculated on-demand via API

**API Endpoint:**
- `GET /workspace/api/kpi/<config_id>/trend`
- Returns: `{'direction': 'up'|'down'|'stable', 'change': value, 'percent_change': percent}`

### Snapshot Comparison
Side-by-side comparison of two snapshots or snapshot vs. current data.

**Comparison View:**
- Select two snapshots (or snapshot vs. current)
- See detailed comparison table with all KPIs
- Each row shows: KPI name, Value Type, Value 1, Value 2, Change, % Change
- Color indicators: Green (increase), Red (decrease), Gray (unchanged)

**Summary Statistics:**
- Count of KPIs that increased
- Count of KPIs that decreased
- Count of KPIs that stayed the same

**Access:**
- Click "Compare" button on any snapshot in list
- Available from Dashboard recent snapshots widget
- Default comparison: Selected snapshot vs. Current

## Comments & Collaboration

### Cell-Level Comments
Discussion threads attached to any KPI cell (specific KPI + Value Type combination).

**Creating Comments:**
1. Click 💬 icon on any KPI cell in workspace
2. Opens comment modal for that specific cell
3. Type comment text (supports @mentions)
4. Click "Post Comment"
5. Comment appears in thread with timestamp

**@Mention System:**
- Type `@` to trigger autocomplete dropdown
- Shows all users in current organization
- Dropdown appears instantly (no typing required after @)
- Navigate with arrow keys (↑/↓)
- Select with Enter key or mouse click
- Selected username inserted into text
- Mentioned user receives notification

**Keyboard Navigation:**
- `@` - Show all users
- `↑/↓` - Navigate dropdown
- `Enter` - Select highlighted user
- `Escape` - Close dropdown

**Threaded Replies:**
- Click "Reply" button on any comment
- Reply form appears indented under parent
- Full nesting support (replies to replies)
- Visual indentation shows thread structure

**Resolve/Unresolve:**
- Top-level comments have "Resolve" button
- Marks discussion as complete
- Resolved comments appear faded
- Can be unresolvedif needed

**Edit/Delete:**
- Own comments have Edit and Delete buttons
- Ownership check prevents editing others' comments
- Deleting comment deletes all replies recursively

### Mention Notifications
Track and display @mentions for each user.

**Notification Bell (🔔):**
- Located in navbar (top right)
- Shows unread count badge when mentions exist
- Click to open mentions modal

**Mentions Modal:**
- Lists all unread mentions with context
- Shows: commenter name, comment text, time ago, KPI context
- "Mark as Read" button for each mention
- "Mark All as Read" button at bottom
- Auto-updates count badge after marking read

**Database Table:**
- `mention_notifications`: Tracks which users were mentioned in which comments
- Fields: user_id, comment_id, is_read, read_at, created_at

### Comment Count Badges
Visual indicators showing discussion activity.

**Display:**
- Small blue badge with number appears next to 💬 icon
- Shows total comment count for that KPI cell
- Updates automatically when comments added/deleted
- Loads on page load for all visible cells

## Charts & Visualization

### Trend Charts
Interactive line charts showing KPI value history over time.

**Technology:**
- Chart.js 4.4.0 (JavaScript charting library)
- Responsive canvas-based rendering
- Hover tooltips with exact values

**Display:**
- Appears on KPI Cell Detail page
- Section titled "Historical Trend"
- Only shown for numeric value types
- Requires at least 1 snapshot to display

**Chart Features:**
- Line graph with filled area under curve
- Blue color scheme matching UI
- X-axis: Snapshot dates
- Y-axis: KPI values (with unit if configured)
- Hover tooltips show exact value and date
- Smooth curve with tension (0.4)
- Point markers at each snapshot

**Data Source:**
- Uses `GET /workspace/api/kpi/<config_id>/history` endpoint
- Returns array of `{date: 'YYYY-MM-DD', value: number}` objects
- Sorted chronologically

**Empty State:**
- When no snapshots exist: "No historical data available. Create snapshots to track trends over time."
- Blue info alert with icon

**Refresh:**
- Refresh button next to chart title
- Reloads data from API
- Updates chart without page reload

### Interactive Features
- **Zoom**: Chart adapts to data range automatically
- **Tooltips**: Hover over points for details
- **Responsive**: Resizes with browser window
- **Animations**: Smooth transitions when data updates

## Administration Features

### Global Administration
Accessible to: Global administrators only

**User Management:**
- Create new users
- Edit user details (login, email, display name)
- Assign users to organizations
- Activate/deactivate users
- Delete users (except last active global admin)

**Organization Management:**
- Create organizations
- Edit organization details
- Activate/deactivate organizations
- View organization statistics

### Organization Administration
Accessible to: Organization users (all users in current implementation)

**Space Management:**
- Create, edit, delete spaces
- Set space label (Season, Site, Customer, etc.)
- Set display order
- View full hierarchy

**Challenge Management:**
- Create challenges under spaces
- Edit challenge details
- Set display order
- View linked initiatives

**Initiative Management:**
- Create initiatives (linked to challenge)
- Edit initiative details
- Initiatives automatically available for reuse
- View linked systems

**System Management:**
- Create systems (linked to initiative)
- Edit system details
- Systems automatically available for reuse
- View KPIs in context

**KPI Management:**
- Create KPIs under initiative-system links
- Edit KPI details
- Select multiple value types for KPI
- Set display order

**Value Type Management:**
- Create value types
- Edit name, display order, active status
- Cannot edit kind, format, or formula after creation
- Delete check shows usage before deletion
- Cannot delete if used in KPIs, contributions, or rollup rules

### Hierarchical Creation Workflow
Administration view shows full tree with creation buttons at each level:
```
Space [Edit] [+ Challenge] [Delete]
    → Challenge [Edit] [+ Initiative]
        ⮕ Initiative [Edit] [+ System]
            ⇨ System [Edit] [+ KPI]
                ⟹ KPI [Edit]
```

Benefits:
- Context-aware creation
- Automatic linking
- Visual hierarchy understanding
- Quick navigation

## Version History

### v2.1.0 (Current - March 7, 2026)
- **Dashboard**: Overview page with statistics, quick actions, and recent activity widgets
- **Time-Series Tracking**: Snapshots with labels, historical view, trend indicators
- **Snapshot Comparison**: Side-by-side comparison with change analysis
- **Charts & Visualization**: Interactive line charts using Chart.js 4.4
- **Comments & Collaboration**: Cell-level discussions with @mention system
- **Threaded Replies**: Full conversation nesting with indentation
- **Mention Notifications**: Bell icon with unread count and mentions modal
- **Autocomplete Enhancement**: Keyboard navigation (arrows + Enter) in @mention dropdown
- **Enhanced Navigation**: Dashboard → Workspace → Administration with Bootstrap Icons
- **Recent Comments Widget**: Latest 10 discussions displayed on dashboard
- **Recent Snapshots Widget**: Last 5 snapshots with View/Compare buttons
- Database: 4 new tables (kpi_snapshots, rollup_snapshots, cell_comments, mention_notifications)
- API: 15 new endpoints for snapshots, comments, mentions, and user search

### v2.0.0 (March 2026)
- **PostgreSQL Migration**: Data persistence across deployments
- **Color System Refactor**: Sign-based colors configured per KPI (not value type)
- **6 Aggregation Formulas**: sum, min, max, avg, median, count
- **New Value Types**: Level (●●●), Sentiment (☹️😐😊)
- **Excel Export**: Hierarchical export with row grouping
- **YAML Export/Import**: Complete structure backup and restore
- **Organization Cloning**: Create test/training environments
- **Drag-and-Drop**: Reorder value types to control column order
- **Smart Deletion**: Impact preview before deleting entities
- **Data Loss Prevention**: Multi-layer safety checks
- Render deployment with persistent PostgreSQL
- psycopg3 driver for Python 3.13+ compatibility

### v1.8
- Two-step login with organization filtering
- Users only see organizations they have access to
- Admin checkbox only for global administrators
- Interactive tree/grid workspace with expand/collapse
- Expand All / Collapse All buttons
- Consensus values displayed in workspace
- Edit contributions functionality
- Conflicting values indicator
- Dynamic value type forms (hide numeric fields for qualitative types)
- Full hierarchical administration view

### v1.7
- Fixed numeric field visibility for value types
- Renamed "Positive Impact" to "Impact"
- JavaScript-based dynamic form fields

### v1.6
- Fixed organization dropdown validation
- Changed validator from DataRequired() to InputRequired() to allow organization ID 0

### v1.0 - v1.5
- Initial implementation
- Core data models
- Authentication system
- Basic CRUD operations
- Consensus calculation
- Initial workspace view

## Future Enhancements

### Planned Features
1. **Roll-up Rule Configuration UI**
   - Per-context formula overrides
   - Enable/disable roll-up at each level
   - Visual roll-up preview

2. **Granular Permissions**
   - Organization role: Admin vs. Viewer vs. Contributor
   - Space-level permissions
   - Challenge-level permissions

3. **Data Export**
   - Excel export with hierarchy
   - PDF reports
   - CSV for analysis

4. **Audit Trail**
   - Track all changes
   - Contribution history
   - Consensus changes over time

5. **Bulk Operations**
   - Copy KPI structure across contexts
   - Bulk value import
   - Template application

6. **Advanced Visualizations**
   - Charts and graphs
   - Trend analysis
   - Comparison views

7. **Notifications**
   - Alert on consensus reached
   - Alert on conflicting contributions
   - Weekly summary emails

8. **API Access**
   - REST API for integrations
   - Webhook support
   - Bulk data operations

## Technical Requirements

### Browser Support
- Modern browsers (Chrome, Firefox, Safari, Edge)
- JavaScript enabled
- Cookies enabled (for session management)

### Server Requirements
- Python 3.11+
- Flask 3.0
- SQLite 3 (or PostgreSQL for production)
- 100MB disk space minimum
- 512MB RAM minimum

### Deployment
- Runs on port 5003 by default
- Single-process server (development)
- Gunicorn for production deployment
- No external database server required (SQLite)

## Security Considerations

### Authentication
- Password hashing with Werkzeug (PBKDF2)
- Session-based authentication (Flask-Login)
- Forced password change for bootstrap admin
- No password hints or exposure

### Authorization
- Organization isolation enforced at database query level
- Session-based organization context
- Decorator-based route protection
- CSRF protection on all forms

### Data Protection
- SQL injection prevention via SQLAlchemy ORM
- XSS prevention via Jinja2 auto-escaping
- No sensitive data in logs
- Foreign key enforcement for referential integrity

### Best Practices
- Minimum 8-character passwords
- Session timeout on browser close
- No user enumeration during login
- Secure session cookies

---

**Document Version**: 1.8
**Last Updated**: March 6, 2026
**Author**: CISK Navigator Team
