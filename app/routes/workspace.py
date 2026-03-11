"""
Workspace routes

Main tree/grid navigation and data entry.
"""

from datetime import date
from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import ContributionForm
from app.models import (
    KPI,
    CellComment,
    Challenge,
    ChallengeInitiativeLink,
    Contribution,
    GovernanceBody,
    Initiative,
    InitiativeSystemLink,
    KPISnapshot,
    KPIValueTypeConfig,
    RollupSnapshot,
    Space,
    System,
    User,
    UserOrganizationMembership,
    ValueType,
)
from app.services import AggregationService, ConsensusService, ExcelExportService
from app.services.comment_service import CommentService
from app.services.snapshot_service import SnapshotService

bp = Blueprint("workspace", __name__, url_prefix="/workspace")


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


@bp.route("/dashboard")
@login_required
@organization_required
def dashboard():
    """Dashboard with overview, charts, and recent activity"""
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

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
    }

    # Get recent snapshots (last 5) - now with full snapshot info
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

    return render_template(
        "workspace/dashboard.html",
        org_name=org_name,
        stats=stats,
        recent_snapshots=recent_snapshots,
        recent_comments=recent_comments,
        unread_mentions=unread_mentions,
    )


@bp.route("/")
@login_required
@organization_required
def index():
    """
    Main workspace view: tree/grid navigation.

    Shows spaces (collapsed by default) with roll-up values visible.
    """
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

    # Get space type filter (all, private, public)
    space_type_filter = request.args.get("space_type", "all")

    # Get space counts for filter pills
    all_spaces_count = Space.query.filter_by(organization_id=org_id).count()
    public_spaces_count = Space.query.filter_by(organization_id=org_id, is_private=False).count()
    private_spaces_count = Space.query.filter_by(organization_id=org_id, is_private=True).count()

    # Get show_all_columns flag (override smart column filtering)
    # Default to True (show all columns by default)
    show_all_columns = request.args.get("show_all_columns", "1") == "1"

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

    # Get show_archived flag
    show_archived = request.args.get("show_archived") == "1"

    # Get spaces based on filter
    spaces_query = Space.query.filter_by(organization_id=org_id)
    if space_type_filter == "private":
        spaces_query = spaces_query.filter_by(is_private=True)
    elif space_type_filter == "public":
        spaces_query = spaces_query.filter_by(is_private=False)
    # 'all' means no additional filter
    spaces = spaces_query.order_by(Space.display_order, Space.name).all()

    # Get space IDs for filtering value types
    space_ids = [space.id for space in spaces]

    # Get active value types that have at least one contribution in the FILTERED spaces
    # Join through the entire hierarchy: Space → Challenge → Initiative → System → KPI → Config → Contribution
    from app.models import Contribution, KPIGovernanceBodyLink

    if space_ids:
        # Build query to find value types with data in filtered spaces
        value_types_query = (
            db.session.query(ValueType.id)
            .join(KPIValueTypeConfig, ValueType.id == KPIValueTypeConfig.value_type_id)
            .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .join(ChallengeInitiativeLink, Initiative.id == ChallengeInitiativeLink.initiative_id)
            .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
            .join(Contribution, KPIValueTypeConfig.id == Contribution.kpi_value_type_config_id)
            .filter(
                Challenge.space_id.in_(space_ids), ValueType.organization_id == org_id, ValueType.is_active.is_(True)
            )
        )

        # Apply governance body filter if selected
        if selected_governance_body_ids:
            gb_ids_int = [int(gb_id) for gb_id in selected_governance_body_ids]
            value_types_query = value_types_query.join(
                KPIGovernanceBodyLink, KPI.id == KPIGovernanceBodyLink.kpi_id
            ).filter(KPIGovernanceBodyLink.governance_body_id.in_(gb_ids_int))

        # Apply archived filter
        if not show_archived:
            value_types_query = value_types_query.filter(KPI.is_archived.is_(False))

        value_types_with_data = value_types_query.distinct().all()
        value_type_ids_with_data = {vt_id for (vt_id,) in value_types_with_data}
    else:
        value_type_ids_with_data = set()

    # Get all active value types
    all_value_types = (
        ValueType.query.filter_by(organization_id=org_id, is_active=True).order_by(ValueType.display_order).all()
    )

    # Get value types - apply smart filtering unless show_all_columns is enabled
    if show_all_columns:
        # Show all columns override
        value_types = all_value_types
        hidden_value_types = []
    elif value_type_ids_with_data:
        # Smart filtering: only show columns with data
        value_types = [vt for vt in all_value_types if vt.id in value_type_ids_with_data]
        hidden_value_types = [vt for vt in all_value_types if vt.id not in value_type_ids_with_data]
    else:
        # If no contributions yet, show all active value types
        value_types = all_value_types
        hidden_value_types = []

    # Get level visibility controls (default all visible)
    show_levels = {
        "spaces": request.args.get("show_spaces", "1") == "1",
        "challenges": request.args.get("show_challenges", "1") == "1",
        "initiatives": request.args.get("show_initiatives", "1") == "1",
        "systems": request.args.get("show_systems", "1") == "1",
        "kpis": request.args.get("show_kpis", "1") == "1",
    }

    return render_template(
        "workspace/index.html",
        org_name=org_name,
        spaces=spaces,
        value_types=value_types,
        hidden_value_types=hidden_value_types,
        governance_bodies=governance_bodies,
        selected_governance_body_ids=selected_governance_body_ids,
        show_archived=show_archived,
        show_levels=show_levels,
        space_type_filter=space_type_filter,
        all_spaces_count=all_spaces_count,
        public_spaces_count=public_spaces_count,
        private_spaces_count=private_spaces_count,
        show_all_columns=show_all_columns,
    )


