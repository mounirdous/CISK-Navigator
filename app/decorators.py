"""
Custom decorators for route protection and permission checking
"""

from functools import wraps

from flask import abort, flash, redirect, request, url_for
from flask_login import current_user


def super_admin_required(f):
    """
    Decorator to require super admin privileges.

    Super admins have access to system-wide settings and all features.
    This is the highest privilege level.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page", "warning")
            return redirect(url_for("auth.login"))

        if not current_user.is_super_admin:
            flash("Super admin access required", "danger")
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


def global_admin_required(f):
    """
    Decorator to require global admin privileges or higher.

    Global admins can manage users and organizations.
    Super admins also have this access.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page", "warning")
            return redirect(url_for("auth.login"))

        if not (current_user.is_super_admin or current_user.is_global_admin):
            flash("Global admin access required", "danger")
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


def admin_required(level="global"):
    """
    Flexible admin decorator that can check for different admin levels.

    Args:
        level: 'super', 'global', or 'any'

    Usage:
        @admin_required(level='super')
        def super_admin_only_route():
            pass
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page", "warning")
                return redirect(url_for("auth.login"))

            if level == "super" and not current_user.is_super_admin:
                flash("Super admin access required", "danger")
                abort(403)
            elif level == "global" and not (current_user.is_super_admin or current_user.is_global_admin):
                flash("Global admin access required", "danger")
                abort(403)
            elif level == "any" and not (current_user.is_super_admin or current_user.is_global_admin):
                flash("Admin access required", "danger")
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def organization_permission_required(permission_name):
    """
    Decorator to check organization-specific permissions.

    Args:
        permission_name: Name of the permission method (e.g., 'can_manage_spaces')

    Usage:
        @organization_permission_required('can_manage_spaces')
        def create_space():
            pass
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page", "warning")
                return redirect(url_for("auth.login"))

            # Super and global admins bypass org permission checks
            if current_user.is_super_admin or current_user.is_global_admin:
                return f(*args, **kwargs)

            # Check organization permission
            from flask import session

            organization_id = session.get("organization_id")
            if not organization_id:
                flash("No organization context", "danger")
                return redirect(url_for("auth.login"))

            if not current_user.has_permission(organization_id, permission_name):
                flash("You don't have permission to access this feature", "danger")
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def maintenance_mode_check(f):
    """
    Decorator to block write operations during maintenance mode.

    Super admins are exempt and can still make changes.
    All other users get read-only access during maintenance.

    Usage:
        @maintenance_mode_check
        def create_space():
            pass
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Import here to avoid circular dependency
        from app.models import SystemSetting

        # Check if maintenance mode is active
        if SystemSetting.is_maintenance_mode():
            # Super admins can bypass maintenance mode
            if current_user.is_authenticated and current_user.is_super_admin:
                return f(*args, **kwargs)

            # Block write operations (POST, PUT, DELETE, PATCH)
            if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
                flash(
                    "System is in maintenance mode. Write operations are temporarily disabled.",
                    "warning",
                )
                # Try to redirect to referer or index
                return redirect(request.referrer or url_for("workspace.dashboard"))

        return f(*args, **kwargs)

    return decorated_function
