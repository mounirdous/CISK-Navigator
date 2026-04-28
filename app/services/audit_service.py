"""
Audit Service - Helper functions for logging system changes
"""

from flask import request, session
from flask_login import current_user

from app.models import AuditLog
from app.models.organization import Organization


class AuditService:
    """Service for creating audit log entries"""

    @staticmethod
    def log_action(
        action, entity_type, entity_id=None, entity_name=None, description=None, old_value=None, new_value=None
    ):
        """
        Log an action with automatic context gathering.

        Args:
            action: Action performed (CREATE, UPDATE, DELETE, etc.)
            entity_type: Type of entity (Organization, KPI, User, etc.)
            entity_id: ID of entity
            entity_name: Name of entity
            description: Human-readable description
            old_value: State before (dict)
            new_value: State after (dict)

        Returns:
            AuditLog instance
        """
        user = current_user if current_user.is_authenticated else None
        organization_id = session.get("organization_id")
        # Session may carry a stale org id (e.g. org was hard-deleted). The FK
        # would then violate on insert, so drop it back to NULL.
        if organization_id and not Organization.query.get(organization_id):
            organization_id = None
        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get("User-Agent") if request else None

        return AuditLog.log(
            user=user,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            old_value=old_value,
            new_value=new_value,
            organization_id=organization_id,
            ip_address=ip_address,
            user_agent=user_agent[:255] if user_agent else None,
        )

    @staticmethod
    def log_login(user, success=True, reason=None):
        """Log user login attempt"""
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        description = "User logged in successfully" if success else f"Login failed: {reason}"

        return AuditLog.log(
            user=user if success else None,
            action=action,
            entity_type="User",
            entity_id=user.id if user else None,
            entity_name=user.login if user else None,
            description=description,
            ip_address=request.remote_addr if request else None,
            user_agent=(
                request.headers.get("User-Agent")[:255] if request and request.headers.get("User-Agent") else None
            ),
        )

    @staticmethod
    def log_logout(user):
        """Log user logout"""
        return AuditLog.log(
            user=user,
            action="LOGOUT",
            entity_type="User",
            entity_id=user.id,
            entity_name=user.login,
            description="User logged out",
            ip_address=request.remote_addr if request else None,
        )

    @staticmethod
    def log_create(entity_type, entity_id, entity_name, new_value=None):
        """Log entity creation"""
        description = f"{entity_type} '{entity_name}' created"
        return AuditService.log_action(
            action="CREATE",
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            new_value=new_value,
        )

    @staticmethod
    def log_update(entity_type, entity_id, entity_name, old_value, new_value, changes_description=None):
        """Log entity update"""
        description = changes_description or f"{entity_type} '{entity_name}' updated"
        return AuditService.log_action(
            action="UPDATE",
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            old_value=old_value,
            new_value=new_value,
        )

    @staticmethod
    def log_delete(entity_type, entity_id, entity_name, old_value=None):
        """Log entity deletion"""
        description = f"{entity_type} '{entity_name}' deleted"
        return AuditService.log_action(
            action="DELETE",
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            old_value=old_value,
        )

    @staticmethod
    def log_archive(entity_type, entity_id, entity_name):
        """Log entity archival (soft delete)"""
        description = f"{entity_type} '{entity_name}' archived"
        return AuditService.log_action(
            action="ARCHIVE",
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
        )

    @staticmethod
    def log_restore(entity_type, entity_id, entity_name):
        """Log entity restoration"""
        description = f"{entity_type} '{entity_name}' restored from archive"
        return AuditService.log_action(
            action="RESTORE",
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
        )
