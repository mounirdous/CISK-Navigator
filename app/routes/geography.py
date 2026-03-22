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

    # Get map color preferences
    map_color_with_kpis = organization.map_country_color_with_kpis or "#3b82f6"
    map_color_no_kpis = organization.map_country_color_no_kpis or "#9ca3af"

    return render_template(
        "geography/index.html",
        organization=organization,
        regions=regions,
        total_regions=len(regions),
        total_countries=total_countries,
        total_sites=total_sites,
        total_kpis_with_geography=total_kpis_with_geography,
        map_color_with_kpis=map_color_with_kpis,
        map_color_no_kpis=map_color_no_kpis,
        csrf_token=generate_csrf,
    )


@bp.route("/save-map-colors", methods=["POST"])
@login_required
@organization_required
def save_map_colors():
    """Save map color preferences for the organization"""
    import re

    try:
        org_id = session.get("organization_id")
        organization = Organization.query.get_or_404(org_id)

        # Check if user has permission (org admin)
        membership = current_user.get_membership(org_id)
        if not membership or not membership.is_org_admin:
            return jsonify({"success": False, "message": "Permission denied"}), 403

        data = request.get_json()
        color_with_kpis = data.get("color_with_kpis")
        color_no_kpis = data.get("color_no_kpis")

        # Validate hex colors
        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        if color_with_kpis and not hex_pattern.match(color_with_kpis):
            return jsonify({"success": False, "message": "Invalid color format"}), 400
        if color_no_kpis and not hex_pattern.match(color_no_kpis):
            return jsonify({"success": False, "message": "Invalid color format"}), 400

        # Check if columns exist (migration might not have run on production)
        if not hasattr(organization, "map_country_color_with_kpis"):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Database not updated. Please run: flask db upgrade on server.",
                    }
                ),
                500,
            )

        # Update colors
        if color_with_kpis:
            organization.map_country_color_with_kpis = color_with_kpis
        if color_no_kpis:
            organization.map_country_color_no_kpis = color_no_kpis

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "color_with_kpis": organization.map_country_color_with_kpis,
                "color_no_kpis": organization.map_country_color_no_kpis,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


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
        csrf_token=generate_csrf,
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
        csrf_token=generate_csrf,
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
        csrf_token=generate_csrf,
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
        csrf_token=generate_csrf,
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
        csrf_token=generate_csrf,
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
        csrf_token=generate_csrf,
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
    kpi_count = len(site.geography_assignments)
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


@bp.route("/api/countries.json")
@login_required
@organization_required
def api_countries_json():
    """Return all countries (with or without KPI assignments) as GeoJSON for map display"""
    org_id = session.get("organization_id")

    countries = GeographyCountry.query.join(GeographyRegion).filter(GeographyRegion.organization_id == org_id).all()

    features = []
    for country in countries:
        # Include ALL countries that have coordinates (not just those with KPIs)
        if country.latitude and country.longitude:
            # Count direct country assignments
            direct_assignments = len(country.geography_assignments)

            # Count site assignments that roll up to this country
            site_assignments = sum(len(site.geography_assignments) for site in country.sites)

            # Count region assignments that roll down to this country
            region_assignments = len(country.region.geography_assignments) if country.region else 0

            total_kpi_count = direct_assignments + site_assignments + region_assignments

            # Include country even if it has 0 KPIs (for grey display)
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(country.longitude), float(country.latitude)],
                    },
                    "properties": {
                        "id": country.id,
                        "name": country.name,
                        "code": country.code,
                        "iso_code": country.iso_code,
                        "region": country.region.name,
                        "kpi_count": total_kpi_count,
                        "level": "country",
                        "in_system": True,  # Flag to indicate country is in geography system
                    },
                }
            )

    return jsonify({"type": "FeatureCollection", "features": features})


