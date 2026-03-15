# CISK Navigator - Complete User Journey Map

**Purpose:** Map EVERY step users take to ensure THE SIMPLEST POSSIBLE experience

**Date:** 2026-03-12 (Original) | **Updated:** 2026-03-15
**Version:** 1.19.0 → 1.33.32

> **📋 Note:** This document describes user flows from v1.19.0. For a comprehensive UX audit covering v1.33.32 with current issues and recommendations, see [COMPREHENSIVE_UX_AUDIT_v1.33.md](./COMPREHENSIVE_UX_AUDIT_v1.33.md)

## 🆕 What's New Since v1.19.0

### Added in v1.33.32:
- **Entity Links** - Attach URLs/documents to any entity with hover popovers
- **Entity links appear in:**
  - Workspace tree view (link icon with popup)
  - All edit pages (links section with add/delete)
- **Smart icon detection** for Google Docs, GitHub, PDFs, etc.
- **Public/Private sharing** options

### Added in v1.32.0 - v1.33.0:
- **Geography Management** - Track KPIs by location (regions/countries/sites)
- **Mapbox Integration** - Professional mapping with colored country polygons
- **Impact Assessment** - Track initiative impact on challenges
- **Saved Filter Search** - Live search for filter presets
- **Dashboard improvements** - Multiple improvements and refinements

---

## 🎯 CORE PRINCIPLE: SIMPLICITY FIRST

**Every step must be:**
- ✓ Obvious (no guessing)
- ✓ Fast (minimal clicks)
- ✓ Forgiving (no data loss on errors)
- ✓ Clear (purpose always visible)

---

## Journey 0: ORGANIZATION ONBOARDING (NEW!)

### Overview
**Entry Points:**
1. User logs in and selects an empty organization
2. User lands on workspace dashboard with empty org

**Purpose:** Guide users through essential setup before they can work

**Trigger:** Dashboard shows welcome card when organization has:
- 0 spaces AND
- 0 governance bodies AND
- 0 value types

**Flow:**
- Admin creates empty organization (assigns users/permissions only)
- User logs in, selects org, lands on dashboard
- Dashboard shows welcome card: "Start Onboarding"
- User clicks → enters onboarding wizard

### Step 0.1: Welcome Screen
**Page:** `/org-admin/onboarding?step=1`

```
User Journey:
1. User clicks "Start Onboarding" from dashboard welcome card
2. Lands on onboarding wizard step 1
3. Welcome screen explains what's needed:
   - Spaces (organize work by domain)
   - Governance Bodies (oversight committees)
   - Value Types (measurement dimensions)
4. Click "Get Started"

Current State: 🟢 NEW - Clear explanation before setup
Pain Points: None - fresh implementation
Visual: Progress bar (4 steps), friendly rocket icon
```

### Step 0.2: Create First Space
**Page:** `/org-admin/onboarding?step=2`

```
User Journey:
1. Enter space name (e.g., "Digital Transformation")
2. Select space type (determines challenges/frameworks)
3. Add description
4. Click "Continue"
   → Creates space
   → Advances to step 3

Current State: 🟢 NEW - Focused single-purpose form
Pain Points: None - streamlined flow
Visual: Progress bar shows 50% complete
```

### Step 0.3: Create Governance Body
**Page:** `/org-admin/onboarding?step=3`

```
User Journey:
1. Enter governance body name (e.g., "Steering Committee")
2. Enter abbreviation (e.g., "SC")
3. Add description
4. Click "Continue"
   → Creates governance body
   → Advances to step 4

Current State: 🟢 NEW - Same form as regular creation but in-flow
Pain Points: None - reuses existing form logic
Visual: Progress bar shows 75% complete
```

### Step 0.4: Create Value Types
**Page:** `/org-admin/onboarding?step=4`

```
User Journey:
1. Page explains we'll create 3 essentials:
   - Cost (€)
   - Revenue (€)
   - User Satisfaction (sentiment)
2. Click "Create Value Types"
   → Creates all 3 default value types
   → Advances to completion

Current State: 🟢 NEW - Opinionated defaults, no form needed
Pain Points: None - fastest path forward
Note: Users can create more value types later
```

### Step 0.5: Complete & Next Steps
**Page:** `/org-admin/onboarding?step=5`

