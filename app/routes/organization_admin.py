"""
Organization Administration routes

For managing business content within an organization (spaces, challenges, initiatives, etc.).
"""

import base64
import io
from datetime import datetime
from functools import wraps

from flask import Blueprint, Response, current_app, flash, jsonify, redirect, render_template, request, send_file, session, stream_with_context, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.csrf import generate_csrf
from PIL import Image
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired

from app.extensions import db
from app.forms import (
    ChallengeCreateForm,
    ChallengeEditForm,
    GovernanceBodyCreateForm,
    GovernanceBodyEditForm,
    InitiativeCreateForm,
    InitiativeEditForm,
    KPICreateForm,
    KPIEditForm,
    SpaceCreateForm,
    SpaceEditForm,
    SystemCreateForm,
    SystemEditForm,
    ValueTypeCreateForm,
    ValueTypeEditForm,
    YAMLUploadForm,
)
from app.models import (
    KPI,
    ActionItem,
    ActionItemMention,
    Challenge,
    ChallengeInitiativeLink,
    EntityLink,
    EntityTypeDefault,
    GovernanceBody,
    Initiative,
    InitiativeProgressUpdate,
    InitiativeSystemLink,
    KPIGovernanceBodyLink,
    KPIValueTypeConfig,
    Organization,
    RollupRule,
    Space,
    System,
    ValueType,
)
from app.services import AuditService, ValueTypeUsageService, YAMLExportService, YAMLImportService

bp = Blueprint("organization_admin", __name__, url_prefix="/org-admin")


class OnboardingConfirmForm(FlaskForm):
    """Simple form for onboarding confirmation steps"""

    submit = SubmitField("Continue")


class QuickStructureForm(FlaskForm):
    """Form for creating complete structure in one step"""

    # Space
    space_name = StringField("Space Name", validators=[DataRequired()], default="Corporate Strategy")
    space_desc = TextAreaField("Space Description", default="Strategic initiatives for corporate goals")

    # Challenge
    challenge_name = StringField("Challenge Name", validators=[DataRequired()], default="Reduce Environmental Impact")
    challenge_desc = TextAreaField(
        "Challenge Description", default="Minimize carbon footprint and improve sustainability"
    )

    # Initiative
    initiative_name = StringField("Initiative Name", validators=[DataRequired()], default="Energy Efficiency Program")
    initiative_desc = TextAreaField("Initiative Description", default="Reduce energy consumption across all facilities")

    # System
    system_name = StringField("System Name", validators=[DataRequired()], default="Office Buildings")
    system_desc = TextAreaField("System Description", default="All corporate office facilities")

    # KPI
    kpi_name = StringField("KPI Name", validators=[DataRequired()], default="Energy Consumption")
    kpi_desc = TextAreaField("KPI Description", default="Total energy usage measured in kWh")

    submit = SubmitField("Create Complete Structure")


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


def permission_required(permission_method_name):
    """Decorator to check user permissions for an organization"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            org_id = session.get("organization_id")
            if not org_id:
                flash("No organization context", "danger")
                return redirect(url_for("auth.login"))

            # Global admins and super admins bypass all permission checks
            if current_user.is_global_admin or current_user.is_super_admin:
                return f(*args, **kwargs)

            # Organization admins bypass all permission checks for their org
            if current_user.is_org_admin(org_id):
                return f(*args, **kwargs)

            # Check specific permission
            permission_method = getattr(current_user, permission_method_name, None)
            if not permission_method or not permission_method(org_id):
                flash("You do not have permission to perform this action", "danger")
                return redirect(url_for("organization_admin.index"))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def any_org_admin_permission_required(f):
    """Decorator to check if user has ANY management permission for the organization"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        org_id = session.get("organization_id")
        if not org_id:
            flash("No organization context", "danger")
            return redirect(url_for("auth.login"))

        # Global admins and super admins bypass all permission checks
        if current_user.is_global_admin or current_user.is_super_admin:
            return f(*args, **kwargs)

        # Organization admins have full access
        if current_user.is_org_admin(org_id):
            return f(*args, **kwargs)

        # Check if user has at least one management permission
        has_any_permission = (
            current_user.can_manage_spaces(org_id)
            or current_user.can_manage_value_types(org_id)
            or current_user.can_manage_governance_bodies(org_id)
            or current_user.can_manage_challenges(org_id)
            or current_user.can_manage_initiatives(org_id)
            or current_user.can_manage_systems(org_id)
            or current_user.can_manage_kpis(org_id)
        )

        if not has_any_permission:
            flash("You do not have permission to access organization administration", "danger")
            return redirect(url_for("workspace.dashboard"))

        return f(*args, **kwargs)

    return decorated_function


def _build_entity_nav(all_ids, current_id):
    """Build prev/next navigation context for sequential entity editing."""
    if current_id not in all_ids:
        return {"nav_pos": 0, "nav_total": len(all_ids), "prev_id": None, "next_id": None}
    pos = all_ids.index(current_id)
    return {
        "nav_pos": pos,
        "nav_total": len(all_ids),
        "prev_id": all_ids[pos - 1] if pos > 0 else None,
        "next_id": all_ids[pos + 1] if pos < len(all_ids) - 1 else None,
    }


def _handle_nav_redirect(nav_action, prev_id, next_id, url_func, id_param, fallback_url):
    """Handle save+navigate redirect. Returns redirect or None."""
    if nav_action == "prev" and prev_id:
        return redirect(url_for(url_func, **{id_param: prev_id}))
    elif nav_action == "next" and next_id:
        return redirect(url_for(url_func, **{id_param: next_id}))
    return None


# Porter's Five Forces Analysis (Organization Level)


@bp.route("/porters")
@login_required
@organization_required
def organization_porters():
    """View Porter's Five Forces analysis for the organization"""
    org_id = session.get("organization_id")
    org = Organization.query.get_or_404(org_id)
    return render_template("organization_admin/organization_porters.html", organization=org, csrf_token=generate_csrf)


# Strategic Pillars (Organization Level)


@bp.route("/strategy", methods=["GET", "POST"])
@login_required
@organization_required
def strategy():
    """Edit strategic pillars"""
    import json as _json

    from app.models import Organization, StrategicPillar

    org_id = session.get("organization_id")
    org = Organization.query.get(org_id) if org_id else None
    if not (org and org.strategy_enabled):
        flash("Strategy is not enabled for this organization.", "warning")
        return redirect(url_for("organization_admin.index"))

    org_id = session.get("organization_id")

    if request.method == "POST":
        # Parse pillars JSON from form
        pillars_json = request.form.get("pillars_json", "[]")
        try:
            pillars_data = _json.loads(pillars_json)
        except (ValueError, TypeError):
            flash("Invalid data", "danger")
            return redirect(url_for("organization_admin.strategy"))

        # Delete existing pillars
        StrategicPillar.query.filter_by(organization_id=org_id).delete()
        db.session.flush()

        # Create new ones
        import base64 as _b64

        for i, p in enumerate(pillars_data):
            pillar = StrategicPillar(
                organization_id=org_id,
                name=p.get("name", "").strip(),
                description=p.get("description", "").strip(),
                accent_color=p.get("accent_color", "#3b82f6"),
                bs_icon=p.get("bs_icon", ""),
                display_order=i,
            )
            # Handle icon image from base64 data URL — resize to max 200x200
            icon_b64 = p.get("icon_b64") or ""
            if icon_b64.startswith("data:"):
                try:
                    from io import BytesIO

                    from PIL import Image

                    header, data = icon_b64.split(",", 1)
                    raw = _b64.b64decode(data)
                    img = Image.open(BytesIO(raw))
                    img.thumbnail((200, 200), Image.LANCZOS)
                    buf = BytesIO()
                    fmt = "PNG" if img.mode == "RGBA" else "JPEG"
                    img.save(buf, format=fmt, quality=85, optimize=True)
                    pillar.icon_data = buf.getvalue()
                    pillar.icon_mime_type = f"image/{fmt.lower()}"
                    pillar.bs_icon = ""
                except (ValueError, IndexError, Exception):
                    pass
            db.session.add(pillar)

        db.session.commit()
        flash("Strategy updated successfully", "success")
        return redirect(url_for("organization_admin.strategy"))

    pillars = (
        StrategicPillar.query.filter_by(organization_id=org_id)
        .order_by(StrategicPillar.display_order)
        .all()
    )
    return render_template("organization_admin/strategy.html", pillars=pillars, csrf_token=generate_csrf)


# Decision Tags Configuration


@bp.route("/decision-tags", methods=["GET", "POST"])
@login_required
@organization_required
@any_org_admin_permission_required
def decision_tags():
    """Configure decision tag categories"""
    import json as _json

    org_id = session.get("organization_id")
    org = Organization.query.get(org_id)

    if request.method == "POST":
        tags_json = request.form.get("decision_tags_json", "")
        if tags_json:
            try:
                org.decision_tags = _json.loads(tags_json)
            except (ValueError, TypeError):
                pass
        db.session.commit()
        flash("Decision tags updated", "success")
        return redirect(url_for("organization_admin.decision_tags"))

    default_tags = ["scope", "budget", "timeline", "resource", "technical", "governance", "other"]
    current_tags = org.decision_tags or default_tags

    # Find used tags
    from app.models import InitiativeProgressUpdate

    _used_tags = set()
    _tag_updates = InitiativeProgressUpdate.query.join(Initiative).filter(
        Initiative.organization_id == org_id, InitiativeProgressUpdate.decisions.isnot(None)
    ).all()
    for _tu in _tag_updates:
        decs = _tu.decisions
        if isinstance(decs, str):
            try:
                decs = _json.loads(decs)
            except (ValueError, TypeError):
                decs = []
        if isinstance(decs, list):
            for _d in decs:
                if _d.get("tag"):
                    _used_tags.add(_d["tag"])

    return render_template(
        "organization_admin/decision_tags.html",
        current_tags=current_tags,
        used_tags=list(_used_tags),
        csrf_token=generate_csrf,
    )


# Impact Levels Configuration


@bp.route("/impact-levels", methods=["GET", "POST"])
@login_required
@organization_required
@any_org_admin_permission_required
def impact_levels():
    """Configure the 3-level impact scale for this organization"""
    from app.models import ImpactLevel

    org_id = session.get("organization_id")

    # Ensure defaults exist
    ImpactLevel.ensure_defaults(org_id)
    db.session.commit()

    org = Organization.query.get(org_id)

    if request.method == "POST":
        for lvl in [1, 2, 3]:
            il = ImpactLevel.query.filter_by(organization_id=org_id, level=lvl).first()
            if il:
                il.label = request.form.get(f"label_{lvl}", il.label).strip()
                il.icon = request.form.get(f"icon_{lvl}", il.icon).strip()
                il.weight = int(request.form.get(f"weight_{lvl}", il.weight))
                il.color = request.form.get(f"color_{lvl}", il.color).strip()
        # Save calculation method
        org.impact_calc_method = request.form.get("calc_method", "geometric_mean")
        # Save custom QFD matrix if provided
        import json as _json
        matrix_json = request.form.get("qfd_matrix_json", "")
        if matrix_json:
            try:
                org.impact_qfd_matrix = _json.loads(matrix_json)
            except (ValueError, TypeError):
                pass
        # Save custom reinforcement weights if provided
        reinforce_json = request.form.get("reinforce_json", "")
        if reinforce_json:
            try:
                org.impact_reinforce_weights = _json.loads(reinforce_json)
            except (ValueError, TypeError):
                pass
        # Save decision tags
        tags_json = request.form.get("decision_tags_json", "")
        if tags_json:
            try:
                org.decision_tags = _json.loads(tags_json)
            except (ValueError, TypeError):
                pass
        db.session.commit()
        flash("Impact levels updated successfully", "success")
        return redirect(url_for("organization_admin.impact_levels"))

    levels = ImpactLevel.query.filter_by(organization_id=org_id).order_by(ImpactLevel.level).all()

    return render_template(
        "organization_admin/impact_levels.html",
        levels=levels,
        csrf_token=generate_csrf,
        calc_method=org.impact_calc_method or "geometric_mean",
        qfd_matrix=org.impact_qfd_matrix,
        reinforce_weights=org.impact_reinforce_weights,
    )


@bp.route("/porters/edit", methods=["GET", "POST"])
@login_required
@organization_required
def edit_organization_porters():
    """Edit Porter's Five Forces analysis for the organization"""
    org_id = session.get("organization_id")

    # Check permission to edit Porter's
    if not current_user.can_edit_porters(org_id):
        flash("You do not have permission to edit Porter's Five Forces analysis", "danger")
        return redirect(url_for("organization_admin.organization_porters"))

    org = Organization.query.get_or_404(org_id)

    if request.method == "POST":
        org.porters_new_entrants = request.form.get("porters_new_entrants", "").strip() or None
        org.porters_suppliers = request.form.get("porters_suppliers", "").strip() or None
        org.porters_buyers = request.form.get("porters_buyers", "").strip() or None
        org.porters_substitutes = request.form.get("porters_substitutes", "").strip() or None
        org.porters_rivalry = request.form.get("porters_rivalry", "").strip() or None

        db.session.commit()
        flash(f"Porter's Five Forces analysis for {org.name} updated successfully", "success")
        return redirect(url_for("organization_admin.organization_porters"))

    return render_template(
        "organization_admin/edit_organization_porters.html", organization=org, csrf_token=generate_csrf
    )


@bp.route("/")
@login_required
@organization_required
@any_org_admin_permission_required
def index():
    """Organization administration dashboard"""
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

    # Get all stats for the organization
    spaces_count = Space.query.filter_by(organization_id=org_id).count()
    challenges_count = Challenge.query.filter_by(organization_id=org_id).count()
    initiatives_count = Initiative.query.filter_by(organization_id=org_id).count()
    systems_count = System.query.filter_by(organization_id=org_id).count()
    value_types_count = ValueType.query.filter_by(organization_id=org_id, is_active=True).count()
    governance_bodies_count = GovernanceBody.query.filter_by(organization_id=org_id, is_active=True).count()

    # Count KPIs
    kpis_count = (
        db.session.query(KPI)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
        .filter(Initiative.organization_id == org_id)
        .count()
    )

    # Count geography entities
    from app.models import GeographyCountry, GeographyRegion, GeographySite

    geography_regions_count = GeographyRegion.query.filter_by(organization_id=org_id).count()
    geography_countries_count = (
        db.session.query(GeographyCountry)
        .join(GeographyRegion)
        .filter(GeographyRegion.organization_id == org_id)
        .count()
    )
    geography_sites_count = (
        db.session.query(GeographySite)
        .join(GeographyCountry)
        .join(GeographyRegion)
        .filter(GeographyRegion.organization_id == org_id)
        .count()
    )

    stats = {
        "spaces": spaces_count,
        "challenges": challenges_count,
        "initiatives": initiatives_count,
        "systems": systems_count,
        "kpis": kpis_count,
        "value_types": value_types_count,
        "governance_bodies": governance_bodies_count,
        "geography_regions": geography_regions_count,
        "geography_countries": geography_countries_count,
        "geography_sites": geography_sites_count,
    }

    # Create empty form for CSRF token
    form = FlaskForm()
    org = Organization.query.get(org_id)

    return render_template(
        "organization_admin/index.html", org_name=org_name, stats=stats, form=form, csrf_token=generate_csrf, org=org
    )


@bp.route("/onboarding", methods=["GET", "POST"])
@login_required
@organization_required
def onboarding():
    """Improved organization onboarding wizard - creates complete working example"""
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

    # Ensure entity type defaults exist for this organization (for icons/logos)
    EntityTypeDefault.ensure_defaults_exist(org_id)

    # Get step from query parameter (default to 1)
    step = request.args.get("step", 1, type=int)

    # Check what's already been created
    spaces_count = Space.query.filter_by(organization_id=org_id).count()
    governance_bodies_count = GovernanceBody.query.filter_by(organization_id=org_id).count()
    value_types_count = ValueType.query.filter_by(organization_id=org_id).count()
    kpis_count = (
        db.session.query(KPI)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
        .filter(Initiative.organization_id == org_id)
        .count()
    )

    # If everything is set up, skip to completion
    if spaces_count > 0 and governance_bodies_count > 0 and value_types_count > 0 and kpis_count > 0:
        step = 5

    # Initialize forms based on step
    form = None

    # STEP 2: Create Value Types (with better defaults including CO2)
    if step == 2:
        form = OnboardingConfirmForm()
        if form.validate_on_submit():
            # Create better default value types
            default_value_types = [
                {
                    "name": "Cost",
                    "kind": "numeric",
                    "numeric_format": "decimal",
                    "decimal_places": 2,
                    "unit_label": "€",
                    "default_aggregation_formula": "sum",
                },
                {
                    "name": "CO2 Emissions",
                    "kind": "numeric",
                    "numeric_format": "decimal",
                    "decimal_places": 2,
                    "unit_label": "tCO2e",
                    "default_aggregation_formula": "sum",
                },
                {
                    "name": "Risk Level",
                    "kind": "risk",
                },
            ]

            for vt_data in default_value_types:
                vt = ValueType(organization_id=org_id, **vt_data)
                db.session.add(vt)
                AuditService.log_create(
                    "ValueType",
                    vt.id if vt.id else 0,
                    vt.name,
                    {"kind": vt.kind},
                )

            db.session.commit()
            flash(f"Created {len(default_value_types)} value types: Cost, CO2 Emissions, Risk Level", "success")
            return redirect(url_for("organization_admin.onboarding", step=3))

    # STEP 3: Create Governance Body (simplified, with explanation)
    elif step == 3:
        form = GovernanceBodyCreateForm()
        # Pre-fill default
        if request.method == "GET":
            form.name.data = "Management Board"
            form.abbreviation.data = "MB"
            form.description.data = "Strategic oversight and decision-making"
            form.color.data = "#3498db"

        if form.validate_on_submit():
            gov_body = GovernanceBody(
                name=form.name.data,
                abbreviation=form.abbreviation.data,
                description=form.description.data,
                color=form.color.data,
                is_active=True,
                organization_id=org_id,
            )
            db.session.add(gov_body)
            db.session.flush()  # Get ID

            AuditService.log_create(
                "GovernanceBody",
                gov_body.id,
                gov_body.name,
                {"abbreviation": gov_body.abbreviation},
            )

            db.session.commit()
            flash(f"Governance body '{gov_body.name}' created successfully", "success")
            return redirect(url_for("organization_admin.onboarding", step=4))

    # STEP 4: Create Complete Structure (Space → Challenge → Initiative → System → KPI)
    elif step == 4:
        form = QuickStructureForm()
        if form.validate_on_submit():
            try:
                # Create Space
                space = Space(
                    name=form.space_name.data,
                    description=form.space_desc.data,
                    organization_id=org_id,
                    created_by=current_user.id,
                )
                db.session.add(space)
                db.session.flush()

                # Create Challenge
                challenge = Challenge(
                    name=form.challenge_name.data,
                    description=form.challenge_desc.data,
                    space_id=space.id,
                    organization_id=org_id,
                )
                db.session.add(challenge)
                db.session.flush()

                # Create Initiative
                initiative = Initiative(
                    name=form.initiative_name.data,
                    description=form.initiative_desc.data,
                    organization_id=org_id,
                )
                db.session.add(initiative)
                db.session.flush()

                # Link Initiative to Challenge
                link = ChallengeInitiativeLink(challenge_id=challenge.id, initiative_id=initiative.id)
                db.session.add(link)

                # Create System
                system = System(
                    name=form.system_name.data,
                    description=form.system_desc.data,
                    organization_id=org_id,
                )
                db.session.add(system)
                db.session.flush()

                # Link System to Initiative
                sys_link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id)
                db.session.add(sys_link)
                db.session.flush()  # Need sys_link.id for KPI

                # Create KPI
                kpi = KPI(
                    name=form.kpi_name.data,
                    description=form.kpi_desc.data,
                    initiative_system_link_id=sys_link.id,
                )
                db.session.add(kpi)
                db.session.flush()

                # Link KPI to all value types
                value_types = ValueType.query.filter_by(organization_id=org_id).all()
                for vt in value_types:
                    config = KPIValueTypeConfig(
                        kpi_id=kpi.id,
                        value_type_id=vt.id,
                        calculation_type="manual",
                    )
                    db.session.add(config)

                # Link KPI to governance body
                gov_body = GovernanceBody.query.filter_by(organization_id=org_id).first()
                if gov_body:
                    gb_link = KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=gov_body.id)
                    db.session.add(gb_link)

                # Audit logs
                AuditService.log_create("Space", space.id, space.name, {})
                AuditService.log_create("Challenge", challenge.id, challenge.name, {})
                AuditService.log_create("Initiative", initiative.id, initiative.name, {})
                AuditService.log_create("System", system.id, system.name, {})
                AuditService.log_create("KPI", kpi.id, kpi.name, {})

                db.session.commit()

                # Store summary for completion page
                session["onboarding_summary"] = {
                    "space": space.name,
                    "challenge": challenge.name,
                    "initiative": initiative.name,
                    "system": system.name,
                    "kpi": kpi.name,
                }

                flash("🎉 Complete structure created successfully!", "success")
                return redirect(url_for("organization_admin.onboarding", step=5))

            except Exception as e:
                db.session.rollback()
                flash(f"Error creating structure: {str(e)}", "danger")

    if form is None:
        form = OnboardingConfirmForm()

    # Get entity type defaults with logos
    entity_defaults_raw = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
    entity_defaults = {}
    for default in entity_defaults_raw:
        logo_url = None
        if default.default_logo_data and default.default_logo_mime_type:
            logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
        entity_defaults[default.entity_type] = {
            "color": default.default_color,
            "icon": default.default_icon,
            "logo": logo_url,
        }

    return render_template(
        "organization_admin/onboarding.html",
        org_name=org_name,
        step=step,
        form=form,
        entity_defaults=entity_defaults,
        csrf_token=generate_csrf,
    )


