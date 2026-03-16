"""
Beta Feature Prototypes
------------------------
Experimental features and UI prototypes for testing.

Beta access is opt-in via /beta landing page.
"""

import base64
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf

from app.extensions import db
from app.models import (
    KPI,
    CellComment,
    Challenge,
    EntityTypeDefault,
    GovernanceBody,
    Initiative,
    InitiativeSystemLink,
    KPIValueTypeConfig,
    Organization,
    Space,
    System,
    SystemAnnouncement,
    ValueType,
)
from app.services.comment_service import CommentService
from app.services.snapshot_service import SnapshotService

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
    """Decorator to restrict access to beta testers and super admins"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.models import SystemSetting

        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        # Check if beta is enabled system-wide
        if not SystemSetting.is_beta_enabled():
            flash("Beta testing program is currently disabled.", "warning")
            return redirect(url_for("workspace.dashboard"))

        # Allow super admins and beta testers
        if current_user.is_super_admin or current_user.beta_tester:
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


@bp.route("/dashboard")
@login_required
@beta_required
def dashboard():
    """Beta dashboard prototype - mobile-optimized"""
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

    # Get organization logo
    org = Organization.query.get(org_id)
    org_logo = None
    if org and org.logo_data:
        org_logo = f"data:{org.logo_mime_type};base64,{base64.b64encode(org.logo_data).decode('utf-8')}"

    # Get entity type defaults (for logos in stats cards)
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

    # Get statistics
    stats = {
        "spaces": Space.query.filter_by(organization_id=org_id).count(),
        "challenges": Challenge.query.join(Space).filter(Space.organization_id == org_id).count(),
        "initiatives": Initiative.query.filter_by(organization_id=org_id).count(),
        "systems": System.query.filter_by(organization_id=org_id).count(),
        "kpis": db.session.query(KPI)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(Initiative.organization_id == org_id)
        .count(),
        "value_types": ValueType.query.filter_by(organization_id=org_id, is_active=True).count(),
        "governance_bodies": GovernanceBody.query.filter_by(organization_id=org_id, is_active=True).count(),
        "initiatives_no_consensus": Initiative.query.filter_by(
            organization_id=org_id, impact_on_challenge="no_consensus"
        ).count(),
    }

    # Check if organization needs onboarding
    is_empty_org = stats["spaces"] == 0 and stats["governance_bodies"] == 0 and stats["value_types"] == 0
    has_admin_permissions = current_user.can_manage_spaces(org_id)
    needs_onboarding = is_empty_org and has_admin_permissions

    # Get recent snapshots (last 5)
    recent_snapshots = SnapshotService.get_all_snapshots(org_id, user_id=current_user.id, limit=5)

    # Get recent comments (last 10)
    recent_comments = (
        db.session.query(CellComment)
        .join(KPIValueTypeConfig)
        .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(Initiative.organization_id == org_id)
        .order_by(CellComment.created_at.desc())
        .limit(10)
        .all()
    )

    # Get unread mentions count
    unread_mentions = CommentService.get_unread_mentions_count(current_user.id)

    # Get active announcements
    active_announcements = []
    all_announcements = SystemAnnouncement.query.filter_by(is_active=True).all()
    for ann in all_announcements:
        if ann.is_visible_for_user(current_user.id, org_id):
            if ann.is_dismissible and ann.has_been_acknowledged_by(current_user.id):
                continue
            active_announcements.append(ann)

    return render_template(
        "beta/dashboard.html",
        page_title="Dashboard (Beta)",
        org_name=org_name,
        org_logo=org_logo,
        entity_defaults=entity_defaults,
        stats=stats,
        recent_snapshots=recent_snapshots,
        recent_comments=recent_comments,
        unread_mentions=unread_mentions,
        needs_onboarding=needs_onboarding,
        active_announcements=active_announcements,
        csrf_token=generate_csrf,
        is_prototype=True,
    )
