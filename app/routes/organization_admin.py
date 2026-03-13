"""
Organization Administration routes

For managing business content within an organization (spaces, challenges, initiatives, etc.).
"""

from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import SubmitField

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
    GovernanceBody,
    Initiative,
    InitiativeSystemLink,
    KPIGovernanceBodyLink,
    KPIValueTypeConfig,
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

    stats = {
        "spaces": spaces_count,
        "challenges": challenges_count,
        "initiatives": initiatives_count,
        "systems": systems_count,
        "kpis": kpis_count,
        "value_types": value_types_count,
        "governance_bodies": governance_bodies_count,
    }

    # Create empty form for CSRF token
    form = FlaskForm()

    return render_template("organization_admin/index.html", org_name=org_name, stats=stats, form=form)


@bp.route("/onboarding", methods=["GET", "POST"])
@login_required
@organization_required
def onboarding():
    """Organization onboarding wizard"""
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")

    # Get step from query parameter (default to 1)
    step = request.args.get("step", 1, type=int)

    # Check what's already been created
    spaces_count = Space.query.filter_by(organization_id=org_id).count()
    governance_bodies_count = GovernanceBody.query.filter_by(organization_id=org_id).count()
    value_types_count = ValueType.query.filter_by(organization_id=org_id).count()

    # If everything is set up, skip to completion
    if spaces_count > 0 and governance_bodies_count > 0 and value_types_count > 0:
        step = 5

    # Initialize forms based on step
    form = None
    if step == 2:
        form = SpaceCreateForm()
        if form.validate_on_submit():
            space = Space(
                name=form.name.data,
                description=form.description.data,
                organization_id=org_id,
            )
            db.session.add(space)

            AuditService.log_create(
                "Space",
                space.id if space.id else 0,
                space.name,
                {"description": space.description},
            )

            db.session.commit()
            flash(f"Space '{space.name}' created successfully", "success")
            return redirect(url_for("organization_admin.onboarding", step=3))

    elif step == 3:
        form = GovernanceBodyCreateForm()
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

            AuditService.log_create(
                "GovernanceBody",
                gov_body.id if gov_body.id else 0,
                gov_body.name,
                {"abbreviation": gov_body.abbreviation},
            )

            db.session.commit()
            flash(f"Governance body '{gov_body.name}' created successfully", "success")
            return redirect(url_for("organization_admin.onboarding", step=4))

    elif step == 4:
        form = OnboardingConfirmForm()
        if form.validate_on_submit():
            # Create default value types
            default_value_types = [
                {
                    "name": "Cost",
                    "kind": "numeric",
                    "numeric_format": "decimal",
                    "decimal_places": 2,
                    "unit_label": "€",
                },
                {
                    "name": "Revenue",
                    "kind": "numeric",
                    "numeric_format": "decimal",
                    "decimal_places": 2,
                    "unit_label": "€",
                },
                {
                    "name": "User Satisfaction",
                    "kind": "sentiment",
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
            flash(f"Created {len(default_value_types)} default value types", "success")
            return redirect(url_for("organization_admin.onboarding", step=5))

    if form is None:
        form = OnboardingConfirmForm()

    return render_template("organization_admin/onboarding.html", org_name=org_name, step=step, form=form)


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

    return render_template("organization_admin/create_space.html", form=form)


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

    return render_template("organization_admin/edit_space.html", form=form, space=space)


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


@bp.route("/spaces/<int:space_id>/swot")
@login_required
@organization_required
def space_swot(space_id):
    """View SWOT analysis for a space"""
    org_id = session.get("organization_id")
    space = Space.query.filter_by(id=space_id, organization_id=org_id).first_or_404()
    return render_template("organization_admin/space_swot.html", space=space)


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
        return redirect(url_for("organization_admin.space_swot", space_id=space.id))

    return render_template("organization_admin/edit_space_swot.html", space=space)


# Challenge Management


@bp.route("/challenges")
@login_required
@organization_required
def challenges():
    """List all challenges"""
    org_id = session.get("organization_id")
    challenges = Challenge.query.filter_by(organization_id=org_id).order_by(Challenge.display_order).all()
    return render_template("organization_admin/challenges.html", challenges=challenges)


@bp.route("/initiatives")
@login_required
@organization_required
def initiatives():
    """List all initiatives"""
    org_id = session.get("organization_id")
    initiatives = Initiative.query.filter_by(organization_id=org_id).all()
    return render_template("organization_admin/initiatives.html", initiatives=initiatives)


@bp.route("/systems")
@login_required
@organization_required
def systems():
    """List all systems"""
    org_id = session.get("organization_id")
    systems = System.query.filter_by(organization_id=org_id).all()
    return render_template("organization_admin/systems.html", systems=systems)


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
        challenge = Challenge(
            organization_id=org_id,
            space_id=space_id,
            name=form.name.data,
            description=form.description.data,
            display_order=form.display_order.data,
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

    return render_template("organization_admin/create_challenge.html", form=form, space=space)


@bp.route("/challenges/<int:challenge_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_challenges")
def edit_challenge(challenge_id):
    """Edit an existing challenge"""
    org_id = session.get("organization_id")
    challenge = Challenge.query.filter_by(id=challenge_id, organization_id=org_id).first_or_404()

    form = ChallengeEditForm(obj=challenge)

    if form.validate_on_submit():
        # Capture old values for audit
        old_values = {"name": challenge.name, "description": challenge.description}

        challenge.name = form.name.data
        challenge.description = form.description.data
        challenge.display_order = form.display_order.data

        # Audit log
        new_values = {"name": challenge.name, "description": challenge.description}
        AuditService.log_update("Challenge", challenge.id, challenge.name, old_values, new_values)

        db.session.commit()
        flash(f"Challenge {challenge.name} updated successfully", "success")
        return redirect(url_for("workspace.index", auto_edit=1))

    # Get value types for rollup configuration tab
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    return render_template(
        "organization_admin/edit_challenge.html", form=form, challenge=challenge, value_types=value_types
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

        # Link to challenge
        link = ChallengeInitiativeLink(challenge_id=challenge_id, initiative_id=initiative.id, display_order=0)
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

    return render_template("organization_admin/create_initiative.html", form=form, challenge=challenge)


@bp.route("/initiatives/<int:initiative_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
@permission_required("can_manage_initiatives")
def edit_initiative(initiative_id):
    """Edit an existing initiative"""
    org_id = session.get("organization_id")
    initiative = Initiative.query.filter_by(id=initiative_id, organization_id=org_id).first_or_404()

    form = InitiativeEditForm(obj=initiative)

    if form.validate_on_submit():
        # Capture old values for audit
        old_values = {
            "name": initiative.name,
            "description": initiative.description,
            "group_label": initiative.group_label,
        }

        initiative.name = form.name.data
        initiative.description = form.description.data
        initiative.group_label = form.group_label.data if form.group_label.data else None

        # Audit log
        new_values = {
            "name": initiative.name,
            "description": initiative.description,
            "group_label": initiative.group_label,
        }
        AuditService.log_update("Initiative", initiative.id, initiative.name, old_values, new_values)

        db.session.commit()
        flash(f"Initiative {initiative.name} updated successfully", "success")
        return redirect(url_for("workspace.index", auto_edit=1))

    # Get value types for rollup configuration tab
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    return render_template(
        "organization_admin/edit_initiative.html", form=form, initiative=initiative, value_types=value_types
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

        # Link to initiative
        link = InitiativeSystemLink(initiative_id=initiative_id, system_id=system.id, display_order=0)
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

    return render_template("organization_admin/create_system.html", form=form, initiative=initiative)


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
        return redirect(url_for("workspace.index", auto_edit=1))

    # Get value types for rollup configuration tab
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    return render_template("organization_admin/edit_system.html", form=form, system=system, value_types=value_types)


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

    # Get active value types for selection
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    # Get active governance bodies for selection
    governance_bodies = (
        GovernanceBody.query.filter_by(organization_id=org_id, is_active=True)
        .order_by(GovernanceBody.display_order)
        .all()
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
        # Validate governance body selection
        selected_gb_ids = request.form.getlist("governance_body_ids")
        if not selected_gb_ids:
            flash("Please select at least one governance body", "danger")
            # Preserve form data on error - extract submitted data
            submitted_vt_ids = request.form.getlist("value_type_ids")
            return render_template(
                "organization_admin/create_kpi.html",
                form=form,
                link=link,
                initiative=link.initiative,
                system=link.system,
                value_types=value_types,
                governance_bodies=governance_bodies,
                preselect_value_types=submitted_vt_ids,  # Preserve value type selection
                preserve_form_data=True,  # Flag to preserve other form data
            )

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

    return render_template(
        "organization_admin/create_kpi.html",
        form=form,
        link=link,
        initiative=link.initiative,
        system=link.system,
        value_types=value_types,
        governance_bodies=governance_bodies,
        preselect_value_types=preselect_value_types,
        preselect_governance_bodies=preselect_governance_bodies,
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

    form = KPIEditForm(obj=kpi)
    if form.validate_on_submit():
        # Capture old values for audit
        old_values = {
            "name": kpi.name,
            "description": kpi.description,
            "governance_bodies_count": len(kpi.governance_body_links),
        }

        # Validate governance body selection
        selected_gb_ids = request.form.getlist("governance_body_ids")
        if not selected_gb_ids:
            flash("Please select at least one governance body", "danger")
            return render_template(
                "organization_admin/edit_kpi.html",
                form=form,
                kpi=kpi,
                governance_bodies=governance_bodies,
                current_gb_ids=current_gb_ids,
            )
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

        # Audit log
        new_values = {"name": kpi.name, "description": kpi.description, "governance_bodies_count": len(selected_gb_ids)}
        AuditService.log_update("KPI", kpi.id, kpi.name, old_values, new_values)

        db.session.commit()
        flash(f"KPI {kpi.name} updated successfully", "success")
        return redirect(url_for("workspace.index", auto_edit=1))

    return render_template(
        "organization_admin/edit_kpi.html",
        form=form,
        kpi=kpi,
        governance_bodies=governance_bodies,
        current_gb_ids=current_gb_ids,
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
    org_id = session.get("organization_id")
    kpi = KPI.query.get_or_404(kpi_id)

    # Verify ownership
    if kpi.initiative_system_link.initiative.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    if kpi.is_archived:
        flash(f'KPI "{kpi.name}" is already archived', "warning")
    else:
        from datetime import datetime

        kpi.is_archived = True
        kpi.archived_at = datetime.utcnow()
        kpi.archived_by_user_id = current_user.id

        # Audit log
        AuditService.log_archive("KPI", kpi.id, kpi.name)

        db.session.commit()
        flash(f'KPI "{kpi.name}" archived successfully', "success")

    # Preserve edit mode if it was active
    edit_mode = request.args.get("edit_mode") or request.args.get("auto_edit")
    if edit_mode:
        return redirect(url_for("workspace.index", auto_edit=1))

    return redirect(url_for("workspace.index"))


@bp.route("/kpis/<int:kpi_id>/unarchive", methods=["POST"])
@login_required
@organization_required
@permission_required("can_manage_kpis")
def unarchive_kpi(kpi_id):
    """Unarchive a KPI (makes it active again)"""
    org_id = session.get("organization_id")
    kpi = KPI.query.get_or_404(kpi_id)

    # Verify ownership
    if kpi.initiative_system_link.initiative.organization_id != org_id:
        flash("Access denied", "danger")
        return redirect(url_for("workspace.index"))

    if not kpi.is_archived:
        flash(f'KPI "{kpi.name}" is not archived', "warning")
    else:
        kpi.is_archived = False
        kpi.archived_at = None
        kpi.archived_by_user_id = None
        db.session.commit()
        flash(f'KPI "{kpi.name}" unarchived successfully', "success")

    # Preserve edit mode if it was active
    edit_mode = request.args.get("edit_mode") or request.args.get("auto_edit")
    if edit_mode:
        return redirect(url_for("workspace.index", auto_edit=1))

    return redirect(url_for("workspace.index"))


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


# Value Type Management


@bp.route("/value-types")
@login_required
@organization_required
def value_types():
    """List all value types"""
    org_id = session.get("organization_id")
    value_types = ValueType.query.filter_by(organization_id=org_id).order_by(ValueType.display_order).all()
    return render_template("organization_admin/value_types.html", value_types=value_types)


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
        )
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

    return render_template("organization_admin/create_value_type.html", form=form)


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

    return render_template("organization_admin/edit_value_type.html", form=form, value_type=value_type)


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

    return render_template(
        "organization_admin/delete_value_type_check.html",
        value_type=value_type,
        can_delete=can_delete,
        reason=reason,
        usage=usage,
    )


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

        # Initiative level formula
        init_enabled = request.form.get("rollup_enabled_initiative") == "on"
        init_formula = request.form.get("formula_initiative", "default")

        # Challenge level formula
        chal_enabled = request.form.get("rollup_enabled_challenge") == "on"
        chal_formula = request.form.get("formula_challenge", "default")

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
                    else:
                        rule = RollupRule(
                            source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM,
                            source_id=link.id,
                            value_type_id=value_type.id,
                            rollup_enabled=True,
                            formula_override=sys_formula,
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
                    else:
                        rule = RollupRule(
                            source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE,
                            source_id=link.id,
                            value_type_id=value_type.id,
                            rollup_enabled=True,
                            formula_override=init_formula,
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
                    else:
                        rule = RollupRule(
                            source_type=RollupRule.SOURCE_CHALLENGE,
                            source_id=challenge.id,
                            value_type_id=value_type.id,
                            rollup_enabled=True,
                            formula_override=chal_formula,
                        )
                        db.session.add(rule)
                    updated_count += 1

            db.session.commit()
            flash(f"✓ Rollup configuration updated for {value_type.name}", "success")
            flash(f"Applied to {updated_count} rollup rules", "info")

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating rollup configuration: {str(e)}", "danger")

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

    # Create form for CSRF token
    form = FlaskForm()

    return render_template(
        "organization_admin/configure_rollup.html",
        value_type=value_type,
        default_enabled=default_enabled,
        default_formula=default_formula,
        form=form,
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
        "organization_admin/governance_bodies.html", governance_bodies=governance_bodies, delete_form=delete_form
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

    return render_template("organization_admin/create_governance_body.html", form=form)


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

    return render_template("organization_admin/edit_governance_body.html", form=form, governance_body=governance_body)


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

    return render_template("organization_admin/yaml_upload.html", form=form)


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
        }

        # Update fields
        initiative.mission = request.form.get("mission")
        initiative.success_criteria = request.form.get("success_criteria")
        initiative.responsible_person = request.form.get("responsible_person")
        initiative.team_members = request.form.get("team_members")
        initiative.handover_organization = request.form.get("handover_organization")
        initiative.deliverables = request.form.get("deliverables")

        # Audit log
        new_values = {
            "mission": initiative.mission,
            "success_criteria": initiative.success_criteria,
            "responsible_person": initiative.responsible_person,
            "team_members": initiative.team_members,
            "handover_organization": initiative.handover_organization,
            "deliverables": initiative.deliverables,
        }
        AuditService.log_update("Initiative Form", initiative.id, initiative.name, old_values, new_values)

        db.session.commit()
        flash(f"Initiative form for '{initiative.name}' updated successfully", "success")
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

    return render_template(
        "organization_admin/initiative_form.html",
        initiative=initiative,
        kpi_data=kpi_data,
        csrf_token=generate_csrf,
        can_edit=can_edit,
        edit_mode=edit_mode,
    )
