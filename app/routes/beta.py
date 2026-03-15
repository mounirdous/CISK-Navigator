"""
Beta Feature Prototypes
------------------------
Experimental features and UI prototypes for testing.

Auto-redirect: Users with mobile_beta_tester=True automatically see beta routes.
"""

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_required

from app.models import Organization, Space, ValueType

bp = Blueprint("beta", __name__, url_prefix="/beta")


def beta_required(f):
    """Decorator to restrict access to beta testers"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        # Allow super admins and beta testers
        if current_user.is_super_admin or current_user.beta_tester:
            return f(*args, **kwargs)

        # Deny access
        flash("Beta features are not enabled for your account. Contact your administrator.", "warning")
        return redirect(url_for("workspace.dashboard"))

    return decorated_function


@bp.route("/")
@login_required
@beta_required
def index():
    """Beta landing page"""
    return render_template("beta/index.html", page_title="Beta Testing", is_prototype=True)


@bp.route("/dashboard")
@login_required
@beta_required
def dashboard():
    """Beta dashboard prototype"""
    # TODO: Implement dashboard data logic
    return render_template(
        "beta/dashboard.html",
        page_title="Dashboard (Beta)",
        org_name=session.get("organization_name", "CISK Navigator"),
        stats={"spaces": 0, "kpis": 0},
        recent_activities=[],
        is_prototype=True,
    )


@bp.route("/workspace")
@login_required
@beta_required
def workspace():
    """Beta workspace prototype"""
    org_id = session.get("organization_id")

    if not org_id:
        flash("Please select an organization first.", "warning")
        return redirect(url_for("auth.login"))

    # Get workspace data (same as desktop)
    organization = Organization.query.get_or_404(org_id)
    spaces = Space.query.filter_by(organization_id=org_id, is_deleted=False).order_by(Space.sort_order).all()
    value_types = (
        ValueType.query.filter_by(organization_id=org_id, is_deleted=False).order_by(ValueType.sort_order).all()
    )

    return render_template(
        "beta/workspace_cards.html",
        page_title="Workspace (Beta)",
        organization=organization,
        org_name=organization.name,
        org_id=org_id,
        spaces=spaces,
        value_types=value_types,
        is_prototype=True,
    )