```
User Journey:
1. Success message: "You're All Set!"
2. Shows clear next steps card:
   1. Create Challenges
   2. Create Initiatives
   3. Add Systems
   4. Create KPIs
   5. View Workspace
3. Click "Go to Organization Dashboard"
   → Redirects to /org-admin

Current State: 🟢 NEW - Clear guidance on what to do next
Pain Points: None - provides roadmap
Visual: Success checkmark, clickable next steps
```

### Onboarding Exit Conditions
**User can skip/exit if:**
- Organization already has spaces, gov bodies, AND value types
  → Automatically skips to step 5 (completion)

**User CANNOT skip:**
- All 3 essentials are required before normal operation
- This prevents "lost" users who don't know what to create first

---

## Journey 1: FIRST TIME USER - Setting Up Organization

### Step 1.1: Create Value Types
**Page:** `/value-types/create`
**Purpose:** Define what you measure (Cost, CO2, Risk, etc.)

```
User Journey:
1. Click "Admin" → "Value Types" → "Create"
2. Enter name (e.g., "Cost")
3. Select kind (Numeric or Qualitative)
4. IF Numeric:
   - Set decimal places
   - Set unit (€, tCO2e, etc.)
5. Click "Create"

Current State: ✅ SIMPLE - No calculation type confusion
Pain Points: None identified
Improvement Ideas:
- Add examples in placeholder text
- Show preview of how it will display
```

### Step 1.2: Create Governance Body
**Page:** `/governance-bodies/create`
**Purpose:** Define who oversees KPIs

```
User Journey:
1. Click "Admin" → "Governance Bodies" → "Create"
2. Enter name (e.g., "Steering Committee")
3. Enter abbreviation (e.g., "SC")
4. Choose color
5. Click "Create"

Current State: ✅ SIMPLE
Pain Points:
- 🔴 If redirected from KPI creation, no explanation WHY
- Users confused about interruption

FIX NEEDED:
Add context message when coming from KPI creation:
"⚠️ KPIs require governance oversight. Create a governance body first,
then you'll return to creating your KPI."
```

### Step 1.3: Build Organization Structure
**Pages:** Create Space → Challenge → Initiative → System

```
User Journey:
1. Dashboard → "Create Space"
2. Space → "Create Challenge"
3. Challenge → "Create Initiative"
4. Initiative → Link System

Current State: ✅ SIMPLE - Clear hierarchy
Pain Points: None identified (out of scope for this doc)
```

---

## Journey 2: CREATE KPI - Manual Entry Type

### Step 2.1: Start KPI Creation
**Page:** `/kpis/create/<link_id>`
**Entry:** Click "+" on Initiative-System link

```
User Journey:
1. Enter KPI name & description
2. Select value types (checkboxes)
3. Select governance bodies (checkboxes)
   - 🟢 NEW: Auto-selects if only one exists
4. Configure colors (optional)
5. Click "Create KPI"

Current State: 🟢 IMPROVED - Form data preserved on error
Pain Points FIXED:
- ✅ Form no longer clears on validation error
- ✅ Auto-selects single governance body

Remaining Pain Points: None
```

### Step 2.2: View KPI Detail (Manual)
**Page:** `/kpi/<id>/value-type/<vt_id>`

```
User Journey:
1. See large centered value card:
   ┌──────────────────────────────────┐
   │ 🧑‍🤝‍🧑 MANUAL ENTRY              │
   │ STRONG CONSENSUS                 │
   │                                  │
   │      1,250,000.00 CHF           │  ← BIG!
   │                                  │
   │ Based on 3 contributions         │
   └──────────────────────────────────┘

2. Scroll down to "Add/Update Contribution"
3. Enter name, value, comment
4. Click "Submit"

5. See updated consensus immediately

Current State: ✅ EXCELLENT - Context-aware, prominent value
Pain Points: None identified
```

---

## Journey 3: CREATE KPI - Formula Type

### Step 3.1: Create KPI (Same as Journey 2.1)
```
Same steps as manual KPI creation.
Calculation type is NOT chosen at creation - chosen later.
```

### Step 3.2: Configure Formula
**Page:** KPI Detail → "Edit Formula" button → Modal

