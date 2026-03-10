"""
Super Admin routes - System-wide settings and configuration
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.decorators import super_admin_required
from app.extensions import db
from app.forms import OrganizationSSOConfigForm
from app.models import AuditLog, Organization, SSOConfig, SystemSetting, User, UserOrganizationMembership

bp = Blueprint("super_admin", __name__, url_prefix="/super-admin")


@bp.route("/")
@super_admin_required
def index():
    """Super Admin dashboard"""
    # Get all settings grouped by category
    settings_grouped = SystemSetting.get_all_settings_grouped()

    # Get system stats
    total_users = User.query.count()
    super_admins = User.query.filter_by(is_super_admin=True, is_active=True).count()
    global_admins = User.query.filter_by(is_global_admin=True, is_active=True).count()

    # Check key feature flags
    sso_config = SSOConfig.get_instance()
    sso_enabled = sso_config and sso_config.is_enabled
    maintenance_mode = SystemSetting.is_maintenance_mode()

    return render_template(
        "super_admin/index.html",
        settings_grouped=settings_grouped,
        total_users=total_users,
        super_admins=super_admins,
        global_admins=global_admins,
        sso_enabled=sso_enabled,
        maintenance_mode=maintenance_mode,
    )


@bp.route("/settings")
@super_admin_required
def settings():
    """View and manage all system settings"""
    settings_grouped = SystemSetting.get_all_settings_grouped()
    return render_template("super_admin/settings.html", settings_grouped=settings_grouped)


@bp.route("/settings/<category>")
@super_admin_required
def settings_category(category):
    """View settings for a specific category"""
    settings = SystemSetting.get_settings_by_category(category)
    return render_template("super_admin/settings_category.html", category=category, settings=settings)


@bp.route("/settings/update", methods=["POST"])
@super_admin_required
def update_setting():
    """Update a system setting"""
    setting_key = request.form.get("key")
    setting_value = request.form.get("value")

    if not setting_key:
        flash("Setting key is required", "danger")
        return redirect(url_for("super_admin.settings"))

    try:
        SystemSetting.set_value(setting_key, setting_value, current_user.id)
        db.session.commit()
        flash(f"Setting '{setting_key}' updated successfully", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating setting: {str(e)}", "danger")

    # Redirect back to the referring page or settings page
    return redirect(request.referrer or url_for("super_admin.settings"))


@bp.route("/settings/sso")
@super_admin_required
def sso_settings():
    """SSO configuration page"""
    # Get SSO-related settings
    sso_settings = SystemSetting.query.filter_by(category="authentication").all()

    sso_enabled = SystemSetting.is_sso_enabled()
    sso_provider = SystemSetting.get_string("sso_provider", "oidc")
    sso_auto_provision = SystemSetting.get_bool("sso_auto_provision", True)

    return render_template(
        "super_admin/sso_settings.html",
        sso_settings=sso_settings,
        sso_enabled=sso_enabled,
        sso_provider=sso_provider,
        sso_auto_provision=sso_auto_provision,
    )


@bp.route("/settings/sso/toggle", methods=["POST"])
@super_admin_required
def toggle_sso():
    """Toggle SSO on/off"""
    current_state = SystemSetting.is_sso_enabled()
    new_state = not current_state

    try:
        SystemSetting.set_value("sso_enabled", str(new_state).lower(), current_user.id)
        db.session.commit()

        if new_state:
            flash("SSO has been ENABLED system-wide", "success")
        else:
            flash("SSO has been DISABLED system-wide", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Error toggling SSO: {str(e)}", "danger")

    return redirect(url_for("super_admin.sso_settings"))


@bp.route("/settings/security")
@super_admin_required
def security_settings():
    """Security settings page"""
    security_settings = SystemSetting.get_settings_by_category("security")

    session_timeout = SystemSetting.get_session_timeout()

    return render_template(
        "super_admin/security_settings.html", security_settings=security_settings, session_timeout=session_timeout
    )


@bp.route("/settings/maintenance")
@super_admin_required
def maintenance_settings():
    """Maintenance mode settings"""
    maintenance_mode = SystemSetting.is_maintenance_mode()

    return render_template("super_admin/maintenance_settings.html", maintenance_mode=maintenance_mode)


@bp.route("/settings/maintenance/toggle", methods=["POST"])
@super_admin_required
def toggle_maintenance():
    """Toggle maintenance mode"""
    current_state = SystemSetting.is_maintenance_mode()
    new_state = not current_state

    try:
        SystemSetting.set_value("maintenance_mode", str(new_state).lower(), current_user.id)
        db.session.commit()

        if new_state:
            flash("Maintenance mode ENABLED - System is now read-only", "warning")
        else:
            flash("Maintenance mode DISABLED - System is fully operational", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error toggling maintenance mode: {str(e)}", "danger")

    return redirect(url_for("super_admin.maintenance_settings"))


@bp.route("/users")
@super_admin_required
def users():
    """View all users with admin levels"""
    all_users = User.query.order_by(User.is_super_admin.desc(), User.is_global_admin.desc(), User.login).all()

    return render_template("super_admin/users.html", users=all_users)


@bp.route("/logs")
@super_admin_required
def logs():
    """System audit logs with search and filters"""
    # Get filter parameters
    action_filter = request.args.get("action", "")
    entity_type_filter = request.args.get("entity_type", "")
    user_filter = request.args.get("user", "")
    search_query = request.args.get("search", "")
    limit = request.args.get("limit", 100, type=int)

    # Build query
    query = AuditLog.query

    if action_filter:
        query = query.filter_by(action=action_filter)
    if entity_type_filter:
        query = query.filter_by(entity_type=entity_type_filter)
    if user_filter:
        query = query.filter_by(user_login=user_filter)
    if search_query:
        # Search in entity_name and description
        query = query.filter(
            db.or_(AuditLog.entity_name.ilike(f"%{search_query}%"), AuditLog.description.ilike(f"%{search_query}%"))
        )

    # Get logs ordered by most recent
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

    # Get unique values for filters
    distinct_actions = db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all()
    distinct_entity_types = db.session.query(AuditLog.entity_type).distinct().order_by(AuditLog.entity_type).all()
    distinct_users = (
        db.session.query(AuditLog.user_login)
        .distinct()
        .filter(AuditLog.user_login.isnot(None))
        .order_by(AuditLog.user_login)
        .all()
    )

    actions = [a[0] for a in distinct_actions]
    entity_types = [e[0] for e in distinct_entity_types]
    users = [u[0] for u in distinct_users]

    return render_template(
        "super_admin/logs.html",
        logs=logs,
        actions=actions,
        entity_types=entity_types,
        users=users,
        current_filters={
            "action": action_filter,
            "entity_type": entity_type_filter,
            "user": user_filter,
            "search": search_query,
            "limit": limit,
        },
    )


@bp.route("/health")
@super_admin_required
def health():
    """System health check dashboard"""
    # Basic health checks
    health_status = {
        "database": "connected",
        "users": User.query.count(),
        "settings": SystemSetting.query.count(),
    }

    return render_template("super_admin/health.html", health_status=health_status)


@bp.route("/settings/sso/config", methods=["GET", "POST"])
@super_admin_required
def sso_config():
    """
    Configure instance-wide SSO settings.

    Manages the single SSO configuration for the entire CISK Navigator instance.
    """
    # Get or create SSO config
    config = SSOConfig.get_or_create()

    form = OrganizationSSOConfigForm()

    if form.validate_on_submit():
        # Update fields
        config.provider_type = form.provider_type.data
        config.is_enabled = form.is_enabled.data
        config.client_id = form.client_id.data.strip() if form.client_id.data else None
        config.client_secret = form.client_secret.data.strip() if form.client_secret.data else None
        config.discovery_url = form.discovery_url.data.strip() if form.discovery_url.data else None
        config.authorization_endpoint = (
            form.authorization_endpoint.data.strip() if form.authorization_endpoint.data else None
        )
        config.token_endpoint = form.token_endpoint.data.strip() if form.token_endpoint.data else None
        config.userinfo_endpoint = form.userinfo_endpoint.data.strip() if form.userinfo_endpoint.data else None

        config.auto_provision_users = form.auto_provision_users.data

        # Build default permissions dict
        config.default_permissions = {
            "can_manage_spaces": form.default_can_manage_spaces.data,
            "can_manage_challenges": form.default_can_manage_challenges.data,
            "can_manage_initiatives": form.default_can_manage_initiatives.data,
            "can_manage_systems": form.default_can_manage_systems.data,
            "can_manage_kpis": form.default_can_manage_kpis.data,
            "can_manage_value_types": form.default_can_manage_value_types.data,
            "can_manage_governance_bodies": form.default_can_manage_governance_bodies.data,
            "can_view_comments": form.default_can_view_comments.data,
            "can_add_comments": form.default_can_add_comments.data,
        }

        config.updated_by = current_user.id

        db.session.commit()

        flash("SSO configuration saved successfully", "success")
        return redirect(url_for("super_admin.sso_config"))

    # Pre-populate form with existing config
    if config and request.method == "GET":
        form.provider_type.data = config.provider_type
        form.is_enabled.data = config.is_enabled
        form.client_id.data = config.client_id
        form.client_secret.data = config.client_secret
        form.discovery_url.data = config.discovery_url
        form.authorization_endpoint.data = config.authorization_endpoint
        form.token_endpoint.data = config.token_endpoint
        form.userinfo_endpoint.data = config.userinfo_endpoint

        form.auto_provision_users.data = config.auto_provision_users

        # Load default permissions
        if config.default_permissions:
            form.default_can_manage_spaces.data = config.default_permissions.get("can_manage_spaces", False)
            form.default_can_manage_challenges.data = config.default_permissions.get("can_manage_challenges", False)
            form.default_can_manage_initiatives.data = config.default_permissions.get("can_manage_initiatives", False)
            form.default_can_manage_systems.data = config.default_permissions.get("can_manage_systems", False)
            form.default_can_manage_kpis.data = config.default_permissions.get("can_manage_kpis", False)
            form.default_can_manage_value_types.data = config.default_permissions.get("can_manage_value_types", False)
            form.default_can_manage_governance_bodies.data = config.default_permissions.get(
                "can_manage_governance_bodies", False
            )
            form.default_can_view_comments.data = config.default_permissions.get("can_view_comments", True)
            form.default_can_add_comments.data = config.default_permissions.get("can_add_comments", False)

    return render_template("super_admin/sso_config.html", form=form, config=config)


@bp.route("/users/pending")
@super_admin_required
def pending_users():
    """
    View SSO users who have no organization memberships.

    These are users who logged in via SSO but haven't been assigned
    to any organization yet.
    """
    # Find users with no organization memberships
    all_users = User.query.filter_by(is_active=True).all()
    pending = []

    for user in all_users:
        memberships = UserOrganizationMembership.query.filter_by(user_id=user.id).count()
        if memberships == 0 and not user.is_global_admin:
            pending.append(user)

    # Get all organizations for the assignment form
    organizations = Organization.query.filter_by(is_active=True).order_by(Organization.name).all()

    return render_template("super_admin/pending_users.html", pending_users=pending, organizations=organizations)


@bp.route("/users/<int:user_id>/assign-organization", methods=["POST"])
@super_admin_required
def assign_organization(user_id):
    """
    Assign a user to an organization with permissions.
    """
    user = User.query.get_or_404(user_id)
    org_id = request.form.get("organization_id", type=int)

    if not org_id:
        flash("Please select an organization", "danger")
        return redirect(url_for("super_admin.pending_users"))

    organization = Organization.query.get(org_id)
    if not organization or not organization.is_active:
        flash("Invalid organization", "danger")
        return redirect(url_for("super_admin.pending_users"))

    # Check if membership already exists
    existing = UserOrganizationMembership.query.filter_by(user_id=user_id, organization_id=org_id).first()

    if existing:
        flash(f"{user.display_name or user.login} is already a member of {organization.name}", "warning")
        return redirect(url_for("super_admin.pending_users"))

    # Get permissions from form (checkboxes)
    membership = UserOrganizationMembership(
        user_id=user_id,
        organization_id=org_id,
        can_manage_spaces=request.form.get("can_manage_spaces") == "on",
        can_manage_challenges=request.form.get("can_manage_challenges") == "on",
        can_manage_initiatives=request.form.get("can_manage_initiatives") == "on",
        can_manage_systems=request.form.get("can_manage_systems") == "on",
        can_manage_kpis=request.form.get("can_manage_kpis") == "on",
        can_manage_value_types=request.form.get("can_manage_value_types") == "on",
        can_manage_governance_bodies=request.form.get("can_manage_governance_bodies") == "on",
        can_view_comments=request.form.get("can_view_comments", "on") == "on",
        can_add_comments=request.form.get("can_add_comments") == "on",
    )

    db.session.add(membership)
    db.session.commit()

    flash(f"✅ {user.display_name or user.login} has been added to {organization.name}", "success")
    return redirect(url_for("super_admin.pending_users"))
