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
from app.services import AuditService, OrganizationCloneService, TestRunnerService

bp = Blueprint("global_admin", __name__, url_prefix="/global-admin")


def global_admin_required(f):
    """Decorator to require global admin access"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_global_admin:
            flash("Access denied: Instance Admin permission required", "danger")
            return redirect(url_for("auth.login"))
        # Set admin mode flag — org context is preserved for navbar menus
        session["_admin_mode"] = True
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

    return render_template("global_admin/health_dashboard.html", health=health_data, csrf_token=generate_csrf)


@bp.route("/health-dashboard/migration-check")
@login_required
@global_admin_required
def migration_health_check():
    """Run migration health check script and display results"""
    import subprocess
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent
    script_path = project_root / "scripts" / "check_migrations.py"

    if not script_path.exists():
        flash("Migration health check script not found", "danger")
        return redirect(url_for("global_admin.health_dashboard"))

    try:
        # Run the script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=30,
        )

        # Parse output
        output = result.stdout
        exit_code = result.returncode
        status = "success" if exit_code == 0 else "error"

        return render_template(
            "global_admin/migration_check_results.html",
            output=output,
            exit_code=exit_code,
            status=status,
        )

    except subprocess.TimeoutExpired:
        flash("Migration check timed out (>30s)", "danger")
        return redirect(url_for("global_admin.health_dashboard"))
    except Exception as e:
        flash(f"Error running migration check: {str(e)}", "danger")
        return redirect(url_for("global_admin.health_dashboard"))


@bp.route("/health-dashboard/run-tests", methods=["GET", "POST"])
@login_required
@global_admin_required
def run_tests():
    """Trigger async test suite execution"""
    from flask import current_app

    # Check if Celery is enabled
    if not current_app.config.get("CELERY_ENABLED"):
        flash("Test runner is not available. Redis/Celery is not configured.", "warning")
        return redirect(url_for("global_admin.health_dashboard"))

    from app.tasks import run_test_suite_task

    if request.method == "POST":
        try:
            test_path = request.form.get("test_path") or None
            task = run_test_suite_task.delay(user_id=current_user.id, test_path=test_path)

            # Redirect to status page with task ID
            return redirect(url_for("global_admin.test_status", task_id=task.id))
        except Exception as e:
            flash(f"Failed to start test execution: {str(e)}", "danger")
            return redirect(url_for("global_admin.health_dashboard"))

    # GET request - show form to trigger tests
    return render_template("global_admin/run_tests_trigger.html")


@bp.route("/health-dashboard/test-status/<task_id>")
@login_required
@global_admin_required
def test_status(task_id):
    """Show test execution status with live polling"""
    return render_template(
        "global_admin/test_status.html",
        task_id=task_id,
    )


@bp.route("/health-dashboard/test-status/<task_id>/poll")
@login_required
@global_admin_required
def test_status_poll(task_id):
    """Poll endpoint for test execution status (returns JSON)"""
    from flask import jsonify

    from app.tasks import run_test_suite_task

    # Get task result
    task = run_test_suite_task.AsyncResult(task_id)

    if task.state == "PENDING":
        response = {
            "state": task.state,
            "status": "Waiting to start...",
        }
    elif task.state == "PROGRESS":
        response = {
            "state": task.state,
            "status": task.info.get("status", "Running..."),
            "step": task.info.get("step", 2),
            "passed": task.info.get("passed", 0),
            "failed": task.info.get("failed", 0),
            "total": task.info.get("total", 0),
        }
    elif task.state == "SUCCESS":
        response = {
            "state": task.state,
            "result": task.info,
        }
    elif task.state == "FAILURE":
        response = {
            "state": task.state,
            "status": str(task.info),
        }
    else:
        response = {
            "state": task.state,
            "status": "Unknown state",
        }

    return jsonify(response)


@bp.route("/health-dashboard/test-result/<task_id>")
@login_required
@global_admin_required
def test_result(task_id):
    """Display test results after task completion"""
    from app.tasks import run_test_suite_task

    # Get task result
    task = run_test_suite_task.AsyncResult(task_id)

    if task.state != "SUCCESS":
        flash("Test execution did not complete successfully", "danger")
        return redirect(url_for("global_admin.health_dashboard"))

    results = task.info

    return render_template(
        "global_admin/test_runner_results.html",
        results=results,
        timestamp=datetime.now(),
    )


@bp.route("/health-dashboard/test-history")
@login_required
@global_admin_required
def test_history():
    """View test execution history with trends"""
    executions = TestRunnerService.get_test_history(limit=30)

    return render_template(
        "global_admin/test_history.html",
        executions=executions,
    )


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
            assistant_enabled=form.assistant_enabled.data,
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
                can_view_action_items=request.form.get(f"perm_view_action_items_{org_id}") == "on",
                can_create_action_items=request.form.get(f"perm_create_action_items_{org_id}") == "on",
                can_view_stakeholders=request.form.get(f"perm_view_stakeholders_{org_id}") == "on",
                can_manage_stakeholders=request.form.get(f"perm_manage_stakeholders_{org_id}") == "on",
                can_view_map=request.form.get(f"perm_view_map_{org_id}") == "on",
                can_edit_porters=request.form.get(f"perm_edit_porters_{org_id}") == "on",
                can_view_snapshots=request.form.get(f"perm_view_snapshots_{org_id}") == "on",
                can_create_snapshots=request.form.get(f"perm_create_snapshots_{org_id}") == "on",
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
        user.assistant_enabled = form.assistant_enabled.data

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
                can_view_action_items=request.form.get(f"perm_view_action_items_{org_id}") == "on",
                can_create_action_items=request.form.get(f"perm_create_action_items_{org_id}") == "on",
                can_view_stakeholders=request.form.get(f"perm_view_stakeholders_{org_id}") == "on",
                can_manage_stakeholders=request.form.get(f"perm_manage_stakeholders_{org_id}") == "on",
                can_view_map=request.form.get(f"perm_view_map_{org_id}") == "on",
                can_edit_porters=request.form.get(f"perm_edit_porters_{org_id}") == "on",
                can_view_snapshots=request.form.get(f"perm_view_snapshots_{org_id}") == "on",
                can_create_snapshots=request.form.get(f"perm_create_snapshots_{org_id}") == "on",
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
                "contribute": request.form.get(f"perm_contribute_{user.id}") == "on",
                "view_action_items": request.form.get(f"perm_view_action_items_{user.id}") == "on",
                "create_action_items": request.form.get(f"perm_create_action_items_{user.id}") == "on",
                "view_stakeholders": request.form.get(f"perm_view_stakeholders_{user.id}") == "on",
                "manage_stakeholders": request.form.get(f"perm_manage_stakeholders_{user.id}") == "on",
                "view_map": request.form.get(f"perm_view_map_{user.id}") == "on",
                "edit_porters": request.form.get(f"perm_edit_porters_{user.id}") == "on",
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

        org = Organization(name=form.name.data.strip(), description=form.description.data, is_active=form.is_active.data)
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
                can_contribute=request.form.get(f"perm_contribute_{user_id}") == "on",
                can_view_action_items=request.form.get(f"perm_view_action_items_{user_id}") == "on",
                can_create_action_items=request.form.get(f"perm_create_action_items_{user_id}") == "on",
                can_view_stakeholders=request.form.get(f"perm_view_stakeholders_{user_id}") == "on",
                can_manage_stakeholders=request.form.get(f"perm_manage_stakeholders_{user_id}") == "on",
                can_view_map=request.form.get(f"perm_view_map_{user_id}") == "on",
                can_edit_porters=request.form.get(f"perm_edit_porters_{user_id}") == "on",
                can_view_snapshots=request.form.get(f"perm_view_snapshots_{user_id}") == "on",
                can_create_snapshots=request.form.get(f"perm_create_snapshots_{user_id}") == "on",
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
        new_name = form.name.data.strip()

        # Check for name conflict (including archived orgs) before touching the session
        if new_name.upper() != org.name.upper():
            conflict = Organization.query.filter(
                Organization.name == new_name,
                Organization.id != org.id
            ).first()
            if conflict:
                if conflict.is_deleted:
                    # Auto-rename the archived org with a unique suffix to free up the name
                    from datetime import date
                    base = f"{conflict.name}_archived_{date.today().strftime('%Y%m%d')}"
                    unique_name = base
                    suffix = 1
                    while Organization.query.filter_by(name=unique_name).first():
                        unique_name = f"{base}_{suffix}"
                        suffix += 1
                    old_archived_name = conflict.name
                    conflict.name = unique_name
                    db.session.flush()
                    flash(
                        f'Archived organization "{old_archived_name}" was automatically renamed to '
                        f'"{unique_name}" to free up the name.',
                        "info",
                    )
                else:
                    flash(f'An active organization named "{new_name}" already exists.', "danger")
                    return render_template("global_admin/edit_organization.html", form=form, org=org, all_users=all_users)

        # Capture old values for audit
        old_values = {
            "name": org.name,
            "description": org.description,
            "is_active": org.is_active,
            "users_count": len(org.user_memberships),
        }

        # Apply changes
        org.name = new_name
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
                can_contribute=request.form.get(f"perm_contribute_{user_id}") == "on",
                can_view_action_items=request.form.get(f"perm_view_action_items_{user_id}") == "on",
                can_create_action_items=request.form.get(f"perm_create_action_items_{user_id}") == "on",
                can_view_stakeholders=request.form.get(f"perm_view_stakeholders_{user_id}") == "on",
                can_manage_stakeholders=request.form.get(f"perm_manage_stakeholders_{user_id}") == "on",
                can_view_map=request.form.get(f"perm_view_map_{user_id}") == "on",
                can_edit_porters=request.form.get(f"perm_edit_porters_{user_id}") == "on",
                can_view_snapshots=request.form.get(f"perm_view_snapshots_{user_id}") == "on",
                can_create_snapshots=request.form.get(f"perm_create_snapshots_{user_id}") == "on",
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
            source_org_id=org_id,
            new_org_name=form.new_name.data,
            new_org_description=form.new_description.data,
            cloned_by_user_id=current_user.id,
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
    from app.models.geography import GeographyCountry, GeographyRegion, GeographySite

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

        regions_count = GeographyRegion.query.filter_by(organization_id=org.id).count()
        countries_count = (
            db.session.query(GeographyCountry)
            .join(GeographyRegion, GeographyCountry.region_id == GeographyRegion.id)
            .filter(GeographyRegion.organization_id == org.id)
            .count()
        )
        sites_count = (
            db.session.query(GeographySite)
            .join(GeographyCountry, GeographySite.country_id == GeographyCountry.id)
            .join(GeographyRegion, GeographyCountry.region_id == GeographyRegion.id)
            .filter(GeographyRegion.organization_id == org.id)
            .count()
        )

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
                "regions": regions_count,
                "countries": countries_count,
                "sites": sites_count,
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
            # Full backup - detect users that need mapping and governance bodies
            try:
                import json

                backup_data = json.loads(backup_content)
                governance_bodies = backup_data.get("governance_bodies", [])
                backup_users = backup_data.get("users", [])
                # Detect portal systems (linked to other CISK orgs)
                portal_org_names = set()
                for sp in backup_data.get("spaces", []):
                    for ch in sp.get("challenges", []):
                        for ini in ch.get("initiatives", []):
                            for sys_d in ini.get("systems", []):
                                lon = sys_d.get("linked_organization_name")
                                if lon:
                                    portal_org_names.add(lon)
                portal_org_names = sorted(portal_org_names)
            except Exception:
                governance_bodies = []
                backup_users = []
                portal_org_names = []

            # Detect users not auto-resolvable by login
            unmapped_users = [u for u in backup_users if not User.query.filter_by(login=u["login"]).first()]

            needs_step = unmapped_users or governance_bodies or portal_org_names
            if needs_step:
                import tempfile

                tmp = tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".json",
                    delete=False,
                    encoding="utf-8",
                    dir=tempfile.gettempdir(),
                    prefix="cisk_restore_",
                )
                tmp.write(backup_content)
                tmp.close()

                session["pending_full_backup_path"] = tmp.name
                session["full_backup_org_id"] = org_id
                session["full_backup_governance_bodies"] = [gb["name"] for gb in governance_bodies]
                session["full_backup_portal_orgs"] = portal_org_names
                session.pop("full_backup_user_mapping", None)
                session.pop("pending_full_backup", None)

                if unmapped_users:
                    session["full_backup_unmapped_users"] = [u["login"] for u in unmapped_users]
                    return redirect(url_for("global_admin.full_backup_user_mapping"))
                else:
                    return redirect(url_for("global_admin.full_backup_governance_mapping"))
            else:
                # All users found in DB and no governance bodies — proceed directly
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

                    if stats.get("errors"):
                        flash(f'Restore errors: {len(stats["errors"])}', "danger")
                        for err in stats["errors"][:5]:
                            flash(f"  • {err}", "danger")
                    if stats.get("warnings"):
                        flash(f'⚠ {len(stats["warnings"])} warnings', "warning")
                        for warning in stats["warnings"][:5]:
                            flash(f"  • {warning}", "warning")
                else:
                    flash("Restore failed", "danger")
                    error_msg = result.get("error", "Unknown error")
                    flash(error_msg, "danger")
                    for err in result.get("errors", [])[:5]:
                        flash(f"  • {err}", "danger")

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


@bp.route("/backup-restore/user-mapping", methods=["GET", "POST"])
@login_required
@global_admin_required
def full_backup_user_mapping():
    """Map backup users that don't exist in DB to existing users or skip them"""
    import json
    import os

    backup_path = session.get("pending_full_backup_path")
    org_id = session.get("full_backup_org_id")
    unmapped_logins = session.get("full_backup_unmapped_users", [])

    if not backup_path or not os.path.exists(backup_path) or not org_id:
        flash("No pending backup restore found", "warning")
        return redirect(url_for("global_admin.backup_restore"))

    with open(backup_path, "r", encoding="utf-8") as f:
        backup_content = f.read()
    backup_data = json.loads(backup_content)

    org = db.session.get(Organization, org_id)
    if not org:
        flash("Organization not found", "danger")
        return redirect(url_for("global_admin.backup_restore"))

    # Only show users that couldn't be auto-resolved
    unmapped_users = [u for u in backup_data.get("users", []) if u["login"] in unmapped_logins]
    existing_users = User.query.filter(User.is_active.is_(True)).order_by(User.display_name).all()
    gb_names = session.get("full_backup_governance_bodies", [])

    if request.method == "POST":
        # Build user mapping from form
        user_mapping = {}
        for idx, backup_user in enumerate(unmapped_users):
            action = request.form.get(f"user_action_{idx}", "skip")
            backup_login = backup_user["login"]
            if action == "map":
                mapped_user_id = request.form.get(f"map_to_user_{idx}", type=int)
                if mapped_user_id:
                    user_mapping[backup_login] = {"action": "map", "user_id": mapped_user_id}
            elif action == "create":
                user_mapping[backup_login] = {
                    "action": "create",
                    "login": backup_login,
                    "email": backup_user["email"],
                    "display_name": backup_user["display_name"],
                    "permissions": backup_user.get("permissions", {}),
                }
            # "skip" → not added to mapping

        session["full_backup_user_mapping"] = json.dumps(user_mapping)

        if gb_names:
            return redirect(url_for("global_admin.full_backup_governance_mapping"))

        # No governance bodies — restore directly
        import json as _json

        from app.services.full_restore_service import FullRestoreService

        tmp_path = session.pop("pending_full_backup_path", None)
        session.pop("full_backup_org_id", None)
        session.pop("full_backup_governance_bodies", None)
        session.pop("full_backup_unmapped_users", None)
        user_mapping_json = session.pop("full_backup_user_mapping", "{}")
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

        result = FullRestoreService.restore_from_json(
            backup_content, org_id, user_mapping=_json.loads(user_mapping_json)
        )

        if result.get("success"):
            stats = result.get("stats", result)
            flash(f"Full restore to {org.name} complete!", "success")
            details = (
                f'Restored: {stats.get("spaces", 0)} spaces, {stats.get("challenges", 0)} challenges, '
                f'{stats.get("initiatives", 0)} initiatives, {stats.get("systems", 0)} systems, '
                f'{stats.get("kpis", 0)} KPIs, {stats.get("contributions", 0)} contributions'
            )
            flash(details, "info")
            if stats.get("warnings"):
                for warning in stats["warnings"][:5]:
                    flash(f"  {warning}", "warning")
        else:
            flash("Restore failed: " + result.get("error", "Unknown error"), "danger")

        return redirect(url_for("global_admin.backup_restore"))

    from flask_wtf.csrf import generate_csrf

    return render_template(
        "global_admin/full_backup_user_mapping.html",
        unmapped_users=unmapped_users,
        existing_users=existing_users,
        org=org,
        has_governance_bodies=bool(gb_names),
        csrf_token=generate_csrf,
    )


