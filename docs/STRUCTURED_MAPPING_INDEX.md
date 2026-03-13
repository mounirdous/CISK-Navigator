# Structured Mapping System - Index & Usage Guide

**Purpose:** Machine-readable mappings of user journeys, concepts, and code dependencies
**Date:** 2026-03-13
**Version:** 1.0

---

## 📋 What Is This?

This directory contains **structured YAML files** that map:
- **User Journeys** - Every path a user can take (by role)
- **Concepts** - Where features are used across the codebase
- **Dependencies** - Which files/models/services interact
- **Impact Analysis** - What changes when you modify something

**Why YAML?** Machine-readable, version-controlled, can generate visualizations!

---

## 🗂️ File Structure

```
docs/
├─ user-journeys/                  # User journey maps by role
│   ├─ role_regular_user_journey.yaml
│   ├─ role_org_admin_journey.yaml  (TODO)
│   ├─ role_global_admin_journey.yaml  (TODO)
│   └─ role_super_admin_journey.yaml  (TODO)
│
├─ concept-mapping/                 # Feature/concept mappings
│   ├─ concept_target_kpi.yaml     # Where "KPI Target" is used
│   ├─ concept_formula_kpi.yaml    (TODO)
│   ├─ concept_linked_kpi.yaml     (TODO)
│   ├─ concept_consensus.yaml      (TODO)
│   └─ concept_permissions.yaml    (TODO)
│
└─ STRUCTURED_MAPPING_INDEX.md     # This file
```

---

## 🎯 Use Cases

### 1. Impact Analysis

**Question:** "If I change the KPI target calculation, what breaks?"

**Answer:**
```bash
# Search concept_target_kpi.yaml
yq '.templates[].sections' docs/concept-mapping/concept_target_kpi.yaml
yq '.javascript[].operations' docs/concept-mapping/concept_target_kpi.yaml
```

**Result:** See ALL files/lines that use target calculation

---

### 2. Feature Location

**Question:** "Where is the contribution form displayed?"

**Answer:**
```bash
# Search user journey YAML
yq '.journeys[] | select(.name == "Contribute KPI Value")' \
   docs/user-journeys/role_regular_user_journey.yaml
```

**Result:**
```yaml
route: "/workspace/kpi/<id>/contribute"
template: "workspace/kpi_cell_detail.html"
models_used: ["Contribution", "KPI"]
services_used: ["consensus_service.py"]
```

---

### 3. Permission Requirements

**Question:** "What can a user do with only `can_contribute`?"

**Answer:**
```bash
# Find journeys that require this permission
yq '.journeys[] | select(.requires_permission == "can_contribute")' \
   docs/user-journeys/role_regular_user_journey.yaml
```

**Result:** List of all accessible journeys/routes

---

### 4. Simplification Analysis

**Question:** "Is the 'target' concept scattered across too many files?"

**Answer:**
```bash
# Count files that touch target
yq '.templates | length' docs/concept-mapping/concept_target_kpi.yaml
yq '.models | length' docs/concept-mapping/concept_target_kpi.yaml
```

**Result:** If >10 files, consider refactoring to centralize logic

---

### 5. Testing Scope

**Question:** "What tests do I need when changing target calculation?"

**Answer:**
```bash
# Get testing requirements from concept mapping
yq '.impact_analysis[] | select(.change == "Modify target calculation logic").testing_required' \
   docs/concept-mapping/concept_target_kpi.yaml
```

**Result:** Checklist of required tests

---

## 🔍 YAML Structure Reference

### User Journey Files

```yaml
role:
  name: "Role Name"
  db_field: "users.is_super_admin"
  access_level: "Description"

permissions:
  - name: "can_contribute"
    description: "What it allows"
    default: true

journeys:
  - id: "J1"
    name: "Journey Name"
    steps:
      - id: "J1.1"
        name: "Step Name"
        route: "/some/route"
        method: "GET/POST"
        template: "path/to/template.html"
        code_files:
          - "app/routes/something.py"
        models_used:
          - "ModelName"
        services_used:
          - "app/services/something.py"
        next_steps:
          - condition: "If condition"
            goto: "J1.2"
```

### Concept Mapping Files

```yaml
concept:
  name: "Feature Name"
  description: "What it does"

database:
  table: "table_name"
  fields:
    - name: "field_name"
      type: "TYPE"
      description: "Purpose"

models:
  - file: "app/models/model.py"
    class: "ClassName"
    attributes: [...]
    methods: [...]

routes:
  - file: "app/routes/route.py"
    route: "/path"
    methods: ["GET", "POST"]
    operations: [...]

templates:
  - file: "app/templates/template.html"
    sections:
      - name: "Section Name"
        lines: [100-200]
        description: "What it does"

impact_analysis:
  - change: "What you're changing"
    affected_files: [...]
    affected_features: [...]
    testing_required: [...]
```

---

## 🚀 Future Feature: Visual Graph Explorer

### Concept
A **Super Admin feature** that reads these YAML files and generates:
- **Interactive dependency graph**
- **User journey flow diagrams**
- **Impact analysis visualization**
- **Complexity heatmaps**

### Implementation Plan

#### Phase 1: Data Loading
```python
# app/routes/super_admin.py
@bp.route("/graph-explorer")
@login_required
@super_admin_required
def graph_explorer():
    # Load all YAML files
    journeys = load_yaml_files('docs/user-journeys/')
    concepts = load_yaml_files('docs/concept-mapping/')

    # Convert to graph data structure
    graph_data = YAMLGraphService.build_graph(journeys, concepts)

    return render_template('super_admin/graph_explorer.html',
                          graph_data=graph_data)
```

