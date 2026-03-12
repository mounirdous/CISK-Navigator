# Changelog

All notable changes to CISK Navigator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.19.0] - 2026-03-12

### Added
- **🔗 Three Calculation Types**: Revolutionary expansion of how KPI values are determined
  - **Manual Entry**: Traditional contribution-based consensus (existing functionality)
  - **Linked KPI**: Pull values from another organization's KPI (cross-org data sharing)
  - **Formula Calculation**: Auto-calculate from other KPIs using operations or Python expressions
- **🧮 Advanced Formula Engine**: Full Python expression support for complex calculations
  - Simple Mode: Basic operations (sum, avg, min, max, multiply, subtract)
  - Advanced Mode: Python expressions with `+`, `-`, `*`, `/`, `//`, `%`, `**`, `()`
  - Available functions: `abs()`, `round()`, `max()`, `min()`, `sum()`
  - Click-to-insert variable badges for easier formula writing
  - Real-time preview with current source KPI values
  - Auto-updates when source KPIs change
- **📚 Comprehensive Formula Help**: In-app documentation with examples
  - Mathematical operators reference table
  - Available functions with descriptions
  - Real-world examples: percentages, ROI, weighted averages, complex calculations
  - Quick template buttons for common patterns
  - Expandable help panel in calculation modal
- **🎨 Context-Aware Interface Redesign**: Major UX improvements
  - Prominent value display (3rem font, centered, color-coded badges)
  - Adaptive UI showing only relevant sections per calculation type:
    - Manual: Contribution form, consensus status, charts, contributions table
    - Formula: Source KPIs list, expression display, auto-update indicator
    - Linked: Sync status, source config, read-only display
  - Smart action buttons that adapt to KPI type:
    - Manual: "Configure Calculation" button → formula builder modal
    - Formula: "Edit Formula" button → direct to configuration
    - Linked: "Configure Link Source" button → settings page
  - Removed clutter: Hidden irrelevant UI sections (no charts for formulas, no forms for linked)

### Changed
- **KPI Detail Page**: Complete redesign focusing on value prominence and context-awareness
  - Large centered value cards with calculation type badges
  - Separate displays for manual/formula/linked with tailored information
  - Color-coded badges: green (formula), blue (linked), primary (manual)
  - Historical trend charts and contributions only shown for manual KPIs
  - Formula details show source KPIs with live values
  - Linked KPIs show sync status and source configuration
- **Calculation Configuration Modal**: Simplified and streamlined
  - Reduced from 3 modes to 2 (Manual, Formula) - Linked moved to Settings
  - Informational alert explaining how to configure linked KPIs
  - Better visual hierarchy with mode toggle buttons
  - Improved KPI search with organization badges
  - Formula mode selector: Simple vs Advanced
- **Formula Details Display**: Enhanced presentation
  - Python expressions shown in code-styled boxes
  - Source KPIs displayed with current values inline
  - Clear mode badges (Simple or Advanced Python)
  - Removed redundant calculation preview text

### Fixed
- **Python 3.14 Compatibility**: Upgraded simpleeval library (0.9.13 → 1.0.4)
  - Fixed `module 'ast' has no attribute 'Num'` error
  - Formula calculations now work on Python 3.14+
- **Formula Persistence**: Selected KPIs now properly reload when editing formulas
  - Made `init()` async to properly await KPI loading
  - Fixed race condition causing empty selected KPIs list
- **Consensus Value Retrieval**: Fixed formula KPIs showing "Not calculated yet"
  - Changed from `ConsensusService.get_cell_value()` to `config.get_consensus_value()`
  - Now correctly retrieves calculated values for formula KPIs

### Database
- Migration `6a27bd82c5e5_add_formula_calculation_support_to_kpi_.py`:
  - Added `calculation_type` column to `kpi_value_type_configs` (manual/linked/formula)
  - Added `calculation_config` JSONB column for formula/link configuration
  - Migrated existing data: manual by default, linked if `linked_kpi_config_id` exists

### Technical
- **Dependencies**: Upgraded simpleeval from 0.9.13 to 1.0.4
- **Safe Execution**: Sandboxed Python evaluation with limited function set
- **Error Handling**: Graceful handling of division by zero and invalid expressions
- **Debug Logging**: Added comprehensive logging for formula calculation troubleshooting
- **Code Organization**: Created `_calculation_config_modal.html` partial template

### Documentation
- Updated SPECIFICATIONS.md with three calculation types section
- Added advanced formula documentation with operators, functions, and examples
- Documented context-aware interface design principles
- Added real-world formula use cases

## [1.14.6] - 2026-03-09

