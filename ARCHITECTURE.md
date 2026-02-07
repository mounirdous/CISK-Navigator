# CISK Navigator - Architecture Documentation

## Overview
CISK Navigator is a Flask-based web application for visualizing relationships between Challenges, Initiatives, Systems, and KPIs. It provides two interactive views: a column-based view and a graph-based network visualization.

**Current Version:** 2.4.0
**Local Development:** http://localhost:5002
**Deployment:** https://cisk-navigator.onrender.com/
**GitHub:** https://github.com/mounirdous/CISK-Navigator

## Recent Updates (v2.4.x)
- **v2.4.0** (2026-02-07): Analytics tracking support via YAML meta.tracking_code field
- **v2.3.3** (2026-02-07): Fixed graph navigation bug (A→B→A scenario)
- **v2.3.1** (2026-02-07): Upload page documentation improvements, optional YAML version field
- **v2.3.0** (2026-02-07): Dual version display (app version + data version), customizable YAML title

---

## Project Structure

```
CISK-Navigator/
├── app.py                          # Flask application (backend)
├── data/
│   └── full_sample_enhanced.yaml   # Sample data file
├── templates/
│   ├── navigator_enhanced.html     # Main interactive UI
│   └── upload.html                 # File upload interface
├── static/                         # Static assets (if any)
├── requirements.txt                # Python dependencies
└── render.yaml                     # Render deployment config
```

---

## Backend Architecture (app.py)

### Flask Routes

1. **`/` (GET)** - Main application
   - Loads `full_sample_enhanced.yaml`
   - Auto-detects format (enhanced vs legacy)
   - Extracts `title` and `version` from YAML meta section
   - Passes both `data_version` (from YAML) and `app_version` (APP_VERSION constant)
   - Renders `navigator_enhanced.html` with data

2. **`/upload` (GET/POST)` - File upload interface
   - GET: Shows upload form (`upload.html`) with APP_VERSION
   - POST: Accepts YAML file, parses it, renders navigator with uploaded data
   - Extracts title and version from uploaded YAML
   - Returns statistics about uploaded data

3. **`/api/data` (GET)** - JSON API endpoint
   - Returns current data as JSON
   - Used for debugging/external integrations

4. **`/generate` (POST)** - Standalone HTML generator
   - Accepts YAML file
   - Extracts title and version from YAML meta section
   - Generates complete standalone HTML file with embedded data and both versions
   - Returns as downloadable file

### Version Management

- **APP_VERSION**: Defined in `app.py` (currently "2.3.1")
  - Generator application version
  - Displayed as "App v2.3.1" in generated HTML

- **YAML meta.version**: Optional field in YAML files
  - Data structure/schema version
  - Defaults to "1.0" if not provided
  - Displayed as "Data v1.0" in generated HTML

- **YAML meta.title**: Required field
  - Displayed as the main title in generated HTML
  - Replaces hardcoded application title

- **YAML meta.tracking_code**: Optional field (v2.4.0+)
  - Allows injection of analytics tracking scripts
  - Supports Google Analytics, Plausible, Fathom, Matomo, custom tracking
  - Injected into HTML <head> section
  - See `TRACKING_EXAMPLES.md` for examples

### Data Format Conversion

#### Enhanced Format (Current)
Supports multi-links with weights and impacts:
- **Challenge Groups**: `id`, `number`, `title`, `priority` (1-3)
- **Sub-Challenges**: `id`, `group_id`, `text`, `priority` (1-3)
- **Initiatives**: `id`, `season`, `text`, `challenges[]` with `challenge_id`, `weight` (1-10), `impact` (L/M/H)
- **Systems**: `id`, `text`, `title`, `initiatives[]` with `initiative_id`, `weight` (1-10)
- **KPIs**: `id`, `text`, `systems[]` with `system_id`, `weight` (1-10)

#### Legacy Format (Backward Compatible)
Uses `group_id` for simple 1:1 relationships. Automatically converted to enhanced format.

### Key Functions

- **`load_yaml_data(file_path)`** - Loads and parses YAML
- **`convert_enhanced_format(yaml_data)`** - Converts enhanced YAML to JS format
- **`convert_legacy_format(yaml_data)`** - Converts legacy YAML to JS format
- **`auto_detect_format(yaml_data)`** - Auto-detects format based on structure

---

## Frontend Architecture (navigator_enhanced.html)

### Global State Management

```javascript
const state = {
  tab: 'challenges',           // Current tab: challenges/initiatives/systems/kpis
  selected: null,              // {type, id} - Currently selected item
  preview: null,               // {type, id} - Right-click preview
  initSeason: 'ALL',           // Filter: 'ALL', 'S1', 'S2', 'S3', 'S4'
  viewMode: 'column'           // 'column' or 'graph'
};
```

### View Modes

#### 1. Column View
Traditional hierarchical layout with left panel (list) and right panel (details).

**Tabs:**
- Challenges (Challenge Groups + Sub-Challenges)
- Initiatives
- Systems
- KPIs

**Key Functions:**
- `setTab(tab)` - Switch between tabs
- `select(type, id, {autoTab, forceSelect})` - Select an item
- `preview(type, id)` - Right-click preview
- `clearSelection()` - Clear selection
- `renderFocusedDetail()` - Render right panel details

#### 2. Graph View
Force-directed network visualization using HTML5 Canvas.

**Node Types:**
- Group (Challenge Group) - Gray circles
- Challenge (Sub-Challenge) - Blue circles
- Initiative - Green circles
- System - Purple circles
- KPI - Orange circles

**Link Types:**
- Group → Challenge (gray)
- Challenge → Initiative (green, thickness = weight)
- Initiative → System (purple, thickness = weight)
- System → KPI (orange, thickness = weight)

**Key Graph Functions:**
- `buildGraphData()` - Converts DATA to graph nodes/links
- `initGraph()` - Initialize canvas and event listeners
- `layoutGraph()` - Force-directed layout algorithm
- `drawGraph()` - Render nodes and links
- `selectGraphNode(node)` - Filter graph to selected node + related nodes
- `clearGraphSelection()` - Show full graph
- `graphGoBack()` - Navigate back through selection history
- `graphFitToView()` - Auto-zoom to fit content

**Layout Algorithm:**
- Uses force-directed simulation
- Repulsion between all nodes
- Attraction along links
- Damping for stability
- Runs for 300 iterations

### View Synchronization

**Problem:** Prevent circular sync loops when updating selection between column and graph views.

**Solution:** `isSyncing` flag

```javascript
let isSyncing = false;

