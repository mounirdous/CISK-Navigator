# CISK Navigator v1.11+ - Feature Updates

**Latest Version**: v1.11.7 (March 8, 2026)
**Status**: ✅ **DEPLOYED TO PRODUCTION**

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
