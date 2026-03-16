# Beta Feature Workflow

Complete guide for developing, testing, and releasing beta features in CISK Navigator.

## Overview

Beta features allow us to test new functionality with a limited user group before rolling out to everyone. The beta system uses:
- **SystemSetting.is_beta_enabled()** - Global beta program toggle
- **User.beta_tester** flag - Per-user beta access
- **User.is_super_admin** - Super admins always have beta access

---

## Phase 1: Development (Beta-Only Access)

### 1. Create the Route

**Option A: Route at root level** (recommended for features that will eventually be public)
```python
# In app/__init__.py after blueprint registrations

@app.route("/your-feature")
def your_feature():
    """Your feature description"""
    from flask import flash, redirect, render_template, session, url_for
    from flask_login import current_user
    from app.models import SystemSetting

    # Require login
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    # Beta access check
    if not SystemSetting.is_beta_enabled():
        flash("Beta testing program is currently disabled.", "warning")
        return redirect(url_for("workspace.dashboard"))

    if not (current_user.is_super_admin or current_user.beta_tester):
        flash("This feature requires beta access.", "warning")
        return redirect(url_for("workspace.dashboard"))

    org_id = session.get("organization_id")

    # Your feature logic here...

    return render_template("your_template.html", ...)
```

**Option B: Route in beta blueprint** (for features that might stay beta-only)
```python
# In app/routes/beta.py

@bp.route("/your-feature")
@login_required
@beta_required  # This decorator handles all beta checks
def your_feature():
    """Your feature description"""
    org_id = session.get("organization_id")

    # Your feature logic here...

    return render_template("beta/your_template.html", ...)
```

### 2. Create the Template

**For root-level routes:**
```
app/templates/workspace/your_feature.html  (if it's workspace-related)
app/templates/your_feature.html            (if it's standalone)
```

**For beta blueprint routes:**
```
app/templates/beta/your_feature.html
```

**Important:** Always use `base.html` as the parent template (not `base_beta.html`) so users get the normal navigation.

```html
{% extends "base.html" %}

{% block title %}Your Feature - {{ org_name }}{% endblock %}

{% block extra_css %}
<style>
    /* Your styles here */
</style>
{% endblock %}

{% block content %}
    <!-- Your content here -->
{% endblock %}
```

### 3. Add to Beta Index Page

```html
<!-- In app/templates/beta/index.html -->

<div class="feature-grid">
    <a href="{{ url_for('your_feature') }}" class="feature-card">
        <div class="feature-icon">🔧</div>
        <div class="feature-title">Your Feature Name</div>
        <div class="feature-desc">
            Brief description of what the feature does.
        </div>
        <span class="feature-badge new">New</span>
    </a>
</div>
```

### 4. Optional: Add Dashboard Alert (Beta-Only)

If you want a beta-only alert on the dashboard:

```python
# In app/routes/workspace.py - dashboard() function

# Calculate feature metric
feature_count = 0
from app.models import SystemSetting

if SystemSetting.is_beta_enabled() and (current_user.is_super_admin or current_user.beta_tester):
    # Your calculation here
    feature_count = YourModel.query.filter_by(...).count()

return render_template(
    "workspace/dashboard.html",
    # ... other context ...
    feature_count=feature_count,
)
```

```html
<!-- In app/templates/workspace/dashboard.html -->

{% if feature_count > 0 %}
<div class="row mb-3">
    <div class="col-12">
        <div class="alert alert-info d-flex justify-content-between align-items-center">
            <div>
                <i class="bi bi-info-circle me-2"></i>
                <strong>{{ feature_count }} items need attention</strong>
                <p class="mb-0 mt-1" style="font-size: 0.9rem;">Description</p>
            </div>
            <a href="{{ url_for('your_feature') }}" class="btn btn-sm btn-info">
                <i class="bi bi-arrow-right"></i> Review
            </a>
        </div>
    </div>
</div>
{% endif %}
```

### 5. Test with Beta Users

1. Enable beta system-wide:
   ```python
   flask shell
   >>> from app.models import SystemSetting
   >>> SystemSetting.set_beta_enabled(True)
   ```