```
🔴 CRITICAL ISSUE - Current Experience:

User Journey (BROKEN):
1. Click "Edit Formula" button
2. Modal opens
3. See mode selection at top
4. ❌ HAVE TO SCROLL to see result
5. Search for KPIs (giant cards everywhere)
6. ❌ Can't see result while selecting KPIs
7. More scrolling...
8. Finally see formula result at bottom
9. ❌ Have to scroll back up to save button

USER FRUSTRATION: "Where's the result?! I can't see what I'm building!"

---

✅ TARGET EXPERIENCE (SIMPLE):

User Journey (FIXED):
1. Click "Edit Formula" button
2. Modal opens
3. See mode selection at top
4. ✅ IMMEDIATELY see result:
   ╔══════════════════════════════════╗
   ║ 🎯 RESULT: 1,250,000.00 CHF    ║  ← NO SCROLLING!
   ║ ✓ Auto-updates when sources    ║
   ║   change                        ║
   ╚══════════════════════════════════╝

5. See compact selected KPIs list:
   Selected (2):
   • ERP Costs → 1,000,000 CHF [×]
   • Licence → 250,000 CHF [×]

6. Click [+ Add KPI] (search appears inline)
7. Select operation: SUM / AVG / etc.
8. Result updates LIVE while selecting
9. Click "Save Configuration"

10. Redirected to KPI Detail
11. See formula result immediately

MODAL STRUCTURE:
┌─────────────────────────────────────┐
│ [Manual] [Formula]                  │
│                                     │
│ ╔═══════════════════════════════╗  │
│ ║ 🎯 RESULT: 1,250,000.00 CHF  ║  │ ← LINE 50!
│ ║ ✓ Auto-updates                ║  │
│ ╚═══════════════════════════════╝  │
│                                     │
│ Selected (2):                       │
│ • ERP Costs → 1M CHF [×]           │
│ • Licence → 250k CHF [×]           │
│                                     │
│ [+ Add KPI] ← click shows search   │
│                                     │
│ Mode: (●)Simple ( )Advanced        │
│ IF Simple: Operation [SUM ▼]       │
│ IF Advanced: Python [______]       │
│                                     │
│ [? Help] ← collapsed by default    │
│                                     │
│ [Cancel] [Save Configuration]      │
└─────────────────────────────────────┘

Lines: ~400 (down from 918!)
```

### Step 3.3: View Formula KPI Detail
**Page:** `/kpi/<id>/value-type/<vt_id>`

```
User Journey:
1. See large formula result card:
   ┌──────────────────────────────────┐
   │ 📐 FORMULA (SUM)                │
   │                                  │
   │      1,250,000.00 CHF           │  ← BIG!
   │                                  │
   │ ✓ Auto-updates automatically     │
   └──────────────────────────────────┘

2. Scroll to see source KPIs
3. Click "Edit Formula" to modify

Current State: ✅ EXCELLENT - Clear formula display
Pain Points: None (once modal fixed)
```

---

## Journey 4: CREATE KPI - Linked Type

### Step 4.1: Create KPI (Same as Journey 2.1)
```
Same steps. Link is configured in Settings later.
```

### Step 4.2: Configure Link
**Page:** `/kpis/<id>/edit` (Settings page)

```
User Journey:
1. From KPI Detail, click "Configure Link Source"
2. Redirected to Settings page
3. See "Calculation Type" section
4. Click "Switch to Linked KPI"
5. Select source organization
6. Select source KPI
7. Select value type
8. Click "Save Changes"
9. Redirected back to KPI Detail

Current State: ✅ IMPROVED - Clear calculation type status
Pain Points FIXED:
- ✅ No more confusing "OR" options
- ✅ Clear which mode is active

Remaining Pain Points: None
```

### Step 4.3: View Linked KPI Detail
**Page:** `/kpi/<id>/value-type/<vt_id>`

```
User Journey:
1. See large linked value card:
   ┌──────────────────────────────────┐
   │ 🔗 LINKED KPI                   │
   │                                  │
   │      1,250,000.00 CHF           │  ← BIG!
   │                                  │
   │ ✓ Synced from source            │
   └──────────────────────────────────┘

2. See link configuration details
3. Click "Configure Link Source" to change

Current State: ✅ EXCELLENT - Clear linked display
Pain Points: None identified
```

---

## Journey 5: WORKSPACE GRID - Overview

### Step 5.1: View All KPIs
**Page:** `/workspace` (Main grid)