#### Phase 2: Visualization (Frontend)
```javascript
// Use D3.js or Cytoscape.js for graph rendering
// app/templates/super_admin/graph_explorer.html

const nodes = [
  {id: 'route_/workspace', type: 'route', label: '/workspace'},
  {id: 'model_KPI', type: 'model', label: 'KPI'},
  {id: 'service_consensus', type: 'service', label: 'ConsensusService'}
];

const edges = [
  {source: 'route_/workspace', target: 'model_KPI', label: 'uses'},
  {source: 'route_/workspace', target: 'service_consensus', label: 'calls'}
];

// Render interactive graph
renderGraph(nodes, edges);
```

#### Phase 3: Queries & Filters
```javascript
// Features:
// - Search: "Show me everything that uses KPI model"
// - Filter: "Show only Regular User journeys"
// - Highlight: "Highlight paths requiring can_contribute"
// - Impact: "What changes if I modify target calculation?"
```

#### Phase 4: Export & Reports
```python
# Generate reports
- PDF: User journey flowchart
- CSV: Dependency matrix
- JSON: Graph data for external tools
```

### UI Mockup

```
╔══════════════════════════════════════════════════════╗
║ 🗺️ Graph Explorer - System Dependency Visualization ║
╚══════════════════════════════════════════════════════╝

[Search: "target"]  [Filter: User Journeys ▼]  [Export ▼]

┌─────────────────────────────────────────────────────┐
│                                                     │
│    ┌─────────┐                                     │
│    │/workspace│──uses──▶ [KPI]                     │
│    └─────────┘              │                       │
│         │                   │                       │
│      calls                  │                       │
│         ▼                   ▼                       │
│   [Consensus     ┌────────────────┐                │
│    Service]      │ Target Feature │                │
│                  └────────────────┘                │
│                        │                            │
│                    used_by                          │
│                        ▼                            │
│              [kpi_cell_detail.html]                │
│                                                     │
└─────────────────────────────────────────────────────┘

📊 Stats:
- Nodes: 47 (15 routes, 12 models, 8 services, 12 templates)
- Edges: 134
- Max Depth: 6
- Complexity Score: Medium

💡 Impact Analysis for "target":
- Files affected: 5
- Lines of code: ~200
- Test coverage: 40% ⚠️
- Refactoring suggestion: Centralize logic in TargetService
```

---

## 🛠️ Tools & Commands

### Query YAML Files

```bash
# Install yq if needed
brew install yq  # macOS
sudo apt install yq  # Linux

# Find all routes a Regular User can access
yq '.journeys[].steps[].route' docs/user-journeys/role_regular_user_journey.yaml

# Find all models used in KPI creation
yq '.journeys[] | select(.name == "Create KPI").steps[].models_used[]' \
   docs/user-journeys/role_regular_user_journey.yaml

# Count concept occurrences
yq '[.templates[], .models[], .routes[]] | length' \
   docs/concept-mapping/concept_target_kpi.yaml

# Find files that need testing for a change
yq '.impact_analysis[] | select(.change | contains("target")).affected_files[]' \
   docs/concept-mapping/concept_target_kpi.yaml
```

### Validate YAML

```bash
# Check YAML syntax
yamllint docs/user-journeys/*.yaml
yamllint docs/concept-mapping/*.yaml

# Validate against schema (if we create one)
python scripts/validate_mappings.py
```

### Generate Reports

```bash
# Future: Generate dependency graph
python scripts/generate_graph.py --output graph.png

# Future: Generate impact report
python scripts/impact_analysis.py --concept target --format markdown
```

---

## 📚 Related Documentation

- [Role-Based Access Map](roles/ROLE_BASED_ACCESS_MAP.md) - Permission overview
- [User Journey Map](ux-journey/USER_JOURNEY_MAP.md) - UX-focused journeys
- [Architecture](../ARCHITECTURE.md) - System design

---

## ✅ Maintenance Checklist

**When adding a new feature:**
- [ ] Update relevant user journey YAML
- [ ] Create concept mapping YAML (if new concept)
- [ ] Document affected files
- [ ] Add impact analysis section
- [ ] Update testing requirements

**When modifying existing feature:**
- [ ] Update concept mapping YAML
- [ ] Check impact_analysis section
- [ ] Update affected_files list
- [ ] Run required tests
- [ ] Update version_history

**Monthly review:**
- [ ] Verify YAML files match current codebase
- [ ] Update stats (total journeys, routes, etc.)
- [ ] Identify technical debt
- [ ] Plan refactoring based on complexity

---

## 🎓 Best Practices

### DO:
- ✅ Keep YAML files up to date with code changes
- ✅ Add impact analysis for complex features
- ✅ Document business rules
- ✅ Include version history
- ✅ Link related concepts

### DON'T:
- ❌ Duplicate information (use references instead)
- ❌ Let YAML fall behind codebase
- ❌ Skip testing requirements
- ❌ Forget to update after refactoring

---

## 🔄 Next Steps

1. **Complete Coverage:**
   - Create remaining user journey YAMLs (Org Admin, Global Admin, Super Admin)
   - Create concept mappings for major features (Formula, Linked KPI, Consensus)

2. **Automation:**
   - Script to validate YAML structure
   - Script to detect outdated mappings (compare with actual code)
   - CI check to ensure YAMLs are updated with code changes

3. **Visualization:**
   - Implement Graph Explorer feature in Super Admin panel
   - Add interactive dependency explorer
   - Create automated impact analysis reports

4. **Integration:**
   - Link from code comments to YAML mappings
   - Add "View in Graph" button in UI
   - Generate documentation from YAML

---

*These structured mappings are living documents - keep them updated!*
