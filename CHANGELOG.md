# Changelog

All notable changes to CISK Navigator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.2] - 2026-03-16

### Added - Enhanced Search API Endpoint (Phase 2)
**Feature**: REST API endpoint exposing the SearchService with enhanced results

**Files Modified**:
- `app/routes/workspace.py` - Added `/api/search/advanced` endpoint (POST)

**New API Endpoint**: `/api/search/advanced`
- **Method**: POST
- **Authentication**: Requires login + organization context
- **Request Body** (JSON):
  ```json
  {
    "query": "search text or operators",
    "filters": {
      "entity_types": ["kpis", "systems", "initiatives", "challenges", "spaces"],
      "date_range": "last_week",
      "status": ["at_risk", "incomplete"]
    }
  }
  ```

- **Response Body** (JSON):
  ```json
  {
    "kpis": [{id, name, description, system_name, initiative_name, match_score, url, edit_url, icon, logo, ...}],
    "systems": [{id, name, description, match_score, url, edit_url, icon, logo, ...}],
    "initiatives": [{id, name, description, impact_on_challenge, match_score, url, edit_url, icon, logo, ...}],
    "challenges": [{id, name, description, space_name, match_score, url, edit_url, icon, logo, ...}],
    "spaces": [{id, name, description, match_score, url, edit_url, icon, logo, ...}],
    "query_info": {
      "original_query": "...",
      "parsed_query": "...",
      "modifiers": [...],
      "operators": {...}
    },
    "total_results": 42
  }
  ```

**Key Features**:
1. **Enhanced Results** - Adds URLs, edit links, icons, and logos to search results
2. **Entity Defaults Integration** - Fetches organization-specific branding
3. **Navigation URLs** - Each result includes:
   - `url` - Link to view entity in workspace (with KPI highlight if applicable)
   - `edit_url` - Link to edit entity in admin panel
   - `icon` - Entity type icon (text or emoji)
   - `logo` - Base64-encoded logo image (if configured)

4. **Total Results Count** - Aggregated count across all entity types
5. **Organization Scoping** - Results automatically filtered to current organization

**Integration Points**:
- Uses `SearchService.search_all()` for core search logic
- Uses `EntityTypeDefault` model for branding
- Uses `url_for()` to generate consistent URLs
- Uses workspace routes: `workspace.index`, `organization_admin.edit_*`

**Error Handling**:
- Returns 400 if query parameter missing
- Returns empty results for queries < 2 characters
- Handles missing entity defaults gracefully

**Architecture Notes**:
- Endpoint separates concerns: SearchService does search, endpoint handles URLs/branding
- RESTful design: POST for complex query with filters
- JSON-only API (no HTML rendering)
- Consistent with existing `/api/search/live` endpoint pattern

**Testing**:
```bash
# Example cURL test
curl -X POST http://localhost:5003/api/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"query": "inventory @risk", "filters": {"entity_types": ["kpis", "systems"]}}'
```

**Next Phase**: Frontend UI to consume this API (v2.5.3)

## [2.5.1] - 2026-03-16

### Added - Enhanced Search Backend (Phase 1)
**Feature**: Advanced search service with fuzzy matching, query parsing, and multi-entity search

**Files Added**:
- `app/services/search_service.py` - Core search service with comprehensive functionality

**Dependencies Added**:
- `python-Levenshtein==0.27.3` - Fuzzy string matching library (added to requirements.txt)
- Provides typo-tolerant search using Levenshtein distance algorithm

**Key Features Implemented**:

1. **SearchService Class** - Main search engine
   - Method: `search_all(query, filters, organization_id)` - Search across all entities
   - Method: `parse_query(query)` - Extract operators and modifiers from query
   - Method: `fuzzy_match(text, query, threshold)` - Levenshtein-based matching
   - Method: `search_kpis()` - KPI-specific search with context
   - Method: `search_systems()` - System search
   - Method: `search_initiatives()` - Initiative search with status filters
   - Method: `search_challenges()` - Challenge search with space context
   - Method: `search_spaces()` - Space search

2. **Query Parser** - Smart query interpretation
   - Modifiers: `@risk`, `@incomplete`, `@no_consensus`, `@archived`
   - Date operators: `updated:last_week`, `updated:last_month`, `updated:today`
   - Numeric operators: `value>100`, `value<50`, `value=25`
   - Ranges: `value:10-20`
   - Cleans query by removing operators for text search

3. **Fuzzy Matching** - Typo-tolerant search
   - Threshold: 0.6 (60% similarity required)
   - Algorithm: Levenshtein ratio from python-Levenshtein
   - Exact substring matches always pass
   - Case-insensitive matching

4. **Multi-Entity Search** - Search across entity types
   - KPIs: Searches name, description, system name, initiative name
   - Systems: Searches name, description
   - Initiatives: Searches name, description, respects status
   - Challenges: Searches name, description, includes space context
   - Spaces: Searches name, description
   - Match scoring: Higher score = better match (name matches worth more)

5. **Result Structure** - Categorized results
   ```json
   {
     "kpis": [{id, name, description, system_name, initiative_name, match_score, ...}],
     "systems": [{id, name, description, match_score, ...}],
     "initiatives": [{id, name, description, impact_on_challenge, match_score, ...}],
     "challenges": [{id, name, description, space_name, match_score, ...}],
     "spaces": [{id, name, description, match_score, ...}],
     "query_info": {
       "original_query": "...",
       "parsed_query": "...",
       "modifiers": [...],
       "operators": {...}
     }
   }
   ```

**Database Queries**:
- Scoped to organization_id for multi-tenancy
- Respects archive status by default
- Joins through relationship chains (e.g., KPI → InitiativeSystemLink → Initiative)
- Uses SQLAlchemy ORM for type safety

