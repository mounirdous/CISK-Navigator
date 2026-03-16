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
    """
    Beta workspace - full copy of regular workspace for responsive testing.

    Shows spaces (collapsed by default) with roll-up values visible.
    """
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

    # Check if user wants to skip auto-loading presets (e.g., after clicking "Clear All")
    skip_default = request.args.get("skip_default") == "1"

    # Check if user has a last-used filter preset and no query params (first load)
    # Skip if user explicitly cleared all filters
    if not skip_default and not request.args:
        # Check for last used preset (stored in membership)
        membership = UserOrganizationMembership.query.filter_by(user_id=current_user.id, organization_id=org_id).first()

        last_preset = None
        if membership and membership.last_workspace_preset_id:
            last_preset = UserFilterPreset.query.get(membership.last_workspace_preset_id)
            # Verify it still exists and belongs to this user/org
            if last_preset and (last_preset.user_id != current_user.id or last_preset.organization_id != org_id):
                last_preset = None
                # Clear invalid reference
                membership.last_workspace_preset_id = None
                db.session.commit()

        # If we have a valid last preset, use it
        if last_preset and last_preset.filters:
            return redirect(url_for("beta.workspace", **last_preset.filters))

    # Get space type filter (all, private, public)
    space_type_filter = request.args.get("space_type", "all")

    # Get space counts for filter pills (with privacy filtering)
    base_spaces_query = Space.query.filter_by(organization_id=org_id)
    if not current_user.is_global_admin and not current_user.is_super_admin and not current_user.is_org_admin(org_id):
        # Regular user: only count spaces they can see
        base_spaces_query = base_spaces_query.filter(
            or_(Space.is_private.is_(False), Space.created_by == current_user.id)
        )
    all_spaces_count = base_spaces_query.count()
    public_spaces_count = base_spaces_query.filter_by(is_private=False).count()
    private_spaces_count = base_spaces_query.filter_by(is_private=True).count()

    # ALWAYS show all columns - user requested removal of column hiding feature
    # Keeping parameter for backwards compatibility but always defaulting to True
    show_all_columns = True

    # Get active governance bodies for filter
    from app.models import GovernanceBody

    governance_bodies = (
        GovernanceBody.query.filter_by(organization_id=org_id, is_active=True)
        .order_by(GovernanceBody.display_order)
        .all()
    )

    # Get selected governance body IDs from query params
    selected_governance_body_ids = request.args.getlist("gb")

    # Smart default: if no governance bodies selected and some exist, select all
    # This fixes the bug where unchecking all filters still shows KPIs
    if not selected_governance_body_ids and governance_bodies:
        selected_governance_body_ids = [str(gb.id) for gb in governance_bodies]

    # Get initiative group filter
    selected_group_labels = request.args.getlist("group")

    # Get initiative impact filter
    selected_impact_levels = request.args.getlist("impact")

    # Get show_archived flag
    show_archived = request.args.get("show_archived") == "1"

    # Get all spaces for space selector filter (with privacy filtering)
    filter_spaces_query = Space.query.filter_by(organization_id=org_id)
    if not current_user.is_global_admin and not current_user.is_super_admin and not current_user.is_org_admin(org_id):
        # Regular user: only show spaces they can see
        filter_spaces_query = filter_spaces_query.filter(
            or_(Space.is_private.is_(False), Space.created_by == current_user.id)
        )
    all_spaces_for_filter = filter_spaces_query.order_by(Space.display_order, Space.name).all()

    # Get selected space IDs (new space filter)
    selected_space_ids = request.args.getlist("space")

    # Get spaces based on filters
    spaces_query = Space.query.filter_by(organization_id=org_id)

    # SECURITY: Filter private spaces based on user permissions
    # Private spaces are only visible to:
    # 1. The creator/owner
    # 2. Global admins
    # 3. Organization admins
    # 4. Super admins
    if not current_user.is_global_admin and not current_user.is_super_admin and not current_user.is_org_admin(org_id):
        # Regular user: only show public spaces OR private spaces they created
        spaces_query = spaces_query.filter(or_(Space.is_private.is_(False), Space.created_by == current_user.id))

    # Apply space type filter (all, private, public)
    if space_type_filter == "private":
        spaces_query = spaces_query.filter_by(is_private=True)
    elif space_type_filter == "public":
        spaces_query = spaces_query.filter_by(is_private=False)

    # Apply individual space selection filter
    if selected_space_ids:
        space_ids_int = [int(sid) for sid in selected_space_ids]
        spaces_query = spaces_query.filter(Space.id.in_(space_ids_int))

    spaces = spaces_query.order_by(Space.display_order, Space.name).all()

    # Filter initiatives by group and impact in Python (cleaner than template logic)
    if selected_group_labels or selected_impact_levels:
        for space in spaces:
            for challenge in space.challenges:
                # Filter initiative_links
                challenge.initiative_links = [
                    link
                    for link in challenge.initiative_links
                    if (
                        # Group filter: if no group labels selected OR initiative matches selected groups or is ungrouped
                        (
                            not selected_group_labels
                            or (not link.initiative.group_label or link.initiative.group_label in selected_group_labels)
                        )
                        and
                        # Impact filter: if no impact levels selected OR initiative matches selected impact levels
                        (not selected_impact_levels or (link.initiative.impact_on_challenge in selected_impact_levels))
                    )
                ]

    # Get space IDs for filtering value types
    space_ids = [space.id for space in spaces]

    # Get active value types that have displayable rollup values in the FILTERED spaces
    # Check for value types with actual contribution data (what creates rollups)
    from app.models import Contribution, KPIGovernanceBodyLink

    if space_ids:
        # Build query to find value types that have data in filtered spaces
        # This includes both manual KPIs (with contributions) and formula KPIs (calculated values)

        # Query 1: Value types with contributions (manual KPIs)
        value_types_with_contributions = (
            db.session.query(ValueType.id)
            .join(KPIValueTypeConfig, ValueType.id == KPIValueTypeConfig.value_type_id)
            .join(Contribution, KPIValueTypeConfig.id == Contribution.kpi_value_type_config_id)
            .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .join(ChallengeInitiativeLink, Initiative.id == ChallengeInitiativeLink.initiative_id)
            .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
            .filter(
                Challenge.space_id.in_(space_ids), ValueType.organization_id == org_id, ValueType.is_active.is_(True)
            )
        )

        # Apply filters to contributions query
        if selected_governance_body_ids:
            gb_ids_int = [int(gb_id) for gb_id in selected_governance_body_ids]
            value_types_with_contributions = value_types_with_contributions.join(
                KPIGovernanceBodyLink, KPI.id == KPIGovernanceBodyLink.kpi_id
            ).filter(KPIGovernanceBodyLink.governance_body_id.in_(gb_ids_int))

        if selected_group_labels:
            value_types_with_contributions = value_types_with_contributions.filter(
                or_(Initiative.group_label.in_(selected_group_labels), Initiative.group_label.is_(None))
            )

        if selected_impact_levels:
            value_types_with_contributions = value_types_with_contributions.filter(
                Initiative.impact_on_challenge.in_(selected_impact_levels)
            )

        if not show_archived:
            value_types_with_contributions = value_types_with_contributions.filter(KPI.is_archived.is_(False))

        # Query 2: Value types with formula KPIs (calculated values)
        value_types_with_formulas = (
            db.session.query(ValueType.id)
            .join(KPIValueTypeConfig, ValueType.id == KPIValueTypeConfig.value_type_id)
            .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .join(ChallengeInitiativeLink, Initiative.id == ChallengeInitiativeLink.initiative_id)
            .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
            .filter(
                Challenge.space_id.in_(space_ids),
                ValueType.organization_id == org_id,
                ValueType.is_active.is_(True),
                KPIValueTypeConfig.calculation_type.in_(["formula", "linked"]),
            )
        )

        # Apply filters to formulas query
        if selected_governance_body_ids:
            gb_ids_int = [int(gb_id) for gb_id in selected_governance_body_ids]
            value_types_with_formulas = value_types_with_formulas.join(
                KPIGovernanceBodyLink, KPI.id == KPIGovernanceBodyLink.kpi_id
            ).filter(KPIGovernanceBodyLink.governance_body_id.in_(gb_ids_int))

        if selected_group_labels:
            value_types_with_formulas = value_types_with_formulas.filter(
                or_(Initiative.group_label.in_(selected_group_labels), Initiative.group_label.is_(None))
            )

        if selected_impact_levels:
            value_types_with_formulas = value_types_with_formulas.filter(
                Initiative.impact_on_challenge.in_(selected_impact_levels)
            )

        if not show_archived:
            value_types_with_formulas = value_types_with_formulas.filter(KPI.is_archived.is_(False))

        # Combine both queries
        value_type_ids_with_data = set(
            [row[0] for row in value_types_with_contributions.all()] + [row[0] for row in value_types_with_formulas.all()]
        )
    else:
        value_type_ids_with_data = set()

    # Get all active value types
    all_value_types = (
        ValueType.query.filter_by(organization_id=org_id, is_active=True).order_by(ValueType.display_order).all()
    )

    # Get value types - apply smart filtering unless show_all_columns is enabled
    if show_all_columns:
        # Show all columns override - show everything
        value_types = all_value_types
        hidden_value_types = []
    else:
        # Smart filtering: only show columns with actual contribution data
        if value_type_ids_with_data:
            # Filter to show only columns with data
            value_types = [vt for vt in all_value_types if vt.id in value_type_ids_with_data]
            hidden_value_types = [vt for vt in all_value_types if vt.id not in value_type_ids_with_data]
        elif not space_ids:
            # No spaces at all - show all columns (nothing to filter)
            value_types = all_value_types
            hidden_value_types = []
        else:
            # Have spaces but no data - hide all columns
            value_types = []
            hidden_value_types = all_value_types

    # Get level visibility controls (default all visible)
    show_levels = {
        "spaces": request.args.get("show_spaces", "1") == "1",
        "challenges": request.args.get("show_challenges", "1") == "1",
        "initiatives": request.args.get("show_initiatives", "1") == "1",
        "systems": request.args.get("show_systems", "1") == "1",
        "kpis": request.args.get("show_kpis", "1") == "1",
    }

    # Get entity links for workspace view
    from app.models import EntityLink

    challenge_links = {}
    initiative_links = {}
    system_links = {}
    kpi_links = {}

    for space in spaces:
        for challenge in space.challenges:
            # Get challenge links
            links = EntityLink.get_links_for_entity("challenge", challenge.id, current_user.id, include_private=True)
            if links:
                challenge_links[challenge.id] = links

            # Get initiative links
            for init_link in challenge.initiative_links:
                initiative = init_link.initiative
                links = EntityLink.get_links_for_entity(
                    "initiative", initiative.id, current_user.id, include_private=True
                )
                if links:
                    initiative_links[initiative.id] = links

                # Get system links
                for sys_link in initiative.system_links:
                    system = sys_link.system
                    links = EntityLink.get_links_for_entity("system", system.id, current_user.id, include_private=True)
                    if links:
                        system_links[system.id] = links

                    # Get KPI links
                    for kpi in sys_link.kpis:
                        links = EntityLink.get_links_for_entity("kpi", kpi.id, current_user.id, include_private=True)
                        if links:
                            kpi_links[kpi.id] = links

    # Calculate counts for initiative group labels (A, B, C, D)
    group_counts = {}
    if space_ids:
        for group_label in ["A", "B", "C", "D"]:
            count = (
                db.session.query(Initiative.id)
                .join(ChallengeInitiativeLink, Initiative.id == ChallengeInitiativeLink.initiative_id)
                .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
                .filter(Challenge.space_id.in_(space_ids), Initiative.group_label == group_label)
                .distinct()
                .count()
            )
            group_counts[group_label] = count
    else:
        group_counts = {"A": 0, "B": 0, "C": 0, "D": 0}

    # Calculate counts for initiative impact levels
    impact_counts = {}
    if space_ids:
        for impact_level in ["not_assessed", "low", "medium", "high", "no_consensus"]:
            count = (
                db.session.query(Initiative.id)
                .join(ChallengeInitiativeLink, Initiative.id == ChallengeInitiativeLink.initiative_id)
                .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
                .filter(Challenge.space_id.in_(space_ids), Initiative.impact_on_challenge == impact_level)
                .distinct()
                .count()
            )
            impact_counts[impact_level] = count
    else:
        impact_counts = {
            "not_assessed": 0,
            "low": 0,
            "medium": 0,
            "high": 0,
            "no_consensus": 0,
        }

    # Calculate KPI counts per governance body
    gb_kpi_counts = {}
    if space_ids and governance_bodies:
        for gb in governance_bodies:
            count = (
                db.session.query(KPI.id)
                .join(KPIGovernanceBodyLink, KPI.id == KPIGovernanceBodyLink.kpi_id)
                .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
                .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
                .join(ChallengeInitiativeLink, Initiative.id == ChallengeInitiativeLink.initiative_id)
                .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
                .filter(Challenge.space_id.in_(space_ids), KPIGovernanceBodyLink.governance_body_id == gb.id)
                .distinct()
                .count()
            )
            gb_kpi_counts[gb.id] = count
    else:
        gb_kpi_counts = {gb.id: 0 for gb in governance_bodies}

    # Calculate level counts (for Show Levels section)
    level_counts = {}
    if space_ids:
        # Spaces count (already calculated)
        level_counts["spaces"] = (
            all_spaces_count
            if space_type_filter == "all"
            else public_spaces_count if space_type_filter == "public" else private_spaces_count
        )

        # Challenges count
        level_counts["challenges"] = db.session.query(Challenge.id).filter(Challenge.space_id.in_(space_ids)).count()

        # Initiatives count
        initiatives_query = (
            db.session.query(Initiative.id)
            .join(ChallengeInitiativeLink, Initiative.id == ChallengeInitiativeLink.initiative_id)
            .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
            .filter(Challenge.space_id.in_(space_ids))
        )
        if selected_group_labels:
            initiatives_query = initiatives_query.filter(
                or_(Initiative.group_label.in_(selected_group_labels), Initiative.group_label.is_(None))
            )
        level_counts["initiatives"] = initiatives_query.distinct().count()

        # Systems count
        level_counts["systems"] = (
            db.session.query(System.id)
            .join(InitiativeSystemLink, System.id == InitiativeSystemLink.system_id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .join(ChallengeInitiativeLink, Initiative.id == ChallengeInitiativeLink.initiative_id)
            .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
            .filter(Challenge.space_id.in_(space_ids))
            .distinct()
            .count()
        )

        # KPIs count
        kpis_query = (
            db.session.query(KPI.id)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .join(ChallengeInitiativeLink, Initiative.id == ChallengeInitiativeLink.initiative_id)
            .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
            .filter(Challenge.space_id.in_(space_ids))
        )
        if selected_governance_body_ids:
            gb_ids_int = [int(gb_id) for gb_id in selected_governance_body_ids]
            kpis_query = kpis_query.join(KPIGovernanceBodyLink, KPI.id == KPIGovernanceBodyLink.kpi_id).filter(
                KPIGovernanceBodyLink.governance_body_id.in_(gb_ids_int)
            )
        if not show_archived:
            kpis_query = kpis_query.filter(KPI.is_archived.is_(False))
        level_counts["kpis"] = kpis_query.distinct().count()
    else:
        level_counts = {"spaces": 0, "challenges": 0, "initiatives": 0, "systems": 0, "kpis": 0}

    # Calculate archived KPIs count
    archived_kpis_count = 0
    if space_ids:
        archived_query = (
            db.session.query(KPI.id)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .join(ChallengeInitiativeLink, Initiative.id == ChallengeInitiativeLink.initiative_id)
            .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
            .filter(Challenge.space_id.in_(space_ids), KPI.is_archived.is_(True))
        )
        if selected_governance_body_ids:
            gb_ids_int = [int(gb_id) for gb_id in selected_governance_body_ids]
            archived_query = archived_query.join(KPIGovernanceBodyLink, KPI.id == KPIGovernanceBodyLink.kpi_id).filter(
                KPIGovernanceBodyLink.governance_body_id.in_(gb_ids_int)
            )
        archived_kpis_count = archived_query.distinct().count()

    # Get filter presets for this user
    filter_presets = (
        UserFilterPreset.query.filter_by(user_id=current_user.id, organization_id=org_id)
        .order_by(UserFilterPreset.name)
        .all()
    )

    # Determine which preset is currently active
    active_preset = None
    if filter_presets:
        current_filters = dict(request.args)
        for preset in filter_presets:
            if preset.filters and _filters_match(current_filters, preset.filters):
                active_preset = preset
                break

    # Get entity type defaults (for logos in tree)
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

    # Get organization object and logo for template
    organization = Organization.query.get(org_id)
    org_logo = None
    if organization and organization.logo_data:
        org_logo = f"data:{organization.logo_mime_type};base64,{base64.b64encode(organization.logo_data).decode('utf-8')}"

    return render_template(
        "beta/workspace.html",
        org_id=org_id,
        org_name=org_name,
        org_logo=org_logo,
        organization=organization,
        entity_defaults=entity_defaults,
        spaces=spaces,
        value_types=value_types,
        hidden_value_types=hidden_value_types,
        governance_bodies=governance_bodies,
        selected_governance_body_ids=selected_governance_body_ids,
        selected_group_labels=selected_group_labels,
        selected_impact_levels=selected_impact_levels,
        show_archived=show_archived,
        show_levels=show_levels,
        space_type_filter=space_type_filter,
        all_spaces_count=all_spaces_count,
        public_spaces_count=public_spaces_count,
        private_spaces_count=private_spaces_count,
        show_all_columns=show_all_columns,
        group_counts=group_counts,
        impact_counts=impact_counts,
        gb_kpi_counts=gb_kpi_counts,
        challenge_links=challenge_links,
        initiative_links=initiative_links,
        system_links=system_links,
        kpi_links=kpi_links,
        level_counts=level_counts,
        archived_kpis_count=archived_kpis_count,
        filter_presets=filter_presets,
        active_preset=active_preset,
        all_spaces_for_filter=all_spaces_for_filter,
        selected_space_ids=selected_space_ids,
    )
