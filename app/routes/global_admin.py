"""
Global Administration routes

For managing users and organizations (global admins only).
"""

import os
import sys
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import text

from app.extensions import db
from app.forms import OrganizationCloneForm, OrganizationCreateForm, OrganizationEditForm, UserCreateForm, UserEditForm
from app.models import (
    KPI,
    CellComment,
    Challenge,
    Contribution,
    Initiative,
    InitiativeSystemLink,
    KPISnapshot,
    KPIValueTypeConfig,
    MentionNotification,
    Organization,
    RollupSnapshot,
    Space,
    System,
    User,
    UserOrganizationMembership,
    ValueType,
)
from app.services import DeletionImpactService, OrganizationCloneService

bp = Blueprint("global_admin", __name__, url_prefix="/global-admin")


def global_admin_required(f):
    """Decorator to require global admin access"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_global_admin:
            flash("Access denied: Global Administrator permission required", "danger")
            return redirect(url_for("auth.login"))
        if session.get("organization_id") is not None:
            flash("Please log in to Global Administration", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


@bp.route("/")
@login_required
@global_admin_required
def index():
    """Global administration dashboard"""
    user_count = User.query.count()
    org_count = Organization.query.count()
    return render_template("global_admin/index.html", user_count=user_count, org_count=org_count)


@bp.route("/health-dashboard")
@login_required
@global_admin_required
def health_dashboard():
    """System health and diagnostics dashboard"""
    health_data = {
        "timestamp": datetime.now(),
        "database": {},
        "migrations": {},
        "tables": {},
        "system": {},
        "recent_activity": {},
    }

    # Database connection check
    try:
        db.session.execute(text("SELECT 1"))
        health_data["database"]["status"] = "healthy"
        health_data["database"]["message"] = "Connected"

        # Get database URL (mask password)
        db_url = str(db.engine.url)
        if "@" in db_url:
            # Mask password: postgresql://user:***@host/db
            parts = db_url.split("@")
            user_part = parts[0].split(":")[0]
            health_data["database"]["url"] = f"{user_part}:***@{parts[1]}"
        else:
            health_data["database"]["url"] = db_url

        health_data["database"]["dialect"] = db.engine.dialect.name

    except Exception as e:
        health_data["database"]["status"] = "error"
        health_data["database"]["message"] = str(e)

    # Migration status
    try:
        result = db.session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        if result:
            health_data["migrations"]["current_revision"] = result[0]
            health_data["migrations"]["status"] = "tracked"
        else:
            health_data["migrations"]["status"] = "no_version"
            health_data["migrations"]["message"] = "No migration version found"
    except Exception as e:
        health_data["migrations"]["status"] = "error"
        health_data["migrations"]["message"] = str(e)

    # Table row counts
    try:
        health_data["tables"]["users"] = User.query.count()
        health_data["tables"]["organizations"] = Organization.query.count()
        health_data["tables"]["spaces"] = Space.query.count()
        health_data["tables"]["challenges"] = Challenge.query.count()
        health_data["tables"]["initiatives"] = Initiative.query.count()
        health_data["tables"]["systems"] = System.query.count()
        health_data["tables"]["kpis"] = KPI.query.count()
        health_data["tables"]["contributions"] = Contribution.query.count()
        health_data["tables"]["kpi_snapshots"] = KPISnapshot.query.count()
        health_data["tables"]["rollup_snapshots"] = RollupSnapshot.query.count()
        health_data["tables"]["comments"] = CellComment.query.count()
        health_data["tables"]["status"] = "success"
    except Exception as e:
        health_data["tables"]["status"] = "error"
        health_data["tables"]["message"] = str(e)

    # System information
    health_data["system"]["python_version"] = sys.version.split()[0]
    health_data["system"]["platform"] = sys.platform
    health_data["system"]["environment"] = os.environ.get("FLASK_ENV", "production")

    # Recent activity (last 24 hours)
    try:
        yesterday = datetime.now() - timedelta(days=1)
        health_data["recent_activity"]["contributions_24h"] = Contribution.query.filter(
            Contribution.created_at >= yesterday
        ).count()
        health_data["recent_activity"]["comments_24h"] = CellComment.query.filter(
            CellComment.created_at >= yesterday
        ).count()
        health_data["recent_activity"]["snapshots_24h"] = KPISnapshot.query.filter(
            KPISnapshot.snapshot_date >= yesterday.date()
        ).count()
    except Exception as e:
        health_data["recent_activity"]["error"] = str(e)

    return render_template("global_admin/health_dashboard.html", health=health_data)


# User Management Routes


@bp.route("/users")
@login_required
@global_admin_required
def users():
    """List all users"""
    users = User.query.order_by(User.login).all()
    return render_template("global_admin/users.html", users=users)


@bp.route("/users/create", methods=["GET", "POST"])
@login_required
@global_admin_required
def create_user():
    """Create a new user"""
    form = UserCreateForm()
    organizations = Organization.query.filter_by(is_active=True, is_deleted=False).order_by(Organization.name).all()
    form.organizations.choices = [(org.id, org.name) for org in organizations]

    if form.validate_on_submit():
        user = User(
            login=form.login.data,
            email=form.email.data,
            display_name=form.display_name.data,
            is_active=form.is_active.data,
            is_global_admin=form.is_global_admin.data,
            must_change_password=True,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        # Assign organizations with permissions
        for org_id in form.organizations.data:
            membership = UserOrganizationMembership(
                user_id=user.id,
                organization_id=org_id,
                can_manage_spaces=request.form.get(f"perm_spaces_{org_id}") == "on",
                can_manage_value_types=request.form.get(f"perm_value_types_{org_id}") == "on",
                can_manage_governance_bodies=request.form.get(f"perm_governance_bodies_{org_id}") == "on",
                can_manage_challenges=request.form.get(f"perm_challenges_{org_id}") == "on",
                can_manage_initiatives=request.form.get(f"perm_initiatives_{org_id}") == "on",
                can_manage_systems=request.form.get(f"perm_systems_{org_id}") == "on",
                can_manage_kpis=request.form.get(f"perm_kpis_{org_id}") == "on",
                can_view_comments=request.form.get(f"perm_view_comments_{org_id}") == "on",
                can_add_comments=request.form.get(f"perm_add_comments_{org_id}") == "on",
            )
            db.session.add(membership)

        db.session.commit()
        flash(f"User {user.login} created successfully", "success")
        return redirect(url_for("global_admin.users"))

    return render_template("global_admin/create_user.html", form=form, organizations=organizations)


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@global_admin_required
def edit_user(user_id):
    """Edit an existing user"""
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)

    organizations = Organization.query.filter_by(is_active=True, is_deleted=False).order_by(Organization.name).all()
    form.organizations.choices = [(org.id, org.name) for org in organizations]

    if request.method == "GET":
        form.organizations.data = [m.organization_id for m in user.organization_memberships]
        form.reset_password.data = None  # Explicitly clear password field

    if form.validate_on_submit():
        user.login = form.login.data
        user.email = form.email.data
        user.display_name = form.display_name.data
        user.is_active = form.is_active.data
        user.is_global_admin = form.is_global_admin.data
        user.must_change_password = form.must_change_password.data

        # Only reset password if field has actual content (strip whitespace)
        if form.reset_password.data and form.reset_password.data.strip():
            user.set_password(form.reset_password.data.strip())
            user.must_change_password = True

        # Update organization memberships
        # Remove old memberships
        UserOrganizationMembership.query.filter_by(user_id=user.id).delete()

        # Add new memberships with permissions
        for org_id in form.organizations.data:
            membership = UserOrganizationMembership(
                user_id=user.id,
                organization_id=org_id,
                can_manage_spaces=request.form.get(f"perm_spaces_{org_id}") == "on",
                can_manage_value_types=request.form.get(f"perm_value_types_{org_id}") == "on",
                can_manage_governance_bodies=request.form.get(f"perm_governance_bodies_{org_id}") == "on",
                can_manage_challenges=request.form.get(f"perm_challenges_{org_id}") == "on",
                can_manage_initiatives=request.form.get(f"perm_initiatives_{org_id}") == "on",
                can_manage_systems=request.form.get(f"perm_systems_{org_id}") == "on",
                can_manage_kpis=request.form.get(f"perm_kpis_{org_id}") == "on",
                can_view_comments=request.form.get(f"perm_view_comments_{org_id}") == "on",
                can_add_comments=request.form.get(f"perm_add_comments_{org_id}") == "on",
            )
            db.session.add(membership)

        db.session.commit()
        flash(f"User {user.login} updated successfully", "success")
        return redirect(url_for("global_admin.users"))

    return render_template("global_admin/edit_user.html", form=form, user=user, organizations=organizations)


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@global_admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)

    # Prevent deletion of last active global admin
    if user.is_global_admin and user.is_active:
        active_admins = User.query.filter_by(is_global_admin=True, is_active=True).count()
        if active_admins <= 1:
            flash("Cannot delete the last active global administrator", "danger")
            return redirect(url_for("global_admin.users"))

    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.login} deleted successfully", "success")
    return redirect(url_for("global_admin.users"))


# Organization Management Routes


@bp.route("/organizations")
@login_required
@global_admin_required
def organizations():
    """List all active (non-deleted) organizations"""
    organizations = Organization.query.filter_by(is_deleted=False).order_by(Organization.name).all()
    deleted_count = Organization.query.filter_by(is_deleted=True).count()
    csrf_form = FlaskForm()  # Simple form for CSRF token
    return render_template("global_admin/organizations.html", organizations=organizations, csrf_form=csrf_form, deleted_count=deleted_count)


@bp.route("/organizations/create", methods=["GET", "POST"])
@login_required
@global_admin_required
def create_organization():
    """Create a new organization"""
    form = OrganizationCreateForm()

    if form.validate_on_submit():
        org = Organization(name=form.name.data, description=form.description.data, is_active=form.is_active.data)
        db.session.add(org)
        db.session.commit()
        flash(f"Organization {org.name} created successfully", "success")
        return redirect(url_for("global_admin.organizations"))

    return render_template("global_admin/create_organization.html", form=form)


@bp.route("/organizations/<int:org_id>/edit", methods=["GET", "POST"])
@login_required
@global_admin_required
def edit_organization(org_id):
    """Edit an existing organization"""
    org = Organization.query.get_or_404(org_id)
    form = OrganizationEditForm(obj=org)

    if form.validate_on_submit():
        org.name = form.name.data
        org.description = form.description.data
        org.is_active = form.is_active.data
        db.session.commit()
        flash(f"Organization {org.name} updated successfully", "success")
        return redirect(url_for("global_admin.organizations"))

    return render_template("global_admin/edit_organization.html", form=form, org=org)


@bp.route("/organizations/<int:org_id>/delete-preview")
@login_required
@global_admin_required
def delete_organization_preview(org_id):
    """Show deletion impact preview for an organization"""
    org = Organization.query.get_or_404(org_id)

    # Calculate impact
    from app.models import KPI, Challenge, Contribution, Initiative, Space, System, ValueType

    impact = {
        "organization": org.name,
        "spaces": Space.query.filter_by(organization_id=org_id).count(),
        "challenges": Challenge.query.filter_by(organization_id=org_id).count(),
        "initiatives": Initiative.query.filter_by(organization_id=org_id).count(),
        "systems": System.query.filter_by(organization_id=org_id).count(),
        "value_types": ValueType.query.filter_by(organization_id=org_id).count(),
    }

    return render_template("global_admin/delete_organization_preview.html", org=org, impact=impact)


@bp.route("/organizations/<int:org_id>/archive", methods=["POST"])
@login_required
@global_admin_required
def archive_organization(org_id):
    """Archive an organization (soft delete - can be restored)"""
    org = Organization.query.get_or_404(org_id)
    org_name = org.name

    org.soft_delete(current_user.id)
    db.session.commit()

    flash(f"Organization '{org_name}' archived successfully. It can be restored from Archived Organizations.", "success")
    return redirect(url_for("global_admin.organizations"))


@bp.route("/organizations/archived")
@login_required
@global_admin_required
def archived_organizations():
    """List all archived (soft-deleted) organizations"""
    archived_orgs = Organization.query.filter_by(is_deleted=True).order_by(Organization.deleted_at.desc()).all()
    csrf_form = FlaskForm()
    return render_template("global_admin/archived_organizations.html", organizations=archived_orgs, csrf_form=csrf_form)


@bp.route("/organizations/<int:org_id>/restore", methods=["POST"])
@login_required
@global_admin_required
def restore_organization(org_id):
    """Restore an archived organization"""
    org = Organization.query.get_or_404(org_id)
    if not org.is_deleted:
        flash(f"Organization '{org.name}' is not archived", "warning")
        return redirect(url_for("global_admin.organizations"))

    org_name = org.name
    org.restore()
    db.session.commit()

    flash(f"Organization '{org_name}' restored successfully", "success")
    return redirect(url_for("global_admin.organizations"))


@bp.route("/organizations/<int:org_id>/delete", methods=["POST"])
@login_required
@global_admin_required
def delete_organization(org_id):
    """Permanently delete an organization (cascades to all data) - CANNOT BE UNDONE"""
    org = Organization.query.get_or_404(org_id)
    org_name = org.name

    # Require organization to be archived first (safety measure)
    if not org.is_deleted:
        flash(f"Organization must be archived before permanent deletion. Use 'Archive' instead.", "danger")
        return redirect(url_for("global_admin.organizations"))

    db.session.delete(org)
    db.session.commit()

    flash(f"Organization '{org_name}' and ALL its data permanently deleted", "warning")
    return redirect(url_for("global_admin.archived_organizations"))


@bp.route("/organizations/<int:org_id>/clone", methods=["GET", "POST"])
@login_required
@global_admin_required
def clone_organization(org_id):
    """Clone an organization with all its structure"""
    source_org = Organization.query.get_or_404(org_id)
    form = OrganizationCloneForm()

    if form.validate_on_submit():
        result = OrganizationCloneService.clone_organization(
            source_org_id=org_id, new_org_name=form.new_name.data, new_org_description=form.new_description.data
        )

        if result["success"]:
            stats = result["statistics"]
            flash(
                f"Organization cloned successfully! Created: "
                f"{stats['value_types']} value types, "
                f"{stats['spaces']} spaces, "
                f"{stats['challenges']} challenges, "
                f"{stats['initiatives']} initiatives, "
                f"{stats['systems']} systems, "
                f"{stats['kpis']} KPIs",
                "success",
            )
            return redirect(url_for("global_admin.organizations"))
        else:
            flash(f"Clone failed: {result['error']}", "danger")

    return render_template("global_admin/clone_organization.html", form=form, source_org=source_org)


@bp.route("/backup-restore")
@login_required
@global_admin_required
def backup_restore():
    """Backup and restore management page"""
    # Get all organizations
    orgs = Organization.query.order_by(Organization.name).all()

    # Get entity counts for each org
    org_stats = []
    for org in orgs:
        spaces_count = Space.query.filter_by(organization_id=org.id).count()
        challenges_count = Challenge.query.filter_by(organization_id=org.id).count()
        initiatives_count = Initiative.query.filter_by(organization_id=org.id).count()
        systems_count = System.query.filter_by(organization_id=org.id).count()

        # Count KPIs through hierarchy
        kpis_count = (
            db.session.query(KPI)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(System, InitiativeSystemLink.system_id == System.id)
            .filter(System.organization_id == org.id)
            .count()
        )

        vt_count = db.session.query(ValueType).filter_by(organization_id=org.id).count()

        org_stats.append(
            {
                "org": org,
                "spaces": spaces_count,
                "challenges": challenges_count,
                "initiatives": initiatives_count,
                "systems": systems_count,
                "kpis": kpis_count,
                "value_types": vt_count,
            }
        )

    return render_template("global_admin/backup_restore.html", org_stats=org_stats)


@bp.route("/backup-restore/create/<int:org_id>", methods=["GET"])
@login_required
@global_admin_required
def create_backup(org_id):
    """Create and download backup of organization"""
    import gzip
    from io import BytesIO

    from app.services.yaml_export_service import YAMLExportService

    org = db.session.get(Organization, org_id)
    if not org:
        flash("Organization not found", "danger")
        return redirect(url_for("global_admin.backup_restore"))

    try:
        # Get compression preference from query parameter
        compress = request.args.get("compress", "false") == "true"

        # Export to YAML
        yaml_content = YAMLExportService.export_to_yaml(org_id)

        # Count entities for metadata
        kpis_count = (
            db.session.query(KPI)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(System, InitiativeSystemLink.system_id == System.id)
            .filter(System.organization_id == org_id)
            .count()
        )

        spaces_count = Space.query.filter_by(organization_id=org_id).count()
        challenges_count = Challenge.query.filter_by(organization_id=org_id).count()
        initiatives_count = Initiative.query.filter_by(organization_id=org_id).count()
        systems_count = System.query.filter_by(organization_id=org_id).count()
        vt_count = ValueType.query.filter_by(organization_id=org_id).count()

        # Add metadata header
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = f"""# CISK Navigator Organization Backup
# Organization: {org.name}
# Organization ID: {org.id}
# Backup Date: {timestamp}
# Backup Version: 1.0
#
# Entities: {spaces_count} spaces, {challenges_count} challenges, {initiatives_count} initiatives, {systems_count} systems, {kpis_count} KPIs, {vt_count} value types
#

