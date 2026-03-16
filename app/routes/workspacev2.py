"""
Workspace V2 - Fully Reactive Alpine.js Implementation
========================================================
Beta feature with in-memory filtering, drag-and-drop, and reactive updates.
"""

from flask import Blueprint, jsonify, render_template, session
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf
from sqlalchemy import or_

from app.extensions import db
from app.models import GovernanceBody, Initiative, Space, SystemSetting, ValueType

bp = Blueprint("workspacev2", __name__, url_prefix="/workspacev2")


def beta_required(f):
    """Decorator to require beta access"""
    from functools import wraps

    from flask import flash, redirect, url_for

    @wraps(f)
    def decorated_function(*args, **kwargs):
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
    """Workspace V2 - Fully reactive Alpine.js interface"""
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

    return render_template(
        "workspacev2/index.html",
        org_name=org_name,
        org_id=org_id,
        csrf_token=generate_csrf,
    )


@bp.route("/data")
@login_required
@beta_required
def get_data():
    """
    API endpoint that returns ALL workspace data as JSON for Alpine.js to handle

    Returns:
    {
        "spaces": [...],
        "valueTypes": [...],
        "governanceBodies": [...],
        "groups": [...],
        "impactLevels": [...]
    }
    """
    org_id = session.get("organization_id")

    # Get spaces with privacy filtering
    spaces_query = Space.query.filter_by(organization_id=org_id)
    if (
        not current_user.is_global_admin
        and not current_user.is_super_admin
        and not current_user.is_org_admin(org_id)
    ):
        spaces_query = spaces_query.filter(or_(Space.is_private.is_(False), Space.created_by == current_user.id))

    spaces = spaces_query.order_by(Space.display_order, Space.name).all()

    # Get value types
    value_types = (
        ValueType.query.filter_by(organization_id=org_id, is_active=True).order_by(ValueType.display_order).all()
    )

    # Get governance bodies
    governance_bodies = (
        GovernanceBody.query.filter_by(organization_id=org_id, is_active=True)
        .order_by(GovernanceBody.display_order)
        .all()
    )

    # Build full hierarchical tree: Spaces → Challenges → Initiatives → Systems → KPIs
    spaces_data = []
    for space in spaces:
        # Get space rollup values
        space_rollup_values = {}
        for vt in value_types:
            rollup_data = space.get_rollup_value(vt.id)
            if rollup_data:
                space_rollup_values[vt.id] = {
                    "value": rollup_data.get("value"),
                    "formatted_value": rollup_data.get("formatted_value"),
                    "unit_label": vt.unit_label,
                    "color": rollup_data.get("color", "#6c757d"),
                }

        challenges_data = []
        for challenge in space.challenges:
            # Get challenge rollup values
            challenge_rollup_values = {}
            for vt in value_types:
                rollup_data = challenge.get_rollup_value(vt.id)
                if rollup_data:
                    challenge_rollup_values[vt.id] = {
                        "value": rollup_data.get("value"),
                        "formatted_value": rollup_data.get("formatted_value"),
                        "unit_label": vt.unit_label,
                        "color": rollup_data.get("color", "#6c757d"),
                    }

            # Get initiatives under this challenge
            initiatives_data = []
            for link in challenge.initiative_links:
                initiative = link.initiative

                # Get initiative rollup values
                initiative_rollup_values = {}
                for vt in value_types:
                    rollup_data = initiative.get_rollup_value(vt.id)
                    if rollup_data:
                        initiative_rollup_values[vt.id] = {
                            "value": rollup_data.get("value"),
                            "formatted_value": rollup_data.get("formatted_value"),
                            "unit_label": vt.unit_label,
                            "color": rollup_data.get("color", "#6c757d"),
                        }

                # Get systems under this initiative
                systems_data = []
                for sys_link in initiative.system_links:
                    system = sys_link.system

                    # Get system rollup values
                    system_rollup_values = {}
                    for vt in value_types:
                        rollup_data = sys_link.get_rollup_value(vt.id)
                        if rollup_data:
                            system_rollup_values[vt.id] = {
                                "value": rollup_data.get("value"),
                                "formatted_value": rollup_data.get("formatted_value"),
                                "unit_label": vt.unit_label,
                                "color": rollup_data.get("color", "#6c757d"),
                            }

                    # Get KPIs under this system
                    kpis_data = []
                    for kpi in sys_link.kpis:
                        if kpi.is_archived:
                            continue

                        # Get KPI values
                        kpi_values = {}
                        for vt in value_types:
                            # Find config for this value type
                            config = next((c for c in kpi.value_type_configs if c.value_type_id == vt.id), None)
                            if config:
                                consensus = config.get_consensus_value()
                                if consensus:
                                    kpi_values[vt.id] = {
                                        "value": consensus.get("value"),
                                        "formatted_value": consensus.get("formatted_value"),
                                        "unit_label": vt.unit_label,
                                        "color": config.get_value_color(consensus.get("value")),
                                    }

                        kpis_data.append(
                            {
                                "id": kpi.id,
                                "name": kpi.name,
                                "display_order": kpi.display_order,
                                "values": kpi_values,
                            }
                        )

                    systems_data.append(
                        {
                            "id": system.id,
                            "name": system.name,
                            "rollup_values": system_rollup_values,
                            "kpis": kpis_data,
                        }
                    )

                initiatives_data.append(
                    {
                        "id": initiative.id,
                        "name": initiative.name,
                        "group_label": initiative.group_label,
                        "impact_on_challenge": initiative.impact_on_challenge,
                        "rollup_values": initiative_rollup_values,
                        "systems": systems_data,
                    }
                )

            challenges_data.append(
                {
                    "id": challenge.id,
                    "name": challenge.name,
                    "display_order": challenge.display_order,
                    "rollup_values": challenge_rollup_values,
                    "initiatives": initiatives_data,
                }
            )

        spaces_data.append(
            {
                "id": space.id,
                "name": space.name,
                "display_order": space.display_order,
                "is_private": space.is_private,
                "rollup_values": space_rollup_values,
                "challenges": challenges_data,
            }
        )

    # Build value types data
    value_types_data = [
        {
            "id": vt.id,
            "name": vt.name,
            "display_order": vt.display_order,
            "unit_label": vt.unit_label,
            "kind": vt.kind,
        }
        for vt in value_types
    ]

    # Build governance bodies data
    governance_bodies_data = [{"id": gb.id, "name": gb.name} for gb in governance_bodies]

    # Get unique initiative groups
    groups = (
        db.session.query(Initiative.group_label)
        .filter(Initiative.organization_id == org_id, Initiative.group_label.isnot(None))
        .distinct()
        .all()
    )
    groups_data = [g[0] for g in groups]

    # Impact levels
    impact_levels_data = [
        {"value": "not_assessed", "label": "Not Assessed"},
        {"value": "low", "label": "Low"},
        {"value": "medium", "label": "Medium"},
        {"value": "high", "label": "High"},
        {"value": "no_consensus", "label": "No Consensus"},
    ]

    return jsonify(
        {
            "spaces": spaces_data,
            "valueTypes": value_types_data,
            "governanceBodies": governance_bodies_data,
            "groups": groups_data,
            "impactLevels": impact_levels_data,
        }
    )
