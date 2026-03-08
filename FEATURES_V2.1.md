# CISK Navigator v1.14 - Feature Updates

**Latest Version**: v1.14.0 (March 8, 2026)
**Status**: ✅ **DEPLOYED TO PRODUCTION**

---

## 🆕 Features Added in v1.13-v1.14

### Governance Bodies (v1.13.0)

**Purpose**: Manage committees, boards, and teams that oversee specific KPIs with visual organization and filtering.

**Features:**

1. **Governance Body Management**:
   - Create bodies with name, abbreviation, description, and color
   - Full CRUD operations (Create, Read, Update, Delete)
   - Drag-to-reorder for custom display order
   - Permission control: `can_manage_governance_bodies`
   - Default "General" body for each organization (renamable, not deletable)

2. **Many-to-Many KPI Links**:
   - KPIs can belong to multiple governance bodies
   - Minimum of 1 governance body required per KPI
   - Junction table: `kpi_governance_body_links`
   - Automatic linking: all existing KPIs assigned to "General" during migration

3. **Workspace Filtering**:
   - Filter KPIs by governance body with pill-shaped buttons
   - Multiple selections supported
   - Smart default: all bodies selected when none explicitly chosen
   - Empty selection = hide all KPIs (bug fixed in v1.14)
   - Color-coded badges on each KPI row showing assignments

4. **Visual Design**:
   - Full color picker for each governance body
   - Pill-shaped badges with abbreviations
   - Hover tooltips show full name
   - Color consistency across all interfaces

**Database Schema:**
```sql
CREATE TABLE governance_bodies (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    abbreviation VARCHAR(20) NOT NULL,
    description TEXT,
    color VARCHAR(7) NOT NULL,  -- Hex color
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE TABLE kpi_governance_body_links (
    id INTEGER PRIMARY KEY,
    kpi_id INTEGER NOT NULL,
    governance_body_id INTEGER NOT NULL,
    created_at TIMESTAMP,
    UNIQUE(kpi_id, governance_body_id),
    FOREIGN KEY (kpi_id) REFERENCES kpis(id),
    FOREIGN KEY (governance_body_id) REFERENCES governance_bodies(id)
);
```

**Migrations**: `597259f31427_add_governance_bodies_and_kpi_.py`

---

### KPI Archiving (v1.13.0)

**Purpose**: Preserve historical KPIs without cluttering active workspace.

**Features:**

1. **Archive/Unarchive Operations**:
   - Archive button on KPI edit page
   - Confirmation dialog prevents accidental archives
   - Unarchive button for archived KPIs
   - Full audit trail: tracks who archived and when

2. **Read-Only Mode**:
   - Archived KPIs cannot accept new contributions
   - Block at route level with flash message
   - Warning banner on KPI detail page
   - All historical data (contributions, snapshots, comments) preserved

3. **Workspace Display**:
   - Hidden by default from workspace
   - "Show Archived KPIs" filter toggle
   - Visual distinction: 60% opacity + archive badge
   - Archive status shown: "🗄️ Archived on YYYY-MM-DD by username"

4. **Data Preservation**:
   - ALL data retained: contributions, snapshots, comments, links
   - Rollup calculations still include archived KPIs
   - Export includes archived KPIs when filter enabled
   - Full restore capability via unarchive

**Database Schema:**
```sql
ALTER TABLE kpis ADD COLUMN is_archived BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE kpis ADD COLUMN archived_at TIMESTAMP NULL;
ALTER TABLE kpis ADD COLUMN archived_by_user_id INTEGER NULL;
ALTER TABLE kpis ADD FOREIGN KEY (archived_by_user_id) REFERENCES users(id) ON DELETE SET NULL;
```

**Routes:**
- POST `/org-admin/kpis/<id>/archive` - Archive KPI
- POST `/org-admin/kpis/<id>/unarchive` - Unarchive KPI

**Migrations**: `e6f86e8171ac_add_kpi_archiving_support.py`

---

### Modern Workspace UI (v1.14.0)

**Purpose**: Complete interface modernization with dark mode, level controls, and enhanced UX.

**Features:**