2. Enable beta access for test users:
   ```python
   >>> from app.models import User
   >>> user = User.query.filter_by(email='tester@example.com').first()
   >>> user.beta_tester = True
   >>> db.session.commit()
   ```

3. Test the feature thoroughly with beta users
4. Gather feedback and iterate

---

## Phase 2: Release to Everyone

### 1. Remove Beta Checks from Route

**For root-level routes (in `app/__init__.py`):**

```python
# BEFORE (Beta)
@app.route("/your-feature")
def your_feature():
    from app.models import SystemSetting

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    # Remove these beta checks ↓
    if not SystemSetting.is_beta_enabled():
        flash("Beta testing program is currently disabled.", "warning")
        return redirect(url_for("workspace.dashboard"))

    if not (current_user.is_super_admin or current_user.beta_tester):
        flash("This feature requires beta access.", "warning")
        return redirect(url_for("workspace.dashboard"))
    # ↑ Remove until here

    # Feature logic...

# AFTER (Public)
@app.route("/your-feature")
def your_feature():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    # Feature logic immediately - no beta checks
```

**For beta blueprint routes:**
Move the entire route to the appropriate blueprint (workspace, organization_admin, etc.)

### 2. Remove Beta Checks from Dashboard Alert

```python
# BEFORE (Beta)
if SystemSetting.is_beta_enabled() and (current_user.is_super_admin or current_user.beta_tester):
    feature_count = YourModel.query.filter_by(...).count()

# AFTER (Public)
feature_count = YourModel.query.filter_by(...).count()
```

### 3. Remove from Beta Index

```html
<!-- In app/templates/beta/index.html -->

<!-- Remove the entire feature card -->
<a href="{{ url_for('your_feature') }}" class="feature-card">
    <!-- DELETE THIS -->
</a>

<!-- If no beta features remain, show empty state -->
<div style="text-align: center; padding: 3rem; color: #6c757d;">
    <i class="bi bi-lightbulb" style="font-size: 3rem; margin-bottom: 1rem;"></i>
    <h3>No Beta Features Available</h3>
    <p>Check back later for new experimental features!</p>
</div>
```

### 4. Add to Main Navigation

Add to the appropriate place in `app/templates/base.html`:

```html
<!-- Dashboards dropdown is a good location for quality/monitoring features -->
<li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" id="dashboardsDropdown" role="button" data-bs-toggle="dropdown">
        <i class="bi bi-speedometer2"></i> Dashboards
    </a>
    <ul class="dropdown-menu" aria-labelledby="dashboardsDropdown">
        <li>
            <a class="dropdown-item" href="{{ url_for('workspace.dashboard') }}">
                <i class="bi bi-house-door"></i> Overview
            </a>
        </li>
        <!-- Add your feature here -->
        <li>
            <a class="dropdown-item" href="{{ url_for('your_feature') }}">
                <i class="bi bi-your-icon"></i> Your Feature
            </a>
        </li>
        <!-- ... -->
    </ul>
</li>
```

### 5. Update Documentation

Update any relevant documentation to mention the new feature is now generally available.

---

## Example: Action Items Feature

Here's the complete journey of the Action Items feature:

### Beta Phase (March 15-16, 2026)

**Route:** `/action-items` in `app/__init__.py`
```python
@app.route("/action-items")
def action_items():
    # Beta checks
    if not SystemSetting.is_beta_enabled():
        flash("Beta testing program is currently disabled.", "warning")
        return redirect(url_for("workspace.dashboard"))

    if not (current_user.is_super_admin or current_user.beta_tester):
        flash("This feature requires beta access.", "warning")
        return redirect(url_for("workspace.dashboard"))

    # Feature logic...
```

**Dashboard alert (beta-only):**
```python
if SystemSetting.is_beta_enabled() and (current_user.is_super_admin or current_user.beta_tester):
    total_action_items = (...)
```

**Listed in:** `/beta` page as a beta feature

### Public Release (March 16, 2026)

**Changes made:**
1. ✅ Removed beta checks from route
2. ✅ Removed beta checks from dashboard calculation
3. ✅ Removed from beta index page
4. ✅ Added to Dashboards dropdown in main navigation
5. ✅ Template uses `base.html` (not beta-specific template)