# Organization Settings (Logo, Branding)


@bp.route("/links")
@login_required
@organization_required
@any_org_admin_permission_required
def organization_links():
    """Organization-level links management"""
    org_id = session.get("organization_id")
    org = Organization.query.get_or_404(org_id)
    from app.models import EntityLink
    entity_links = EntityLink.get_links_for_entity("organization", org_id, current_user.id, include_private=True)
    form = FlaskForm()  # For CSRF
    return render_template(
        "organization_admin/organization_links.html",
        organization=org, form=form, csrf_token=generate_csrf,
        entity_links=entity_links,
    )


@bp.route("/link-health")
@login_required
@organization_required
@any_org_admin_permission_required
def link_health():
    """Link health dashboard — shows all org entity links with status."""
    from collections import Counter

    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

    links_with_entity = _get_all_org_links_enriched(org_id)

    total = len(links_with_entity)
    checked = sum(1 for l in links_with_entity if l["link"].last_checked_at is not None)
    broken = sum(1 for l in links_with_entity if l["link"].link_status == "invalid")
    unreachable = sum(1 for l in links_with_entity if l["link"].link_status == "unreachable")

    status_counts = Counter(row["link"].link_status for row in links_with_entity)
    entity_type_counts = Counter(row["link"].entity_type for row in links_with_entity)

    return render_template(
        "organization_admin/link_health.html",
        organization_name=org_name,
        links=links_with_entity,
        total=total,
        checked=checked,
        broken=broken,
        unreachable=unreachable,
        status_counts=status_counts,
        entity_type_counts=entity_type_counts,
        csrf_token=generate_csrf,
    )


@bp.route("/link-health/stream")
@login_required
@organization_required
@any_org_admin_permission_required
def link_health_stream():
    """SSE endpoint — probes org entity links in real time and streams results.
    Accepts optional query params: status=<link_status>, entity_type=<type>
    """
    import json as _json

    org_id = session.get("organization_id")
    status_filter = request.args.get("status", "").strip()
    entity_type_filter = request.args.get("entity_type", "").strip()

    all_rows = _get_all_org_links_enriched(org_id)
    link_ids = [
        row["link"].id for row in all_rows
        if (not status_filter or row["link"].link_status == status_filter)
        and (not entity_type_filter or row["link"].entity_type == entity_type_filter)
    ]

    def generate():
        total = len(link_ids)
        for i, link_id in enumerate(link_ids):
            link = EntityLink.query.get(link_id)
            if not link:
                continue
            try:
                result = link.probe_and_save()
                db.session.commit()
            except Exception as e:
                result = {
                    "status": "unknown", "detected_type": None,
                    "bs_icon": "bi-link-45deg", "icon_color": "#6c757d",
                    "type_label": "", "status_label": "Error",
                    "status_color": "#dc3545", "status_bg": "danger",
                    "status_icon": "bi-exclamation-circle", "error": str(e)[:80],
                }
                db.session.rollback()

            payload = {
                "link_id": link_id,
                "status": result["status"],
                "detected_type": result.get("detected_type"),
                "bs_icon": result.get("bs_icon", "bi-link-45deg"),
                "icon_color": result.get("icon_color", "#6c757d"),
                "type_label": result.get("type_label", ""),
                "status_label": result.get("status_label", ""),
                "status_color": result.get("status_color", "#6c757d"),
                "status_bg": result.get("status_bg", "secondary"),
                "status_icon": result.get("status_icon", "bi-question-circle"),
                "status_code": result.get("status_code"),
                "progress": i + 1,
                "total": total,
            }
            yield f"data: {_json.dumps(payload)}\n\n"

        yield f"data: {_json.dumps({'done': True, 'total': total})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _get_all_org_links_enriched(org_id):
    """
    Return all entity links for an org, each wrapped with resolved entity name.
    Returns list of dicts: {link, entity_name, entity_label}
    """
    # Collect all entity links scoped to this org
    space_ids = db.session.query(Space.id).filter_by(organization_id=org_id).subquery()
    challenge_ids = db.session.query(Challenge.id).filter_by(organization_id=org_id).subquery()
    initiative_ids = db.session.query(Initiative.id).filter_by(organization_id=org_id).subquery()
    system_ids = db.session.query(System.id).filter_by(organization_id=org_id).subquery()
    kpi_ids = (
        db.session.query(KPI.id)
        .join(KPI.initiative_system_link)
        .join(InitiativeSystemLink.initiative)
        .filter(Initiative.organization_id == org_id)
        .subquery()
    )

    org_filter = db.or_(
        db.and_(EntityLink.entity_type == "organization", EntityLink.entity_id == org_id),
        db.and_(EntityLink.entity_type == "space", EntityLink.entity_id.in_(space_ids)),
        db.and_(EntityLink.entity_type == "challenge", EntityLink.entity_id.in_(challenge_ids)),
        db.and_(EntityLink.entity_type == "initiative", EntityLink.entity_id.in_(initiative_ids)),
        db.and_(EntityLink.entity_type == "system", EntityLink.entity_id.in_(system_ids)),
        db.and_(EntityLink.entity_type == "kpi", EntityLink.entity_id.in_(kpi_ids)),
    )

    links = EntityLink.query.filter(org_filter).order_by(EntityLink.entity_type, EntityLink.entity_id).all()

    # Build lookup maps for entity names
    spaces = {s.id: s.name for s in Space.query.filter_by(organization_id=org_id).all()}
    challenges = {c.id: c.name for c in Challenge.query.filter_by(organization_id=org_id).all()}
    initiatives = {i.id: i.name for i in Initiative.query.filter_by(organization_id=org_id).all()}
    systems = {s.id: s.name for s in System.query.filter_by(organization_id=org_id).all()}
    kpi_map = {
        k.id: k.name
        for k in db.session.query(KPI).join(KPI.initiative_system_link)
        .join(InitiativeSystemLink.initiative).filter(Initiative.organization_id == org_id).all()
    }

    name_maps = {
        "space": spaces, "challenge": challenges, "initiative": initiatives,
        "system": systems, "kpi": kpi_map,
    }
    type_labels = {
        "space": "Space", "challenge": "Challenge", "initiative": "Initiative",
        "system": "System", "kpi": "KPI", "organization": "Organization",
        "action_item": "Action Item",
    }

    result = []
    for link in links:
        nm = name_maps.get(link.entity_type, {})
        entity_name = nm.get(link.entity_id, f"#{link.entity_id}")
        result.append({
            "link": link,
            "entity_name": entity_name,
            "entity_label": type_labels.get(link.entity_type, link.entity_type.title()),
        })
    return result


@bp.route("/settings/toggle-strategy", methods=["POST"])
@login_required
@organization_required
@any_org_admin_permission_required
def toggle_strategy():
    """Toggle strategy feature on/off for this organization"""
    org_id = session.get("organization_id")
    org = Organization.query.get_or_404(org_id)
    org.strategy_enabled = not org.strategy_enabled
    db.session.commit()
    flash(f"Strategy {'enabled' if org.strategy_enabled else 'disabled'}.", "success")
    return redirect(url_for("organization_admin.index"))


@bp.route("/settings/upload-logo", methods=["POST"])
@login_required
@organization_required
@any_org_admin_permission_required
def upload_logo():
    """Upload organization logo with automatic resizing"""
    import io
    import os

    from PIL import Image

    org_id = session.get("organization_id")
    org = Organization.query.get_or_404(org_id)

    if "logo" not in request.files:
        flash("No file uploaded", "danger")
        return redirect(url_for("organization_admin.branding_manager"))

    file = request.files["logo"]
    if file.filename == "":
        flash("No file selected", "danger")
        return redirect(url_for("organization_admin.branding_manager"))

    # Validate file type
    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        flash("Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP", "danger")
        return redirect(url_for("organization_admin.branding_manager"))

    # Validate file size (max 5MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 5 * 1024 * 1024:  # 5MB
        flash("File too large. Maximum size: 5MB", "danger")
        return redirect(url_for("organization_admin.branding_manager"))

    try:
        # Read image
        image = Image.open(file)

        # Convert RGBA to RGB if needed (for JPEG compatibility)
        if image.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
            image = background

        # Resize maintaining aspect ratio (max 200x200)
        max_size = (200, 200)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Save to bytes
        output = io.BytesIO()
        image_format = "PNG" if ext in ("png", "webp") else "JPEG"
        mime_type = f"image/{ext}" if ext in ("png", "webp") else "image/jpeg"
        image.save(output, format=image_format, quality=85, optimize=True)
        logo_data = output.getvalue()

        # Store in database
        org.logo_data = logo_data
        org.logo_mime_type = mime_type
        db.session.commit()

        # Update session with new logo URL
        session["organization_logo"] = url_for("logo.organization_logo", entity_id=org.id)

        flash("Logo uploaded successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error uploading logo: {str(e)}", "danger")

    return redirect(url_for("organization_admin.branding_manager"))