@bp.route("/export-excel")
@login_required
@organization_required
def export_excel():
    """Export workspace to Excel file"""
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

    # Generate Excel file
    excel_file = ExcelExportService.export_workspace(org_id)

    # Create safe filename
    safe_org_name = "".join(c for c in org_name if c.isalnum() or c in (" ", "-", "_")).strip()
    filename = f"Workspace_{safe_org_name}.xlsx"

    return send_file(
        excel_file,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@bp.route("/kpi/<int:kpi_id>/value-type/<int:vt_id>", methods=["GET", "POST"])
@login_required
@organization_required
def kpi_cell_detail(kpi_id, vt_id):
    """
    Detail page for one KPI cell (KPI + value type).

    Shows:
    - Breadcrumb (org > space > challenge > initiative > system > kpi)
    - Current consensus status
    - List of contributions
    - Form to add/edit contribution
    """
    org_id = session.get("organization_id")

    # Get KPI and value type
    kpi = KPI.query.get_or_404(kpi_id)
    value_type = ValueType.query.get_or_404(vt_id)

    # Security check: ensure KPI belongs to current organization
    is_link = kpi.initiative_system_link
    initiative = is_link.initiative
    if initiative.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    # Get KPI-ValueType config
    config = KPIValueTypeConfig.query.filter_by(kpi_id=kpi_id, value_type_id=vt_id).first()
    if not config:
        flash("This KPI does not use this value type", "warning")
        return redirect(url_for("workspace.index"))

    # Get consensus status
    consensus = ConsensusService.get_cell_value(config)

    # Get all contributions
    contributions = config.contributions

    # Handle contribution form
    form = ContributionForm()

    # Customize qualitative level choices based on value type kind
    if value_type.is_qualitative():
        if value_type.kind == "risk":
            form.qualitative_level.choices = [
                ("", "Select..."),
                ("1", "! (Low)"),
                ("2", "!! (Medium)"),
                ("3", "!!! (High)"),
            ]
        elif value_type.kind == "positive_impact":
            form.qualitative_level.choices = [
                ("", "Select..."),
                ("1", "★ (Low)"),
                ("2", "★★ (Medium)"),
                ("3", "★★★ (High)"),
            ]
        elif value_type.kind == "negative_impact":
            form.qualitative_level.choices = [
                ("", "Select..."),
                ("1", "▼ (Low)"),
                ("2", "▼▼ (Medium)"),
                ("3", "▼▼▼ (High)"),
            ]
        elif value_type.kind == "level":
            form.qualitative_level.choices = [
                ("", "Select..."),
                ("1", "● (Low)"),
                ("2", "●● (Medium)"),
                ("3", "●●● (High)"),
            ]
        elif value_type.kind == "sentiment":
            form.qualitative_level.choices = [
                ("", "Select..."),
                ("1", "☹️ (Negative)"),
                ("2", "😐 (Neutral)"),
                ("3", "😊 (Positive)"),
            ]

    # Check if KPI is archived
    if kpi.is_archived:
        flash(
            "This KPI is archived and cannot accept new contributions. Please unarchive it first if you need to add data.",
            "warning",
        )
        return redirect(url_for("workspace.index"))

    if form.validate_on_submit():
        contributor_name = form.contributor_name.data
        entry_mode = request.form.get("entry_mode", "contributing")  # 'new_data' or 'contributing'

        # Check if this is "new data" mode (time evolved)
        if entry_mode == "new_data":
            # Auto-create snapshot before replacing data
            try:
                snapshot_label = f"Auto: Before update by {contributor_name}"

                # Create snapshot for this specific KPI cell
                # Use allow_duplicates=True so multiple snapshots can be created on same day
                snapshot = SnapshotService.create_kpi_snapshot(
                    config_id=config.id,
                    snapshot_date=date.today(),
                    label=snapshot_label,
                    user_id=current_user.id,
                    allow_duplicates=True,  # Always create new snapshot for auto-snapshots
                )

                if snapshot:
                    flash(f"Snapshot created: {snapshot.snapshot_label} (value: {snapshot.get_value()})", "info")

                # Delete ALL existing contributions for this cell
                Contribution.query.filter_by(kpi_value_type_config_id=config.id).delete()

                # Create new contribution
                contribution = Contribution(
                    kpi_value_type_config_id=config.id, contributor_name=contributor_name, comment=form.comment.data
                )
                if value_type.is_numeric():
                    contribution.numeric_value = form.numeric_value.data
                else:
                    contribution.qualitative_level = form.qualitative_level.data

                db.session.add(contribution)
                db.session.commit()

                flash(f"Previous value saved in snapshot. New value entered by {contributor_name}", "success")
                return redirect(url_for("workspace.index", show_all_columns=1))

            except Exception as e:
                db.session.rollback()
                flash(f"Error creating snapshot: {str(e)}", "danger")
                return redirect(url_for("workspace.kpi_cell_detail", kpi_id=kpi_id, vt_id=vt_id))

        # Normal mode: contributing to current period
        # Check if this contributor already has a contribution for this cell
        existing = Contribution.query.filter_by(
            kpi_value_type_config_id=config.id, contributor_name=contributor_name
        ).first()

        if existing:
            # Update existing contribution
            if value_type.is_numeric():
                existing.numeric_value = form.numeric_value.data
                existing.qualitative_level = None
            else:
                existing.numeric_value = None
                existing.qualitative_level = form.qualitative_level.data
            existing.comment = form.comment.data
            flash(f"Contribution from {contributor_name} updated", "success")
        else:
            # Create new contribution
            contribution = Contribution(
                kpi_value_type_config_id=config.id, contributor_name=contributor_name, comment=form.comment.data
            )
            if value_type.is_numeric():
                contribution.numeric_value = form.numeric_value.data
            else:
                contribution.qualitative_level = form.qualitative_level.data

            db.session.add(contribution)
            flash(f"Contribution from {contributor_name} added", "success")

        db.session.commit()
        return redirect(url_for("workspace.index", show_all_columns=1))

    # Build breadcrumb
    system = is_link.system
    challenge_names = [ci.challenge.name for ci in initiative.challenge_links]
    space_names = [ci.challenge.space.name for ci in initiative.challenge_links]

    breadcrumb = {
        "organization": session.get("organization_name"),
        "space": space_names[0] if space_names else "N/A",
        "challenge": challenge_names[0] if challenge_names else "N/A",
        "initiative": initiative.name,
        "system": system.name,
        "kpi": kpi.name,
        "value_type": value_type.name,
    }

    return render_template(
        "workspace/kpi_cell_detail.html",
        kpi=kpi,
        value_type=value_type,
        config=config,
        consensus=consensus,
        contributions=contributions,
        form=form,
        breadcrumb=breadcrumb,
    )


@bp.route("/kpi/<int:kpi_id>/value-type/<int:vt_id>/delete-contribution", methods=["POST"])
@login_required
@organization_required
def delete_contribution(kpi_id, vt_id):
    """
    Delete a contribution from a KPI cell.
    """
    org_id = session.get("organization_id")
    contribution_id = request.form.get("contribution_id")

    if not contribution_id:
        flash("Invalid request", "danger")
        return redirect(url_for("workspace.kpi_cell_detail", kpi_id=kpi_id, vt_id=vt_id))

    # Get contribution and verify ownership
    contribution = Contribution.query.get_or_404(contribution_id)
    config = contribution.kpi_value_type_config
    kpi = config.kpi
    initiative = kpi.initiative_system_link.initiative

    if initiative.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    contributor_name = contribution.contributor_name
    db.session.delete(contribution)
    db.session.commit()

    flash(f'Contribution from "{contributor_name}" has been deleted', "success")
    return redirect(url_for("workspace.kpi_cell_detail", kpi_id=kpi_id, vt_id=vt_id))


@bp.route("/api/rollup/<string:entity_type>/<int:entity_id>/<int:value_type_id>")
@login_required
@organization_required
def api_rollup(entity_type, entity_id, value_type_id):
    """
    API endpoint to get roll-up value for a specific entity and value type.

    Used by the tree/grid to display rolled-up values.
    """
    try:
        if entity_type == "system":
            # KPI → System rollup
            from app.models import InitiativeSystemLink

            is_link = InitiativeSystemLink.query.get(entity_id)
            if not is_link:
                return jsonify({"error": "Not found"}), 404

            result = AggregationService.get_kpi_to_system_rollup(is_link, value_type_id)
            return jsonify(result)

        elif entity_type == "initiative":
            result = AggregationService.get_system_to_initiative_rollup(entity_id, value_type_id)
            return jsonify(result)

        elif entity_type == "challenge":
            result = AggregationService.get_initiative_to_challenge_rollup(entity_id, value_type_id)
            return jsonify(result)

        elif entity_type == "space":
            result = AggregationService.get_challenge_to_space_rollup(entity_id, value_type_id)
            return jsonify(result)

        else:
            return jsonify({"error": "Invalid entity type"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# SNAPSHOT MANAGEMENT ROUTES (Time-Series Tracking)
# ============================================================================


@bp.route("/snapshots/create", methods=["POST"])
@login_required
@organization_required
def create_snapshot():
    """
    Create a snapshot of current workspace state.

    Captures all KPI values and rollups for the organization.
    """
    org_id = session.get("organization_id")
    snapshot_date_str = request.form.get("snapshot_date")
    label = request.form.get("label", "").strip()
    is_public = request.form.get("is_public") == "true"

    # Parse date
    if snapshot_date_str:
        try:
            snapshot_date = date.fromisoformat(snapshot_date_str)
        except ValueError:
            flash("Invalid date format", "danger")
            return redirect(url_for("workspace.index"))
    else:
        snapshot_date = date.today()

    # Create snapshots
    try:
        result = SnapshotService.create_organization_snapshot(
            org_id, snapshot_date=snapshot_date, label=label or None, user_id=current_user.id, is_public=is_public
        )

        visibility = "Public" if is_public else "Private"
        flash(
            f'{visibility} snapshot created: {result["kpi_snapshots"]} KPI values, '
            f'{result["rollup_snapshots"]} rollup values captured for {snapshot_date.isoformat()}',
            "success",
        )

        if result["skipped"] > 0:
            flash(f'{result["skipped"]} KPIs skipped (no consensus data)', "info")

    except Exception as e:
        db.session.rollback()
        flash(f"Error creating snapshot: {str(e)}", "danger")

    return redirect(url_for("workspace.list_snapshots"))


@bp.route("/snapshots/list")
@login_required
@organization_required
def list_snapshots():
    """List all available snapshots for the organization"""
    org_id = session.get("organization_id")

    # Get filter parameters
    show_private = request.args.get("show_private", "1") == "1"
    show_public = request.args.get("show_public", "1") == "1"

    try:
        # Get all snapshots with full details
        snapshots = SnapshotService.get_all_snapshots(
            org_id, user_id=current_user.id, show_private=show_private, show_public=show_public
        )

        # Format for template
        snapshots_info = []
        for snap in snapshots:
            snapshots_info.append(
                {
                    "batch_id": snap["snapshot_batch_id"],
                    "date": snap["snapshot_date"].isoformat(),
                    "created_at": snap["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                    "timestamp": snap["created_at"].isoformat(),
                    "label": snap["snapshot_label"],
                    "kpi_count": snap["kpi_count"],
                    "formatted_date": snap["snapshot_date"].strftime("%Y-%m-%d (%A)"),
                    "formatted_time": snap["created_at"].strftime("%H:%M:%S"),
                    "is_public": snap["is_public"],
                    "owner_user_id": snap["owner_user_id"],
                    "owner_name": snap["owner_name"],
                    "is_owner": snap["owner_user_id"] == current_user.id,
                }
            )

        return render_template(
            "workspace/snapshots.html",
            snapshots=snapshots_info,
            organization_name=session.get("organization_name"),
            show_private=show_private,
            show_public=show_public,
            current_user_id=current_user.id,
        )

    except Exception as e:
        flash(f"Error loading snapshots: {str(e)}", "danger")
        return redirect(url_for("workspace.index"))


@bp.route("/snapshots/view/<batch_id>")
@login_required
@organization_required
def view_snapshot(batch_id):
    """
    View workspace state as of a specific snapshot batch.

    Shows historical values instead of current values.
    """
    org_id = session.get("organization_id")

    # Get snapshot info from batch
    sample = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).first()
    if not sample:
        flash("Snapshot not found", "danger")
        return redirect(url_for("workspace.list_snapshots"))

    view_date = sample.snapshot_date

    # Get spaces and value types (current structure)
    spaces = Space.query.filter_by(organization_id=org_id).order_by(Space.display_order, Space.name).all()

    value_types = (
        ValueType.query.filter_by(organization_id=org_id, is_active=True).order_by(ValueType.display_order).all()
    )

    # Get governance bodies for filtering
    governance_bodies = (
        GovernanceBody.query.filter_by(organization_id=org_id, is_active=True)
        .order_by(GovernanceBody.display_order)
        .all()
    )

    # Get level visibility controls (default all visible)
    show_levels = {
        "spaces": request.args.get("show_spaces", "1") == "1",
        "challenges": request.args.get("show_challenges", "1") == "1",
        "initiatives": request.args.get("show_initiatives", "1") == "1",
        "systems": request.args.get("show_systems", "1") == "1",
        "kpis": request.args.get("show_kpis", "1") == "1",
    }

    return render_template(
        "workspace/index.html",
        spaces=spaces,
        value_types=value_types,
        governance_bodies=governance_bodies,
        selected_governance_body_ids=[],
        show_archived=False,
        show_levels=show_levels,
        organization_name=session.get("organization_name"),
        snapshot_date=view_date,
        is_historical_view=True,
    )


@bp.route("/snapshots/compare")
@login_required
@organization_required
def compare_snapshots():
    """Compare two snapshots side-by-side"""
    org_id = session.get("organization_id")

    # Get batch_id parameters
    batch_id1 = request.args.get("batch_id1")
    batch_id2 = request.args.get("batch_id2", "current")

    if not batch_id1:
        flash("Please select a snapshot to compare", "warning")
        return redirect(url_for("workspace.list_snapshots"))

    # Get first snapshot info
    sample1 = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id1).first()
    if not sample1:
        flash("Snapshot not found", "danger")
        return redirect(url_for("workspace.list_snapshots"))

    date1 = sample1.snapshot_date
    datetime1 = sample1.created_at
    label1 = sample1.snapshot_label

    # Get second snapshot info (or use current)
    if batch_id2 != "current":
        sample2 = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id2).first()
        if not sample2:
            flash("Second snapshot not found", "danger")
            return redirect(url_for("workspace.list_snapshots"))
        date2 = sample2.snapshot_date
        datetime2 = sample2.created_at
        label2 = sample2.snapshot_label
    else:
        date2 = None
        datetime2 = None
        label2 = "Current"

    # Get all KPI configs for this organization
    configs = (
        db.session.query(KPIValueTypeConfig)
        .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(Initiative.organization_id == org_id)
        .all()
    )

    # Build comparison data
    comparisons = []
    for config in configs:
        # Get snapshot 1 value - match by batch_id
        snapshot1 = KPISnapshot.query.filter_by(kpi_value_type_config_id=config.id, snapshot_batch_id=batch_id1).first()

        # Get snapshot 2 value (or current consensus)
        if batch_id2 != "current":
            snapshot2 = KPISnapshot.query.filter_by(
                kpi_value_type_config_id=config.id, snapshot_batch_id=batch_id2
            ).first()
            value2 = snapshot2.get_value() if snapshot2 else None
        else:
            # Use current consensus - get contributions for this config
            contributions = Contribution.query.filter_by(kpi_value_type_config_id=config.id).all()
            consensus = ConsensusService.calculate_consensus(contributions)
            value2 = consensus.get("value")

        value1 = snapshot1.get_value() if snapshot1 else None

        # Calculate change
        change = None
        percent_change = None
        if value1 is not None and value2 is not None:
            change = float(value2) - float(value1)
            if value1 != 0:
                percent_change = (change / float(value1)) * 100

        comparisons.append(
            {
                "config": config,
                "kpi": config.kpi,
                "value_type": config.value_type,
                "value1": value1,
                "value2": value2,
                "change": change,
                "percent_change": percent_change,
            }
        )

    return render_template(
        "workspace/compare_snapshots.html",
        comparisons=comparisons,
        date1=date1,
        datetime1=datetime1,
        date2=date2,
        datetime2=datetime2,
        label1=label1,
        label2=label2,
        organization_name=session.get("organization_name"),
    )


@bp.route("/snapshots/<batch_id>/toggle-privacy", methods=["POST"])
@login_required
@organization_required
def toggle_snapshot_privacy(batch_id):
    """Toggle privacy status of a snapshot batch (private <-> public)"""
    try:
        print(f"[DEBUG] Toggling privacy for batch_id: {batch_id}")

        # Get one snapshot from this batch to check ownership
        sample_snapshot = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).first()

        if not sample_snapshot:
            print(f"[DEBUG] Snapshot not found for batch_id: {batch_id}")
            return jsonify({"error": "Snapshot not found"}), 404

        print(
            f"[DEBUG] Current is_public: {sample_snapshot.is_public}, owner: {sample_snapshot.owner_user_id}, current_user: {current_user.id}"
        )

        # Check ownership
        if sample_snapshot.owner_user_id != current_user.id:
            print(f"[DEBUG] Ownership check failed: {sample_snapshot.owner_user_id} != {current_user.id}")
            return jsonify({"error": "Only the snapshot owner can change privacy settings"}), 403

        # Toggle all KPI snapshots in this batch
        new_status = not sample_snapshot.is_public
        kpi_count = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).update({"is_public": new_status})

        # Toggle all rollup snapshots in this batch
        rollup_count = RollupSnapshot.query.filter_by(snapshot_batch_id=batch_id).update({"is_public": new_status})

        db.session.commit()

        print(
            f"[DEBUG] Toggled {kpi_count} KPI snapshots and {rollup_count} rollup snapshots to is_public={new_status}"
        )

        return jsonify(
            {
                "success": True,
                "is_public": new_status,
                "message": f'Snapshot is now {"public" if new_status else "private"}',
            }
        )

    except Exception:
        db.session.rollback()


