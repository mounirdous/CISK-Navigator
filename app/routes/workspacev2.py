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
    EntityTypeDefault,
    GovernanceBody,
    Initiative,
    InitiativeSystemLink,
    Organization,
    Space,
    System,
    SystemSetting,
    UserFilterPreset,
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

    # Get organization for logo and Porter's completion
    org = Organization.query.get(org_id)
    org_logo = None
    porters_completion = None
    if org:
        if org.logo_data:
            org_logo = f"data:{org.logo_mime_type};base64,{base64.b64encode(org.logo_data).decode('utf-8')}"

        # Get Porter's Five Forces completion
        filled, total, status = org.get_porters_completion()
        porters_completion = {"filled": filled, "total": total, "status": status}

    # Get filter presets for this user (from database, not localStorage)
    filter_presets = (
        UserFilterPreset.query.filter_by(user_id=current_user.id, organization_id=org_id)
        .order_by(UserFilterPreset.name)
        .all()
    )

    return render_template(
        "workspacev2/index.html",
        org_name=org_name,
        org_id=org_id,
        organization=org,
        org_logo=org_logo,
        porters_completion=porters_completion,
        filter_presets=filter_presets,
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

    # Get entity type defaults for logo fallbacks
    entity_defaults = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
    default_logos = {}
    for default in entity_defaults:
        if default.default_logo_data and default.default_logo_mime_type:
            default_logos[default.entity_type] = (
                f"data:{default.default_logo_mime_type};base64,"
                f"{base64.b64encode(default.default_logo_data).decode('utf-8')}"
            )

    # Helper function to get logo URL for an entity
    def get_logo_url(entity, entity_type):
        """Get logo URL - entity's own logo or default logo for the type"""
        if (
            hasattr(entity, "logo_data")
            and entity.logo_data
            and hasattr(entity, "logo_mime_type")
            and entity.logo_mime_type
        ):
            return f"data:{entity.logo_mime_type};base64,{base64.b64encode(entity.logo_data).decode('utf-8')}"
        return default_logos.get(entity_type)

    # Helper function to get entity links
    from app.models import EntityLink

    def get_entity_links(entity_type, entity_id):
        """Get all links for a specific entity"""
        links = (
            EntityLink.query.filter_by(entity_type=entity_type, entity_id=entity_id)
            .order_by(EntityLink.display_order)
            .all()
        )
        result = []
        for link in links:
            result.append(
                {
                    "id": link.id,
                    "title": link.title,
                    "url": link.url,
                    "icon": link.get_display_icon(),
                }
            )
        return result

    # Build full hierarchical tree: Spaces → Challenges → Initiatives → Systems → KPIs
    spaces_data = []
    for space in spaces:
        # Get space rollup values
        space_rollup_values = {}
        for vt in value_types:
            rollup_data = space.get_rollup_value(vt.id)
            if rollup_data and rollup_data.get("value") is not None:
                # Get color config for formatting
                color_config = space.get_color_config(vt.id)

                # Format the value using the Jinja filter
                from flask import current_app

                formatted_value = current_app.jinja_env.filters["format_value"](
                    rollup_data.get("value"), vt, color_config
                )

                # Get color from config
                if color_config and hasattr(color_config, "get_value_color"):
                    color = color_config.get_value_color(rollup_data.get("value"))
                else:
                    # Use default color filter
                    color = current_app.jinja_env.filters["default_value_color"](rollup_data.get("value"))

                space_rollup_values[vt.id] = {
                    "value": rollup_data.get("value"),
                    "formatted_value": formatted_value,
                    "unit_label": vt.unit_label,
                    "color": color or "#6c757d",
                    "formula": rollup_data.get("formula"),
                    "is_complete": rollup_data.get("is_complete", False),
                }

        # Get space SWOT completion
        swot_filled, swot_total, swot_status = space.get_swot_completion()
        swot_completion = {
            "filled": swot_filled,
            "total": swot_total,
            "status": swot_status,  # 'empty', 'partial', 'complete'
        }

        # Get space entity links
        space_entity_links = get_entity_links("space", space.id)

        challenges_data = []
        for challenge in space.challenges:
            # Get challenge rollup values
            challenge_rollup_values = {}
            for vt in value_types:
                rollup_data = challenge.get_rollup_value(vt.id)
                if rollup_data and rollup_data.get("value") is not None:
                    color_config = challenge.get_color_config(vt.id)
                    from flask import current_app

                    formatted_value = current_app.jinja_env.filters["format_value"](
                        rollup_data.get("value"), vt, color_config
                    )
                    if color_config and hasattr(color_config, "get_value_color"):
                        color = color_config.get_value_color(rollup_data.get("value"))
                    else:
                        color = current_app.jinja_env.filters["default_value_color"](rollup_data.get("value"))

                    challenge_rollup_values[vt.id] = {
                        "value": rollup_data.get("value"),
                        "formatted_value": formatted_value,
                        "unit_label": vt.unit_label,
                        "color": color or "#6c757d",
                        "formula": rollup_data.get("formula"),
                        "is_complete": rollup_data.get("is_complete", False),
                    }

            # Get challenge entity links
            challenge_entity_links = get_entity_links("challenge", challenge.id)

            # Get initiatives under this challenge
            initiatives_data = []
            for link in challenge.initiative_links:
                initiative = link.initiative

                # Get initiative rollup values
                initiative_rollup_values = {}
                for vt in value_types:
                    rollup_data = initiative.get_rollup_value(vt.id)
                    if rollup_data and rollup_data.get("value") is not None:
                        color_config = initiative.get_color_config(vt.id)
                        from flask import current_app

                        formatted_value = current_app.jinja_env.filters["format_value"](
                            rollup_data.get("value"), vt, color_config
                        )
                        if color_config and hasattr(color_config, "get_value_color"):
                            color = color_config.get_value_color(rollup_data.get("value"))
                        else:
                            color = current_app.jinja_env.filters["default_value_color"](rollup_data.get("value"))

                        initiative_rollup_values[vt.id] = {
                            "value": rollup_data.get("value"),
                            "formatted_value": formatted_value,
                            "unit_label": vt.unit_label,
                            "color": color or "#6c757d",
                            "formula": rollup_data.get("formula"),
                            "is_complete": rollup_data.get("is_complete", False),
                        }

                # Get initiative form completion
                form_filled, form_total, form_status = initiative.get_form_completion()
                form_completion = {
                    "filled": form_filled,
                    "total": form_total,
                    "status": form_status,  # 'empty', 'partial', 'complete'
                }

                # Get initiative entity links
                initiative_entity_links = get_entity_links("initiative", initiative.id)

                # Get systems under this initiative
                systems_data = []
                for sys_link in initiative.system_links:
                    system = sys_link.system

                    # Get system rollup values
                    system_rollup_values = {}
                    for vt in value_types:
                        rollup_data = sys_link.get_rollup_value(vt.id)
                        if rollup_data and rollup_data.get("value") is not None:
                            color_config = sys_link.get_color_config(vt.id)
                            from flask import current_app

                            formatted_value = current_app.jinja_env.filters["format_value"](
                                rollup_data.get("value"), vt, color_config
                            )
                            if color_config and hasattr(color_config, "get_value_color"):
                                color = color_config.get_value_color(rollup_data.get("value"))
                            else:
                                color = current_app.jinja_env.filters["default_value_color"](rollup_data.get("value"))

                            system_rollup_values[vt.id] = {
                                "value": rollup_data.get("value"),
                                "formatted_value": formatted_value,
                                "unit_label": vt.unit_label,
                                "color": color or "#6c757d",
                                "formula": rollup_data.get("formula"),
                                "is_complete": rollup_data.get("is_complete", False),
                            }

                    # Get system entity links
                    system_entity_links = get_entity_links("system", system.id)

                    # Get KPIs under this system
                    kpis_data = []
                    for kpi in sys_link.kpis:
                        # Get KPI values with full details for rendering
                        kpi_values = {}
                        for vt in value_types:
                            # Find config for this value type
                            config = next((c for c in kpi.value_type_configs if c.value_type_id == vt.id), None)
                            if config:
                                consensus = config.get_consensus_value()

                                # Calculate target progress if target exists
                                target_progress = None
                                target_color = None
                                if config.target_value is not None and consensus and consensus.get("value") is not None:
                                    target_dir = config.target_direction or "maximize"
                                    target_val = float(config.target_value)
                                    current_val = float(consensus.get("value"))

                                    if target_dir == "minimize":
                                        progress = int((target_val / current_val) * 100) if current_val != 0 else 100
                                    elif target_dir == "exact":
                                        tolerance = target_val * (config.target_tolerance_pct or 10) / 100
                                        diff = abs(current_val - target_val)
                                        if diff <= tolerance:
                                            progress = 100
                                        else:
                                            progress = max(0, int(100 - ((diff - tolerance) / target_val * 100)))
                                    else:  # maximize
                                        progress = int((current_val / target_val) * 100)

                                    target_progress = progress
                                    if progress >= 90:
                                        target_color = "#28a745"
                                    elif progress >= 60:
                                        target_color = "#ffc107"
                                    else:
                                        target_color = "#dc3545"

                                # Format the value using config settings
                                formatted_value = None
                                if consensus and consensus.get("value") is not None:
                                    from flask import current_app

                                    formatted_value = current_app.jinja_env.filters["format_value"](
                                        consensus.get("value"), vt, config
                                    )

                                kpi_values[vt.id] = {
                                    "config_id": config.id,
                                    "value": consensus.get("value") if consensus else None,
                                    "formatted_value": formatted_value,
                                    "unit_label": vt.unit_label,
                                    "color": config.get_value_color(consensus.get("value")) if consensus else None,
                                    "calculation_type": config.calculation_type,
                                    "consensus_status": consensus.get("status") if consensus else "no_data",
                                    "consensus_count": consensus.get("count") if consensus else 0,
                                    "has_target": config.target_value is not None,
                                    "target_value": config.target_value,
                                    "target_date": (
                                        config.target_date.strftime("%Y-%m-%d") if config.target_date else None
                                    ),
                                    "target_direction": (
                                        config.target_direction or "maximize" if config.target_value else None
                                    ),
                                    "target_progress": target_progress,
                                    "target_color": target_color,
                                }

                        # Get governance body info (full details for badges)
                        governance_bodies_data = []
                        for gb_link in kpi.governance_body_links:
                            governance_bodies_data.append(
                                {
                                    "id": gb_link.governance_body.id,
                                    "name": gb_link.governance_body.name,
                                    "abbreviation": gb_link.governance_body.abbreviation,
                                    "color": gb_link.governance_body.color,
                                }
                            )

                        # Get target direction from configs (if any has a target)
                        target_direction = None
                        for config in kpi.value_type_configs:
                            if config.target_value is not None:
                                target_direction = config.target_direction or "maximize"
                                break

                        # Check if KPI has linked sources
                        has_linked_sources = any(config.linked_source_kpi_id for config in kpi.value_type_configs)

                        # Get KPI entity links
                        kpi_entity_links = get_entity_links("kpi", kpi.id)

                        kpis_data.append(
                            {
                                "id": kpi.id,
                                "name": kpi.name,
                                "display_order": kpi.display_order,
                                "logo_url": get_logo_url(kpi, "kpi"),
                                "values": kpi_values,
                                "is_archived": kpi.is_archived,
                                "archived_at": kpi.archived_at.strftime("%Y-%m-%d") if kpi.archived_at else None,
                                "governance_bodies": governance_bodies_data,
                                "target_direction": target_direction,
                                "has_linked_sources": has_linked_sources,
                                "entity_links": kpi_entity_links,
                            }
                        )

                    systems_data.append(
                        {
                            "id": system.id,
                            "link_id": sys_link.id,  # For parent change operations
                            "name": system.name,
                            "logo_url": get_logo_url(system, "system"),
                            "rollup_values": system_rollup_values,
                            "entity_links": system_entity_links,
                            "kpis": kpis_data,
                        }
                    )

                initiatives_data.append(
                    {
                        "id": initiative.id,
                        "link_id": link.id,  # For parent change operations
                        "name": initiative.name,
                        "logo_url": get_logo_url(initiative, "initiative"),
                        "group_label": initiative.group_label,
                        "impact_on_challenge": initiative.impact_on_challenge,
                        "rollup_values": initiative_rollup_values,
                        "form_completion": form_completion,
                        "entity_links": initiative_entity_links,
                        "systems": systems_data,
                    }
                )

            challenges_data.append(
                {
                    "id": challenge.id,
                    "name": challenge.name,
                    "logo_url": get_logo_url(challenge, "challenge"),
                    "display_order": challenge.display_order,
                    "rollup_values": challenge_rollup_values,
                    "entity_links": challenge_entity_links,
                    "initiatives": initiatives_data,
                }
            )

        spaces_data.append(
            {
                "id": space.id,
                "name": space.name,
                "logo_url": get_logo_url(space, "space"),
                "display_order": space.display_order,
                "is_private": space.is_private,
                "space_label": space.space_label,
                "rollup_values": space_rollup_values,
                "swot_completion": swot_completion,
                "entity_links": space_entity_links,
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


@bp.route("/api/action-items-count")
@login_required
@beta_required
def get_action_items_count():
    """Get count of action items requiring attention"""
    org_id = session.get("organization_id")

    # Get initiatives with no consensus
    initiatives_no_consensus = Initiative.query.filter_by(
        organization_id=org_id, impact_on_challenge="no_consensus"
    ).count()

    # Get initiatives with incomplete forms
    all_initiatives = Initiative.query.filter_by(organization_id=org_id).all()
    initiatives_incomplete = 0
    for initiative in all_initiatives:
        filled, total, status = initiative.get_form_completion()
        if status != "complete":
            initiatives_incomplete += 1

    # Get spaces without SWOT (empty or partial)
    all_spaces = Space.query.filter_by(organization_id=org_id).all()
    spaces_no_swot = 0
    for space in all_spaces:
        filled, total, status = space.get_swot_completion()
        if status != "complete":
            spaces_no_swot += 1

    # Get systems without KPIs
    systems_without_kpis = (
        db.session.query(System)
        .join(InitiativeSystemLink, System.id == InitiativeSystemLink.system_id)
        .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
        .outerjoin(KPI, InitiativeSystemLink.id == KPI.initiative_system_link_id)
        .filter(Initiative.organization_id == org_id, KPI.id.is_(None))
        .distinct()
        .count()
    )

    # Get KPIs without governance bodies
    from app.models import KPIGovernanceBodyLink

    kpis_without_gb = (
        db.session.query(KPI)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
        .outerjoin(KPIGovernanceBodyLink, KPI.id == KPIGovernanceBodyLink.kpi_id)
        .filter(Initiative.organization_id == org_id, KPIGovernanceBodyLink.id.is_(None))
        .count()
    )

    # Calculate total
    total_issues = (
        initiatives_no_consensus + initiatives_incomplete + spaces_no_swot + systems_without_kpis + kpis_without_gb
    )

    return jsonify({"total_issues": total_issues})


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
