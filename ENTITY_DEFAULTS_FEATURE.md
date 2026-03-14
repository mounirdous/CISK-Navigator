# Entity Type Defaults - Branding & White-Labeling System

**Version:** v1.30.0
**Date:** 2026-03-14
**Status:** ✅ Production Ready - Fully Deployed

## Overview

Organization admins can now configure default colors, icons, and custom logos for all entity types (Organization, Space, Challenge, Initiative, System, KPI). This enables:
- **White-labeling**: Customize platform appearance without code changes
- **Brand consistency**: Apply your brand colors and logos throughout the UI
- **Professional look**: Make the platform feel like your own product
- **Custom logos**: Upload and display custom logos for each entity type across all pages
- **Organization branding**: Each organization can have its own custom branding

---

## ✅ What's Implemented

### 1. Database & Model
- **Table**: `entity_type_defaults`
  - Stores color (hex), icon (emoji/Greek letter), display name, description
  - **Logo storage**: Binary data (`default_logo_data`) + MIME type (`default_logo_mime_type`)
  - One row per organization per entity type
  - Tracks who updated and when
- **Migrations**:
  - Initial table creation with logo support
  - `b22a92c1a37e_fix_entity_type_default_icons.py` - Fixed wrong default icons
- **Model**: `app/models/entity_type_default.py`
  - `EntityTypeDefault.get_defaults(organization_id, entity_type)` - get color/icon/logo
  - `EntityTypeDefault.get_all_defaults(organization_id)` - get all as dict
  - `EntityTypeDefault.ensure_defaults_exist(organization_id)` - bootstrap on first use
  - **Default icons**: Uses Greek letters and symbols (🏢, ƒ, δ, Φ, Ψ) not emoji

### 2. Organization Admin UI
- **Route**: `/organization-admin/entity-type-defaults`
- **Features**:
  - ✅ Color picker with live preview
  - ✅ Hex color text input
  - ✅ Icon selector with emoji/symbol suggestions
  - ✅ **Custom logo upload** (JPG, PNG, GIF, WebP)
  - ✅ **Logo preview** with current/uploaded logo display
  - ✅ **Logo removal** - reset to default icon
  - ✅ **Image processing** - Auto-resize to 128x128px, format conversion
  - ✅ Real-time preview of entity cards
  - ✅ Save all changes at once
- **File**: `app/templates/organization_admin/entity_type_defaults.html`
- **Production ready**: Uses Pillow (PIL) for image processing

### 3. Logo Display Across All Pages
Custom logos are displayed throughout the application:

#### Executive Dashboard (`app/routes/executive.py`)
- ✅ Top Performers section - KPI logos
- ✅ Needs Attention section - KPI logos
- ✅ All KPI listings use custom logos when available

#### Snapshot Comparison (`app/routes/workspace.py`)
- ✅ Comparison table - KPI logos next to each metric
- ✅ Pivot views - Entity type logos

#### Search Results (`app/routes/workspace.py`)
- ✅ Full search page - Logos for all entity types (Spaces, Challenges, Initiatives, Systems, KPIs)
- ✅ Live search dropdown - Real-time display of custom logos

#### Profile Page (`app/routes/auth.py`)
- ✅ Organization logos in membership list
- ✅ Shows custom organization branding

#### KPI Details & Charts
- ✅ KPI cell detail views
- ✅ Chart builders and visualizations

### 4. Live Search API Enhancement
- **Route**: `/api/search/live`
- **Returns**: JSON with logo data URLs for each result
- **Format**: `data:{mime_type};base64,{encoded_data}`
- **Client-side**: JavaScript displays logos in search dropdown
- **File**: `app/templates/base.html` (displayResults function)

### 5. Global Availability
- **Context processor** injects `entity_defaults` with logo URLs into ALL templates
- **Base64 encoding**: Logos converted to data URLs for inline display
- **Access in any template**:
  ```jinja2
  {{ entity_defaults['space']['color'] }}  → "#10b981"
  {{ entity_defaults['space']['icon'] }}   → "🏢"
  {{ entity_defaults['space']['logo'] }}   → "data:image/png;base64,..." (if uploaded)
  ```
- **Files**: Templates across the application load entity_defaults

---

## 🎨 Logo Implementation Details

### Image Processing (Production-Ready)
- **Library**: Pillow (PIL) - version 12.1.1
- **Upload formats**: JPG, PNG, GIF, WebP
- **Processing**:
  - Resize to 128x128px (maintains aspect ratio, adds padding if needed)
  - Convert to PNG for consistency
  - Store as binary data in PostgreSQL