@bp.route("/snapshots/<batch_id>/delete", methods=["POST"])
@login_required
@organization_required
def delete_snapshot(batch_id):
    """Delete all snapshots in a batch"""
    try:
        # Get one snapshot from this batch to check ownership
        sample_snapshot = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).first()

        if not sample_snapshot:
            return jsonify({"error": "Snapshot not found"}), 404

        # Check ownership
        if sample_snapshot.owner_user_id != current_user.id:
            return jsonify({"error": "Only the snapshot owner can delete snapshots"}), 403

        # Delete all KPI snapshots in this batch
        kpi_count = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).delete()

        # Delete all rollup snapshots in this batch
        rollup_count = RollupSnapshot.query.filter_by(snapshot_batch_id=batch_id).delete()

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Deleted snapshot batch ({kpi_count} KPI snapshots, {rollup_count} rollup snapshots)",
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/snapshots/bulk/toggle-privacy", methods=["POST"])
@login_required
@organization_required
def bulk_toggle_snapshot_privacy():
    """Toggle privacy status for multiple snapshot batches"""
    try:
        data = request.get_json()
        batch_ids = data.get("batch_ids", [])
        make_public = data.get("make_public", True)

        if not batch_ids:
            return jsonify({"error": "No batch IDs provided"}), 400

        success_count = 0
        error_count = 0

        for batch_id in batch_ids:
            # Get one snapshot from this batch to check ownership
            sample_snapshot = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).first()

            if not sample_snapshot:
                error_count += 1
                continue

            # Check ownership
            if sample_snapshot.owner_user_id != current_user.id:
                error_count += 1
                continue

            # Update all KPI snapshots in this batch
            KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).update({"is_public": make_public})

            # Update all rollup snapshots in this batch
            RollupSnapshot.query.filter_by(snapshot_batch_id=batch_id).update({"is_public": make_public})

            success_count += 1

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "success_count": success_count,
                "error_count": error_count,
                "message": f'Updated {success_count} snapshot(s) to {"public" if make_public else "private"}',
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/snapshots/bulk/delete", methods=["POST"])
@login_required
@organization_required
def bulk_delete_snapshots():
    """Delete multiple snapshot batches"""
    try:
        data = request.get_json()
        batch_ids = data.get("batch_ids", [])

        if not batch_ids:
            return jsonify({"error": "No batch IDs provided"}), 400

        success_count = 0
        error_count = 0

        for batch_id in batch_ids:
            # Get one snapshot from this batch to check ownership
            sample_snapshot = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).first()

            if not sample_snapshot:
                error_count += 1
                continue

            # Check ownership
            if sample_snapshot.owner_user_id != current_user.id:
                error_count += 1
                continue

            # Delete all KPI snapshots in this batch
            KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).delete()

            # Delete all rollup snapshots in this batch
            RollupSnapshot.query.filter_by(snapshot_batch_id=batch_id).delete()

            success_count += 1

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "success_count": success_count,
                "error_count": error_count,
                "message": f"Deleted {success_count} snapshot batch(es)",
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
        return jsonify({"error": str(e)}), 500
        print(f"[DEBUG] Error toggling privacy: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/kpi/<int:config_id>/trend")
