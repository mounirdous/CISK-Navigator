"""Routes for stakeholder mapping and network analysis."""

from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf

from app import db
from app.forms import StakeholderFilterForm, StakeholderForm, StakeholderMapForm
from app.models import (
    KPI,
    Challenge,
    GeographyCountry,
    GeographyRegion,
    GeographySite,
    Initiative,
    Organization,
    Space,
    Stakeholder,
    StakeholderEntityLink,
    StakeholderMap,
    StakeholderMapMembership,
    StakeholderRelationship,
    System,
)
from app.services.audit_service import AuditService

bp = Blueprint("stakeholders", __name__, url_prefix="/stakeholders")


@bp.route("/")
@login_required
def index():
    """Stakeholder network map view."""
    org_id = request.args.get("organization_id", type=int)
    map_id = request.args.get("map_id", type=int)

    if not org_id:
        if current_user.is_super_admin or current_user.is_global_admin:
            orgs = Organization.query.order_by(Organization.name).all()
            if orgs:
                org_id = orgs[0].id
        else:
            memberships = current_user.organization_memberships
            if memberships:
                org_id = memberships[0].organization_id

    if not org_id:
        flash("No organization selected", "warning")
        return redirect(url_for("workspace.index"))

    organization = Organization.query.get_or_404(org_id)

    # Permission check
    if not (current_user.is_super_admin or current_user.is_global_admin or current_user.is_org_admin(org_id)):
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    # Get all maps for this organization (for dropdown)
    all_maps = StakeholderMap.query.filter_by(organization_id=org_id).all()
    visible_maps = [m for m in all_maps if m.is_visible_to_user(current_user)]

    # Require map selection - redirect to first map if none selected
    if not map_id and visible_maps:
        return redirect(url_for("stakeholders.index", organization_id=org_id, map_id=visible_maps[0].id))

    # Filter stakeholders by selected map
    if map_id:
        selected_map = StakeholderMap.query.get(map_id)
        if not selected_map or not selected_map.is_visible_to_user(current_user):
            flash("Map not found or access denied", "warning")
            return redirect(url_for("stakeholders.index", organization_id=org_id))

        stakeholders = selected_map.get_stakeholders()
    else:
        # No maps available - show empty view with message
        selected_map = None
        stakeholders = []

    # Filter by visibility
    visible_stakeholders = [s for s in stakeholders if s.is_visible_to_user(current_user)]

    # Get relationships, filtering to only those between visible stakeholders
    stakeholder_ids = [s.id for s in visible_stakeholders]
    relationships = (
        StakeholderRelationship.query.filter(
            StakeholderRelationship.from_stakeholder_id.in_(stakeholder_ids),
            StakeholderRelationship.to_stakeholder_id.in_(stakeholder_ids),
        ).all()
        if stakeholder_ids
        else []
    )

    # Get unique departments for filter
    departments = (
        db.session.query(Stakeholder.department)
        .filter(Stakeholder.organization_id == org_id, Stakeholder.department.isnot(None))
        .distinct()
        .all()
    )
    departments = [d[0] for d in departments if d[0]]

    filter_form = StakeholderFilterForm()
    filter_form.department.choices = [("", "All Departments")] + [(d, d) for d in sorted(departments)]

    # Get sites that are actually used by stakeholders in this organization
    sites = (
        db.session.query(GeographySite)
        .join(Stakeholder, GeographySite.id == Stakeholder.site_id)
        .join(GeographySite.country)
        .filter(Stakeholder.organization_id == org_id, Stakeholder.site_id.isnot(None))
        .distinct()
        .order_by(GeographySite.name)
        .all()
    )

    # Convert to dicts for JSON serialization
    stakeholders_data = [s.to_dict() for s in visible_stakeholders]
    relationships_data = [r.to_dict() for r in relationships]
    maps_data = [
        {"id": m.id, "name": m.name, "visibility": m.visibility, "stakeholder_count": m.memberships.count()}
        for m in visible_maps
    ]

    return render_template(
        "stakeholders/index.html",
        organization=organization,
        stakeholders=stakeholders_data,
        relationships=relationships_data,
        filter_form=filter_form,
        sites=sites,
        maps=maps_data,
        selected_map=selected_map,
        csrf_token=generate_csrf,
    )