@bp.route("/backup-restore/governance-mapping", methods=["GET", "POST"])
@login_required
@global_admin_required
def full_backup_governance_mapping():
    """Map governance bodies from full backup to existing or create new"""
    # Check if we have pending backup restore
    import os

    from app.services.full_restore_service import FullRestoreService

    backup_path = session.get("pending_full_backup_path")
    org_id = session.get("full_backup_org_id")
    gb_names = session.get("full_backup_governance_bodies", [])
    portal_org_names = session.get("full_backup_portal_orgs", [])

    if not backup_path or not os.path.exists(backup_path) or not org_id or not (gb_names or portal_org_names):
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

            # Build portal org mapping from form
            portal_org_mapping = {}
            for po_name in portal_org_names:
                po_action = request.form.get(f"portal_action_{po_name}")
                if po_action and po_action.startswith("map_"):
                    portal_org_mapping[po_name] = int(po_action.split("_")[1])
                # else: skip (no link)

            # Pick up user mapping from previous step (if user mapping was done)
            import json as _json

            user_mapping_json = session.pop("full_backup_user_mapping", None)
            user_mapping = _json.loads(user_mapping_json) if user_mapping_json else None

            # Clear session data and temp file
            tmp_path = session.pop("pending_full_backup_path", None)
            session.pop("pending_full_backup", None)
            session.pop("full_backup_org_id", None)
            session.pop("full_backup_governance_bodies", None)
            session.pop("full_backup_unmapped_users", None)
            session.pop("full_backup_portal_orgs", None)
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

            # Restore with governance body mapping, user mapping, and portal mapping
            result = FullRestoreService.restore_from_json(
                backup_content, org_id,
                governance_body_mapping=governance_body_mapping,
                user_mapping=user_mapping,
                portal_org_mapping=portal_org_mapping if portal_org_mapping else None,
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

                if stats.get("errors"):
                    flash(f'Restore errors: {len(stats["errors"])}', "danger")
                    for err in stats["errors"][:5]:
                        flash(f"  • {err}", "danger")
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

    # Get all orgs for portal mapping (excluding target org)
    all_orgs = Organization.query.filter(Organization.id != org_id, Organization.is_deleted.is_(False)).order_by(Organization.name).all()

    return render_template(
        "global_admin/full_backup_governance_mapping.html",
        governance_bodies=gb_names,
        existing_gbs=existing_gbs,
        org=org,
        portal_org_names=portal_org_names,
        all_orgs=all_orgs,
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


@bp.route("/organizations/<int:org_id>/empty", methods=["POST"])
@login_required
@global_admin_required
def empty_organization(org_id):
    """Permanently delete ALL data from an organization (structure + contributions + everything)."""
    from app.routes.organization_admin import _delete_all_organization_data

    org = Organization.query.get_or_404(org_id)
    import unicodedata
    raw_confirm = request.form.get("confirm_org_name", "").strip()

    def _strip_accents(s):
        """Remove all diacritical marks for comparison."""
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

    # Try exact match, then NFC-normalized, then accent-stripped casefold
    # Strip both sides — DB values may have trailing whitespace
    org_name = org.name.strip()
    match = (
        raw_confirm == org_name
        or unicodedata.normalize("NFC", raw_confirm) == unicodedata.normalize("NFC", org_name)
        or _strip_accents(raw_confirm).casefold() == _strip_accents(org_name).casefold()
    )
    if not match:
        flash("Organization name confirmation does not match. Deletion cancelled.", "danger")
        return redirect(url_for("global_admin.organizations"))

    try:
        AuditService.log_action(
            action="EMPTY_ORGANIZATION",
            entity_type="Organization",
            entity_id=org.id,
            entity_name=org.name,
            description=f"Global admin emptied all data for organization {org.name}",
        )
        _delete_all_organization_data(org.id)
        db.session.commit()
        flash(f"All data permanently deleted from '{org.name}'. The organization is now empty.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error emptying organization: {str(e)}", "danger")

    return redirect(url_for("global_admin.organizations"))