```
🟡 CURRENT ISSUE:

User Journey:
1. See grid of all KPIs
2. ❌ Can't tell which are manual/linked/formula
3. Have to click into each to see calculation type
4. Confusing at a glance

---

✅ TARGET EXPERIENCE:

User Journey (WITH BADGES):
1. See grid with calc type badges:

   ┌──────────────┬──────────────┐
   │ ERP Costs    │ Licensing    │
   │ 1,000,000 €  │ 250,000 € 🔗│ ← Linked badge
   └──────────────┴──────────────┘

   ┌──────────────┬──────────────┐
   │ Total Cost 📐│ Impact       │
   │ 1,250,000 € │ ★★★ High    │
   └──────────────┴──────────────┘
         ↑
    Formula badge

2. Instantly know which KPIs are:
   - (no badge) = Manual entry
   - 🔗 = Linked from another KPI
   - 📐 = Formula calculated

FIX NEEDED:
Add small badges to KPI cells in workspace grid
```

---

## Journey 6: EDITING EXISTING KPIs

### Step 6.1: Change Calculation Type
**Page:** `/kpis/<id>/edit` (Settings)

```
User Journey:
1. Manual KPI:
   - Shows "Switch to Formula" button
   - Shows "Switch to Linked KPI" button
   - Clear what current mode is

2. Formula KPI:
   - Shows "Edit Formula" button
   - Formula details visible
   - Can't accidentally break it

3. Linked KPI:
   - Shows link configuration
   - "Switch to Manual" button
   - "Switch to Formula" button

Current State: ✅ EXCELLENT - Clear mode switching
Pain Points: None identified
```

---

## Journey 7: CHARTS & HISTORY

### Step 7.1: View Historical Trend
**Page:** KPI Detail page (bottom section)

```
User Journey:
1. Manual KPI:
   ✅ Shows historical chart
   ✅ Shows contributions table
   ✅ Shows consensus info cards

2. Formula KPI:
   ✅ NO chart (doesn't make sense)
   ✅ NO contributions (auto-calculated)
   ✅ Shows source KPIs instead

3. Linked KPI:
   ✅ NO chart (pulled from source)
   ✅ NO contributions (read-only)
   ✅ Shows link info instead

Current State: ✅ EXCELLENT - Context-aware display
Pain Points: None identified
```

---

## Journey 8: SNAPSHOT PIVOT ANALYSIS & CHARTING (v1.28.0)

### Step 8.1: Access Pivot Analysis
**Page:** `/workspace/snapshots/pivot`
**Entry:** Navigate to Workspace → "Snapshot Analysis"

```
User Journey:
1. Click "Snapshot Analysis" from main navigation
2. Land on pivot table view
3. See filters at top:
   - View Type (Monthly/Quarterly/Yearly)
   - Space dropdown
   - Challenge dropdown (smart: updates based on space)
   - Value Type dropdown
   - Show Targets toggle
   - Time Range (Simple or Custom Dates)

4. Apply filters to narrow down KPIs

Current State: ✅ EXCELLENT - Comprehensive filtering
Pain Points: None identified
Visual: Clean filter cards with gradient headers
```

### Step 8.2: Apply Filters
**Page:** Same pivot page

```
User Journey:
1. Select Space → Challenge dropdown updates automatically
   Shows: "Challenge (5 in this space)"

2. Select Challenge → Space auto-selects

3. Toggle "Show Targets" → Apply
   - Table shows new TARGET column
   - Displays target value, date, type badge (↑↓±), tolerance %

4. Choose date range:
   - Simple mode: year range + period toggles
   - Custom mode: month/year pickers for precise range

5. Click "Apply Filters" → Table refreshes

Current State: ✅ EXCELLENT - Smart bidirectional filtering
Pain Points: None identified
Note: Private spaces hidden unless user is owner
```

### Step 8.3: Build Chart with Quick Add
**Page:** Chart Builder section (below table)

```
User Journey:
1. See "Quick Add KPIs" search box
2. Type "revenue" → Instant results appear:
   ┌────────────────────────────────┐
   │ Revenue 🎯↑         Selected   │
   │ Revenue Growth 🎯↑             │
   └────────────────────────────────┘

3. Click result → Auto-checks checkbox
   - Toast notification: "Added Revenue to chart"
   - Search box clears

4. Alternative: Check boxes directly in table above
   - Both methods work together

5. Selected KPIs appear with color pickers:
   ┌────────────────────────────────┐
   │ ✓ Revenue [🎨 #007bff]        │
   │ ✓ Operating Costs [🎨 #28a745]│
   └────────────────────────────────┘

Current State: ✅ EXCELLENT - Two selection methods
Pain Points: None identified
Note: Search respects current filters (only searches visible KPIs)
```

### Step 8.4: View Chart with Targets
**Page:** Same page, chart renders below