**Architecture Notes**:
- Pure service class (no Flask dependencies)
- Stateless design - all state in method parameters
- Results sorted by match_score (descending)
- Empty results return consistent structure

**Future Enhancements** (planned):
- Phase 2: Database schema for saved searches (v2.5.2)
- Phase 3: Frontend UI (v2.5.3-v2.5.5)
- Phase 4: Saved searches & history (v2.5.6-v2.5.7)
- Phase 5: Performance optimization (v2.5.8)

**Impact Analysis**:
- NEW service - no breaking changes
- Dependencies: Adds python-Levenshtein (3 packages total with dependencies)
- Models used: KPI, System, Initiative, Challenge, Space (read-only)
- No database schema changes in this phase
- No frontend changes yet - backend foundation only

**Testing Notes**:
- Service can be tested independently via Flask shell
- Example: `SearchService.search_all("inventory", {}, org_id=1)`
- All searches scoped to organization for security

## [2.5.0] - 2026-03-16

### Branch Created
- **🌿 New feature branch**: `feature/enhanced-search`
- Major feature development: Enhanced Search with fuzzy matching, AI insights, and saved searches
- Version bumped from 2.4.0 → 2.5.0 for new feature track
- Incremental versions (2.5.1, 2.5.2, etc.) track development progress

### Planned Features (Multi-Phase)
1. **Phase 1 (v2.5.1)**: Backend search service with fuzzy matching
2. **Phase 2 (v2.5.2)**: Database schema for saved searches
3. **Phase 3 (v2.5.3-v2.5.5)**: Frontend UI (search bar, filters, results)
4. **Phase 4 (v2.5.6-v2.5.7)**: Saved searches & history
5. **Phase 5 (v2.5.8)**: Performance optimization & polish

## [2.4.0] - 2026-03-16

### Added
- **🏠 Home button in navbar**: Quick access to dashboard from anywhere
  - Added home icon (house-fill) before "CISK" logo in top left
  - Links to `workspace.dashboard`
  - Only visible when organization is selected
  - Clean icon-only design for minimal space usage

### Changed
- **📊 Organization name replaced with "Workspace" in navbar**
  - Previous: Organization logo + name (e.g., "MIKRON")
  - Now: Grid icon + "Workspace" text
  - Links to `workspace.index` (the main workspace grid)
  - Maintains same styling (blue pill background with hover effect)
  - More intuitive navigation: "Workspace" clearly indicates where you'll go

### Improved
- **Better navigation clarity**: Users now understand navbar links better
  - Home icon = Dashboard (overview/stats)
  - Workspace = Grid view (Spaces/Challenges/Initiatives/Systems/KPIs)
  - Organizations dropdown still available for switching orgs

## [2.3.6] - 2026-03-16

### Reverted
- **↩️ Removed thick border attempt (v2.3.5)**: Border wasn't visible, code removed
  - User feedback: No thick border visible despite changes
  - Reverted to simple `border-left: 5px solid #667eea`
  - Removed border-radius, full border, box-shadow
  - Removed dual animation (kpiBorderGlow)
  - Back to original working spotlight with left border only
  - Lesson: Table row borders don't work the same as div borders

## [2.3.5] - 2026-03-16 [REVERTED]

### Attempted (but didn't work)
- **❌ Thick border highlight around entire KPI row**: Didn't display
  - Tried `border: 4px solid` on all sides - not visible
  - Table display-mode prevents full borders from showing
  - Reverted in v2.3.6

## [2.3.4] - 2026-03-16

### Fixed
- **📜 Perfect KPI centering**: Changed to 50% (true center) for maximum visibility
  - User feedback: At 35%, KPI name "ERP Consolidation Story" barely visible at top, effect almost invisible
  - Changed to 50% from top = **centered in viewport**
  - Formula: `targetScroll = rowTop - (viewportHeight * 0.5)`
  - **Minimal scroll** - KPI stays in comfortable viewing position
  - Both KPI name AND spotlight effect fully visible

## [2.3.3] - 2026-03-16

### Fixed
- **📜 Gentler KPI scroll positioning**: Reduced scroll distance (35% from top instead of 20%)
  - User feedback: Still scrolling too much with 20% positioning
  - Changed to 35% from top for more gentle, natural scroll
  - Formula: `targetScroll = rowTop - (viewportHeight * 0.35)`
  - Fixed scroll calculation to account for current scroll position
  - Less jarring, more natural highlighting experience

## [2.3.2] - 2026-03-16

### Fixed
- **📜 KPI Spotlight scroll positioning**: KPI now fully visible, not cut off
  - Problem: `scrollIntoView({block: 'center'})` was scrolling too far, hiding part of the KPI
  - Solution: Custom scroll calculation positions KPI at 20% from top of viewport
  - Uses `getBoundingClientRect()` to calculate precise positioning
  - Formula: `targetScroll = kpiRow.offsetTop - (viewportHeight * 0.2)`
  - Ensures full KPI row is visible with comfortable spacing above
  - Still uses smooth scroll animation

## [2.3.1] - 2026-03-16

### Fixed
- **🎬 KPI Spotlight now visible**: Auto-closes filters panel when highlighting a KPI
  - Root cause: Filters panel was covering the entire view, hiding the spotlight animation
  - Solution: Sets `filtersExpanded = false` before highlighting
  - Added 250ms delay to wait for filter panel close animation to complete
  - Ensures spotlight effect is fully visible in the center of the screen
  - Timing: Filter close (150ms) → DOM update → Scroll (smooth) → Spotlight (600ms delay)