@login_required
@organization_required
def get_kpi_trend(config_id):
    """
    Get trend information for a KPI.

    Returns: {'direction': 'up'|'down'|'stable', 'change': value, 'percent_change': percent}
    """
    try:
        trend = SnapshotService.calculate_trend(config_id, periods=2)

        if trend is None:
            return jsonify({"error": "Insufficient historical data"}), 404

        return jsonify(trend)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/kpi/<int:config_id>/history")
@login_required
@organization_required
def get_kpi_history(config_id):
    """
    Get historical snapshots for a KPI.

    Returns array of snapshots with dates and values.
    """
    try:
        limit = request.args.get("limit", 50, type=int)
        snapshots = SnapshotService.get_kpi_history(config_id, limit=limit)

        # Get the config and current consensus value
        config = KPIValueTypeConfig.query.get_or_404(config_id)
        consensus = ConsensusService.get_cell_value(config)

        # Format for chart: array of {date, value} objects
        # Reverse so oldest is first (better for chart display)
        # Use created_at timestamp to distinguish snapshots on the same day
        history = []
        for snapshot in reversed(snapshots):
            value = snapshot.get_value()
            if value is not None:  # Only include snapshots with actual values
                # Use full timestamp for snapshots on same day
                date_label = snapshot.created_at.strftime("%Y-%m-%d %H:%M:%S")
                history.append({"date": date_label, "value": float(value), "label": snapshot.snapshot_label})

        # Add current value as the latest point (if it exists and differs from last snapshot)
        if consensus and consensus.get("status") != "no_data":
            current_value = consensus.get("value")
            if current_value is not None:
                # Use current timestamp for current value
                from datetime import datetime

                current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                history.append({"date": current_time, "value": float(current_value), "label": "Current"})

        return jsonify({"history": history, "count": len(history)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# COMMENTS & COLLABORATION ROUTES (@mentions support)
# ============================================================================


@bp.route("/api/cell/<int:config_id>/comments", methods=["GET"])
@login_required
@organization_required
def get_cell_comments(config_id):
    """Get all comments for a KPI cell"""
    try:
        org_id = session.get("organization_id")

        # Check permission to view comments
        if not current_user.can_view_comments(org_id):
            return jsonify({"error": "You do not have permission to view comments"}), 403

        include_resolved = request.args.get("include_resolved", "true").lower() == "true"
        comments = CommentService.get_comments_for_cell(config_id, include_resolved=include_resolved)

        def render_comment_tree(comment):
            """Recursively render comment with replies"""
            result = {
                **comment.to_dict(),
                "rendered_text": CommentService.render_comment_with_mentions(comment.comment_text, org_id),
                "replies": [],
            }

            # Add replies
            for reply in comment.replies:
                result["replies"].append(render_comment_tree(reply))

            return result

        return jsonify(
            {
                "comments": [c.to_dict() for c in comments],
                "count": len(comments),
                "rendered_comments": [render_comment_tree(c) for c in comments],
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/cell/<int:config_id>/comments", methods=["POST"])
@login_required
@organization_required
def create_cell_comment(config_id):
    """Create a new comment on a KPI cell"""
    try:
        org_id = session.get("organization_id")

        # Check permission to add comments
        if not current_user.can_add_comments(org_id):
            return jsonify({"error": "You do not have permission to add comments"}), 403

        data = request.get_json()
        comment_text = data.get("comment_text", "").strip()
        parent_comment_id = data.get("parent_comment_id")

        if not comment_text:
            return jsonify({"error": "Comment text is required"}), 400

        comment = CommentService.create_comment(
            config_id=config_id,
            user_id=current_user.id,
            comment_text=comment_text,
            parent_comment_id=parent_comment_id,
            organization_id=org_id,
        )

        return jsonify(
            {
                "success": True,
                "comment": comment.to_dict(),
                "rendered_text": CommentService.render_comment_with_mentions(comment.comment_text, org_id),
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/comments/<int:comment_id>", methods=["PUT"])
@login_required
@organization_required
def update_cell_comment(comment_id):
    """Update an existing comment"""
    try:
        comment = CellComment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        # Check ownership
        if comment.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        data = request.get_json()
        comment_text = data.get("comment_text", "").strip()

        if not comment_text:
            return jsonify({"error": "Comment text is required"}), 400

        org_id = session.get("organization_id")

        updated_comment = CommentService.update_comment(
            comment_id=comment_id, comment_text=comment_text, organization_id=org_id
        )

        return jsonify(
            {
                "success": True,
                "comment": updated_comment.to_dict(),
                "rendered_text": CommentService.render_comment_with_mentions(updated_comment.comment_text, org_id),
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/comments/<int:comment_id>", methods=["DELETE"])
@login_required
@organization_required
def delete_cell_comment(comment_id):
    """Delete a comment"""
    try:
        comment = CellComment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        # Check ownership or admin
        if comment.user_id != current_user.id and not current_user.is_global_admin:
            return jsonify({"error": "Unauthorized"}), 403

        success = CommentService.delete_comment(comment_id)

        return jsonify({"success": success})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/comments/<int:comment_id>/resolve", methods=["POST"])
@login_required
@organization_required
def resolve_comment(comment_id):
    """Mark a comment as resolved"""
    try:
        comment = CommentService.resolve_comment(comment_id, current_user.id)

        return jsonify({"success": True, "comment": comment.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/comments/<int:comment_id>/unresolve", methods=["POST"])
@login_required
@organization_required
def unresolve_comment(comment_id):
    """Mark a comment as unresolved"""
    try:
        comment = CommentService.unresolve_comment(comment_id)

        return jsonify({"success": True, "comment": comment.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/mentions/unread")
@login_required
@organization_required
def get_unread_mentions():
    """Get unread mentions for current user"""
    try:
        limit = request.args.get("limit", 20, type=int)
        mentions = CommentService.get_unread_mentions(current_user.id, limit=limit)
        total_count = CommentService.get_unread_mentions_count(current_user.id)

        return jsonify(
            {
                "mentions": [m.to_dict() for m in mentions],
                "count": len(mentions),  # Number of mentions returned (limited)
                "total_count": total_count,  # Total unread mentions count
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/mentions/<int:notification_id>/read", methods=["POST"])
@login_required
@organization_required
def mark_mention_read(notification_id):
    """Mark a mention as read"""
    try:
        notification = CommentService.mark_mention_read(notification_id)

        return jsonify({"success": True, "notification": notification.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/mentions/mark-all-read", methods=["POST"])
@login_required
@organization_required
def mark_all_mentions_read():
    """Mark all mentions as read for current user"""
    try:
        count = CommentService.mark_all_mentions_read(current_user.id)

        return jsonify({"success": True, "count": count})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/org/users/search")
@login_required
@organization_required
def search_org_users():
    """
    Search users in current organization for @mention autocomplete.

    Query param: q=search_term
    """
    try:
        org_id = session.get("organization_id")
        search_term = request.args.get("q", "").strip().lower()

        # Build query
        query = (
            db.session.query(User)
            .join(UserOrganizationMembership)
            .filter(UserOrganizationMembership.organization_id == org_id)
        )

        # Filter by search term if provided
        if search_term:
            query = query.filter(
                db.or_(User.login.ilike(f"%{search_term}%"), User.display_name.ilike(f"%{search_term}%"))
            )

        # Get results (limit 10)
        users = query.order_by(User.display_name).limit(10).all()

        return jsonify(
            {"users": [{"id": u.id, "login": u.login, "display_name": u.display_name, "email": u.email} for u in users]}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/search")
@login_required
@organization_required
def search_page():
    """Search results page"""
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")
    query = request.args.get("q", "").strip()

    if not query:
        return render_template("workspace/search.html", organization_name=org_name, query="", results={})

    # Search across all entities
    results = {
        "spaces": [],
        "challenges": [],
        "initiatives": [],
        "systems": [],
        "kpis": [],
        "value_types": [],
        "comments": [],
    }

    search_pattern = f"%{query}%"

    # Search Spaces
    spaces = Space.query.filter(
        Space.organization_id == org_id,
        db.or_(Space.name.ilike(search_pattern), Space.description.ilike(search_pattern)),
    ).all()
    results["spaces"] = [{"id": s.id, "name": s.name, "description": s.description} for s in spaces]

    # Search Challenges
    challenges = (
        Challenge.query.join(Space)
        .filter(
            Space.organization_id == org_id,
            db.or_(Challenge.name.ilike(search_pattern), Challenge.description.ilike(search_pattern)),
        )
        .all()
    )
    results["challenges"] = [
        {"id": c.id, "name": c.name, "description": c.description, "space": c.space.name} for c in challenges
    ]

    # Search Initiatives
    initiatives = Initiative.query.filter(
        Initiative.organization_id == org_id,
        db.or_(Initiative.name.ilike(search_pattern), Initiative.description.ilike(search_pattern)),
    ).all()
    results["initiatives"] = [{"id": i.id, "name": i.name, "description": i.description} for i in initiatives]

    # Search Systems
    systems = System.query.filter(
        System.organization_id == org_id,
        db.or_(System.name.ilike(search_pattern), System.description.ilike(search_pattern)),
    ).all()
    results["systems"] = [{"id": s.id, "name": s.name, "description": s.description} for s in systems]

    # Search KPIs
    kpis = (
        db.session.query(KPI)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(
            Initiative.organization_id == org_id,
            db.or_(KPI.name.ilike(search_pattern), KPI.description.ilike(search_pattern)),
        )
        .all()
    )
    results["kpis"] = [
        {
            "id": k.id,
            "name": k.name,
            "description": k.description,
            "initiative": k.initiative_system_link.initiative.name if k.initiative_system_link else "",
            "system": k.initiative_system_link.system.name if k.initiative_system_link else "",
        }
        for k in kpis
    ]

    # Search Value Types
    value_types = ValueType.query.filter(
        ValueType.organization_id == org_id,
        db.or_(ValueType.name.ilike(search_pattern), ValueType.unit_label.ilike(search_pattern)),
    ).all()
    results["value_types"] = [
        {"id": v.id, "name": v.name, "unit_label": v.unit_label, "kind": v.kind} for v in value_types
    ]

    # Search Comments
    comments = (
        db.session.query(CellComment)
        .join(KPIValueTypeConfig)
        .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(Initiative.organization_id == org_id, CellComment.comment_text.ilike(search_pattern))
        .limit(50)
        .all()
    )
    results["comments"] = [
        {
            "id": c.id,
            "text": c.comment_text[:200],
            "user": c.user.display_name if c.user else "Unknown",
            "kpi": c.config.kpi.name if c.config and c.config.kpi else "Unknown",
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "",
        }
        for c in comments
    ]

    # Count totals
    total = sum(len(results[key]) for key in results)

    return render_template(
        "workspace/search.html", organization_name=org_name, query=query, results=results, total=total
    )


@bp.route("/api/search/live")
@login_required
@organization_required
def live_search():
    """Live search API endpoint - returns JSON results as user types"""
    org_id = session.get("organization_id")
    query = request.args.get("q", "").strip()

    if not query or len(query) < 2:
        return jsonify({"results": []})

    search_pattern = f"%{query}%"
    results = []

    # Limit to top 3 of each type for quick display
    limit = 3

    # Search Spaces
    spaces = (
        Space.query.filter(
            Space.organization_id == org_id,
            db.or_(Space.name.ilike(search_pattern), Space.description.ilike(search_pattern)),
        )
        .limit(limit)
        .all()
    )

    for s in spaces:
        results.append(
            {
                "type": "space",
                "id": s.id,
                "name": s.name,
                "description": s.description[:100] if s.description else None,
                "url": url_for("workspace.index", _anchor=f"space-{s.id}"),
                "edit_url": url_for("organization_admin.edit_space", space_id=s.id),
            }
        )

    # Search Challenges
    challenges = (
        Challenge.query.join(Space)
        .filter(
            Space.organization_id == org_id,
            db.or_(Challenge.name.ilike(search_pattern), Challenge.description.ilike(search_pattern)),
        )
        .limit(limit)
        .all()
    )

    for c in challenges:
        results.append(
            {
                "type": "challenge",
                "id": c.id,
                "name": c.name,
                "description": c.description[:100] if c.description else None,
                "space": c.space.name,
                "url": url_for("workspace.index", _anchor=f"challenge-{c.id}"),
                "edit_url": url_for("organization_admin.edit_challenge", challenge_id=c.id),
            }
        )

    # Search Initiatives
    initiatives = (
        Initiative.query.filter(
            Initiative.organization_id == org_id,
            db.or_(Initiative.name.ilike(search_pattern), Initiative.description.ilike(search_pattern)),
        )
        .limit(limit)
        .all()
    )

    for i in initiatives:
        results.append(
            {
                "type": "initiative",
                "id": i.id,
                "name": i.name,
                "description": i.description[:100] if i.description else None,
                "url": url_for("workspace.index", _anchor=f"initiative-{i.id}"),
                "edit_url": url_for("organization_admin.edit_initiative", initiative_id=i.id),
            }
        )

    # Search Systems
    systems = (
        System.query.filter(
            System.organization_id == org_id,
            db.or_(System.name.ilike(search_pattern), System.description.ilike(search_pattern)),
        )
        .limit(limit)
        .all()
    )

    for s in systems:
        results.append(
            {
                "type": "system",
                "id": s.id,
                "name": s.name,
                "description": s.description[:100] if s.description else None,
                "url": url_for("workspace.index", _anchor=f"system-{s.id}"),
                "edit_url": url_for("organization_admin.edit_system", system_id=s.id),
            }
        )

    # Search KPIs
    kpis = (
        db.session.query(KPI)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(
            Initiative.organization_id == org_id,
            db.or_(KPI.name.ilike(search_pattern), KPI.description.ilike(search_pattern)),
        )
        .limit(limit)
        .all()
    )

    for k in kpis:
        results.append(
            {
                "type": "kpi",
                "id": k.id,
                "name": k.name,
                "description": k.description[:100] if k.description else None,
                "initiative": k.initiative_system_link.initiative.name if k.initiative_system_link else None,
                "system": k.initiative_system_link.system.name if k.initiative_system_link else None,
                "url": url_for("workspace.index", _anchor=f"kpi-{k.id}"),
                "edit_url": url_for("organization_admin.edit_kpi", kpi_id=k.id),
            }
        )

    return jsonify({"results": results, "total": len(results)})


@bp.route("/api/kpi/<int:kpi_id>/status")
@login_required
@organization_required
def get_kpi_status(kpi_id):
    """
    Get traffic light status for a KPI.

    Returns JSON with status (green/yellow/red), reason, and details.
    """
    try:
        # Verify KPI belongs to current organization
        kpi = (
            KPI.query.join(InitiativeSystemLink)
            .join(System)
            .filter(KPI.id == kpi_id, System.organization_id == session.get("organization_id"))
            .first_or_404()
        )

        status_data = kpi.get_status()

        return jsonify(
            {
                "kpi_id": kpi.id,
                "kpi_name": kpi.name,
                "status": status_data["status"],
                "reason": status_data["reason"],
                "details": status_data["details"],
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/kpis/statuses")
@login_required
@organization_required
def get_all_kpi_statuses():
    """
    Get traffic light statuses for all KPIs in the organization.

    Returns JSON with array of {kpi_id, kpi_name, status, reason, details}.
    Useful for dashboard displays.
    """
    try:
        org_id = session.get("organization_id")

        # Get all KPIs for this organization
        kpis = (
            KPI.query.join(InitiativeSystemLink)
            .join(System)
            .filter(System.organization_id == org_id)
            .order_by(KPI.name)
            .all()
        )

        results = []
        for kpi in kpis:
            status_data = kpi.get_status()
            results.append(
                {
                    "kpi_id": kpi.id,
                    "kpi_name": kpi.name,
                    "status": status_data["status"],
                    "reason": status_data["reason"],
                    "details": status_data["details"],
                    "is_archived": kpi.is_archived,
                }
            )

        # Count by status
        status_counts = {"green": 0, "yellow": 0, "red": 0}
        for result in results:
            status_counts[result["status"]] += 1

        return jsonify({"kpis": results, "summary": status_counts, "total": len(results)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/value-types/reorder", methods=["POST"])
@login_required
@organization_required
def reorder_value_types():
    """Update display order of value types via drag-and-drop"""
    try:
        org_id = session.get("organization_id")
        data = request.get_json()

        if not data or "value_type_ids" not in data:
            return jsonify({"error": "Missing value_type_ids"}), 400

        value_type_ids = data["value_type_ids"]

        # Update display_order for each value type
        for index, vt_id in enumerate(value_type_ids):
            vt = ValueType.query.filter_by(id=vt_id, organization_id=org_id).first()
            if vt:
                vt.display_order = index

        db.session.commit()

        return jsonify({"success": True, "message": "Value type order updated"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/reorder/<entity_type>", methods=["POST"])
@login_required
@organization_required
def reorder_rows(entity_type):
    """Update display order of rows (spaces, challenges, initiatives, systems, KPIs) via drag-and-drop"""
    try:
        org_id = session.get("organization_id")
        data = request.get_json()

        if not data or "ids" not in data:
            return jsonify({"error": "Missing ids"}), 400

        ids = data["ids"]
        parent_id = data.get("parent_id")

        # Route to appropriate handler based on entity type
        if entity_type == "space":
            _reorder_spaces(org_id, ids)
        elif entity_type == "challenge":
            _reorder_challenges(org_id, ids, parent_id)
        elif entity_type == "initiative":
            _reorder_initiatives(org_id, ids, parent_id)
        elif entity_type == "system":
            _reorder_systems(org_id, ids, parent_id)
        elif entity_type == "kpi":
            _reorder_kpis(org_id, ids, parent_id)
        else:
            return jsonify({"error": f"Unknown entity type: {entity_type}"}), 400

        db.session.commit()
        return jsonify({"success": True, "message": f"{entity_type.capitalize()} order updated"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


def _reorder_spaces(org_id, space_ids):
    """Reorder spaces within an organization"""
    from app.models import Space

    for index, space_id in enumerate(space_ids):
        space = Space.query.filter_by(id=space_id, organization_id=org_id).first()
        if space:
            space.display_order = index


def _reorder_challenges(org_id, challenge_ids, parent_space_id):
    """Reorder challenges within a space"""
    from app.models import Challenge

    for index, challenge_id in enumerate(challenge_ids):
        challenge = Challenge.query.filter_by(id=challenge_id, space_id=parent_space_id, organization_id=org_id).first()
        if challenge:
            challenge.display_order = index


def _reorder_initiatives(org_id, link_ids, parent_challenge_id):
    """Reorder initiatives within a challenge (by updating ChallengeInitiativeLink)"""
    from app.models import ChallengeInitiativeLink

    for index, link_id in enumerate(link_ids):
        link = ChallengeInitiativeLink.query.filter_by(id=link_id, challenge_id=parent_challenge_id).first()
        if link:
            link.display_order = index


def _reorder_systems(org_id, link_ids, parent_initiative_id):
    """Reorder systems within an initiative (by updating InitiativeSystemLink)"""
    from app.models import InitiativeSystemLink

    for index, link_id in enumerate(link_ids):
        link = InitiativeSystemLink.query.filter_by(id=link_id, initiative_id=parent_initiative_id).first()
        if link:
            link.display_order = index


def _reorder_kpis(org_id, kpi_ids, parent_link_id):
    """Reorder KPIs within a system (within an InitiativeSystemLink)"""
    from app.models import KPI

    for index, kpi_id in enumerate(kpi_ids):
        kpi = KPI.query.filter_by(id=kpi_id, initiative_system_link_id=parent_link_id).first()
        if kpi:
            kpi.display_order = index


@bp.route("/api/linked-kpi/organizations")
@login_required
def api_get_organizations_for_linking():
    """Get list of organizations user has access to for linking KPIs"""
    from app.models import Organization

    # Get all orgs where user has membership
    user_org_ids = [m.organization_id for m in current_user.memberships]
    orgs = Organization.query.filter(Organization.id.in_(user_org_ids)).filter_by(is_deleted=False).all()

    return jsonify(
        [
            {
                "id": org.id,
                "name": org.name,
            }
            for org in orgs
        ]
    )


@bp.route("/api/linked-kpi/kpis/<int:org_id>")
@login_required
def api_get_kpis_for_linking(org_id):
    """Get list of KPIs from an organization for linking"""
    # Verify user has access to this org
    has_access = any(m.organization_id == org_id for m in current_user.memberships)
    if not has_access:
        return jsonify({"error": "Access denied"}), 403

    # Get all KPIs from this org with full hierarchy context (not archived)
    kpis = (
        db.session.query(KPI)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(Initiative.organization_id == org_id)
        .filter_by(is_archived=False)
        .join(ChallengeInitiativeLink)
        .join(Challenge)
        .join(Space)
        .all()
    )

    result = []
    for kpi in kpis:
        is_link = kpi.initiative_system_link
        initiative = is_link.initiative
        system = is_link.system

        # Get challenges
        challenges = [ci_link.challenge.name for ci_link in initiative.challenge_links]
        # Get space
        spaces = list(set([ci_link.challenge.space.name for ci_link in initiative.challenge_links]))

        result.append(
            {
                "id": kpi.id,
                "name": kpi.name,
                "system": system.name,
                "initiative": initiative.name,
                "challenges": ", ".join(challenges),
                "spaces": ", ".join(spaces),
                "full_path": f"{', '.join(spaces)} → {', '.join(challenges)} → {initiative.name} → {system.name} → {kpi.name}",
            }
        )

    return jsonify(result)


@bp.route("/api/linked-kpi/value-types/<int:kpi_id>")
@login_required
def api_get_value_types_for_linking(kpi_id):
    """Get list of value types from a KPI for linking"""
    kpi = KPI.query.get_or_404(kpi_id)

    # Verify user has access to this KPI's org
    org_id = kpi.initiative_system_link.initiative.organization_id
    has_access = any(m.organization_id == org_id for m in current_user.memberships)
    if not has_access:
        return jsonify({"error": "Access denied"}), 403

    result = []
    for config in kpi.value_type_configs:
        vt = config.value_type
        result.append(
            {
                "id": vt.id,
                "name": vt.name,
                "kind": vt.kind,
                "unit_label": vt.unit_label,
                "display": f"{vt.name}" + (f" ({vt.unit_label})" if vt.unit_label else ""),
            }
        )

    return jsonify(result)
