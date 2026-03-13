# CISK Navigator v1.14 - User Guide

**New Features Guide**: Governance Bodies, KPI Archiving & Modern Workspace UI

---

## 🏛️ Governance Bodies

### What are Governance Bodies?

Governance Bodies represent the committees, boards, teams, or organizational units that oversee and manage specific KPIs. Examples:
- **Technical Committee** - Oversees IT and technology KPIs
- **Finance Board** - Manages financial KPIs
- **Executive Team** - Monitors strategic KPIs
- **Operations Team** - Tracks operational metrics

### Key Features

- **Visual Identity**: Each body has a name, abbreviation, and color for easy recognition
- **Many-to-Many**: KPIs can belong to multiple governance bodies
- **Filtering**: Filter workspace view by governance body
- **Default Body**: Every organization has a "General" body (can be renamed but not deleted)

### How to Manage Governance Bodies

#### Creating a Governance Body

1. Navigate to **Administration**
2. Click **"Manage Governance Bodies"**
3. Click **"Create Governance Body"**
4. Fill in details:
   - **Name**: Full name (e.g., "Technical Committee")
   - **Abbreviation**: Short code (e.g., "TECH")
   - **Description**: Optional details about the body's role
   - **Color**: Choose a color for visual identification
   - **Active**: Toggle to enable/disable
5. Click **"Create Governance Body"**

#### Editing a Governance Body

1. Go to **Administration** → **Governance Bodies**
2. Click **"Edit"** on the body you want to modify
3. Update any fields (name, abbreviation, description, color, status)
4. Click **"Save Changes"**

**Note**: The default "General" body can be renamed but cannot be deleted.

#### Reordering Governance Bodies

1. Go to **Administration** → **Governance Bodies**
2. Drag governance bodies using the **⋮⋮** handle
3. Order is saved automatically

#### Deleting a Governance Body

1. Go to **Administration** → **Governance Bodies**
2. Click **"Delete"** on the body (not available for default body)
3. Confirm deletion
4. KPIs linked to this body are NOT deleted - they remain linked to other governance bodies

### Assigning Governance Bodies to KPIs

#### When Creating a KPI

1. Navigate to the system where you want to create a KPI
2. Click **"+ KPI"**
3. Fill in KPI details
4. In **"Governance Bodies"** section:
   - At least one governance body must be selected
   - Default "General" body is pre-checked
   - Check additional bodies as needed
5. Click **"Create KPI"**

#### When Editing a KPI

1. Edit any KPI
2. Scroll to **"Governance Bodies"** section
3. Check/uncheck governance bodies
4. **At least one must remain checked**
5. Click **"Save Changes"**

### Filtering Workspace by Governance Body

#### Using Governance Body Filters

1. Open **Workspace**
2. In the filter toolbar, you'll see pill-shaped buttons for each governance body
3. Click a governance body pill to toggle filtering:
   - **Blue (Active)**: Show KPIs from this body
   - **Gray (Inactive)**: Hide KPIs from this body
4. Multiple bodies can be active simultaneously
5. **Smart Default**: All bodies are selected by default
6. **Empty Selection**: Unchecking all bodies hides all KPIs

#### Understanding the Badges

In the workspace, each KPI row displays colored badges showing which governance bodies oversee it:

```
📊 Customer Satisfaction  [GEN] [TECH] [EXEC]
```

- **[GEN]** = General governance body
- **[TECH]** = Technical Committee
- **[EXEC]** = Executive Team

Hover over a badge to see the full name of the governance body.

---

## 🗄️ KPI Archiving

### What is KPI Archiving?

Archiving allows you to preserve KPIs that are no longer actively tracked without deleting their historical data. Archived KPIs:
- Hide from workspace by default
- Become read-only (no new contributions)
- Preserve all historical data
- Can be restored anytime

### When to Archive a KPI

Archive KPIs when:
- The metric is no longer relevant to current strategy
- You've replaced it with a better metric
- The project/initiative has ended
- You want to declutter workspace but preserve history

### How to Archive a KPI

