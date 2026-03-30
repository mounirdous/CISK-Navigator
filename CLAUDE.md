# CISK Navigator - Development Guidelines

## UI ↔ Model Terminology (IMPORTANT)

The UI uses different terms than the database models:

| UI Text | DB Model | Notes |
|---|---|---|
| **Workspace** | `Organization` | "Workspaces" menu, "Switch Workspace", "Workspace Administration" |
| **CISK** | Workspace entry point | Top-left brand link → `workspace.index` |
| **Collaborate** | Actions, Decisions, Stakeholders | Menu grouping |
| **Portal System** | `System.linked_organization_id` | System linked to another CISK org |

**Rule:** Use "Workspace" in UI text, "Organization" only in code/models/DB.

## Presets System (IMPORTANT)

To add preset save/load to a new page:

1. Add feature name to `VALID_FEATURES` in `app/routes/presets_api.py`
2. Add it to the `if feature in (...)` branch for the correct model:
   - `UserFilterPreset`: workspace, action_items, decisions
   - `SavedSearch`: search
   - `SavedChart`: pivot
3. In the route, query presets: `UserFilterPreset.query.filter_by(user_id=current_user.id, organization_id=org_id, feature="my_feature")`
4. Pass to template: `presets_list=[{"id": p.id, "name": p.name, "config": p.filters} for p in presets]`
5. In template: `{% from "_preset_bar.html" import preset_bar %}` then `{{ preset_bar('my_feature', presets_list) }}`
6. Register JS callbacks in template:
   ```js
   PresetManager.setCsrf('{{ csrf_token() }}');
   PresetManager.register('my_feature', {
       getState: function() { return { /* filter state */ }; },
       applyState: function(config, _isAutoRestore) { /* apply filters */ },
       onReset: function() { /* clear all filters back to defaults */ }
   }, true); // true = auto-restore on page load
   ```
   - Without `getState`, presets save empty config!
   - Without `onReset`, the reset button does nothing!

## Semantic Versioning

This project follows [Semantic Versioning](https://semver.org/) with the format: **x.y.z**

### Version Number Rules

Given a version number **x.y.z** (e.g., 2.10.4):

- **x (Major version)** - Increase for breaking changes or major feature releases
  - When incrementing x, set y and z to 0
  - Example: 2.10.4 → 3.0.0

- **y (Minor version)** - Increase for new features or significant enhancements
  - When incrementing y, set z to 0
  - Example: 2.10.4 → 2.11.0

- **z (Patch version)** - Increase for bug fixes, small updates, and minor improvements
  - Example: 2.10.4 → 2.10.5

### What Qualifies as Each Type

**Patch (z)** - Bug fixes and small improvements:
- Bug fixes
- CSRF token fixes
- Permission fixes
- UI tweaks (adding icons, styling)
- Test fixes
- Documentation updates
- Performance improvements without behavior changes

**Minor (y)** - New features and enhancements:
- New functionality
- New permissions or access control features
- New pages or major UI components
- Database schema additions (new columns, tables)
- API additions
- New integrations

**Major (x)** - Breaking changes:
- Database migrations that require manual intervention
- API changes that break existing clients
- Removal of features
- Major architectural changes
- Changes requiring migration scripts

### When to Update Version

**Always update the version number when committing changes that will be deployed.**

Files to update:
1. `app/__init__.py` - Update `__version__` variable
2. `CHANGELOG.md` - Add entry describing the changes

### Example Changelog Entry

```markdown
## [2.10.5] - 2026-03-18

### Fixed
- Fixed CSRF token errors in entity create/edit forms
- Fixed permission check in Porter's Five Forces edit page

### Added
- Added + icon at organization level to create spaces
```
