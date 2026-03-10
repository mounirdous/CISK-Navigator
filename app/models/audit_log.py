"""
Audit Log model for tracking system changes
"""

from datetime import datetime

from app.extensions import db


class AuditLog(db.Model):
    """
    Audit log for tracking all significant changes in the system.

    Tracks who did what, when, and stores before/after values for changes.
    Essential for compliance, debugging, and accountability.
    """

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    # Who performed the action
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_login = db.Column(db.String(80), nullable=True)  # Denormalized for history preservation

    # What action was performed
    action = db.Column(db.String(50), nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    entity_type = db.Column(db.String(50), nullable=False, index=True)  # Organization, KPI, User, etc.
    entity_id = db.Column(db.Integer, nullable=True)  # ID of the affected entity
    entity_name = db.Column(db.String(200), nullable=True)  # Denormalized for history

    # Change details
    description = db.Column(db.Text, nullable=True)  # Human-readable description
    old_value = db.Column(db.JSON, nullable=True)  # State before change
    new_value = db.Column(db.JSON, nullable=True)  # State after change

    # Context
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    user_agent = db.Column(db.String(255), nullable=True)

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id])
    organization = db.relationship("Organization", foreign_keys=[organization_id])

    def __repr__(self):
        return f"<AuditLog {self.action} {self.entity_type} by {self.user_login}>"

    @staticmethod
    def log(
        user,
        action,
        entity_type,
        entity_id=None,
        entity_name=None,
        description=None,
        old_value=None,
        new_value=None,
        organization_id=None,
        ip_address=None,
        user_agent=None,
    ):
        """
        Create an audit log entry.

        Args:
            user: User object or None for system actions
            action: Action performed (CREATE, UPDATE, DELETE, LOGIN, etc.)
            entity_type: Type of entity affected (Organization, KPI, User, etc.)
            entity_id: ID of affected entity
            entity_name: Name of affected entity (for history)
            description: Human-readable description
            old_value: State before change (dict)
            new_value: State after change (dict)
            organization_id: Organization context
            ip_address: User's IP address
            user_agent: User's browser/client

        Returns:
            AuditLog instance
        """
        log = AuditLog(
            user_id=user.id if user else None,
            user_login=user.login if user else "system",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            old_value=old_value,
            new_value=new_value,
            organization_id=organization_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.session.add(log)
        return log

    @staticmethod
    def get_recent(limit=100, user_id=None, entity_type=None, organization_id=None):
        """
        Get recent audit logs with optional filters.

        Args:
            limit: Maximum number of logs to return
            user_id: Filter by user
            entity_type: Filter by entity type
            organization_id: Filter by organization

        Returns:
            Query object
        """
        query = AuditLog.query

        if user_id:
            query = query.filter_by(user_id=user_id)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        if organization_id:
            query = query.filter_by(organization_id=organization_id)

        return query.order_by(AuditLog.created_at.desc()).limit(limit)