**Result:** Available to all users via Dashboards > Action Items

---

## Best Practices

### ✅ DO

- **Use root-level routes** for features that will be public eventually
- **Test thoroughly** with beta users before release
- **Keep beta checks simple** - just check `is_beta_enabled()` and `beta_tester` flag
- **Use normal templates** (`base.html`) even for beta features
- **Document return_to parameters** for features that link to edit pages
- **Clean up beta references** completely when releasing to public

### ❌ DON'T

- **Don't use `/beta` prefix** for routes that will be public (use root-level routes)
- **Don't use `base_beta.html`** - it has a beta banner that confuses users
- **Don't leave beta checks** after public release
- **Don't forget to remove** from beta index page
- **Don't forget to add** to main navigation after release

---

## File Locations Reference

```
app/
├── __init__.py                              # Root-level routes (public features)
├── routes/
│   ├── beta.py                              # Beta-only routes
│   ├── workspace.py                         # Dashboard and workspace routes
│   └── organization_admin.py                # Admin routes
├── templates/
│   ├── base.html                            # Main template (USE THIS)
│   ├── beta/
│   │   ├── base_beta.html                   # Beta banner template (DON'T USE)
│   │   ├── index.html                       # Beta feature listing
│   │   └── dashboard.html                   # Beta mobile dashboard
│   ├── workspace/
│   │   ├── dashboard.html                   # Main dashboard
│   │   ├── action_items.html                # Action items (example)
│   │   └── ...
│   └── organization_admin/
│       ├── initiative_form.html             # Forms with return_to support
│       └── ...
└── models/
    └── system_setting.py                    # is_beta_enabled()
    └── user.py                              # beta_tester flag
```

---

## Return-to Pattern for Edit Pages

When a feature links to edit pages, preserve the return path:

### In the Feature Template

```html
<!-- Add return_to parameter to all edit links -->
<a href="{{ url_for('organization_admin.initiative_form',
                     initiative_id=initiative.id,
                     return_to='your_feature') }}">
    Edit
</a>
```

### In the Edit Route

```python
# After successful save
db.session.commit()
flash(f"Changes saved successfully", "success")

# Check if we should return to the feature
if request.args.get("return_to") == "your_feature":
    return redirect(url_for("your_feature"))

# Otherwise, default redirect
return redirect(url_for("workspace.index"))
```

### In the Edit Template

```html
<!-- Preserve return_to in "Edit" button -->
<a href="{{ url_for('organization_admin.initiative_form',
                     initiative_id=initiative.id,
                     edit=1,
                     return_to=request.args.get('return_to')) }}">
    Edit
</a>

<!-- Dynamic back button -->
{% if request.args.get('return_to') == 'your_feature' %}
<a href="{{ url_for('your_feature') }}">
    <i class="bi bi-arrow-left"></i> Back to Your Feature
</a>
{% else %}
<a href="{{ url_for('workspace.index') }}">
    <i class="bi bi-arrow-left"></i> Back to Workspace
</a>
{% endif %}
```

---

## Testing Checklist

### Beta Testing
- [ ] Feature accessible with beta flag enabled + beta_tester flag
- [ ] Feature blocked without beta flags
- [ ] Super admins can access regardless of beta_tester flag
- [ ] Dashboard alert only shows for beta users
- [ ] Listed in `/beta` page
- [ ] Return-to navigation works from edit pages

### Public Release
- [ ] Feature accessible to all authenticated users
- [ ] No beta checks remaining in code
- [ ] Dashboard alert shows for all users
- [ ] Removed from `/beta` page
- [ ] Added to main navigation
- [ ] Return-to navigation still works
- [ ] No console errors or warnings
- [ ] Works across different user permission levels

---

## Questions?

If you're unsure about any step, check the Action Items feature implementation as a reference:
- Route: `app/__init__.py` (search for `@app.route("/action-items")`)
- Template: `app/templates/workspace/action_items.html`
- Dashboard alert: `app/routes/workspace.py` (dashboard function)
- Navigation: `app/templates/base.html` (Dashboards dropdown)

Last Updated: March 16, 2026
