"""
Beta Feature Prototypes
------------------------
Experimental features and UI prototypes for testing.

Beta access is opt-in via /beta landing page.
"""

import base64
from datetime import date
from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf
from sqlalchemy import or_

from app.extensions import db
from app.forms import ContributionForm
from app.models import (
    KPI,
    CellComment,
    Challenge,
    ChallengeInitiativeLink,
    Contribution,
    EntityTypeDefault,
    GovernanceBody,
    Initiative,
    InitiativeSystemLink,
    KPISnapshot,
    KPIValueTypeConfig,
    Organization,
    RollupSnapshot,
    SavedChart,
    Space,
    System,
    SystemAnnouncement,
    User,
    UserAnnouncementAcknowledgment,
    UserFilterPreset,
    UserOrganizationMembership,
    ValueType,
)
from app.services import AggregationService, ConsensusService, ExcelExportService
from app.services.comment_service import CommentService
from app.services.snapshot_pivot_service import SnapshotPivotService
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


def beta_required(f):
    """Decorator to restrict access to beta testers and super admins"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

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


@bp.route("/workspace")
@login_required
@organization_required
@beta_required
def workspace():
    """Beta workspace - redirects to regular workspace for now (full copy coming)"""
    # Temporary: Just use the regular workspace
    # Template is already copied to beta/workspace.html
    return redirect(url_for("workspace.index"))