@bp.route("/settings/delete-logo", methods=["POST"])
@login_required
@organization_required
@any_org_admin_permission_required
def delete_logo():
    """Delete organization logo"""
    org_id = session.get("organization_id")
    org = Organization.query.get_or_404(org_id)

    if org.logo_data:
        try:
            # Clear logo from database
            org.logo_data = None
            org.logo_mime_type = None
            db.session.commit()

            # Clear from session
            session["organization_logo"] = None

            flash("Logo deleted successfully", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting logo: {str(e)}", "danger")
    else:
        flash("No logo to delete", "info")

    return redirect(url_for("organization_admin.branding_manager"))


@bp.route("/branding")
@login_required
@organization_required
@any_org_admin_permission_required
def branding_manager():
    """Branding manager - manage colors, icons, and logos for all entity types"""
    import base64

    org_id = session.get("organization_id")
    org = Organization.query.get_or_404(org_id)

    # Ensure defaults exist for this organization
    EntityTypeDefault.ensure_defaults_exist(org_id)

    # Get entity defaults for this organization (color and icon only)
    entity_defaults = EntityTypeDefault.get_all_defaults(org_id)

    # Get full entity defaults with logos
    entity_defaults_full = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
    entity_default_logos = {}
    for default in entity_defaults_full:
        if default.default_logo_data and default.default_logo_mime_type:
            logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
            entity_default_logos[default.entity_type] = logo_url

    # Hardcoded fallbacks
    entity_defaults_hardcoded = EntityTypeDefault.get_hardcoded_defaults()

    return render_template(
        "organization_admin/branding_manager.html",
        organization=org,
        entity_defaults=entity_defaults,
        entity_default_logos=entity_default_logos,
        entity_defaults_hardcoded=entity_defaults_hardcoded,
        csrf_token=generate_csrf,
    )


@bp.route("/branding/update", methods=["POST"])
@login_required
@organization_required
@any_org_admin_permission_required
def update_branding():
    """Update branding (colors and icons) for all entity types"""
    org_id = session.get("organization_id")

    try:
        entity_types = ["organization", "space", "challenge", "initiative", "system", "kpi",
                        "action_urgent", "action_high", "action_medium", "action_low"]

        for entity_type in entity_types:
            color = request.form.get(f"{entity_type}_color")
            icon = request.form.get(f"{entity_type}_icon")

            if color and icon:
                # Get or create entity default for this organization
                entity_default = EntityTypeDefault.query.filter_by(
                    organization_id=org_id, entity_type=entity_type
                ).first()

                if entity_default:
                    entity_default.default_color = color
                    entity_default.default_icon = icon
                    entity_default.updated_by = current_user.id
                    entity_default.updated_at = datetime.utcnow()
                else:
                    # Create new default
                    entity_default = EntityTypeDefault(
                        organization_id=org_id,
                        entity_type=entity_type,
                        default_color=color,
                        default_icon=icon,
                        display_name=entity_type.title(),
                        updated_by=current_user.id,
                    )
                    db.session.add(entity_default)

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/logo-manager")
@login_required
@organization_required
@any_org_admin_permission_required
def logo_manager():
    """Logo manager - manage all entity logos for this organization (legacy, redirects to branding)"""
    return redirect(url_for("organization_admin.branding_manager"))


@bp.route("/logo-manager/upload", methods=["POST"])
@login_required
@organization_required
@any_org_admin_permission_required
def upload_entity_logo():
    """Upload logo - for organization OR default logo for entity type"""
    import os

    org_id = session.get("organization_id")
    entity_type = request.form.get("entity_type")
    entity_id = request.form.get("entity_id")

    if "logo" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files["logo"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    # Validate file type
    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        return jsonify({"success": False, "error": "Invalid file type"}), 400

    # Validate file size (max 5MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 5 * 1024 * 1024:
        return jsonify({"success": False, "error": "File too large (max 5MB)"}), 400

    try:
        # Read and process image
        image = Image.open(file)

        # Convert RGBA to RGB if needed
        if image.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
            image = background

        # Resize maintaining aspect ratio (max 200x200)
        max_size = (200, 200)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Save to bytes
        output = io.BytesIO()
        image_format = "PNG" if ext in ("png", "webp") else "JPEG"
        mime_type = f"image/{ext}" if ext in ("png", "webp") else "image/jpeg"
        image.save(output, format=image_format, quality=85, optimize=True)
        logo_data = output.getvalue()

        # Store based on entity type
        if entity_type == "organization":
            # Individual organization logo
            org = Organization.query.get_or_404(entity_id)
            if org.id != org_id:
                return jsonify({"success": False, "error": "Unauthorized"}), 403
            org.logo_data = logo_data
            org.logo_mime_type = mime_type
            db.session.commit()
            # Update session
            session["organization_logo"] = url_for("logo.organization_logo", entity_id=org.id)
        else:
            # Default logo for entity type
            entity_default = EntityTypeDefault.query.filter_by(organization_id=org_id, entity_type=entity_type).first()

            if not entity_default:
                # Create if doesn't exist
                entity_default = EntityTypeDefault(
                    organization_id=org_id,
                    entity_type=entity_type,
                    default_color=EntityTypeDefault.get_hardcoded_defaults()[entity_type]["color"],
                    default_icon=EntityTypeDefault.get_hardcoded_defaults()[entity_type]["icon"],
                    display_name=entity_type.title(),
                    description="",
                )
                db.session.add(entity_default)

            entity_default.default_logo_data = logo_data
            entity_default.default_logo_mime_type = mime_type
            db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/logo-manager/apply-template", methods=["POST"])
@login_required
@organization_required
@any_org_admin_permission_required
def apply_logo_template():
    """Apply logo template (AJAX endpoint)"""
    org_id = session.get("organization_id")
    data = request.get_json()
    entity_type = data.get("entity_type")
    entity_id = data.get("entity_id")
    template_url = data.get("template_url")

    try:
        # Extract SVG data from data URL first
        if not template_url.startswith("data:image/svg+xml"):
            return jsonify({"success": False, "error": "Invalid template URL format"}), 400

        # Decode SVG data - handle both formats with and without charset
        if ";charset=utf-8," in template_url:
            svg_data = template_url.split(";charset=utf-8,", 1)[1]
        elif "," in template_url:
            svg_data = template_url.split(",", 1)[1]
        else:
            return jsonify({"success": False, "error": "Invalid SVG data URL format"}), 400

        # URL decode
        from urllib.parse import unquote

        svg_data = unquote(svg_data)
        svg_bytes = svg_data.encode("utf-8")

        # Organization logos are stored on the Organization model
        if entity_type == "organization":
            entity = Organization.query.get_or_404(entity_id)
            if entity.id != org_id:
                return jsonify({"success": False, "error": "Unauthorized"}), 403
            entity.logo_data = svg_bytes
            entity.logo_mime_type = "image/svg+xml"
            db.session.commit()
            session["organization_logo"] = url_for("logo.organization_logo", entity_id=entity.id)
        else:
            # All other entity type logos are stored in EntityTypeDefault
            entity_default = EntityTypeDefault.query.filter_by(organization_id=org_id, entity_type=entity_type).first()

            if not entity_default:
                # Create if doesn't exist
                entity_default = EntityTypeDefault(
                    organization_id=org_id,
                    entity_type=entity_type,
                    default_color=EntityTypeDefault.get_hardcoded_defaults()[entity_type]["color"],
                    default_icon=EntityTypeDefault.get_hardcoded_defaults()[entity_type]["icon"],
                    display_name=entity_type.title(),
                    description="",
                )
                db.session.add(entity_default)

            entity_default.default_logo_data = svg_bytes
            entity_default.default_logo_mime_type = "image/svg+xml"
            db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/logo-manager/delete", methods=["POST"])
@login_required
@organization_required
@any_org_admin_permission_required
def delete_entity_logo():
    """Delete entity logo (AJAX endpoint)"""
    org_id = session.get("organization_id")
    data = request.get_json()
    entity_type = data.get("entity_type")
    entity_id = data.get("entity_id")

    try:
        # Organization logos are stored on the Organization model
        if entity_type == "organization":
            entity = Organization.query.get_or_404(entity_id)
            if entity.id != org_id:
                return jsonify({"success": False, "error": "Unauthorized"}), 403
            entity.logo_data = None
            entity.logo_mime_type = None
            db.session.commit()
            session["organization_logo"] = None
        else:
            # All other entity type logos are stored in EntityTypeDefault
            entity_default = EntityTypeDefault.query.filter_by(organization_id=org_id, entity_type=entity_type).first()

            if entity_default:
                entity_default.default_logo_data = None
                entity_default.default_logo_mime_type = None
                db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# Space Management


@bp.route("/spaces")
@login_required
@organization_required
def spaces():
    """Redirect to workspace - modern interface with Edit Mode"""
    flash("Use the Workspace view to manage your organization structure with Edit Mode toggle.", "info")
    return redirect(url_for("workspace.index"))


@bp.route("/spaces/create", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_spaces")
def create_space():
    """Create a new space"""
    form = SpaceCreateForm()

    if form.validate_on_submit():
        space = Space(
            organization_id=session.get("organization_id"),
            name=form.name.data,
            description=form.description.data,
            space_label=form.space_label.data,
            display_order=form.display_order.data,
            is_private=form.is_private.data,
            created_by=current_user.id,
            impact_level=int(request.form.get("impact_level")) if request.form.get("impact_level") else None,
        )
        db.session.add(space)
        db.session.flush()

        # Audit log
        AuditService.log_create(
            "Space",
            space.id,
            space.name,
            {
                "description": space.description,
                "space_label": space.space_label,
                "is_private": space.is_private,
                "organization_id": space.organization_id,
            },
        )

        db.session.commit()
        flash(f"Space {space.name} created successfully", "success")
        return redirect(url_for("workspace.index", auto_edit=1))

    return render_template("organization_admin/create_space.html", form=form, csrf_token=generate_csrf)


@bp.route("/spaces/<int:space_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_spaces")
def edit_space(space_id):
    """Edit an existing space"""
    org_id = session.get("organization_id")
    space = Space.query.filter_by(id=space_id, organization_id=org_id).first_or_404()

    # Sequential nav
    all_ids = [s.id for s in Space.query.filter_by(organization_id=org_id).order_by(Space.display_order, Space.name).all()]
    nav = _build_entity_nav(all_ids, space_id)

    form = SpaceEditForm(obj=space)

    if form.validate_on_submit():
        # Capture old values for audit
        old_values = {
            "name": space.name,
            "description": space.description,
            "space_label": space.space_label,
            "is_private": space.is_private,
        }

        space.name = form.name.data
        space.description = form.description.data
        space.space_label = form.space_label.data
        space.display_order = form.display_order.data
        space.is_private = form.is_private.data
        space.impact_level = int(request.form.get("impact_level")) if request.form.get("impact_level") else None

        # Audit log
        new_values = {
            "name": space.name,
            "description": space.description,
            "space_label": space.space_label,
            "is_private": space.is_private,
        }
        AuditService.log_update("Space", space.id, space.name, old_values, new_values)

        db.session.commit()

        nav_redir = _handle_nav_redirect(request.form.get("nav_action"), nav["prev_id"], nav["next_id"],
                                          "organization_admin.edit_space", "space_id", None)
        if nav_redir:
            return nav_redir
        flash(f"Space {space.name} updated successfully", "success")
        return redirect(url_for("workspace.index", auto_edit=1))

    # Get entity type defaults with logos
    entity_defaults_raw = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
    entity_defaults = {}
    for default in entity_defaults_raw:
        logo_url = None
        if default.default_logo_data and default.default_logo_mime_type:
            logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
        entity_defaults[default.entity_type] = {
            "color": default.default_color,
            "icon": default.default_icon,
            "logo": logo_url,
        }

    # Get entity links for this space
    entity_links = EntityLink.get_links_for_entity("space", space.id, current_user.id, include_private=True)

    return render_template(
        "organization_admin/edit_space.html",
        form=form,
        space=space,
        entity_defaults=entity_defaults,
        entity_links=entity_links,
        csrf_token=generate_csrf,
        current_impact=space.impact_level,
        **nav,
    )


@bp.route("/spaces/<int:space_id>/delete", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_spaces")
def delete_space(space_id):
    """Delete a space"""
    org_id = session.get("organization_id")
    space = Space.query.filter_by(id=space_id, organization_id=org_id).first_or_404()

    space_name = space.name
    space_id_for_audit = space.id
    space_details = {
        "description": space.description,
        "space_label": space.space_label,
        "is_private": space.is_private,
        "organization_id": space.organization_id,
    }

    db.session.delete(space)

    # Audit log
    AuditService.log_delete("Space", space_id_for_audit, space_name, space_details)

    db.session.commit()
    flash(f"Space {space_name} deleted successfully", "success")
    return redirect(url_for("workspace.index"))


@bp.route("/spaces/<int:space_id>", methods=["DELETE"])
@login_required
@organization_required
@permission_required("can_manage_spaces")
def delete_space_api(space_id):
    """Delete a space (REST API endpoint)"""
    try:
        org_id = session.get("organization_id")
        space = Space.query.filter_by(id=space_id, organization_id=org_id).first_or_404()

        space_name = space.name
        space_id_for_audit = space.id
        space_details = {
            "description": space.description,
            "space_label": space.space_label,
            "is_private": space.is_private,
            "organization_id": space.organization_id,
        }

        db.session.delete(space)

        # Audit log
        AuditService.log_delete("Space", space_id_for_audit, space_name, space_details)

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/spaces/<int:space_id>/swot")
@login_required
@organization_required
def space_swot(space_id):
    """View SWOT analysis for a space"""
    org_id = session.get("organization_id")
    space = Space.query.filter_by(id=space_id, organization_id=org_id).first_or_404()
    return render_template("organization_admin/space_swot.html", space=space, csrf_token=generate_csrf)


@bp.route("/spaces/<int:space_id>/swot/edit", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_spaces")
def edit_space_swot(space_id):
    """Edit SWOT analysis for a space"""
    org_id = session.get("organization_id")
    space = Space.query.filter_by(id=space_id, organization_id=org_id).first_or_404()

    if request.method == "POST":
        space.swot_strengths = request.form.get("swot_strengths", "").strip() or None
        space.swot_weaknesses = request.form.get("swot_weaknesses", "").strip() or None
        space.swot_opportunities = request.form.get("swot_opportunities", "").strip() or None
        space.swot_threats = request.form.get("swot_threats", "").strip() or None

        db.session.commit()
        flash(f"SWOT analysis for {space.name} updated successfully", "success")

        # Check if we should return to action items page
        if request.args.get("return_to") == "action_items":
            return redirect(url_for("action_items"))

        return redirect(url_for("organization_admin.space_swot", space_id=space.id))

    return render_template("organization_admin/edit_space_swot.html", space=space, csrf_token=generate_csrf)


# Challenge Management


@bp.route("/challenges")
@login_required
@organization_required
def challenges():
    """List all challenges"""
    org_id = session.get("organization_id")
    challenges = Challenge.query.filter_by(organization_id=org_id).order_by(Challenge.display_order).all()
    return render_template("organization_admin/challenges.html", challenges=challenges, csrf_token=generate_csrf)


@bp.route("/initiatives")
@login_required
@organization_required
def initiatives():
    """List all initiatives"""
    org_id = session.get("organization_id")
    initiatives = Initiative.query.filter_by(organization_id=org_id).all()
    return render_template("organization_admin/initiatives.html", initiatives=initiatives, csrf_token=generate_csrf)


# REMOVED: /systems route - structure is managed in workspace Edit Structure mode
# @bp.route("/systems")
# @login_required
# @organization_required
# def systems():
#     """List all systems"""
#     org_id = session.get("organization_id")
#     systems = System.query.filter_by(organization_id=org_id).all()
#     return render_template("organization_admin/systems.html", systems=systems)


@bp.route("/spaces/<int:space_id>/challenges/create", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_challenges")
def create_challenge(space_id):
    """Create a new challenge under a space"""
    org_id = session.get("organization_id")
    space = Space.query.filter_by(id=space_id, organization_id=org_id).first_or_404()

    form = ChallengeCreateForm()

    if form.validate_on_submit():
        max_order = db.session.query(db.func.max(Challenge.display_order)).filter_by(
            organization_id=org_id, space_id=space_id
        ).scalar() or 0
        challenge = Challenge(
            organization_id=org_id,
            space_id=space_id,
            name=form.name.data,
            description=form.description.data,
            display_order=max_order + 1,
            impact_level=int(request.form.get("impact_level")) if request.form.get("impact_level") else None,
        )
        db.session.add(challenge)
        db.session.flush()

        # Audit log
        AuditService.log_create(
            "Challenge",
            challenge.id,
            challenge.name,
            {"description": challenge.description, "space": space.name, "organization_id": org_id},
        )

        db.session.commit()
        flash(f"Challenge {challenge.name} created successfully in {space.name}", "success")
        return redirect(url_for("workspace.index", auto_edit=1))

    return render_template("organization_admin/create_challenge.html", form=form, space=space, csrf_token=generate_csrf)


@bp.route("/challenges/<int:challenge_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_challenges")
def edit_challenge(challenge_id):
    """Edit an existing challenge"""
    org_id = session.get("organization_id")
    challenge = Challenge.query.filter_by(id=challenge_id, organization_id=org_id).first_or_404()

    # Nav within siblings under the same space + bridge between spaces
    all_ids = [c.id for c in Challenge.query.filter_by(space_id=challenge.space_id).order_by(Challenge.display_order, Challenge.name).all()]
    nav = _build_entity_nav(all_ids, challenge_id)
    nav["bridge_prev"] = None
    nav["bridge_next"] = None
    all_spaces = Space.query.filter_by(organization_id=org_id).order_by(Space.display_order, Space.name).all()
    sp_ids = [s.id for s in all_spaces]
    sp_pos = sp_ids.index(challenge.space_id) if challenge.space_id in sp_ids else -1
    if nav["nav_pos"] == 0 and sp_pos > 0:
        prev_sp = all_spaces[sp_pos - 1]
        prev_chs = [c.id for c in Challenge.query.filter_by(space_id=prev_sp.id).order_by(Challenge.display_order, Challenge.name).all()]
        if prev_chs:
            nav["bridge_prev"] = {"url": url_for("organization_admin.edit_challenge", challenge_id=prev_chs[-1]), "label": f"{prev_sp.name} (previous space)"}
    if nav["nav_pos"] == nav["nav_total"] - 1 and sp_pos < len(sp_ids) - 1:
        next_sp = all_spaces[sp_pos + 1]
        next_chs = [c.id for c in Challenge.query.filter_by(space_id=next_sp.id).order_by(Challenge.display_order, Challenge.name).all()]
        if next_chs:
            nav["bridge_next"] = {"url": url_for("organization_admin.edit_challenge", challenge_id=next_chs[0]), "label": f"{next_sp.name} (next space)"}

    form = ChallengeEditForm(obj=challenge)

    # Load all spaces for the dropdown
    spaces = Space.query.filter_by(organization_id=org_id).order_by(Space.name).all()
    form.space_id.choices = [(s.id, s.name) for s in spaces]

    if form.validate_on_submit():
        # Capture old values for audit
        old_values = {
            "name": challenge.name,
            "description": challenge.description,
            "space_id": challenge.space_id,
        }

        challenge.name = form.name.data
        challenge.description = form.description.data
        challenge.space_id = form.space_id.data
        challenge.impact_level = int(request.form.get("impact_level")) if request.form.get("impact_level") else None

        # Audit log
        new_values = {
            "name": challenge.name,
            "description": challenge.description,
            "space_id": challenge.space_id,
        }
        AuditService.log_update("Challenge", challenge.id, challenge.name, old_values, new_values)

        db.session.commit()
        nav_redir = _handle_nav_redirect(request.form.get("nav_action"), nav["prev_id"], nav["next_id"],
                                          "organization_admin.edit_challenge", "challenge_id", None)
        if nav_redir:
            return nav_redir
        flash(f"Challenge {challenge.name} updated successfully", "success")
        return redirect(url_for("workspace.index", auto_edit=1))

    # Get value types for rollup configuration tab
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    # Get entity type defaults with logos
    entity_defaults_raw = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
    entity_defaults = {}
    for default in entity_defaults_raw:
        logo_url = None
        if default.default_logo_data and default.default_logo_mime_type:
            logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
        entity_defaults[default.entity_type] = {
            "color": default.default_color,
            "icon": default.default_icon,
            "logo": logo_url,
        }

    # Get entity links for this challenge
    entity_links = EntityLink.get_links_for_entity("challenge", challenge.id, current_user.id, include_private=True)

    return render_template(
        "organization_admin/edit_challenge.html",
        form=form,
        challenge=challenge,
        value_types=value_types,
        entity_defaults=entity_defaults,
        entity_links=entity_links,
        csrf_token=generate_csrf,
        current_impact=challenge.impact_level,
        parent_context={"space": {"name": challenge.space.name, "impact_level": challenge.space.impact_level, "true_importance_level": challenge.space.impact_level}} if challenge.space else {},
        **nav,
    )


@bp.route("/challenges/<int:challenge_id>/rollup-config", methods=["POST"])
@login_required
@organization_required
def configure_challenge_rollup(challenge_id):
    """Configure rollup rules for a challenge (from Initiatives to Challenge to Space)"""
    org_id = session.get("organization_id")
    challenge = Challenge.query.filter_by(id=challenge_id, organization_id=org_id).first_or_404()

    # Get all value types
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    # Process form data for each value type
    for vt in value_types:
        enabled = request.form.get(f"enabled_{vt.id}") == "on"
        formula = request.form.get(f"formula_{vt.id}", "default")

        # Find or create rule
        rule = RollupRule.query.filter_by(source_type="challenge", source_id=challenge_id, value_type_id=vt.id).first()

        if rule:
            rule.rollup_enabled = enabled
            rule.formula_override = formula
        else:
            rule = RollupRule(
                source_type="challenge",
                source_id=challenge_id,
                value_type_id=vt.id,
                rollup_enabled=enabled,
                formula_override=formula,
            )
            db.session.add(rule)

    db.session.commit()
    flash(f"Rollup configuration saved for {challenge.name}", "success")
    return redirect(url_for("organization_admin.edit_challenge", challenge_id=challenge_id))


# Initiative Management


@bp.route("/challenges/<int:challenge_id>/initiatives/create", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_initiatives")
def create_initiative(challenge_id):
    """Create a new initiative and link it to a challenge"""
    org_id = session.get("organization_id")
    challenge = Challenge.query.filter_by(id=challenge_id, organization_id=org_id).first_or_404()

    form = InitiativeCreateForm()

    if form.validate_on_submit():
        # Create the initiative
        initiative = Initiative(
            organization_id=org_id,
            name=form.name.data,
            description=form.description.data,
            group_label=form.group_label.data if form.group_label.data else None,
            impact_level=int(request.form.get("impact_level")) if request.form.get("impact_level") else None,
        )
        db.session.add(initiative)
        db.session.flush()  # Get the ID

        # Link to challenge with next display_order
        max_init_order = db.session.query(db.func.max(ChallengeInitiativeLink.display_order)).filter_by(
            challenge_id=challenge_id
        ).scalar() or 0
        link = ChallengeInitiativeLink(challenge_id=challenge_id, initiative_id=initiative.id, display_order=max_init_order + 1)
        db.session.add(link)

        # Audit log
        AuditService.log_create(
            "Initiative",
            initiative.id,
            initiative.name,
            {
                "description": initiative.description,
                "group_label": initiative.group_label,
                "challenge": challenge.name,
                "organization_id": org_id,
            },
        )

        db.session.commit()

        flash(f"Initiative {initiative.name} created and linked to {challenge.name}", "success")
        return redirect(url_for("workspace.index", auto_edit=1))

    # Get entity type defaults with logos
    entity_defaults_raw = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
    entity_defaults = {}
    for default in entity_defaults_raw:
        logo_url = None
        if default.default_logo_data and default.default_logo_mime_type:
            logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
        entity_defaults[default.entity_type] = {
            "color": default.default_color,
            "icon": default.default_icon,
            "logo": logo_url,
        }

    return render_template(
        "organization_admin/create_initiative.html",
        form=form,
        challenge=challenge,
        entity_defaults=entity_defaults,
        csrf_token=generate_csrf,
    )


@bp.route("/initiatives/<int:initiative_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_initiatives")
def edit_initiative(initiative_id):
    """Edit an existing initiative"""
    org_id = session.get("organization_id")
    initiative = Initiative.query.filter_by(id=initiative_id, organization_id=org_id).first_or_404()

    # Nav within siblings under the same challenge + bridge to prev/next challenge
    from app.models import ChallengeInitiativeLink
    _ci_link = ChallengeInitiativeLink.query.filter_by(initiative_id=initiative_id).first()
    if _ci_link:
        sibling_ids = [cl.initiative_id for cl in ChallengeInitiativeLink.query.filter_by(challenge_id=_ci_link.challenge_id)
                       .join(Initiative).order_by(Initiative.name).all()]
    else:
        sibling_ids = [initiative_id]
    nav = _build_entity_nav(sibling_ids, initiative_id)

    # Bridge navigation: when at first/last initiative, find prev/next challenge
    nav["bridge_prev"] = None
    nav["bridge_next"] = None
    if _ci_link:
        _ch = _ci_link.challenge
        if _ch and _ch.space:
            all_challenges = Challenge.query.filter_by(space_id=_ch.space_id).order_by(Challenge.display_order, Challenge.name).all()
            ch_ids = [c.id for c in all_challenges]
            ch_pos = ch_ids.index(_ch.id) if _ch.id in ch_ids else -1

            # At first initiative → bridge to last initiative of previous challenge
            if nav["nav_pos"] == 0 and ch_pos > 0:
                prev_ch = all_challenges[ch_pos - 1]
                prev_inits = [cl.initiative_id for cl in ChallengeInitiativeLink.query.filter_by(challenge_id=prev_ch.id)
                              .join(Initiative).order_by(Initiative.name).all()]
                if prev_inits:
                    nav["bridge_prev"] = {
                        "url": url_for("organization_admin.edit_initiative", initiative_id=prev_inits[-1]),
                        "label": f"{prev_ch.name} (previous challenge)",
                    }

            # At last initiative → bridge to first initiative of next challenge
            if nav["nav_pos"] == nav["nav_total"] - 1 and ch_pos < len(ch_ids) - 1:
                next_ch = all_challenges[ch_pos + 1]
                next_inits = [cl.initiative_id for cl in ChallengeInitiativeLink.query.filter_by(challenge_id=next_ch.id)
                              .join(Initiative).order_by(Initiative.name).all()]
                if next_inits:
                    nav["bridge_next"] = {
                        "url": url_for("organization_admin.edit_initiative", initiative_id=next_inits[0]),
                        "label": f"{next_ch.name} (next challenge)",
                    }

    form = InitiativeEditForm(obj=initiative)

    # Load all challenges for the dropdown
    challenges = Challenge.query.filter_by(organization_id=org_id).order_by(Challenge.name).all()
    form.challenge_ids.choices = [(c.id, f"{c.space.name} > {c.name}") for c in challenges]

    # Pre-populate with currently linked challenges
    current_challenge_ids = [link.challenge_id for link in initiative.challenge_links]
    if not form.is_submitted():
        form.challenge_ids.data = current_challenge_ids

    if form.validate_on_submit():
        # Capture old values for audit
        old_values = {
            "name": initiative.name,
            "description": initiative.description,
            "group_label": initiative.group_label,
            "challenge_ids": current_challenge_ids,
        }

        initiative.name = form.name.data
        initiative.description = form.description.data
        initiative.group_label = form.group_label.data if form.group_label.data else None
        initiative.impact_level = int(request.form.get("impact_level")) if request.form.get("impact_level") else None

        # Update challenge links
        new_challenge_ids = form.challenge_ids.data

        # Remove links that are no longer selected
        for link in list(initiative.challenge_links):
            if link.challenge_id not in new_challenge_ids:
                db.session.delete(link)

        # Add new links
        existing_challenge_ids = [link.challenge_id for link in initiative.challenge_links]
        for challenge_id in new_challenge_ids:
            if challenge_id not in existing_challenge_ids:
                max_ord = db.session.query(db.func.max(ChallengeInitiativeLink.display_order)).filter_by(
                    challenge_id=challenge_id
                ).scalar() or 0
                new_link = ChallengeInitiativeLink(
                    challenge_id=challenge_id, initiative_id=initiative.id, display_order=max_ord + 1
                )
                db.session.add(new_link)

        # Audit log
        new_values = {
            "name": initiative.name,
            "description": initiative.description,
            "group_label": initiative.group_label,
            "challenge_ids": new_challenge_ids,
        }
        AuditService.log_update("Initiative", initiative.id, initiative.name, old_values, new_values)

        db.session.commit()
        nav_redir = _handle_nav_redirect(request.form.get("nav_action"), nav["prev_id"], nav["next_id"],
                                          "organization_admin.edit_initiative", "initiative_id", None)
        if nav_redir:
            return nav_redir
        flash(f"Initiative {initiative.name} updated successfully", "success")
        return_to = request.args.get("return_to") or request.form.get("return_to")
        if return_to:
            return redirect(return_to)
        return redirect(url_for("workspace.index", auto_edit=1))

    # Get value types for rollup configuration tab
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    # Get entity type defaults with logos
    entity_defaults_raw = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
    entity_defaults = {}
    for default in entity_defaults_raw:
        logo_url = None
        if default.default_logo_data and default.default_logo_mime_type:
            logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
        entity_defaults[default.entity_type] = {
            "color": default.default_color,
            "icon": default.default_icon,
            "logo": logo_url,
        }

    # Get entity links for this initiative
    entity_links = EntityLink.get_links_for_entity("initiative", initiative.id, current_user.id, include_private=True)

    # Parent context for impact
    from app.models import ImpactLevel as _ILi, ChallengeInitiativeLink as _CILi
    from app.services.impact_service import compute_true_importance as _ctii
    _ili = _ILi.get_org_levels(org_id)
    _orgi = Organization.query.get(org_id)
    _wi = {lvl: _ili[lvl]["weight"] for lvl in _ili} if _ili else {}
    _mi = _orgi.impact_calc_method or "geometric_mean" if _orgi else "geometric_mean"
    _cmi = _orgi.impact_qfd_matrix if _orgi else None
    _cri = _orgi.impact_reinforce_weights if _orgi else None
    _init_parent_ctx = {}
    _ci_link = _CILi.query.filter_by(initiative_id=initiative_id).first()
    if _ci_link and _ci_link.challenge:
        _ch = _ci_link.challenge
        _sp = _ch.space
        if _sp:
            _init_parent_ctx["space"] = {"name": _sp.name, "impact_level": _sp.impact_level, "true_importance_level": _sp.impact_level}
        if _ch:
            _ch_ti = _ctii([_sp.impact_level, _ch.impact_level], _mi, _wi, _cmi, _cri) if _sp and _sp.impact_level and _ch.impact_level else None
            _init_parent_ctx["challenge"] = {"name": _ch.name, "impact_level": _ch.impact_level, "true_importance_level": _ch_ti}

    from flask_wtf.csrf import generate_csrf

    return render_template(
        "organization_admin/edit_initiative.html",
        form=form,
        initiative=initiative,
        value_types=value_types,
        entity_defaults=entity_defaults,
        entity_links=entity_links,
        csrf_token=generate_csrf,
        current_impact=initiative.impact_level,
        parent_context=_init_parent_ctx,
        **nav,
    )


@bp.route("/challenge-initiative-links/<int:link_id>/rollup-config", methods=["POST"])
@login_required
@organization_required
def configure_initiative_rollup(link_id):
    """Configure rollup rules for an initiative (from Systems to Initiative)"""
    org_id = session.get("organization_id")
    link = ChallengeInitiativeLink.query.get_or_404(link_id)

    # Verify ownership
    if link.initiative.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    # Get all value types
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    # Process form data for each value type
    for vt in value_types:
        enabled = request.form.get(f"enabled_{vt.id}") == "on"
        formula = request.form.get(f"formula_{vt.id}", "default")

        # Find or create rule
        rule = RollupRule.query.filter_by(
            source_type="challenge_initiative", source_id=link_id, value_type_id=vt.id
        ).first()

        if rule:
            rule.rollup_enabled = enabled
            rule.formula_override = formula
        else:
            rule = RollupRule(
                source_type="challenge_initiative",
                source_id=link_id,
                value_type_id=vt.id,
                rollup_enabled=enabled,
                formula_override=formula,
            )
            db.session.add(rule)

    db.session.commit()
    flash(f"Rollup configuration saved for {link.initiative.name}", "success")
    return redirect(url_for("organization_admin.edit_initiative", initiative_id=link.initiative_id))


# System Management


@bp.route("/initiatives/<int:initiative_id>/systems/create", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_systems")
def create_system(initiative_id):
    """Create a new system and link it to an initiative"""
    org_id = session.get("organization_id")
    initiative = Initiative.query.filter_by(id=initiative_id, organization_id=org_id).first_or_404()

    form = SystemCreateForm()

    if form.validate_on_submit():
        # Create the system
        _linked_org = request.form.get("linked_organization_id")
        system = System(
            organization_id=org_id, name=form.name.data, description=form.description.data,
            impact_level=int(request.form.get("impact_level")) if request.form.get("impact_level") else None,
            linked_organization_id=int(_linked_org) if _linked_org else None,
        )
        db.session.add(system)
        db.session.flush()  # Get the ID

        # Link to initiative with next display_order
        max_sys_order = db.session.query(db.func.max(InitiativeSystemLink.display_order)).filter_by(
            initiative_id=initiative_id
        ).scalar() or 0
        link = InitiativeSystemLink(initiative_id=initiative_id, system_id=system.id, display_order=max_sys_order + 1)
        db.session.add(link)

        # Audit log
        AuditService.log_create(
            "System",
            system.id,
            system.name,
            {"description": system.description, "initiative": initiative.name, "organization_id": org_id},
        )

        db.session.commit()

        flash(f"System {system.name} created and linked to {initiative.name}", "success")
        return redirect(url_for("workspace.index", auto_edit=1))

    all_orgs = Organization.query.filter(Organization.id != org_id, Organization.is_deleted.is_(False)).order_by(Organization.name).all()
    return render_template(
        "organization_admin/create_system.html", form=form, initiative=initiative, csrf_token=generate_csrf,
        all_orgs=all_orgs,
    )


@bp.route("/systems/<int:system_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_systems")
def edit_system(system_id):
    """Edit an existing system"""
    org_id = session.get("organization_id")
    system = System.query.filter_by(id=system_id, organization_id=org_id).first_or_404()

    # Nav within siblings under the same initiative + bridge between initiatives
    from app.models import InitiativeSystemLink, ChallengeInitiativeLink as _CILs
    _is_links = InitiativeSystemLink.query.filter_by(system_id=system_id).first()
    if _is_links:
        sibling_ids = [sl.system_id for sl in InitiativeSystemLink.query.filter_by(initiative_id=_is_links.initiative_id)
                       .join(System).order_by(System.name).all()]
    else:
        sibling_ids = [system_id]
    nav = _build_entity_nav(sibling_ids, system_id)
    nav["bridge_prev"] = None
    nav["bridge_next"] = None
    if _is_links:
        _ci_s = _CILs.query.filter_by(initiative_id=_is_links.initiative_id).first()
        if _ci_s and _ci_s.challenge:
            _sibling_inits = [cl.initiative_id for cl in _CILs.query.filter_by(challenge_id=_ci_s.challenge_id)
                              .join(Initiative).order_by(Initiative.name).all()]
            _ini_pos = _sibling_inits.index(_is_links.initiative_id) if _is_links.initiative_id in _sibling_inits else -1
            if nav["nav_pos"] == 0 and _ini_pos > 0:
                prev_ini_id = _sibling_inits[_ini_pos - 1]
                prev_sys = [sl.system_id for sl in InitiativeSystemLink.query.filter_by(initiative_id=prev_ini_id).join(System).order_by(System.name).all()]
                if prev_sys:
                    prev_ini = Initiative.query.get(prev_ini_id)
                    nav["bridge_prev"] = {"url": url_for("organization_admin.edit_system", system_id=prev_sys[-1]), "label": f"{prev_ini.name} (previous initiative)"}
            if nav["nav_pos"] == nav["nav_total"] - 1 and _ini_pos < len(_sibling_inits) - 1:
                next_ini_id = _sibling_inits[_ini_pos + 1]
                next_sys = [sl.system_id for sl in InitiativeSystemLink.query.filter_by(initiative_id=next_ini_id).join(System).order_by(System.name).all()]
                if next_sys:
                    next_ini = Initiative.query.get(next_ini_id)
                    nav["bridge_next"] = {"url": url_for("organization_admin.edit_system", system_id=next_sys[0]), "label": f"{next_ini.name} (next initiative)"}

    form = SystemEditForm(obj=system)

    if form.validate_on_submit():
        # Capture old values for audit
        old_values = {"name": system.name, "description": system.description}

        system.name = form.name.data
        system.description = form.description.data
        system.impact_level = int(request.form.get("impact_level")) if request.form.get("impact_level") else None
        _linked_org = request.form.get("linked_organization_id")
        system.linked_organization_id = int(_linked_org) if _linked_org else None

        # Audit log
        new_values = {"name": system.name, "description": system.description}
        AuditService.log_update("System", system.id, system.name, old_values, new_values)

        db.session.commit()
        nav_redir = _handle_nav_redirect(request.form.get("nav_action"), nav["prev_id"], nav["next_id"],
                                          "organization_admin.edit_system", "system_id", None)
        if nav_redir:
            return nav_redir
        flash(f"System {system.name} updated successfully", "success")

        if request.args.get("return_to") == "action_items":
            return redirect(url_for("action_items"))
        return redirect(url_for("workspace.index", auto_edit=1))

    # Get value types for rollup configuration tab
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    # Get entity type defaults with logos
    entity_defaults_raw = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
    entity_defaults = {}
    for default in entity_defaults_raw:
        logo_url = None
        if default.default_logo_data and default.default_logo_mime_type:
            logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
        entity_defaults[default.entity_type] = {
            "color": default.default_color,
            "icon": default.default_icon,
            "logo": logo_url,
        }

    # Get entity links for this system
    entity_links = EntityLink.get_links_for_entity("system", system.id, current_user.id, include_private=True)

    # Parent context for impact (with true importance)
    from app.models import ImpactLevel as _IL2, ChallengeInitiativeLink as _CIL2
    from app.services.impact_service import compute_true_importance as _cti2
    _sys_parent_ctx = {}
    _il2 = _IL2.get_org_levels(org_id)
    _org2 = Organization.query.get(org_id)
    _w2 = {lvl: _il2[lvl]["weight"] for lvl in _il2} if _il2 else {}
    _m2 = _org2.impact_calc_method or "geometric_mean" if _org2 else "geometric_mean"
    _cm2 = _org2.impact_qfd_matrix if _org2 else None
    _cr2 = _org2.impact_reinforce_weights if _org2 else None
    if _is_links:
        _ini = _is_links.initiative
        _ci = _CIL2.query.filter_by(initiative_id=_ini.id).first()
        _sp = _ci.challenge.space if _ci and _ci.challenge else None
        _ch = _ci.challenge if _ci else None
        if _sp:
            _sys_parent_ctx["space"] = {"name": _sp.name, "impact_level": _sp.impact_level, "true_importance_level": _sp.impact_level}
        if _ch:
            _ch_ti = _cti2([_sp.impact_level, _ch.impact_level], _m2, _w2, _cm2, _cr2) if _sp and _sp.impact_level and _ch.impact_level else None
            _sys_parent_ctx["challenge"] = {"name": _ch.name, "impact_level": _ch.impact_level, "true_importance_level": _ch_ti}
        _ini_ti = _cti2([_sp.impact_level, _ch.impact_level, _ini.impact_level], _m2, _w2, _cm2, _cr2) if _sp and _sp.impact_level and _ch and _ch.impact_level and _ini.impact_level else None
        _sys_parent_ctx["initiative"] = {"name": _ini.name, "impact_level": _ini.impact_level, "true_importance_level": _ini_ti}

    all_orgs = Organization.query.filter(Organization.id != org_id, Organization.is_deleted.is_(False)).order_by(Organization.name).all()
    return render_template(
        "organization_admin/edit_system.html",
        form=form,
        system=system,
        value_types=value_types,
        entity_defaults=entity_defaults,
        entity_links=entity_links,
        csrf_token=generate_csrf,
        current_impact=system.impact_level,
        parent_context=_sys_parent_ctx,
        all_orgs=all_orgs,
        **nav,
    )


@bp.route("/initiative-system-links/<int:link_id>", methods=["DELETE"])
@login_required
@organization_required
@permission_required("can_manage_systems")
def unlink_system_api(link_id):
    """Unlink a system from an initiative (REST API endpoint)"""
    try:
        org_id = session.get("organization_id")
        link = InitiativeSystemLink.query.get_or_404(link_id)

        # Verify ownership
        if link.initiative.organization_id != org_id:
            return jsonify({"success": False, "error": "Access denied"}), 403

        link_details = {
            "initiative": link.initiative.name,
            "system": link.system.name,
            "kpi_count": len(link.kpis),
        }

        # Delete the link (cascade will delete associated KPIs)
        db.session.delete(link)

        # Audit log
        AuditService.log_delete(
            "InitiativeSystemLink",
            link.id,
            f"{link.initiative.name} - {link.system.name}",
            link_details,
        )

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/initiative-system-links/<int:link_id>/rollup-config", methods=["POST"])
@login_required
@organization_required
def configure_system_rollup(link_id):
    """Configure rollup rules for a system (from KPIs to System)"""
    org_id = session.get("organization_id")
    link = InitiativeSystemLink.query.get_or_404(link_id)

    # Verify ownership
    if link.initiative.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    # Get all value types
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    # Process form data for each value type
    for vt in value_types:
        enabled = request.form.get(f"enabled_{vt.id}") == "on"
        formula = request.form.get(f"formula_{vt.id}", "default")

        # Find or create rule
        rule = RollupRule.query.filter_by(
            source_type="initiative_system", source_id=link_id, value_type_id=vt.id
        ).first()

        if rule:
            rule.rollup_enabled = enabled
            rule.formula_override = formula
        else:
            rule = RollupRule(
                source_type="initiative_system",
                source_id=link_id,
                value_type_id=vt.id,
                rollup_enabled=enabled,
                formula_override=formula,
            )
            db.session.add(rule)

    db.session.commit()
    flash(f"Rollup configuration saved for {link.system.name}", "success")
    return redirect(url_for("organization_admin.edit_system", system_id=link.system_id))


# KPI Management


@bp.route("/initiative-system-links/<int:link_id>/kpis/create", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_kpis")
def create_kpi(link_id):
    """Create a new KPI under an initiative-system link"""
    org_id = session.get("organization_id")
    link = InitiativeSystemLink.query.get_or_404(link_id)

    # Verify ownership
    if link.initiative.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    # Get active value types for selection (exclude formula value types - they're computed)
    value_types = (
        ValueType.query.filter_by(organization_id=org_id, is_active=True)
        .filter(ValueType.calculation_type != "formula")
        .order_by(ValueType.display_order)
        .all()
    )

    # Get active governance bodies for selection
    governance_bodies = (
        GovernanceBody.query.filter_by(organization_id=org_id, is_active=True)
        .order_by(GovernanceBody.display_order)
        .all()
    )

    # Get active geography sites for selection (optional)
    from app.models import GeographyRegion

    geography_regions = (
        GeographyRegion.query.filter_by(organization_id=org_id).order_by(GeographyRegion.display_order).all()
    )

    # Check prerequisites: Value Types must exist
    if not value_types:
        # Store return context in session
        session["return_to_kpi_creation"] = link_id
        flash(
            "⚠️ Please create at least one Value Type first. KPIs require value types to track metrics. "
            "After creating a value type, you'll be returned here to continue creating your KPI.",
            "warning",
        )
        return redirect(url_for("organization_admin.create_value_type"))

    # Check prerequisites: Governance Bodies must exist
    if not governance_bodies:
        # Store return context in session
        session["return_to_kpi_creation"] = link_id
        flash(
            "⚠️ Please create at least one Governance Body first. KPIs require governance bodies for oversight. "
            "After creating a governance body, you'll be returned here to continue creating your KPI.",
            "warning",
        )
        return redirect(url_for("organization_admin.create_governance_body"))

    form = KPICreateForm()
    form.value_type_ids.choices = [(vt.id, vt.name) for vt in value_types]

    if form.validate_on_submit():
        # Get governance body selection (optional - allows global KPIs)
        selected_gb_ids = request.form.getlist("governance_body_ids")

        # Create the KPI
        kpi = KPI(
            initiative_system_link_id=link_id,
            name=form.name.data,
            description=form.description.data,
            display_order=form.display_order.data,
            impact_level=int(request.form.get("impact_level")) if request.form.get("impact_level") else None,
        )
        db.session.add(kpi)
        db.session.flush()  # Get the ID

        # Link to governance bodies
        for gb_id in selected_gb_ids:
            gb_link = KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=int(gb_id))
            db.session.add(gb_link)

        # Link to geography (multi-level: regions, countries, sites)
        from app.models import KPIGeographyAssignment

        # Region-level assignments
        selected_region_ids = request.form.getlist("region_ids")
        for region_id in selected_region_ids:
            assignment = KPIGeographyAssignment(kpi_id=kpi.id, region_id=int(region_id))
            db.session.add(assignment)

        # Country-level assignments
        selected_country_ids = request.form.getlist("country_ids")
        for country_id in selected_country_ids:
            assignment = KPIGeographyAssignment(kpi_id=kpi.id, country_id=int(country_id))
            db.session.add(assignment)

        # Site-level assignments
        selected_site_ids = request.form.getlist("site_ids")
        for site_id in selected_site_ids:
            assignment = KPIGeographyAssignment(kpi_id=kpi.id, site_id=int(site_id))
            db.session.add(assignment)

        # Link selected value types with colors
        selected_vt_ids = request.form.getlist("value_type_ids")
        first_formula_config_id = None
        first_config_vt_id = None

        for vt_id in selected_vt_ids:
            vt_id_int = int(vt_id)

            # Get calculation type choice
            calc_type = request.form.get(f"calc_type_{vt_id}", "manual")

            # Get color values from form
            color_positive = request.form.get(f"color_positive_{vt_id}", "#28a745")
            color_zero = request.form.get(f"color_zero_{vt_id}", "#6c757d")
            color_negative = request.form.get(f"color_negative_{vt_id}", "#dc3545")

            # Get display scale
            display_scale = request.form.get(f"display_scale_{vt_id}", "default")

            # Get display decimals
            display_decimals = None
            display_decimals_str = request.form.get(f"display_decimals_{vt_id}")
            if display_decimals_str and display_decimals_str.strip():
                try:
                    display_decimals = int(display_decimals_str)
                except ValueError:
                    pass

            # Get target values from form (if checkbox was checked)
            has_target = request.form.get(f"has_target_{vt_id}")
            target_value = None
            target_date = None
            target_direction = "maximize"  # default
            target_tolerance_pct = 10  # default

            if has_target:
                target_value_str = request.form.get(f"target_value_{vt_id}")
                target_date_str = request.form.get(f"target_date_{vt_id}")
                target_direction = request.form.get(f"target_direction_{vt_id}", "maximize")
                target_tolerance_str = request.form.get(f"target_tolerance_{vt_id}")

                if target_value_str:
                    try:
                        target_value = float(target_value_str)
                    except ValueError:
                        pass

                if target_date_str:
                    from datetime import datetime

                    try:
                        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        pass

                if target_tolerance_str:
                    try:
                        target_tolerance_pct = int(target_tolerance_str)
                    except ValueError:
                        target_tolerance_pct = 10

            # Handle linked KPI source (for same org or cross-org value linking)
            linked_source_org_id = None
            linked_source_kpi_id = None
            linked_source_value_type_id = None
            calculation_type = "manual"  # default

            if calc_type == "linked":
                linked_org_id = request.form.get(f"linked_org_{vt_id}")
                linked_kpi_id = request.form.get(f"linked_kpi_{vt_id}")
                linked_vt_id = request.form.get(f"linked_vt_{vt_id}")

                if linked_org_id and linked_kpi_id and linked_vt_id:
                    # Validate value type compatibility
                    source_vt = ValueType.query.get(int(linked_vt_id))
                    current_vt = ValueType.query.get(vt_id_int)

                    if source_vt and current_vt:
                        # Check compatibility: numeric to numeric, or same qualitative type
                        if current_vt.kind == "numeric" and source_vt.kind != "numeric":
                            flash(
                                f"Cannot link numeric '{current_vt.name}' to {source_vt.kind} '{source_vt.name}'. Only numeric to numeric allowed.",
                                "danger",
                            )
                            return redirect(url_for("organization_admin.create_kpi", link_id=link_id))
                        elif current_vt.kind != "numeric" and source_vt.kind != current_vt.kind:
                            flash(
                                f"Cannot link {current_vt.kind} '{current_vt.name}' to {source_vt.kind} '{source_vt.name}'. Types must match.",
                                "danger",
                            )
                            return redirect(url_for("organization_admin.create_kpi", link_id=link_id))

                    linked_source_org_id = int(linked_org_id)
                    linked_source_kpi_id = int(linked_kpi_id)
                    linked_source_value_type_id = int(linked_vt_id)
                    calculation_type = "linked"

            config = KPIValueTypeConfig(
                kpi_id=kpi.id,
                value_type_id=vt_id_int,
                display_order=0,
                color_positive=color_positive,
                color_zero=color_zero,
                color_negative=color_negative,
                display_scale=display_scale,
                display_decimals=display_decimals,
                target_value=target_value,
                target_date=target_date,
                target_direction=target_direction,
                target_tolerance_pct=target_tolerance_pct,
                linked_source_org_id=linked_source_org_id,
                linked_source_kpi_id=linked_source_kpi_id,
                linked_source_value_type_id=linked_source_value_type_id,
                calculation_type=calculation_type,
            )
            db.session.add(config)
            db.session.flush()  # Get the config ID

            # Track if formula was selected (for redirect)
            if calc_type == "formula" and first_formula_config_id is None:
                first_formula_config_id = config.id
                first_config_vt_id = vt_id_int

        # Audit log
        AuditService.log_create(
            "KPI",
            kpi.id,
            kpi.name,
            {
                "description": kpi.description,
                "initiative": link.initiative.name,
                "system": link.system.name,
                "value_types_count": len(selected_vt_ids),
                "governance_bodies_count": len(selected_gb_ids),
                "organization_id": org_id,
            },
        )

        db.session.commit()
        flash(f"KPI {kpi.name} created successfully", "success")

        # If formula was selected, redirect to KPI detail page with formula modal open
        if first_formula_config_id and first_config_vt_id:
            return redirect(
                url_for("workspace.kpi_cell_detail", kpi_id=kpi.id, vt_id=first_config_vt_id, open_formula=1)
            )

        return redirect(url_for("workspace.index", auto_edit=1))

    # Get preselected items from session (if returning from creation flow)
    preselect_value_types = session.pop("preselect_value_types", [])
    preselect_governance_bodies = session.pop("preselect_governance_bodies", [])

    # Auto-select governance body if only one exists
    if len(governance_bodies) == 1 and not preselect_governance_bodies:
        preselect_governance_bodies = [governance_bodies[0].id]

    # Get entity type defaults with logos
    entity_defaults_raw = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
    entity_defaults = {}
    for default in entity_defaults_raw:
        logo_url = None
        if default.default_logo_data and default.default_logo_mime_type:
            logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
        entity_defaults[default.entity_type] = {
            "color": default.default_color,
            "icon": default.default_icon,
            "logo": logo_url,
        }

    return render_template(
        "organization_admin/create_kpi.html",
        form=form,
        link=link,
        initiative=link.initiative,
        system=link.system,
        value_types=value_types,
        governance_bodies=governance_bodies,
        geography_regions=geography_regions,
        preselect_value_types=preselect_value_types,
        preselect_governance_bodies=preselect_governance_bodies,
        entity_defaults=entity_defaults,
        csrf_token=generate_csrf,
    )


@bp.route("/kpis/<int:kpi_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_kpis")
def edit_kpi(kpi_id):
    """Edit an existing KPI"""
    org_id = session.get("organization_id")
    kpi = KPI.query.get_or_404(kpi_id)

    # Verify ownership
    if kpi.initiative_system_link.initiative.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    # Nav within siblings under the same system + bridge between systems
    sibling_ids = [k.id for k in KPI.query.filter_by(initiative_system_link_id=kpi.initiative_system_link_id)
                   .order_by(KPI.display_order, KPI.name).all()]
    nav = _build_entity_nav(sibling_ids, kpi_id)
    nav["bridge_prev"] = None
    nav["bridge_next"] = None
    _kpi_isl = kpi.initiative_system_link
    if _kpi_isl:
        _sys_siblings = [sl for sl in InitiativeSystemLink.query.filter_by(initiative_id=_kpi_isl.initiative_id)
                         .join(System).order_by(System.name).all()]
        _sys_link_ids = [sl.id for sl in _sys_siblings]
        _sl_pos = _sys_link_ids.index(_kpi_isl.id) if _kpi_isl.id in _sys_link_ids else -1
        if nav["nav_pos"] == 0 and _sl_pos > 0:
            prev_sl = _sys_siblings[_sl_pos - 1]
            prev_kpis = [k.id for k in KPI.query.filter_by(initiative_system_link_id=prev_sl.id).order_by(KPI.display_order, KPI.name).all()]
            if prev_kpis:
                nav["bridge_prev"] = {"url": url_for("organization_admin.edit_kpi", kpi_id=prev_kpis[-1]), "label": f"{prev_sl.system.name} (previous system)"}
        if nav["nav_pos"] == nav["nav_total"] - 1 and _sl_pos < len(_sys_link_ids) - 1:
            next_sl = _sys_siblings[_sl_pos + 1]
            next_kpis = [k.id for k in KPI.query.filter_by(initiative_system_link_id=next_sl.id).order_by(KPI.display_order, KPI.name).all()]
            if next_kpis:
                nav["bridge_next"] = {"url": url_for("organization_admin.edit_kpi", kpi_id=next_kpis[0]), "label": f"{next_sl.system.name} (next system)"}

    # Get active governance bodies for selection
    governance_bodies = (
        GovernanceBody.query.filter_by(organization_id=org_id, is_active=True)
        .order_by(GovernanceBody.display_order)
        .all()
    )

    # Get current governance body IDs for this KPI
    current_gb_ids = [link.governance_body_id for link in kpi.governance_body_links]

    # Get active geography sites for selection (optional)
    from app.models import GeographyRegion

    geography_regions = (
        GeographyRegion.query.filter_by(organization_id=org_id).order_by(GeographyRegion.display_order).all()
    )

    # Get current geography assignments for this KPI (all levels)
    current_region_ids = [a.region_id for a in kpi.geography_assignments if a.region_id]
    current_country_ids = [a.country_id for a in kpi.geography_assignments if a.country_id]
    current_site_ids = [a.site_id for a in kpi.geography_assignments if a.site_id]

    form = KPIEditForm(obj=kpi)
    if form.validate_on_submit():
        # Capture old values for audit
        old_values = {
            "name": kpi.name,
            "description": kpi.description,
            "governance_bodies_count": len(kpi.governance_body_links),
        }

        # Get governance body selection (optional - allows global KPIs)
        selected_gb_ids = request.form.getlist("governance_body_ids")

        kpi.name = form.name.data
        kpi.description = form.description.data
        kpi.display_order = form.display_order.data
        kpi.impact_level = int(request.form.get("impact_level")) if request.form.get("impact_level") else None

        # Update colors and targets for each value type config
        for config in kpi.value_type_configs:
            if config.value_type.kind == "numeric":
                color_positive = request.form.get(f"color_positive_{config.id}")
                color_zero = request.form.get(f"color_zero_{config.id}")
                color_negative = request.form.get(f"color_negative_{config.id}")

                if color_positive:
                    config.color_positive = color_positive
                if color_zero:
                    config.color_zero = color_zero
                if color_negative:
                    config.color_negative = color_negative

                # Handle display scale
                display_scale = request.form.get(f"display_scale_{config.id}")
                if display_scale:
                    config.display_scale = display_scale

                # Handle display decimals
                display_decimals_str = request.form.get(f"display_decimals_{config.id}")
                if display_decimals_str and display_decimals_str.strip():
                    try:
                        config.display_decimals = int(display_decimals_str)
                    except ValueError:
                        pass
                else:
                    config.display_decimals = None

                # Handle target updates
                has_target = request.form.get(f"has_target_{config.id}")
                if has_target:
                    target_value_str = request.form.get(f"target_value_{config.id}")
                    target_date_str = request.form.get(f"target_date_{config.id}")
                    target_direction = request.form.get(f"target_direction_{config.id}", "maximize")
                    target_tolerance_str = request.form.get(f"target_tolerance_{config.id}")

                    if target_value_str and target_value_str.strip():
                        try:
                            config.target_value = float(target_value_str)
                        except ValueError:
                            # If conversion fails, clear the target
                            config.target_value = None

                    if target_date_str:
                        from datetime import datetime

                        try:
                            config.target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            pass

                    # Update target direction
                    config.target_direction = target_direction

                    # Update tolerance
                    if target_tolerance_str:
                        try:
                            config.target_tolerance_pct = int(target_tolerance_str)
                        except ValueError:
                            config.target_tolerance_pct = 10
                    else:
                        config.target_tolerance_pct = 10
                else:
                    # Clear target if checkbox unchecked
                    config.target_value = None
                    config.target_date = None
                    config.target_direction = "maximize"
                    config.target_tolerance_pct = 10

            # Handle linked KPI source (for same org or cross-org value linking)
            is_linked = request.form.get(f"is_linked_{config.id}")
            if is_linked:
                linked_org_id = request.form.get(f"linked_org_{config.id}")
                linked_kpi_id = request.form.get(f"linked_kpi_{config.id}")
                linked_vt_id = request.form.get(f"linked_vt_{config.id}")

                if linked_org_id and linked_kpi_id and linked_vt_id:
                    config.linked_source_org_id = int(linked_org_id)
                    config.linked_source_kpi_id = int(linked_kpi_id)
                    config.linked_source_value_type_id = int(linked_vt_id)
                else:
                    # If not all fields filled, clear the link
                    config.linked_source_org_id = None
                    config.linked_source_kpi_id = None
                    config.linked_source_value_type_id = None
            else:
                # Clear link if checkbox unchecked
                config.linked_source_org_id = None
                config.linked_source_kpi_id = None
                config.linked_source_value_type_id = None

        # Update governance body links
        # Remove all existing links
        for link in kpi.governance_body_links:
            db.session.delete(link)

        # Flush deletes before adding new ones to avoid unique constraint violations
        db.session.flush()

        # Add new links
        for gb_id in selected_gb_ids:
            gb_link = KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=int(gb_id))
            db.session.add(gb_link)

        # Update geography assignments (multi-level: regions, countries, sites)
        from app.models import KPIGeographyAssignment

        # Remove all existing geography assignments
        KPIGeographyAssignment.query.filter_by(kpi_id=kpi.id).delete()
        # Flush deletes before adding new ones
        db.session.flush()

        # Add new region-level assignments
        selected_region_ids = request.form.getlist("region_ids")
        for region_id in selected_region_ids:
            assignment = KPIGeographyAssignment(kpi_id=kpi.id, region_id=int(region_id))
            db.session.add(assignment)

        # Add new country-level assignments
        selected_country_ids = request.form.getlist("country_ids")
        for country_id in selected_country_ids:
            assignment = KPIGeographyAssignment(kpi_id=kpi.id, country_id=int(country_id))
            db.session.add(assignment)

        # Add new site-level assignments
        selected_site_ids = request.form.getlist("site_ids")
        for site_id in selected_site_ids:
            assignment = KPIGeographyAssignment(kpi_id=kpi.id, site_id=int(site_id))
            db.session.add(assignment)

        # Audit log
        new_values = {"name": kpi.name, "description": kpi.description, "governance_bodies_count": len(selected_gb_ids)}
        AuditService.log_update("KPI", kpi.id, kpi.name, old_values, new_values)

        db.session.commit()
        nav_redir = _handle_nav_redirect(request.form.get("nav_action"), nav["prev_id"], nav["next_id"],
                                          "organization_admin.edit_kpi", "kpi_id", None)
        if nav_redir:
            return nav_redir
        flash(f"KPI {kpi.name} updated successfully", "success")

        if request.args.get("return_to") == "action_items":
            return redirect(url_for("action_items"))
        return redirect(url_for("workspace.index", auto_edit=1))

    # Get entity type defaults with logos
    entity_defaults_raw = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
    entity_defaults = {}
    for default in entity_defaults_raw:
        logo_url = None
        if default.default_logo_data and default.default_logo_mime_type:
            logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
        entity_defaults[default.entity_type] = {
            "color": default.default_color,
            "icon": default.default_icon,
            "logo": logo_url,
        }

    # Get entity links for this KPI
    entity_links = EntityLink.get_links_for_entity("kpi", kpi.id, current_user.id, include_private=True)

    # Parent context for impact (with true importance)
    from app.models import ImpactLevel as _IL3, ChallengeInitiativeLink as _CIL3
    from app.services.impact_service import compute_true_importance as _cti3
    _kpi_parent_ctx = {}
    _il3 = _IL3.get_org_levels(org_id)
    _org3 = Organization.query.get(org_id)
    _w3 = {lvl: _il3[lvl]["weight"] for lvl in _il3} if _il3 else {}
    _m3 = _org3.impact_calc_method or "geometric_mean" if _org3 else "geometric_mean"
    _cm3 = _org3.impact_qfd_matrix if _org3 else None
    _cr3 = _org3.impact_reinforce_weights if _org3 else None
    _kpi_link = kpi.initiative_system_link
    if _kpi_link:
        _sys = _kpi_link.system
        _ini = _kpi_link.initiative
        _ci = _CIL3.query.filter_by(initiative_id=_ini.id).first()
        _ch = _ci.challenge if _ci else None
        _sp = _ch.space if _ch else None
        if _sp:
            _kpi_parent_ctx["space"] = {"name": _sp.name, "impact_level": _sp.impact_level, "true_importance_level": _sp.impact_level}
        if _ch:
            _ch_ti = _cti3([_sp.impact_level, _ch.impact_level], _m3, _w3, _cm3, _cr3) if _sp and _sp.impact_level and _ch.impact_level else None
            _kpi_parent_ctx["challenge"] = {"name": _ch.name, "impact_level": _ch.impact_level, "true_importance_level": _ch_ti}
        _ini_ti = _cti3([_sp.impact_level, _ch.impact_level, _ini.impact_level], _m3, _w3, _cm3, _cr3) if _sp and _sp.impact_level and _ch and _ch.impact_level and _ini.impact_level else None
        _kpi_parent_ctx["initiative"] = {"name": _ini.name, "impact_level": _ini.impact_level, "true_importance_level": _ini_ti}
        _sys_ti = _cti3([_sp.impact_level, _ch.impact_level, _ini.impact_level, _sys.impact_level], _m3, _w3, _cm3, _cr3) if _sp and _sp.impact_level and _ch and _ch.impact_level and _ini.impact_level and _sys.impact_level else None
        _kpi_parent_ctx["system"] = {"name": _sys.name, "impact_level": _sys.impact_level, "true_importance_level": _sys_ti}

    return render_template(
        "organization_admin/edit_kpi.html",
        form=form,
        kpi=kpi,
        governance_bodies=governance_bodies,
        current_gb_ids=current_gb_ids,
        geography_regions=geography_regions,
        current_region_ids=current_region_ids,
        current_country_ids=current_country_ids,
        current_site_ids=current_site_ids,
        entity_defaults=entity_defaults,
        entity_links=entity_links,
        csrf_token=generate_csrf,
        current_impact=kpi.impact_level,
        parent_context=_kpi_parent_ctx,
        **nav,
    )


@bp.route("/kpis/<int:kpi_id>/delete", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_kpis")
def delete_kpi(kpi_id):
    """Delete a KPI"""
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.content_type == "multipart/form-data"
    org_id = session.get("organization_id")
    kpi = KPI.query.get_or_404(kpi_id)

    # Verify ownership
    if kpi.initiative_system_link.initiative.organization_id != org_id:
        if is_ajax:
            return jsonify({"success": False, "error": "Access denied"}), 403
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    # Check if any other KPI is reading values from this KPI (linked KPI protection)
    from app.models import KPIValueTypeConfig

    linked_consumers = KPIValueTypeConfig.query.filter_by(linked_source_kpi_id=kpi_id).all()
    if linked_consumers:
        consumer_info = []
        for consumer in linked_consumers[:3]:
            consumer_kpi = consumer.kpi
            org_name = consumer_kpi.initiative_system_link.initiative.organization.name
            consumer_info.append(f"{consumer_kpi.name} (Org: {org_name})")

        error_msg = f'Cannot delete — linked source for {len(linked_consumers)} KPI(s): {", ".join(consumer_info)}'
        if is_ajax:
            return jsonify({"success": False, "error": error_msg}), 400
        flash(error_msg, "danger")
        return redirect(url_for("workspace.index"))

    kpi_name = kpi.name
    db.session.delete(kpi)
    db.session.commit()

    if is_ajax:
        return jsonify({"success": True})
    flash(f'KPI "{kpi_name}" deleted successfully', "success")
    return redirect(url_for("workspace.index"))


@bp.route("/kpis/<int:kpi_id>/archive", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_kpis")
def archive_kpi(kpi_id):
    """Archive a KPI (makes it read-only and hidden by default)"""
    try:
        org_id = session.get("organization_id")
        kpi = KPI.query.get_or_404(kpi_id)

        # Verify ownership
        if kpi.initiative_system_link.initiative.organization_id != org_id:
            return jsonify({"success": False, "error": "Access denied"}), 403

        if kpi.is_archived:
            return jsonify({"success": False, "error": f'KPI "{kpi.name}" is already archived'})

        from datetime import datetime

        kpi.is_archived = True
        kpi.archived_at = datetime.utcnow()
        kpi.archived_by_user_id = current_user.id

        # Audit log
        AuditService.log_archive("KPI", kpi.id, kpi.name)

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/kpis/<int:kpi_id>/unarchive", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_kpis")
def unarchive_kpi(kpi_id):
    """Unarchive a KPI (makes it active again)"""
    try:
        org_id = session.get("organization_id")
        kpi = KPI.query.get_or_404(kpi_id)

        # Verify ownership
        if kpi.initiative_system_link.initiative.organization_id != org_id:
            return jsonify({"success": False, "error": "Access denied"}), 403

        if not kpi.is_archived:
            return jsonify({"success": False, "error": f'KPI "{kpi.name}" is not archived'})

        kpi.is_archived = False
        kpi.archived_at = None
        kpi.archived_by_user_id = None

        # Audit log
        AuditService.log_update("KPI", kpi.id, kpi.name, {"is_archived": True}, {"is_archived": False})

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/systems/<int:system_id>/delete", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_systems")
def delete_system(system_id):
    """Delete a System"""
    org_id = session.get("organization_id")
    system = System.query.get_or_404(system_id)

    # Verify ownership
    if system.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("organization_admin.systems"))

    system_name = system.name
    system_id_for_audit = system.id

    # Check if system is linked to any initiatives
    links = InitiativeSystemLink.query.filter_by(system_id=system_id).all()
    if links:
        flash(
            f'Cannot delete system "{system_name}" - it is linked to {len(links)} initiative(s). Remove links first.',
            "danger",
        )
        return redirect(url_for("organization_admin.systems"))

    system_details = {"description": system.description, "organization_id": org_id}

    db.session.delete(system)

    # Audit log
    AuditService.log_delete("System", system_id_for_audit, system_name, system_details)

    db.session.commit()

    flash(f'System "{system_name}" deleted successfully', "success")
    return redirect(url_for("organization_admin.systems"))


@bp.route("/initiatives/<int:initiative_id>/delete", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_initiatives")
def delete_initiative(initiative_id):
    """Delete an Initiative"""
    org_id = session.get("organization_id")
    initiative = Initiative.query.get_or_404(initiative_id)

    # Verify ownership
    if initiative.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("organization_admin.initiatives"))

    initiative_name = initiative.name
    initiative_id_for_audit = initiative.id
    initiative_details = {"description": initiative.description, "organization_id": org_id}

    # Find systems that will be orphaned (only linked to this initiative)
    systems_to_delete = []
    for sys_link in initiative.system_links:
        other_links = InitiativeSystemLink.query.filter(
            InitiativeSystemLink.system_id == sys_link.system_id,
            InitiativeSystemLink.initiative_id != initiative_id,
        ).count()
        if other_links == 0:
            systems_to_delete.append(sys_link.system)

    # Delete initiative — cascades: challenge links, system links, KPIs
    db.session.delete(initiative)
    db.session.flush()

    # Delete systems that are no longer linked to any initiative
    for system in systems_to_delete:
        db.session.delete(system)

    # Audit log
    AuditService.log_delete("Initiative", initiative_id_for_audit, initiative_name, initiative_details)

    db.session.commit()

    flash(f'Initiative "{initiative_name}" deleted successfully', "success")
    return redirect(url_for("organization_admin.initiatives"))


@bp.route("/initiatives/<int:initiative_id>", methods=["DELETE"])
@login_required
@organization_required
@permission_required("can_manage_initiatives")
def delete_initiative_api(initiative_id):
    """Delete an Initiative (REST API endpoint)"""
    try:
        org_id = session.get("organization_id")
        initiative = Initiative.query.get_or_404(initiative_id)

        # Verify ownership
        if initiative.organization_id != org_id:
            return jsonify({"success": False, "error": "Access denied"}), 403

        initiative_name = initiative.name
        initiative_id_for_audit = initiative.id
        initiative_details = {"description": initiative.description, "organization_id": org_id}

        # Find systems that will be orphaned (only linked to this initiative)
        systems_to_delete = []
        for sys_link in initiative.system_links:
            other_links = InitiativeSystemLink.query.filter(
                InitiativeSystemLink.system_id == sys_link.system_id,
                InitiativeSystemLink.initiative_id != initiative_id,
            ).count()
            if other_links == 0:
                systems_to_delete.append(sys_link.system)

        # Delete initiative — cascades: challenge links, system links, KPIs
        db.session.delete(initiative)
        db.session.flush()

        # Delete systems that are no longer linked to any initiative
        for system in systems_to_delete:
            db.session.delete(system)

        # Audit log
        AuditService.log_delete("Initiative", initiative_id_for_audit, initiative_name, initiative_details)

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/challenges/<int:challenge_id>/delete", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_challenges")
def delete_challenge(challenge_id):
    """Delete a Challenge"""
    org_id = session.get("organization_id")
    challenge = Challenge.query.get_or_404(challenge_id)

    # Verify ownership
    if challenge.space.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    challenge_name = challenge.name
    challenge_id_for_audit = challenge.id
    challenge_details = {"description": challenge.description, "space": challenge.space.name, "organization_id": org_id}

    db.session.delete(challenge)

    # Audit log
    AuditService.log_delete("Challenge", challenge_id_for_audit, challenge_name, challenge_details)

    db.session.commit()

    flash(f'Challenge "{challenge_name}" deleted successfully', "success")
    return redirect(url_for("workspace.index"))


@bp.route("/challenges/<int:challenge_id>", methods=["DELETE"])
@login_required
@organization_required
@permission_required("can_manage_challenges")
def delete_challenge_api(challenge_id):
    """Delete a Challenge (REST API endpoint)"""
    try:
        org_id = session.get("organization_id")
        challenge = Challenge.query.get_or_404(challenge_id)

        # Verify ownership
        if challenge.space.organization_id != org_id:
            return jsonify({"success": False, "error": "Access denied"}), 403

        challenge_name = challenge.name
        challenge_id_for_audit = challenge.id
        challenge_details = {
            "description": challenge.description,
            "space": challenge.space.name,
            "organization_id": org_id,
        }

        db.session.delete(challenge)

        # Audit log
        AuditService.log_delete("Challenge", challenge_id_for_audit, challenge_name, challenge_details)

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# Value Type Management


@bp.route("/value-types")
@login_required
@organization_required
def value_types():
    """List all value types"""
    org_id = session.get("organization_id")
    value_types = ValueType.query.filter_by(organization_id=org_id).order_by(ValueType.display_order).all()
    return render_template("organization_admin/value_types.html", value_types=value_types, csrf_token=generate_csrf)


@bp.route("/value-types/reorder", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_value_types")
def reorder_value_types():
    """Update value type display order via AJAX (CSRF exempt for AJAX)"""
    # Note: CSRF validation happens through login_required - user must be authenticated
    org_id = session.get("organization_id")
    data = request.get_json()
    order = data.get("order", [])

    if not order:
        return jsonify({"success": False, "error": "No order provided"}), 400

    try:
        # Update display_order for each value type
        for index, vt_id in enumerate(order):
            vt = ValueType.query.filter_by(id=vt_id, organization_id=org_id).first()
            if vt:
                vt.display_order = index

        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/value-types/create", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_value_types")
def create_value_type():
    """Create a new value type"""
    form = ValueTypeCreateForm()

    if form.validate_on_submit():
        value_type = ValueType(
            organization_id=session.get("organization_id"),
            name=form.name.data,
            description=form.description.data,
            kind=form.kind.data,
            numeric_format=form.numeric_format.data if form.kind.data == "numeric" else None,
            decimal_places=form.decimal_places.data if form.kind.data == "numeric" else None,
            unit_label=form.unit_label.data,
            default_aggregation_formula=form.default_aggregation_formula.data,
            display_order=form.display_order.data,
            is_active=form.is_active.data,
            calculation_type=form.calculation_type.data or "manual",
        )

        # Handle formula configuration
        if form.calculation_type.data == "formula":
            formula_mode = form.formula_mode.data or "simple"

            try:
                if formula_mode == "advanced":
                    # Advanced mode: Python expression
                    if form.formula_expression.data:
                        value_type.calculation_config = {
                            "mode": "advanced",
                            "expression": form.formula_expression.data,
                        }
                    else:
                        flash("Please enter a Python expression for the formula", "danger")
                        return render_template(
                            "organization_admin/create_value_type.html", form=form, csrf_token=generate_csrf
                        )
                else:
                    # Simple mode: operation on source value types
                    if form.formula_operation.data and form.formula_source_ids.data:
                        source_ids = [int(id.strip()) for id in form.formula_source_ids.data.split(",") if id.strip()]
                        value_type.calculation_config = {
                            "mode": "simple",
                            "operation": form.formula_operation.data,
                            "source_value_type_ids": source_ids,
                        }
                    else:
                        flash("Please select an operation and at least 2 source value types", "danger")
                        return render_template(
                            "organization_admin/create_value_type.html", form=form, csrf_token=generate_csrf
                        )

                # Validate formula configuration
                is_valid, error_message = value_type.validate_formula_config()
                if not is_valid:
                    flash(f"Formula validation error: {error_message}", "danger")
                    return render_template(
                        "organization_admin/create_value_type.html", form=form, csrf_token=generate_csrf
                    )
            except (ValueError, KeyError) as e:
                flash(f"Invalid formula configuration: {e}", "danger")
                return render_template("organization_admin/create_value_type.html", form=form, csrf_token=generate_csrf)

        # Handle list options
        if form.kind.data == "list" and form.list_options_json.data:
            import json

            try:
                value_type.list_options = json.loads(form.list_options_json.data)
            except (ValueError, TypeError):
                pass

        db.session.add(value_type)
        db.session.flush()

        # Audit log
        AuditService.log_create(
            "ValueType",
            value_type.id,
            value_type.name,
            {
                "kind": value_type.kind,
                "numeric_format": value_type.numeric_format,
                "unit_label": value_type.unit_label,
                "default_aggregation_formula": value_type.default_aggregation_formula,
                "calculation_type": value_type.calculation_type,
                "organization_id": value_type.organization_id,
            },
        )

        db.session.commit()
        flash(f"Value Type {value_type.name} created successfully", "success")

        # Check if we need to return to KPI creation
        return_to_link_id = session.pop("return_to_kpi_creation", None)
        if return_to_link_id:
            # Store the newly created value type ID for pre-selection
            if "preselect_value_types" not in session:
                session["preselect_value_types"] = []
            session["preselect_value_types"].append(value_type.id)
            session.modified = True
            flash("✓ Value Type created! Continue creating your KPI below.", "info")
            return redirect(url_for("organization_admin.create_kpi", link_id=return_to_link_id))

        return redirect(url_for("organization_admin.value_types"))

    return render_template("organization_admin/create_value_type.html", form=form, csrf_token=generate_csrf)


@bp.route("/value-types/<int:vt_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_value_types")
def edit_value_type(vt_id):
    """Edit a value type"""
    org_id = session.get("organization_id")
    value_type = ValueType.query.get_or_404(vt_id)

    if value_type.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("organization_admin.value_types"))

    # Build sequential nav list (stable sort: order then name)
    all_vts = ValueType.query.filter_by(organization_id=org_id).order_by(ValueType.display_order, ValueType.name).all()
    nav_ids = [vt.id for vt in all_vts]
    nav_pos = nav_ids.index(vt_id) if vt_id in nav_ids else 0
    prev_id = nav_ids[nav_pos - 1] if nav_pos > 0 else None
    next_id = nav_ids[nav_pos + 1] if nav_pos < len(nav_ids) - 1 else None

    form = ValueTypeEditForm(obj=value_type)

    if form.validate_on_submit():
        # Capture old values for audit
        old_values = {
            "name": value_type.name,
            "decimal_places": value_type.decimal_places,
            "unit_label": value_type.unit_label,
            "is_active": value_type.is_active,
        }

        value_type.name = form.name.data
        value_type.description = form.description.data
        if value_type.kind == "numeric" and form.decimal_places.data is not None:
            value_type.decimal_places = form.decimal_places.data
        if form.unit_label.data is not None:
            value_type.unit_label = form.unit_label.data
        value_type.is_active = form.is_active.data
        value_type.display_order = form.display_order.data
        if form.default_aggregation_formula.data:
            value_type.default_aggregation_formula = form.default_aggregation_formula.data

        # Handle list options update
        if value_type.kind == "list" and form.list_options_json.data:
            import json

            try:
                value_type.list_options = json.loads(form.list_options_json.data)
            except (ValueError, TypeError):
                pass

        # Audit log
        new_values = {
            "name": value_type.name,
            "decimal_places": value_type.decimal_places,
            "unit_label": value_type.unit_label,
            "is_active": value_type.is_active,
        }
        AuditService.log_update("ValueType", value_type.id, value_type.name, old_values, new_values)

        db.session.commit()

        # Navigate based on action
        nav_action = request.form.get("nav_action")
        if nav_action == "prev" and prev_id:
            return redirect(url_for("organization_admin.edit_value_type", vt_id=prev_id))
        elif nav_action == "next" and next_id:
            return redirect(url_for("organization_admin.edit_value_type", vt_id=next_id))

        flash(f"Value Type {value_type.name} updated successfully", "success")
        return redirect(url_for("organization_admin.value_types"))

    return render_template(
        "organization_admin/edit_value_type.html",
        form=form,
        value_type=value_type,
        csrf_token=generate_csrf,
        nav_pos=nav_pos,
        nav_total=len(nav_ids),
        prev_id=prev_id,
        next_id=next_id,
    )


@bp.route("/value-types/<int:vt_id>/delete-check")
@login_required
@organization_required
@permission_required("can_manage_value_types")
def delete_value_type_check(vt_id):
    """Check if value type can be deleted and show usage"""
    value_type = ValueType.query.get_or_404(vt_id)

    if value_type.organization_id != session.get("organization_id"):
        flash("Access denied", "danger")
        return redirect(url_for("organization_admin.value_types"))

    can_delete, reason = ValueTypeUsageService.can_delete(vt_id)
    usage = ValueTypeUsageService.check_usage(vt_id)

    # Calculate impact for deletion (counts)
    inner = usage.get("usage", {}) if usage else {}
    impact = {
        "kpi_configs": len(inner.get("kpi_configs", [])),
        "contributions": inner.get("contributions_count", 0),
        "consensus_values": len(inner.get("kpi_configs", [])),
        "rollup_rules": inner.get("rollup_rules_count", 0),
    }

    return render_template(
        "organization_admin/delete_value_type_check.html",
        value_type=value_type,
        can_delete=can_delete,
        reason=reason,
        usage=usage,
        impact=impact,
        csrf_token=generate_csrf,
    )


@bp.route("/value-types/<int:vt_id>/delete", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_value_types")
def delete_value_type(vt_id):
    """Delete a value type (after confirmation check)"""
    try:
        org_id = session.get("organization_id")
        value_type = ValueType.query.get_or_404(vt_id)

        if value_type.organization_id != org_id:
            flash("Access denied", "danger")
            return redirect(url_for("organization_admin.value_types"))

        # Handle force deletion: delete rollup rules first
        if request.form.get("force") == "true":
            from app.models import RollupRule

            RollupRule.query.filter_by(value_type_id=vt_id).delete()

        # Double check if it can be deleted
        can_delete, reason = ValueTypeUsageService.can_delete(vt_id)
        if not can_delete:
            flash(f"Cannot delete value type: {reason}", "danger")
            return redirect(url_for("organization_admin.value_types"))

        value_type_name = value_type.name
        value_type_id = value_type.id

        # Delete the value type (cascade will handle related records)
        db.session.delete(value_type)

        # Audit log
        AuditService.log_delete(
            "ValueType",
            value_type_id,
            value_type_name,
            {"kind": value_type.kind, "organization_id": org_id},
        )

        db.session.commit()
        flash(f'Value type "{value_type_name}" deleted successfully', "success")
        return redirect(url_for("organization_admin.value_types"))

    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting value type: {str(e)}", "danger")
        return redirect(url_for("organization_admin.value_types"))


@bp.route("/value-types/<int:vt_id>/rollup-config", methods=["GET", "POST"])
@login_required
@organization_required
def configure_rollup(vt_id):
    """Configure rollup rules for a value type"""
    org_id = session.get("organization_id")
    value_type = ValueType.query.get_or_404(vt_id)

    if value_type.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("organization_admin.value_types"))

    if request.method == "POST":
        # Get form data for rollup configuration
        # Note: This updates the default aggregation formula for the value type
        # Actual rollup rules are per-entity (InitiativeSystemLink, ChallengeInitiativeLink, Challenge)

        # System level formula
        sys_enabled = request.form.get("rollup_enabled_system") == "on"
        sys_formula = request.form.get("formula_system", "default")
        sys_display_scale = request.form.get("display_scale_system") or None
        sys_display_decimals = request.form.get("display_decimals_system")
        sys_display_decimals = (
            int(sys_display_decimals) if sys_display_decimals and sys_display_decimals.strip() else None
        )

        # Initiative level formula
        init_enabled = request.form.get("rollup_enabled_initiative") == "on"
        init_formula = request.form.get("formula_initiative", "default")
        init_display_scale = request.form.get("display_scale_initiative") or None
        init_display_decimals = request.form.get("display_decimals_initiative")
        init_display_decimals = (
            int(init_display_decimals) if init_display_decimals and init_display_decimals.strip() else None
        )

        # Challenge level formula
        chal_enabled = request.form.get("rollup_enabled_challenge") == "on"
        chal_formula = request.form.get("formula_challenge", "default")
        chal_display_scale = request.form.get("display_scale_challenge") or None
        chal_display_decimals = request.form.get("display_decimals_challenge")
        chal_display_decimals = (
            int(chal_display_decimals) if chal_display_decimals and chal_display_decimals.strip() else None
        )

        # VALIDATION: Prevent SUM on qualitative value types
        # If user somehow tries to use SUM on qualitative, convert to MAX (sensible default)
        if value_type.is_qualitative():
            if sys_formula == "sum":
                sys_formula = "max"
                flash(
                    "⚠️ SUM formula not valid for qualitative types - changed to MAX",
                    "warning",
                )
            if init_formula == "sum":
                init_formula = "max"
                flash(
                    "⚠️ SUM formula not valid for qualitative types - changed to MAX",
                    "warning",
                )
            if chal_formula == "sum":
                chal_formula = "max"
                flash(
                    "⚠️ SUM formula not valid for qualitative types - changed to MAX",
                    "warning",
                )

        # For now, update the ValueType's default aggregation formula
        # This will be used when creating new rollup rules
        if sys_formula != "default":
            value_type.default_aggregation_formula = sys_formula
        elif init_formula != "default":
            value_type.default_aggregation_formula = init_formula
        elif chal_formula != "default":
            value_type.default_aggregation_formula = chal_formula

        # Create/update rollup rules for ALL existing entities
        # This applies the configuration to all current links
        try:
            updated_count = 0

            if sys_enabled:
                # Apply to all InitiativeSystemLinks
                links = InitiativeSystemLink.query.join(System).filter(System.organization_id == org_id).all()

                for link in links:
                    rule = RollupRule.query.filter_by(
                        source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM, source_id=link.id, value_type_id=value_type.id
                    ).first()

                    if rule:
                        rule.rollup_enabled = True
                        rule.formula_override = sys_formula
                        rule.display_scale = sys_display_scale
                        rule.display_decimals = sys_display_decimals
                    else:
                        rule = RollupRule(
                            source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM,
                            source_id=link.id,
                            value_type_id=value_type.id,
                            rollup_enabled=True,
                            formula_override=sys_formula,
                            display_scale=sys_display_scale,
                            display_decimals=sys_display_decimals,
                        )
                        db.session.add(rule)
                    updated_count += 1

            if init_enabled:
                # Apply to all ChallengeInitiativeLinks
                links = ChallengeInitiativeLink.query.join(Challenge).filter(Challenge.organization_id == org_id).all()

                for link in links:
                    rule = RollupRule.query.filter_by(
                        source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE,
                        source_id=link.id,
                        value_type_id=value_type.id,
                    ).first()

                    if rule:
                        rule.rollup_enabled = True
                        rule.formula_override = init_formula
                        rule.display_scale = init_display_scale
                        rule.display_decimals = init_display_decimals
                    else:
                        rule = RollupRule(
                            source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE,
                            source_id=link.id,
                            value_type_id=value_type.id,
                            rollup_enabled=True,
                            formula_override=init_formula,
                            display_scale=init_display_scale,
                            display_decimals=init_display_decimals,
                        )
                        db.session.add(rule)
                    updated_count += 1

            if chal_enabled:
                # Apply to all Challenges
                challenges = Challenge.query.filter_by(organization_id=org_id).all()

                for challenge in challenges:
                    rule = RollupRule.query.filter_by(
                        source_type=RollupRule.SOURCE_CHALLENGE, source_id=challenge.id, value_type_id=value_type.id
                    ).first()

                    if rule:
                        rule.rollup_enabled = True
                        rule.formula_override = chal_formula
                        rule.display_scale = chal_display_scale
                        rule.display_decimals = chal_display_decimals
                    else:
                        rule = RollupRule(
                            source_type=RollupRule.SOURCE_CHALLENGE,
                            source_id=challenge.id,
                            value_type_id=value_type.id,
                            rollup_enabled=True,
                            formula_override=chal_formula,
                            display_scale=chal_display_scale,
                            display_decimals=chal_display_decimals,
                        )
                        db.session.add(rule)
                    updated_count += 1

            db.session.commit()
            flash(f"✓ Rollup configuration updated for {value_type.name}", "success")
            flash(f"Applied to {updated_count} rollup rules", "info")

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating rollup configuration: {str(e)}", "danger")

        # If coming from workspace quick-access, return to workspace
        return_to = request.args.get("return_to")
        if return_to == "workspace":
            return redirect(url_for("workspace.index", auto_edit=1))

        return redirect(url_for("organization_admin.value_types"))

    # Get current default settings
    default_enabled = True  # By default, rollup is enabled
    default_formula = value_type.default_aggregation_formula

    # FIX: If qualitative value type has invalid default (sum), auto-correct it
    if value_type.is_qualitative() and default_formula == "sum":
        # Update to smart default
        smart_default = ValueType.get_smart_default_formula(value_type.kind)
        value_type.default_aggregation_formula = smart_default
        db.session.commit()

        flash(
            f"⚠️ Auto-corrected invalid default formula from SUM → {smart_default.upper()} "
            f"(SUM not valid for {value_type.kind})",
            "warning",
        )
        default_formula = smart_default

    # Load existing configuration from RollupRules to show current settings
    # Get a sample rule from each level to show what's currently configured
    current_system_rule = RollupRule.query.filter_by(
        source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM, value_type_id=value_type.id
    ).first()

    current_initiative_rule = RollupRule.query.filter_by(
        source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE, value_type_id=value_type.id
    ).first()

    current_challenge_rule = RollupRule.query.filter_by(
        source_type=RollupRule.SOURCE_CHALLENGE, value_type_id=value_type.id
    ).first()

    # Load entity defaults for gradient colors
    entity_defaults = EntityTypeDefault.get_all_defaults(org_id)

    # Create form for CSRF token
    form = FlaskForm()

    return render_template(
        "organization_admin/configure_rollup.html",
        value_type=value_type,
        default_enabled=default_enabled,
        default_formula=default_formula,
        current_system_rule=current_system_rule,
        current_initiative_rule=current_initiative_rule,
        current_challenge_rule=current_challenge_rule,
        entity_defaults=entity_defaults,
        form=form,
        csrf_token=generate_csrf,
    )


# Governance Body Management


@bp.route("/governance-bodies")
@login_required
@organization_required
def governance_bodies():
    """List all governance bodies"""
    from flask_wtf import FlaskForm

    org_id = session.get("organization_id")
    governance_bodies = (
        GovernanceBody.query.filter_by(organization_id=org_id).order_by(GovernanceBody.display_order).all()
    )
    delete_form = FlaskForm()  # Simple form just for CSRF token
    return render_template(
        "organization_admin/governance_bodies.html",
        governance_bodies=governance_bodies,
        delete_form=delete_form,
        csrf_token=generate_csrf,
    )


@bp.route("/governance-bodies/reorder", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_governance_bodies")
def reorder_governance_bodies():
    """Update governance body display order via AJAX"""
    org_id = session.get("organization_id")
    data = request.get_json()
    order = data.get("order", [])

    if not order:
        return jsonify({"success": False, "error": "No order provided"}), 400

    try:
        for index, gb_id in enumerate(order):
            gb = GovernanceBody.query.filter_by(id=gb_id, organization_id=org_id).first()
            if gb:
                gb.display_order = index

        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/governance-bodies/create", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_governance_bodies")
def create_governance_body():
    """Create a new governance body"""
    form = GovernanceBodyCreateForm()

    if form.validate_on_submit():
        governance_body = GovernanceBody(
            organization_id=session.get("organization_id"),
            name=form.name.data,
            abbreviation=form.abbreviation.data,
            description=form.description.data,
            color=form.color.data,
            is_active=form.is_active.data,
            is_default=False,  # Only migration creates default
        )
        db.session.add(governance_body)
        db.session.commit()
        flash(f"Governance Body {governance_body.name} created successfully", "success")

        # Check if we need to return to KPI creation
        return_to_link_id = session.pop("return_to_kpi_creation", None)
        if return_to_link_id:
            # Store the newly created governance body ID for pre-selection
            if "preselect_governance_bodies" not in session:
                session["preselect_governance_bodies"] = []
            session["preselect_governance_bodies"].append(governance_body.id)
            session.modified = True
            flash("✓ Governance Body created! Continue creating your KPI below.", "info")
            return redirect(url_for("organization_admin.create_kpi", link_id=return_to_link_id))

        return redirect(url_for("organization_admin.governance_bodies"))

    return render_template("organization_admin/create_governance_body.html", form=form, csrf_token=generate_csrf)


@bp.route("/governance-bodies/<int:gb_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_governance_bodies")
def edit_governance_body(gb_id):
    """Edit a governance body"""
    org_id = session.get("organization_id")
    governance_body = GovernanceBody.query.get_or_404(gb_id)

    if governance_body.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("organization_admin.governance_bodies"))

    # Build sequential nav list (stable sort: order then name)
    all_gbs = GovernanceBody.query.filter_by(organization_id=org_id).order_by(GovernanceBody.display_order, GovernanceBody.name).all()
    nav_ids = [gb.id for gb in all_gbs]
    nav_pos = nav_ids.index(gb_id) if gb_id in nav_ids else 0
    prev_id = nav_ids[nav_pos - 1] if nav_pos > 0 else None
    next_id = nav_ids[nav_pos + 1] if nav_pos < len(nav_ids) - 1 else None

    form = GovernanceBodyEditForm(obj=governance_body)

    if form.validate_on_submit():
        governance_body.name = form.name.data
        governance_body.abbreviation = form.abbreviation.data
        governance_body.description = form.description.data
        governance_body.color = form.color.data
        governance_body.is_active = form.is_active.data
        db.session.commit()

        # Navigate based on action
        nav_action = request.form.get("nav_action")
        if nav_action == "prev" and prev_id:
            return redirect(url_for("organization_admin.edit_governance_body", gb_id=prev_id))
        elif nav_action == "next" and next_id:
            return redirect(url_for("organization_admin.edit_governance_body", gb_id=next_id))

        flash(f"Governance Body {governance_body.name} updated successfully", "success")
        return redirect(url_for("organization_admin.governance_bodies"))

    return render_template(
        "organization_admin/edit_governance_body.html",
        form=form,
        governance_body=governance_body,
        csrf_token=generate_csrf,
        nav_pos=nav_pos,
        nav_total=len(nav_ids),
        prev_id=prev_id,
        next_id=next_id,
    )


@bp.route("/governance-bodies/<int:gb_id>/delete", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_governance_bodies")
def delete_governance_body(gb_id):
    """Delete a governance body (cannot delete default)"""
    org_id = session.get("organization_id")
    governance_body = GovernanceBody.query.filter_by(id=gb_id, organization_id=org_id).first_or_404()

    if governance_body.is_default:
        flash("Cannot delete the default governance body", "danger")
        return redirect(url_for("organization_admin.governance_bodies"))

    gb_name = governance_body.name
    db.session.delete(governance_body)
    db.session.commit()
    flash(f"Governance Body {gb_name} deleted successfully", "success")
    return redirect(url_for("organization_admin.governance_bodies"))


# YAML Import/Export


@bp.route("/yaml-upload", methods=["GET", "POST"])
@login_required
@organization_required
def yaml_upload():
    """Upload YAML file to create complete organizational structure"""
    org_id = session.get("organization_id")
    form = YAMLUploadForm()

    if form.validate_on_submit():
        if not form.confirm_delete.data:
            flash("You must confirm that you understand all data will be deleted", "danger")
            return redirect(url_for("organization_admin.yaml_upload"))

        try:
            # Read uploaded file
            yaml_file = form.yaml_file.data
            yaml_content = yaml_file.read().decode("utf-8")

            # Delete ALL existing organization data
            # This is intentional and destructive - user was warned!
            _delete_all_organization_data(org_id)

            # Import from YAML
            result = YAMLImportService.import_from_string(yaml_content, org_id, dry_run=False)

            if result.get("success"):
                flash("✓ Import successful!", "success")
                flash(
                    f'Created: {result["spaces"]} spaces, {result["challenges"]} challenges, '
                    f'{result["initiatives"]} initiatives, {result["systems"]} systems, '
                    f'{result["kpis"]} KPIs, {result["value_types"]} value types',
                    "info",
                )

                if result.get("errors"):
                    flash(f'Warnings: {len(result["errors"])} issues encountered', "warning")
                    for error in result["errors"][:5]:  # Show first 5 errors
                        flash(f"⚠ {error}", "warning")

                return redirect(url_for("workspace.index"))
            else:
                flash("Import failed", "danger")
                for error in result.get("errors", []):
                    flash(error, "danger")

        except Exception as e:
            db.session.rollback()
            flash(f"Error uploading YAML: {str(e)}", "danger")

    return render_template("organization_admin/yaml_upload.html", form=form, csrf_token=generate_csrf)


@bp.route("/yaml-export")
@login_required
@organization_required
def yaml_export():
    """Export organization structure to YAML file"""
    from io import BytesIO

    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

    try:
        # Generate YAML content
        yaml_content = YAMLExportService.export_to_yaml(org_id)

        # Create BytesIO object for download
        yaml_bytes = BytesIO(yaml_content.encode("utf-8"))
        yaml_bytes.seek(0)

        # Create safe filename
        safe_org_name = "".join(c for c in org_name if c.isalnum() or c in (" ", "-", "_")).strip()
        filename = f"structure_{safe_org_name}.yaml"

        return send_file(yaml_bytes, mimetype="application/x-yaml", as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f"Error exporting YAML: {str(e)}", "danger")
        return redirect(url_for("organization_admin.index"))


def _delete_all_organization_data(org_id):
    """
    Delete ALL data for an organization.
    This is called before YAML import to start fresh.

    WARNING: This is destructive and irreversible!
    """
    # Delete in correct order to respect foreign keys
    # RULE: Delete dependent data BEFORE the entities they depend on

    # 1. Delete Mentions and Comments (depends on KPIs)
    from app.models import CellComment, MentionNotification

    # Delete mentions first (they reference comments with CASCADE, but explicit is safer)
    mentions = (
        MentionNotification.query.join(CellComment)
        .join(KPIValueTypeConfig)
        .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(Initiative.organization_id == org_id)
        .all()
    )
    for mention in mentions:
        db.session.delete(mention)

    # Then delete comments
    comments = (
        CellComment.query.join(KPIValueTypeConfig)
        .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(Initiative.organization_id == org_id)
        .all()
    )
    for comment in comments:
        db.session.delete(comment)

    # 2. Delete Snapshots (depends on KPIs and ValueTypes)
    from app.models import KPISnapshot, RollupSnapshot

    kpi_snapshots = (
        KPISnapshot.query.join(KPIValueTypeConfig)
        .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(Initiative.organization_id == org_id)
        .all()
    )
    for snapshot in kpi_snapshots:
        db.session.delete(snapshot)

    rollup_snapshots = RollupSnapshot.query.join(ValueType).filter(ValueType.organization_id == org_id).all()
    for snapshot in rollup_snapshots:
        db.session.delete(snapshot)

    # 3. Delete Contributions (depends on Configs)
    from app.models import Contribution

    contributions = (
        Contribution.query.join(KPIValueTypeConfig)
        .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(Initiative.organization_id == org_id)
        .all()
    )
    for contrib in contributions:
        db.session.delete(contrib)

    # 4. Delete KPI-Governance Body Links (depends on KPIs and GovernanceBodies)
    from app.models import KPIGovernanceBodyLink

    gb_links = (
        KPIGovernanceBodyLink.query.join(KPI)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(Initiative.organization_id == org_id)
        .all()
    )
    for link in gb_links:
        db.session.delete(link)

    # 5. Delete KPIValueTypeConfigs (depends on KPIs and ValueTypes)
    configs = (
        KPIValueTypeConfig.query.join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink)
        .join(Initiative)
        .filter(Initiative.organization_id == org_id)
        .all()
    )
    for config in configs:
        db.session.delete(config)

    # 6. Delete KPIs (depends on InitiativeSystemLinks)
    kpis = KPI.query.join(InitiativeSystemLink).join(Initiative).filter(Initiative.organization_id == org_id).all()
    for kpi in kpis:
        db.session.delete(kpi)

    # 7. Delete InitiativeSystemLinks
    links = InitiativeSystemLink.query.join(Initiative).filter(Initiative.organization_id == org_id).all()
    for link in links:
        db.session.delete(link)

    # 8. Delete Systems
    systems = System.query.filter_by(organization_id=org_id).all()
    for system in systems:
        db.session.delete(system)

    # 9. Delete ChallengeInitiativeLinks
    from app.models import ChallengeInitiativeLink

    challenge_links = ChallengeInitiativeLink.query.join(Challenge).filter(Challenge.organization_id == org_id).all()
    for link in challenge_links:
        db.session.delete(link)

    # 10. Delete Initiatives
    initiatives = Initiative.query.filter_by(organization_id=org_id).all()
    for initiative in initiatives:
        db.session.delete(initiative)

    # 11. Delete Challenges
    challenges = Challenge.query.filter_by(organization_id=org_id).all()
    for challenge in challenges:
        db.session.delete(challenge)

    # 12. Delete Spaces
    spaces = Space.query.filter_by(organization_id=org_id).all()
    for space in spaces:
        db.session.delete(space)

    # 13. Delete Action Items and Memos (and their mentions via cascade)
    from app.models import ActionItem

    action_items = ActionItem.query.filter_by(organization_id=org_id).all()
    for ai in action_items:
        db.session.delete(ai)

    db.session.flush()

    # 15. Delete RollupRules (depends on ValueTypes)
    from app.models import RollupRule

    rollup_rules = RollupRule.query.join(ValueType).filter(ValueType.organization_id == org_id).all()
    for rule in rollup_rules:
        db.session.delete(rule)

    # 16. Delete ValueTypes (NOW safe to delete)
    value_types = ValueType.query.filter_by(organization_id=org_id).all()
    for vt in value_types:
        db.session.delete(vt)

    # 17. Delete Governance Bodies (NOW safe to delete)
    gov_bodies = GovernanceBody.query.filter_by(organization_id=org_id).all()
    for gb in gov_bodies:
        db.session.delete(gb)

    # 18. Delete Audit Logs
    from app.models import AuditLog

    audit_logs = AuditLog.query.filter_by(organization_id=org_id).all()
    for log in audit_logs:
        db.session.delete(log)

    # 19. Delete Stakeholders (memberships/relationships/entity links cascade)
    from app.models import Stakeholder, StakeholderMap

    StakeholderMap.query.filter_by(organization_id=org_id).delete(synchronize_session=False)
    Stakeholder.query.filter_by(organization_id=org_id).delete(synchronize_session=False)

    # 21. Delete Geography (regions, countries, sites — cascade deletes children)
    from app.models import GeographyRegion

    GeographyRegion.query.filter_by(organization_id=org_id).delete(synchronize_session=False)

    # 22. Delete User Filter Presets (saved views) for this org
    from app.models import UserFilterPreset

    UserFilterPreset.query.filter_by(organization_id=org_id).delete(synchronize_session=False)

    # 23a. Delete Standalone Decisions
    from app.models import Decision
    Decision.query.filter_by(organization_id=org_id).delete(synchronize_session=False)

    # 23. Delete Strategic Pillars
    from app.models import StrategicPillar

    StrategicPillar.query.filter_by(organization_id=org_id).delete(synchronize_session=False)

    # 24. Delete Impact Levels
    from app.models import ImpactLevel

    ImpactLevel.query.filter_by(organization_id=org_id).delete(synchronize_session=False)

    # 25. Delete Entity Type Defaults (branding)
    from app.models import EntityTypeDefault

    EntityTypeDefault.query.filter_by(organization_id=org_id).delete(synchronize_session=False)

    # 26. Delete org-level entity links
    EntityLink.query.filter_by(entity_type="organization", entity_id=org_id).delete(synchronize_session=False)

    db.session.flush()



@bp.route("/initiatives/<int:initiative_id>/form", methods=["GET", "POST"])
@login_required
@organization_required
def initiative_form(initiative_id):
    """View and edit detailed initiative form"""
    from app.models import Decision
    org_id = session.get("organization_id")
    initiative = Initiative.query.filter_by(id=initiative_id, organization_id=org_id).first_or_404()

    # Check edit permission
    can_edit = current_user.can_manage_initiatives(org_id)

    # Check if user requested edit mode
    edit_mode = request.args.get("edit", "0") == "1" and can_edit

    if request.method == "POST":
        if not can_edit:
            flash("You do not have permission to edit initiative forms", "error")
            return redirect(url_for("organization_admin.initiative_form", initiative_id=initiative.id))
        # Capture old values for audit
        old_values = {
            "mission": initiative.mission,
            "success_criteria": initiative.success_criteria,
            "responsible_person": initiative.responsible_person,
            "team_members": initiative.team_members,
            "handover_organization": initiative.handover_organization,
            "deliverables": initiative.deliverables,
            "impact_on_challenge": initiative.impact_on_challenge,
            "impact_rationale": initiative.impact_rationale,
        }

        # Update fields
        initiative.mission = request.form.get("mission")
        initiative.success_criteria = request.form.get("success_criteria")
        initiative.responsible_person = request.form.get("responsible_person")
        initiative.team_members = request.form.get("team_members")
        initiative.handover_organization = request.form.get("handover_organization")
        initiative.deliverables = request.form.get("deliverables")
        initiative.impact_on_challenge = request.form.get("impact_on_challenge")
        initiative.impact_rationale = request.form.get("impact_rationale")
        initiative.impact_level = int(request.form.get("impact_level")) if request.form.get("impact_level") else None

        # Audit log
        new_values = {
            "mission": initiative.mission,
            "success_criteria": initiative.success_criteria,
            "responsible_person": initiative.responsible_person,
            "team_members": initiative.team_members,
            "handover_organization": initiative.handover_organization,
            "deliverables": initiative.deliverables,
            "impact_on_challenge": initiative.impact_on_challenge,
            "impact_rationale": initiative.impact_rationale,
        }
        AuditService.log_update("Initiative Form", initiative.id, initiative.name, old_values, new_values)

        db.session.commit()
        flash(f"Initiative form for '{initiative.name}' updated successfully", "success")

        # Return to origin (review position, action items, workspace, or self)
        return_to = request.args.get("return_to") or request.form.get("return_to")
        if return_to and return_to not in ("action_items", "workspace"):
            return redirect(return_to)
        if return_to == "action_items":
            return redirect(url_for("action_items"))
        if return_to == "workspace" or request.form.get("redirect_after_save") == "workspace":
            return redirect(url_for("workspace.index"))

        return redirect(url_for("organization_admin.initiative_form", initiative_id=initiative.id))

    # Prepare KPI data with values
    kpi_data = []
    for sys_link in initiative.system_links:
        system_kpis = []
        for kpi in sys_link.kpis:
            if kpi.is_archived:
                continue

            # Get status
            status = kpi.get_status()

            # Get values for each value type
            value_types_data = []
            for config in kpi.value_type_configs:
                consensus = config.get_consensus_value()
                if consensus:
                    raw_value = consensus.get("value")
                    formatted_value = current_app.jinja_env.filters["format_value"](
                        raw_value, config.value_type, config
                    )
                    vt = config.value_type
                    value_types_data.append(
                        {
                            "name": vt.name,
                            "value": raw_value,
                            "formatted_value": formatted_value,
                            "unit_label": vt.unit_label,
                            "color": config.get_value_color(raw_value),
                            "kind": vt.kind,
                            "list_label": vt.get_list_option_label(raw_value) if vt.is_list() and raw_value else None,
                            "list_color": vt.get_list_option_color(raw_value) if vt.is_list() and raw_value else None,
                        }
                    )

            kpi_gbs = [{"id": gbl.governance_body_id, "name": gbl.governance_body.name,
                        "abbreviation": gbl.governance_body.abbreviation, "color": gbl.governance_body.color}
                       for gbl in kpi.governance_body_links if gbl.governance_body]
            system_kpis.append(
                {
                    "id": kpi.id,
                    "name": kpi.name,
                    "status": status["status"],
                    "status_reason": status["reason"],
                    "value_types": value_types_data,
                    "first_vt_id": kpi.value_type_configs[0].value_type_id if kpi.value_type_configs else None,
                    "governance_bodies": kpi_gbs,
                }
            )

        if system_kpis:
            kpi_data.append({"system_name": sys_link.system.name, "kpis": system_kpis})

    from flask_wtf.csrf import generate_csrf

    # Get entity type defaults with logos
    entity_defaults_raw = EntityTypeDefault.query.filter_by(organization_id=org_id).all()
    entity_defaults = {}
    for default in entity_defaults_raw:
        logo_url = None
        if default.default_logo_data and default.default_logo_mime_type:
            logo_url = f"data:{default.default_logo_mime_type};base64,{base64.b64encode(default.default_logo_data).decode('utf-8')}"
        entity_defaults[default.entity_type] = {
            "color": default.default_color,
            "icon": default.default_icon,
            "logo": logo_url,
        }

    # Get entity links for this initiative
    entity_links = EntityLink.get_links_for_entity("initiative", initiative.id, current_user.id, include_private=True)

    # Get org users for action generation owner dropdown
    from app.models import GovernanceBody, User, UserOrganizationMembership
    org_users = (
        db.session.query(User)
        .join(UserOrganizationMembership, UserOrganizationMembership.user_id == User.id)
        .filter(UserOrganizationMembership.organization_id == org_id, User.is_active.is_(True))
        .order_by(User.display_name)
        .all()
    )
    org_governance_bodies = GovernanceBody.query.filter_by(organization_id=org_id, is_active=True).order_by(
        GovernanceBody.display_order
    ).all()

    # Collect all entity references that belong to this initiative
    # (initiative itself, its systems, and their KPIs)
    entity_refs = [("initiative", initiative.id, initiative.name)]
    for sys_link in initiative.system_links:
        sys = sys_link.system
        entity_refs.append(("system", sys.id, sys.name))
        for kpi in sys_link.kpis:
            entity_refs.append(("kpi", kpi.id, kpi.name))

    # Query all action item mentions for any of these entities
    from sqlalchemy import or_
    mention_filters = or_(*[
        (ActionItemMention.entity_type == etype) & (ActionItemMention.entity_id == eid)
        for etype, eid, _ename in entity_refs
    ])
    all_mentions = ActionItemMention.query.filter(mention_filters).all()

    # Build map: action_item_id → list of source dicts
    entity_name_map = {(etype, eid): (eid, ename, etype) for etype, eid, ename in entity_refs}
    action_sources_map = {}
    for mention in all_mentions:
        key = (mention.entity_type, mention.entity_id)
        if key in entity_name_map:
            _, ename, etype = entity_name_map[key]
            action_sources_map.setdefault(mention.action_item_id, []).append(
                {"type": etype, "name": ename}
            )

    # Get deduplicated action items ordered by status + due date
    if action_sources_map:
        linked_actions = (
            ActionItem.query
            .filter(ActionItem.id.in_(action_sources_map.keys()), ActionItem.organization_id == org_id)
            .order_by(ActionItem.status, ActionItem.due_date.asc().nullslast())
            .all()
        )
    else:
        linked_actions = []

    # Get progress updates for this initiative (newest first)
    progress_updates = (
        InitiativeProgressUpdate.query
        .filter_by(initiative_id=initiative.id)
        .order_by(InitiativeProgressUpdate.created_at.desc())
        .all()
    )
    active_tab = request.args.get("tab", "form")
    today = datetime.utcnow().date()

    # Execution Review Navigator
    nav_context = None
    nav_param = request.args.get("nav", "")
    nav_pos_arg = request.args.get("nav_pos", 0, type=int)
    nav_back = request.args.get("nav_back", "")
    nav_tab = request.args.get("nav_tab", "execution")
    if nav_param:
        try:
            nav_ids = [int(x) for x in nav_param.split(",") if x.strip().isdigit()]
        except Exception:
            nav_ids = []
        if nav_ids and 0 <= nav_pos_arg < len(nav_ids):
            # Fetch all initiative names for the nav list (org-scoped)
            from sqlalchemy import func as sqlfunc
            nav_initiatives = Initiative.query.filter(
                Initiative.id.in_(nav_ids), Initiative.organization_id == org_id
            ).all()
            nav_init_map = {i.id: i for i in nav_initiatives}

            # Get latest RAG per initiative (one query)
            rag_subq = (
                db.session.query(
                    InitiativeProgressUpdate.initiative_id,
                    sqlfunc.max(InitiativeProgressUpdate.created_at).label("max_at"),
                )
                .filter(InitiativeProgressUpdate.initiative_id.in_(nav_ids))
                .group_by(InitiativeProgressUpdate.initiative_id)
                .subquery()
            )
            latest_rags = db.session.query(
                InitiativeProgressUpdate.initiative_id,
                InitiativeProgressUpdate.rag_status,
            ).join(
                rag_subq,
                (InitiativeProgressUpdate.initiative_id == rag_subq.c.initiative_id)
                & (InitiativeProgressUpdate.created_at == rag_subq.c.max_at),
            ).all()
            nav_rag_map = {r.initiative_id: r.rag_status for r in latest_rags}

            # Resolve Space + Challenge context for current initiative
            from app.models import ChallengeInitiativeLink as CIL
            first_link = CIL.query.filter_by(initiative_id=initiative.id).first()
            nav_space_name = first_link.challenge.space.name if first_link and first_link.challenge and first_link.challenge.space else None
            nav_challenge_name = first_link.challenge.name if first_link and first_link.challenge else None

            prev_pos = nav_pos_arg - 1
            next_pos = nav_pos_arg + 1
            prev_id = nav_ids[prev_pos] if prev_pos >= 0 else None
            next_id = nav_ids[next_pos] if next_pos < len(nav_ids) else None

            # In review mode, active tab is driven by nav_tab preference
            active_tab = nav_tab if nav_tab in ("form", "execution") else "execution"

            from urllib.parse import quote as _urlquote
            nav_context = {
                "nav_param": nav_param,
                "nav_back": nav_back,
                "nav_back_enc": _urlquote(nav_back, safe="") if nav_back else "",
                "nav_tab": nav_tab,
                "pos": nav_pos_arg,
                "total": len(nav_ids),
                "prev_id": prev_id,
                "prev_name": nav_init_map[prev_id].name if prev_id and prev_id in nav_init_map else None,
                "next_id": next_id,
                "next_name": nav_init_map[next_id].name if next_id and next_id in nav_init_map else None,
                "space_name": nav_space_name,
                "challenge_name": nav_challenge_name,
                "dots": [
                    {
                        "id": iid,
                        "name": nav_init_map[iid].name if iid in nav_init_map else f"#{iid}",
                        "rag": nav_rag_map.get(iid),
                        "impact_level": nav_init_map[iid].impact_level if iid in nav_init_map else None,
                    }
                    for iid in nav_ids
                ],
            }

    # Compute true importance + parent context
    from app.models import ImpactLevel, ChallengeInitiativeLink as _CIL
    from app.services.impact_service import compute_true_importance

    impact_scale = ImpactLevel.get_org_levels(org_id)
    _org = Organization.query.get(org_id)
    true_importance_level = None
    parent_context = {}
    _link = _CIL.query.filter_by(initiative_id=initiative.id).first()
    _weights = {lvl: impact_scale[lvl]["weight"] for lvl in impact_scale} if impact_scale else {}
    _method = _org.impact_calc_method or "geometric_mean" if _org else "geometric_mean"
    _custom_matrix = _org.impact_qfd_matrix if _org else None
    _custom_reinforce = _org.impact_reinforce_weights if _org else None

    if _link and _link.challenge:
        ch = _link.challenge
        sp = ch.space
        sp_ti = compute_true_importance([sp.impact_level], _method, _weights, _custom_matrix, _custom_reinforce) if sp and sp.impact_level else None
        ch_ti = compute_true_importance([sp.impact_level, ch.impact_level], _method, _weights, _custom_matrix, _custom_reinforce) if sp and sp.impact_level and ch.impact_level else None
        parent_context["challenge"] = {"name": ch.name, "impact_level": ch.impact_level, "true_importance_level": ch_ti}
        if sp:
            parent_context["space"] = {"name": sp.name, "impact_level": sp.impact_level, "true_importance_level": sp_ti}

    if impact_scale and initiative.impact_level and _link and _link.challenge and _link.challenge.space:
        chain = [_link.challenge.space.impact_level, _link.challenge.impact_level, initiative.impact_level]
        if all(chain):
            true_importance_level = compute_true_importance(chain, _method, _weights, _custom_matrix, _custom_reinforce)

    # GB-scoped KPI split (when ?gb= param is present from filtered review)
    gb_filter_param = request.args.get("gb", "")
    gb_filter_ids = set()
    if gb_filter_param:
        try:
            gb_filter_ids = {int(x) for x in gb_filter_param.split(",") if x.strip().isdigit()}
        except (ValueError, TypeError):
            pass

    kpi_data_scoped = []
    kpi_data_other = []
    if gb_filter_ids:
        for group in kpi_data:
            scoped_kpis = []
            other_kpis = []
            for kpi_info in group["kpis"]:
                kpi_gb_ids = {gb["id"] for gb in kpi_info.get("governance_bodies", [])}
                if kpi_gb_ids & gb_filter_ids:
                    scoped_kpis.append(kpi_info)
                else:
                    other_kpis.append(kpi_info)
            if scoped_kpis:
                kpi_data_scoped.append({"system_name": group["system_name"], "kpis": scoped_kpis})
            if other_kpis:
                kpi_data_other.append({"system_name": group["system_name"], "kpis": other_kpis})
    else:
        kpi_data_scoped = kpi_data

    # Get GB names for display
    gb_filter_names = []
    if gb_filter_ids:
        gb_filter_names = [gb.abbreviation or gb.name for gb in GovernanceBody.query.filter(GovernanceBody.id.in_(gb_filter_ids)).all()]

    return render_template(
        "organization_admin/initiative_form.html",
        initiative=initiative,
        kpi_data=kpi_data_scoped,
        kpi_data_other=kpi_data_other,
        gb_filter_names=gb_filter_names,
        csrf_token=generate_csrf,
        can_edit=can_edit,
        edit_mode=edit_mode,
        entity_defaults=entity_defaults,
        entity_links=entity_links,
        org_users=org_users,
        org_governance_bodies=org_governance_bodies,
        linked_actions=linked_actions,
        action_sources_map=action_sources_map,
        progress_updates=progress_updates,
        active_tab=active_tab,
        today=today,
        nav_context=nav_context,
        true_importance_level=true_importance_level,
        parent_context=parent_context,
        initiative_decisions=[d for d in Decision.query.filter_by(organization_id=org_id).order_by(Decision.created_at.desc()).all()
                              if d.mentions_entity("initiative", initiative.id)],
    )


@bp.route("/initiatives/<int:initiative_id>/progress-update", methods=["POST"])
@login_required
@organization_required
def initiative_progress_update_create(initiative_id):
    """Create a progress update for an initiative"""
    org_id = session.get("organization_id")
    initiative = Initiative.query.filter_by(id=initiative_id, organization_id=org_id).first_or_404()
    if not current_user.can_manage_initiatives(org_id):
        flash("Permission denied.", "error")
        return redirect(url_for("organization_admin.initiative_form", initiative_id=initiative_id, tab="execution"))

    rag_status = request.form.get("rag_status", "").strip()
    if rag_status not in ("green", "amber", "red"):
        flash("Invalid RAG status.", "error")
        return redirect(url_for("organization_admin.initiative_form", initiative_id=initiative_id, tab="execution"))

    upd = InitiativeProgressUpdate(
        initiative_id=initiative.id,
        rag_status=rag_status,
        accomplishments=request.form.get("accomplishments", "").strip() or None,
        next_steps=request.form.get("next_steps", "").strip() or None,
        blockers=request.form.get("blockers", "").strip() or None,
        created_by=current_user.id,
    )
    db.session.add(upd)
    db.session.flush()
    # Create Decision objects from the decisions JSON
    import json as _dec_json
    from app.models import Decision
    _dec_raw = request.form.get("decisions_json", "")
    if _dec_raw:
        try:
            _dec_list = _dec_json.loads(_dec_raw)
            for _d in (_dec_list if isinstance(_dec_list, list) else []):
                if not _d.get("what", "").strip():
                    continue
                # Build entity mentions — always include this initiative
                _mentions = [{"entity_type": "initiative", "entity_id": initiative.id, "entity_name": initiative.name}]
                for _m in (_d.get("mentions") or []):
                    if _m.get("entity_type") and _m.get("entity_id"):
                        _mentions.append(_m)
                _tags = _d.get("tag", "")
                _tags_list = [t.strip() for t in _tags.split(",") if t.strip()] if isinstance(_tags, str) else ([_tags] if _tags else [])
                _gb_id = _d.get("gb_id")
                db.session.add(Decision(
                    organization_id=org_id,
                    created_by_id=current_user.id,
                    what=_d["what"].strip(),
                    who=_d.get("who", "").strip() or None,
                    tags=_tags_list if _tags_list else None,
                    entity_mentions=_mentions,
                    governance_body_id=int(_gb_id) if _gb_id else None,
                ))
        except (ValueError, TypeError):
            pass
    AuditService.log_create("InitiativeProgressUpdate", initiative.id, initiative.name, {"rag_status": rag_status})
    db.session.commit()
    flash("Progress update saved.", "success")
    redirect_kwargs = {"initiative_id": initiative_id, "tab": "execution"}
    nav = request.form.get("nav", "")
    nav_pos = request.form.get("nav_pos", "")
    if nav:
        redirect_kwargs["nav"] = nav
    if nav_pos:
        redirect_kwargs["nav_pos"] = nav_pos
    nav_back = request.form.get("nav_back", "")
    if nav_back:
        redirect_kwargs["nav_back"] = nav_back
    nav_tab = request.form.get("nav_tab", "")
    if nav_tab:
        redirect_kwargs["nav_tab"] = nav_tab
    return redirect(url_for("organization_admin.initiative_form", **redirect_kwargs))


@bp.route("/initiatives/<int:initiative_id>/progress-update/<int:update_id>/edit", methods=["POST"])
@login_required
@organization_required
def initiative_progress_update_edit(initiative_id, update_id):
    """Edit a progress update"""
    org_id = session.get("organization_id")
    initiative = Initiative.query.filter_by(id=initiative_id, organization_id=org_id).first_or_404()
    upd = InitiativeProgressUpdate.query.filter_by(id=update_id, initiative_id=initiative.id).first_or_404()
    if not current_user.can_manage_initiatives(org_id):
        flash("Permission denied.", "error")
        return redirect(url_for("organization_admin.initiative_form", initiative_id=initiative_id, tab="execution"))

    rag_status = request.form.get("rag_status", "").strip()
    if rag_status not in ("green", "amber", "red"):
        flash("Invalid RAG status.", "error")
        return redirect(url_for("organization_admin.initiative_form", initiative_id=initiative_id, tab="execution"))

    old_rag = upd.rag_status
    upd.rag_status = rag_status
    upd.accomplishments = request.form.get("accomplishments", "").strip() or None
    upd.next_steps = request.form.get("next_steps", "").strip() or None
    upd.blockers = request.form.get("blockers", "").strip() or None
    # Create Decision objects from decisions JSON (edit: only new ones)
    import json as _dec_json2
    from app.models import Decision
    _dec_raw2 = request.form.get("decisions_json", "")
    if _dec_raw2:
        try:
            _dec_list2 = _dec_json2.loads(_dec_raw2)
            for _d2 in (_dec_list2 if isinstance(_dec_list2, list) else []):
                if not _d2.get("what", "").strip():
                    continue
                _mentions2 = [{"entity_type": "initiative", "entity_id": initiative.id, "entity_name": initiative.name}]
                for _m2 in (_d2.get("mentions") or []):
                    if _m2.get("entity_type") and _m2.get("entity_id"):
                        _mentions2.append(_m2)
                _tags2 = _d2.get("tag", "")
                _tags_list2 = [t.strip() for t in _tags2.split(",") if t.strip()] if isinstance(_tags2, str) else ([_tags2] if _tags2 else [])
                _gb_id2 = _d2.get("gb_id")
                db.session.add(Decision(
                    organization_id=org_id,
                    created_by_id=current_user.id,
                    what=_d2["what"].strip(),
                    who=_d2.get("who", "").strip() or None,
                    tags=_tags_list2 if _tags_list2 else None,
                    entity_mentions=_mentions2,
                    governance_body_id=int(_gb_id2) if _gb_id2 else None,
                ))
        except (ValueError, TypeError):
            pass
    AuditService.log_update(
        "InitiativeProgressUpdate", upd.id, initiative.name,
        {"rag_status": old_rag}, {"rag_status": rag_status}
    )
    db.session.commit()
    flash("Progress update updated.", "success")
    redirect_kwargs = {"initiative_id": initiative_id, "tab": "execution"}
    nav = request.form.get("nav", "")
    nav_pos = request.form.get("nav_pos", "")
    if nav:
        redirect_kwargs["nav"] = nav
    if nav_pos:
        redirect_kwargs["nav_pos"] = nav_pos
    nav_back = request.form.get("nav_back", "")
    if nav_back:
        redirect_kwargs["nav_back"] = nav_back
    nav_tab = request.form.get("nav_tab", "")
    if nav_tab:
        redirect_kwargs["nav_tab"] = nav_tab
    return redirect(url_for("organization_admin.initiative_form", **redirect_kwargs))


@bp.route("/initiatives/<int:initiative_id>/progress-update/<int:update_id>/delete", methods=["POST"])
@login_required
@organization_required
def initiative_progress_update_delete(initiative_id, update_id):
    """Delete a progress update"""
    org_id = session.get("organization_id")
    initiative = Initiative.query.filter_by(id=initiative_id, organization_id=org_id).first_or_404()
    upd = InitiativeProgressUpdate.query.filter_by(id=update_id, initiative_id=initiative.id).first_or_404()
    if not current_user.can_manage_initiatives(org_id):
        flash("Permission denied.", "error")
        return redirect(url_for("organization_admin.initiative_form", initiative_id=initiative_id, tab="execution"))

    AuditService.log_delete("InitiativeProgressUpdate", upd.id, initiative.name)
    db.session.delete(upd)
    db.session.commit()
    flash("Progress update deleted.", "success")
    redirect_kwargs = {"initiative_id": initiative_id, "tab": "execution"}
    nav = request.form.get("nav", "")
    nav_pos = request.form.get("nav_pos", "")
    if nav:
        redirect_kwargs["nav"] = nav
    if nav_pos:
        redirect_kwargs["nav_pos"] = nav_pos
    nav_back = request.form.get("nav_back", "")
    if nav_back:
        redirect_kwargs["nav_back"] = nav_back
    nav_tab = request.form.get("nav_tab", "")
    if nav_tab:
        redirect_kwargs["nav_tab"] = nav_tab
    return redirect(url_for("organization_admin.initiative_form", **redirect_kwargs))


@bp.route("/initiatives/<int:initiative_id>/check-action-titles")
@login_required
@organization_required
def check_action_titles(initiative_id):
    """Return which of the given titles already exist as actions linked to this initiative."""
    from app.models import ActionItem, ActionItemMention

    org_id = session.get("organization_id")
    titles = request.args.getlist("titles[]")
    if not titles:
        return jsonify({"existing": []})

    # Find actions linked to this initiative
    linked_ids = db.session.query(ActionItemMention.action_item_id).filter_by(
        entity_type="initiative", entity_id=initiative_id
    )
    existing = (
        ActionItem.query.filter(
            ActionItem.id.in_(linked_ids),
            ActionItem.organization_id == org_id,
            ActionItem.title.in_(titles),
        )
        .with_entities(ActionItem.title)
        .all()
    )
    return jsonify({"existing": [row.title for row in existing]})


@bp.route("/initiatives/<int:initiative_id>/generate-actions", methods=["POST"])
@login_required
@organization_required
def generate_actions(initiative_id):
    """Create action items from selected deliverable rows and link them to the initiative."""
    from datetime import date, timedelta

    from app.models import ActionItem, ActionItemMention, Initiative, User, UserOrganizationMembership
    from app.services.action_item_service import ActionItemService

    org_id = session.get("organization_id")
    initiative = Initiative.query.filter_by(id=initiative_id, organization_id=org_id).first_or_404()

    data = request.get_json()
    if not data or "actions" not in data:
        return jsonify({"error": "No actions provided"}), 400

    # Validate owner belongs to org
    valid_owner_ids = {
        row.user_id
        for row in UserOrganizationMembership.query.filter_by(organization_id=org_id).with_entities(
            UserOrganizationMembership.user_id
        )
    }

    created = []
    errors = []

    from app.models import GovernanceBody

    for action_data in data["actions"]:
        try:
            owner_id = int(action_data.get("owner_user_id", current_user.id))
            if owner_id not in valid_owner_ids:
                owner_id = current_user.id

            # Parse start_date and due_date
            start_date = None
            raw_start = action_data.get("start_date", "").strip()
            if raw_start:
                try:
                    start_date = date.fromisoformat(raw_start)
                except ValueError:
                    pass

            due_date = None
            raw_date = action_data.get("due_date", "").strip()
            if raw_date:
                try:
                    due_date = date.fromisoformat(raw_date)
                except ValueError:
                    pass  # Invalid date left as None

            item = ActionItem(
                organization_id=org_id,
                owner_user_id=owner_id,
                created_by_user_id=current_user.id,
                title=action_data["title"].strip(),
                description=action_data.get("description", f"Generated from initiative: {initiative.name}"),
                type="action",
                status=action_data.get("status", "draft"),
                priority=action_data.get("priority", "medium"),
                start_date=start_date,
                due_date=due_date,
                visibility=action_data.get("visibility", "shared"),
            )
            db.session.add(item)
            db.session.flush()

            # Attach per-action governance bodies
            gb_ids = action_data.get("governance_body_ids", [])
            if gb_ids:
                item.governance_bodies = GovernanceBody.query.filter(
                    GovernanceBody.id.in_(gb_ids),
                    GovernanceBody.organization_id == org_id,
                ).all()

            # Link to initiative
            mention = ActionItemMention(
                action_item_id=item.id,
                entity_type="initiative",
                entity_id=initiative_id,
                mention_text=f"@{initiative.name}",
            )
            db.session.add(mention)
            created.append({"id": item.id, "title": item.title})

        except Exception as e:
            errors.append({"title": action_data.get("title", "?"), "error": str(e)})

    db.session.commit()
    return jsonify({"created": len(created), "actions": created, "errors": errors})
