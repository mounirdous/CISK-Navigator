# UX Audit: Complete Data Entry Journey

## Audit Date: 2026-03-12

### Pages to Review:

1. **Value Type Creation** - `create_value_type.html`
   - [ ] Check if any calculation type mentioned (shouldn't be)

2. **Value Type Editing** - `edit_value_type.html`
   - [ ] Check if any calculation type mentioned (shouldn't be)

3. **KPI Creation** - `create_kpi.html`
   - [ ] Check for calculation type options
   - [ ] Should only mention Manual by default

4. **KPI Editing/Settings** - `edit_kpi.html`
   - [x] FIXED: Redesigned to show current calculation type clearly
   - [x] Manual shows: options to switch to Formula or Linked
   - [x] Formula shows: edit button, no confusing "OR" options
   - [x] Linked shows: configuration fields, options to switch

5. **KPI Detail Page** - `kpi_cell_detail.html`
   - [x] FIXED: Context-aware display based on calculation_type
   - [x] Large value display for all types
   - [x] Hidden irrelevant sections
   - [x] Smart action buttons

6. **Calculation Config Modal** - `_calculation_config_modal.html`
   - [ ] ISSUE: Too long, requires scrolling to see result
   - [ ] ISSUE: Result not visible when opening
   - [ ] FIX: Move result/preview to top
   - [ ] FIX: Make formula section more compact
   - [ ] FIX: Reduce help documentation size

7. **Workspace Grid** - `index.html`
   - [ ] Check if any calculation type indicators needed

8. **Dashboard** - Dashboard page
   - [ ] Check if any changes needed

## Critical Issues Found:

### 1. Calculation Modal UX (HIGH PRIORITY)
- **Problem**: User has to scroll to see formula result
- **Impact**: Poor user experience, can't see what they're building
- **Solution**: Move Live Preview to top, make compact

### 2. Settings Page Confusion (FIXED)
- **Problem**: "OR: Linked Value Source" appeared even when Formula active
- **Impact**: User confused about which mode is active
- **Solution**: Complete redesign - show current mode prominently, hide inactive options

### 3. Modal Help Documentation (MEDIUM PRIORITY)
- **Problem**: Expandable help takes up too much space
- **Impact**: Pushes important content below fold
- **Solution**: Make help collapsible by default, show only when needed

## Action Plan:

1. Fix calculation modal - move preview to top
2. Simplify formula builder - make more compact
3. Audit all remaining pages
4. Test complete user journey
5. Update documentation