1. Navigate to **Administration** → **Spaces** (or directly edit KPI)
2. Click **"Edit"** on the KPI you want to archive
3. Scroll to bottom of the page
4. Click **"Archive KPI"** button
5. Confirm in the dialog
6. KPI is now archived

**What happens:**
- KPI disappears from workspace (unless "Show Archived" is enabled)
- Archive badge appears on KPI row
- Audit trail records who archived and when
- All historical data remains intact

### Viewing Archived KPIs

1. Open **Workspace**
2. In the filter toolbar, check **"Show Archived KPIs"** pill
3. Archived KPIs appear grayed out with archive badge: 🗄️ Archived
4. Click on archived KPI to view historical data
5. Warning banner explains read-only status

### Unarchiving a KPI

1. Enable **"Show Archived KPIs"** in workspace
2. Edit the archived KPI
3. At top of page, you'll see archive status alert
4. Click **"Unarchive KPI"** button
5. KPI becomes active again

**Result**: KPI reappears in workspace and accepts new contributions.

### Archive vs. Delete

| Feature | Archive | Delete |
|---------|---------|--------|
| Preserves Data | ✅ Yes | ❌ No |
| Reversible | ✅ Yes | ❌ No |
| Shows in Workspace | ✅ Optional | ❌ Never |
| Can Add Data | ❌ No | ❌ No |
| Use Case | Temporary removal | Permanent removal |

**Recommendation**: Always archive first. Only delete if you're certain you'll never need the data.

---

## 🎨 Modern Workspace UI (v1.14)

### What's New

The workspace interface has been completely modernized with:
- True dark mode theme
- Compact modern toolbar
- Level visibility controls
- Enhanced visual hierarchy
- Interactive filter pills

### True Dark Mode

**Automatic Activation**: Dark mode activates when you enable it in your profile settings.

