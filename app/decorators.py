"""
Custom decorators for route protection and permission checking
"""

from functools import wraps

from flask import abort, flash, redirect, url_for
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
                flash(f"You don't have permission to access this feature", "danger")
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator
