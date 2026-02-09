# CISK Navigator - Architecture Documentation

## Overview
CISK Navigator is a Flask-based web application for visualizing relationships between Challenges, Initiatives, Systems, and KPIs. It provides three interactive views: Column view (traditional hierarchical layout), Graph view (force-directed network visualization), and Flow view (Sankey diagram showing relationship strength).

**Current Version:** 2.7.5
**Local Development:** http://localhost:5002
**Deployment:** https://cisk-navigator.onrender.com/
**GitHub:** https://github.com/mounirdous/CISK-Navigator

## Recent Updates (v2.7.x)
- **v2.7.5** (2026-02-09): Graph and Flow view selections sync back to Column view - full bidirectional sync
- **v2.7.4** (2026-02-09): Flow view uses gradient colors - flows transition from source color to target color
- **v2.7.3** (2026-02-09): Flow view shows selected node with visual highlight and selection indicator
- **v2.7.2** (2026-02-09): Column view selections properly sync to Graph and Flow views
- **v2.7.1** (2026-02-09): Flow view selections sync to Graph view, filters persist when switching views
- **v2.7.0** (2026-02-09): Flow view redesigned with colored dots instead of boxes
- **v2.6.x** (2026-02-09): Flow View (Sankey diagram) implementation, season filtering, selection sync
- **v2.5.x** (2026-02-07): Color customization, mobile touch support, mouse wheel zoom, tooltips
- **v2.4.0** (2026-02-07): Analytics tracking support via YAML meta.tracking_code field

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

### Color Customization (v2.5.0+)

Users can customize colors via YAML `meta.colors` section:
```yaml
meta:
  colors:
    challenge: '#f0d24f'    # Yellow (default)
    initiative: '#8fd0ff'   # Light blue (default)
    system: '#1d4ed8'       # Dark blue (default)
    kpi: '#22c55e'          # Green (default)
```

Colors are injected as CSS variables and used across all views.

### Global State Management

```javascript
const state = {
  tab: 'challenges',           // Current tab: challenges/initiatives/systems/kpis
  selected: null,              // {type, id} - Currently selected item
  preview: null,               // {type, id} - Right-click preview
  initSeason: 'ALL',           // Filter: 'ALL', 'S1', 'S2', 'S3'
  viewMode: 'column'           // 'column', 'graph', or 'flow'
};

const graph = {
  canvas: null, ctx: null,
  nodes: [], links: [],
  selectedNode: null,          // Currently selected node in graph
  filteredNodes: null,         // Set of visible node IDs when filtered
  filteredLinks: null,         // Set of visible links when filtered
  zoom: 1, panX: 0, panY: 0,
  history: []                  // Navigation history for back button
};

const flow = {
  canvas: null, ctx: null,
  nodes: [], links: [],
  selectedNode: null,          // Currently selected node in flow
  filteredNodes: null,         // Set of visible node IDs when filtered
  filteredLinks: null,         // Set of visible links when filtered
  zoom: 1, panX: 0, panY: 0,
  colors: {}                   // Cached colors for performance
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
Force-directed network visualization using HTML5 Canvas with interactive filtering and tooltips.

**Node Types (Customizable Colors):**
- Group (Challenge Group) - Yellow/custom
- Challenge (Sub-Challenge) - Yellow/custom
- Initiative - Light Blue/custom
- System - Dark Blue/custom
- KPI - Green/custom

**Link Types:**
- Group → Challenge (weight-based thickness)
- Challenge → Initiative (weight-based thickness, shows impact H/M/L)
- Initiative → System (weight-based thickness)
- System → KPI (weight-based thickness)

**Features:**
- Click node to filter to related chain
- Hover for tooltips showing full names
- Mouse wheel zoom (desktop)
- Pinch-to-zoom (mobile)
- Drag to pan
- Back button with history
- Fit to view button
- Selection persists across view switches

**Key Graph Functions:**
- `renderGraph()` - Initialize and render full graph
- `buildGraphData()` - Converts DATA to graph nodes/links with season filtering
- `layoutGraph()` - Force-directed layout algorithm
- `drawGraph()` - Render nodes and links with current zoom/pan
- `selectGraphNode(node)` - Filter graph and sync to other views
- `clearGraphSelection()` - Show full graph
- `graphGoBack()` - Navigate back through selection history
- `graphFitToView()` - Auto-zoom to fit content
- `updateGraphUI()` - Update back button and selection indicator

**Interaction Modes:**
- **Desktop**: Mouse wheel zoom, drag to pan, click to select
- **Mobile**: Pinch-to-zoom, single-finger pan, tap to select

#### 3. Flow View (Sankey Diagram) - v2.6.0+
Sankey diagram visualization showing relationship strength through flow thickness and gradient colors.

**Structure:**
- 5 columns: Challenge Groups → Sub-Challenges → Initiatives → Systems → KPIs
- Nodes: Small colored dots (5-8px radius)
- Links: Bezier curves with gradient colors and weight-based thickness

**Visual Design:**
- **Dots**: Color-coded by type, larger when selected (8px), glow effect on selection
- **Flows**: Linear gradient from source color to target color (e.g., yellow challenge → blue initiative)
- **Labels**: Text positioned left of columns 0-2, right of columns 3-4
- **Selection**: White border + glow ring around dot, bold white text, selection info at top

**Features:**
- Click any node (dot or text) to filter to complete chain
- Hover for tooltips showing full text
- All nodes clickable with expanded hitbox including text
- Gradient flows show source → target color transition
- Season filtering applies to flow
- Selection syncs with Graph and Column views
- Zoom in/out/reset controls

**Key Flow Functions:**
- `initFlowView()` - Initialize canvas, cache colors, build data
- `buildFlowData()` - Create flow nodes and links with season filtering
- `layoutFlowDiagram()` - Position nodes in 5 columns with reasonable heights (30-150px)
- `drawFlowDiagram()` - Render gradient flows and colored dots
- `selectFlowNode(nodeId)` - Filter flow and sync to other views
- `updateFlowUI()` - Update selection indicator at top
- `setupFlowInteractions()` - Click, hover, tooltip handlers

**Gradient Flow Colors:**
- Each link uses linear gradient from source node color to target node color
- 80% opacity when normal, 100% when hovered
- Makes flow origin and destination visually clear

### View Synchronization (Full Bidirectional) - v2.7.5

**Problem:** Maintain a single global selection across three views while preventing circular sync loops.

**Solution:** `isSyncing` flag + bidirectional sync functions

**Synchronization Matrix:**
```
         TO: Column | Graph | Flow
FROM:
Column       ✓        ✓       ✓
Graph        ✓        ✓       ✓
Flow         ✓        ✓       ✓
```

**Key Functions:**

```javascript
let isSyncing = false; // Prevents circular loops

// Column → Graph/Flow
function select(type, id, {autoTab, forceSelect}) {
  state.selected = {type, id};

  // Clear graph/flow selections so new column selection propagates
  if (graph.canvas) {
    graph.selectedNode = null;
    graph.filteredNodes = null;
    graph.filteredLinks = null;
  }
  if (flow.canvas) {
    flow.selectedNode = null;
    flow.filteredNodes = null;
    flow.filteredLinks = null;
  }

  // Sync to active view immediately
  if (state.viewMode === 'graph' && !isSyncing) {
    syncColumnToGraphView(type, id);
  }
  if (state.viewMode === 'flow') {
    syncColumnToFlowView(type, id);
  }
}

// Graph → Column
function syncGraphToColumnView(node) {
  if (isSyncing) return;
  isSyncing = true;
  try {
    const type = mapGraphTypeToColumnType(node.type);
    select(type, node.entityId, {forceSelect: true, autoTab: getTabForType(type)});
  } finally {
    isSyncing = false;
  }
}

// Graph → Flow
function syncGraphToFlowView() {
  if (!graph.selectedNode || !flow.canvas) return;
  selectFlowNode(graph.selectedNode.entityId);
}

// Flow → Graph
function syncFlowToGraphView() {
  if (!flow.selectedNode || !graph.canvas) return;
  const graphNodeId = mapFlowIdToGraphId(flow.selectedNode.id, flow.selectedNode.type);
  const graphNode = graph.nodes.find(n => n.id === graphNodeId);
  if (graphNode) selectGraphNode(graphNode);
}

// Flow → Column
// Handled in selectFlowNode() by calling select() with isSyncing guard
```

**Synchronization on View Switch:**

When switching views, priority order:
1. **To Graph**: Graph selection > Flow selection > Column selection > Show all
2. **To Flow**: Flow selection > Graph selection > Column selection > Show all
3. **To Column**: Sync from Graph/Flow if their selection differs from Column

**Key Points:**
1. Single source of truth: The view selection states (state.selected, graph.selectedNode, flow.selectedNode)
2. When user selects in any view, it clears the other views' selections
3. When switching views, existing selections are preserved unless a different view has a selection
4. `isSyncing` flag prevents infinite loops when syncing back to column view
5. All three views stay synchronized at all times

### Event Handling

**Column View:**
- Left click: `select(type, id)` - Selects item and syncs to Graph/Flow
- Right click: `preview(type, id)` - Shows preview (also syncs)

**Graph View:**
- Click node: `selectGraphNode(node)` - Filters graph and syncs to Column/Flow
- Click background: `clearGraphSelection()` - Shows full graph
- Drag: Pan canvas
- Mouse wheel (desktop): Zoom towards cursor
- Pinch (mobile): Zoom with two fingers
- Pan (mobile): Drag with one finger
- Hover: Show tooltip with full node name
- Back button: Navigate through selection history

**Flow View:**
- Click node (dot or text): `selectFlowNode(nodeId)` - Filters flow and syncs to Column/Graph
- Click background: Reset filter to show full flow
- Hover: Show tooltip with full label, highlight dot and text
- Zoom buttons: Zoom in/out/reset
- Expanded clickable area includes text labels (150px)

**Mobile Touch Support (v2.5.1+):**
- Viewport meta tag: `user-scalable=no, maximum-scale=1` to prevent page zoom
- Touch events: `touchstart`, `touchmove`, `touchend` with `{ passive: false }`
- Canvas style: `touch-action: none` to prevent default gestures
- Pinch-to-zoom calculates distance between two touches
- Single-finger pan when not zooming

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

### 1. Why Three View Modes?
- **Column view**: Best for detailed reading and traditional navigation
- **Graph view**: Best for understanding network structure and connections
- **Flow view**: Best for seeing relationship strength and flow patterns
- Each view serves different analysis needs

### 2. Why Force-Directed Layout (Graph View)?
- Automatically arranges nodes based on relationships
- Visually shows clusters and patterns
- More intuitive than hierarchical tree for multi-links

### 3. Why Sankey Diagram (Flow View)?
- Weight-based flow thickness shows relationship strength at a glance
- Linear columns make it easy to trace left-to-right flow
- Gradient colors show source → target transitions visually

### 4. Why HTML5 Canvas vs SVG?
- Better performance for large graphs (100+ nodes)
- Smooth animations and interactions
- Custom rendering control (gradients, transforms)
- Native support for touch events

### 5. Why Embed Data in HTML?
- Single-file distribution (standalone HTML)
- No external API calls required
- Works offline
- Easy to share and archive

### 6. Why Priority System?
- 1 = High priority (⭐⭐⭐)
- 2 = Medium priority (⭐⭐)
- 3 = Low priority (⭐)
- Helps users focus on critical items

### 7. Why Weight-Based Link Thickness?
- Visual indication of relationship strength
- Weight 1-10 maps to line thickness
- Helps identify key dependencies

### 8. Why Gradient Colors in Flow View?
- Shows origin and destination of each flow
- Makes it easy to trace flows visually
- Eliminates ambiguity about flow direction
- More intuitive than single-color flows

### 9. Why Customizable Colors?
- Different organizations have brand colors
- Some users prefer specific color schemes
- Maintains consistency across views
- Colors stored in YAML for version control

### 10. Why Bidirectional Sync?
- Single source of truth across all views
- Users can work in their preferred view
- Selections persist when switching views
- Reduces cognitive load - one selection, visible everywhere

---

## Version History

### v2.7.5 (Current - 2026-02-09)
- Full bidirectional synchronization: Graph/Flow → Column
- Selections in any view update all other views

### v2.7.4 (2026-02-09)
- Flow view gradient colors: flows transition from source color to target color
- More intuitive flow visualization

### v2.7.3 (2026-02-09)
- Flow view selection indicator with visual highlight
- Selected dot: larger size, white border, glow effect
- Selection info displayed at top of Flow view

### v2.7.2 (2026-02-09)
- Column view selections properly sync to Graph and Flow
- Fixed: selecting in column now updates graph/flow filters

### v2.7.1 (2026-02-09)
- Flow view selections sync to Graph view
- Filters persist when switching between views

### v2.7.0 (2026-02-09)
- Flow view redesigned: colored dots instead of large boxes
- Clickable text labels with expanded hitbox
- Hover highlights and tooltips

### v2.6.9 (2026-02-09)
- Flow view nodes maintain reasonable size (30-150px) when filtered

### v2.6.8 (2026-02-09)
- "Show All" button resets filters in all views
- Season filtering applies to Flow view

### v2.6.6-v2.6.7 (2026-02-09)
- Flow view filtered layout uses full canvas space
- All node types clickable in Flow view

### v2.6.5 (2026-02-09)
- Fixed challenge group links in Flow view (groupId vs group_id)

### v2.6.0-v2.6.4 (2026-02-09)
- **Flow View (Sankey Diagram)** - Major feature
- 5 columns: Groups → Challenges → Initiatives → Systems → KPIs
- Weight-based flow thickness
- Clickable nodes with filtering
- Synchronized with Graph and Column views

### v2.5.3 (2026-02-07)
- Tooltips on hover for truncated node names in Graph view

### v2.5.2 (2026-02-07)
- Mouse wheel zoom on desktop (scroll to zoom towards cursor)

### v2.5.1 (2026-02-07)
- Mobile touch support: pinch-to-zoom and pan on iPhone/Android
- Prevents page zoom, enables canvas-only gestures

### v2.5.0 (2026-02-07)
- **Customizable colors** via YAML meta.colors section
- Applies to all views (Column, Graph, Flow)

### v2.4.0 (2026-02-07)
- Analytics tracking support via YAML meta.tracking_code

### v2.3.x (2026-02-07)
- Dual version display (app + data)
- Customizable YAML title
- Fixed graph navigation bugs

### v2.2
- Fixed graph-to-column synchronization
- Added `isSyncing` flag

### v2.1
- Graph link thickness matches weight
- "Fit to View" button

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

1. **Search/Filter** - ~~Add search bar to filter by text~~ ✅ Implemented
2. **Export** - Export graph/flow as PNG/SVG
3. **Edit Mode** - Allow in-app editing of connections
4. **Undo/Redo** - History for selections and filters (partially implemented with graph back button)
5. **Multi-select** - Select multiple nodes
6. **Custom Colors** - ~~User-defined color schemes~~ ✅ Implemented (v2.5.0)
7. **Analytics** - Show statistics (most connected nodes, etc.)
8. **Collaboration** - Share specific views via URL parameters
9. **Animation** - Animated transitions when filtering/selecting
10. **Diff View** - Compare two versions of data side-by-side

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

**Basic Functionality:**
- [ ] Load sample data in browser
- [ ] Upload custom YAML file
- [ ] Switch between all tabs (Challenges/Initiatives/Systems/KPIs)
- [ ] Switch between all views (Column/Graph/Flow)

**Column View:**
- [ ] Click items in column view
- [ ] Search functionality works
- [ ] Preview (right-click) works

**Graph View:**
- [ ] Click nodes in graph view to filter
- [ ] Test "Fit to View" button
- [ ] Test zoom and pan (mouse wheel on desktop)
- [ ] Test Back button navigation
- [ ] Hover shows tooltips

**Flow View:**
- [ ] Click nodes (dots and text) to filter
- [ ] Hover shows tooltips
- [ ] Gradient colors visible in flows
- [ ] Zoom in/out/reset buttons work
- [ ] Selected node shows highlight (white border + glow)

**View Synchronization:**
- [ ] Column → Graph sync: Select in column, switch to graph, verify selection
- [ ] Column → Flow sync: Select in column, switch to flow, verify selection
- [ ] Graph → Column sync: Click in graph, switch to column, verify highlighted in sidebar
- [ ] Graph → Flow sync: Click in graph, switch to flow, verify selection
- [ ] Flow → Column sync: Click in flow, switch to column, verify highlighted in sidebar
- [ ] Flow → Graph sync: Click in flow, switch to graph, verify selection

**Filtering:**
- [ ] Season filter (S1/S2/S3/ALL) works in all views
- [ ] "Show All" button resets all views
- [ ] Filtered views show only related nodes/items

**Mobile Testing (iPhone/Android):**
- [ ] Pinch-to-zoom works in Graph view
- [ ] Pinch-to-zoom works in Flow view
- [ ] Single-finger pan works
- [ ] Page zoom is prevented (only canvas zooms)
- [ ] Tap to select works
- [ ] Responsive layout works

**Desktop Testing:**
- [ ] Mouse wheel zoom works
- [ ] Drag to pan works
- [ ] Hover tooltips work
- [ ] Click to select works

**Download & Distribution:**
- [ ] Download standalone HTML
- [ ] Verify standalone HTML works offline
- [ ] Verify both app and data versions displayed

**Custom Colors:**
- [ ] Upload YAML with custom colors
- [ ] Verify colors apply to Column view
- [ ] Verify colors apply to Graph view nodes/links
- [ ] Verify colors apply to Flow view dots/flows

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

## Shared Filtering Logic

The `computeRelatedEntities(entityType, entityId, allLinks)` function is shared between Graph and Flow views to ensure consistent filtering behavior. It traces the full chain of relationships:

- **Challenge Group**: Downstream to challenges → initiatives → systems → KPIs
- **Challenge**: Upstream to group, downstream to initiatives → systems → KPIs
- **Initiative**: Upstream to challenges + groups, downstream to systems → KPIs
- **System**: Upstream to initiatives → challenges → groups, downstream to KPIs
- **KPI**: Upstream through full chain to groups

This ensures that when you select any node, you see the complete connected chain in all views.

---

*Last updated: 2026-02-09 (v2.7.5)*