### Added
- **📊 Display Scale Feature**: Show numeric values in thousands (k) or millions (M)
  - Configurable per KPI value type: Normal, Thousands, Millions
  - Display decimals field for precision control (0-6 decimals)
  - Smart trailing zero removal for clean display
  - Applied to workspace, KPI detail pages, and charts
  - Data entry still uses raw values (no confusion)
- **🔄 Organization Switcher**: Modern dropdown in navbar
  - One-click organization switching without logout
  - Shows current organization with icon
  - Lists all accessible organizations
  - Modern UI with user info, org switcher, and actions
  - Full dark mode support
- **📈 Qualitative KPI Historical Trends**: Charts now work for all value types
  - Risk, Positive Impact, Negative Impact, Level, Sentiment
  - Stepped line charts with color-coded points
  - Y-axis shows text labels (e.g., "! Low", "!!! High")
  - Same chart system as numeric KPIs
- **🎯 Smart Rollup Scaling**: Intelligent scale selection for aggregations
  - When rolling up KPIs with different scales, uses the largest (millions > thousands > default)
  - Ensures appropriate precision for aggregated values
  - Example: Rolling up 50k + 1.25M shows as 1.3M (not 1,300,000)

### Changed
- **KPI Detail Page**: Entry form moved to top for better UX
  - No more scrolling to enter values
  - Compact horizontal layout (3 columns)
  - Clear button added
  - Info cards and contributions table below
  - Edit button scrolls to top with highlight
- **Decimal Formatting**: Smart precision handling
  - When using scale, automatically shows at least 2 decimals
  - User can override with display_decimals field
  - Respects value type's decimal_places setting
  - Clean display with trailing zero removal

### Database
- Migration `c8f5a9b2e3d1_add_display_scale_to_kpi_configs.py` - Added display_scale column
- Migration `d9e6f8a4b5c2_add_display_decimals_to_kpi_configs.py` - Added display_decimals column

## [1.14.5] - 2026-03-09

### Fixed
- **Comment Deletion with Mentions**: Fixed cascade delete for comments containing @mentions
  - Added `ON DELETE CASCADE` to `mention_notifications` foreign key constraint
  - Added `passive_deletes=True` to SQLAlchemy relationship in `app/models/cell_comment.py`
  - Comments with mentions can now be deleted without foreign key constraint errors
- **Deployment Migration**: Fixed `render.yaml` to run `flask db upgrade` in `startCommand` instead of `buildCommand`
  - Ensures database migrations run before app starts, not during build

### Database
- Migration `a7d3e4f2b8c9_fix_mention_cascade_delete.py`

## [1.14.4] - 2026-03-09

### Added
- **🔒 Comment Permissions System**: Granular control over comment access per organization
  - **View Comments** permission: See existing comments, mentions bell, recent comments on dashboard
  - **Add Comments** permission: Create new comments (requires View permission)
  - Permissions managed in user create/edit forms with dependency logic
  - Global admins bypass all permission checks
  - API enforcement: 403 responses for unauthorized access
  - Database columns: `can_view_comments`, `can_add_comments` in `user_organization_memberships`

### Changed
- **Comment Icon UX**: Smarter visibility based on permissions
  - Users who can add: 💬 icon always visible
  - Users who can only view: 💬 icon only shows when comments exist (count > 0)
  - Prevents misleading empty state for view-only users
- **Empty State Message**: Changed from "Be the first to comment!" to "No comments yet."
- **Admin UI**: "Add Comments" checkbox automatically disables when "View Comments" unchecked

### Database
- Migration `f3a9b2c1d5e7_add_comment_permissions.py`

## [1.14.3] - 2026-03-09

### Changed
- **🏛️ Redesigned Spaces Admin Page**: Modern card-based layout with icons
  - Added space icons (🏢) for visual identification
  - Improved dark mode support with proper contrast
  - Enhanced visual hierarchy and spacing

## [1.14.2] - 2026-03-09

### Fixed
- **Dark Mode Readability**: Improved overall contrast and text visibility
  - Enhanced color scheme for better readability in dark mode
  - Fixed border colors and background contrasts
  - Improved form element visibility

## [1.14.1] - 2026-03-08

### Fixed
- **Level Visibility Toggle Issues**: Complete fix for level show/hide functionality
  - Pills now properly toggle between blue (visible) and gray (hidden) using inline styles
  - Rows correctly hide when level is disabled
  - Rows correctly reappear when level is re-enabled (checks parent expansion state)
  - Fixed double-firing of click events that caused immediate toggle-back
  - Auto-collapse then expand on page load for proper initial tree state
  - Event bubbling prevented with stopPropagation() and preventDefault()
