"""
User model
"""

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    """
    User model for authentication and authorization.

    A user can be:
    - A super administrator (can manage system settings and has all privileges)
    - An instance administrator (can manage users and organizations)
    - A regular user assigned to one or more organizations

    Hierarchy: Super Admin > Instance Admin > Org User
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)
    display_name = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for SSO-only users
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_global_admin = db.Column(db.Boolean, default=False, nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    dark_mode = db.Column(db.Boolean, default=False, nullable=False)
    navbar_position = db.Column(db.String(10), default="top", nullable=False)  # 'top' or 'left'
    navbar_autohide = db.Column(db.Boolean, default=False, nullable=False)
    beta_tester = db.Column(db.Boolean, default=False, nullable=False)  # Enable beta feature access
    default_organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )

    # SSO Fields
    sso_provider = db.Column(db.String(50), nullable=True)  # 'oidc', 'saml', 'google', 'azure', etc.
    sso_subject_id = db.Column(db.String(255), nullable=True, index=True)  # Unique ID from IdP
    sso_email = db.Column(db.String(255), nullable=True)  # Email from SSO provider
    last_sso_login = db.Column(db.DateTime, nullable=True)  # Track last SSO login

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization_memberships = db.relationship(
        "UserOrganizationMembership", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)

    def get_organizations(self):
        """Get list of organizations this user belongs to"""
        try:
            return [membership.organization for membership in self.organization_memberships]
        except Exception:
            # During migrations, schema might not match - return empty list
            return []

    def has_organization_access(self, organization_id):
        """Check if user has access to a specific organization"""
        try:
            return any(m.organization_id == organization_id for m in self.organization_memberships)
        except Exception:
            # During migrations, schema might not match
            return False

    def get_membership(self, organization_id):
        """Get the membership object for a specific organization"""
        try:
            for membership in self.organization_memberships:
                if membership.organization_id == organization_id:
                    return membership
            return None
        except Exception:
            # During migrations, schema might not match
            return None

    def is_org_admin(self, organization_id):
        """Check if user is an organization administrator"""
        if self.is_super_admin or self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return bool(membership and membership.is_org_admin)

    def can_manage_spaces(self, organization_id):
        """Check if user can manage spaces in an organization"""
        if self.is_super_admin or self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return bool(membership and (membership.is_org_admin or membership.can_manage_spaces))

    def can_manage_value_types(self, organization_id):
        """Check if user can manage value types in an organization"""
        if self.is_super_admin or self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return bool(membership and (membership.is_org_admin or membership.can_manage_value_types))

    def can_manage_governance_bodies(self, organization_id):
        """Check if user can manage governance bodies in an organization"""
        if self.is_super_admin or self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return bool(membership and (membership.is_org_admin or membership.can_manage_governance_bodies))

    def can_manage_challenges(self, organization_id):
        """Check if user can manage challenges in an organization"""
        if self.is_super_admin or self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return bool(membership and (membership.is_org_admin or membership.can_manage_challenges))

    def can_manage_initiatives(self, organization_id):
        """Check if user can manage initiatives in an organization"""
        if self.is_super_admin or self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return bool(membership and (membership.is_org_admin or membership.can_manage_initiatives))

    def can_manage_systems(self, organization_id):
        """Check if user can manage systems in an organization"""
        if self.is_super_admin or self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return bool(membership and (membership.is_org_admin or membership.can_manage_systems))

    def can_manage_kpis(self, organization_id):
        """Check if user can manage KPIs in an organization"""
        if self.is_super_admin or self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return bool(membership and (membership.is_org_admin or membership.can_manage_kpis))

    def can_view_comments(self, organization_id):
        """Check if user can view comments in an organization"""
        if self.is_super_admin or self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return bool(membership and (membership.is_org_admin or membership.can_view_comments))

    def can_add_comments(self, organization_id):
        """Check if user can add comments in an organization"""
        if self.is_super_admin or self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return bool(membership and (membership.is_org_admin or membership.can_add_comments))

    def can_contribute(self, organization_id):
        """Check if user can contribute values (enter KPI data) in an organization"""
        if self.is_super_admin or self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return bool(membership and (membership.is_org_admin or membership.can_contribute))

    def has_permission(self, organization_id, permission_name):
        """Generic permission checker - delegates to specific permission methods"""
        if self.is_super_admin or self.is_global_admin:
            return True
        method = getattr(self, permission_name, None)
        if method and callable(method):
            return method(organization_id)
        return False

    def get_admin_level(self):
        """Get the admin level of this user (for display purposes)"""
        if self.is_super_admin:
            return "Super Admin"
        elif self.is_global_admin:
            return "Instance Admin"
        else:
            return "User"

    def is_sso_user(self):
        """Check if this user authenticates via SSO"""
        return self.sso_provider is not None and self.sso_subject_id is not None

    def can_login_with_password(self):
        """Check if user can authenticate with password"""
        return self.password_hash is not None

    def is_sso_only(self):
        """Check if user can ONLY authenticate via SSO (no password)"""
        return self.is_sso_user() and not self.can_login_with_password()

    def update_sso_login(self):
        """Update last SSO login timestamp"""
        self.last_sso_login = datetime.utcnow()

    def __repr__(self):
        return f"<User {self.login}>"
