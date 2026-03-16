"""
Beta Feature Prototypes
------------------------
Experimental features and UI prototypes for testing.

Beta access is opt-in via /beta landing page.
"""

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_required

bp = Blueprint("beta", __name__, url_prefix="/beta")


def organization_required(f):
    """Decorator to require organization context"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if session.get("organization_id") is None:
            flash("Please log in to an organization", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


def _filters_match(current, preset):
    """Helper to compare current filters with preset filters"""

    # Normalize both to have consistent format
    def normalize_value(val):
        if val is None:
            return None
        if isinstance(val, list):
            if len(val) == 0:
                return None
            if len(val) == 1:
                return str(val[0])
            # Multiple values - return as sorted list of strings
            return sorted([str(v) for v in val])
        return str(val)

    # Remove skip_default from comparison (it's a control parameter, not a filter)
    current_clean = {k: v for k, v in current.items() if k != "skip_default"}
    preset_clean = {k: v for k, v in preset.items() if k != "skip_default"}

    # Get all keys from both
    all_keys = set(current_clean.keys()) | set(preset_clean.keys())

    for key in all_keys:
        current_norm = normalize_value(current_clean.get(key))
        preset_norm = normalize_value(preset_clean.get(key))

        # Both None/missing - match
        if current_norm is None and preset_norm is None:
            continue

        # One missing - no match
        if current_norm is None or preset_norm is None:
            return False

        # Compare (both are now either strings or sorted lists)
        if current_norm != preset_norm:
            return False

    return True


def beta_required(f):
    """Decorator to restrict access to beta testers only"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.models import SystemSetting

        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        # Check if beta is enabled system-wide
        if not SystemSetting.is_beta_enabled():
            flash("Beta testing program is currently disabled.", "warning")
            return redirect(url_for("workspace.dashboard"))

        # Allow ONLY beta testers (not super admins)
        if current_user.beta_tester:
            return f(*args, **kwargs)

        # Deny access - redirect to main dashboard
        flash(
            "Beta features are not enabled for your account. Contact your administrator to request beta access.",
            "warning",
        )
        return redirect(url_for("workspace.dashboard"))

    return decorated_function


@bp.route("/")
@login_required
@beta_required
def index():
    """Beta testing program landing page with disclaimers and feature links"""
    return render_template("beta/index.html", page_title="Beta Testing Program", is_prototype=True)
