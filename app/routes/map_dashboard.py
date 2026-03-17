"""
Map Dashboard route for geographic visualization of KPIs
"""

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf

from app.extensions import db
from app.models import GeographyRegion, KPIGeographyAssignment, Organization

bp = Blueprint("map_dashboard", __name__, url_prefix="/map")


@bp.route("/")
@login_required
def index():
    """Map dashboard showing KPIs by geographic location"""
    org_id = session.get("organization_id")

    if not org_id:
        # Redirect to org selection if no context
        return redirect(url_for("auth.select_organization"))

    organization = Organization.query.get_or_404(org_id)

    # Get all regions for this organization
    regions = GeographyRegion.query.filter_by(organization_id=org_id).order_by(GeographyRegion.display_order).all()

    # Count total KPIs with geography assignments (distinct KPI IDs) for this organization
    # Join through KPI → InitiativeSystemLink → Initiative to filter by organization
    from app.models import KPI, Initiative, InitiativeSystemLink

    total_kpis_with_location = (
        db.session.query(KPIGeographyAssignment.kpi_id)
        .join(KPI, KPIGeographyAssignment.kpi_id == KPI.id)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
        .filter(Initiative.organization_id == org_id)
        .distinct()
        .count()
    )

    # Get map color preferences (with defaults)
    map_color_with_kpis = organization.map_country_color_with_kpis or "#3b82f6"
    map_color_no_kpis = organization.map_country_color_no_kpis or "#9ca3af"

    return render_template(
        "map_dashboard/index.html",
        organization=organization,
        regions=regions,
        total_kpis=total_kpis_with_location,
        map_color_with_kpis=map_color_with_kpis,
        map_color_no_kpis=map_color_no_kpis,
        csrf_token=generate_csrf,
    )


@bp.route("/save-colors", methods=["POST"])
@login_required
def save_colors():
    """Save map color preferences for the organization"""
    org_id = session.get("organization_id")

    if not org_id:
        return jsonify({"success": False, "message": "No organization context"}), 400

    organization = Organization.query.get_or_404(org_id)

    # Check if user has permission (org admin)
    membership = current_user.get_organization_membership(org_id)
    if not membership or not membership.is_org_admin:
        return jsonify({"success": False, "message": "Permission denied. Only org admins can change map colors."}), 403

    data = request.get_json()
    color_with_kpis = data.get("color_with_kpis")
    color_no_kpis = data.get("color_no_kpis")

    # Validate hex colors
    import re

    hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
    if color_with_kpis and not hex_pattern.match(color_with_kpis):
        return jsonify({"success": False, "message": "Invalid hex color for countries with KPIs"}), 400
    if color_no_kpis and not hex_pattern.match(color_no_kpis):
        return jsonify({"success": False, "message": "Invalid hex color for countries without KPIs"}), 400

    # Update colors
    if color_with_kpis:
        organization.map_country_color_with_kpis = color_with_kpis
    if color_no_kpis:
        organization.map_country_color_no_kpis = color_no_kpis

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": "Map colors updated successfully",
            "color_with_kpis": organization.map_country_color_with_kpis,
            "color_no_kpis": organization.map_country_color_no_kpis,
        }
    )
