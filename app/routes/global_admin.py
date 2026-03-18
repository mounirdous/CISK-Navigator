"""
Instance Admin routes

For managing users and organizations (instance admins only).
"""

import os
import sys
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.csrf import generate_csrf
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
from app.services import AuditService, OrganizationCloneService

bp = Blueprint("global_admin", __name__, url_prefix="/global-admin")


def global_admin_required(f):
    """Decorator to require global admin access"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_global_admin:
            flash("Access denied: Instance Admin permission required", "danger")
            return redirect(url_for("auth.login"))
        if session.get("organization_id") is not None:
            flash("Please log in to Instance Admin", "warning")
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
            is_super_admin=form.is_super_admin.data if current_user.is_super_admin else False,
            beta_tester=form.beta_tester.data,
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
                is_org_admin=request.form.get(f"perm_is_org_admin_{org_id}") == "on",
                can_manage_spaces=request.form.get(f"perm_spaces_{org_id}") == "on",
                can_manage_value_types=request.form.get(f"perm_value_types_{org_id}") == "on",
                can_manage_governance_bodies=request.form.get(f"perm_governance_bodies_{org_id}") == "on",
                can_manage_challenges=request.form.get(f"perm_challenges_{org_id}") == "on",
                can_manage_initiatives=request.form.get(f"perm_initiatives_{org_id}") == "on",
                can_manage_systems=request.form.get(f"perm_systems_{org_id}") == "on",
                can_manage_kpis=request.form.get(f"perm_kpis_{org_id}") == "on",
                can_view_comments=request.form.get(f"perm_view_comments_{org_id}") == "on",
                can_add_comments=request.form.get(f"perm_add_comments_{org_id}") == "on",
                can_contribute=request.form.get(f"perm_contribute_{org_id}") == "on",
            )
            db.session.add(membership)

        # Audit log
        AuditService.log_create(
            "User",
            user.id,
            user.login,
            {
                "email": user.email,
                "display_name": user.display_name,
                "is_active": user.is_active,
                "is_global_admin": user.is_global_admin,
                "is_super_admin": user.is_super_admin,
                "organizations_assigned": len(form.organizations.data),
            },
        )

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
        # Capture old values for audit
        old_values = {
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "is_global_admin": user.is_global_admin,
            "is_super_admin": user.is_super_admin,
            "organizations_count": len(user.organization_memberships),
        }

        user.login = form.login.data
        user.email = form.email.data
        user.display_name = form.display_name.data
        user.is_active = form.is_active.data
        user.is_global_admin = form.is_global_admin.data

        # Only Super Admins can set Super Admin status
        if current_user.is_super_admin:
            user.is_super_admin = form.is_super_admin.data

        user.must_change_password = form.must_change_password.data
        user.beta_tester = form.beta_tester.data

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
                is_org_admin=request.form.get(f"perm_is_org_admin_{org_id}") == "on",
                can_manage_spaces=request.form.get(f"perm_spaces_{org_id}") == "on",
                can_manage_value_types=request.form.get(f"perm_value_types_{org_id}") == "on",
                can_manage_governance_bodies=request.form.get(f"perm_governance_bodies_{org_id}") == "on",
                can_manage_challenges=request.form.get(f"perm_challenges_{org_id}") == "on",
                can_manage_initiatives=request.form.get(f"perm_initiatives_{org_id}") == "on",
                can_manage_systems=request.form.get(f"perm_systems_{org_id}") == "on",
                can_manage_kpis=request.form.get(f"perm_kpis_{org_id}") == "on",
                can_view_comments=request.form.get(f"perm_view_comments_{org_id}") == "on",
                can_add_comments=request.form.get(f"perm_add_comments_{org_id}") == "on",
                can_contribute=request.form.get(f"perm_contribute_{org_id}") == "on",
            )
            db.session.add(membership)

        # Audit log
        new_values = {
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "is_global_admin": user.is_global_admin,
            "is_super_admin": user.is_super_admin,
            "organizations_count": len(form.organizations.data),
        }
        AuditService.log_update("User", user.id, user.login, old_values, new_values)

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

    # Capture user details before deletion
    user_login = user.login
    user_details = {
        "email": user.email,
        "display_name": user.display_name,
        "is_global_admin": user.is_global_admin,
        "is_super_admin": user.is_super_admin,
        "organizations_count": len(user.organization_memberships),
    }

    db.session.delete(user)

    # Audit log
    AuditService.log_delete("User", user_id, user_login, user_details)

    db.session.commit()
    flash(f"User {user_login} deleted successfully", "success")
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
    return render_template(
        "global_admin/organizations.html", organizations=organizations, csrf_form=csrf_form, deleted_count=deleted_count
    )


@bp.route("/organizations/create", methods=["GET", "POST"])
@login_required
@global_admin_required
def create_organization():
    """Create a new organization"""
    form = OrganizationCreateForm()

    # Populate users choices
    all_users = User.query.filter_by(is_active=True).order_by(User.display_name, User.login).all()
    form.users.choices = [(u.id, u.display_name or u.login) for u in all_users]

    # Preserve permission checkboxes on validation failure
    preserved_permissions = {}
    if request.method == "POST":
        for user in all_users:
            preserved_permissions[user.id] = {
                "is_org_admin": request.form.get(f"perm_is_org_admin_{user.id}") == "on",
                "spaces": request.form.get(f"perm_spaces_{user.id}") == "on",
                "value_types": request.form.get(f"perm_value_types_{user.id}") == "on",
                "governance_bodies": request.form.get(f"perm_governance_bodies_{user.id}") == "on",
                "challenges": request.form.get(f"perm_challenges_{user.id}") == "on",
                "initiatives": request.form.get(f"perm_initiatives_{user.id}") == "on",
                "systems": request.form.get(f"perm_systems_{user.id}") == "on",
                "kpis": request.form.get(f"perm_kpis_{user.id}") == "on",
                "view_comments": request.form.get(f"perm_view_comments_{user.id}") == "on",
                "add_comments": request.form.get(f"perm_add_comments_{user.id}") == "on",
            }

    if form.validate_on_submit():
        # Check if an organization with this name already exists (including deleted ones)
        existing_org = Organization.query.filter_by(name=form.name.data).first()

        if existing_org:
            if existing_org.is_deleted:
                # Archived organization with same name exists
                flash(
                    f"An archived organization named '{form.name.data}' already exists. "
                    f"Please restore it from the Organizations list or choose a different name.",
                    "warning",
                )
                return render_template(
                    "global_admin/create_organization.html",
                    form=form,
                    all_users=all_users,
                    preserved_permissions=preserved_permissions,
                )
            else:
                # Active organization with same name exists
                flash(
                    f"An organization named '{form.name.data}' already exists. Please choose a different name.",
                    "danger",
                )
                return render_template(
                    "global_admin/create_organization.html",
                    form=form,
                    all_users=all_users,
                    preserved_permissions=preserved_permissions,
                )

        org = Organization(name=form.name.data, description=form.description.data, is_active=form.is_active.data)
        db.session.add(org)
        db.session.flush()  # Get org.id before audit log

        # Assign users with permissions
        for user_id in form.users.data:
            membership = UserOrganizationMembership(
                user_id=user_id,
                organization_id=org.id,
                is_org_admin=request.form.get(f"perm_is_org_admin_{user_id}") == "on",
                can_manage_spaces=request.form.get(f"perm_spaces_{user_id}") == "on",
                can_manage_value_types=request.form.get(f"perm_value_types_{user_id}") == "on",
                can_manage_governance_bodies=request.form.get(f"perm_governance_bodies_{user_id}") == "on",
                can_manage_challenges=request.form.get(f"perm_challenges_{user_id}") == "on",
                can_manage_initiatives=request.form.get(f"perm_initiatives_{user_id}") == "on",
                can_manage_systems=request.form.get(f"perm_systems_{user_id}") == "on",
                can_manage_kpis=request.form.get(f"perm_kpis_{user_id}") == "on",
                can_view_comments=request.form.get(f"perm_view_comments_{user_id}") == "on",
                can_add_comments=request.form.get(f"perm_add_comments_{user_id}") == "on",
            )
            db.session.add(membership)

        # Audit log
        AuditService.log_create(
            "Organization",
            org.id,
            org.name,
            {"description": org.description, "is_active": org.is_active, "users_assigned": len(form.users.data)},
        )

        db.session.commit()
        flash(f"Organization {org.name} created successfully with {len(form.users.data)} user(s)", "success")
        return redirect(url_for("global_admin.organizations"))

    return render_template(
        "global_admin/create_organization.html",
        form=form,
        all_users=all_users,
        preserved_permissions=preserved_permissions if request.method == "POST" else {},
    )


@bp.route("/organizations/<int:org_id>/edit", methods=["GET", "POST"])
@login_required
@global_admin_required
def edit_organization(org_id):
    """Edit an existing organization"""
    org = Organization.query.get_or_404(org_id)
    form = OrganizationEditForm(obj=org)

    # Populate users choices
    all_users = User.query.filter_by(is_active=True).order_by(User.display_name, User.login).all()
    form.users.choices = [(u.id, u.display_name or u.login) for u in all_users]

    # Pre-populate with existing users on GET
    if request.method == "GET":
        form.users.data = [m.user_id for m in org.user_memberships]

    if form.validate_on_submit():
        # Capture old values for audit
        old_values = {
            "name": org.name,
            "description": org.description,
            "is_active": org.is_active,
            "users_count": len(org.user_memberships),
        }

        # Apply changes
        org.name = form.name.data
        org.description = form.description.data
        org.is_active = form.is_active.data

        # Update user memberships
        # Remove old memberships
        UserOrganizationMembership.query.filter_by(organization_id=org.id).delete()

        # Add new memberships with permissions
        for user_id in form.users.data:
            membership = UserOrganizationMembership(
                user_id=user_id,
                organization_id=org.id,
                is_org_admin=request.form.get(f"perm_is_org_admin_{user_id}") == "on",
                can_manage_spaces=request.form.get(f"perm_spaces_{user_id}") == "on",
                can_manage_value_types=request.form.get(f"perm_value_types_{user_id}") == "on",
                can_manage_governance_bodies=request.form.get(f"perm_governance_bodies_{user_id}") == "on",
                can_manage_challenges=request.form.get(f"perm_challenges_{user_id}") == "on",
                can_manage_initiatives=request.form.get(f"perm_initiatives_{user_id}") == "on",
                can_manage_systems=request.form.get(f"perm_systems_{user_id}") == "on",
                can_manage_kpis=request.form.get(f"perm_kpis_{user_id}") == "on",
                can_view_comments=request.form.get(f"perm_view_comments_{user_id}") == "on",
                can_add_comments=request.form.get(f"perm_add_comments_{user_id}") == "on",
            )
            db.session.add(membership)

        # Audit log
        new_values = {
            "name": org.name,
            "description": org.description,
            "is_active": org.is_active,
            "users_count": len(form.users.data),
        }
        AuditService.log_update("Organization", org.id, org.name, old_values, new_values)

        db.session.commit()
        flash(f"Organization {org.name} updated successfully", "success")
        return redirect(url_for("global_admin.organizations"))

    return render_template("global_admin/edit_organization.html", form=form, org=org, all_users=all_users)


@bp.route("/organizations/<int:org_id>/delete-preview")
@login_required
@global_admin_required
def delete_organization_preview(org_id):
    """Show deletion impact preview for an organization"""
    org = Organization.query.get_or_404(org_id)

    # Calculate impact
    from app.models import Challenge, Initiative, Space, System, ValueType

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

    # Audit log
    AuditService.log_archive("Organization", org.id, org_name)

    db.session.commit()

    flash(
        f"Organization '{org_name}' archived successfully. It can be restored from Archived Organizations.", "success"
    )
    return redirect(url_for("global_admin.organizations"))


@bp.route("/organizations/archived")
@login_required
@global_admin_required
def archived_organizations():
    """List all archived (soft-deleted) organizations"""
    archived_orgs = Organization.query.filter_by(is_deleted=True).order_by(Organization.deleted_at.desc()).all()
    csrf_form = FlaskForm()
    return render_template(
        "global_admin/archived_organizations.html",
        organizations=archived_orgs,
        csrf_form=csrf_form,
        csrf_token=generate_csrf,
    )


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

    # Audit log
    AuditService.log_restore("Organization", org.id, org_name)

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
    org_description = org.description

    # Require organization to be archived first (safety measure)
    if not org.is_deleted:
        flash("Organization must be archived before permanent deletion. Use 'Archive' instead.", "danger")
        return redirect(url_for("global_admin.organizations"))

    # Audit log before deletion
    AuditService.log_delete(
        "Organization",
        org.id,
        org_name,
        {
            "name": org_name,
            "description": org_description,
            "was_deleted": org.is_deleted,
            "deleted_at": org.deleted_at.isoformat() if org.deleted_at else None,
        },
    )

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
    # Get organizations based on context
    # If in Global Admin mode (no org context), show ALL active organizations
    # If in organization context, show only user's organizations
    if session.get("organization_id") is None:
        # Global Admin mode - show all active (non-archived) organizations
        orgs = Organization.query.filter_by(is_deleted=False).order_by(Organization.name).all()
    else:
        # Organization context - show only user's organizations
        orgs = current_user.get_organizations()
        orgs = sorted([org for org in orgs if org.is_active and not org.is_deleted], key=lambda o: o.name)

    # Get entity counts for each org
    from app.models import GovernanceBody, Stakeholder

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
        gb_count = db.session.query(GovernanceBody).filter_by(organization_id=org.id).count()
        stakeholder_count = db.session.query(Stakeholder).filter_by(organization_id=org.id).count()

        org_stats.append(
            {
                "org": org,
                "spaces": spaces_count,
                "challenges": challenges_count,
                "initiatives": initiatives_count,
                "systems": systems_count,
                "kpis": kpis_count,
                "value_types": vt_count,
                "governance_bodies": gb_count,
                "stakeholders": stakeholder_count,
            }
        )

    return render_template("global_admin/backup_restore.html", org_stats=org_stats)


@bp.route("/backup-restore/create/<int:org_id>", methods=["GET"])
@login_required
@global_admin_required
def create_backup(org_id):
    """Create and download FULL backup of organization with all data"""
    import gzip
    from io import BytesIO

    from app.services.full_backup_service import FullBackupService

    org = db.session.get(Organization, org_id)
    if not org:
        flash("Organization not found", "danger")
        return redirect(url_for("global_admin.backup_restore"))

    try:
        # Get compression preference from query parameter
        compress = request.args.get("compress", "false") == "true"

        # Create FULL backup (structure + all data)
        json_content = FullBackupService.export_to_json_string(org_id)

        # Generate filename
        safe_org_name = org.name.lower().replace(" ", "-").replace("/", "-")
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"full_backup_{safe_org_name}_{timestamp_str}.json"

        # Stream file to browser
        if compress:
            filename += ".gz"
            # Compress in memory
            bio = BytesIO()
            with gzip.open(bio, "wt", encoding="utf-8") as f:
                f.write(json_content)
            bio.seek(0)
            return send_file(bio, mimetype="application/gzip", as_attachment=True, download_name=filename)
        else:
            # Send uncompressed
            bio = BytesIO(json_content.encode("utf-8"))
            bio.seek(0)
            return send_file(bio, mimetype="application/json", as_attachment=True, download_name=filename)

    except Exception as e:
        flash(f"Error creating backup: {str(e)}", "danger")
        return redirect(url_for("global_admin.backup_restore"))


@bp.route("/backup-restore/restore", methods=["POST"])
@login_required
@global_admin_required
def restore_backup():
    """Restore organization from uploaded backup file (JSON format with full data)"""
    import gzip
    import io

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
        backup_content = None

        # Read uploaded file (handle compression)
        if filename.endswith(".gz"):
            with gzip.open(io.BytesIO(file.read()), "rt", encoding="utf-8") as f:
                backup_content = f.read()
        else:
            backup_content = file.read().decode("utf-8")

        # Detect format: JSON (full backup) or YAML (structure only)
        if filename.endswith((".json", ".json.gz")):
            # Full backup - extract governance bodies for mapping
            try:
                import json

                backup_data = json.loads(backup_content)
                governance_bodies = backup_data.get("governance_bodies", [])
            except Exception:
                governance_bodies = []

            if governance_bodies:
                # Store backup to a temp file (too large for session cookie)
                import os
                import tempfile
                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False, encoding="utf-8",
                    dir=tempfile.gettempdir(), prefix="cisk_restore_"
                )
                tmp.write(backup_content)
                tmp.close()

                session["pending_full_backup_path"] = tmp.name
                session["full_backup_org_id"] = org_id
                session["full_backup_governance_bodies"] = [gb["name"] for gb in governance_bodies]
                # Remove old key if present
                session.pop("pending_full_backup", None)

                # Redirect to mapping page
                return redirect(url_for("global_admin.full_backup_governance_mapping"))
            else:
                # No governance bodies, proceed directly
                from app.services.full_restore_service import FullRestoreService

                result = FullRestoreService.restore_from_json(backup_content, org_id)

                if result.get("success"):
                    flash(f"✓ Full restore to {org.name} complete!", "success")

                    stats = result.get("stats", result)  # Handle both old and new format
                    details = f'Restored: {stats.get("value_types", 0)} value types, {stats.get("governance_bodies", 0)} governance bodies, '
                    details += f'{stats.get("spaces", 0)} spaces, {stats.get("challenges", 0)} challenges, '
                    details += f'{stats.get("initiatives", 0)} initiatives, {stats.get("systems", 0)} systems, '
                    details += f'{stats.get("kpis", 0)} KPIs, {stats.get("contributions", 0)} contributions'

                    # Add v2.0 features
                    if stats.get("geography_assignments", 0) > 0:
                        details += f', {stats.get("geography_assignments", 0)} geography assignments'
                    if stats.get("stakeholders", 0) > 0:
                        details += f', {stats.get("stakeholders", 0)} stakeholders'
                    if stats.get("stakeholder_relationships", 0) > 0:
                        details += f', {stats.get("stakeholder_relationships", 0)} relationships'
                    if stats.get("stakeholder_maps", 0) > 0:
                        details += f', {stats.get("stakeholder_maps", 0)} maps'
                    if stats.get("logos_restored", 0) > 0:
                        details += f', {stats.get("logos_restored", 0)} logos'
                    if stats.get("formulas_restored", 0) > 0:
                        details += f', {stats.get("formulas_restored", 0)} formulas'
                    if stats.get("linked_kpis_restored", 0) > 0:
                        details += f', {stats.get("linked_kpis_restored", 0)} linked KPIs'

                    flash(details, "info")

                    if stats.get("warnings"):
                        flash(f'⚠ {len(stats["warnings"])} warnings', "warning")
                        for warning in stats["warnings"][:5]:
                            flash(f"  • {warning}", "warning")
                else:
                    flash("Restore failed", "danger")
                    error_msg = result.get("error", "Unknown error")
                    flash(error_msg, "danger")

        else:
            # YAML - structure only (backward compatibility)
            from app.services.yaml_import_service import YAMLImportService

            result = YAMLImportService.import_from_string(backup_content, org_id, dry_run=False)

            msg = f'Restored structure to {org.name}: {result["value_types"]} value types, {result["spaces"]} spaces, '
            msg += f'{result["challenges"]} challenges, {result["initiatives"]} initiatives, '
            msg += f'{result["systems"]} systems, {result["kpis"]} KPIs (structure only, no data)'

            if result["errors"]:
                msg += f' (with {len(result["errors"])} errors)'
                flash(msg, "warning")
                for error in result["errors"][:5]:
                    flash(f"  • {error}", "warning")
            else:
                flash(msg, "info")

    except Exception as e:
        flash(f"Error restoring backup: {str(e)}", "danger")
        import traceback

        traceback.print_exc()

    return redirect(url_for("global_admin.backup_restore"))


@bp.route("/backup-restore/governance-mapping", methods=["GET", "POST"])
@login_required
@global_admin_required
def full_backup_governance_mapping():
    """Map governance bodies from full backup to existing or create new"""
    from app.services.full_restore_service import FullRestoreService

    # Check if we have pending backup restore
    import os
    backup_path = session.get("pending_full_backup_path")
    org_id = session.get("full_backup_org_id")
    gb_names = session.get("full_backup_governance_bodies", [])

    if not backup_path or not os.path.exists(backup_path) or not org_id or not gb_names:
        flash("No pending backup restore found", "warning")
        return redirect(url_for("global_admin.backup_restore"))

    with open(backup_path, "r", encoding="utf-8") as f:
        backup_content = f.read()

    org = db.session.get(Organization, org_id)
    if not org:
        flash("Organization not found", "danger")
        return redirect(url_for("global_admin.backup_restore"))

    # Get existing governance bodies in target organization
    from app.models import GovernanceBody

    existing_gbs = GovernanceBody.query.filter_by(organization_id=org_id, is_active=True).all()

    if request.method == "POST":
        try:
            # Build governance body mapping from form
            governance_body_mapping = {}

            for gb_name in gb_names:
                action = request.form.get(f"gb_action_{gb_name}")

                if action == "create":
                    governance_body_mapping[gb_name] = "create"
                elif action and action.startswith("map_"):
                    # Extract GB ID from "map_123"
                    gb_id = int(action.split("_")[1])
                    governance_body_mapping[gb_name] = gb_id

            # Clear session data and temp file
            tmp_path = session.pop("pending_full_backup_path", None)
            session.pop("pending_full_backup", None)
            session.pop("full_backup_org_id", None)
            session.pop("full_backup_governance_bodies", None)
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

            # Restore with governance body mapping
            result = FullRestoreService.restore_from_json(
                backup_content, org_id, governance_body_mapping=governance_body_mapping
            )

            if result.get("success"):
                flash(f"✓ Full restore to {org.name} complete!", "success")

                stats = result.get("stats", result)  # Handle both old and new format
                details = f'Restored: {stats.get("value_types", 0)} value types, {stats.get("governance_bodies", 0)} governance bodies, '
                details += f'{stats.get("spaces", 0)} spaces, {stats.get("challenges", 0)} challenges, '
                details += f'{stats.get("initiatives", 0)} initiatives, {stats.get("systems", 0)} systems, '
                details += f'{stats.get("kpis", 0)} KPIs, {stats.get("contributions", 0)} contributions'

                # Add v2.0 features
                if stats.get("geography_assignments", 0) > 0:
                    details += f', {stats.get("geography_assignments", 0)} geography assignments'
                if stats.get("stakeholders", 0) > 0:
                    details += f', {stats.get("stakeholders", 0)} stakeholders'
                if stats.get("stakeholder_relationships", 0) > 0:
                    details += f', {stats.get("stakeholder_relationships", 0)} relationships'
                if stats.get("stakeholder_maps", 0) > 0:
                    details += f', {stats.get("stakeholder_maps", 0)} maps'
                if stats.get("logos_restored", 0) > 0:
                    details += f', {stats.get("logos_restored", 0)} logos'
                if stats.get("formulas_restored", 0) > 0:
                    details += f', {stats.get("formulas_restored", 0)} formulas'
                if stats.get("linked_kpis_restored", 0) > 0:
                    details += f', {stats.get("linked_kpis_restored", 0)} linked KPIs'

                flash(details, "info")

                if stats.get("warnings"):
                    flash(f'⚠ {len(stats["warnings"])} warnings', "warning")
                    for warning in stats["warnings"][:5]:
                        flash(f"  • {warning}", "warning")
            else:
                flash("Restore failed", "danger")
                error_msg = result.get("error", "Unknown error")
                flash(error_msg, "danger")
                for error in result.get("errors", [])[:5]:
                    flash(f"  • {error}", "danger")

            return redirect(url_for("global_admin.backup_restore"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error during restore: {str(e)}", "danger")
            import traceback

            traceback.print_exc()

    return render_template(
        "global_admin/full_backup_governance_mapping.html",
        governance_bodies=gb_names,
        existing_gbs=existing_gbs,
        org=org,
    )


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
            .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
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