## [2.3.0] - 2026-03-16

### Added
- **🎯✨ KPI Spotlight Highlighting** - Modern, fun animation for "View Full KPI Details" from Map Dashboard
  - Clicking "View Full KPI Details" in Map Dashboard now actually finds and highlights the KPI!
  - **Multi-stage animation**:
    1. 🔍 Searches entire hierarchy to find KPI by ID
    2. 📂 Auto-expands all parent entities (Space → Challenge → Initiative → System)
    3. 📜 Smooth scrolls to center the KPI row in viewport
    4. 🎯 Target emoji bounces in from left with rotation
    5. 💫 Pulsing glow effect (4 pulses over 3 seconds)
    6. ✨ Shimmer light sweep across the row
    7. 🌈 Gradient background animation with inset glow
    8. 🎨 Animated border color (purple → magenta gradient)
    9. 🧹 Auto-cleanup: Removes URL parameter after highlight
  - **Smart handling**: Shows archived KPIs if the target is archived
  - **Visual effects**:
    - Pulsing outer glow (box-shadow rings)
    - Inner glow/shimmer effect
    - Subtle scale/bounce animation (1.02x at peak)
    - 5px purple border on left side
    - Light shimmer sweep effect
  - **Console logging**: "🎯 KPI Spotlight Applied!" for debugging

### Fixed
- **Map Dashboard "View Full KPI Details" now functional** - Previously went to workspace but did nothing
  - Added `?kpi_id=X` URL parameter handling in workspace
  - Implements full KPI discovery and highlighting flow
  - No more confusion about what the button does!

### Technical
- New CSS animations:
  - `@keyframes kpiSpotlight` (3s pulsing glow effect)
  - `@keyframes kpiBorderGlow` (color shift animation)
  - `@keyframes kpiShimmer` (light sweep effect)
  - `@keyframes kpiTargetBounce` (emoji bounce with rotation)
- New JavaScript method: `highlightKPIFromURL()`
- Added `data-kpi-id` attribute to KPI rows for DOM querying
- Uses Alpine.js `$nextTick()` for DOM update synchronization
- Auto-removes `kpi_id` URL parameter after 3 seconds

## [2.2.1] - 2026-03-16

### Added
- **🌍 2D/3D Map Toggle (EXPERIMENTAL)**: Test 3D globe view in Map Dashboard
  - New toggle button in page title: "3D View" / "2D View"
  - Switches between Mapbox projections:
    - 2D: `projection: 'mercator'` (flat map)
    - 3D: `projection: 'globe'` (interactive globe)
  - Smooth zoom adjustment when entering 3D mode
  - **Purpose**: Test if mobile optimizations work with 3D view
  - **Note**: May be reverted if issues found on mobile

### Technical
- Added `map.setProjection()` to dynamically switch projections
- State tracking with `is3DMode` boolean flag
- Button text updates dynamically based on current mode
- Console logging for debugging projection changes

## [2.2.0] - 2026-03-16

### Improved
- **📱 Mobile dashboard layout optimization**: Consistent button widths and better layout
  - Fixed inconsistent widths for "View" and "Compare" buttons in snapshot list
  - Buttons now use `flex: 1` for equal width distribution (50/50 split)
  - Snapshot items stack vertically on mobile instead of wrapping awkwardly
  - Fixed lock badge wrapping below - now stays inline with date/label
  - Metadata section uses flexbox with proper wrapping to prevent overflow
  - Hero card "Download Excel" button now full width on mobile
  - Reduced padding on hero card for better mobile fit (2.5rem → 1.5rem)

### Technical
- Added `@media (max-width: 768px)` styles for dashboard
- Changed snapshot list from `justify-content-between` to vertical stacking
- Buttons get equal width with `flex: 1` and `min-width: 0` for text truncation
- Touch-friendly button padding: `0.6rem 0.75rem`

## [2.1.9] - 2026-03-16

### Changed
- **📱 First column no longer sticky on mobile workspace**: Entity names column now scrolls horizontally
  - Removed `position: sticky` from first column on mobile
  - Removed `left: 0` and `box-shadow` styling
  - Changed to `position: relative` to allow free horizontal scrolling
  - Users can now swipe to see the entire grid from left to right
  - Desktop still has sticky first column for easy reference

## [2.1.8] - 2026-03-16

### Fixed
- **🐛 Inconsistent column widths on mobile workspace**: Fixed cells having different widths
  - Root cause: Table cells had `min-width` but no explicit `width`, causing auto-sizing
  - Each row's cells could be different widths based on content
  - Solution: Added fixed widths for consistency on mobile:
    - First column (entity names): `width: 250px`
    - Value columns: `width: 110px`
    - Header cells: `width: 110px`
  - Removed `display: inline-grid` (was causing inconsistency)
  - Kept `display: table` for proper table cell alignment

## [2.1.7] - 2026-03-16

### Fixed
- **🐛 Mobile horizontal scroll in workspace**: Fixed inability to scroll to see value columns on mobile
  - Root cause: `.ws-grid-container` had `min-width: max-content` making it expand to fit content (no overflow)
  - Container must be constrained to viewport width (`width: 100%; max-width: 100vw`) to allow scrolling
  - Grid inside has `min-width: max-content` to expand beyond container, creating scrollable overflow
  - Added `display: inline-grid` to grid to prevent collapsing to container width

### Removed
- **Workspace V2 route and templates**: Consolidated to single workspace implementation
  - Deleted `/workspace/v2` route (`app/routes/workspacev2.py`)
  - Deleted `app/templates/workspacev2/` directory
  - Removed blueprint registration from `app/__init__.py`
  - Updated beta page to show "No Beta Features Currently"
  - Main `/workspace` route now uses modern Alpine.js implementation (was V2, now the only version)

