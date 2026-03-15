"""
Map Dashboard route for geographic visualization of KPIs
"""

from flask import Blueprint, redirect, render_template, session, url_for
from flask_login import login_required

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
    from app.models import KPI, InitiativeSystemLink, Initiative

    total_kpis_with_location = (
        db.session.query(KPIGeographyAssignment.kpi_id)
        .join(KPI, KPIGeographyAssignment.kpi_id == KPI.id)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
        .filter(Initiative.organization_id == org_id)
        .distinct()
        .count()
    )

    return render_template(
        "map_dashboard/index.html", organization=organization, regions=regions, total_kpis=total_kpis_with_location
    )
