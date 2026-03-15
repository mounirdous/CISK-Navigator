"""
Map Dashboard route for geographic visualization of KPIs
"""

from flask import Blueprint, render_template, session
from flask_login import login_required

from app.models import GeographyRegion, Organization

bp = Blueprint("map_dashboard", __name__, url_prefix="/map")


@bp.route("/")
@login_required
def index():
    """Map dashboard showing KPIs by geographic location"""
    org_id = session.get("organization_id")

    if not org_id:
        # Redirect to org selection if no context
        from flask import redirect, url_for

        return redirect(url_for("auth.select_organization"))

    organization = Organization.query.get_or_404(org_id)

    # Get all regions with sites that have KPI assignments
    regions = GeographyRegion.query.filter_by(organization_id=org_id).order_by(GeographyRegion.display_order).all()

    # Count total KPIs with geography
    total_kpis_with_location = 0
    for region in regions:
        for country in region.countries:
            for site in country.sites:
                total_kpis_with_location += site.get_kpi_count()

    return render_template(
        "map_dashboard/index.html", organization=organization, regions=regions, total_kpis=total_kpis_with_location
    )