- **Dark Mode Readability**: Improved contrast and visibility
  - Lightened background from #0a0a0a to #1a1a1a for better readability
  - Increased level-specific colors for better visual distinction
  - Restored proper indentation hierarchy (2.5rem to 10rem with !important)
  - Fixed border colors from #333 to #444 for better separation
- **CSRF Token Error**: Fixed 500 error when accessing governance bodies list after creation
  - Pass FlaskForm instance to template for proper CSRF token generation
  - Replace invalid csrf_token() call with delete_form.hidden_tag()

### Changed
- Level visibility controls now use inline styles with !important for guaranteed visual updates
- Simplified updateLevelVisibility() logic to work with expand/collapse functions
- Removed duplicate CSS rules that caused pill color conflicts

## [1.14.0] - 2026-03-08

### Added
- **🎨 Modern Workspace UI**: Complete interface redesign with dark mode and level visibility controls
  - True dark mode theme with deep black background (#0a0a0a) and high contrast text
  - Modern compact toolbar with gradient background and pill-shaped filter buttons
  - Level visibility controls: Toggle display of Spaces, Challenges, Initiatives, Systems, KPIs
  - Quick stats bar showing active filters and counts
  - Icons for each hierarchy level: 🏢 Spaces, 🎯 Challenges, 💡 Initiatives, ⚙️ Systems, 📊 KPIs
  - Color-coded left borders (4px) for visual hierarchy
  - Rollup indicator (Σ symbol) for aggregated values
  - Sticky table headers and first column
  - Smooth transitions and hover effects

### Fixed
- **Filter Logic Bug**: Governance body filters now work correctly
  - Auto-select all governance bodies when none chosen (smart default)
  - Empty selection correctly hides all KPIs (was showing everything before)
  - Fixed issue where unchecking GEN still showed KPIs
- **Version Display**: Login page now shows correct version "CISK Navigator v1.14.0"

### Changed
- Enhanced filter UX with clickable pills (no visible checkboxes)
- Modern expand/collapse icons with hover effects
- Level-specific dark colors for better visual distinction
- Improved spacing and typography throughout workspace

## [1.13.0] - 2026-03-08

### Added
- **🏛️ Governance Bodies System**: Full CRUD system for committees/boards/teams oversight
  - Organization-level governance bodies with name, abbreviation, description, and color
  - Many-to-many relationship with KPIs (junction table: kpi_governance_body_links)
  - Default "General" governance body created for each organization (renamable, not deletable)
  - Full color picker for visual identification
  - Drag-to-reorder interface for governance bodies
  - Permission system: `can_manage_governance_bodies` (defaults to true)
  - KPIs must belong to at least one governance body
  - Workspace filtering by multiple governance bodies
  - Color-coded badges on KPIs showing governance assignments
  - Governance body management at `/org-admin/governance-bodies`

- **🗄️ KPI Archiving**: Preserve historical data without workspace clutter
  - Archive/unarchive KPIs with full audit trail
  - Tracks who archived and when (`archived_by_user_id`, `archived_at`)
  - Archived KPIs are read-only (no new contributions accepted)
  - Hidden by default with "Show Archived KPIs" filter toggle
  - Visual distinction: grayed out with archive badge (60% opacity)
  - All historical data preserved (contributions, snapshots, comments)
  - Easy to unarchive if needed (fully reversible)
  - Warning banner on archived KPI detail pages

### Database Schema
- New tables: `governance_bodies`, `kpi_governance_body_links`
- Added to `kpis`: `is_archived` (Boolean), `archived_at` (DateTime), `archived_by_user_id` (Integer)
- Added to `user_organization_memberships`: `can_manage_governance_bodies` (Boolean, default true)
- Migration auto-creates "General" governance body for existing organizations
- Migration links all existing KPIs to "General" governance body
- Migrations: `597259f31427`, `e6f86e8171ac`

### Changed
- KPI create/edit forms include governance body selection (checkboxes, minimum 1 required)
- User create/edit forms include governance bodies permission checkbox
- Admin dashboard shows governance bodies card with count
- Workspace filter section expanded with governance body pills and archive toggle

## [1.12.0] - 2026-03-08

### Added
- **Per-Organization User Permissions**: Comprehensive permission system allowing granular control over what users can create/edit/delete
  - 6 permission types: Spaces, Value Types, Challenges, Initiatives, Systems, KPIs
  - Permissions configurable per organization during user creation/editing
  - Global administrators automatically bypass all permission checks
  - UI buttons hidden when user lacks permission
  - Direct URL access blocked with flash message and redirect
- Permission management UI in user create/edit forms with collapsible per-organization sections
- 20 routes now protected with `@permission_required` decorator
- User model methods: `can_manage_spaces()`, `can_manage_value_types()`, `can_manage_challenges()`, `can_manage_initiatives()`, `can_manage_systems()`, `can_manage_kpis()`

### Changed
- User-organization membership now includes 6 permission boolean columns (all default to TRUE)
- User edit form now shows existing permissions for easy modification
- Organization assignment UI changed from multi-select dropdown to checkboxes with expandable permission controls

### Database
- Migration `119d8257cb6a`: Add 5 permission columns to user_organization_memberships
- Migration `b8447fd59186`: Add can_manage_spaces column

## [1.11.10] - 2026-03-08

### Fixed
- **Password Reset Bug**: Password field no longer auto-populated when editing users, preventing unintended password resets
- Password field now explicitly cleared on form load with `autocomplete="new-password"`
- Password validation improved: only processes if field has actual content (strips whitespace)

### Added
- **Manual Password Change Control**: New "Force Password Change on Next Login" checkbox in user edit form
- Admins can now control must_change_password flag without resetting password

### Changed
- Organization assignment UI improved: replaced multi-select dropdown with checkboxes in scrollable container (max-height: 200px)
- Better visual hierarchy for user management forms

## [1.11.9] - 2026-03-08

### Added
- **User Profile Page**: New profile page at `/auth/profile` showing user information
  - Editable display name and email fields
  - Account status badges (Active, Global Admin)
  - Organization memberships list
  - Link to change password functionality
- Profile link added to navbar with person icon

### Changed
- Navbar updated: "Profile" link replaces direct "Change Password" link
- Change password remains accessible from profile page

## [1.11.7] - 2026-03-08

### Fixed
- **Chart Display**: Current value now included in trend charts (was only showing historical snapshots)
- **Same-Day Snapshots**: Multiple snapshots created on same day now display as separate points using full timestamps
- Chart now shows complete time series: snapshots + current value

### Changed
- Chart date labels use full timestamp (YYYY-MM-DD HH:MM:SS) instead of just date
- Increased snapshot history limit from 10 to 50 points on charts

## [1.11.6] - 2026-03-08

### Fixed
- **Chart API Mismatch**: Fixed API returning `data.snapshots` when JavaScript expected `data.history`
- Charts now display properly when snapshots exist
- Added flash message to confirm snapshot creation (debugging aid)

### Changed
- API endpoint `/api/kpi/<id>/history` now returns correct data structure
- History array ordered chronologically (oldest first) for proper chart display

## [1.11.5] - 2026-03-08

### Fixed
- **Baseline Snapshot Feature Restored**: Re-added `baseline_snapshot_id` field after accidental removal
- Implemented without Foreign Key constraint to avoid circular dependency issues

### Added
- `@property baseline_snapshot` for fetching baseline snapshot object
- Baseline snapshot allows tracking progress from a specific starting point

## [1.11.4] - 2026-03-08

### Changed
- Temporarily removed `baseline_snapshot_id` field (causing circular FK issues)
- Core target tracking features (target_value, target_date) still functional

## [1.11.3] - 2026-03-08

### Fixed
- Changed from implicit `backref='snapshots'` to explicit `back_populates='snapshots'`
- Resolved ambiguity between multiple foreign key relationships

## [1.11.2] - 2026-03-08

### Fixed
- Made `baseline_snapshot` relationship view-only to prevent SQLAlchemy synchronization issues

## [1.11.1] - 2026-03-08

### Fixed
- **Circular Foreign Key Fix**: Resolved ambiguous foreign key relationship between KPISnapshot and KPIValueTypeConfig
- Added explicit `foreign_keys` parameters to both relationship definitions
- Added `post_update=True` to handle circular dependency

## [1.11.0] - 2026-03-08

### Added
- **🎯 Target Tracking Feature**
  - Set optional target value and date when creating/editing KPIs
  - Target displayed as dashed red line on historical trend charts
  - Progress indicator (🎯 X%) shown in workspace grid
  - Targets are per KPI-value type configuration
  - Database migration: `0e11e44f5949_add_target_tracking_fields.py`

### Database Schema
- Added `target_value` (Decimal) to `kpi_value_type_configs`
- Added `target_date` (Date) to `kpi_value_type_configs`
- Added `baseline_snapshot_id` (Integer) to `kpi_value_type_configs`

## [1.10.2] - 2026-03-08

### Fixed
- **Smart Value Entry Bug Fixes**
  - Fixed `SnapshotService.create_snapshot()` method name (should be `create_kpi_snapshot()`)
  - Fixed form auto-submission after modal selection (use `requestSubmit()` instead of `submit()`)
  - Fixed snapshot deduplication preventing multiple snapshots on same day (added `allow_duplicates` parameter)
  - Fixed CSRF token errors in templates (use `FlaskForm` instance instead of `csrf_token()` function)

## [1.10.1] - 2026-03-07

### Added
- **📝 Editable List Views**
  - Dedicated list views for Challenges, Initiatives, and Systems
  - Inline editing and management capabilities
  - Improved navigation and organization management

### Changed
- Enhanced admin interface organization
- Better separation of concerns between entity types

## [1.10.0] - 2026-03-08

### Added
- **🔄 Smart Value Entry Feature**
  - Modal prompt when entering value on cell with existing consensus
  - Two modes:
    - **NEW data (time evolved)**: Auto-creates snapshot, replaces all contributions
    - **Contributing to CURRENT period**: Adds contribution normally
  - Automatic snapshot creation with label "Auto: Before update by [user]"
  - Preserves historical data when values change over time

### Changed
- Enhanced KPI cell detail page with entry mode selection
- Added JavaScript modal for entry mode choice
- Modified workspace routes to handle entry_mode parameter

## [1.9.5] - 2026-02-XX

### Added
- Decimal places editing for numeric value types
- Configurable precision display

### Fixed
- Value formatting issues in workspace display

## [1.9.4] - 2026-02-XX

### Added
- Value type edit functionality
- Admin interface improvements

## [1.9.3] - 2026-02-XX

### Fixed
- CSRF token errors in forms
- Auto-login for single organization users

### Added
- Streamlined login experience

## [2.1.0] - 2026-03-07 - **Major Feature Release**

### Added
- **📊 Dashboard & Overview**
  - Interactive dashboard with statistics cards
  - Recent snapshots widget with View/Compare buttons
  - Recent comments widget showing latest discussions
  - Quick actions for common tasks
  - Getting started guide for new users

- **📈 Time-Series Tracking**
  - Snapshot system for capturing KPI values over time
  - Historical view to see workspace state as of any date
  - Automatic trend indicators (↗️↘️→) on KPI cells
  - Snapshot comparison with side-by-side analysis
  - Custom labels for organizing snapshots

- **📉 Charts & Visualization**
  - Interactive line charts using Chart.js 4.4
  - Trend visualization on KPI detail pages
  - Tooltips showing exact values and dates
  - Responsive design adapting to screen size

- **💬 Comments & Collaboration**
  - Cell-level comments on any KPI
  - @Mention system with autocomplete
  - Threaded replies with full nesting support
  - Resolve/unresolve discussions
  - Unread mentions tracking with bell notification (🔔)
  - Keyboard navigation in mention dropdown

- **🎨 Enhanced Navigation**
  - Dashboard as new home page
  - Three-tier navigation: Dashboard → Workspace → Administration
  - Bootstrap Icons for visual clarity

### Database Schema
- New tables: `kpi_snapshots`, `rollup_snapshots`, `cell_comments`, `mention_notifications`
- Migration: `498afb934c2e`

### API Endpoints (15 new routes)
- Snapshot management (create, list, view, compare)
- Comment CRUD operations
- Mention tracking and notifications
- User search/autocomplete

## [2.0.0] - 2026-03-XX - **Major Release**

### Changed
- **🗄️ Database Migration**: SQLite → PostgreSQL for data persistence
- **🎨 Color System Refactor**: Moved colors from ValueType to KPI level

### Added
- **📊 New Aggregation Formulas**
  - Median (outlier-resistant aggregation)
  - Count (quantity tracking)
  - Total of 6 formulas: sum, min, max, avg, median, count

- **🎭 New Value Types**
  - Level (●●●): Generic 3-level scale
  - Sentiment (☹️😐😊): Emotional states
  - All qualitative types use 3-level scale

- **📤 Export & Backup**
  - Excel export with hierarchical row grouping
  - YAML export/import for structure backup
  - Organization cloning for testing/training

- **🎯 UX Improvements**
  - Drag-and-drop value type reordering
  - Smart deletion with impact preview
  - Improved visual hierarchy

### Infrastructure
- Deployed on Render with persistent PostgreSQL
- Automatic migrations on deployment
- psycopg3 driver for Python 3.13+ compatibility
- Multi-layer data loss prevention

---

## Version Numbering

- **Major (X.0.0)**: Breaking changes, major architecture changes
- **Minor (1.X.0)**: New features, non-breaking changes
- **Patch (1.0.X)**: Bug fixes, minor improvements

## Links

- [Repository](https://github.com/mounirdous/CISK-Navigator)
- [Documentation](README.md)
- [Architecture](ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT.md)