- **Display**: Base64-encoded data URLs
- **Storage**: No file system required (works on Render's ephemeral storage)

### Logo Display Pattern
All pages follow this consistent pattern:

```jinja2
<!-- Template pattern -->
{% if entity_defaults.get('kpi') and entity_defaults['kpi']['logo'] %}
<img src="{{ entity_defaults['kpi']['logo'] }}" alt="KPI" style="width: 24px; height: 24px; object-fit: contain;">
{% else %}
<span style="font-size: 1.25rem;">{{ entity_defaults['kpi']['icon'] }}</span>
{% endif %}
```

### Route Handler Pattern
All routes that display logos follow this pattern:

```python
import base64
from app.models import EntityTypeDefault

# Load entity defaults with logos
entity_defaults_raw = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
entity_defaults = {}
for default in entity_defaults_raw:
    logo_url = None
    if default.default_logo_data and default.default_logo_mime_type:
        logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
    entity_defaults[default.entity_type] = {
        "color": default.default_color,
        "icon": default.default_icon,
        "logo": logo_url,
    }

# Pass to template
return render_template("template.html", entity_defaults=entity_defaults)
```

### JavaScript Live Search
The live search dropdown displays logos dynamically:

```javascript
// In base.html displayResults function
if (result.logo) {
    html += `<img src="${result.logo}" alt="${result.type}" style="width: 24px; height: 24px; object-fit: contain;">`;
} else if (icon.startsWith('unicode-')) {
    const symbol = icon.replace('unicode-', '');
    html += `<span style="font-size: 1.1rem;">${symbol}</span>`;
}
```

---

## 🔮 Future Enhancements

### Individual Entity Customization
Allow specific entities to override defaults:

1. **Add fields to entity models**:
   ```python
   # Space, Challenge, Initiative, System, KPI
   custom_color = db.Column(db.String(7), nullable=True)
   custom_icon = db.Column(db.String(10), nullable=True)
   custom_logo_data = db.Column(db.LargeBinary, nullable=True)
   ```

2. **Fallback chain**:
   - Entity-specific logo/color/icon (highest priority)
   - Organization-level default (current system)
   - System-wide fallback (hardcoded)

### Icon Library Support
Expand beyond emoji/symbols:
- Font Awesome icons
- Bootstrap Icons
- Custom SVG icons
- Icon color customization

### Advanced Features
- Dark mode variants for logos/colors
- Preview mode to see changes across workspace before saving
- Bulk logo upload for multiple entity types
- Logo templates/presets

---

## Testing Checklist

### Organization Admin UI
- [x] Navigate to Organization Admin → Entity Type Defaults
- [x] Click color picker, change colors
- [x] Type hex color directly
- [x] Click icon suggestions
- [x] Type custom emoji/symbol
- [x] Upload custom logo (JPG, PNG, GIF, WebP)
- [x] See logo preview after upload
- [x] Remove logo and verify reset to icon
- [x] See real-time preview update
- [x] Save changes
- [x] Refresh page, verify colors/logos persisted
- [x] Check database: `SELECT * FROM entity_type_defaults WHERE organization_id = X;`

### Logo Display Verification
- [x] Executive Dashboard - KPI logos in Top Performers/Needs Attention
- [x] Snapshot Comparison - KPI logos in comparison table
- [x] Search Results Page - Logos for all entity types
- [x] Live Search Dropdown - Real-time logo display
- [x] Profile Page - Organization logos
- [x] All pages show custom logos when configured
- [x] Fallback to icons when no logo uploaded

### Production Deployment
- [x] Pillow added to requirements.txt
- [x] Logo upload works in production (Render)
- [x] No file system storage required
- [x] Binary data stored in PostgreSQL
- [x] Base64 encoding works correctly

### Database
- [x] Run migrations: `flask db upgrade`
- [x] Check table exists: `\dt entity_type_defaults`
- [x] Verify default icons fixed (ƒ, δ, Φ, Ψ, not emoji)
- [x] Logo data stored as binary
- [x] MIME types stored correctly

---

## Technical Notes

### Performance
- **Minimal impact**: Context processor runs once per request
- **Cached by Flask**: entity_defaults loaded from DB once per request
- **No N+1 queries**: Single query gets all defaults
- **Future**: Add Redis caching if needed (unlikely)

### Maintenance
- **No code changes needed** to rebrand platform
- **Database-driven**: All config in entity_type_defaults table
- **Version controlled**: Migration tracks when feature added
- **Auditable**: `updated_by` and `updated_at` fields

### Compatibility
- **Backwards compatible**: Fallback to hardcoded defaults if table empty
- **Safe migration**: Inserts defaults automatically
- **Rollback safe**: `flask db downgrade` removes table cleanly

---

## API for Developers

### In Templates
```jinja2
{# Get color for entity type #}
{{ entity_defaults['space']['color'] }}  {# → "#10b981" #}

{# Get icon #}
{{ entity_defaults['initiative']['icon'] }}  {# → "δ" #}

{# Get logo (may be None) #}
{{ entity_defaults['kpi']['logo'] }}  {# → "data:image/png;base64,..." or None #}

{# Display with logo fallback to icon #}
{% if entity_defaults.get('kpi') and entity_defaults['kpi']['logo'] %}
<img src="{{ entity_defaults['kpi']['logo'] }}" alt="KPI" style="width: 24px; height: 24px; object-fit: contain;">
{% else %}
<span style="font-size: 1.25rem;">{{ entity_defaults['kpi']['icon'] }}</span>
{% endif %}

{# Apply color to element #}
<div style="background-color: {{ entity_defaults['challenge']['color'] }}20;">
    {{ entity_defaults['challenge']['icon'] }} Challenge Name
</div>
```

### In Python Code
```python
import base64
from app.models import EntityTypeDefault

# Get all defaults for an organization (without logos)
defaults = EntityTypeDefault.get_all_defaults(organization_id)
# {'space': {'color': '#10b981', 'icon': '🏢'}, ...}

# Get specific type defaults
space_defaults = EntityTypeDefault.get_defaults(organization_id, 'space')
# {'color': '#10b981', 'icon': '🏢'}

# Get defaults with logo data URLs (for templates)
entity_defaults_raw = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
entity_defaults = {}
for default in entity_defaults_raw:
    logo_url = None
    if default.default_logo_data and default.default_logo_mime_type:
        logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
    entity_defaults[default.entity_type] = {
        "color": default.default_color,
        "icon": default.default_icon,
        "logo": logo_url,
    }

# Ensure defaults exist (bootstrap)
EntityTypeDefault.ensure_defaults_exist(organization_id)
```

### In API Responses (JSON)
```python
# For AJAX/API endpoints that return entity data
{
    "id": 123,
    "name": "Revenue",
    "type": "kpi",
    "icon": entity_defaults.get("kpi", {}).get("icon", "Ψ"),
    "logo": entity_defaults.get("kpi", {}).get("logo"),  # Base64 data URL or None
    "color": entity_defaults.get("kpi", {}).get("color", "#06b6d4")
}
```

---

## Production Deployment Requirements

### Required Dependencies
```bash
# requirements.txt
Pillow==12.1.1  # CRITICAL - Required for logo upload/processing
```

### Environment Variables
No additional environment variables required. Logo data is stored in PostgreSQL.

### Database
- PostgreSQL with binary data support (LargeBinary columns)
- Sufficient storage for logo images (typically < 50KB each after processing)

### Server Configuration
- No file system storage required (works on Render's ephemeral file system)
- PIL/Pillow must be available in production environment
- Base64 encoding happens server-side before sending to browser

### Deployment Checklist
- [x] Add Pillow to requirements.txt
- [x] Run database migrations
- [x] Import PIL at module level (not lazy import)
- [x] Test logo upload in production
- [x] Verify logo display across all pages

## Known Limitations

1. **No individual entity customization** - Only organization-level defaults (future enhancement)
2. **No UI to preview changes** across full workspace before saving
3. **Icon limited to text/emoji** - No icon library support (Font Awesome, Bootstrap Icons)
4. **No dark mode variants** for logos/colors
5. **Fixed logo size** - 128x128px (could allow configurable sizes)

---

## Migration Path

### If you need to rollback:
```bash
flask db downgrade  # Removes entity_type_defaults table
```

### If you need to reset to defaults:
```sql
DELETE FROM entity_type_defaults;
-- Then restart Flask app, defaults will be re-inserted
```

---

## Recent Fixes & Improvements (v1.30.0 - 2026-03-14)

### Default Icons Fixed
- **Issue**: Reset to default was using wrong emoji icons
- **Fix**: Updated hardcoded defaults to use correct symbols
  - Challenge: ⚡ → ƒ (italic f)
  - Initiative: 🚀 → δ (delta)
  - System: ⚙️ → Φ (phi)
  - KPI: 📊 → Ψ (psi)
  - Space: 🎯 → 🏢 (building)
- **Migration**: `b22a92c1a37e_fix_entity_type_default_icons.py`

### Production Deployment Fixed
- **Issue**: Logo upload returned "Unexpected token '<', "<!html><"... is not valid JSON"
- **Root Cause**: Pillow missing from requirements.txt
- **Fix**: Added Pillow==12.1.1 to requirements.txt
- **Lesson**: Always sync local pip installs with requirements.txt for production

### Logo Display Comprehensive Implementation
- ✅ Executive Dashboard - Top Performers/Needs Attention
- ✅ Snapshot Comparison - Comparison table
- ✅ Full Search Results - All entity types
- ✅ Live Search Dropdown - Real-time display
- ✅ Profile Page - Organization logos
- ✅ All KPI displays across the application

## Next Steps (Future Enhancements)

1. **Individual Entity Customization**
   - Allow specific Spaces/Challenges/etc. to have custom logos
   - Implement fallback chain: entity-specific → org default → system default

2. **Icon Library Support**
   - Font Awesome icons
   - Bootstrap Icons
   - SVG icon upload

3. **Preview Mode**
   - Show mockup workspace with chosen colors/logos before saving
   - Real-time preview across different pages

4. **Bulk Operations**
   - Upload multiple logos at once
   - Export/import branding configurations
   - Logo templates/presets

5. **Advanced Features**
   - Dark mode logo variants
   - Configurable logo sizes
   - Logo position customization (left/right/top of text)

---

## Files Modified

### New Files
- `app/models/entity_type_default.py` - Model with logo support
- `app/templates/organization_admin/entity_type_defaults.html` - Organization admin UI
- `migrations/versions/b22a92c1a37e_fix_entity_type_default_icons.py` - Data migration for default icons

### Modified Files - Core Functionality
- `app/__init__.py` - Context processor (injects entity_defaults globally)
- `app/models/__init__.py` - Import EntityTypeDefault model
- `app/routes/organization_admin.py` - Entity defaults routes with logo upload
- `requirements.txt` - Added Pillow==12.1.1 for image processing

### Modified Files - Logo Display Implementation
- `app/routes/executive.py` - Executive dashboard with KPI logos
- `app/routes/workspace.py` - Multiple endpoints:
  - `compare_snapshots()` - Snapshot comparison logos
  - `search_page()` - Full search results logos
  - `live_search()` - API endpoint with logo data
  - `kpi_cell_detail()` - KPI detail view logos
  - `snapshot_pivot()` - Pivot view logos
- `app/routes/auth.py` - Profile page with organization logos

### Modified Templates
- `app/templates/executive/dashboard.html` - Top Performers/Needs Attention with logos
- `app/templates/workspace/compare_snapshots.html` - Comparison table with KPI logos
- `app/templates/workspace/search.html` - All entity type search results with logos
- `app/templates/auth/profile.html` - Organization membership with logos
- `app/templates/base.html` - Live search JavaScript with logo display logic

---

## Security Considerations

- ✅ Organization admin only (protected by `@org_admin_required`)
- ✅ CSRF protection on all forms
- ✅ Input validation:
  - Hex color pattern validation
  - Icon length limits
  - Logo file type validation (JPG, PNG, GIF, WebP only)
  - Logo size validation (max 5MB)
  - Image processing sanitization via Pillow
- ✅ No XSS risk:
  - Colors rendered as CSS hex values
  - Icons rendered as text content
  - Logos rendered as base64 data URLs (no executable code)
- ✅ Binary data storage in PostgreSQL (no file system risk)
- ✅ Audit trail (updated_by, updated_at)
- ✅ Organization isolation (each org has separate defaults)

---

## Troubleshooting

### Logo Upload Issues
1. **"Unexpected token '<', "<!html><"... is not valid JSON"**
   - Cause: Pillow missing in production
   - Fix: Ensure `Pillow==12.1.1` in requirements.txt
   - Verify: Check production logs for PIL import errors

2. **Logo not displaying**
   - Check database: `SELECT default_logo_data IS NOT NULL, default_logo_mime_type FROM entity_type_defaults WHERE organization_id = X;`
   - Verify base64 encoding in route handler
   - Check browser console for image loading errors
   - Verify `entity_defaults` passed to template

3. **Wrong default icons after reset**
   - Run migration: `flask db upgrade`
   - Check for migration `b22a92c1a37e_fix_entity_type_default_icons.py`
   - Verify hardcoded defaults in `entity_type_default.py`

### Database Issues
```sql
-- Check current defaults
SELECT entity_type, default_color, default_icon,
       LENGTH(default_logo_data) as logo_size_bytes,
       default_logo_mime_type
FROM entity_type_defaults
WHERE organization_id = 1;

-- Reset to system defaults (removes custom logos)
DELETE FROM entity_type_defaults WHERE organization_id = 1;
-- Then restart Flask, defaults will be re-inserted
```

### Performance
- Logos cached per request (loaded once per page view)
- No N+1 query issues
- Base64 encoding adds ~33% overhead but eliminates file storage
- Typical logo size: 20-50KB (after 128x128px resize)

---

**Status: Production Ready ✅**