function syncGraphToColumnView(node) {
  if (isSyncing) return;
  isSyncing = true;
  try {
    // Map graph node type to column type
    // Call select() with forceSelect and autoTab
    select(type, id, {forceSelect: true, autoTab: tab});
  } finally {
    isSyncing = false;
  }
}

function syncColumnToGraphView(type, id) {
  if (isSyncing) return;
  isSyncing = true;
  try {
    // Find node in graph
    // Call selectGraphNode()
  } finally {
    isSyncing = false;
  }
}

function select(type, id, {autoTab, forceSelect}) {
  // Update state and UI

  // Only sync to graph if NOT already syncing
  if (state.viewMode === 'graph' && !isSyncing) {
    syncColumnToGraphView(type, id);
  }
}
```

**Key Points:**
1. Clicking in graph → `selectGraphNode()` → `syncGraphToColumnView()` → `select()` (skips graph sync due to flag)
2. Clicking in column → `select()` → `syncColumnToGraphView()` → `selectGraphNode()`
3. `isSyncing` flag prevents infinite loops

### Event Handling

**Column View:**
- Left click: `select(type, id)`
- Right click: `preview(type, id)`

**Graph View:**
- Click node: `selectGraphNode(node)`
- Click background: `clearGraphSelection()`
- Drag: Pan canvas
- Scroll: Zoom in/out
- Double-click background: Fit to view

---

## Data Flow

```
YAML File
    ↓
Flask Backend (app.py)
    ↓
Auto-detect format
    ↓
Convert to JS format
    ↓
Jinja2 Template (navigator_enhanced.html)
    ↓
Embedded as DATA variable
    ↓
JavaScript renders UI
    ↓
User interaction updates state
    ↓