**Features**:
- Deep black background (#0a0a0a) for reduced eye strain
- High contrast text for readability
- Level-specific colors for visual distinction
- Smooth hover effects and transitions

**Dark Mode Colors**:
- **Spaces**: Dark blue tint
- **Challenges**: Dark gray
- **Initiatives**: Medium gray
- **Systems**: Dark blue-gray
- **KPIs**: Dark yellow-gray

### Level Visibility Controls

**Toggle Display of Hierarchy Levels**:

In the filter toolbar, you'll see level toggle pills:
```
👁️ Show Levels: [🏢 Spaces] [🎯 Challenges] [💡 Initiatives] [⚙️ Systems] [📊 KPIs]
```

**How to Use**:
1. Click any level pill to toggle visibility for that hierarchy level
2. **Blue pill**: Level is visible in the tree
3. **Gray pill**: Level is hidden from the tree
4. Changes apply **instantly** (no page reload required)
5. Hidden levels are completely removed from view - children collapse up to visible parent

**On Page Load**:
- All levels are enabled (blue) by default
- Tree auto-expands to show all visible levels
- You see the complete hierarchy structure

**Examples**:
- **Hide Systems**: Click "Systems" pill (turns gray) → Systems disappear, KPIs appear directly under Initiatives
- **Show Only Strategic Levels**: Click Systems and KPIs (turn gray) → See only Spaces, Challenges, Initiatives with rollup values
- **Show Only Operational Data**: Click Spaces, Challenges, Initiatives (turn gray) → See only Systems and KPIs in flat list
- **Focus on Execution**: Hide Challenges → See direct path from Spaces to Initiatives to Systems

**Important Notes**:
- Hiding a level doesn't delete data - just removes it from view
- You can toggle levels on/off as often as needed
- Works with other filters (governance bodies, archive)
- Expand/Collapse buttons respect level visibility settings

### Visual Hierarchy

**Icons**: Each level has a unique icon:
- 🏢 **Spaces**
- 🎯 **Challenges**
- 💡 **Initiatives**
- ⚙️ **Systems**
- 📊 **KPIs**

**Color Borders**: 4px left border in distinct color per level

**Rollup Indicator**: Aggregated values show "Σ" symbol

### Interactive Filter Pills

**Governance Body Filters**:
- Click pill to toggle (no checkboxes needed)
- Active pills turn blue
- Multiple selections supported

**Archive Filter**:
- Single toggle for "Show Archived KPIs"
- Blue when active, gray when inactive

**Clear All**: Click "Clear All" button to reset all filters (except level visibility)

### Quick Stats Bar

Below the toolbar, see real-time stats:
```
📊 Viewing: 2 Spaces • 5 Challenges • 12 Initiatives
Filters: All Governance Bodies
```

### Sticky Elements

**Sticky Headers**: Column headers stay visible when scrolling vertically

**Sticky First Column**: Structure column stays visible when scrolling horizontally

**Result**: Always know which row and column you're viewing

### Expand/Collapse Enhancements

**Modern Icons**:
- ▶ Collapsed (click to expand)
- ▼ Expanded (click to collapse)
- Rounded background on hover

**Bulk Operations**:
- **Expand All**: Click button in toolbar
- **Collapse All**: Click button in toolbar

---

## 💡 Tips & Best Practices

### Governance Bodies

1. **Create Meaningful Bodies**: Use bodies that match your actual organizational structure
2. **Color Code**: Choose distinct colors for easy recognition
3. **Use Abbreviations**: Keep abbreviations short (3-4 characters) for better display
4. **Strategic Filtering**: Filter by executive team bodies for board meetings
5. **Multi-Assignment**: Assign critical KPIs to multiple bodies for cross-functional visibility

### KPI Archiving

1. **Archive, Don't Delete**: Preserve history by archiving instead of deleting
2. **Regular Cleanup**: Review KPIs quarterly and archive inactive ones
3. **Document Reasons**: Use KPI description to explain why it was archived
4. **Easy Restore**: Don't hesitate to archive - you can always unarchive later
5. **Historical Analysis**: Use "Show Archived" to include old KPIs in historical analysis

### Workspace UI

1. **Dark Mode**: Enable in profile for reduced eye strain during long sessions
2. **Focus on Levels**: Hide unnecessary hierarchy levels for cleaner view
3. **Strategic View**: For executive meetings, hide KPIs and show only rollups
4. **Tactical View**: For team meetings, hide upper levels and focus on systems/KPIs
5. **Filter Combinations**: Combine governance body + level filters for precise views
6. **Keyboard Navigation**: Use Tab to navigate, Enter to toggle filters

---

## 🔧 Permissions

### Governance Bodies Permission

**Permission**: `can_manage_governance_bodies`

**Default**: True for all users

**What it controls**:
- Create governance bodies
- Edit governance bodies
- Delete governance bodies (except default)
- Reorder governance bodies

**Viewing**: All users can view governance bodies and filter by them

### KPI Archive Permission

**Permission**: `can_manage_kpis`

**What it controls**:
- Archive KPIs
- Unarchive KPIs
- Edit KPIs (including archive status)

**Viewing**: All users can view archived KPIs when filter is enabled

---

## 📚 Related Documentation

- [Full Changelog](CHANGELOG.md)
- [Architecture Guide](ARCHITECTURE.md)
- [Permissions Guide](USER_GUIDE_PERMISSIONS.md)
- [Previous Version Guide (v1.11)](USER_GUIDE_V1.11.md)

---

## ❓ FAQ

**Q: Can I delete the "General" governance body?**
A: No, but you can rename it to match your organization's terminology.

**Q: What happens to KPIs when I delete a governance body?**
A: KPIs are NOT deleted. They remain linked to their other governance bodies.

**Q: Can archived KPIs be edited?**
A: You can edit KPI metadata (name, description) but cannot add new contributions.

**Q: Do archived KPIs count in rollups?**
A: Yes, archived KPIs still contribute to rollup calculations unless you hide them.

**Q: Can I export archived KPIs?**
A: Yes, enable "Show Archived KPIs" before exporting to include them.

**Q: Will hiding a level affect data?**
A: No, hiding levels is purely visual. All data and rollups remain intact.

**Q: Can I have KPIs with no governance body?**
A: No, every KPI must belong to at least one governance body.

**Q: What's the "Σ" symbol in cells?**
A: It indicates a rolled-up (aggregated) value from child entities.

---

*Last Updated: March 8, 2026*
*Version: 1.14.0*