1. **True Dark Mode Theme**:
   - Deep black background (#0a0a0a) for reduced eye strain
   - High contrast text (#e0e0e0)
   - Level-specific dark colors for visual hierarchy
   - Smooth transitions and hover effects
   - Sticky headers with dark background

2. **Compact Modern Toolbar**:
   - Gradient background (linear-gradient 135deg)
   - Icon-based compact buttons
   - Pill-shaped filter interface
   - Single unified toolbar (replaced old button rows + card)
   - Quick stats bar showing active filters and counts

3. **Level Visibility Controls** (NEW):
   - Toggle display of: Spaces, Challenges, Initiatives, Systems, KPIs
   - Pill-shaped checkboxes with icons
   - Instant filtering (no page reload)
   - Checkboxes managed in session state
   - Query params: `show_spaces`, `show_challenges`, etc.

4. **Enhanced Visual Hierarchy**:
   - Icons per level: 🏢 🎯 💡 ⚙️ 📊
   - Color-coded left borders (4px) per level
   - Rollup indicator (Σ symbol) on aggregated values
   - Modern expand/collapse icons with rounded background
   - Vertical guide lines (like VS Code tree)

5. **Interactive Filter Pills**:
   - Click pill to toggle (no visible checkboxes)
   - Active state: blue background (#0d6efd)
   - Inactive state: dark gray (#2a2a2a)
   - Auto-submit on change
   - Clear All button resets all filters

6. **Sticky Elements**:
   - First column (Structure) sticky on horizontal scroll
   - Header row sticky on vertical scroll
   - Both scroll independently
   - z-index properly layered

7. **Bug Fixes**:
   - Fixed governance body filter logic (empty = hide all, not show all)
   - Smart default: auto-select all bodies when none explicitly chosen
   - Fixed version display on login page (now v1.14.0)

**CSS Classes Added:**
- `.modern-toolbar` - Gradient toolbar container
- `.filter-pill` - Pill-shaped filter button
- `.hierarchy-icon` - Icon container for each level
- `.level-border` - Colored left border per level
- `.expand-icon` - Modern expand/collapse button
- `.rollup-indicator` - Σ symbol for rollups
- `.stats-bar` - Quick stats display
- `.level-controls` - Level visibility toggles

**Route Changes:**
```python
# Added to workspace.index():
show_levels = {
    'spaces': request.args.get('show_spaces', '1') == '1',
    'challenges': request.args.get('show_challenges', '1') == '1',
    'initiatives': request.args.get('show_initiatives', '1') == '1',
    'systems': request.args.get('show_systems', '1') == '1',
    'kpis': request.args.get('show_kpis', '1') == '1',
}
```

**JavaScript Enhancements:**
- Modern filter pill click handlers
- Auto-submit on checkbox change
- Clear All filters functionality
- Maintains active state classes

---

## 🆕 Features Added Post-v2.1

### Smart Value Entry (v1.10.0+)

**Purpose**: Distinguish between time evolution and consensus building when entering KPI values.

**The Problem:**
- Single contributor updating a value creates "low consensus"
- Historical values get lost when replaced
- No clear way to indicate "time has passed" vs "still building consensus"

**The Solution:**
When entering a value on a cell with existing consensus, a modal prompts:
- **"NEW data (time evolved)"**:
  - Auto-creates snapshot with label "Auto: Before update by [user]"
  - Deletes ALL existing contributions
  - Adds new contribution (clean slate for new period)
- **"Contributing to CURRENT period"**:
  - Normal behavior - adds contribution to existing pool
  - Consensus calculation runs as usual

**Benefits:**
- Clean time series evolution
- Preserved historical data
- Single contributor can update without creating "weak consensus"
- Clear intent declaration

**Database:**
- Uses existing snapshot system (`allow_duplicates=True` parameter)
- No schema changes required

**UI:**
- Modal on KPI cell detail page
- Two radio button choices
- Form auto-submits after selection

---

### Target Tracking (v1.11.0+)

**Purpose**: Track progress toward goals with visual indicators and baseline comparisons.

**Features:**
1. **Set Targets on KPIs**:
   - Target value (numeric)
   - Target date (optional)
   - Baseline snapshot (optional reference point)

2. **Progress Indicators**:
   - Workspace grid shows: `🎯 X%` below value
   - Tooltip: "Target: 1000 by 2026-12-31"
   - Progress calculated as: (current / target) × 100

3. **Chart Visualization**:
   - Horizontal dashed red line shows target value
   - Label: "Target (1000 by 2026-12-31)"
   - Makes it easy to see trajectory toward goal

4. **Baseline Support**:
   - Reference a snapshot as starting point
   - Progress measured from baseline to target
   - Example: Baseline=500, Target=1000, Current=750 → 50% progress

**Configuration:**
- Per KPI-value type config (different KPIs can have different targets)
- Optional "Set Target Value" checkbox on create/edit KPI
- Shows input fields only when checkbox is checked

**Database Schema:**
```sql
ALTER TABLE kpi_value_type_configs ADD COLUMN target_value NUMERIC(20,6);
ALTER TABLE kpi_value_type_configs ADD COLUMN target_date DATE;
ALTER TABLE kpi_value_type_configs ADD COLUMN baseline_snapshot_id INTEGER;
```

**Migration**: `0e11e44f5949_add_target_tracking_fields.py`

**Technical Notes:**
- `baseline_snapshot_id` stored as plain integer (no FK constraint)
- Avoids circular dependency with `kpi_snapshots` table
- Uses `@property` to fetch snapshot object when needed

---

### Chart Improvements (v1.11.6-v1.11.7)

**Issues Fixed:**
1. **Current Value Missing**: Charts only showed historical snapshots, not current value
2. **Same-Day Overlap**: Multiple snapshots on same day appeared as single point
3. **API Mismatch**: JavaScript expected `data.history`, API returned `data.snapshots`

**Solutions:**
1. **Include Current Value**:
   - API now appends current consensus value as latest point
   - Label: "Current"
   - Uses current timestamp

2. **Full Timestamps**:
   - Changed from date (YYYY-MM-DD) to timestamp (YYYY-MM-DD HH:MM:SS)
   - Snapshots created minutes apart now show as distinct points
   - Proper time progression visible

3. **API Alignment**:
   - Endpoint returns `data.history` array
   - Format: `{date, value, label}` objects
   - Chronological order (oldest first)

**Result:**
- Charts now show complete time series: snapshots + current
- Example: Enter values 1, 2, 3 with "new data" → see 3 points progressing

---

### Delete Functionality (v1.10.1+)

**Added Delete Operations For:**
- KPIs
- Systems
- Initiatives
- Challenges

**Implementation:**
1. **List View Buttons**:
   - Inline delete buttons in spaces.html
   - Shows all entities in hierarchical tree
   - Delete button on each row

2. **Edit Page Buttons**:
   - Delete button at bottom of edit forms
   - Separated from main form (red danger zone)
   - Confirmation dialog before deletion

3. **Confirmation**:
   - JavaScript `confirm()` dialog
   - Shows what will be deleted
   - Prevents accidental deletions

**Route Examples:**
```python
@bp.route('/kpis/<int:kpi_id>/delete', methods=['POST'])
@bp.route('/systems/<int:system_id>/delete', methods=['POST'])
@bp.route('/initiatives/<int:initiative_id>/delete', methods=['POST'])
@bp.route('/challenges/<int:challenge_id>/delete', methods=['POST'])
```

**CSRF Protection:**
- Uses FlaskForm instance for CSRF tokens
- Proper form submission with hidden token field

---

## 🎯 Major Features Added (v2.1)

## 🎯 Major Features Added

### 1. Time-Series Tracking 📊

Track KPI values over time with historical snapshots and trend analysis.

**Database Tables:**
- `kpi_snapshots` - Historical KPI values
- `rollup_snapshots` - Historical rollup values at all hierarchy levels

**Features:**
- ✅ Create snapshots manually (on-demand)
- ✅ Create organization-wide snapshots (all KPIs at once)
- ✅ Label snapshots ("Q1 2026", "Baseline", "Sprint 5")
- ✅ View historical workspace state
- ✅ Trend calculation (↗️ up, ↘️ down, → stable)
- ✅ Trend indicators on KPI cells
- ✅ Historical comparison (current vs. snapshot)
- ✅ Query snapshot dates

**API Endpoints:**
- `POST /workspace/snapshots/create` - Create snapshot
- `GET /workspace/snapshots/list` - List all snapshots
- `GET /workspace/snapshots/view/<date>` - View historical state
- `GET /api/kpi/<id>/trend` - Get trend data
- `GET /api/kpi/<id>/history` - Get value history

**UI Components:**
- Snapshots management page
- Quick snapshot modal in workspace
- Trend indicators (↗️↘️→) on cells
- Historical view mode
- Date selector

---

### 2. Comments & Collaboration 💬

Cell-level discussions with @mention support and threaded replies.

**Database Tables:**
- `cell_comments` - Comments on KPI cells
- `mention_notifications` - @mention tracking

**Features:**
- ✅ Comment on any KPI cell
- ✅ @mention users with autocomplete (keyboard navigation!)
- ✅ Threaded replies (full nesting support)
- ✅ Resolve/unresolve discussions
- ✅ Unread mentions tracking
- ✅ Notification badge in navbar with count
- ✅ Edit/delete comments (ownership checks)
- ✅ Real-time mention rendering
- ✅ Organization-scoped user search
- ✅ **Keyboard navigation** (arrows + Enter)
- ✅ **Instant autocomplete** (shows all users after @)

**API Endpoints:**
- `GET /api/cell/<id>/comments` - Get all comments
- `POST /api/cell/<id>/comments` - Create comment
- `PUT /api/comments/<id>` - Update comment
- `DELETE /api/comments/<id>` - Delete comment
- `POST /api/comments/<id>/resolve` - Resolve
- `POST /api/comments/<id>/unresolve` - Unresolve
- `GET /api/mentions/unread` - Get unread mentions
- `POST /api/mentions/<id>/read` - Mark as read
- `POST /api/mentions/mark-all-read` - Clear all
- `GET /api/org/users/search?q=term` - User autocomplete

**UI Components:**
- Comment modal per cell
- Reply threading with indentation
- @mention autocomplete dropdown with keyboard navigation
- Mentions bell (🔔) in navbar with unread count
- Mentions modal showing all unread with mark as read
- Comment count badges on KPI cells
- Resolved comment styling
- Recent comments widget on dashboard

---

### 3. Dashboard & Overview 📊

Central hub for quick access and recent activity monitoring.

**Features:**
- ✅ Statistics cards (Spaces, Challenges, Initiatives, Systems, KPIs, Value Types)
- ✅ Quick actions (Create snapshot, Export Excel, View mentions)
- ✅ Recent snapshots widget (last 5 with View/Compare buttons)
- ✅ Recent comments widget (last 10 discussions)
- ✅ Getting started guide for new users
- ✅ Unread mentions alert button
- ✅ Color-coded statistics with hover effects
- ✅ One-click navigation to all major features

**Routes:**
- `GET /workspace/dashboard` - Main dashboard page

**UI Components:**
- Dashboard page (replaces workspace as home)
- Statistics cards with color coding
- Quick actions bar
- Recent snapshots list with action buttons
- Recent comments feed with context
- Getting started info panel
- Quick snapshot modal

---

### 4. Charts & Visualization 📈

Interactive trend charts for visualizing KPI history over time.

**Features:**
- ✅ Line charts showing KPI value history
- ✅ Chart.js 4.4 integration
- ✅ Hover tooltips with exact values
- ✅ Responsive design (adapts to screen size)
- ✅ Auto-refresh capability
- ✅ Only shown for numeric value types
- ✅ "No data" message when no snapshots exist
- ✅ Smooth animations and transitions

**API Usage:**
- Uses existing `GET /api/kpi/<id>/history` endpoint
- Renders on KPI cell detail pages

**UI Components:**
- Trend chart section on KPI detail page
- Chart container with responsive sizing
- Refresh button
- Loading states
- Empty state messaging

---

### 5. Snapshot Comparison 📊

Side-by-side comparison of snapshot values with change analysis.

**Features:**
- ✅ Compare any two snapshots
- ✅ Compare snapshot vs. current data
- ✅ Absolute change calculation
- ✅ Percentage change calculation
- ✅ Color-coded change indicators (green=increase, red=decrease)
- ✅ Summary statistics (increased/decreased/unchanged counts)
- ✅ Comprehensive comparison table
- ✅ Accessible from snapshots list and dashboard

**Routes:**
- `GET /workspace/snapshots/compare?date1=X&date2=Y` - Comparison view

**UI Components:**
- Comparison page with two-column header
- Detailed comparison table
- Change indicators and badges
- Summary statistics cards
- Navigation breadcrumbs

---

## 🔧 Technical Details

### Services Added:
1. `app/services/snapshot_service.py` - Snapshot management
2. `app/services/comment_service.py` - Comment and mention handling

### Models Added:
1. `app/models/kpi_snapshot.py` - KPISnapshot, RollupSnapshot
2. `app/models/cell_comment.py` - CellComment, MentionNotification

### Frontend Assets:
1. `app/static/js/comments.js` - Comment UI manager
2. `app/static/css/comments.css` - Comment styling

### Database Migration:
- Migration file: `498afb934c2e_add_time_series_snapshots_and_.py`
- **Status**: ✅ Applied and tested locally
- **Tables created**: 4 new tables with proper indexes
- **Relationships**: All foreign keys and cascades configured

---

## ✅ Testing Results

**Test Script**: `test_new_features.py`

### Time-Series Snapshots:
- ✅ Single KPI snapshot creation
- ✅ KPI history retrieval
- ✅ Trend calculation
- ✅ Organization-wide snapshot
- ✅ Available dates query
- ✅ Snapshot with labels

### Comments & Mentions:
- ✅ Mention parsing (@username)
- ✅ Comment creation
- ✅ Comment retrieval
- ✅ Comment update
- ✅ Comment resolution
- ✅ Unread mentions tracking
- ✅ HTML rendering with mentions
- ✅ Reply threading
- ✅ User search autocomplete

**Result**: 🎉 ALL TESTS PASSED

---

## 📋 Migration Checklist

### Pre-Deployment:
- ✅ Database models created
- ✅ Services implemented
- ✅ API routes added
- ✅ UI components built
- ✅ Migration generated
- ✅ Migration tested locally
- ✅ All tests passing
- ✅ Reply threading UI added

### Deployment to Render:
1. ✅ Push code to repository
2. ✅ Render auto-deploys
3. ✅ Migration runs (manually via Shell: `flask db upgrade`)
4. ✅ New tables created in production PostgreSQL
5. ✅ Features live

### Post-Deployment Verification:
- ✅ Create a test snapshot
- ✅ View snapshots list
- ✅ Create a test comment with @mention
- ✅ Verify unread mention notification
- ✅ Test reply threading
- ✅ Check trend indicators appear
- ✅ Dashboard loads with statistics
- ✅ Snapshot comparison works
- ✅ Charts render on KPI detail pages
- ✅ @mention autocomplete with keyboard nav
- ✅ Recent comments widget displays
- ✅ Navigation links all functional

---

## 🎨 User Experience

### First Login:
1. **Login** → Automatically lands on **Dashboard**
2. See overview of entire organization at a glance
3. Quick actions available immediately

### Dashboard:
1. **Statistics**: See counts of all entities (Spaces, Challenges, etc.)
2. **Quick Actions**: One-click access to common tasks
3. **Recent Snapshots**: Last 5 with View/Compare buttons
4. **Recent Comments**: Latest discussions across organization
5. **Unread Mentions**: Alert button if you have new mentions

### Snapshots:
1. **Create**: Click "Quick Snapshot" button → Enter label → Done
2. **View**: Click "Snapshots" → See list → Click "View" to see historical state
3. **Compare**: Click "Compare" button → See side-by-side with changes
4. **Trends**: Automatic ↗️↘️→ indicators on cells (requires 2+ snapshots)

### Comments:
1. **Comment**: Click 💬 icon on any cell → Type (use @username) → Post
2. **Reply**: Click "Reply" on comment → Type → Post (shows indented)
3. **Mention**: Type @ → See all users instantly → Arrow keys to navigate → Enter to select
4. **Notifications**: Click 🔔 bell → See unread mentions → Mark as read
5. **Resolve**: Click "Resolve" to mark discussion complete

### Charts:
1. **View**: Click any KPI cell → Scroll to "Historical Trend" section
2. **Interact**: Hover over points to see exact values
3. **Refresh**: Click refresh button to reload latest data
4. **Requires**: At least 2 snapshots to show trend

---

## 🚀 Ready for Production!

**All systems tested and working**:
- Database schema ✅
- Backend services ✅
- API endpoints ✅
- Frontend UI ✅
- Migration files ✅
- Test coverage ✅

**Next Steps:**
1. Push to GitHub
2. Render will auto-deploy
3. Migration runs automatically
4. Features go live

**Estimated Deployment Time:** ~5 minutes (Render build + migration)

---

## 📊 Impact

### For Users:
- Track progress over time
- Compare baseline vs. current
- Collaborate on KPI values
- Get notified when mentioned
- Resolve discussions
- Historical analysis

### For Administrators:
- Regular snapshot scheduling (can add cron later)
- Audit trail of value changes
- Team collaboration visibility
- Trend analysis for reporting

---

## 🔮 Future Enhancements (Optional)

### Time-Series:
- Chart visualization (line charts)
- Automated snapshot scheduling (cron)
- Comparison view (side-by-side)
- Export snapshots to Excel
- Baseline vs. Target tracking

### Comments:
- Email notifications for mentions
- Rich text / Markdown support
- File attachments
- Comment search
- Activity feed
- @channel mention (notify all)

---

**Version**: 2.1.0
**Migration ID**: 498afb934c2e
**Tested**: ✅ Local SQLite + PostgreSQL
**Ready**: ✅ Production Deployment