UI re-renders
```

---

## Key Technical Decisions

### 1. Why Force-Directed Layout?
- Automatically arranges nodes based on relationships
- Visually shows clusters and patterns
- More intuitive than hierarchical tree for multi-links

### 2. Why HTML5 Canvas vs SVG?
- Better performance for large graphs (100+ nodes)
- Smooth animations and interactions
- Custom rendering control

### 3. Why Embed Data in HTML?
- Single-file distribution (standalone HTML)
- No external API calls required
- Works offline

### 4. Why Priority System?
- 1 = High priority (red highlight)
- 2 = Medium priority (orange highlight)
- 3 = Low priority (no highlight)
- Helps users focus on critical items

### 5. Why Weight-Based Link Thickness?
- Visual indication of relationship strength
- Weight 1-10 maps to line thickness 1-5px
- Helps identify key dependencies

---

## Version History

### v2.2 (Current)
- Fixed graph-to-column synchronization
- Added `isSyncing` flag to prevent circular sync loops
- Added `autoTab` parameter to switch tabs when syncing

### v2.1.19
- Re-enabled graph-to-column sync

### v2.1.18
- Added upload statistics banner

### v2.1.17
- Show app version in generated HTML instead of YAML version

### v2.1.16
- Prioritize preview over selected when switching views

### v2.1.14
- Fixed iPhone responsive layout

### v2.1.13
- Made column and graph views independent (no auto-sync)

### v2.1.6
- Auto-fit when graph updates

### v2.1.5
- Added "Fit to View" button

### v2.1
- Graph link thickness matches weight

---

## Deployment

**Platform:** Render.com
**Type:** Web Service
**Build Command:** `pip install -r requirements.txt`
**Start Command:** `gunicorn app:app`
**Auto-Deploy:** Enabled (deploys on git push to main)

**Environment:**
- Python 3.11
- Flask
- PyYAML
- Gunicorn

---

## Common Issues & Solutions

### Issue: Circular sync loop
**Symptom:** Selection doesn't update, console shows "Sync blocked by isSyncing flag"
**Solution:** Check that `isSyncing` flag is properly reset in finally block

### Issue: Graph doesn't fit viewport
**Symptom:** Nodes outside visible area
**Solution:** Click "Fit to View" or double-click background

### Issue: Deployment fails on Render
**Symptom:** Build succeeds but service doesn't start
**Solution:** Check Python version in render.yaml matches requirements.txt

### Issue: Wrong tab shown when clicking graph node
**Symptom:** Selection set but wrong tab visible
**Solution:** Ensure `autoTab` parameter passed to `select()` in `syncGraphToColumnView()`

---

## Future Enhancement Ideas

1. **Search/Filter** - Add search bar to filter by text
2. **Export** - Export graph as PNG/SVG
3. **Edit Mode** - Allow in-app editing of connections
4. **Undo/Redo** - History for selections and filters
5. **Multi-select** - Select multiple nodes
6. **Custom Colors** - User-defined color schemes
7. **Analytics** - Show statistics (most connected nodes, etc.)
8. **Collaboration** - Share specific views via URL parameters

---

## Code Style Guidelines

1. Use camelCase for JavaScript variables/functions
2. Use snake_case for Python variables/functions
3. Keep functions small and focused
4. Document complex algorithms with comments
5. Use semantic HTML5 elements
6. Maintain consistent indentation (2 spaces)

---

## Testing Checklist

- [ ] Load sample data in browser
- [ ] Upload custom YAML file
- [ ] Switch between all tabs
- [ ] Click items in column view
- [ ] Click nodes in graph view
- [ ] Verify column-to-graph sync
- [ ] Verify graph-to-column sync
- [ ] Test season filter (S1/S2/S3/S4/ALL)
- [ ] Test "Fit to View" button
- [ ] Test graph zoom and pan
- [ ] Test on mobile (responsive layout)
- [ ] Download standalone HTML
- [ ] Verify standalone HTML works offline

---

## Debugging Tips

**Console Logging:**
- Look for "select() called" to trace selections
- Look for "syncGraphToColumnView" / "syncColumnToGraphView" to trace sync
- Look for "isSyncing" messages to debug sync loops

**Common Debug Commands:**
```javascript
// In browser console
console.log(state);           // Check current state
console.log(DATA);            // Check loaded data
console.log(graph.nodes);     // Check graph nodes
console.log(graph.selectedNode); // Check graph selection
console.log(isSyncing);       // Check sync flag
```

---

## Contact & Support

For issues, feature requests, or questions:
- GitHub Issues: https://github.com/mounirdous/CISK-Navigator/issues
- Version updates tracked in git commits

---

*Last updated: 2026-02-06 (v2.2)*
