# CISK Navigator - Development Guidelines

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
