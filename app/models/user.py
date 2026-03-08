"""
User model
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    """
    User model for authentication and authorization.

    A user can be:
    - A global administrator (can manage users and organizations)
    - A regular user assigned to one or more organizations
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)
    display_name = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_global_admin = db.Column(db.Boolean, default=False, nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    dark_mode = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization_memberships = db.relationship('UserOrganizationMembership',
                                               back_populates='user',
                                               cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)

    def get_organizations(self):
        """Get list of organizations this user belongs to"""
        return [membership.organization for membership in self.organization_memberships]

    def has_organization_access(self, organization_id):
        """Check if user has access to a specific organization"""
        return any(m.organization_id == organization_id for m in self.organization_memberships)

    def get_membership(self, organization_id):
        """Get the membership object for a specific organization"""
        for membership in self.organization_memberships:
            if membership.organization_id == organization_id:
                return membership
        return None

    def can_manage_spaces(self, organization_id):
        """Check if user can manage spaces in an organization"""
        if self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return membership and membership.can_manage_spaces

    def can_manage_value_types(self, organization_id):
        """Check if user can manage value types in an organization"""
        if self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return membership and membership.can_manage_value_types

    def can_manage_governance_bodies(self, organization_id):
        """Check if user can manage governance bodies in an organization"""
        if self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return membership and membership.can_manage_governance_bodies

    def can_manage_challenges(self, organization_id):
        """Check if user can manage challenges in an organization"""
        if self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return membership and membership.can_manage_challenges

    def can_manage_initiatives(self, organization_id):
        """Check if user can manage initiatives in an organization"""
        if self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return membership and membership.can_manage_initiatives

    def can_manage_systems(self, organization_id):
        """Check if user can manage systems in an organization"""
        if self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return membership and membership.can_manage_systems

    def can_manage_kpis(self, organization_id):
        """Check if user can manage KPIs in an organization"""
        if self.is_global_admin:
            return True
        membership = self.get_membership(organization_id)
        return membership and membership.can_manage_kpis

    def __repr__(self):
        return f'<User {self.login}>'