"""
        full_content = metadata + yaml_content

        # Generate filename
        safe_org_name = org.name.lower().replace(" ", "-").replace("/", "-")
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{safe_org_name}_{timestamp_str}.yaml"

        # Stream file to browser
        if compress:
            filename += ".gz"
            # Compress in memory
            bio = BytesIO()
            with gzip.open(bio, "wt", encoding="utf-8") as f:
                f.write(full_content)
            bio.seek(0)
            return send_file(bio, mimetype="application/gzip", as_attachment=True, download_name=filename)
        else:
            # Send uncompressed
            bio = BytesIO(full_content.encode("utf-8"))
            bio.seek(0)
            return send_file(bio, mimetype="application/x-yaml", as_attachment=True, download_name=filename)

    except Exception as e:
        flash(f"Error creating backup: {str(e)}", "danger")
        return redirect(url_for("global_admin.backup_restore"))


@bp.route("/backup-restore/restore", methods=["POST"])
@login_required
@global_admin_required
def restore_backup():
    """Restore organization from uploaded backup file"""
    import gzip
    import io

    from app.services.yaml_import_service import YAMLImportService

    org_id = request.form.get("org_id", type=int)

    if not org_id:
        flash("Please select a target organization", "danger")
        return redirect(url_for("global_admin.backup_restore"))

    org = db.session.get(Organization, org_id)
    if not org:
        flash("Organization not found", "danger")
        return redirect(url_for("global_admin.backup_restore"))

    # Check if file was uploaded
    if "backup_upload" not in request.files:
        flash("No file uploaded", "danger")
        return redirect(url_for("global_admin.backup_restore"))

    file = request.files["backup_upload"]
    if file.filename == "":
        flash("No file selected", "danger")
        return redirect(url_for("global_admin.backup_restore"))

    try:
        filename = file.filename
        yaml_content = None

        # Read uploaded file (handle compression)
        if filename.endswith(".gz"):
            with gzip.open(io.BytesIO(file.read()), "rt", encoding="utf-8") as f:
                yaml_content = f.read()
        else:
            yaml_content = file.read().decode("utf-8")

        # Import from YAML
        result = YAMLImportService.import_from_string(yaml_content, org_id, dry_run=False)

        # Build success message
        msg = f'Restored to {org.name}: {result["value_types"]} value types, {result["spaces"]} spaces, '
        msg += f'{result["challenges"]} challenges, {result["initiatives"]} initiatives, '
        msg += f'{result["systems"]} systems, {result["kpis"]} KPIs'

        if result["errors"]:
            msg += f' (with {len(result["errors"])} errors)'
            flash(msg, "warning")
            for error in result["errors"][:5]:  # Show first 5 errors
                flash(f"  • {error}", "warning")
        else:
            flash(msg, "success")

    except Exception as e:
        flash(f"Error restoring backup: {str(e)}", "danger")
        import traceback

        traceback.print_exc()

    return redirect(url_for("global_admin.backup_restore"))


@bp.route("/organizations/<int:org_id>/clear-comments", methods=["POST"])
@login_required
@global_admin_required
def clear_organization_comments(org_id):
    """Clear all comments and mentions for an organization"""
    org = Organization.query.get_or_404(org_id)
    org_name = org.name

    try:
        # Get all KPI configs for this organization
        kpi_config_ids = (
            db.session.query(KPIValueTypeConfig.id)
            .join(KPI)
            .join(InitiativeSystemLink)
            .join(Initiative)
            .filter(Initiative.organization_id == org_id)
            .all()
        )

        config_ids = [c[0] for c in kpi_config_ids]

        if not config_ids:
            flash(f"No comments found for organization {org_name}", "info")
            return redirect(url_for("global_admin.organizations"))

        # Get all comment IDs for these configs
        comment_ids = (
            db.session.query(CellComment.id).filter(CellComment.kpi_value_type_config_id.in_(config_ids)).all()
        )

        comment_ids_list = [c[0] for c in comment_ids]

        if not comment_ids_list:
            flash(f"No comments found for organization {org_name}", "info")
            return redirect(url_for("global_admin.organizations"))

        # Delete all mentions for these comments
        mention_count = MentionNotification.query.filter(MentionNotification.comment_id.in_(comment_ids_list)).delete(
            synchronize_session=False
        )

        # Delete all comments for these configs
        comment_count = CellComment.query.filter(CellComment.kpi_value_type_config_id.in_(config_ids)).delete(
            synchronize_session=False
        )

        db.session.commit()

        flash(
            f"Successfully cleared {comment_count} comment(s) and {mention_count} mention(s) from organization {org_name}",
            "success",
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Error clearing comments: {str(e)}", "danger")

    return redirect(url_for("global_admin.organizations"))