@bp.route("/api/map-kpis.json")
@login_required
@organization_required
def api_map_kpis():
    """Return all KPIs with their geographic locations and latest values for map display"""
    from app.models import KPI, Initiative, InitiativeSystemLink

    org_id = session.get("organization_id")

    # Get all KPIs with geography assignments in this organization
    # Join through InitiativeSystemLink → Initiative to filter by organization
    kpis = (
        KPI.query.join(KPI.geography_assignments)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
        .join(GeographyCountry, KPIGeographyAssignment.country_id == GeographyCountry.id, isouter=True)
        .join(GeographySite, KPIGeographyAssignment.site_id == GeographySite.id, isouter=True)
        .join(GeographyRegion, KPIGeographyAssignment.region_id == GeographyRegion.id, isouter=True)
        .filter(Initiative.organization_id == org_id)
        .distinct()
        .all()
    )

    from app.services.consensus_service import ConsensusService

    features = []
    for kpi in kpis:
        # Get current value from contributions via ConsensusService
        primary_config = kpi.value_type_configs[0] if kpi.value_type_configs else None
        if primary_config:
            consensus = ConsensusService.calculate_consensus(primary_config.contributions)
            consensus_value = consensus["value"]
            if consensus_value is not None:
                formatted = primary_config.format_display_value(consensus_value)
                unit = primary_config.value_type.unit_label if primary_config.value_type else None
                suffix = primary_config.get_scale_suffix()
                display_value = f"{formatted}{suffix}{(' ' + unit) if unit else ''}"
            else:
                display_value = "No data"
        else:
            display_value = "No data"

        # Get geographic location for this KPI
        for assignment in kpi.geography_assignments:
            lat, lon, location_name, location_type = None, None, None, None

            if assignment.site_id and assignment.site:
                lat, lon = assignment.site.latitude, assignment.site.longitude
                location_name = assignment.site.name
                location_type = "site"
            elif assignment.country_id and assignment.country:
                lat, lon = assignment.country.latitude, assignment.country.longitude
                location_name = assignment.country.name
                location_type = "country"
            elif assignment.region_id and assignment.region:
                # For regions, use first country's coordinates
                if assignment.region.countries:
                    first_country = assignment.region.countries[0]
                    lat, lon = first_country.latitude, first_country.longitude
                    location_name = assignment.region.name
                    location_type = "region"

            if lat and lon:
                target_value = primary_config.target_value if primary_config else None

                # Collect non-empty contribution comments
                comments = []
                if primary_config:
                    for contrib in primary_config.contributions:
                        if contrib.comment and contrib.comment.strip():
                            comments.append({
                                "contributor": contrib.contributor_name,
                                "comment": contrib.comment.strip(),
                                "updated_at": contrib.updated_at.strftime("%Y-%m-%d") if contrib.updated_at else None,
                            })

                # Build parent chain for tree display
                region_name = None
                country_name = None
                if location_type == "site" and assignment.site:
                    if assignment.site.country:
                        country_name = assignment.site.country.name
                        if assignment.site.country.region:
                            region_name = assignment.site.country.region.name
                elif location_type == "country" and assignment.country:
                    if assignment.country.region:
                        region_name = assignment.country.region.name

                features.append(
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                        "properties": {
                            "kpi_id": kpi.id,
                            "kpi_name": kpi.name,
                            "initiative_name": kpi.initiative_system_link.initiative.name if kpi.initiative_system_link and kpi.initiative_system_link.initiative else None,
                            "system_name": kpi.initiative_system_link.system.name if kpi.initiative_system_link and kpi.initiative_system_link.system else None,
                            "challenge_name": kpi.initiative_system_link.initiative.challenge_links[0].challenge.name if kpi.initiative_system_link and kpi.initiative_system_link.initiative and kpi.initiative_system_link.initiative.challenge_links else None,
                            "location_name": location_name,
                            "location_type": location_type,
                            "region_name": region_name,
                            "country_name": country_name,
                            "value": display_value,
                            "period": None,
                            "target": str(target_value) if target_value is not None else None,
                            "unit": None,
                            "comments": comments,
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


@bp.route("/api/geocode")
@login_required
def api_geocode():
    """Geocode an address using Nominatim (OpenStreetMap)"""
    import requests

    address = request.args.get("address", "").strip()
    if not address:
        return jsonify({"error": "Address is required"}), 400

    try:
        # Use Nominatim API (OpenStreetMap geocoding service)
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": "CISK-Navigator/1.0"},
            timeout=10,
        )
        response.raise_for_status()

        results = response.json()
        if not results:
            return jsonify({"error": "Address not found"}), 404

        location = results[0]
        return jsonify(
            {
                "latitude": float(location["lat"]),
                "longitude": float(location["lon"]),
                "display_name": location.get("display_name", ""),
                "address": location.get("address", {}),
            }
        )
    except requests.RequestException as e:
        return jsonify({"error": f"Geocoding service error: {str(e)}"}), 500
    except (ValueError, KeyError) as e:
        return jsonify({"error": f"Invalid response from geocoding service: {str(e)}"}), 500
