"""
Super Admin routes - System-wide settings and configuration
"""

from datetime import datetime
from pathlib import Path

import yaml
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf
from markupsafe import Markup

from app.decorators import super_admin_required
from app.extensions import db
from app.forms import EmailConfigForm, OrganizationSSOConfigForm
from app.models import (
    AnnouncementTargetOrganization,
    AnnouncementTargetUser,
    AuditLog,
    Organization,
    SSOConfig,
    SystemAnnouncement,
    SystemSetting,
    User,
    UserAnnouncementAcknowledgment,
    UserOrganizationMembership,
)

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
    beta_enabled = SystemSetting.is_beta_enabled()

    return render_template(
        "super_admin/index.html",
        settings_grouped=settings_grouped,
        total_users=total_users,
        super_admins=super_admins,
        global_admins=global_admins,
        sso_enabled=sso_enabled,
        maintenance_mode=maintenance_mode,
        beta_enabled=beta_enabled,
        csrf_token=generate_csrf,
    )


@bp.route("/settings")
@super_admin_required
def settings():
    """View and manage all system settings"""
    settings_grouped = SystemSetting.get_all_settings_grouped()
    return render_template("super_admin/settings.html", settings_grouped=settings_grouped, csrf_token=generate_csrf)


@bp.route("/settings/<category>")
@super_admin_required
def settings_category(category):
    """View settings for a specific category"""
    settings = SystemSetting.get_settings_by_category(category)
    return render_template(
        "super_admin/settings_category.html", category=category, settings=settings, csrf_token=generate_csrf
    )


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
        csrf_token=generate_csrf,
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
        "super_admin/security_settings.html",
        security_settings=security_settings,
        session_timeout=session_timeout,
        csrf_token=generate_csrf,
    )


@bp.route("/settings/maintenance")
@super_admin_required
def maintenance_settings():
    """Maintenance mode settings"""
    maintenance_mode = SystemSetting.is_maintenance_mode()

    return render_template(
        "super_admin/maintenance_settings.html", maintenance_mode=maintenance_mode, csrf_token=generate_csrf
    )


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


