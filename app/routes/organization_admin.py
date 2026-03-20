"""
Organization Administration routes

For managing business content within an organization (spaces, challenges, initiatives, etc.).
"""

import base64
import io
from datetime import datetime
from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, session, url_for
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
    Challenge,
    ChallengeInitiativeLink,
    EntityLink,
    EntityTypeDefault,
    GovernanceBody,
    Initiative,
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


# Porter's Five Forces Analysis (Organization Level)


@bp.route("/porters")
@login_required
@organization_required
def organization_porters():
    """View Porter's Five Forces analysis for the organization"""
    org_id = session.get("organization_id")
    org = Organization.query.get_or_404(org_id)
    return render_template("organization_admin/organization_porters.html", organization=org, csrf_token=generate_csrf)


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

    return render_template(
        "organization_admin/index.html", org_name=org_name, stats=stats, form=form, csrf_token=generate_csrf
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


@bp.route("/settings")
@login_required
@organization_required
@any_org_admin_permission_required
def organization_settings():
    """Organization settings - logo, branding"""
    org_id = session.get("organization_id")
    org = Organization.query.get_or_404(org_id)
    form = FlaskForm()  # For CSRF
    return render_template(
        "organization_admin/organization_settings.html", organization=org, form=form, csrf_token=generate_csrf
    )


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
        return redirect(url_for("organization_admin.organization_settings"))

    file = request.files["logo"]
    if file.filename == "":
        flash("No file selected", "danger")
        return redirect(url_for("organization_admin.organization_settings"))

    # Validate file type
    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        flash("Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP", "danger")
        return redirect(url_for("organization_admin.organization_settings"))

    # Validate file size (max 5MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 5 * 1024 * 1024:  # 5MB
        flash("File too large. Maximum size: 5MB", "danger")
        return redirect(url_for("organization_admin.organization_settings"))

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

    return redirect(url_for("organization_admin.organization_settings"))


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

    return redirect(url_for("organization_admin.organization_settings"))


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
        entity_types = ["organization", "space", "challenge", "initiative", "system", "kpi"]

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

        # Audit log
        new_values = {
            "name": space.name,
            "description": space.description,
            "space_label": space.space_label,
            "is_private": space.is_private,
        }
        AuditService.log_update("Space", space.id, space.name, old_values, new_values)

        db.session.commit()
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

        # Audit log
        new_values = {
            "name": challenge.name,
            "description": challenge.description,
            "space_id": challenge.space_id,
        }
        AuditService.log_update("Challenge", challenge.id, challenge.name, old_values, new_values)

        db.session.commit()
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
        flash(f"Initiative {initiative.name} updated successfully", "success")
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

    from flask_wtf.csrf import generate_csrf

    return render_template(
        "organization_admin/edit_initiative.html",
        form=form,
        initiative=initiative,
        value_types=value_types,
        entity_defaults=entity_defaults,
        entity_links=entity_links,
        csrf_token=generate_csrf,
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
        system = System(organization_id=org_id, name=form.name.data, description=form.description.data)
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

    return render_template(
        "organization_admin/create_system.html", form=form, initiative=initiative, csrf_token=generate_csrf
    )


@bp.route("/systems/<int:system_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_systems")
def edit_system(system_id):
    """Edit an existing system"""
    org_id = session.get("organization_id")
    system = System.query.filter_by(id=system_id, organization_id=org_id).first_or_404()

    form = SystemEditForm(obj=system)

    if form.validate_on_submit():
        # Capture old values for audit
        old_values = {"name": system.name, "description": system.description}

        system.name = form.name.data
        system.description = form.description.data

        # Audit log
        new_values = {"name": system.name, "description": system.description}
        AuditService.log_update("System", system.id, system.name, old_values, new_values)

        db.session.commit()
        flash(f"System {system.name} updated successfully", "success")

        # Check if we should return to action items page
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

    return render_template(
        "organization_admin/edit_system.html",
        form=form,
        system=system,
        value_types=value_types,
        entity_defaults=entity_defaults,
        entity_links=entity_links,
        csrf_token=generate_csrf,
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
        flash(f"KPI {kpi.name} updated successfully", "success")

        # Check if we should return to action items page
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
    )


@bp.route("/kpis/<int:kpi_id>/delete", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_kpis")
def delete_kpi(kpi_id):
    """Delete a KPI"""
    org_id = session.get("organization_id")
    kpi = KPI.query.get_or_404(kpi_id)

    # Verify ownership
    if kpi.initiative_system_link.initiative.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    # Check if any other KPI is reading values from this KPI (linked KPI protection)
    from app.models import KPIValueTypeConfig

    linked_consumers = KPIValueTypeConfig.query.filter_by(linked_source_kpi_id=kpi_id).all()
    if linked_consumers:
        consumer_info = []
        for consumer in linked_consumers[:3]:  # Show up to 3 examples
            consumer_kpi = consumer.kpi
            org_name = consumer_kpi.initiative_system_link.initiative.organization.name
            consumer_info.append(f"{consumer_kpi.name} (Org: {org_name})")

        flash(
            f'Cannot delete KPI "{kpi.name}" - it is being used as a linked source by {len(linked_consumers)} other KPI(s): {", ".join(consumer_info)}{"..." if len(linked_consumers) > 3 else ""}. Please contact those organizations to remove the link first.',
            "danger",
        )
        return redirect(url_for("workspace.index"))

    kpi_name = kpi.name
    db.session.delete(kpi)
    db.session.commit()

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

    # Check if initiative is linked to any challenges
    challenge_links = ChallengeInitiativeLink.query.filter_by(initiative_id=initiative_id).all()
    if challenge_links:
        flash(
            f'Cannot delete initiative "{initiative_name}" - it is linked to {len(challenge_links)} challenge(s). Remove links first.',
            "danger",
        )
        return redirect(url_for("organization_admin.initiatives"))

    initiative_details = {"description": initiative.description, "organization_id": org_id}

    db.session.delete(initiative)

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

        # Check if initiative is linked to any challenges
        challenge_links = ChallengeInitiativeLink.query.filter_by(initiative_id=initiative_id).all()
        if challenge_links:
            return jsonify(
                {
                    "success": False,
                    "error": f'Cannot delete initiative "{initiative_name}" - it is linked to {len(challenge_links)} challenge(s). Remove links first.',
                }
            )

        initiative_details = {"description": initiative.description, "organization_id": org_id}

        db.session.delete(initiative)

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
        if value_type.kind == "numeric" and form.decimal_places.data is not None:
            value_type.decimal_places = form.decimal_places.data
        if form.unit_label.data is not None:
            value_type.unit_label = form.unit_label.data
        value_type.is_active = form.is_active.data
        value_type.display_order = form.display_order.data

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
        flash(f"Value Type {value_type.name} updated successfully", "success")
        return redirect(url_for("organization_admin.value_types"))

    return render_template(
        "organization_admin/edit_value_type.html", form=form, value_type=value_type, csrf_token=generate_csrf
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

    form = GovernanceBodyEditForm(obj=governance_body)

    if form.validate_on_submit():
        governance_body.name = form.name.data
        governance_body.abbreviation = form.abbreviation.data
        governance_body.description = form.description.data
        governance_body.color = form.color.data
        governance_body.is_active = form.is_active.data
        db.session.commit()
        flash(f"Governance Body {governance_body.name} updated successfully", "success")
        return redirect(url_for("organization_admin.governance_bodies"))

    return render_template(
        "organization_admin/edit_governance_body.html",
        form=form,
        governance_body=governance_body,
        csrf_token=generate_csrf,
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

    # 13. Delete RollupRules (depends on ValueTypes)
    from app.models import RollupRule

    rollup_rules = RollupRule.query.join(ValueType).filter(ValueType.organization_id == org_id).all()
    for rule in rollup_rules:
        db.session.delete(rule)

    # 14. Delete ValueTypes (NOW safe to delete)
    value_types = ValueType.query.filter_by(organization_id=org_id).all()
    for vt in value_types:
        db.session.delete(vt)

    # 15. Delete Governance Bodies (NOW safe to delete)
    gov_bodies = GovernanceBody.query.filter_by(organization_id=org_id).all()
    for gb in gov_bodies:
        db.session.delete(gb)

    # 16. Delete Audit Logs
    from app.models import AuditLog

    audit_logs = AuditLog.query.filter_by(organization_id=org_id).all()
    for log in audit_logs:
        db.session.delete(log)

    db.session.flush()


@bp.route("/clear-organization-data", methods=["POST"])
@login_required
@organization_required
def clear_organization_data():
    """Clear all data from the current organization (DESTRUCTIVE!)"""
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

    # Verify organization name confirmation
    confirm_name = request.form.get("confirm_org_name", "").strip()
    if confirm_name != org_name:
        flash("Organization name confirmation does not match. Data deletion cancelled.", "danger")
        return redirect(url_for("organization_admin.index"))

    try:
        # Log the action before deletion
        AuditService.log_action(
            action="CLEAR_ALL_DATA",
            entity_type="Organization",
            entity_id=org_id,
            entity_name=org_name,
            description=f"Complete data deletion for organization {org_name}",
        )

        # Delete all organization data
        _delete_all_organization_data(org_id)

        # Commit the transaction
        db.session.commit()

        flash(
            f"All data has been permanently deleted from {org_name}. The organization is now empty.",
            "success",
        )

        return redirect(url_for("workspace.index"))

    except Exception as e:
        db.session.rollback()
        flash(f"Error clearing organization data: {str(e)}", "danger")
        return redirect(url_for("organization_admin.index"))


@bp.route("/initiatives/<int:initiative_id>/form", methods=["GET", "POST"])
@login_required
@organization_required
def initiative_form(initiative_id):
    """View and edit detailed initiative form"""
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

        # Check if we should return to action items page
        if request.args.get("return_to") == "action_items":
            return redirect(url_for("action_items"))

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
                    value_types_data.append(
                        {
                            "name": config.value_type.name,
                            "value": consensus.get("value"),
                            "formatted_value": consensus.get("formatted_value"),
                            "unit_label": config.value_type.unit_label,
                            "color": config.get_value_color(consensus.get("value")),
                            "kind": config.value_type.kind,
                        }
                    )

            system_kpis.append(
                {
                    "id": kpi.id,
                    "name": kpi.name,
                    "status": status["status"],
                    "status_reason": status["reason"],
                    "value_types": value_types_data,
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

    return render_template(
        "organization_admin/initiative_form.html",
        initiative=initiative,
        kpi_data=kpi_data,
        csrf_token=generate_csrf,
        can_edit=can_edit,
        edit_mode=edit_mode,
        entity_defaults=entity_defaults,
        entity_links=entity_links,
    )