## [2.1.6] - 2026-03-16

### Fixed
- **🐛 Mobile navigation click-through issue**: Fixed clicks on menu items triggering profile button behind
  - Root cause: Mobile menu (navbar-collapse) had insufficient z-index stacking
  - Clicks on "Analytics" and other menu items would accidentally trigger profile dropdown
  - Solution: Added comprehensive z-index hierarchy for mobile menu (z-index: 1070+)
  - Added semi-transparent backdrop overlay to prevent interaction with elements behind
  - Set explicit `pointer-events: auto` on nav items to ensure clickability
  - Applied only on mobile breakpoint (@media max-width: 991.98px)

### Improved
- **Mobile menu visual polish**:
  - Added backdrop blur effect for better visual separation
  - Rounded bottom corners (border-radius: 12px)
  - Enhanced shadow for depth perception
  - Background: `rgba(33, 37, 41, 0.98)` with backdrop-filter blur

## [2.1.5] - 2026-03-16

### Improved
- **🔍 Enhanced error debugging for Map Dashboard KPI loading**
  - Added detailed HTTP response status logging
  - Show error messages in UI for troubleshooting
  - Added try-catch blocks around renderKPIList and setupSidebarInteractions
  - Better error context (message, stack, type) for debugging

- **📱 Responsive map fitBounds for mobile**
  - Reduced padding on mobile devices (40px instead of 450px left padding)
  - Desktop: `{ top: 80, bottom: 80, left: 450, right: 80 }` (sidebar offset)
  - Mobile: `{ top: 60, bottom: 60, left: 40, right: 40 }` (centered)
  - Applies to both initial load and "Show All" button

## [2.1.4] - 2026-03-16

### Fixed
- **🐛 HOTFIX: Map rendering on mobile**: Restored correct Mapbox positioning
  - Mapbox requires `position: absolute` on map element to render properly
  - Previous fix incorrectly changed to `position: relative`
  - Correct solution: Parent `.map-container` gets `position: relative` + explicit height, child `#map` stays `position: absolute`

## [2.1.3] - 2026-03-16

### Mobile Optimization - Map Dashboard 🗺️📱

Complete mobile-responsive overhaul of the Geographic KPI Distribution map view.

### Added
- **📱 Responsive Layout**: Adaptive layout based on screen size
  - **Portrait mode**: Vertical stack (sidebar on top, map below)
  - **Landscape mode**: Side-by-side (40% sidebar, 60% map)
  - **Tablet mode**: Narrower sidebar (320px)

- **🎯 Touch-Optimized Controls**: Mobile-first interaction design
  - Minimum 44px touch targets on all buttons
  - 36px minimum height for filter chips
  - Larger tap areas for KPI list items (min 80px)
  - Touch feedback on tap (scale animation)

- **📏 Compact UI Elements**: Space-efficient design
  - Smaller fonts (16px → 13px for KPI names)
  - Reduced padding throughout (20px → 15px)
  - Horizontally scrollable filter chips (no wrap)
  - Compact badges and labels

- **🗺️ Adaptive Map Display**:
  - **Portrait**: 50% viewport height
  - **Landscape**: 60% width, full height
  - Touch-friendly zoom controls (1.2x scale)
  - Map controls FAB in bottom-right

- **📋 Full-Screen Details Panel**: Better mobile UX
  - Slides in from right covering 100% width
  - Dedicated close button
  - Scrollable content

### Changed
- **Sidebar**: Full-width on mobile (360px → 100%)
- **KPI List**: Max height 50vh with scroll on mobile
- **Filter Chips**: Horizontal scroll instead of wrap
- **Page Title**: Stacks vertically on mobile
- **Button Group**: Full width with flex distribution

### Fixed
- **🐛 Map initialization on small screens**: Fixed KPI loading failure on mobile devices
  - Root cause: `.map-container` had no explicit height on mobile (relied on flex: 1 with parent height: auto)
  - Without a defined container height, Mapbox failed to initialize properly
  - Solution: Added explicit `height: 50vh` to `.map-container` on mobile
  - Added `position: relative` to `.map-container` (parent for absolute positioned `#map`)
  - Kept `#map` as `position: absolute` (required by Mapbox for proper rendering)
  - Moved CSS `order` property to `.map-container` for correct flex ordering

### Technical
- **Breakpoints**:
  - Mobile: `@media (max-width: 768px)`
  - Tablet: `@media (min-width: 769px) and (max-width: 1024px)`
  - Touch: `@media (hover: none) and (pointer: coarse)`
  - Landscape: `@media (max-width: 768px) and (orientation: landscape)`
- **Flex Order**: Sidebar (order:1), Map (order:2) for logical tab order
- **iOS Momentum**: `-webkit-overflow-scrolling: touch` on filter chips

### Performance
- CSS-only responsive design (no JavaScript)
- Hardware-accelerated transforms for animations
- Efficient media query stacking

### User Experience
- **Adaptive**: Layout changes based on orientation
- **Touch-friendly**: All targets meet accessibility standards
- **Scrollable**: Horizontal scroll for filters, vertical for list
- **Feedback**: Visual feedback on all touch interactions

## [2.1.2] - 2026-03-16

### Fixed
- **CRITICAL Mobile Scroll Fix**: Fixed CSS selector mismatch and grid width
  - Changed `.ws-grid-wrapper` to `.ws-grid-container` in all mobile CSS
  - Fixed `.ws-grid` width from `100%` to `auto` on mobile with `min-width: max-content`
  - Updated JavaScript querySelector to use correct class name
  - Grid now properly extends beyond viewport enabling horizontal scroll

