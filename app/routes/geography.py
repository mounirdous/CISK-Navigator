"""
Geography management routes for regions, countries, and sites
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf

from app.extensions import db
from app.forms.geography_forms import GeographyCountryForm, GeographyRegionForm, GeographySiteForm
from app.models import GeographyCountry, GeographyRegion, GeographySite, KPIGeographyAssignment, Organization
from app.services import AuditService

bp = Blueprint("geography", __name__, url_prefix="/org-admin/geography")


def organization_required(f):
    """Decorator to ensure user has organization context"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if session.get("organization_id") is None:
            flash("Please select an organization first.", "warning")
            return redirect(url_for("auth.select_organization"))
        return f(*args, **kwargs)

    return decorated_function


# ========================================
# GEOGRAPHY OVERVIEW & BULK IMPORT
# ========================================


@bp.route("/")
@login_required
@organization_required
def index():
    """Geography management dashboard showing all regions, countries, sites"""
    org_id = session.get("organization_id")
    organization = Organization.query.get_or_404(org_id)

    regions = GeographyRegion.query.filter_by(organization_id=org_id).order_by(GeographyRegion.display_order).all()

    # Calculate statistics
    total_countries = sum(len(region.countries) for region in regions)
    total_sites = sum(len(country.sites) for region in regions for country in region.countries)
    total_kpis_with_geography = db.session.query(KPIGeographyAssignment.kpi_id).distinct().count()

    return render_template(
        "geography/index.html",
        organization=organization,
        regions=regions,
        total_regions=len(regions),
        total_countries=total_countries,
        total_sites=total_sites,
        total_kpis_with_geography=total_kpis_with_geography,
        csrf_token=generate_csrf(),
    )


@bp.route("/import-csv", methods=["GET", "POST"])
@login_required
@organization_required
def import_csv():
    """Bulk import geography data from CSV"""
    if request.method == "POST":
        # TODO: Implement CSV import
        flash("CSV import functionality coming soon!", "info")
        return redirect(url_for("geography.index"))

    return render_template("geography/import_csv.html", csrf_token=generate_csrf())


# ========================================
# REGIONS
# ========================================


@bp.route("/regions/create", methods=["GET", "POST"])
@login_required
@organization_required
def create_region():
    """Create a new geography region"""
    org_id = session.get("organization_id")
    organization = Organization.query.get_or_404(org_id)
    form = GeographyRegionForm()

    if form.validate_on_submit():
        region = GeographyRegion(
            organization_id=org_id,
            name=form.name.data,
            code=form.code.data,
            display_order=form.display_order.data or 0,
        )
        db.session.add(region)
        db.session.commit()

        # Audit log
        AuditService.log_create(
            entity_type="GeographyRegion",
            entity_id=region.id,
            entity_name=region.name,
            new_value={"name": region.name, "code": region.code},
        )

        flash(f"Region '{region.name}' created successfully!", "success")
        return redirect(url_for("geography.index"))

    return render_template(
        "geography/region_form.html",
        form=form,
        organization=organization,
        title="Create Region",
        csrf_token=generate_csrf(),
    )


