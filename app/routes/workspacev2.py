"""
Workspace V2 - Fully Reactive Alpine.js Implementation
========================================================
Beta feature with in-memory filtering, drag-and-drop, and reactive updates.
"""

import base64

from flask import Blueprint, jsonify, render_template, request, session
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf
from sqlalchemy import or_

from app.extensions import db
from app.models import (
    KPI,
    Challenge,
    ChallengeInitiativeLink,
    GovernanceBody,
    Initiative,
    InitiativeSystemLink,
    Space,
    SystemSetting,
    ValueType,
)

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
    if not current_user.is_global_admin and not current_user.is_super_admin and not current_user.is_org_admin(org_id):
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

                        # Get KPI logo
                        kpi_logo_url = None
                        if kpi.logo_data and kpi.logo_mime_type:
                            kpi_logo_url = (
                                f"data:{kpi.logo_mime_type};base64,{base64.b64encode(kpi.logo_data).decode('utf-8')}"
                            )

                        kpis_data.append(
                            {
                                "id": kpi.id,
                                "name": kpi.name,
                                "display_order": kpi.display_order,
                                "logo_url": kpi_logo_url,
                                "values": kpi_values,
                            }
                        )

                    # Get system logo
                    system_logo_url = None
                    if system.logo_data and system.logo_mime_type:
                        system_logo_url = (
                            f"data:{system.logo_mime_type};base64,{base64.b64encode(system.logo_data).decode('utf-8')}"
                        )

                    systems_data.append(
                        {
                            "id": system.id,
                            "link_id": sys_link.id,  # For parent change operations
                            "name": system.name,
                            "logo_url": system_logo_url,
                            "rollup_values": system_rollup_values,
                            "kpis": kpis_data,
                        }
                    )

                # Get initiative logo
                initiative_logo_url = None
                if initiative.logo_data and initiative.logo_mime_type:
                    initiative_logo_url = f"data:{initiative.logo_mime_type};base64,{base64.b64encode(initiative.logo_data).decode('utf-8')}"

                initiatives_data.append(
                    {
                        "id": initiative.id,
                        "link_id": link.id,  # For parent change operations
                        "name": initiative.name,
                        "logo_url": initiative_logo_url,
                        "group_label": initiative.group_label,
                        "impact_on_challenge": initiative.impact_on_challenge,
                        "rollup_values": initiative_rollup_values,
                        "systems": systems_data,
                    }
                )

            # Get challenge logo
            challenge_logo_url = None
            if challenge.logo_data and challenge.logo_mime_type:
                challenge_logo_url = (
                    f"data:{challenge.logo_mime_type};base64,{base64.b64encode(challenge.logo_data).decode('utf-8')}"
                )

            challenges_data.append(
                {
                    "id": challenge.id,
                    "name": challenge.name,
                    "logo_url": challenge_logo_url,
                    "display_order": challenge.display_order,
                    "rollup_values": challenge_rollup_values,
                    "initiatives": initiatives_data,
                }
            )

        # Get space logo
        space_logo_url = None
        if space.logo_data and space.logo_mime_type:
            space_logo_url = f"data:{space.logo_mime_type};base64,{base64.b64encode(space.logo_data).decode('utf-8')}"

        spaces_data.append(
            {
                "id": space.id,
                "name": space.name,
                "logo_url": space_logo_url,
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


@bp.route("/api/change-parent/<entity_type>", methods=["POST"])
@login_required
@beta_required
def change_parent(entity_type):
    """Change the parent of an entity (move to different parent)"""
    try:
        org_id = session.get("organization_id")
        data = request.get_json()

        entity_id = data.get("entity_id")
        new_parent_id = data.get("new_parent_id")

        if not entity_id or not new_parent_id:
            return jsonify({"error": "Missing entity_id or new_parent_id"}), 400

        if entity_type == "challenge":
            # Move challenge to different space
            challenge = Challenge.query.filter_by(id=entity_id, organization_id=org_id).first()
            if not challenge:
                return jsonify({"error": "Challenge not found"}), 404

            challenge.space_id = new_parent_id

        elif entity_type == "initiative":
            # Move initiative to different challenge
            link = ChallengeInitiativeLink.query.filter_by(id=entity_id).first()
            if not link or link.initiative.organization_id != org_id:
                return jsonify({"error": "Initiative link not found"}), 404

            link.challenge_id = new_parent_id

        elif entity_type == "system":
            # Move system to different initiative
            link = InitiativeSystemLink.query.filter_by(id=entity_id).first()
            if not link or link.system.organization_id != org_id:
                return jsonify({"error": "System link not found"}), 404

            link.initiative_id = new_parent_id

        elif entity_type == "kpi":
            # Move KPI to different system (system is a link)
            kpi = KPI.query.filter_by(id=entity_id).first()
            if not kpi:
                return jsonify({"error": "KPI not found"}), 404

            # Verify ownership through system link
            old_link = InitiativeSystemLink.query.get(kpi.initiative_system_link_id)
            if not old_link or old_link.system.organization_id != org_id:
                return jsonify({"error": "Unauthorized"}), 403

            # new_parent_id is the InitiativeSystemLink id
            kpi.initiative_system_link_id = new_parent_id

        else:
            return jsonify({"error": f"Unknown entity type: {entity_type}"}), 400

        db.session.commit()
        return jsonify({"success": True, "message": f"{entity_type.capitalize()} parent changed"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