**Root Cause**: The grid table had `width: 100%` forcing it to viewport width, preventing overflow. Mobile CSS was also targeting wrong selector (`.ws-grid-wrapper` instead of `.ws-grid-container`).

## [2.1.1] - 2026-03-16

### Fixed
- **Mobile Scroll Issue**: Removed sticky positioning from first column
  - Sticky entity column was blocking horizontal scroll on mobile
  - Now allows free horizontal scrolling across all columns
  - Entity names scroll with content (no freeze pane)

## [2.1.0] - 2026-03-16

### Mobile Optimization - Option 3 Implementation 📱

Complete mobile-responsive overhaul implementing hybrid approach for optimal mobile experience.

### Added
- **📱 Horizontal Scrollable Grid**: Touch-friendly workspace grid
  - iOS momentum scrolling (-webkit-overflow-scrolling: touch)
  - Smooth scroll behavior for natural feel
  - Free horizontal scrolling (no sticky columns blocking scroll)
  - Visual scroll indicator: "← Swipe to see values →"
  - Auto-hiding indicator after user scrolls

- **🎯 Touch-Optimized Controls**: Mobile-first button design
  - Minimum 44px touch targets (Apple HIG compliant)
  - Larger expand/collapse icons (1.2rem with padding)
  - Floating action buttons for snapshot controls
  - Circular FABs with shadows (56px diameter)
  - Fixed bottom-right positioning prevents overlap

- **📐 Responsive Toolbar**: Adaptive command bar
  - Auto-stacking on mobile (vertical layout)
  - Hides non-essential controls (collapse all, column toggles)
  - Larger button padding (0.5rem vs 0.25rem)
  - Flexible wrapping for narrow screens

- **🎨 Mobile-Specific Styling**: Optimized visual hierarchy
  - Reduced entity indentation (0.5rem base vs 1.5rem)
  - Hidden badges by default (less clutter)
  - Minimum 100px value cell width
  - Larger action icons (1.2rem + padding)
  - Custom scrollbar styling (8px width)

### Changed
- **Filter Section**: Full-width expansion on mobile
- **Summary Bar**: Stacks vertically on narrow screens
- **Grid Container**: Now allows horizontal overflow with min-width: max-content
- **Hover Effects**: Disabled on touch devices, replaced with tap feedback
- **Row Heights**: Minimum 48px on touch devices for better tapping

### Technical
- **Breakpoints**:
  - Mobile: `@media (max-width: 768px)`
  - Tablet: `@media (min-width: 769px) and (max-width: 1024px)`
  - Touch devices: `@media (hover: none) and (pointer: coarse)`
- **New JavaScript**: `setupMobileScrollIndicator()` method
  - Detects horizontal scroll events
  - Adds/removes 'scrolled' class dynamically
  - 2-second timeout before re-showing indicator
- **CSS Architecture**: Mobile-first with progressive enhancement
- **Scroll Architecture**: Removed sticky positioning to allow unrestricted horizontal scroll

### Fixed
- **Button Overlap**: Snapshot controls no longer conflict with filters
- **Grid Overflow**: Can now scroll to see all value columns
- **Toolbar Chaos**: Controls stack properly instead of overflowing
- **Touch Targets**: All interactive elements meet accessibility standards

### Performance
- Hardware-accelerated scrolling on iOS
- CSS-only responsive design (no JS layout shifts)
- Minimal reflows with position: sticky
- Efficient scroll event debouncing (2s timeout)

### User Experience
- **Discoverable scrolling**: Visual cue teaches horizontal swipe
- **Familiar gestures**: Native-feeling momentum scroll
- **No mode switching**: Same workspace adapts seamlessly
- **Progressive disclosure**: Hides complexity on small screens
- **Tap confidence**: Large, well-spaced interactive elements

## [2.0.0] - 2026-03-16

### Major Release - Workspace V2 Complete & Holiday Edition 🎄

This major version brings the V2 workspace to full feature parity with V1, enhanced UX, and festive seasonal theming.

### Added
- **🎯 Global Search Auto-Scroll**: Click search results to smoothly scroll to entities
  - Automatic parent expansion (spaces → challenges → initiatives → systems → KPIs)
  - Modern pulse-glow highlight animation (2.5s blue glow with subtle scale)
  - Smooth scroll behavior centers target entity on screen
  - Works from both live search dropdown and "View all results" page
  - Prevents browser's default hash jump for better UX

- **🎄 Festive Christmas Theme**: Seasonal workspace decorations
  - Custom CSS Christmas trees replace default entity icons
  - Multi-layer green tree with gold star topper ⭐
  - Three twinkling ornaments (red, gold, blue) with pulsing animation
  - Shows on all entities: spaces, challenges, initiatives, systems, KPIs
  - 🎄 Toolbar button toggles between festive trees and regular Bootstrap icons

