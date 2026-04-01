# 🧭 CISK Navigator v7.7.0

**Production-ready data collection and aggregation system** for tracking KPIs across hierarchical organization structures.

![Version](https://img.shields.io/badge/version-7.7.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Database](https://img.shields.io/badge/database-PostgreSQL-blue)
![License](https://img.shields.io/badge/license-MIT-orange)
![Tests](https://img.shields.io/badge/tests-330%20passing-success)

## ✨ What's New in v5.x (March 2026)

### 🎯 **Impact Assessment & True Importance**
- **Configurable 3-level impact scale** per organization — custom symbols, weights, colors
- **Impact on all 5 entity types** (Space, Challenge, Initiative, System, KPI) — set from edit forms or click-to-assign in workspace
- **True Importance computation** — product of impact weights through the full hierarchy chain, normalized to Level 1/2/3
- **3 compounding methods** — Simple Product, Geometric Mean, Toyota QFD (fuzzy lookup table)
- **Editable QFD matrix** — admin can customize the Toyota QFD lookup table
- **Impact documentation page** — standalone page explaining each method with formulas, examples, comparison table
- **Impact badges in workspace tree** — assessed (outline) + computed (filled) per entity

### 🎄 **3-Level Xmas Tree (Progressive Disclosure)**
- **Badge mode cycle** (Level 0 / 1 / 2) across ALL pages: Workspace, Action Register, Initiative Review, Map Dashboard, Decision Register, GB Dashboard
- Level 0 = minimal scan mode, Level 1 = standard, Level 2 = full detail with filters and stats

### 📋 **Decision Log System**
- **Structured decisions** in progress updates — what, who, tags, entity mentions, governance body
- **Decision Register page** with search, date/tag/RAG/initiative filters, CSV export
- **Multi-tag decisions** with chip UI and configurable tag categories
- **Entity mentions** in decisions with bi-directional links (workspace ↔ decision register)

### 📊 **Dashboards Suite**
- **Challenges Dashboard** — RAG dot strips, coverage bars, impact badges, decision counts, space/RAG filters
- **Systems Dashboard** — reuse badges, KPI health dots, portal chips, shared/orphan filters
- **KPI Dashboard** — target progress bars, impact badges, consensus status, GB/target-status filters
- **Impacts Dashboard** — SVG coverage rings, entity heatmap, per-type coverage, gap analysis table
- **Governance Dashboard** — per-GB view with KPIs, Actions, Decisions, Initiatives
- **Geographies Dashboard** — world map with country coloring, marker clustering
- All dashboards: 🌱/🌲/🎄 xmas tree + ★ impact filter + preset save/load
- Dashboards menu organized: CISK Entities (with branding logos) + Other

### 🧭 **Entity Navigation**
- **Sequential prev/next arrows** on all 7 entity edit pages
- **Bridge navigation** — skip across parent boundaries
- **Initiative Review focus mode** — sorts by impact level with visual separators

### 🗺️ **Map Improvements**
- Country coloring fix (continuous render for viewport-based matching)
- Marker clustering with cluster popup list
- 3-level xmas tree for map dashboard

### 🏗️ **Strategic Features**
- **Strategic Pillars** — editable strategy with icon picker, glassmorphism view page
- **Value Dimensions page** — card view of all value types with descriptions
- **Enriched CISK Theory page** — Ecosystem, Execution Engine, Intelligence Layer, Strategic Context sections

### 🔗 **Portal Systems (System as CISK)**
- **Link a system to another CISK organization** — when a system IS itself a CISK workspace, link it for recursive navigation
- **Portal chip in workspace tree** — sleek gradient pill with linked org logo, name, and arrow; click opens the linked workspace in a new tab
- Configurable from system create/edit forms; included in backup/restore

### ⚙️ **Org Admin**
- **Strategy toggle per organization** — enable/disable strategic pillars feature from org admin dashboard
- **Comprehensive sample import** (`docs/SAMPLE_IMPORT.json`) — 3 spaces, 8 challenges, 12 initiatives, 12 systems, ~35 KPIs, 8 action items covering a CIO first-year scenario

### ✨ **Workspace UX**
- **Cinematic loading screen** — glassmorphism backdrop, dramatic org logo reveal, entity icons with colored glow rings, ripple pulses, connecting beam animation
- **3-level xmas tree** (🌲/🎄/🎄✨) — Level 0 = tree only, Level 1 = tree + values, Level 2 = full decorations + Impact column
- **Impact filter** (☆/○/★/★★/★★★) — cycling icon filters all entity levels by true importance; available on workspace, action register, and decision register
- **Tree state persistence** — expanded/collapsed nodes survive navigation and page reloads via localStorage
- **Pre-computed rollups** — 22x faster workspace loads (220ms vs 6s); incremental recompute on data changes (5 entities vs 180); auto-invalidation on saves; Super Admin toggle
- **5 impact compounding methods** — Simple Product, Geometric Mean, Toyota QFD, Toyota Weighted (DS), Toyota Weighted (Full); configurable reinforcement weights
- **Decision Register** — unified decision management with tags, entity mentions, GB selector, presets, filters, xmas tree, impact filter. Decisions created from initiative review or standalone — single `Decision` model, no more JSON blobs
- **Click-based info windows** replacing hover tooltips — draggable with touch support
- **Tree state persistence** via localStorage — survives navigation and page reload
- **KPI single value type** — radio button at creation (was incorrectly multi-select)

## ✨ What's New in v3.4.x (March 2026)

### 🔗 **URL Link Intelligence**
- **Sync URL probe on save** — detects file type (PDF, Word, Excel, PowerPoint, image, video, archive, code, web page) and validates reachability on every link save
- **Live URL checker in forms** — spinner + type icon + status badge appear as you type/paste, before saving
- **SharePoint / OneDrive type detection** — recognises `/:w:/`, `/:x:/`, `/:b:/`, `/:p:/` URL patterns without network requests; 1drv.ms short codes supported
- **Link Health dashboard** (`/org-admin/link-health`) — table of all org entity links with real-time SSE-driven bulk check, live progress bar, row-level status updates and live counters; filter-scoped checking
- **Consistent type icons everywhere** — same Bootstrap icons (PDF 📕, Word, Excel, PowerPoint…) in workspace link modal, navbar search, global search, and Link Health
- **Status badges** on all entity link displays: Valid / Login required / Broken / Unreachable / Not checked

### 🔒 **Mention System — Rename-Safe**
- **Cell comments**: `@user` and `@"Entity"` mentions now resolve using stored IDs at render time — renaming a user login or entity no longer breaks existing mentions
- New `CommentUserMention` table stores `(comment_id, user_id, mention_login)` at write time
- **JSON backup/restore** (action item mentions & stakeholder entity links): now use `json_id` cross-references (stable within-backup IDs) instead of entity names — eliminates same-name collision risk on restore; fully backward-compatible

### 🗂️ **Action Register UX**
- Table / Timeline view toggle moved from the filter panel into the blue header bar

## ✨ What's New in v2.32.x (March 2026)

### 💾 **Persistent Workspace Preferences (per user, per org)**
UI preferences are now saved to the database and restored automatically — works across devices:
- **Badges/decorations toggle** (🎄) — remembered across sessions; hide cluttered icons for a cleaner view
- **Level Focus mode** — remembered across sessions; dims parent levels to highlight the deepest expanded level when using the ▼/▲ step buttons

### 🎯 **Level Focus Mode**
When stepping through tree levels with the ▼/▲ buttons, parent rows are dimmed so you can focus on the deepest active level:
- Toggle in the **Filters & Display → Display Options** panel
- Resets automatically on any manual expand/collapse action
- Tooltip added to the toggle explaining its behaviour

### 📁 **Preset Improvements**
- Tree collapse/expand state is now **saved and restored with presets**
- Saving a preset is always enabled — no longer blocked when no data filter is set
- Preset selector moved to the workspace **toolbar header bar** (compact Bootstrap dropdown, saves vertical space)

### ↕️ **Expand/Collapse One Level**
Two new buttons in the workspace toolbar step through the tree one level at a time (▼/▲), sitting between the expand-all and collapse-all buttons.

### 🔗 **URL Links in Search**
- URL links now appear in the **navbar live search** and **global search** with an "Open" button (opens in new tab)
- "URL Links" filter checkbox added to the search filter panel
- Duplicate URL results deduplicated; cross-org results correctly excluded

## ✨ What's New in v2.17.7 (March 2026)

### 🛠️ **Workspace Fixes**
- **Collapse/expand fully works** — collapsing a row at any level (space, challenge, initiative, system) now immediately hides all child rows; fixed Alpine.js reactivity issue in nested loops
- **Collapse state preserved on data reload** — collapsed rows stay collapsed after background data refreshes (e.g. after editing a KPI value)
- **System edit link** — pencil icon on system rows in edit mode now navigates to the edit system page (was showing a v1 alert); returns to workspace after save

### 🎨 **Branding Icons on Edit Pages**
- Edit pages for Space, Challenge, Initiative, System, and KPI now show the **per-instance logo** first, falling back to the entity-type default logo, then the icon — no more hardcoded symbols

### 🔗 **Action Items**
- "View in Action Items" link from Generate Actions modal now correctly points to `/toolbox/actions/`

---

## ✨ What's New in v2.16.0 (March 2026)

### ⚡ **Generate Actions from Deliverables & Success Criteria**
Turn initiative milestones into action items in seconds:

**Smart Parsing**:
- Lightning button on the Deliverables section of the initiative form (view mode)
- Parses all deliverable rows and success criteria rows automatically
- Extracts title from milestone text, due date from the date column

**Intelligent Pre-fill**:
- **Title** — milestone or success criterion text
- **Owner** — current user (dropdown of all org members)
- **Priority** — suggested from initiative impact level (High impact → High priority)
- **Due date** — auto-parsed from "Week N" (configurable reference date: today or custom picker), "Q1–Q4 YYYY", or ISO date
- **Status** — Draft by default
- **Visibility** — Shared by default

**Deduplication**:
- Detects actions already linked to this initiative with the same title
- Duplicate rows shown with an "exists" badge and unchecked by default
- No accidental duplicates created

**Bulk Creation**:
- Review and edit all rows before creating
- Uncheck any row to skip it
- One click creates all selected actions and links them to the initiative

### 📝 **Initiative Form Improvements**
- **Header Save button** — Save button added next to "Back to Workspace" in edit mode (no more scrolling to bottom to save); returns to workspace after save
- **Branding icons** — System and KPI entries in initiative view use stored branding (logo/icon) instead of hardcoded Greek letters (Φ/Ψ)
- **Contribution decimal formatting** — Editing a contribution pre-fills the value with correct decimal places (e.g. `10` not `10.00000`)
- **Edit contribution skips modal** — Editing an existing contribution no longer triggers the "new data vs contributing" mode selector
- **View mode redesign** — Left-aligned content, vertical-align top, dynamic font sizing (short text larger, long text smaller), tight padding for maximum info density, colored category headers, styled deliverable/steps tables

### 🛡️ **Bug Fixes**
- Organization deletion no longer fails with `NotNullViolation` on `cell_comments` — `passive_deletes=True` added to defer FK handling to DB-level CASCADE
- Aggregation formula options consistent across all 3 surfaces (create value type, edit value type, rollup config): List → Mode only; Numeric → sum/min/max/avg/median/count; Qualitative → min/max/avg

### 💾 **Backup/Restore Completeness**
- Backup and restore now cover **initiative form fields**: mission, responsible person, team members, handover organization, deliverables, success criteria, impact level, impact rationale
- Backup and restore now cover **Porter's Five Forces** data

## ✨ What's New in v2.15.0 (March 2026)

### 📋 **List Value Type**
New "list" kind for choice-based KPIs (Yes/No, status, categories):

**Features**:
- Define any number of options with custom labels and colors (per-option color picker)
- **Mode aggregation** (most frequent choice) with tie-breaking — returns no result on tie
- Full rollup and consensus support: list values propagate up the full hierarchy with colored badges
- Target support: set a target list value per KPI config
- Snapshot support: `list_value` saved in KPI and rollup snapshots
- Workspace display: colored badge at all levels (KPI, system, initiative, challenge, space)
- Backup/restore: `list_options` and `list_value` included in JSON and YAML exports

**Aggregation Consistency**:
- List value types show only "Mode (most frequent)" in all formula selectors
- Numeric types show sum/min/max/avg/median/count
- Qualitative types show min/max/avg

## ✨ What's New in v2.14.0 (March 2026)

### 🧪 **Test Suite Runner with Celery + Redis**
Production-ready async test execution with beautiful UI:

**Async Background Processing**:
- **Celery + Redis** for proper task queueing
- Tests run in background without blocking server
- Flask stays responsive during test execution
- Scalable architecture for production

**Real-Time Progress Monitoring**:
- Beautiful loading overlay with animated spinner
- Live progress steps (Queueing → Executing → Complete)
- Elapsed time counter
- AJAX polling for status updates
- Automatic redirect when done

**Test Results & Coverage**:
- Execute full pytest suite from Health Dashboard
- Visual progress bars and circular charts
- Module-level code coverage breakdown
- Color-coded coverage (high/medium/low)
- Failed test details with error messages
- Raw pytest output for debugging

**Test History & Trends**:
- Track test execution history over time
- Interactive Chart.js graphs:
  - Pass rate trends
  - Coverage progression
  - Test distribution
  - Execution duration
- See who ran tests and when

**How to Use**:
1. Start Redis: `brew services start redis` (or Render managed Redis)
2. Start Celery worker: `celery -A app.celery worker --loglevel=info --pool=solo`
3. Access: Global Admin → Health Dashboard → Run Test Suite
4. Tests run in background, page polls for completion

**Production Deployment on Render**:
- Add managed Redis service
- Set `REDIS_URL` environment variable
- Add Celery worker as background worker
- See full deployment guide below

## ✨ What's New in v2.11.0 (March 2026)

### 🎩 **Demo Data Generator**
Comprehensive demo organization creator for testing and demonstrations:

**Three Fun Scenarios**:
- **Riverside FC** - Community football club with youth development
- **MyHealth Journey** - Personal health and wellness transformation
- **Green Home Project** - Eco-friendly sustainable living

**What's Generated**:
- ✅ Complete entity hierarchy (Spaces, Challenges, Initiatives, Systems, KPIs)
- ✅ Stakeholder ecosystem (5-10 stakeholders per org, 2-3 maps, relationships)
- ✅ Entity-stakeholder links (owners, reviewers, contributors, interested parties)
- ✅ Historical snapshots (configurable years, realistic trends and variations)
- ✅ KPIs with different frequencies (Daily, Weekly, Monthly, Quarterly, Yearly)
- ✅ Linked KPIs and formula KPIs
- ✅ Mix of public/private spaces
- ✅ Action items in various states
- ✅ Demo users with configurable emails

**Features**:
- Drop & recreate existing organizations (clean start every time)
- Configurable years of history (1-5 years)
- Configurable snapshot frequency (daily, weekly, monthly)
- Realistic data with trends (+2%/snapshot) and random variation (±10%)
- Super admin only (destructive operation)

## ✨ What's New in v2.10.7 (March 2026)

### 📊 **Weekly Pivot Analysis**
New time-series view for finer-grained snapshot analysis:

**What's New**:
- **Weekly View** added to Snapshot Pivot Analysis
- Snapshots now grouped by ISO week (Week 1-53)
- Complements existing Daily, Monthly, Quarterly, and Yearly views

**Why This Matters**:
- More granular than monthly, less noisy than daily
- Perfect for tracking weekly progress on short-term initiatives
- Uses ISO 8601 week calendar for consistency

## ✨ What's New in v2.10.6 (March 2026)

### 🚀 **Critical Workspace Fixes**
Three major regression bugs fixed that were blocking normal workflow:

**v2.10.6 - Workspace Data Not Refreshing** (CRITICAL)
- **Issue**: After creating entities (space, challenge, initiative, system, KPI), flash message appeared but entity was invisible until manual refresh
- **Fix**: Workspace now reloads data from server when returning with `auto_edit=1` parameter
- **Impact**: Users can now see newly created entities immediately

**v2.10.5 - Empty Entities Hidden** (CRITICAL)
- **Issue**: Newly created spaces/challenges/systems invisible until populated with children
- **Root Cause**: Filter logic was hiding entities with no children (`challenges.length > 0`, `systems.kpis.length > 0`)
- **Fix**: Removed aggressive filters - all entities now visible regardless of children
- **Impact**: Normal workflow restored (Create → Populate → Build hierarchy)

**v2.10.4 - Filter Panel Auto-Expansion**
- **Issue**: After entity creation, filter panel stayed expanded hiding the workspace tree
- **Fix**: When `auto_edit=1` present, force collapse filters and enable edit mode
- **Result**: Clean workspace view after entity creation

### 🔐 **Porter's Five Forces Permission**
New granular permission for competitive analysis editing:

**New Permission**:
- **Can Edit Porter's** - Control who can edit Porter's Five Forces analysis

**Why This Matters**:
- Previously: Only org admins could edit Porter's Five Forces
- Now: Fine-grained control separate from org admin role
- View access remains available to all members

### 🔧 **CSRF Token Fixes**
Fixed missing CSRF tokens in 12 create/edit routes:
- Porter's Five Forces edit page
- Space create/edit/SWOT
- Challenge create/edit
- Initiative create/edit
- System create/edit
- KPI create
- Value Type create/edit
- Governance Body create/edit

### 🎨 **Workspace UI Improvements**
- Added + icon at organization level to create spaces (consistent with other entity levels)
- Complete hierarchy now has + icons: Organization → Space → Challenge → Initiative → System → KPI

### 📝 **Documentation**
- Added `CLAUDE.md` with semantic versioning guidelines
- Clarified x.y.z version bump rules (major/minor/patch)

## ✨ What's New in v1.33.32 (March 2026)

### 🔗 **Entity Links & Resources**
- **Attach URLs to Any Entity**: Link documents, wikis, Jira tickets, GitHub repos, or any web resource to Spaces, Challenges, Initiatives, Systems, or KPIs
- **Public/Private Sharing**:
  - **Public links**: Visible to entire organization
  - **Private links**: Visible only to creator
- **Smart Icon Detection**: Automatically recognizes and displays appropriate icons for:
  - 📄 Google Docs, Sheets, Slides
  - 🐙 GitHub repositories and issues
  - 📑 PDF files
  - 🖼️ Images
  - 🌐 Generic web pages
- **Workspace Integration**:
  - Link icon (🔗) appears next to entities that have links
  - Hover to see popup with all clickable links
  - Persistent hover: popup stays visible when moving mouse to click
- **Edit Page Management**:
  - Links section on all entity edit pages
  - Add new links inline without leaving the page
  - Delete your own links
  - Manual reordering support
- **URL Validation**: Enforces valid URLs (http://, https://, ftp://)
- **Use Cases**:
  - Link to project documentation (Google Docs, Confluence)
  - Reference Jira tickets or GitHub issues
  - Connect to external dashboards or reports
  - Attach meeting notes or presentations
  - Share relevant resources with team

### 🎨 **UI/UX Improvements**
- **Consistent Edit Icons**: All entities now use pencil icon (✏️) for editing
- **Fixed Space Edit**: Pencil button now properly navigates to space edit page

### 🐛 **Bug Fixes**
- Fixed workspace AttributeError when displaying KPIs
- Improved CSRF token handling for entity links

## ✨ What's New in v1.32.0 (March 2026)

### 🗺️ **Complete Geography Management System with Professional Mapping**
- **3-Tier Hierarchy**: Regions → Countries → Sites for organizing KPIs by location
- **Professional Map Dashboard**: **Mapbox GL JS** with built-in country boundaries
  - **Colored Country Polygons**: Countries with KPIs filled bright green, others gray
  - **Smart KPI Visualization**: Different marker styles by level:
    - 🌍 **Region Level** (Blue gradient) - Largest markers for regional KPIs
    - 🏳️ **Country Level** (Green gradient) - Medium markers for country KPIs
    - 📍 **Site Level** (Purple gradient) - Smaller markers for site KPIs
  - **Interactive Features**: Hover highlighting, click for popups with KPI details
  - **KPI Values Displayed**: Shows current value, unit, target, period on map
  - **Auto-Zoom**: Fits to show all countries and sites with KPIs
  - **Professional Quality**: Same mapping library used by Uber, Airbnb, NYT
- **Multi-Level KPI Assignment**: Assign KPIs at region, country, OR site level
  - **Hierarchical Checkbox Interface**: Auto-checks parent levels when child selected
  - **Constraint Enforcement**: Cannot uncheck parent if child still selected
  - **Intelligent Rollup**: Assignments cascade up the hierarchy
  - Coordinate display next to site/country names
- **Address Geocoding**: Auto-convert addresses to coordinates
  - Click "Get Coordinates from Address" button
  - Uses Nominatim API (OpenStreetMap - free)
  - Auto-fills latitude/longitude fields
- **Country Autocomplete**: Live search from 195+ georeferenced countries
  - Real coordinates for accurate map display
  - ISO codes for international standards
- **Full CRUD Admin UI**: Modern tree view with color-coded hierarchy
  - Purple gradients for regions
  - Green for countries with map coordinates
  - Red for sites with precise locations
  - Statistics cards (regions, countries, sites, KPIs by location)
  - Cascade delete protection
- **GeoJSON API**: RESTful endpoints for map data integration
- **Organization-Scoped**: Complete data isolation per organization
- **Audit Logging**: Full trail for all geography operations

**Navigation:**
- Organization Admin → Geography Management
- Dashboards → Map View

**Setup Required:**
- Free Mapbox account (50,000 map loads/month free tier)
- Set `MAPBOX_ACCESS_TOKEN` environment variable
- See "Mapbox Configuration" section below

**Use Cases:**
- Track KPIs across multiple office locations
- Visualize performance by geographic region (entire countries highlighted!)
- Identify location-specific trends and patterns
- Multi-site companies with regional operations
- Global organizations tracking country-level metrics

## ✨ What's New in v1.31.0 (March 2026)

### 🎨 **Dynamic Entity Colors & Branding Improvements**
- **Branding Color Persistence Fixed**: Colors now save properly and persist after page reload
  - Hidden icon fields added (server requires both color AND icon)
  - Custom entity colors appear in workspace tree view with light tints (6-15% opacity)
  - Visual consistency across the entire application
- **Rollup Gradient Colors**: Configuration page headers use dynamic gradients based on branding
  - Level 1 (KPI→System): gradient from KPI color to System color
  - Level 2 (System→Initiative): gradient from System through Initiative to Challenge color
  - Level 3 (Initiative→Challenge): gradient from Initiative through Challenge to Space color
  - Reflects organization's branding instead of hardcoded values
- **Simplified Rollup Headers**: Clearer, more concise level descriptions
  - Removed confusing "Primary/Secondary" text
  - Clean headers: "Level 1: KPI → System", "Level 2: System → Initiative", "Level 3: Initiative → Challenge"

### 🎨 **UI/UX Polish**
- **Dashboard Stat Box Heights**: All 7 stat boxes now uniform height for consistent appearance
- **Workspace Description**: Updated Open Workspace text to explicitly list all entity types
  - "View and manage Spaces, Challenges, Initiatives, Systems, KPIs and track progress"

## ✨ What's New in v1.28.0 (March 2026)

### 🎯 **Complete Target System with Visual Zones**
- **Three Target Types**:
  - **↑ Maximize** (at or above): Green zone ABOVE target line on charts
  - **↓ Minimize** (at or below): Green zone BELOW target line on charts
  - **± Exact** (at with tolerance band): Colored band (e.g., ±10%) on charts
- **Visual Indicators**: Target badges in tables (🎯↑ 🎯↓ 🎯±)
- **Chart Integration**: Dashed target lines with shaded acceptable zones
- **Pivot Table**: Show Targets toggle displays target value, date, type, and tolerance
- **Hover Tooltips**: Target details on bullseye icon (🎯)

### 📊 **Enhanced Snapshot Pivot Analysis**
- **Show Targets Column**: Toggle to display/hide target information
- **Target Badges**: Color-coded badges showing target type and tolerance
- **Target Date Display**: Shows deadline for each target
- **Smart Filtering**: Targets respect space/challenge/value type filters
- **Most Recent Snapshot**: Automatically uses latest snapshot when multiple exist per period

### 📥 **Comprehensive Excel Export**
- **Metadata Columns**: Organization, Space, Challenge, Initiative, System (before KPI)
- **Target Columns**: Target Value, Target Date, Target Direction, Tolerance %
- **Complete Hierarchy**: Full organizational context for each KPI
- **Filtered Export**: Respects all active filters (space, challenge, value type, date range)
- **Analysis Ready**: Import directly into BI tools with proper structure

### 🔍 **Live KPI Search for Quick Chart Building**
- **Instant Search**: Type to find KPIs from filtered results (200ms debounce)
- **Target Badges**: Shows 🎯↑ (maximize), 🎯↓ (minimize), 🎯± (exact) in results
- **One-Click Add**: Click result to add KPI to chart (auto-checks checkbox)
- **Already Selected Indicator**: Dimmed results with "Selected" badge
- **Toast Notifications**: Confirms KPI addition
- **No Scrolling**: Find KPIs without scrolling through large tables
- **Filter Aware**: Only searches within current space/challenge/value type filters

### 🧪 **Test Data Generator**
- **Comprehensive Script**: `create_full_fake_dataset.py`
- **10 Sample KPIs**: Examples of all target types:
  - 2 maximize (Revenue, Customer Satisfaction)
  - 3 minimize (Operating Costs, CAC, Support Response Time)
  - 2 exact with bands (Product Dev Time ±15%, Inventory ±10%)
  - 3 without targets (Marketing, R&D, Infrastructure)
- **36 Months of Data**: January 2024 - December 2026
- **Realistic Trends**: Trending up, down, or stable with volatility
- **Complete Hierarchy**: Space → Challenge → Initiative → System → KPIs

## ✨ What's New in v1.27.1 (March 2026)

### 🧪 **Comprehensive Rollup Testing**
- **28 New Unit Tests**: Complete type safety validation for rollup aggregations
- **Type Mixing Tests**: Decimal + float + int combinations work correctly
- **Edge Case Coverage**: Zero values, negatives, very large/small numbers, high precision
- **Real-World Scenarios**: Tests based on actual production data patterns
- **All Formulas Tested**: sum, min, max, avg, median, count
- **100% Passing**: Robust rollup functionality verified

### 🔢 **Rollup Type Safety Fixes**
- **Fixed Decimal/Float Mixing**: All aggregation formulas now handle mixed types correctly
- **Formula KPI Rollup**: Formula-calculated KPIs now participate in rollups to parent levels
- **Linked KPI Rollup**: Linked KPIs properly included in aggregations
- **Partial Data Support**: Rollups work with incomplete data (shows ⚠ indicator)
- **Consistent Return Types**: All aggregations return float for predictable behavior

### 🌍 **Global KPIs Feature**
- **No Governance Body Required**: KPIs can be created without governance body assignment
- **Always Visible**: Global KPIs shown regardless of governance body filters
- **Organization-Wide Metrics**: Perfect for KPIs that transcend specific committees

### 🎨 **UI/UX Improvements**
- **Consistent Navigation**: Standardized buttons across SWOT, Initiative Form, Porter's Five Forces
- **Better Table Display**: No multi-line wrapping, true auto-sizing columns
- **Collapsed Columns Fixed**: Content fully hidden in collapsed state
- **Clearer Labels**: "Back to Workspace" instead of just "Back"
- **Navbar Update**: Organization name badge now links to Dashboard

## ✨ What's New in v1.17.0 (March 2026)

### 🎯 **Reorganized Navigation**
- **Cleaner Structure**: Workspace → Dashboards → Admin (no more confusion!)
- **Main Workspace**: Primary KPI grid for day-to-day work
- **Dashboards Dropdown**: Overview, Executive, Analytics (all viewing options grouped)
- **Admin Dropdown**: Org Admin, Global Admin, Super Admin (all admin functions grouped)
- **User-Friendly**: New users can navigate intuitively

### 🎨 **Customizable Navigation Bar**
- **Position Choice**: Top (horizontal) or Left Sidebar (vertical)
- **Auto-Hide Option**: Navbar hides when not in use, shows on hover
- **User Preference**: Each user chooses their own layout
- **Smooth Animations**: Polished transitions for professional feel
- **Trigger Bar**: Visual indicator when navbar is hidden (hover edge to show)
- **Responsive**: Works perfectly on all screen sizes
- **Profile Settings**: Configure in User Profile → Navigation Bar Position/Auto-hide

### 🚀 **Executive Dashboard** (v1.16.0 → v1.17.0)
- **Traffic Light Status**: Green/Yellow/Red KPI health indicators
- **High-Level Metrics**: Active KPIs, On Target %, Needs Attention, At Risk
- **Governance Performance**: Track which governance bodies are on track
- **Top Performers**: KPIs exceeding targets
- **Activity Trends**: Weekly contribution graphs
- **Smart Insights**: Auto-generated recommendations
- **Export Options**: PDF, PowerPoint, Excel downloads
- **Compact Layout**: Traffic lights + chart side-by-side

### 🗄️ **Database Changes**
- **New Migration**: `j4d5e6f7g8h9_add_navbar_preferences.py`
- **New Columns**: `users.navbar_position` (default: 'top'), `users.navbar_autohide` (default: false)

## ✨ What's New in v1.16.0 (March 2026)

### 📋 **Audit Logging System**
- **Complete Audit Trail**: Tracks all create, update, delete, and archive operations
- **Comprehensive Coverage**: User management, Spaces, Challenges, Initiatives, Systems, KPIs, Value Types, Governance Bodies
- **Detailed Tracking**: Records who, what, when, old values, new values
- **Super Admin Access**: View audit logs from Super Admin panel
- **New Database Table**: `audit_logs` with migration `b2c3d4e5f6a7`
- **Centralized Service**: `AuditService` with log_create/update/delete/archive methods

### 📊 **Analytics Dashboard**
- **KPI Health Metrics**: Total, active, recent activity (7 days), stale KPIs
- **30-Day Contribution Trends**: Interactive Chart.js line graph
- **Top Contributors**: Leaderboard of most active contributors
- **Most Commented KPIs**: Top 10 KPIs by comment count
- **Space Statistics**: Public/private space counts
- **New Route**: `/analytics/dashboard` accessible from main navigation

### 🔍 **Search & Navigation**
- **Global Search Documented**: Comprehensive search across all entities
- **Top Navbar Integration**: Search bar accessible from anywhere
- **Permission-Aware Results**: Edit buttons only shown when authorized
- **User Search API**: Autocomplete for @mentions in comments

### 📚 **Documentation Improvements**
- **Comprehensive README**: All features documented with clear categorization
- **Security & Authentication Section**: SSO, password management, access control, audit trail
- **Administration Section**: Global Admin, Organization Admin, User Management, Super Admin, Analytics, Search, Audit Logging
- **Updated Memory**: Existing features list to prevent duplicate work

## ✨ What's New in v1.15.2 (March 2026)

### 🚨 **CRITICAL FIX**
- **Missing Migration Restored**: Added `f5c8a9b3d2e4_add_snapshot_privacy_columns.py`
- **Fixed Production Error**: "column kpi_snapshots.owner_user_id does not exist"
- **Lesson Learned**: Always create migration files when modifying database schema

### 🔒 **Private/Public Spaces**
- **Privacy Control**: Mark spaces as private or public with toggle switch
- **Workspace Filter**: Filter by All Spaces / Public / Private
- **Discreet Badges**: Only private spaces show 🔒 badge (public spaces have no badge)
- **Space Counts**: Filter pills show counts: "All Spaces (15)", "Public (12)", "Private (3)"

### 👁️ **Smart Column Filtering**
- **Auto-Hide Empty Columns**: Only shows value types with actual data in filtered view
- **Context-Aware**: Respects space type, governance body, and archived filters
- **Show All Columns Toggle**: Override to see all value types even if empty
- **Hidden Columns Indicator**: Shows which columns are hidden and why

### 💾 **Filter State Persistence**
- **Remember Your Filters**: Uses localStorage to persist selections across sessions
- **Auto-Restore**: Reloads governance bodies, space type, show_archived, show_all_columns
- **Clear All Button**: Resets all filters and clears localStorage

## ✨ What's New in v1.14.6 (March 2026)

### 📊 **Display Scale Feature**
- **Thousands & Millions Display**: Show values as 1.25M or 125k instead of 1,250,000
- **Configurable per KPI**: Choose Normal, Thousands (k), or Millions (M) scale
- **Precision Control**: Set display decimals (0-6) for scaled values
- **Smart Defaults**: Auto-shows 2+ decimals when using scale to preserve precision
- **Applied Everywhere**: Workspace, KPI detail pages, charts, rollups
- **Data Entry Unaffected**: Always enter raw values (no confusion)

### 🔄 **Organization Switcher**
- **One-Click Switching**: Change organizations without logging out
- **Modern Dropdown**: Click username → select organization
- **User-Friendly**: Shows current org, all accessible orgs, profile, logout
- **Full Dark Mode**: Styled for both light and dark themes

### 📈 **Qualitative KPI Trends**
- **Historical Charts**: Now work for Risk, Impact, Level, Sentiment value types
- **Color-Coded Points**: Visual distinction for Low/Medium/High values
- **Stepped Line Charts**: Clear transitions between discrete levels
- **Text Y-Axis**: Shows "! Low", "!! Medium", "!!! High" instead of numbers

### 🎯 **Smart Rollup Scaling**
- **Intelligent Aggregation**: Uses largest scale when rolling up mixed KPIs
- **Example**: 50,000 + 1,250,000 = 1.3M (not 1,300,000)
- **Automatic**: No configuration needed, just works

### 🎨 **UX Improvements**
- **Entry Form at Top**: No more scrolling on KPI detail page
- **Compact Layout**: Form fields in horizontal row
- **Edit Highlight**: Clicking Edit scrolls to top with yellow border flash

## ✨ What's New in v1.14 (March 2026)

### 🔒 **Comment Permissions** (v1.14.4-v1.14.5)
- **Granular Comment Access**: Control who can view and add comments per organization
- **Two Permission Levels**: "View Comments" and "Add Comments" (dependent on view)
- **Smart Comment Icons**: Icons only show for view-only users when comments exist
- **API Security**: 403 responses for unauthorized comment access
- **Fixed Comment Deletion**: Comments with @mentions now delete properly with cascade

### 🎨 **UI Improvements** (v1.14.2-v1.14.3)
- **Redesigned Spaces Admin**: Modern card-based layout with icons and better dark mode
- **Enhanced Dark Mode**: Improved contrast and readability throughout the app

### 🐛 **Bug Fixes** (v1.14.1)
- **Level Toggle Fixes**: Pills now properly toggle colors (blue/gray) and rows hide/show correctly
- **Dark Mode Improvements**: Better contrast and restored indentation hierarchy for readability
- **CSRF Error Fix**: Governance body creation now works without 500 errors

### 🎨 **Modern Workspace UI** (v1.14.0)
- **True Dark Mode**: Deep background with high contrast for reduced eye strain
- **Modern Toolbar**: Compact design with gradient background and pill-shaped interactive filters
- **Level Visibility Controls**: Toggle display of any hierarchy level (Spaces, Challenges, Initiatives, Systems, KPIs)
- **Visual Hierarchy**: Icons (🏢🎯💡⚙️📊) and color-coded borders for each level
- **Enhanced UX**: Sticky headers, smooth animations, rollup indicators (Σ symbol)
- **Smart Filters**: Governance bodies and archive filters with instant feedback
- **Quick Stats**: Real-time display of active filters and entity counts

## ✨ What's New in v1.13 (March 2026)

### 🏛️ **Governance Bodies** (v1.13.0)
- **Committee/Board Management**: Create and manage governance bodies that oversee KPIs
- **Visual Identity**: Each body has name, abbreviation, color, and description
- **Many-to-Many Links**: KPIs can belong to multiple governance bodies
- **Workspace Filtering**: Filter KPIs by governance body with color-coded pill badges
- **Default Body**: Every organization gets a "General" governance body (renamable, not deletable)
- **Permissions**: New `can_manage_governance_bodies` permission control
- **Drag-to-Reorder**: Customize display order of governance bodies
- **Full CRUD**: Create, edit, delete (except default) with complete audit trail

### 🗄️ **KPI Archiving** (v1.13.0)
- **Archive Inactive KPIs**: Preserve historical data without cluttering workspace
- **Audit Trail**: Tracks who archived and when
- **Read-Only Mode**: Archived KPIs cannot accept new contributions
- **Toggle Visibility**: "Show Archived KPIs" filter to view when needed
- **Visual Distinction**: Grayed out with archive badge
- **Easy Restore**: Unarchive anytime to make KPI active again
- **Data Preservation**: All contributions, snapshots, and comments retained

## ✨ What's New in v1.12 (March 2026)

### 🔐 **Per-Organization User Permissions** (v1.12.0)
- **Granular Access Control**: Control what users can create/edit/delete on a per-organization basis
- **6 Permission Types**: Spaces, Value Types, Challenges, Initiatives, Systems, KPIs
- **Organization-Specific**: Same user can have different permissions in different organizations
- **UI Integration**: Buttons automatically hidden when user lacks permission
- **URL Protection**: Direct URL access blocked with friendly error message
- **Global Admin Bypass**: Global administrators always have full access
- **Easy Management**: Checkbox interface during user creation/editing
- **Backward Compatible**: All existing users get full permissions by default

### 👤 **User Profile Management** (v1.11.9-v1.11.10)
- **Profile Page**: View and edit display name and email
- **Password Management**: Improved password change flow with manual "Force Password Change" control
- **Bug Fixes**: Fixed password auto-population issue that caused unintended resets
- **Better UX**: Organization assignment now uses checkboxes instead of multi-select dropdown

## ✨ What's New in v1.11 (March 2026)

### 🔄 **Smart Value Entry** (v1.10.0+)
- **Intelligent Mode Selection**: When entering a value on a cell with existing consensus, choose your intent:
  - **"NEW data (time evolved)"**: Auto-creates snapshot of current value, then replaces all contributions with new value
  - **"Contributing to CURRENT period"**: Adds contribution normally without creating snapshot
- **Automatic Snapshot Creation**: Historical values preserved when time moves forward
- **Clean Value Evolution**: Single contributor can update values without creating "low consensus"
- **No Data Loss**: Every value change optionally preserved in snapshot history

### 🎯 **Target Tracking** (v1.11.0+)
- **Set Targets**: Optional target value and date for any KPI
- **Visual Progress**: Progress indicator (🎯 X%) displayed in workspace grid
- **Chart Integration**: Target shown as horizontal dashed red line on trend charts
- **Flexible Tracking**: Different targets for different KPIs, even with same value type
- **Baseline Support**: Reference snapshot as starting point for progress measurement

### 🗑️ **Delete Functionality** (v1.10.1+)
- **Complete CRUD**: Delete operations for KPIs, Systems, Initiatives, and Challenges
- **Inline Deletion**: Delete buttons directly in list views
- **Confirmation Dialogs**: Prevents accidental deletions
- **Cascade Handling**: Related entities handled appropriately

### 📊 **Chart Improvements** (v1.11.6-v1.11.7)
- **Current Value Included**: Charts now show historical snapshots + current value
- **Same-Day Snapshots**: Multiple snapshots on same day display as separate points
- **Full Timestamps**: Uses HH:MM:SS for precise time series display
- **Better History**: Up to 50 data points displayed on charts

## ✨ What's New in v2.1 (March 2026)

### 📊 **Dashboard & Overview**
- **Interactive Dashboard**: Statistics cards, quick actions, recent activity
- **Recent Snapshots Widget**: Last 5 snapshots with View/Compare buttons
- **Recent Comments Widget**: Latest discussions across all KPIs
- **Quick Actions**: One-click access to create snapshots, export data, view mentions

### 📈 **Time-Series Tracking**
- **Snapshots**: Capture KPI values at specific points in time
- **Historical View**: View workspace state as of any snapshot date
- **Trend Indicators**: Automatic ↗️↘️→ indicators on KPI cells
- **Snapshot Comparison**: Side-by-side comparison of any two snapshots
- **Labels**: Organize snapshots with custom labels ("Q1 2026", "Sprint 5", "Baseline")

### 📉 **Charts & Visualization**
- **Trend Charts**: Interactive line charts showing KPI history over time (Chart.js)
- **Tooltips**: Hover for exact values and dates
- **Auto-refresh**: Update charts with latest snapshot data
- **Responsive Design**: Charts adapt to screen size

### 💬 **Comments & Collaboration**
- **Cell-Level Comments**: Discuss KPI values with your team
- **@Mention System**: Notify users with @username autocomplete
- **Threaded Replies**: Full conversation threading with indentation
- **Resolve Discussions**: Mark conversations as complete
- **Unread Mentions**: Bell notification (🔔) with unread count
- **Real-time Updates**: See latest comments on dashboard

### 🎨 **Enhanced Navigation**
- **Three-Tier Nav**: Dashboard → Workspace → Administration
- **Bootstrap Icons**: Visual cues for all navigation items
- **Logo Redirect**: Click logo to return to Dashboard
- **Contextual Buttons**: Dashboard button on every page

## ✨ What's in v2.0

### 🎨 **Flexible Color System**
- Colors configured per KPI, not per value type
- Same value type (e.g., "Cost") can have different meanings in different KPIs
- Colors propagate through all rollup levels automatically

### 🗄️ **PostgreSQL Database**
- Data persists across deployments
- Production-ready for real use
- Support for concurrent users
- Automatic migrations

### 📊 **Enhanced Aggregation**
- **6 Aggregation Formulas**: sum, min, max, avg, median (outlier-resistant), count (quantities)
- **Median**: Better than average when data has outliers
- **Count**: Track "how many" metrics (e.g., number of systems integrated)

### 🎭 **New Value Types**
- **Level (●●●)**: Generic 3-level for readiness, maturity, quality, preparedness
- **Sentiment (☹️😐😊)**: Emotional states for morale, satisfaction, stakeholder feelings
- **3-Level Design**: Easier consensus than 5-level scales

### 📤 **Export & Backup**
- **Excel Export**: Hierarchical with row grouping and color coding (outline levels 1-5)
- **YAML Export/Import**: Complete structure backup and restore
- **Organization Cloning**: Create test/training environments from production

### 🎯 **Enhanced UX**
- **Drag-and-Drop Reordering**: Reorder value types to control workspace column order
- **Smart Deletion**: Impact preview before deleting (shows orphaned vs. preserved entities)
- **Visual Hierarchy**: Improved tree navigation with expand/collapse

### 🛡️ **Data Loss Prevention**
- Multi-layer safety checks to prevent accidental database resets
- Startup validation of DATABASE_URL in production
- Database creation guards (no SQLite in production)
- Automatic migration enforcement

### 🚀 **Production Deployment**
- Deployed on Render with persistent PostgreSQL
- Zero downtime deployments
- Automatic database migrations

## 🎯 Features

### Core Capabilities
- **📊 Hierarchical Data Model**: Spaces → Challenges → Initiatives → Systems → KPIs
- **👥 Consensus-Based Input**: Multiple contributors, automatic consensus calculation
- **📈 Automatic Roll-ups**: Values aggregate up the hierarchy with 6 formulas (sum, avg, min, max, median, count)
- **🎨 Flexible Color Configuration**: Sign-based colors (positive/negative/zero) per KPI
- **🔢 6 Value Types**: Numeric, Risk, Positive/Negative Impact, Level, Sentiment
- **🏢 Multi-Organization**: Complete data isolation between organizations
- **👤 User Management**: Global admins, organization members, granular permissions
- **📤 Export Options**: Excel (hierarchical), YAML (structure backup), Organization cloning
- **🎯 Smart Deletion**: Impact preview showing what will be deleted vs. preserved
- **🔒 SSO Integration**: SAML 2.0 authentication with Okta, Azure AD, Google Workspace
- **📊 Analytics Dashboard**: KPI health metrics, contribution trends, activity tracking
- **🔍 Global Search**: Search across all entities (Spaces, Challenges, Initiatives, Systems, KPIs, Value Types, Comments)

### Dashboard & Overview
- **📊 Statistics Dashboard**: Overview of Spaces, Challenges, Initiatives, Systems, KPIs, Value Types
- **🚀 Quick Actions**: Create snapshots, export data, view mentions - all one click away
- **📸 Recent Snapshots**: Last 5 snapshots with View/Compare functionality
- **💬 Recent Comments**: Latest 10 discussions across organization
- **🔔 Unread Mentions**: Alert for new @mentions with count badge

### Workspace Features
- **🌲 Interactive Tree/Grid View**: Expandable/collapsible hierarchy
- **✅ Consensus Status**: Visual indicators (✓ complete, ⚠ partial)
- **🎨 Color-Coded Values**: Configurable per KPI for better interpretation
- **📊 Rollup Indicators**: See aggregated values at every level with Σ symbol
- **🔍 Quick Navigation**: Expand All / Collapse All buttons
- **💬 Comment Icons**: Click 💬 on any KPI cell to open discussions
- **↗️ Trend Indicators**: Automatic trend arrows when snapshots exist
- **🎚️ Level Visibility Controls**: Toggle display of hierarchy levels (Spaces, Challenges, Initiatives, Systems, KPIs)
- **🔍 Smart Filters**:
  - Governance body filtering (multi-select with color-coded pills)
  - Space type filtering (All/Public/Private with counts)
  - Show archived KPIs toggle
  - Show all columns toggle (override smart column hiding)
  - Filter state persistence via localStorage
  - Clear All button
- **📊 Smart Column Filtering**: Auto-hide value type columns with no data (context-aware)
- **📱 Responsive Design**: Works on desktop, tablet, and mobile
- **🌙 True Dark Mode**: Deep background with high contrast for reduced eye strain
- **📤 Excel Export**: Hierarchical export with outline levels and color coding

### Time-Series & Analytics
- **📸 Snapshots**: Capture current state with custom labels
- **📅 Historical View**: View workspace as of any snapshot date
- **📈 Trend Analysis**: Automatic calculation of value changes over time
- **📊 Comparison View**: Side-by-side snapshot comparison with % change
- **📉 Trend Charts**: Interactive line charts (Chart.js) showing KPI history with current value
- **🏷️ Labels**: Organize snapshots ("Q1 2026", "Baseline", "Sprint 5")
- **🔄 Smart Value Entry**: Choose between "new data" (creates snapshot) or "contributing" mode
- **🎯 Target Tracking**: Set target values with progress indicators and chart visualization

### Collaboration & Communication
- **💬 Cell Comments**: Discussion threads on any KPI cell
- **@Mentions**: Notify users with autocomplete dropdown
- **🧵 Threading**: Full reply nesting with indentation
- **✅ Resolve**: Mark discussions as complete
- **🔔 Notifications**: Bell icon shows unread mention count
- **👥 User Search**: Type @ to see all organization members
- **⌨️ Keyboard Nav**: Arrow keys + Enter in mention dropdown
- **🔒 Comment Permissions**: Granular view/add permissions per organization

### Security & Authentication
- **🔐 SSO/SAML Integration**: Enterprise single sign-on
  - Okta, Azure AD, Google Workspace support
  - SAML 2.0 protocol
  - Auto-provision users on first login
  - Pending user approval workflow
  - Configurable via Super Admin panel
  - Organization-based user mapping
- **🔒 Password Management**: Secure credential handling
  - Werkzeug password hashing
  - Force password change on first login
  - Self-service password change
  - Profile management (display name, email)
- **🛡️ Access Control**: Multi-level permissions
  - Super Admin (system-wide configuration)
  - Global Admin (cross-organization management)
  - Organization Member (per-org permissions)
  - Granular permissions: Spaces, Value Types, Challenges, Initiatives, Systems, KPIs
  - Comment permissions (view/add)
  - Permission-aware UI (buttons/links only shown when authorized)
- **🔍 Audit Trail**: Complete activity logging
  - All create/edit/delete operations
  - User management events
  - Tracks: who, what, when, old/new values
  - Super Admin access only

### Value Types (7 Kinds)
- **Numeric**: Cost, CO2 emissions, licenses, people, time, etc.
  - Integer or decimal format
  - Configurable decimal places (e.g., €1,234.56)
  - Unit labels (€, tCO2e, licenses, days, etc.)
  - Sign-based colors per KPI (positive/negative/zero)
  - Display scale options: Normal, Thousands (k), Millions (M)
- **List**: Custom choice-based KPIs (Yes/No, status, categories)
  - Define options with labels and colors
  - Mode aggregation (most frequent choice) with tie-breaking
  - Colored badges in workspace at all hierarchy levels
- **Risk**: 3 levels (!, !!, !!!) - Low, Medium, High risk
- **Positive Impact**: 3 levels (★, ★★, ★★★) - Impact magnitude
- **Negative Impact**: 3 levels (▼, ▼▼, ▼▼▼) - Negative consequences
- **Level**: 3 levels (●, ●●, ●●●) - Generic scale for readiness, maturity, quality
- **Sentiment**: 3 levels (☹️, 😐, 😊) - Emotional states, satisfaction, morale

### Administration & Management
- **🔐 Global Admin Panel**: Organization management, user administration, health dashboard
  - Create/edit/archive/restore organizations
  - User creation with organization assignments and permissions
  - Organization cloning for test/training environments
  - Backup & restore system (YAML-based)
  - Clear comments utility (bulk cleanup)
  - Health dashboard with system statistics
- **🏢 Organization Admin Panel**: Entity management within an organization
  - Spaces (create, edit, delete, privacy controls)
  - Challenges (create, edit, delete, link to initiatives)
  - Initiatives (create, edit, delete, reusable across challenges)
  - Systems (create, edit, delete, reusable across initiatives)
  - KPIs (create, edit, delete, archive/unarchive)
  - Value Types (create, edit, delete, reorder via drag-and-drop)
  - Governance Bodies (create, edit, delete, reorder, color-coded)
  - Rollup configuration at each link level
  - YAML import/export for structure management
- **👤 User Management**:
  - User profiles (display name, email, password)
  - Per-organization permissions (6 types: Spaces, Value Types, Challenges, Initiatives, Systems, KPIs)
  - Comment permissions (view/add comments)
  - Organization switcher (multi-org access from dropdown)
  - Force password change flag
  - Pending user approval workflow (SSO-based)
- **🔧 Super Admin Panel**: System-wide configuration
  - SSO/SAML configuration (Okta, Azure AD, Google Workspace)
  - Security settings
  - Maintenance mode toggle
  - **Audit log viewer** with advanced filtering:
    - Search by entity name
    - Filter by action (CREATE, UPDATE, DELETE, ARCHIVE, RESTORE, LOGIN)
    - Filter by entity type (User, Space, Challenge, Initiative, System, KPI, ValueType, etc.)
    - Filter by user who performed action
    - Adjustable result limits (50, 100, 250, 500)
    - Color-coded display (green=create, blue=update, red=delete, yellow=archive)
    - JSON viewer for old/new value comparison
  - User overview with pending approvals
  - Health monitoring
- **📊 Analytics Dashboard**: Organization-level insights
  - KPI statistics (total, active, recent activity, stale)
  - 30-day contribution trends (interactive chart)
  - Top contributors leaderboard
  - Most commented KPIs
  - Space statistics (public/private counts)
- **🔍 Enhanced Search**: Advanced global search with fuzzy matching and action item tracking
  - **Search bar in top navigation** with Ctrl+K keyboard shortcut
  - **Fuzzy matching**: Typo-tolerant search (e.g., "inventroy" finds "Inventory")
  - **Advanced filters**: Filter panel with entity types, date range, and status
    - **Entity type filters**: Restrict search to specific types (KPIs, Systems, Initiatives, Challenges, Spaces)
    - **Filter persistence**: Filters pass from navbar to search results page via URL parameters
    - **Filter restoration**: Filter panel state restored from URL on page reload
    - **Visual indicator**: Yellow funnel icon shows when filters are active
  - **Search modifiers**: Filter by status and quality (work with entity type filters)
    - `@requires_action` - All items needing attention (matches Action Items page, 28 items total)
    - `@incomplete` - Initiatives/Spaces with incomplete forms/SWOT
    - `@no_consensus` - Initiatives without consensus on impact
    - `@missing_kpis` - Systems without KPIs
    - `@missing_governance` - KPIs without governance bodies (18 KPIs)
    - `@archived` - Archived KPIs
    - **Modifier + Filter examples**:
      - `@requires_action` + "KPIs only" = 18 KPIs without governance
      - `@incomplete` + "Initiatives only" = 6 incomplete initiatives
  - **Saved searches**: Save frequently used queries, set default search
  - **Live search dropdown**: Real-time results as you type (navbar, up to 5 per type)
  - **Full search page**: Comprehensive results with manual search button
  - **Searches across**: Spaces, Challenges, Initiatives, Systems, KPIs, Value Types, Comments
  - **Permission-aware results**: Edit buttons only if authorized
  - **Color-coded results** by entity type
  - **User search API** for @mentions in comments
- **📋 Audit Logging**: Comprehensive audit trail
  - **Coverage**: User management, Spaces, Challenges, Initiatives, Systems, KPIs, Value Types, Governance Bodies
  - **Tracks**: who, what, when, old values, new values, IP address, user agent
  - **Advanced Filtering**: Search, action type, entity type, user, result limits
  - **Visual**: Color-coded by action type (CREATE/UPDATE/DELETE/ARCHIVE/RESTORE)
  - **Detail View**: Expandable JSON viewer for change comparison
  - **Access**: Super Admins only

## 🚀 Quick Start

> **⚡ For daily development startup:** See **[QUICK_START.md](./QUICK_START.md)** for one-liner commands to start PostgreSQL + Flask instantly.

### Prerequisites
- Python 3.11+
- PostgreSQL 16+ (local development)
- Git

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/mounirdous/CISK-Navigator.git
cd CISK-Navigator

# Install PostgreSQL (macOS with Homebrew)
brew install postgresql@18
brew services start postgresql@18

# Create database
createdb cisknavigator

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env to set:
#   DATABASE_URL=postgresql://localhost/cisknavigator
#   MAPBOX_ACCESS_TOKEN=pk.YOUR_TOKEN_HERE (see Mapbox Configuration below)

# Run database migrations
flask db upgrade

# Start development server
flask run --port 5003

# Open browser
open http://localhost:5003
```

## 🗺️ Mapbox Configuration (Required for Maps)

The map dashboard requires a free Mapbox account. **Without this token, the map will appear empty.**

### 1. Get Your FREE Mapbox Token (2 minutes)

1. Go to **https://account.mapbox.com/**
2. **Sign up** (no credit card required)
3. Click **"Create a token"** or use the default public token
4. **Copy the token** (starts with `pk.`)
5. **Free tier includes 50,000 map loads/month** - plenty for most use cases!

### 2. Configure the Token

**Local Development:**

Add to your `.env` file:
```bash
MAPBOX_ACCESS_TOKEN=pk.YOUR_TOKEN_HERE
```

Or set in terminal:
```bash
export MAPBOX_ACCESS_TOKEN="pk.YOUR_TOKEN_HERE"
```

**Production (Render):**

1. Go to **Render Dashboard**: https://dashboard.render.com/
2. Select your **CISK-Navigator web service**
3. Click **"Environment"** in left sidebar
4. Click **"Add Environment Variable"**
5. Add:
   - **Key**: `MAPBOX_ACCESS_TOKEN`
   - **Value**: `pk.YOUR_TOKEN_HERE`
6. Click **"Save Changes"** (Render will auto-redeploy)

### 3. Restart and Test

**Local:**
```bash
# Stop Flask (Ctrl+C)
source venv/bin/activate
flask run --port 5003
```

**Production:**
- Render automatically restarts after saving environment variable

### 4. Verify It's Working

Go to: http://localhost:5003/map

**You should see:**
- ✅ **Countries with KPIs = Bright green fills** (entire country polygons)
- ✅ **Countries without KPIs = Light gray**
- ✅ **KPI markers** with values (blue=region, green=country, purple=site)
- ✅ Professional map with zoom controls

**If map is still empty:**
- Check browser console (F12) for error messages
- Verify token starts with `pk.`
- Ensure Flask was restarted after adding token

### Default Credentials

```
Username: cisk
Password: Zurich20
```

**⚠️ You will be prompted to change the password on first login.**

## 📖 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture and data model
- **[app/SPECIFICATIONS.md](app/SPECIFICATIONS.md)** - Functional specifications
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment guide for Render

## 🏗️ Architecture Overview

### Technology Stack
- **Backend**: Python 3.11, Flask 3.0, SQLAlchemy 2.0
- **Database**: PostgreSQL 16+ (psycopg3 driver)
- **Migrations**: Flask-Migrate (Alembic)
- **Authentication**: Flask-Login, Werkzeug password hashing
- **Forms**: Flask-WTF with CSRF protection
- **Frontend**: Bootstrap 5, Bootstrap Icons, SortableJS 1.15 (drag-and-drop), Chart.js 4.4 (charts), Vanilla JavaScript
- **Export**: openpyxl (Excel), PyYAML (structure files)

### Data Model

```
Organization
├── Spaces (flexible grouping: seasons, sites, customers)
│   └── Challenges
│       └── Challenge-Initiative Links
│           └── Initiatives (reusable)
│               └── Initiative-System Links
│                   ├── Systems (reusable)
│                   └── KPIs (context-specific)
│                       └── KPI-ValueType Configs
│                           └── Contributions (from users)
└── Value Types (organization-wide definitions)
```

**Key Principles:**
- **Reusability**: Initiatives and Systems are reusable across multiple parents
- **Context-Specific KPIs**: KPIs belong to Initiative-System pairs
- **Consensus-Driven**: Multiple contributors, automatic consensus calculation
- **Hierarchical Roll-ups**: Values aggregate upward with configurable formulas

## 💡 Use Cases

- **Enterprise Architecture**: Map systems, initiatives, and business challenges
- **Digital Transformation**: Track transformation KPIs across the organization
- **Portfolio Management**: Manage initiative portfolios with multiple value dimensions
- **Strategic Planning**: Link strategic initiatives to business challenges
- **Technology Governance**: Track technical systems and their business impact
- **Sustainability Tracking**: Aggregate CO2, cost, and impact metrics

## 🔄 Version History

### v1.11.7 (March 8, 2026)
- 🐛 **Fixed**: Current value now included in trend charts
- 🐛 **Fixed**: Same-day snapshots display as separate points using timestamps
- 📊 **Improved**: Chart displays complete time series progression

### v1.11.6 (March 8, 2026)
- 🐛 **Fixed**: Chart API mismatch (snapshots vs history key)
- 🐛 **Fixed**: Charts now render properly when snapshots exist
- 📊 **Added**: Debug flash messages for snapshot creation

### v1.11.5 (March 8, 2026)
- ✨ **Restored**: Baseline snapshot feature (without FK constraint)
- 🔧 **Changed**: Baseline implemented as property for flexibility

### v1.11.0-1.11.4 (March 8, 2026)
- ✨ **Added**: Target tracking feature with progress indicators
- 🐛 **Fixed**: Multiple circular foreign key relationship issues
- 🗄️ **Migration**: Added target_value, target_date fields

### v1.10.2 (March 8, 2026)
- 🐛 **Fixed**: Smart Value Entry snapshot creation bugs
- 🐛 **Fixed**: Form auto-submission after modal
- 🐛 **Fixed**: Snapshot deduplication on same day
- 🐛 **Fixed**: CSRF token errors in templates

### v1.10.1 (March 7, 2026)
- ✨ **Added**: Editable list views for challenges, initiatives, and systems
- 🎨 **Improved**: Navigation and management interface

### v1.10.0 (March 8, 2026)
- ✨ **Added**: Smart Value Entry feature with mode selection modal
- ✨ **Added**: Automatic snapshot creation for time evolution
- 📊 **Enhanced**: KPI cell detail page with entry mode choice

### v1.9.5 (February 2026)
- ✨ **Added**: Decimal places editing
- 🐛 **Fixed**: Value formatting issues

### v2.1.0 (March 2026) - **Major Feature Release**

**Dashboard & Overview:**
- ✨ Interactive dashboard with statistics cards and widgets
- ✨ Recent snapshots widget with View/Compare buttons
- ✨ Recent comments widget showing latest discussions
- ✨ Quick actions for common tasks
- ✨ Getting started guide for new users

**Time-Series Tracking:**
- ✨ Snapshot system for capturing KPI values over time
- ✨ Historical view to see workspace state as of any date
- ✨ Automatic trend indicators (↗️↘️→) on KPI cells
- ✨ Snapshot comparison with side-by-side analysis
- ✨ Custom labels for organizing snapshots

**Charts & Visualization:**
- ✨ Interactive line charts using Chart.js 4.4
- ✨ Trend visualization on KPI detail pages
- ✨ Tooltips showing exact values and dates
- ✨ Responsive design adapting to screen size
- ✨ Auto-refresh capability

**Collaboration Features:**
- ✨ Cell-level comments on any KPI
- ✨ @Mention system with autocomplete (type @ for dropdown)
- ✨ Threaded replies with full nesting support
- ✨ Resolve/unresolve discussions
- ✨ Unread mentions tracking with bell notification (🔔)
- ✨ Keyboard navigation in mention dropdown (arrows + Enter)
- ✨ Real-time mention rendering with highlighted names

**Enhanced Navigation:**
- ✨ Dashboard as new home page (replaces workspace)
- ✨ Three-tier navigation: Dashboard → Workspace → Administration
- ✨ Bootstrap Icons for visual clarity
- ✨ Logo click redirects to Dashboard
- ✨ Contextual buttons on all pages

**Database Schema:**
- 🗄️ New tables: kpi_snapshots, rollup_snapshots, cell_comments, mention_notifications
- 🗄️ Proper indexes and foreign key relationships
- 🗄️ Migration ID: 498afb934c2e

**API Endpoints (15 new routes):**
- GET /workspace/dashboard - Dashboard page
- GET /workspace/snapshots/compare - Snapshot comparison
- POST /workspace/snapshots/create - Create snapshot
- GET /workspace/snapshots/list - List snapshots
- GET /workspace/snapshots/view/<date> - Historical view
- GET /workspace/api/kpi/<id>/trend - Trend data
- GET /workspace/api/kpi/<id>/history - Value history
- GET/POST /workspace/api/cell/<id>/comments - Comments CRUD
- PUT/DELETE /workspace/api/comments/<id> - Edit/delete comments
- POST /workspace/api/comments/<id>/resolve - Resolve discussion
- POST /workspace/api/comments/<id>/unresolve - Unresolve discussion
- GET /workspace/api/mentions/unread - Get unread mentions
- POST /workspace/api/mentions/<id>/read - Mark as read
- POST /workspace/api/mentions/mark-all-read - Clear all
- GET /workspace/api/org/users/search - User autocomplete

### v2.0.0 (March 2026) - **Major Release**

**Database & Infrastructure:**
- ✨ Migrated from SQLite to PostgreSQL for data persistence
- ✨ Deployed on Render with persistent database
- ✨ Automatic migrations on deployment
- ✨ psycopg3 driver for Python 3.13+ compatibility
- 🛡️ Multi-layer data loss prevention with safety checks

**Color System Refactor:**
- ✨ Color configuration moved from ValueType to KPI level
- ✨ Colors propagate through all rollup levels
- 🐛 Fixed rollup color inheritance

**New Aggregation Features:**
- ✨ Added median formula (outlier-resistant aggregation)
- ✨ Added count formula (quantity tracking)
- ✨ Total of 6 aggregation formulas available

**New Value Types:**
- ✨ Added Level type (●●●) - generic 3-level scale
- ✨ Added Sentiment type (☹️😐😊) - emotional states
- ✨ All qualitative types use 3-level scale for easier consensus

**Export & Backup:**
- ✨ Excel export with hierarchical row grouping (outline levels 1-5)
- ✨ YAML export for complete structure backup
- ✨ YAML import with ID reuse logic for initiatives/systems
- ✨ Organization cloning for testing/training environments

**UX Improvements:**
- ✨ Drag-and-drop value type reordering (controls column order)
- ✨ Smart deletion with impact preview
- ✨ Improved visual hierarchy in workspace
- 🐛 Fixed duplicate flash/redirect in edit routes
- 🐛 Fixed redirect loop between login and workspace

### v1.10.1 (March 2026)
- ✨ Add editable list views for challenges, initiatives, and systems
- 🎨 Improved navigation and management interface

### v1.10.0 (February 2026)
- ✨ Add color picker feature for numeric value types
- 🎨 Sign-based color configuration (positive/negative/zero)

### v1.9.5 (February 2026)
- ✨ Add decimal places editing
- 🐛 Fix value formatting issues

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - Free for personal and commercial use.

See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built for strategic business planning, digital transformation tracking, and collaborative data collection across complex organizational hierarchies.

---

**Made with ❤️ for better decision-making**