@bp.route("/settings/beta/toggle", methods=["POST"])
@super_admin_required
def toggle_beta():
    """Toggle beta testing program"""
    current_state = SystemSetting.is_beta_enabled()
    new_state = not current_state

    try:
        SystemSetting.set_value("beta_enabled", str(new_state).lower(), current_user.id)
        db.session.commit()

        if new_state:
            flash("Beta testing program ENABLED - Beta menu will appear for beta testers", "success")
        else:
            flash("Beta testing program DISABLED - Beta menu hidden from all users", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Error toggling beta: {str(e)}", "danger")

    return redirect(url_for("super_admin.index"))


@bp.route("/settings/email", methods=["GET", "POST"])
@super_admin_required
def email_settings():
    """Configure email/SMTP settings"""
    from app.services.email_service import EmailService

    form = EmailConfigForm()

    if request.method == "GET":
        # Load current settings into form
        config = EmailService.get_smtp_config()
        form.smtp_host.data = config["smtp_host"]
        form.smtp_port.data = config["smtp_port"]
        form.smtp_username.data = config["smtp_username"]
        # Don't populate password field for security
        form.smtp_use_tls.data = config["smtp_use_tls"]
        form.smtp_use_ssl.data = config["smtp_use_ssl"]
        form.smtp_from_email.data = config["from_email"]
        form.smtp_from_name.data = config["from_name"]

        # Load notification settings
        form.enable_mention_notifications.data = SystemSetting.get_bool("email_mention_notifications", default=False)
        form.enable_action_notifications.data = SystemSetting.get_bool("email_action_notifications", default=False)

    if form.validate_on_submit():
        try:
            # Save SMTP settings
            SystemSetting.set_value("smtp_host", form.smtp_host.data, current_user.id)
            SystemSetting.set_value("smtp_port", str(form.smtp_port.data), current_user.id)
            SystemSetting.set_value("smtp_username", form.smtp_username.data, current_user.id)

            # Only update password if provided
            if form.smtp_password.data:
                SystemSetting.set_value("smtp_password", form.smtp_password.data, current_user.id)

            SystemSetting.set_value("smtp_use_tls", str(form.smtp_use_tls.data).lower(), current_user.id)
            SystemSetting.set_value("smtp_use_ssl", str(form.smtp_use_ssl.data).lower(), current_user.id)
            SystemSetting.set_value("smtp_from_email", form.smtp_from_email.data, current_user.id)
            SystemSetting.set_value("smtp_from_name", form.smtp_from_name.data, current_user.id)

            # Save notification settings
            SystemSetting.set_value(
                "email_mention_notifications", str(form.enable_mention_notifications.data).lower(), current_user.id
            )
            SystemSetting.set_value(
                "email_action_notifications", str(form.enable_action_notifications.data).lower(), current_user.id
            )

            db.session.commit()

            # Send test email if requested
            if form.test_email.data:
                success = EmailService.send_test_email(form.test_email.data)
                if success:
                    flash(f"Email configuration saved and test email sent to {form.test_email.data}!", "success")
                else:
                    flash(
                        "Email configuration saved, but test email failed. Check logs for details.",
                        "warning",
                    )
            else:
                flash("Email configuration saved successfully!", "success")

            return redirect(url_for("super_admin.email_settings"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error saving email configuration: {str(e)}", "danger")

    return render_template("super_admin/email_settings.html", form=form, csrf_token=generate_csrf)


@bp.route("/settings/email/test", methods=["POST"])
@super_admin_required
def test_email():
    """Send a test email"""
    from app.services.email_service import EmailService

    test_address = request.form.get("test_email")

    if not test_address:
        flash("Please provide an email address for testing", "warning")
        return redirect(url_for("super_admin.email_settings"))

    if not EmailService.is_configured():
        flash("Email service is not configured yet", "danger")
        return redirect(url_for("super_admin.email_settings"))

    success = EmailService.send_test_email(test_address)

    if success:
        flash(f"Test email sent successfully to {test_address}!", "success")
    else:
        flash("Failed to send test email. Check logs for details.", "danger")

    return redirect(url_for("super_admin.email_settings"))


@bp.route("/users")
@super_admin_required
def users():
    """View all users with admin levels"""
    # Get filter parameter
    role_filter = request.args.get("role", "")

    # Build query
    query = User.query

    if role_filter == "super_admin":
        query = query.filter_by(is_super_admin=True)
    elif role_filter == "instance_admin":
        query = query.filter_by(is_global_admin=True)
    elif role_filter == "org_admin":
        # Users who have org_admin role in at least one organization
        query = query.join(UserOrganizationMembership).filter(UserOrganizationMembership.is_org_admin.is_(True))
    elif role_filter == "regular":
        # Users who are neither super nor instance admin and don't have org_admin role
        query = (
            query.filter(User.is_super_admin.is_(False), User.is_global_admin.is_(False))
            .outerjoin(
                UserOrganizationMembership,
                (UserOrganizationMembership.user_id == User.id) & (UserOrganizationMembership.is_org_admin.is_(True)),
            )
            .filter(UserOrganizationMembership.id.is_(None))
        )

    all_users = query.order_by(User.is_super_admin.desc(), User.is_global_admin.desc(), User.login).all()

    return render_template(
        "super_admin/users.html", users=all_users, current_role_filter=role_filter, csrf_token=generate_csrf
    )


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
        csrf_token=generate_csrf,
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

    return render_template("super_admin/health.html", health_status=health_status, csrf_token=generate_csrf)


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

    return render_template("super_admin/sso_config.html", form=form, config=config, csrf_token=generate_csrf)


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

    return render_template(
        "super_admin/pending_users.html", pending_users=pending, organizations=organizations, csrf_token=generate_csrf
    )


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


@bp.route("/linked-kpis")
@super_admin_required
def linked_kpis():
    """
    View all linked KPIs across the platform.

    Shows which KPIs are reading values from other KPIs (same org or cross-org).
    Useful for understanding data dependencies and transparency.
    """
    from app.models import KPIValueTypeConfig

    # Get all linked configs
    linked_configs = (
        KPIValueTypeConfig.query.filter(KPIValueTypeConfig.linked_source_kpi_id.isnot(None))
        .order_by(KPIValueTypeConfig.id.desc())
        .all()
    )

    # Build detailed list with full context
    linked_data = []
    for config in linked_configs:
        # Consumer KPI info
        consumer_kpi = config.kpi
        consumer_is_link = consumer_kpi.initiative_system_link
        consumer_initiative = consumer_is_link.initiative
        consumer_org = consumer_initiative.organization
        consumer_system = consumer_is_link.system
        consumer_challenges = [ci_link.challenge.name for ci_link in consumer_initiative.challenge_links]
        consumer_spaces = list(set([ci_link.challenge.space.name for ci_link in consumer_initiative.challenge_links]))

        # Source KPI info
        source_kpi = config.linked_source_kpi
        source_is_link = source_kpi.initiative_system_link
        source_initiative = source_is_link.initiative
        source_org = source_initiative.organization
        source_system = source_is_link.system
        source_challenges = [ci_link.challenge.name for ci_link in source_initiative.challenge_links]
        source_spaces = list(set([ci_link.challenge.space.name for ci_link in source_initiative.challenge_links]))

        # Value type info
        value_type = config.value_type

        linked_data.append(
            {
                "config_id": config.id,
                "consumer": {
                    "org_name": consumer_org.name,
                    "org_id": consumer_org.id,
                    "spaces": ", ".join(consumer_spaces),
                    "challenges": ", ".join(consumer_challenges),
                    "initiative": consumer_initiative.name,
                    "system": consumer_system.name,
                    "kpi": consumer_kpi.name,
                    "kpi_id": consumer_kpi.id,
                },
                "source": {
                    "org_name": source_org.name,
                    "org_id": source_org.id,
                    "spaces": ", ".join(source_spaces),
                    "challenges": ", ".join(source_challenges),
                    "initiative": source_initiative.name,
                    "system": source_system.name,
                    "kpi": source_kpi.name,
                    "kpi_id": source_kpi.id,
                },
                "value_type": {
                    "name": value_type.name,
                    "kind": value_type.kind,
                    "unit_label": value_type.unit_label,
                },
                "is_cross_org": consumer_org.id != source_org.id,
            }
        )

    # Get summary stats
    total_linked = len(linked_data)
    cross_org_count = sum(1 for link in linked_data if link["is_cross_org"])
    same_org_count = total_linked - cross_org_count

    # Count unique organizations involved
    consumer_org_ids = set(link["consumer"]["org_id"] for link in linked_data)
    source_org_ids = set(link["source"]["org_id"] for link in linked_data)
    unique_orgs = len(consumer_org_ids | source_org_ids)

    stats = {
        "total_linked": total_linked,
        "cross_org": cross_org_count,
        "same_org": same_org_count,
        "unique_orgs": unique_orgs,
    }

    return render_template(
        "super_admin/linked_kpis.html", linked_data=linked_data, stats=stats, csrf_token=generate_csrf
    )


@bp.route("/backup")
@super_admin_required
def backup():
    """Backup and restore page"""
    organizations = Organization.query.order_by(Organization.name).all()
    return render_template("super_admin/backup.html", organizations=organizations, csrf_token=generate_csrf)


@bp.route("/backup/create/<path:org_id>")
@super_admin_required
def create_backup(org_id):
    """Create full backup for one or more organizations"""
    import io
    import json
    import zipfile

    from flask import make_response, send_file

    from app.services.full_backup_service import FullBackupService

    # Handle comma-separated org IDs
    org_ids = [int(id.strip()) for id in org_id.split(",")]

    if len(org_ids) == 1:
        # Single org - return JSON file
        org = Organization.query.get_or_404(org_ids[0])
        backup_data = FullBackupService.create_full_backup(org_ids[0])

        if not backup_data:
            flash("Failed to create backup", "danger")
            return redirect(url_for("super_admin.backup"))

        response = make_response(json.dumps(backup_data, indent=2))
        response.headers["Content-Type"] = "application/json"
        response.headers["Content-Disposition"] = (
            f"attachment; filename=backup_{org.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        return response

    else:
        # Multiple orgs - create ZIP file
        memory_file = io.BytesIO()

        with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for org_id_single in org_ids:
                org = Organization.query.get(org_id_single)
                if not org:
                    continue

                backup_data = FullBackupService.create_full_backup(org_id_single)
                if backup_data:
                    filename = f"backup_{org.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    zf.writestr(filename, json.dumps(backup_data, indent=2))

        memory_file.seek(0)

        flash(f"Backup created for {len(org_ids)} organization(s)", "success")

        return send_file(
            memory_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"backups_all_orgs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        )


@bp.route("/backup/restore", methods=["POST"])
@super_admin_required
def restore_backup():
    """Step 1: Upload backup file and show user mapping screen"""
    import base64
    import json

    if "backup_file" not in request.files:
        flash("No backup file provided", "danger")
        return redirect(url_for("super_admin.backup"))

    file = request.files["backup_file"]

    if file.filename == "":
        flash("No file selected", "danger")
        return redirect(url_for("super_admin.backup"))

    if not file.filename.endswith(".json"):
        flash("Backup file must be a JSON file", "danger")
        return redirect(url_for("super_admin.backup"))

    try:
        # Get target organization ID from form
        target_org_id = request.form.get("target_org_id", type=int)

        if not target_org_id:
            flash("Please select a target organization", "danger")
            return redirect(url_for("super_admin.backup"))

        # Read JSON content
        json_content = file.read().decode("utf-8")
        backup_data = json.loads(json_content)

        # Extract users from backup
        backup_users = backup_data.get("users", [])

        if not backup_users:
            flash("⚠️ No users found in backup. Proceeding without user mapping.", "warning")
            # Restore without user mapping
            from app.services.full_restore_service import FullRestoreService

            result = FullRestoreService.restore_from_json(json_content, target_org_id)

            if result.get("success"):
                stats = result.get("stats", {})
                flash(
                    f"✅ Backup restored: {stats.get('spaces', 0)} spaces, {stats.get('kpis', 0)} KPIs",
                    "success",
                )
            else:
                flash(f"❌ Restore failed: {result.get('error', 'Unknown error')}", "danger")

            return redirect(url_for("super_admin.backup"))

        # Get existing users in target organization
        target_org = Organization.query.get(target_org_id)
        existing_users = (
            User.query.join(UserOrganizationMembership)
            .filter(UserOrganizationMembership.organization_id == target_org_id)
            .all()
        )

        # Encode backup data for next step (base64 to pass through form)
        backup_base64 = base64.b64encode(json_content.encode("utf-8")).decode("utf-8")

        # Show mapping screen
        return render_template(
            "super_admin/restore_user_mapping.html",
            backup_users=backup_users,
            existing_users=existing_users,
            target_org=target_org,
            backup_base64=backup_base64,
            csrf_token=generate_csrf,
        )

    except json.JSONDecodeError:
        flash("Invalid JSON file", "danger")
        return redirect(url_for("super_admin.backup"))
    except Exception as e:
        flash(f"Error reading backup: {str(e)}", "danger")
        return redirect(url_for("super_admin.backup"))


@bp.route("/backup/restore_execute", methods=["POST"])
@super_admin_required
def restore_backup_execute():
    """Step 2: Execute restore with user mappings"""
    import base64
    import json

    from app.services.full_restore_service import FullRestoreService

    try:
        # Get backup data from hidden field
        backup_base64 = request.form.get("backup_data")
        target_org_id = request.form.get("target_org_id", type=int)

        if not backup_base64 or not target_org_id:
            flash("Missing restore data", "danger")
            return redirect(url_for("super_admin.backup"))

        # Decode backup
        json_content = base64.b64decode(backup_base64).decode("utf-8")
        backup_data = json.loads(json_content)

        # Build user mapping from form
        user_mapping = {}
        backup_users = backup_data.get("users", [])

        for idx, backup_user in enumerate(backup_users):
            backup_login = backup_user["login"]
            action = request.form.get(f"user_action_{idx}")

            if action == "map":
                # Map to existing user
                mapped_user_id = request.form.get(f"map_to_user_{idx}", type=int)
                if mapped_user_id:
                    user_mapping[backup_login] = {"action": "map", "user_id": mapped_user_id}
            elif action == "create":
                # Create new user
                user_mapping[backup_login] = {
                    "action": "create",
                    "login": backup_login,
                    "email": backup_user["email"],
                    "display_name": backup_user["display_name"],
                    "permissions": backup_user["permissions"],
                }
            # If action == "skip", don't include in mapping

        # Restore with user mapping
        result = FullRestoreService.restore_from_json(json_content, target_org_id, user_mapping=user_mapping)

        if result.get("success"):
            stats = result.get("stats", {})
            flash(
                f"✅ Restore complete: {stats.get('spaces', 0)} spaces, {stats.get('kpis', 0)} KPIs, {stats.get('users_created', 0)} users created",
                "success",
            )
        else:
            flash(f"❌ Restore failed: {result.get('error', 'Unknown error')}", "danger")

    except Exception as e:
        flash(f"Restore error: {str(e)}", "danger")

    return redirect(url_for("super_admin.backup"))


@bp.route("/backup/restore_full_instance", methods=["POST"])
@super_admin_required
def restore_full_instance():
    """Step 1: Upload ZIP and show user mapping screen for full instance restore"""
    import base64
    import io
    import json
    import zipfile

    if "backup_file" not in request.files:
        flash("No backup file provided", "danger")
        return redirect(url_for("super_admin.backup"))

    file = request.files["backup_file"]

    if file.filename == "":
        flash("No file selected", "danger")
        return redirect(url_for("super_admin.backup"))

    if not file.filename.endswith(".zip"):
        flash("Full instance backup must be a ZIP file", "danger")
        return redirect(url_for("super_admin.backup"))

    try:
        # Read ZIP file into memory
        zip_bytes = file.read()
        zip_data = io.BytesIO(zip_bytes)

        # Extract all users from all backup files
        all_users = {}  # login -> user_data (deduplicated)
        org_count = 0

        with zipfile.ZipFile(zip_data, "r") as zf:
            # Get all JSON files from ZIP
            json_files = [f for f in zf.namelist() if f.endswith(".json")]

            if not json_files:
                flash("No JSON backup files found in ZIP", "danger")
                return redirect(url_for("super_admin.backup"))

            org_count = len(json_files)

            # Collect all unique users from all organizations
            for json_file in json_files:
                json_content = zf.read(json_file).decode("utf-8")
                backup_data = json.loads(json_content)

                for user in backup_data.get("users", []):
                    login = user["login"]
                    # Keep first occurrence (in case same user in multiple orgs)
                    if login not in all_users:
                        all_users[login] = user

        # Convert to list
        backup_users = list(all_users.values())

        if not backup_users:
            from app.services.full_restore_service import FullRestoreService

            flash(
                f"⚠️ No users found in {org_count} organization(s). Proceeding without user mapping.",
                "warning",
            )
            # Proceed without mapping - perform restore directly
            zip_data_reset = io.BytesIO(zip_bytes)

            # Perform restore with no user mapping
            with zipfile.ZipFile(zip_data_reset, "r") as zf:
                json_files = [f for f in zf.namelist() if f.endswith(".json")]

                # Delete ALL existing organizations
                existing_orgs = Organization.query.all()
                for org in existing_orgs:
                    db.session.delete(org)
                db.session.commit()
                flash(f"⚠️ Deleted {len(existing_orgs)} existing organization(s)", "warning")

                # Restore each organization from backup
                restored_count = 0
                failed_count = 0

                for json_file in json_files:
                    try:
                        json_content = zf.read(json_file).decode("utf-8")
                        backup_data = json.loads(json_content)

                        # Get organization name
                        org_name = None
                        if "organization" in backup_data and backup_data["organization"].get("name"):
                            org_name = backup_data["organization"]["name"]
                        elif "metadata" in backup_data and backup_data["metadata"].get("organization_name"):
                            org_name = backup_data["metadata"]["organization_name"]
                        else:
                            org_name = f"Restored_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                        # Handle duplicate names
                        original_name = org_name
                        suffix = 1
                        while Organization.query.filter_by(name=org_name).first():
                            org_name = f"{original_name} ({suffix})"
                            suffix += 1

                        # Create new organization
                        new_org = Organization(
                            name=org_name,
                            description=backup_data.get("organization", {}).get("description"),
                            is_active=True,
                        )
                        db.session.add(new_org)
                        db.session.flush()

                        # Restore data without user mapping
                        result = FullRestoreService.restore_from_json(json_content, new_org.id, user_mapping=None)

                        if result.get("success"):
                            restored_count += 1
                            db.session.commit()
                        else:
                            failed_count += 1
                            db.session.rollback()
                            flash(f"Failed to restore {org_name}: {result.get('error', 'Unknown error')}", "warning")

                    except Exception as e:
                        failed_count += 1
                        db.session.rollback()
                        flash(f"Error restoring {json_file}: {str(e)}", "warning")

                if restored_count > 0:
                    flash(f"✅ Restore complete: {restored_count} organization(s) restored", "success")
                else:
                    flash("❌ Restore failed: No organizations were restored", "danger")

            return redirect(url_for("super_admin.backup"))

        # Get all existing users across all organizations
        all_existing_users = User.query.all()

        # Encode ZIP data for next step (base64)
        zip_base64 = base64.b64encode(zip_bytes).decode("utf-8")

        # Show mapping screen
        return render_template(
            "super_admin/restore_full_instance_mapping.html",
            backup_users=backup_users,
            existing_users=all_existing_users,
            org_count=org_count,
            zip_base64=zip_base64,
            csrf_token=generate_csrf,
        )

    except zipfile.BadZipFile:
        flash("Invalid ZIP file", "danger")
        return redirect(url_for("super_admin.backup"))
    except Exception as e:
        flash(f"Error analyzing backup: {str(e)}", "danger")
        return redirect(url_for("super_admin.backup"))


@bp.route("/backup/restore_full_instance_execute", methods=["POST"])
@super_admin_required
def restore_full_instance_execute():
    """Step 2: Execute full instance restore with user mappings"""
    import base64
    import io
    import json
    import zipfile

    from app.services.full_restore_service import FullRestoreService

    try:
        # Get ZIP data from hidden field
        zip_base64 = request.form.get("zip_data")

        if not zip_base64:
            flash("Missing restore data", "danger")
            return redirect(url_for("super_admin.backup"))

        # Decode ZIP
        zip_bytes = base64.b64decode(zip_base64)
        zip_data = io.BytesIO(zip_bytes)

        # Build user mapping from form
        user_mapping = {}

        # Get all backup users from first pass through ZIP
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            json_files = [f for f in zf.namelist() if f.endswith(".json")]
            all_users = {}
            for json_file in json_files:
                json_content = zf.read(json_file).decode("utf-8")
                backup_data = json.loads(json_content)
                for user in backup_data.get("users", []):
                    login = user["login"]
                    if login not in all_users:
                        all_users[login] = user

        backup_users = list(all_users.values())

        for idx, backup_user in enumerate(backup_users):
            backup_login = backup_user["login"]
            action = request.form.get(f"user_action_{idx}")

            if action == "map":
                # Map to existing user
                mapped_user_id = request.form.get(f"map_to_user_{idx}", type=int)
                if mapped_user_id:
                    user_mapping[backup_login] = {"action": "map", "user_id": mapped_user_id}
            elif action == "create":
                # Create new user
                user_mapping[backup_login] = {
                    "action": "create",
                    "login": backup_login,
                    "email": backup_user["email"],
                    "display_name": backup_user["display_name"],
                    "permissions": backup_user["permissions"],
                }
            # If action == "skip", don't include in mapping

        # Now perform the actual restore
        with zipfile.ZipFile(zip_data, "r") as zf:
            json_files = [f for f in zf.namelist() if f.endswith(".json")]

            # Delete ALL existing organizations
            existing_orgs = Organization.query.all()
            for org in existing_orgs:
                db.session.delete(org)
            db.session.commit()
            flash(f"⚠️ Deleted {len(existing_orgs)} existing organization(s)", "warning")

            # Restore each organization from backup
            restored_count = 0
            failed_count = 0

            for json_file in json_files:
                try:
                    # Read JSON content
                    json_content = zf.read(json_file).decode("utf-8")
                    backup_data = json.loads(json_content)

                    # Get organization name from backup (try multiple sources)
                    org_name = None
                    if "organization" in backup_data and backup_data["organization"].get("name"):
                        org_name = backup_data["organization"]["name"]
                    elif "metadata" in backup_data and backup_data["metadata"].get("organization_name"):
                        org_name = backup_data["metadata"]["organization_name"]
                    else:
                        # Fallback: extract from filename
                        import re

                        match = re.search(r"backup_(.+?)_\d{8}_\d{6}\.json", json_file)
                        if match:
                            org_name = match.group(1)
                        else:
                            org_name = f"Restored_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                    # Handle duplicate names by appending suffix
                    original_name = org_name
                    suffix = 1
                    while Organization.query.filter_by(name=org_name).first():
                        org_name = f"{original_name} ({suffix})"
                        suffix += 1

                    # Create new organization
                    new_org = Organization(
                        name=org_name,
                        description=backup_data.get("organization", {}).get("description"),
                        is_active=True,
                    )
                    db.session.add(new_org)
                    db.session.flush()  # Get the ID

                    # Restore data into this organization WITH user mapping
                    result = FullRestoreService.restore_from_json(json_content, new_org.id, user_mapping=user_mapping)

                    if result.get("success"):
                        restored_count += 1
                        db.session.commit()
                    else:
                        failed_count += 1
                        db.session.rollback()
                        flash(
                            f"Failed to restore {org_name}: {result.get('error', 'Unknown error')}",
                            "warning",
                        )

                except Exception as e:
                    failed_count += 1
                    db.session.rollback()
                    flash(f"Error restoring {json_file}: {str(e)}", "warning")

            if restored_count > 0:
                stats_msg = f"✅ Full instance restore complete: {restored_count} organization(s) restored"
                if failed_count > 0:
                    stats_msg += f", {failed_count} failed"
                flash(stats_msg, "success")
            else:
                flash("❌ Full instance restore failed: No organizations were restored", "danger")

    except zipfile.BadZipFile:
        flash("Invalid ZIP file", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Full instance restore error: {str(e)}", "danger")

    return redirect(url_for("super_admin.backup"))


# ==================== SYSTEM ANNOUNCEMENTS ====================


@bp.route("/announcements")
@login_required
@super_admin_required
def list_announcements():
    """List all system announcements with stats"""
    announcements = SystemAnnouncement.query.order_by(SystemAnnouncement.created_at.desc()).all()

    # Add stats to each announcement
    announcement_stats = []
    for ann in announcements:
        stats = {
            "announcement": ann,
            "acknowledgment_count": ann.get_acknowledgment_count(),
            "is_visible": ann.is_visible_now(),
            "target_count": 0,
        }

        # Calculate target count
        if ann.target_type == "all":
            stats["target_count"] = User.query.filter_by(is_active=True).count()
        elif ann.target_type == "organizations":
            # Count users across all target organizations
            total_users = 0
            for target_org in ann.target_organizations:
                total_users += UserOrganizationMembership.query.filter_by(
                    organization_id=target_org.organization_id
                ).count()
            stats["target_count"] = total_users
        elif ann.target_type == "users":
            stats["target_count"] = len(ann.target_users)

        announcement_stats.append(stats)

    return render_template(
        "super_admin/announcements/list.html", announcement_stats=announcement_stats, csrf_token=generate_csrf
    )


@bp.route("/announcements/create", methods=["GET", "POST"])
@login_required
@super_admin_required
def create_announcement():
    """Create a new system announcement"""
    from app.forms.announcement_forms import AnnouncementCreateForm

    form = AnnouncementCreateForm()

    # Populate organization choices
    organizations = Organization.query.filter_by(is_active=True).order_by(Organization.name).all()
    form.target_organization_ids.choices = [(org.id, org.name) for org in organizations]

    # Populate user choices
    users = User.query.filter_by(is_active=True).order_by(User.login).all()
    form.target_user_ids.choices = [(user.id, f"{user.login} ({user.email})") for user in users]

    if form.validate_on_submit():
        announcement = SystemAnnouncement(
            title=form.title.data,
            message=form.message.data,
            banner_type=form.banner_type.data,
            is_dismissible=form.is_dismissible.data,
            target_type=form.target_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            is_active=form.is_active.data,
            created_by=current_user.id,
        )

        db.session.add(announcement)
        db.session.flush()  # Get ID for target users/organizations

        # Add specific target organizations if needed
        if form.target_type.data == "organizations" and form.target_organization_ids.data:
            for org_id in form.target_organization_ids.data:
                target = AnnouncementTargetOrganization(announcement_id=announcement.id, organization_id=org_id)
                db.session.add(target)

        # Add specific target users if needed
        if form.target_type.data == "users" and form.target_user_ids.data:
            for user_id in form.target_user_ids.data:
                target = AnnouncementTargetUser(announcement_id=announcement.id, user_id=user_id)
                db.session.add(target)

        db.session.commit()
        flash(f"Announcement '{announcement.title}' created successfully", "success")
        return redirect(url_for("super_admin.list_announcements"))

    return render_template("super_admin/announcements/create.html", form=form, csrf_token=generate_csrf)


@bp.route("/announcements/<int:announcement_id>/edit", methods=["GET", "POST"])
@login_required
@super_admin_required
def edit_announcement(announcement_id):
    """Edit an existing system announcement"""
    from app.forms.announcement_forms import AnnouncementEditForm

    announcement = SystemAnnouncement.query.get_or_404(announcement_id)
    form = AnnouncementEditForm(obj=announcement)

    # Populate organization choices
    organizations = Organization.query.filter_by(is_active=True).order_by(Organization.name).all()
    form.target_organization_ids.choices = [(org.id, org.name) for org in organizations]

    # Populate user choices
    users = User.query.filter_by(is_active=True).order_by(User.login).all()
    form.target_user_ids.choices = [(user.id, f"{user.login} ({user.email})") for user in users]

    # Pre-select current target users and organizations
    if request.method == "GET":
        form.target_user_ids.data = [target.user_id for target in announcement.target_users]
        form.target_organization_ids.data = [target.organization_id for target in announcement.target_organizations]

    if form.validate_on_submit():
        announcement.title = form.title.data
        announcement.message = form.message.data
        announcement.banner_type = form.banner_type.data
        announcement.is_dismissible = form.is_dismissible.data
        announcement.target_type = form.target_type.data
        announcement.start_date = form.start_date.data
        announcement.end_date = form.end_date.data
        announcement.is_active = form.is_active.data

        # Update target organizations
        AnnouncementTargetOrganization.query.filter_by(announcement_id=announcement.id).delete()
        if form.target_type.data == "organizations" and form.target_organization_ids.data:
            for org_id in form.target_organization_ids.data:
                target = AnnouncementTargetOrganization(announcement_id=announcement.id, organization_id=org_id)
                db.session.add(target)

        # Update target users
        AnnouncementTargetUser.query.filter_by(announcement_id=announcement.id).delete()
        if form.target_type.data == "users" and form.target_user_ids.data:
            for user_id in form.target_user_ids.data:
                target = AnnouncementTargetUser(announcement_id=announcement.id, user_id=user_id)
                db.session.add(target)

        db.session.commit()
        flash(f"Announcement '{announcement.title}' updated successfully", "success")
        return redirect(url_for("super_admin.list_announcements"))

    return render_template(
        "super_admin/announcements/edit.html", form=form, announcement=announcement, csrf_token=generate_csrf
    )


@bp.route("/announcements/<int:announcement_id>/delete", methods=["POST"])
@login_required
@super_admin_required
def delete_announcement(announcement_id):
    """Delete a system announcement"""
    announcement = SystemAnnouncement.query.get_or_404(announcement_id)
    title = announcement.title

    db.session.delete(announcement)
    db.session.commit()

    flash(f"Announcement '{title}' deleted successfully", "success")
    return redirect(url_for("super_admin.list_announcements"))


@bp.route("/announcements/<int:announcement_id>/stats")
@login_required
@super_admin_required
def announcement_stats(announcement_id):
    """View detailed stats for an announcement"""
    announcement = SystemAnnouncement.query.get_or_404(announcement_id)

    # Get all acknowledgments with user info
    acknowledgments = (
        db.session.query(UserAnnouncementAcknowledgment, User)
        .join(User, UserAnnouncementAcknowledgment.user_id == User.id)
        .filter(UserAnnouncementAcknowledgment.announcement_id == announcement_id)
        .order_by(UserAnnouncementAcknowledgment.acknowledged_at.desc())
        .all()
    )

    # Calculate stats
    stats = {
        "total_acknowledgments": len(acknowledgments),
        "is_visible": announcement.is_visible_now(),
        "target_count": 0,
    }

    # Get users who have NOT acknowledged
    acknowledged_user_ids = [ack.user_id for ack, user in acknowledgments]
    not_acknowledged = []

    if announcement.target_type == "all":
        stats["target_count"] = User.query.filter_by(is_active=True).count()
        # Get all active users who haven't acknowledged
        not_acknowledged = (
            User.query.filter(User.is_active, User.id.notin_(acknowledged_user_ids)).order_by(User.login).all()
        )
    elif announcement.target_type == "organizations":
        # Get all users in target organizations
        target_org_ids = [target_org.organization_id for target_org in announcement.target_organizations]
        target_user_ids = (
            db.session.query(UserOrganizationMembership.user_id)
            .filter(UserOrganizationMembership.organization_id.in_(target_org_ids))
            .distinct()
            .all()
        )
        target_user_ids = [uid[0] for uid in target_user_ids]
        stats["target_count"] = len(target_user_ids)

        # Get users who haven't acknowledged
        not_acknowledged_ids = [uid for uid in target_user_ids if uid not in acknowledged_user_ids]
        not_acknowledged = User.query.filter(User.id.in_(not_acknowledged_ids)).order_by(User.login).all()
    elif announcement.target_type == "users":
        stats["target_count"] = len(announcement.target_users)
        # Get target users who haven't acknowledged
        target_user_ids = [target.user_id for target in announcement.target_users]
        not_acknowledged_ids = [uid for uid in target_user_ids if uid not in acknowledged_user_ids]
        not_acknowledged = User.query.filter(User.id.in_(not_acknowledged_ids)).order_by(User.login).all()

    return render_template(
        "super_admin/announcements/stats.html",
        announcement=announcement,
        acknowledgments=acknowledgments,
        not_acknowledged=not_acknowledged,
        stats=stats,
        csrf_token=generate_csrf,
    )


# Documentation System Routes
@bp.route("/documentation")
@super_admin_required
def documentation():
    """View the complete system documentation"""
    docs_path = Path("docs")

    # Get all documentation files
    user_journeys = sorted(docs_path.glob("user-journeys/*.yaml"))
    concept_mappings = sorted(docs_path.glob("concept-mapping/*.yaml"))
    ui_audit = docs_path / "ui-ux" / "UI_CONSISTENCY_AUDIT.yaml"

    # Parse the complete documentation index
    index_path = docs_path / "COMPLETE_DOCUMENTATION_INDEX.md"
    index_content = None
    if index_path.exists():
        with open(index_path, "r") as f:
            index_content = f.read()

    # Parse YAML files for quick stats
    journey_stats = {}
    for journey_file in user_journeys:
        with open(journey_file, "r") as f:
            data = yaml.safe_load(f)
            role_name = data.get("role", {}).get("name", journey_file.stem)
            journey_count = len(data.get("journeys", []))
            journey_stats[journey_file.stem] = {"name": role_name, "count": journey_count, "file": journey_file.name}

    concept_stats = {
        "critical": len([f for f in concept_mappings if "MASTER" not in f.name]),
        "total": len([f for f in concept_mappings if "MASTER" not in f.name]),
    }

    return render_template(
        "super_admin/documentation/index.html",
        user_journeys=journey_stats,
        concept_count=concept_stats,
        ui_audit_exists=ui_audit.exists(),
        index_content=index_content,
        csrf_token=generate_csrf,
    )


@bp.route("/documentation/journey/<role>")
@super_admin_required
def documentation_journey(role):
    """View a specific user journey"""
    docs_path = Path("docs") / "user-journeys"
    file_path = docs_path / f"{role}.yaml"

    if not file_path.exists():
        flash(f"Journey file not found: {role}", "danger")
        return redirect(url_for("super_admin.documentation"))

    with open(file_path, "r") as f:
        journey_data = yaml.safe_load(f)

    return render_template(
        "super_admin/documentation/journey.html", role=role, journey_data=journey_data, csrf_token=generate_csrf
    )


@bp.route("/documentation/concept/<concept>")
@super_admin_required
def documentation_concept(concept):
    """View a specific concept mapping"""
    docs_path = Path("docs") / "concept-mapping"
    file_path = docs_path / f"{concept}.yaml"

    if not file_path.exists():
        flash(f"Concept file not found: {concept}", "danger")
        return redirect(url_for("super_admin.documentation"))

    with open(file_path, "r") as f:
        concept_data = yaml.safe_load(f)

    return render_template(
        "super_admin/documentation/concept.html", concept=concept, concept_data=concept_data, csrf_token=generate_csrf
    )


@bp.route("/documentation/ui-audit")
@super_admin_required
def documentation_ui_audit():
    """View the UI/UX consistency audit"""
    docs_path = Path("docs") / "ui-ux" / "UI_CONSISTENCY_AUDIT.yaml"

    if not docs_path.exists():
        flash("UI/UX audit file not found", "danger")
        return redirect(url_for("super_admin.documentation"))

    with open(docs_path, "r") as f:
        audit_data = yaml.safe_load(f)

    return render_template("super_admin/documentation/ui_audit.html", audit_data=audit_data, csrf_token=generate_csrf)


@bp.route("/documentation/analysis")
@super_admin_required
def documentation_analysis():
    """View simplification analysis"""
    docs_path = Path("docs") / "SIMPLIFICATION_ANALYSIS.md"

    if not docs_path.exists():
        flash("Simplification analysis file not found", "danger")
        return redirect(url_for("super_admin.documentation"))

    with open(docs_path, "r") as f:
        analysis_content = f.read()

    return render_template(
        "super_admin/documentation/analysis.html", analysis_content=analysis_content, csrf_token=generate_csrf
    )


# ============================================================================
# BULK OPERATIONS - FOR TESTING & CLEANUP
# ============================================================================


@bp.route("/bulk-operations")
@login_required
@super_admin_required
def bulk_operations():
    """Bulk delete page for testing"""
    from flask_wtf.csrf import generate_csrf

    from app.models import Organization, User

    # Get all organizations (including deleted/archived)
    organizations = Organization.query.order_by(Organization.name).all()

    # Get all users (except current user)
    users = User.query.filter(User.id != current_user.id).order_by(User.display_name, User.login).all()

    return render_template(
        "super_admin/bulk_operations.html",
        organizations=organizations,
        users=users,
        csrf_token=generate_csrf,  # Pass function, not result (template calls it)
    )


@bp.route("/bulk-operations/delete-organizations", methods=["POST"])
@login_required
@super_admin_required
def bulk_delete_organizations():
    """Bulk delete selected organizations"""
    from app.models import Organization

    org_ids = request.form.getlist("org_ids")

    if not org_ids:
        flash("No organizations selected", "warning")
        return redirect(url_for("super_admin.bulk_operations"))

    deleted_count = 0
    for org_id in org_ids:
        try:
            org = Organization.query.get(int(org_id))
            if org:
                org_name = org.name
                # CASCADE delete will handle all related data
                db.session.delete(org)
                deleted_count += 1
                print(f"[BULK DELETE] Deleted organization: {org_name} (ID: {org_id})")
        except Exception as e:
            flash(f"Error deleting organization ID {org_id}: {str(e)}", "danger")
            db.session.rollback()
            continue

    try:
        db.session.commit()
        flash(f"Successfully deleted {deleted_count} organization(s) and all their data", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error committing bulk delete: {str(e)}", "danger")

    return redirect(url_for("super_admin.bulk_operations"))


@bp.route("/bulk-operations/delete-users", methods=["POST"])
@login_required
@super_admin_required
def bulk_delete_users():
    """Bulk delete selected users"""
    from app.models import User

    user_ids = request.form.getlist("user_ids")

    if not user_ids:
        flash("No users selected", "warning")
        return redirect(url_for("super_admin.bulk_operations"))

    deleted_count = 0
    for user_id in user_ids:
        try:
            user = User.query.get(int(user_id))
            if user:
                # Protect super admins
                if user.is_super_admin:
                    flash(f"Cannot delete super admin: {user.display_name or user.login}", "warning")
                    continue

                # Protect current user
                if user.id == current_user.id:
                    flash("Cannot delete your own account", "warning")
                    continue

                user_name = user.display_name or user.login
                db.session.delete(user)
                deleted_count += 1
                print(f"[BULK DELETE] Deleted user: {user_name} (ID: {user_id})")
        except Exception as e:
            flash(f"Error deleting user ID {user_id}: {str(e)}", "danger")
            db.session.rollback()
            continue

    try:
        db.session.commit()
        flash(f"Successfully deleted {deleted_count} user(s)", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error committing bulk delete: {str(e)}", "danger")

    return redirect(url_for("super_admin.bulk_operations"))


# ============================================================================
# DEMO DATA GENERATOR
# ============================================================================


@bp.route("/demo-generator")
@login_required
@super_admin_required
def demo_generator():
    """Demo data generator - Create realistic demo organizations"""
    from app.services.demo_data_service import DemoDataService

    scenarios = DemoDataService.SCENARIOS

    return render_template(
        "super_admin/demo_generator.html",
        scenarios=scenarios,
        csrf_token=generate_csrf,
    )


@bp.route("/demo-generator/create", methods=["POST"])
@login_required
@super_admin_required
def demo_generator_create():
    """Create demo organization"""
    from app.services.demo_data_service import DemoDataService

    scenario_key = request.form.get("scenario_key")
    if not scenario_key:
        flash("Please select a scenario", "danger")
        return redirect(url_for("super_admin.demo_generator"))

    # Parse user emails (comma-separated)
    user_emails_str = request.form.get("user_emails", "").strip()
    user_emails = None
    if user_emails_str:
        user_emails = [email.strip() for email in user_emails_str.split(",") if email.strip()]

    # Get configuration
    years_of_history = int(request.form.get("years_of_history", 2))
    snapshot_frequency = request.form.get("snapshot_frequency", "weekly")

    try:
        result = DemoDataService.create_demo_organization(
            scenario_key=scenario_key,
            user_emails=user_emails,
            years_of_history=years_of_history,
            snapshot_frequency=snapshot_frequency,
        )

        flash(
            f"✅ Demo organization '{result['organization'].name}' created successfully!",
            "success",
        )

        # Display login credentials for each user
        credentials_msg = "🔑 LOGIN CREDENTIALS (Password: Demo2026! for all):<br>"
        for user_data in result["user_info"]:
            role_label = user_data["role"].upper()
            status = "(existing)" if user_data["is_existing"] else "(new)"
            credentials_msg += (
                f"&nbsp;&nbsp;• <strong>{role_label}</strong> {status}: "
                f"Username = <code>{user_data['username']}</code> | "
                f"Email = {user_data['email']}<br>"
            )
        credentials_msg += "No forced password change required."
        flash(Markup(credentials_msg), "warning")

        flash(
            f"📊 Created: {len(result['users'])} users, {result['stakeholders']} stakeholders, "
            f"{result['stakeholder_maps']} maps, {result['spaces']} spaces, "
            f"{result['challenges']} challenges, {result['initiatives']} initiatives, "
            f"{result['systems']} systems, {result['kpis']} KPIs, "
            f"{result['snapshots']} snapshots, {result['action_items']} action items",
            "info",
        )

        return redirect(url_for("super_admin.demo_generator"))

    except Exception as e:
        db.session.rollback()
        flash(f"Error creating demo organization: {str(e)}", "danger")
        return redirect(url_for("super_admin.demo_generator"))