- **🎨 Badges Toggle Control**: Unified decoration management
  - Single 🎄 button controls ALL workspace decorations
  - **Toggles visibility of**:
    - Entity icons/trees
    - Rollup formula indicators (Σ, ↑, ↓, ≈, m, #)
    - Target direction arrows (⬇️, 🎯, ⬆️)
    - Target progress indicators in value cells
    - Completeness indicators (✓, ⚠)
    - Trend indicators (↗️, ↘️, →)
    - Comment icons (💬)
    - SWOT/form completion badges
    - Governance body badges
    - Private badges
    - Entity link icons
  - **OFF mode**: Clean, minimal view with only values and colors
  - **ON mode**: Full decorative experience with all visual aids
  - **Edit mode**: Always shows regular icons for clarity

### Changed
- **Workspace V2 = Workspace V1**: V2 now replaces V1 completely
  - All V1 features fully implemented in V2
  - Improved performance with Alpine.js 3.x
  - Better filter management with database-backed presets
  - Enhanced visual consistency

- **Simplified Preset Management**: Removed complexity, improved reliability
  - Presets save to database and use URL parameters for state
  - Removed problematic active preset badge feature
  - Focus on stable, working functionality over feature completeness

### Fixed
- **Search Page BuildError**: Fixed `edit_value_type` URL parameter (`vt_id` not `value_type_id`)
- **Smooth Scroll Issues**: Prevented browser's automatic hash jump behavior
- **Filter Preset Save**: Now properly saves to database and keeps filters active
- **Governance Body Counts**: Fixed to use `kpi.governance_bodies` array
- **JSON Serialization**: Removed complex filter_presets_json passing to avoid Alpine errors

### Technical
- Added `:id` attributes to all entity rows for hash-based navigation
- Implemented `scrollToHashTarget()` and `expandParentsForTarget()` methods
- Added CSS keyframe animation `@keyframes searchHighlight` for modern pulse effect
- Added `data-badges-visible` attribute binding for CSS-based toggle control
- Trend indicators and comment icons dynamically controlled via CSS selectors
- Import fix: `from markupsafe import Markup` (Flask 2.x compatibility)

### Performance
- CSS-based visibility toggles (no JavaScript re-rendering needed)
- Optimized element rendering with Alpine.js x-show directives
- Reduced DOM manipulation for smoother UX

### User Experience
- **Holiday delight**: Festive theme brings seasonal cheer to workspace
- **Clean focus mode**: Badges OFF provides distraction-free data view
- **Smart defaults**: Badges ON by default for full visual experience
- **Consistent behavior**: All decorative elements controlled by single toggle
- **Smooth animations**: Modern transitions and effects throughout

## [1.35.0] - 2026-03-16

### Added
- **📋 Action Items - Quality Dashboard**: Comprehensive data quality monitoring
  - Lists all incomplete and problematic items requiring attention
  - **5 quality checks**: No consensus initiatives, incomplete forms, missing SWOT, systems without KPIs, KPIs without governance
  - **Smart filtering**: Only shows sections with actual items (empty sections hidden)
  - **Direct edit links**: One-click access to fix each issue with automatic return navigation
  - **Dashboard alert**: Shows total action items count for all users
  - **Navigation**: Added to Dashboards dropdown menu
  - **Progress indicators**: Visual progress bars for incomplete forms and SWOT analysis
  - **Priority color coding**: Critical (red), High (orange), Medium (yellow), Low (cyan)
  - **Return-to navigation**: After editing from action items, automatically returns to action items page
  - Template support in initiative forms, SWOT editing, system editing, and KPI editing

### Added (Documentation)
- **BETA_WORKFLOW.md**: Complete guide for developing and releasing beta features
  - Phase 1: Development with beta restrictions
  - Phase 2: Public release process
  - Best practices and common pitfalls
  - Return-to pattern implementation
  - Testing checklists
  - Real example using Action Items feature

### Changed
- **Beta program**: Action Items graduated from beta to public release
- **Dashboard alert**: Replaced "No Consensus" alert with comprehensive "Action Items" alert
- **Initiative forms**: Back button text changes based on return_to parameter
- **SWOT editing**: Back button text changes based on return_to parameter

### Technical
- Route: `/action-items` at root level in `app/__init__.py`
- Template: `app/templates/workspace/action_items.html`
- Return-to support added to: `initiative_form.html`, `edit_space_swot.html`
- Backend logic in workspace.dashboard() for action items calculation

## [1.33.32] - 2026-03-15

### Added
- **🔗 Entity Links & Resources**: Attach URLs and documents to any entity
  - Link any web resource (documents, wikis, Jira, GitHub, etc.) to Spaces, Challenges, Initiatives, Systems, or KPIs
  - **Public/Private links**: Share across organization or keep private
  - **Smart icon detection**: Automatically recognizes Google Docs, GitHub, PDFs, images, and more
  - **Workspace integration**: Link icon with hover popover shows all links next to entity names
  - **Edit page integration**: Links section on all entity edit pages (Spaces, Challenges, Initiatives, Systems, KPIs)
  - **Inline management**: Add, edit, delete links without leaving the page
  - **URL validation**: Enforces valid URLs (http://, https://, ftp://)
  - **Display ordering**: Manual reordering support for link organization
  - **Clickable popovers**: Hover persistence allows clicking links in workspace tree view

### Changed
- **Edit icons consistency**: Changed KPI edit icon from sliders (⚙️) to pencil (✏️) to match other entities
- **Edit Space navigation**: Fixed pencil button to properly navigate to edit page

### Fixed
- **Workspace AttributeError**: Fixed `system.kpis` error by correctly accessing `sys_link.kpis`
- **Entity links routes**: Switched from JSON API to form POST for better CSRF handling

### Database
- **Migration**: `fcbf234294da_add_entity_links_table_for_urls.py`
- **New table**: `entity_links` with polymorphic entity_type/entity_id design
- **Indexes**: Composite index on (entity_type, entity_id) and index on created_by for performance

## [1.33.0] - 2026-03-15

### Added
- **Impact Assessment for Initiatives**: Capture impact levels on challenges
  - New fields: `impact_on_challenge` (not_assessed, low, medium, high, no_consensus)
  - Rationale field to capture opinions and discussions
  - Integrated into initiative form with colored badges and emojis
  - Impact filter in workspace with counts per level
  - Dashboard alerts for initiatives with "No Consensus" status
  - Form completion tracking includes impact assessment (8 fields total)
- **Live Search for Saved Filters**: Dropdown pattern for filter presets
  - Click search box to display all available saved filters
  - Type to filter dropdown results in real-time
  - Shows preset name, filter count, and delete button
  - Consistent with other live search patterns across platform

### Changed
- Initiative form now includes Impact section with pink branding
- Workspace filter interface updated with impact level pills

### Database
- **Migration**: `999c86785d6c_add_impact_assessment_fields_to_.py`
- New fields in `initiatives` table: `impact_on_challenge`, `impact_rationale`

## [1.32.0] - 2026-03-15

### Added
- **🗺️ Complete Geography Management System**: Track KPIs by physical location
  - **3-tier hierarchy**: Regions → Countries → Sites (organization-scoped)
  - **Database schema**: 4 new tables with full cascade delete support
  - **Admin UI**: Full CRUD for geography entities with modern tree view
  - **KPI Assignment**: Optional multi-site assignment in KPI create/edit forms
  - **Interactive Map Dashboard**: Leaflet.js-powered map with circle markers
  - **GeoJSON API**: `/org-admin/geography/api/sites.json` for map data
  - **Coordinate support**: Latitude/longitude for precise site locations
  - **Visual hierarchy**: Purple gradients (regions), green (countries), red (sites)
  - **Statistics display**: Region/country/site counts in org admin dashboard
  - **Active/inactive sites**: Control site visibility and map display
  - **Empty states**: Helpful setup instructions when no geography data exists
  - **Audit logging**: Complete audit trail for all geography operations

### Changed
- **Organization Admin Dashboard**: Added Geography Management card
- **Map Dashboard**: Added to Dashboards dropdown (Overview, Executive, Analytics, Map View)
- **Navigation**: Geography accessed via Organization Administration section

### Database
- **Migration**: `5553507a4208_add_geography_hierarchy_regions_.py`
- **New tables**: `geography_regions`, `geography_countries`, `geography_sites`, `kpi_site_assignments`
- **Indexes**: All foreign keys indexed for performance
- **Cascade delete**: Full cascade support (region → countries → sites → assignments)

### Documentation
- **GEOGRAPHY_FEATURE.md**: Complete technical documentation (45 pages)
- **GEOGRAPHY_QUICKSTART.md**: 60-second setup guide for users
- **Future roadmap**: Workspace filtering, geographic rollups, CSV import (Phases 6-9)

## [1.31.0] - 2026-03-14

### Added
- **🎨 Dynamic Entity Colors in Rollup Configuration**: Rollup level headers now use gradient colors based on entity type branding
  - Level 1 (KPI→System): gradient from KPI color to System color
  - Level 2 (System→Initiative): gradient from System color through Initiative to Challenge color
  - Level 3 (Initiative→Challenge): gradient from Initiative through Challenge to Space color
  - Colors dynamically reflect organization's branding settings instead of hardcoded values
  - Visual consistency across the application

### Fixed
- **✅ Branding Color Persistence**: Colors now save correctly in branding manager
  - Added missing icon input fields (server requires both color AND icon to save)
  - Colors persist after page reload
  - Custom entity colors now appear in workspace tree view with light tints (6-15% opacity)
- **📏 Dashboard Stat Box Heights**: All 7 stat boxes now have uniform height
  - Changed from `min-height: 80px` to `height: 80px`
  - Consistent visual appearance across dashboard

### Changed
- **📝 Simplified Rollup Configuration Headers**: Clearer, more concise level descriptions
  - Removed confusing "Primary/Secondary" text that didn't add value
  - Simplified headers: "Level 1: KPI → System", "Level 2: System → Initiative", "Level 3: Initiative → Challenge"
  - Each level clearly shows exactly one aggregation step
- **🏢 Workspace Description**: Updated Open Workspace button text
  - Now reads: "View and manage Spaces, Challenges, Initiatives, Systems, KPIs and track progress"
  - Explicitly lists all entity types users can manage

## [1.28.0] - 2026-03-13

### Added
- **🎯 Complete Target System**: Three target types with visual indicators
  - **↑ Maximize** (at or above): Shows green zone above target line on charts
  - **↓ Minimize** (at or below): Shows green zone below target line on charts
  - **± Exact** (at with tolerance band): Shows tolerance band (e.g., ±10%) on charts
  - Target badges in pivot table showing type and tolerance
  - Target indicator (🎯) next to KPI names in table
  - Tooltip on hover showing target value and date
- **📊 Enhanced Pivot Table**: Show targets column toggle
  - Displays target value, date, and type badge for each KPI
  - Works with all three target types
  - Respects filters (space, challenge, value type, date range)
- **📈 Target Lines on Charts**: Visual target representation
  - Dashed target line for all target types
  - Green shaded zones for maximize/minimize targets
  - Colored tolerance bands for exact targets
  - Chart legend shows target direction (↑, ↓, ±)
- **📥 Enhanced Excel Export**: Comprehensive metadata columns
  - Added columns: Organization, Space, Challenge, Initiative, System (before KPI)
  - Added target columns: Target Value, Target Date, Target Direction, Target Tolerance %
  - All filters applied to export (space, challenge, value type, date range)
  - Hierarchical organization for better data analysis
- **🔍 Live KPI Search**: Quick add KPIs to charts
  - Search input in Chart Builder section
  - Instant results as you type (200ms debounce)
  - Searches only within filtered KPIs (respects space/challenge/value type filters)
  - Shows target badges in search results (🎯↑ 🎯↓ 🎯±)
  - Indicates already-selected KPIs with badge
  - One-click to add KPI to chart (auto-checks checkbox)
  - Toast notification on successful add
  - No scrolling needed through large KPI tables
- **🧪 Test Data Generator**: Comprehensive fake dataset script
  - Script: `create_full_fake_dataset.py`
  - Creates 10 KPIs with all target type examples:
    - 2 maximize targets (Revenue, Customer Satisfaction)
    - 3 minimize targets (Operating Costs, CAC, Support Response Time)
    - 2 exact targets with bands (Product Dev Time ±15%, Inventory ±10%)
    - 3 KPIs with no targets (Marketing, R&D, Infrastructure)
  - 36 months of data (Jan 2024 - Dec 2026)
  - Realistic trends and volatility
  - Two value types: Cost and Time to Deliver
  - Creates complete hierarchy: Space → Challenge → Initiative → System → KPIs

### Fixed
- **✅ Show Targets Toggle**: Fixed checkbox not submitting value
  - Added explicit `value="on"` attribute
  - Target column now appears/disappears correctly when toggled
- **📅 Multiple Snapshots Per Period**: Uses most recent snapshot
  - Fixed issue where multiple snapshots in same month/quarter/year could overwrite each other
  - Now orders by `snapshot_date DESC` to get most recent first
  - Only stores first (most recent) snapshot per period for each KPI
  - Predictable and correct behavior when multiple snapshots exist

### Changed
- **🎨 Pivot Table UI**: Improved target display
  - Target column has yellow background (#fff3cd) for visibility
  - Target badges color-coded: green (maximize), blue (minimize), yellow (exact)
  - Selected KPIs info text updated to mention "Quick Add search"
- **📊 Chart Builder Layout**: Added Quick Add section
  - New search input above "Selected KPIs" section
  - Helper text explains search is within filtered results
  - Improved workflow for building charts with many KPIs

### Database Changes
- **🗄️ New Table: `saved_charts`**
  - Migration: `6dbe28a58429_add_savedchart_model_for_persistent_.py`
  - Stores user-saved chart configurations (filters, KPIs, colors)
  - Columns: name, description, year range, view type, chart type, space filter, value type filter, period filter, KPI config IDs with colors (JSON), sharing status
  - Foreign keys: organization_id, created_by_user_id, space_id (optional), value_type_id (optional)
  - Supports private/public charts within organization

## [1.27.1] - 2026-03-13

### Added
- **🧪 Comprehensive Rollup Test Suite**: 28 new unit tests ensuring type safety in aggregations
  - Type mixing tests: Decimal + float + int combinations across all formulas
  - All aggregation formulas: sum, min, max, avg, median, count
  - Consensus calculations with mixed types
  - Partial data scenarios (5/6 KPIs with values)
  - Qualitative value aggregation (risk, sentiment, etc.)
  - Edge cases: zero values, negatives, very large/small numbers, high-precision decimals
  - Real-world test cases using production data patterns
  - Test file: `tests/unit/test_rollup.py`
- **🌍 Global KPIs Feature**: KPIs without governance bodies
  - KPIs can now be created without any governance body assignment
  - Global KPIs always visible regardless of governance body filters
  - UI explanation added to KPI creation/edit forms
  - Backend validation updated to allow empty governance body selection
  - Useful for organization-wide metrics that transcend specific committees

### Fixed
- **🔢 Rollup Type Safety**: Fixed Decimal/float mixing in all aggregation formulas
  - All aggregation operations now convert to float before calculation
  - Prevents `TypeError: unsupported operand type(s) for +: 'float' and 'decimal.Decimal'`
  - Affects: sum, min, max, avg, median formulas
  - Ensures consistent float return types across all aggregations
  - Formula KPIs (float) + Manual KPIs (Decimal) now aggregate correctly
- **📐 Formula KPI Rollup**: Fixed formula KPIs not participating in rollups
  - Changed `ConsensusService.get_cell_value()` to delegate to formula/linked KPI calculations
  - Formula KPIs now correctly roll up to System → Initiative → Challenge → Space
  - Linked KPIs also properly included in rollups
- **⚠️ Partial Rollup Support**: Removed strict `is_complete` requirement
  - Rollups now work with partial data (e.g., 5/6 KPIs have values)
  - Shows warning indicator (⚠) when rolling up incomplete data
  - Previously blocked all rollups if any KPI was missing data

### Changed
- **🎨 Consistent Navigation Buttons**: Standardized across SWOT, Initiative Form, and Porter's Five Forces
  - All "Back" buttons now say "Back to Workspace" for clarity
  - All "Edit" buttons in view mode use `btn-outline-light` styling
  - SWOT and Porter's edit modes now have "Back to Workspace" in header
  - Initiative Form edit mode: removed duplicate bottom navigation (only in header now)
  - Organization name badge in navbar now links to Dashboard (was Workspace)
- **📊 Table Display Improvements**: Better space usage and visibility
  - All table cells use `white-space: nowrap` (no multi-line wrapping)
  - Saves vertical space, allows more rows visible on screen
  - True auto-sizing: removed all `min-width` constraints from columns
  - Columns size dynamically based on content
  - Collapsed columns fully hide content with improved CSS (`font-size: 0`, `visibility: hidden`)

### Technical
- **Type Conversion**: All aggregation service methods now explicitly convert to `float()`
- **Consensus Delegation**: Formula/linked KPIs use `config.get_consensus_value()` instead of contribution-based consensus
- **Test Coverage**: Rollup functionality now has 28 dedicated tests (100% passing)
- **CSS Improvements**: Stronger selectors and multiple fallbacks for hiding collapsed column content

### Database
- No migrations required for this release

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