@bp.route("/regions/<int:region_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
def edit_region(region_id):
    """Edit an existing geography region"""
    org_id = session.get("organization_id")
    organization = Organization.query.get_or_404(org_id)
    region = GeographyRegion.query.filter_by(id=region_id, organization_id=org_id).first_or_404()

    form = GeographyRegionForm(obj=region)

    if form.validate_on_submit():
        old_values = {"name": region.name, "code": region.code}

        region.name = form.name.data
        region.code = form.code.data
        region.display_order = form.display_order.data

        db.session.commit()

        # Audit log
        AuditService.log_update(
            entity_type="GeographyRegion",
            entity_id=region.id,
            entity_name=region.name,
            old_value=old_values,
            new_value={"name": region.name, "code": region.code},
        )

        flash(f"Region '{region.name}' updated successfully!", "success")
        return redirect(url_for("geography.index"))

    return render_template(
        "geography/region_form.html",
        form=form,
        organization=organization,
        region=region,
        title="Edit Region",
        csrf_token=generate_csrf(),
    )


@bp.route("/regions/<int:region_id>/delete", methods=["POST"])
@login_required
@organization_required
def delete_region(region_id):
    """Delete a geography region"""
    org_id = session.get("organization_id")
    region = GeographyRegion.query.filter_by(id=region_id, organization_id=org_id).first_or_404()

    # Check if region has countries
    if region.countries:
        flash(
            f"Cannot delete region '{region.name}' - it has {len(region.countries)} countries. "
            "Delete countries first.",
            "danger",
        )
        return redirect(url_for("geography.index"))

    region_name = region.name

    # Audit log
    AuditService.log_delete(
        entity_type="GeographyRegion",
        entity_id=region.id,
        entity_name=region_name,
        old_value={"name": region.name, "code": region.code},
    )

    db.session.delete(region)
    db.session.commit()

    flash(f"Region '{region_name}' deleted successfully.", "success")
    return redirect(url_for("geography.index"))


# ========================================
# COUNTRIES
# ========================================


@bp.route("/countries/create", methods=["GET", "POST"])
@login_required
@organization_required
def create_country():
    """Create a new geography country"""
    org_id = session.get("organization_id")
    organization = Organization.query.get_or_404(org_id)

    form = GeographyCountryForm()
    form.region_id.choices = [
        (r.id, f"{r.name} ({r.code or 'No code'})")
        for r in GeographyRegion.query.filter_by(organization_id=org_id).order_by(GeographyRegion.display_order).all()
    ]

    if not form.region_id.choices:
        flash("Please create a region first before adding countries.", "warning")
        return redirect(url_for("geography.create_region"))

    if form.validate_on_submit():
        country = GeographyCountry(
            region_id=form.region_id.data,
            name=form.name.data,
            code=form.code.data,
            iso_code=form.iso_code.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            display_order=form.display_order.data or 0,
        )
        db.session.add(country)
        db.session.commit()

        # Audit log
        AuditService.log_create(
            entity_type="GeographyCountry",
            entity_id=country.id,
            entity_name=country.name,
            new_value={
                "name": country.name,
                "code": country.code,
                "iso_code": country.iso_code,
                "latitude": float(country.latitude) if country.latitude else None,
                "longitude": float(country.longitude) if country.longitude else None,
            },
        )

        flash(f"Country '{country.name}' created successfully!", "success")
        return redirect(url_for("geography.index"))

    return render_template(
        "geography/country_form.html",
        form=form,
        organization=organization,
        title="Create Country",
        csrf_token=generate_csrf(),
    )


@bp.route("/countries/<int:country_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
def edit_country(country_id):
    """Edit an existing geography country"""
    org_id = session.get("organization_id")
    organization = Organization.query.get_or_404(org_id)
    country = (
        GeographyCountry.query.join(GeographyRegion)
        .filter(GeographyCountry.id == country_id, GeographyRegion.organization_id == org_id)
        .first_or_404()
    )

    form = GeographyCountryForm(obj=country)
    form.region_id.choices = [
        (r.id, f"{r.name} ({r.code or 'No code'})")
        for r in GeographyRegion.query.filter_by(organization_id=org_id).order_by(GeographyRegion.display_order).all()
    ]

    if form.validate_on_submit():
        old_values = {
            "name": country.name,
            "code": country.code,
            "iso_code": country.iso_code,
            "latitude": float(country.latitude) if country.latitude else None,
            "longitude": float(country.longitude) if country.longitude else None,
        }

        country.region_id = form.region_id.data
        country.name = form.name.data
        country.code = form.code.data
        country.iso_code = form.iso_code.data
        country.latitude = form.latitude.data
        country.longitude = form.longitude.data
        country.display_order = form.display_order.data

        db.session.commit()

        # Audit log
        AuditService.log_update(
            entity_type="GeographyCountry",
            entity_id=country.id,
            entity_name=country.name,
            old_value=old_values,
            new_value={
                "name": country.name,
                "code": country.code,
                "iso_code": country.iso_code,
                "latitude": float(country.latitude) if country.latitude else None,
                "longitude": float(country.longitude) if country.longitude else None,
            },
        )

        flash(f"Country '{country.name}' updated successfully!", "success")
        return redirect(url_for("geography.index"))

    return render_template(
        "geography/country_form.html",
        form=form,
        organization=organization,
        country=country,
        title="Edit Country",
        csrf_token=generate_csrf(),
    )


@bp.route("/countries/<int:country_id>/delete", methods=["POST"])
@login_required
@organization_required
def delete_country(country_id):
    """Delete a geography country"""
    org_id = session.get("organization_id")
    country = (
        GeographyCountry.query.join(GeographyRegion)
        .filter(GeographyCountry.id == country_id, GeographyRegion.organization_id == org_id)
        .first_or_404()
    )

    # Check if country has sites
    if country.sites:
        flash(
            f"Cannot delete country '{country.name}' - it has {len(country.sites)} sites. " "Delete sites first.",
            "danger",
        )
        return redirect(url_for("geography.index"))

    country_name = country.name

    # Audit log
    AuditService.log_delete(
        entity_type="GeographyCountry",
        entity_id=country.id,
        entity_name=country_name,
        old_value={"name": country.name, "code": country.code, "iso_code": country.iso_code},
    )

    db.session.delete(country)
    db.session.commit()

    flash(f"Country '{country_name}' deleted successfully.", "success")
    return redirect(url_for("geography.index"))


# ========================================
# SITES
# ========================================


@bp.route("/sites/create", methods=["GET", "POST"])
@login_required
@organization_required
def create_site():
    """Create a new geography site"""
    org_id = session.get("organization_id")
    organization = Organization.query.get_or_404(org_id)

    form = GeographySiteForm()

    # Build country choices with region context
    countries = (
        GeographyCountry.query.join(GeographyRegion)
        .filter(GeographyRegion.organization_id == org_id)
        .order_by(GeographyRegion.display_order, GeographyCountry.display_order)
        .all()
    )
    form.country_id.choices = [(c.id, f"{c.region.name} → {c.name} ({c.code or 'No code'})") for c in countries]

    if not form.country_id.choices:
        flash("Please create a country first before adding sites.", "warning")
        return redirect(url_for("geography.create_country"))

    if form.validate_on_submit():
        site = GeographySite(
            country_id=form.country_id.data,
            name=form.name.data,
            code=form.code.data,
            address=form.address.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            is_active=form.is_active.data,
            display_order=form.display_order.data or 0,
        )
        db.session.add(site)
        db.session.commit()

        # Audit log
        AuditService.log_create(
            entity_type="GeographySite",
            entity_id=site.id,
            entity_name=site.name,
            new_value={
                "name": site.name,
                "code": site.code,
                "address": site.address,
                "latitude": float(site.latitude) if site.latitude else None,
                "longitude": float(site.longitude) if site.longitude else None,
            },
        )

        flash(f"Site '{site.name}' created successfully!", "success")
        return redirect(url_for("geography.index"))

    return render_template(
        "geography/site_form.html",
        form=form,
        organization=organization,
        title="Create Site",
        csrf_token=generate_csrf(),
    )


@bp.route("/sites/<int:site_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
def edit_site(site_id):
    """Edit an existing geography site"""
    org_id = session.get("organization_id")
    organization = Organization.query.get_or_404(org_id)
    site = (
        GeographySite.query.join(GeographyCountry)
        .join(GeographyRegion)
        .filter(GeographySite.id == site_id, GeographyRegion.organization_id == org_id)
        .first_or_404()
    )

    form = GeographySiteForm(obj=site)

    # Build country choices with region context
    countries = (
        GeographyCountry.query.join(GeographyRegion)
        .filter(GeographyRegion.organization_id == org_id)
        .order_by(GeographyRegion.display_order, GeographyCountry.display_order)
        .all()
    )
    form.country_id.choices = [(c.id, f"{c.region.name} → {c.name} ({c.code or 'No code'})") for c in countries]

    if form.validate_on_submit():
        old_values = {
            "name": site.name,
            "code": site.code,
            "address": site.address,
            "latitude": float(site.latitude) if site.latitude else None,
            "longitude": float(site.longitude) if site.longitude else None,
            "is_active": site.is_active,
        }

        site.country_id = form.country_id.data
        site.name = form.name.data
        site.code = form.code.data
        site.address = form.address.data
        site.latitude = form.latitude.data
        site.longitude = form.longitude.data
        site.is_active = form.is_active.data
        site.display_order = form.display_order.data

        db.session.commit()

        # Audit log
        AuditService.log_update(
            entity_type="GeographySite",
            entity_id=site.id,
            entity_name=site.name,
            old_value=old_values,
            new_value={
                "name": site.name,
                "code": site.code,
                "address": site.address,
                "latitude": float(site.latitude) if site.latitude else None,
                "longitude": float(site.longitude) if site.longitude else None,
                "is_active": site.is_active,
            },
        )

        flash(f"Site '{site.name}' updated successfully!", "success")
        return redirect(url_for("geography.index"))

    return render_template(
        "geography/site_form.html",
        form=form,
        organization=organization,
        site=site,
        title="Edit Site",
        csrf_token=generate_csrf(),
    )


@bp.route("/sites/<int:site_id>/delete", methods=["POST"])
@login_required
@organization_required
def delete_site(site_id):
    """Delete a geography site"""
    org_id = session.get("organization_id")
    site = (
        GeographySite.query.join(GeographyCountry)
        .join(GeographyRegion)
        .filter(GeographySite.id == site_id, GeographyRegion.organization_id == org_id)
        .first_or_404()
    )

    # Check if site has KPI assignments
    kpi_count = len(site.kpi_assignments)
    if kpi_count > 0:
        flash(
            f"Cannot delete site '{site.name}' - it has {kpi_count} KPI assignments. " "Remove KPI assignments first.",
            "danger",
        )
        return redirect(url_for("geography.index"))

    site_name = site.name

    # Audit log
    AuditService.log_delete(
        entity_type="GeographySite",
        entity_id=site.id,
        entity_name=site_name,
        old_value={
            "name": site.name,
            "code": site.code,
            "address": site.address,
            "latitude": float(site.latitude) if site.latitude else None,
            "longitude": float(site.longitude) if site.longitude else None,
        },
    )

    db.session.delete(site)
    db.session.commit()

    flash(f"Site '{site_name}' deleted successfully.", "success")
    return redirect(url_for("geography.index"))


# ========================================
# API ENDPOINTS (for AJAX and maps)
# ========================================


@bp.route("/api/sites.json")
@login_required
@organization_required
def api_sites_json():
    """Return all sites as GeoJSON for map display"""
    org_id = session.get("organization_id")

    sites = (
        GeographySite.query.join(GeographyCountry)
        .join(GeographyRegion)
        .filter(GeographyRegion.organization_id == org_id, GeographySite.is_active.is_(True))
        .all()
    )

    features = []
    for site in sites:
        if site.latitude and site.longitude:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(site.longitude), float(site.latitude)],
                    },
                    "properties": {
                        "id": site.id,
                        "name": site.name,
                        "code": site.code,
                        "country": site.country.name,
                        "region": site.country.region.name,
                        "address": site.address,
                        "kpi_count": site.get_kpi_count(),
                    },
                }
            )

    return jsonify({"type": "FeatureCollection", "features": features})


@bp.route("/api/countries/search")
@login_required
def api_countries_search():
    """Search countries from reference database for autocomplete"""
    import json
    import os

    query = request.args.get("q", "").lower()
    if len(query) < 2:
        return jsonify([])

    # Load countries from JSON file
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "countries.json")
    with open(json_path, "r") as f:
        countries = json.load(f)

    # Filter countries matching query
    results = [
        {
            "name": country["name"],
            "iso2": country["iso2"],
            "iso3": country["iso3"],
            "lat": country["lat"],
            "lon": country["lon"],
        }
        for country in countries
        if query in country["name"].lower() or query in country["iso2"].lower() or query in country["iso3"].lower()
    ]

    # Limit to 10 results
    return jsonify(results[:10])