@bp.route("/list")
@login_required
def list_stakeholders():
    """List view of stakeholders."""
    org_id = request.args.get("organization_id", type=int)
    if not org_id:
        flash("No organization selected", "warning")
        return redirect(url_for("workspace.index"))

    organization = Organization.query.get_or_404(org_id)

    # Permission check
    if not (current_user.is_super_admin or current_user.is_global_admin or current_user.is_org_admin(org_id)):
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    stakeholders = Stakeholder.query.filter_by(organization_id=org_id).order_by(Stakeholder.name).all()

    return render_template(
        "stakeholders/list.html",
        organization=organization,
        stakeholders=stakeholders,
        csrf_token=generate_csrf,
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new stakeholder."""
    org_id = request.args.get("organization_id", type=int) or request.form.get("organization_id", type=int)
    if not org_id:
        flash("No organization selected", "warning")
        return redirect(url_for("workspace.index"))

    organization = Organization.query.get_or_404(org_id)
    form = StakeholderForm()

    # Populate site choices (only sites belonging to this organization)
    sites = (
        GeographySite.query.join(GeographyCountry, GeographySite.country_id == GeographyCountry.id)
        .join(GeographyRegion, GeographyCountry.region_id == GeographyRegion.id)
        .filter(GeographyRegion.organization_id == org_id, GeographySite.is_active.is_(True))
        .order_by(GeographySite.name)
        .all()
    )
    form.site_id.choices = [(0, "-- No Site --")] + [(s.id, f"{s.name} ({s.country.name})") for s in sites]

    # Populate map choices (all maps visible to current user in this organization)
    all_maps = StakeholderMap.query.filter_by(organization_id=org_id).order_by(StakeholderMap.name).all()
    visible_maps = [m for m in all_maps if m.is_visible_to_user(current_user)]
    form.maps.choices = [
        (m.id, f"{m.name} ({'Private' if m.visibility == 'private' else 'Shared'})") for m in visible_maps
    ]

    if not visible_maps:
        flash("No maps available. Please create a map first.", "warning")
        return redirect(url_for("stakeholders.create_map", organization_id=org_id))

    if form.validate_on_submit():
        stakeholder = Stakeholder(
            organization_id=org_id,
            created_by_user_id=current_user.id,
            name=form.name.data,
            role=form.role.data,
            department=form.department.data,
            site_id=form.site_id.data if form.site_id.data != 0 else None,
            email=form.email.data,
            influence_level=form.influence_level.data,
            interest_level=form.interest_level.data,
            support_level=form.support_level.data,
            visibility=form.visibility.data,
            notes=form.notes.data,
        )

        db.session.add(stakeholder)
        db.session.flush()  # Get stakeholder.id before adding to maps

        # Add stakeholder to selected maps
        selected_map_ids = form.maps.data
        for map_id in selected_map_ids:
            stakeholder_map = StakeholderMap.query.get(map_id)
            if stakeholder_map and stakeholder_map.is_visible_to_user(current_user):
                stakeholder_map.add_stakeholder(stakeholder.id)

        db.session.commit()

        AuditService.log_action(
            action="create",
            entity_type="stakeholder",
            entity_id=stakeholder.id,
            entity_name=stakeholder.name,
            description=f"Created stakeholder: {stakeholder.name} and added to {len(selected_map_ids)} map(s)",
        )

        flash(f"Stakeholder '{stakeholder.name}' created and added to {len(selected_map_ids)} map(s)", "success")
        return redirect(url_for("stakeholders.index", organization_id=org_id))

    return render_template("stakeholders/create.html", form=form, organization=organization, csrf_token=generate_csrf)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    """Edit a stakeholder."""
    stakeholder = Stakeholder.query.get_or_404(id)
    organization = stakeholder.organization

    # Permission check
    if not (
        current_user.is_super_admin
        or current_user.is_global_admin
        or current_user.is_org_admin(stakeholder.organization_id)
    ):
        flash("Access denied", "danger")
        return redirect(url_for("stakeholders.index", organization_id=stakeholder.organization_id))

    form = StakeholderForm(obj=stakeholder)

    # Populate site choices (only sites belonging to this organization)
    sites = (
        GeographySite.query.join(GeographyCountry, GeographySite.country_id == GeographyCountry.id)
        .join(GeographyRegion, GeographyCountry.region_id == GeographyRegion.id)
        .filter(GeographyRegion.organization_id == org_id, GeographySite.is_active.is_(True))
        .order_by(GeographySite.name)
        .all()
    )
    form.site_id.choices = [(0, "-- No Site --")] + [(s.id, f"{s.name} ({s.country.name})") for s in sites]

    # Populate map choices
    all_maps = (
        StakeholderMap.query.filter_by(organization_id=stakeholder.organization_id).order_by(StakeholderMap.name).all()
    )
    visible_maps = [m for m in all_maps if m.is_visible_to_user(current_user)]
    form.maps.choices = [
        (m.id, f"{m.name} ({'Private' if m.visibility == 'private' else 'Shared'})") for m in visible_maps
    ]

    # Set current values
    if request.method == "GET":
        form.site_id.data = stakeholder.site_id if stakeholder.site_id else 0
        # Get current maps for this stakeholder
        current_map_ids = [
            m.map_id for m in StakeholderMapMembership.query.filter_by(stakeholder_id=stakeholder.id).all()
        ]
        form.maps.data = current_map_ids

    if form.validate_on_submit():
        stakeholder.name = form.name.data
        stakeholder.role = form.role.data
        stakeholder.department = form.department.data
        stakeholder.site_id = form.site_id.data if form.site_id.data != 0 else None
        stakeholder.email = form.email.data
        stakeholder.influence_level = form.influence_level.data
        stakeholder.interest_level = form.interest_level.data
        stakeholder.support_level = form.support_level.data
        stakeholder.visibility = form.visibility.data
        stakeholder.notes = form.notes.data
        stakeholder.updated_at = datetime.utcnow()

        # Update map memberships
        selected_map_ids = set(form.maps.data)
        current_memberships = StakeholderMapMembership.query.filter_by(stakeholder_id=stakeholder.id).all()
        current_map_ids = set(m.map_id for m in current_memberships)

        # Remove from maps that are no longer selected
        maps_to_remove = current_map_ids - selected_map_ids
        for map_id in maps_to_remove:
            membership = StakeholderMapMembership.query.filter_by(map_id=map_id, stakeholder_id=stakeholder.id).first()
            if membership:
                db.session.delete(membership)

        # Add to newly selected maps
        maps_to_add = selected_map_ids - current_map_ids
        for map_id in maps_to_add:
            stakeholder_map = StakeholderMap.query.get(map_id)
            if stakeholder_map and stakeholder_map.is_visible_to_user(current_user):
                stakeholder_map.add_stakeholder(stakeholder.id)

        db.session.commit()

        AuditService.log_action(
            action="update",
            entity_type="stakeholder",
            entity_id=stakeholder.id,
            entity_name=stakeholder.name,
            description=f"Updated stakeholder: {stakeholder.name}",
        )

        flash(f"Stakeholder '{stakeholder.name}' updated successfully", "success")
        return redirect(url_for("stakeholders.index", organization_id=stakeholder.organization_id))

    return render_template(
        "stakeholders/edit.html",
        form=form,
        stakeholder=stakeholder,
        organization=organization,
        csrf_token=generate_csrf,
    )


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    """Delete a stakeholder."""
    stakeholder = Stakeholder.query.get_or_404(id)
    org_id = stakeholder.organization_id
    name = stakeholder.name

    # Permission check
    if not (current_user.is_super_admin or current_user.is_global_admin or current_user.is_org_admin(org_id)):
        flash("Access denied", "danger")
        return redirect(url_for("stakeholders.index", organization_id=org_id))

    db.session.delete(stakeholder)
    db.session.commit()

    AuditService.log_action(
        action="delete",
        entity_type="stakeholder",
        entity_id=id,
        entity_name=name,
        description=f"Deleted stakeholder: {name}",
    )

    flash(f"Stakeholder '{name}' deleted successfully", "success")
    return redirect(url_for("stakeholders.index", organization_id=org_id))


@bp.route("/api/graph-data")
@login_required
def api_graph_data():
    """API endpoint to get graph data for visualization."""
    org_id = request.args.get("organization_id", type=int)
    map_id = request.args.get("map_id", type=int)

    if not org_id:
        return jsonify({"error": "No organization specified"}), 400

    # Permission check
    if not (current_user.is_super_admin or current_user.is_global_admin or current_user.is_org_admin(org_id)):
        return jsonify({"error": "Access denied"}), 403

    # Filter by map if specified
    if map_id:
        selected_map = StakeholderMap.query.get(map_id)
        if not selected_map or not selected_map.is_visible_to_user(current_user):
            return jsonify({"error": "Map not found or access denied"}), 403

        # Get stakeholders in this map
        stakeholders = selected_map.get_stakeholders()
        query = None  # Skip query building, we already have stakeholders
    else:
        # Apply filters to all stakeholders in organization
        query = Stakeholder.query.filter_by(organization_id=org_id)

    # Apply additional filters only if not using map (query-based filtering)
    if query is not None:
        department = request.args.get("department")
        if department:
            query = query.filter_by(department=department)

        support_level = request.args.get("support_level")
        if support_level:
            query = query.filter_by(support_level=support_level)

        min_influence = request.args.get("min_influence", type=int, default=1)
        max_influence = request.args.get("max_influence", type=int, default=100)
        query = query.filter(Stakeholder.influence_level >= min_influence, Stakeholder.influence_level <= max_influence)

        stakeholders = query.all()
    # else: stakeholders already set from map.get_stakeholders()

    # Filter by visibility
    visible_stakeholders = [s for s in stakeholders if s.is_visible_to_user(current_user)]
    stakeholder_ids = [s.id for s in visible_stakeholders]

    # Get relationships for filtered stakeholders
    relationships = StakeholderRelationship.query.filter(
        StakeholderRelationship.from_stakeholder_id.in_(stakeholder_ids),
        StakeholderRelationship.to_stakeholder_id.in_(stakeholder_ids),
    ).all()

    # Format for vis.js
    nodes = []
    for s in visible_stakeholders:
        # Color by support level
        color_map = {
            "champion": "#28a745",
            "supporter": "#6c757d",
            "neutral": "#ffc107",
            "skeptic": "#fd7e14",
            "blocker": "#dc3545",
        }

        nodes.append(
            {
                "id": s.id,
                "label": s.name,
                "title": f"{s.name}\n{s.role or ''}\n{s.department or ''}\nInfluence: {s.influence_level}\nSupport: {s.support_level}",
                "value": s.influence_level,  # Size by influence
                "color": color_map.get(s.support_level, "#6c757d"),
                "x": s.position_x,
                "y": s.position_y,
                "data": s.to_dict(),
            }
        )

    edges = []
    for r in relationships:
        # Style by relationship type
        style_map = {
            "reports_to": {"color": "#6c757d", "dashes": True},
            "influences": {"color": "#007bff", "width": 3},
            "collaborates": {"color": "#28a745", "dashes": False},
            "sponsors": {"color": "#ffc107", "width": 3},
            "blocks": {"color": "#dc3545", "width": 2},
        }

        style = style_map.get(r.relationship_type, {})
        edges.append(
            {
                "from": r.from_stakeholder_id,
                "to": r.to_stakeholder_id,
                "title": f"{r.relationship_type} (strength: {r.strength})",
                "width": r.strength / 25,  # Scale width
                **style,
            }
        )

    return jsonify({"nodes": nodes, "edges": edges})


@bp.route("/api/save-positions", methods=["POST"])
@login_required
def api_save_positions():
    """Save node positions from the graph."""
    data = request.get_json()
    positions = data.get("positions", {})

    for node_id, position in positions.items():
        stakeholder = Stakeholder.query.get(int(node_id))
        if stakeholder:
            # Permission check
            if not (
                current_user.is_super_admin
                or current_user.is_global_admin
                or current_user.is_org_admin(stakeholder.organization_id)
            ):
                continue

            stakeholder.position_x = position.get("x")
            stakeholder.position_y = position.get("y")

    db.session.commit()
    return jsonify({"success": True})


@bp.route("/relationships/create", methods=["POST"])
@login_required
def create_relationship():
    """Create a relationship between stakeholders."""
    data = request.get_json()

    from_id = data.get("from_stakeholder_id")
    to_id = data.get("to_stakeholder_id")
    rel_type = data.get("relationship_type")
    strength = data.get("strength", 50)

    if not all([from_id, to_id, rel_type]):
        return jsonify({"error": "Missing required fields"}), 400

    from_stakeholder = Stakeholder.query.get(from_id)
    to_stakeholder = Stakeholder.query.get(to_id)

    if not from_stakeholder or not to_stakeholder:
        return jsonify({"error": "Stakeholder not found"}), 404

    # Permission check
    if not (
        current_user.is_super_admin
        or current_user.is_global_admin
        or current_user.is_org_admin(from_stakeholder.organization_id)
    ):
        return jsonify({"error": "Access denied"}), 403

    relationship = StakeholderRelationship(
        from_stakeholder_id=from_id, to_stakeholder_id=to_id, relationship_type=rel_type, strength=strength
    )

    db.session.add(relationship)
    db.session.commit()

    AuditService.log_action(
        action="create",
        entity_type="stakeholder_relationship",
        entity_id=relationship.id,
        description=f"Created relationship: {from_stakeholder.name} -> {to_stakeholder.name}",
    )

    return jsonify({"success": True, "relationship": relationship.to_dict()})


@bp.route("/relationships/<int:id>/delete", methods=["POST"])
@login_required
def delete_relationship(id):
    """Delete a relationship."""
    relationship = StakeholderRelationship.query.get_or_404(id)

    # Permission check
    if not (
        current_user.is_super_admin
        or current_user.is_global_admin
        or current_user.is_org_admin(relationship.from_stakeholder.organization_id)
    ):
        return jsonify({"error": "Access denied"}), 403

    db.session.delete(relationship)
    db.session.commit()

    AuditService.log_action(
        action="delete", entity_type="stakeholder_relationship", entity_id=id, description="Deleted relationship"
    )

    return jsonify({"success": True})


@bp.route("/api/power-interest-matrix")
@login_required
def api_power_interest_matrix():
    """Get data for power/interest matrix analysis."""
    org_id = request.args.get("organization_id", type=int)
    if not org_id:
        return jsonify({"error": "No organization specified"}), 400

    # Permission check
    if not (current_user.is_super_admin or current_user.is_global_admin or current_user.is_org_admin(org_id)):
        return jsonify({"error": "Access denied"}), 403

    stakeholders = Stakeholder.query.filter_by(organization_id=org_id).all()

    # Filter by visibility
    visible_stakeholders = [s for s in stakeholders if s.is_visible_to_user(current_user)]

    matrix_data = []
    for s in visible_stakeholders:
        matrix_data.append(
            {
                "id": s.id,
                "name": s.name,
                "power": s.influence_level,
                "interest": s.interest_level,
                "support": s.support_level,
                "role": s.role,
                "department": s.department,
            }
        )

    return jsonify(matrix_data)


@bp.route("/api/sponsor-recommendations")
@login_required
def api_sponsor_recommendations():
    """Get sponsor recommendations based on influence and support."""
    org_id = request.args.get("organization_id", type=int)

    if not org_id:
        return jsonify({"error": "No organization specified"}), 400

    # Permission check
    if not (current_user.is_super_admin or current_user.is_global_admin or current_user.is_org_admin(org_id)):
        return jsonify({"error": "Access denied"}), 403

    # Get high-influence, positive stakeholders
    ideal_sponsors = (
        Stakeholder.query.filter_by(organization_id=org_id)
        .filter(Stakeholder.influence_level >= 70, Stakeholder.support_level.in_(["champion", "supporter"]))
        .order_by(Stakeholder.influence_level.desc())
        .limit(10)
        .all()
    )

    # Filter by visibility
    visible_sponsors = [s for s in ideal_sponsors if s.is_visible_to_user(current_user)]

    recommendations = []
    for s in visible_sponsors:
        recommendations.append(
            {
                "id": s.id,
                "name": s.name,
                "role": s.role,
                "department": s.department,
                "influence_level": s.influence_level,
                "support_level": s.support_level,
                "score": s.influence_level * 0.7 + ({"champion": 100, "supporter": 75}.get(s.support_level, 0)) * 0.3,
                "reason": f"High influence ({s.influence_level}) and positive support ({s.support_level})",
            }
        )

    # Sort by score
    recommendations.sort(key=lambda x: x["score"], reverse=True)

    return jsonify(recommendations)


@bp.route("/api/entities/<entity_type>")
@login_required
def api_get_entities(entity_type):
    """Get list of entities by type for linking."""
    org_id = request.args.get("organization_id", type=int)
    if not org_id:
        return jsonify({"error": "No organization specified"}), 400

    # Permission check
    if not (current_user.is_super_admin or current_user.is_global_admin or current_user.is_org_admin(org_id)):
        return jsonify({"error": "Access denied"}), 403

    # Map entity types to models
    entity_map = {
        "space": Space,
        "challenge": Challenge,
        "initiative": Initiative,
        "system": System,
        "kpi": KPI,
    }

    entity_class = entity_map.get(entity_type)
    if not entity_class:
        return jsonify({"error": "Invalid entity type"}), 400

    # Query entities for the organization
    entities = entity_class.query.filter_by(organization_id=org_id).order_by(entity_class.name).all()

    # Return simple list of id and name
    result = [{"id": e.id, "name": e.name} for e in entities]

    return jsonify(result)


@bp.route("/<int:id>/link-entity", methods=["POST"])
@login_required
def link_entity(id):
    """Link a stakeholder to an entity (Challenge, Initiative, System, KPI)."""
    stakeholder = Stakeholder.query.get_or_404(id)

    # Permission check
    if not (
        current_user.is_super_admin
        or current_user.is_global_admin
        or current_user.is_org_admin(stakeholder.organization_id)
    ):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    entity_type = data.get("entity_type")
    entity_id = data.get("entity_id")
    interest_level = data.get("interest_level", "medium")
    impact_level = data.get("impact_level", "medium")

    if not entity_type or not entity_id:
        return jsonify({"error": "Missing entity_type or entity_id"}), 400

    # Validate entity type
    valid_types = ["space", "challenge", "initiative", "system", "kpi"]
    if entity_type not in valid_types:
        return jsonify({"error": "Invalid entity type"}), 400

    # Check if link already exists
    existing = StakeholderEntityLink.query.filter_by(
        stakeholder_id=stakeholder.id, entity_type=entity_type, entity_id=entity_id
    ).first()

    if existing:
        return jsonify({"error": "Link already exists"}), 400

    # Create the link
    link = StakeholderEntityLink(
        stakeholder_id=stakeholder.id,
        entity_type=entity_type,
        entity_id=entity_id,
        interest_level=interest_level,
        impact_level=impact_level,
    )

    db.session.add(link)
    db.session.commit()

    AuditService.log_action(
        action="create",
        entity_type="stakeholder_entity_link",
        entity_id=link.id,
        entity_name=f"{stakeholder.name} -> {entity_type}#{entity_id}",
        description=f"Linked stakeholder {stakeholder.name} to {entity_type} #{entity_id}",
    )

    return jsonify({"success": True, "link_id": link.id})


@bp.route("/<int:id>/unlink-entity", methods=["POST"])
@login_required
def unlink_entity(id):
    """Unlink a stakeholder from an entity."""
    stakeholder = Stakeholder.query.get_or_404(id)

    # Permission check
    if not (
        current_user.is_super_admin
        or current_user.is_global_admin
        or current_user.is_org_admin(stakeholder.organization_id)
    ):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    entity_type = data.get("entity_type")
    entity_id = data.get("entity_id")

    if not entity_type or not entity_id:
        return jsonify({"error": "Missing entity_type or entity_id"}), 400

    # Find and delete the link
    link = StakeholderEntityLink.query.filter_by(
        stakeholder_id=stakeholder.id, entity_type=entity_type, entity_id=entity_id
    ).first()

    if not link:
        return jsonify({"error": "Link not found"}), 404

    link_id = link.id
    db.session.delete(link)
    db.session.commit()

    AuditService.log_action(
        action="delete",
        entity_type="stakeholder_entity_link",
        entity_id=link_id,
        entity_name=f"{stakeholder.name} -> {entity_type}#{entity_id}",
        description=f"Unlinked stakeholder {stakeholder.name} from {entity_type} #{entity_id}",
    )

    return jsonify({"success": True})


@bp.route("/matrix")
@login_required
def power_interest_matrix():
    """Power/Interest matrix view."""
    org_id = request.args.get("organization_id", type=int)
    if not org_id:
        flash("No organization selected", "warning")
        return redirect(url_for("workspace.index"))

    organization = Organization.query.get_or_404(org_id)

    # Permission check
    if not (current_user.is_super_admin or current_user.is_global_admin or current_user.is_org_admin(org_id)):
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    return render_template("stakeholders/matrix.html", organization=organization, csrf_token=generate_csrf)


@bp.route("/maps")
@login_required
def list_maps():
    """List all stakeholder maps for an organization."""
    org_id = request.args.get("organization_id", type=int)
    if not org_id:
        flash("No organization selected", "warning")
        return redirect(url_for("workspace.index"))

    organization = Organization.query.get_or_404(org_id)

    # Permission check
    if not (current_user.is_super_admin or current_user.is_global_admin or current_user.is_org_admin(org_id)):
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    all_maps = StakeholderMap.query.filter_by(organization_id=org_id).order_by(StakeholderMap.name).all()
    visible_maps = [m for m in all_maps if m.is_visible_to_user(current_user)]

    return render_template(
        "stakeholders/maps.html", organization=organization, maps=visible_maps, csrf_token=generate_csrf
    )


@bp.route("/maps/create", methods=["GET", "POST"])
@login_required
def create_map():
    """Create a new stakeholder map."""
    org_id = request.args.get("organization_id", type=int) or request.form.get("organization_id", type=int)
    if not org_id:
        flash("No organization selected", "warning")
        return redirect(url_for("workspace.index"))

    organization = Organization.query.get_or_404(org_id)
    form = StakeholderMapForm()

    if form.validate_on_submit():
        stakeholder_map = StakeholderMap(
            organization_id=org_id,
            created_by_user_id=current_user.id,
            name=form.name.data,
            description=form.description.data,
            visibility=form.visibility.data,
        )

        db.session.add(stakeholder_map)
        db.session.commit()

        AuditService.log_action(
            action="create",
            entity_type="stakeholder_map",
            entity_id=stakeholder_map.id,
            entity_name=stakeholder_map.name,
            description=f"Created stakeholder map: {stakeholder_map.name}",
        )

        flash(f"Map '{stakeholder_map.name}' created successfully", "success")
        return redirect(url_for("stakeholders.edit_map", id=stakeholder_map.id))

    return render_template(
        "stakeholders/create_map.html", form=form, organization=organization, csrf_token=generate_csrf
    )


@bp.route("/maps/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_map(id):
    """Edit a stakeholder map."""
    stakeholder_map = StakeholderMap.query.get_or_404(id)
    organization = stakeholder_map.organization

    # Permission check
    if not (
        current_user.is_super_admin
        or current_user.is_global_admin
        or current_user.is_org_admin(stakeholder_map.organization_id)
    ):
        flash("Access denied", "danger")
        return redirect(url_for("stakeholders.list_maps", organization_id=stakeholder_map.organization_id))

    form = StakeholderMapForm(obj=stakeholder_map)

    if form.validate_on_submit():
        stakeholder_map.name = form.name.data
        stakeholder_map.description = form.description.data
        stakeholder_map.visibility = form.visibility.data
        stakeholder_map.updated_at = datetime.utcnow()

        db.session.commit()

        AuditService.log_action(
            action="update",
            entity_type="stakeholder_map",
            entity_id=stakeholder_map.id,
            entity_name=stakeholder_map.name,
            description=f"Updated stakeholder map: {stakeholder_map.name}",
        )

        flash(f"Map '{stakeholder_map.name}' updated successfully", "success")
        return redirect(url_for("stakeholders.edit_map", id=stakeholder_map.id))

    # Get all stakeholders in organization
    all_stakeholders = (
        Stakeholder.query.filter_by(organization_id=stakeholder_map.organization_id).order_by(Stakeholder.name).all()
    )
    map_stakeholders = stakeholder_map.get_stakeholders()
    map_stakeholder_ids = [s.id for s in map_stakeholders]

    return render_template(
        "stakeholders/edit_map.html",
        form=form,
        stakeholder_map=stakeholder_map,
        organization=organization,
        all_stakeholders=all_stakeholders,
        map_stakeholders=map_stakeholders,
        map_stakeholder_ids=map_stakeholder_ids,
        csrf_token=generate_csrf,
    )


@bp.route("/maps/<int:id>/delete", methods=["POST"])
@login_required
def delete_map(id):
    """Delete a stakeholder map."""
    stakeholder_map = StakeholderMap.query.get_or_404(id)
    org_id = stakeholder_map.organization_id
    name = stakeholder_map.name

    # Permission check
    if not (current_user.is_super_admin or current_user.is_global_admin or current_user.is_org_admin(org_id)):
        flash("Access denied", "danger")
        return redirect(url_for("stakeholders.list_maps", organization_id=org_id))

    db.session.delete(stakeholder_map)
    db.session.commit()

    AuditService.log_action(
        action="delete",
        entity_type="stakeholder_map",
        entity_id=id,
        entity_name=name,
        description=f"Deleted stakeholder map: {name}",
    )

    flash(f"Map '{name}' deleted successfully", "success")
    return redirect(url_for("stakeholders.list_maps", organization_id=org_id))


@bp.route("/maps/<int:map_id>/add-stakeholder", methods=["POST"])
@login_required
def add_stakeholder_to_map(map_id):
    """Add a stakeholder to a map."""
    stakeholder_map = StakeholderMap.query.get_or_404(map_id)

    # Permission check
    if not (
        current_user.is_super_admin
        or current_user.is_global_admin
        or current_user.is_org_admin(stakeholder_map.organization_id)
    ):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    stakeholder_id = data.get("stakeholder_id")

    if not stakeholder_id:
        return jsonify({"error": "Missing stakeholder_id"}), 400

    # Check if already in map
    existing = StakeholderMapMembership.query.filter_by(map_id=map_id, stakeholder_id=stakeholder_id).first()
    if existing:
        return jsonify({"error": "Stakeholder already in this map"}), 400

    stakeholder_map.add_stakeholder(stakeholder_id)
    db.session.commit()

    stakeholder = Stakeholder.query.get(stakeholder_id)
    AuditService.log_action(
        action="create",
        entity_type="stakeholder_map_membership",
        entity_id=map_id,
        entity_name=f"{stakeholder_map.name} + {stakeholder.name if stakeholder else 'unknown'}",
        description=f"Added stakeholder to map {stakeholder_map.name}",
    )

    return jsonify({"success": True})


@bp.route("/maps/<int:map_id>/remove-stakeholder", methods=["POST"])
@login_required
def remove_stakeholder_from_map(map_id):
    """Remove a stakeholder from a map."""
    stakeholder_map = StakeholderMap.query.get_or_404(map_id)

    # Permission check
    if not (
        current_user.is_super_admin
        or current_user.is_global_admin
        or current_user.is_org_admin(stakeholder_map.organization_id)
    ):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()
    stakeholder_id = data.get("stakeholder_id")

    if not stakeholder_id:
        return jsonify({"error": "Missing stakeholder_id"}), 400

    stakeholder_map.remove_stakeholder(stakeholder_id)
    db.session.commit()

    stakeholder = Stakeholder.query.get(stakeholder_id)
    AuditService.log_action(
        action="delete",
        entity_type="stakeholder_map_membership",
        entity_id=map_id,
        entity_name=f"{stakeholder_map.name} - {stakeholder.name if stakeholder else 'unknown'}",
        description=f"Removed stakeholder from map {stakeholder_map.name}",
    )

    return jsonify({"success": True})


@bp.route("/export/image")
@login_required
def export_image():
    """Export the graph as an image (placeholder - client-side implementation)."""
    # This will be handled client-side using canvas.toDataURL()
    return jsonify({"message": "Use client-side export"})