```
User Journey:
1. Select chart type: Line or Bar
2. Click "Update Chart" → Chart appears

3. Chart shows:
   - KPI lines in selected colors
   - IF Show Targets enabled:
     • ↑ Maximize: Green zone ABOVE target line
     • ↓ Minimize: Green zone BELOW target line
     • ± Exact: Colored tolerance band
   - Legend shows target type (↑ At or Above, etc.)

4. Visual zones make targets instantly clear:
   ┌────────────────────────────────┐
   │        (green shaded)          │ ← Good zone
   │ ........target line........... │ ← Target
   │        (unshaded)              │ ← Below target
   └────────────────────────────────┘

Current State: ✅ EXCELLENT - Visual target zones
Pain Points: None identified
```

### Step 8.5: Save Chart for Later
**Page:** Click "Save This Chart" button below chart

```
User Journey:
1. Click "Save This Chart" → Modal opens
2. Enter chart name (required)
3. Add description (optional)
4. Toggle "Make public" (share with org or keep private)
5. Click "Save Chart"
   → Toast: "Chart saved successfully!"

6. Chart saved with:
   - All selected KPIs + colors
   - All filters (space, challenge, value type, date range)
   - Chart type (line/bar)
   - View type (monthly/quarterly/yearly)

Current State: ✅ EXCELLENT - Saves everything
Pain Points: None identified
```

### Step 8.6: Load Saved Chart
**Page:** Top of page, "Load Saved Chart" section

```
User Journey:
1. Click in search box → See all charts instantly
2. Type to filter (e.g., "revenue")
3. Results show:
   ┌────────────────────────────────┐
   │ Q1 Revenue Analysis            │
   │ By: You | 3 KPIs | Private     │
   └────────────────────────────────┘

4. Click chart → Everything loads:
   - Filters applied
   - KPIs selected with colors
   - Chart rendered
   - Ready to view/modify

Current State: ✅ EXCELLENT - Instant search + load
Pain Points: None identified
```

### Step 8.7: Export to Excel
**Page:** Click "Export Excel" button (top right)

```
User Journey:
1. Click "Export Excel" → Download starts
2. Excel file includes:
   - Columns: Org, Space, Challenge, Initiative, System, KPI, Value Type
   - Target columns: Target Value, Date, Direction, Tolerance %
   - Period columns: All filtered periods with values
   - Respects all active filters

3. Use in Excel/BI tools for further analysis

Current State: ✅ EXCELLENT - Complete hierarchy + targets
Pain Points: None identified
```

---

## 🎯 SUMMARY: PAIN POINTS BY SEVERITY

### 🔴 CRITICAL (Must fix immediately):
1. **Calculation Modal** - Result not visible, 918 lines too long
   - Fix: Complete modal rewrite (~400 lines, result at top)

### 🟡 IMPORTANT (Should fix soon):
2. **Workspace Grid** - Can't identify calc types at a glance
   - Fix: Add small badges (🔗 📐)

3. **Governance Body Creation** - No context when redirected
   - Fix: Add "Why am I here?" alert message

### 🟢 MINOR (Nice to have):
- All other areas are good!

---

## ✅ WHAT'S WORKING WELL:

1. **KPI Detail Pages** - Context-aware, prominent values
2. **Settings Page** - Clear calculation type status
3. **Form Preservation** - No data loss on errors
4. **Value Type Creation** - Simple, no confusion
5. **Hierarchical Structure** - Clear organization

---

## 🚀 IMPLEMENTATION PRIORITY:

1. **NOW:** Fix calculation modal (biggest frustration)
2. **NEXT:** Add governance body context message
3. **THEN:** Add workspace grid badges
4. **TEST:** Complete flow for all three calc types
5. **DOCUMENT:** Update user guide with new UX

---

## 📊 SUCCESS METRICS:

**How to measure if UX is simple:**
- [ ] Users can create formula KPI in < 2 minutes
- [ ] No confused support questions about calc types
- [ ] Form validation errors don't lose data
- [ ] Workspace grid shows calc types at a glance
- [ ] Modal result visible without scrolling
- [ ] Users say "This is easy!" not "Where do I click?"

---

## 🔄 CONTINUOUS IMPROVEMENT:

**This document should be updated:**
- After each major UX change
- When new features added
- When user feedback received
- Before each release

**Next review:** After v1.19.0 release

---

*Remember: THE SIMPLEST USER EXPERIENCE POSSIBLE*
