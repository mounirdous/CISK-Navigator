"""
Organization models
"""

from datetime import datetime

from app.extensions import db


class Organization(db.Model):
    """
    Organization model.

    An organization is an isolated root that contains:
    - Spaces, Challenges, Initiatives, Systems, KPIs
    - Value Types (organization-specific)
    - Roll-up configurations
    """

    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user_memberships = db.relationship(
        "UserOrganizationMembership", back_populates="organization", cascade="all, delete-orphan"
    )
    spaces = db.relationship("Space", back_populates="organization", cascade="all, delete-orphan")
    challenges = db.relationship("Challenge", back_populates="organization", cascade="all, delete-orphan")
    initiatives = db.relationship("Initiative", back_populates="organization", cascade="all, delete-orphan")
    systems = db.relationship("System", back_populates="organization", cascade="all, delete-orphan")
    value_types = db.relationship("ValueType", back_populates="organization", cascade="all, delete-orphan")
    governance_bodies = db.relationship("GovernanceBody", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization {self.name}>"


class UserOrganizationMembership(db.Model):
    """
    Association between users and organizations.

    A user can belong to multiple organizations with different permissions per org.
    """

    __tablename__ = "user_organization_memberships"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Permissions (per organization)
    can_manage_spaces = db.Column(db.Boolean, default=True, nullable=False)
    can_manage_value_types = db.Column(db.Boolean, default=True, nullable=False)
    can_manage_governance_bodies = db.Column(db.Boolean, default=True, nullable=False)
    can_manage_challenges = db.Column(db.Boolean, default=True, nullable=False)
    can_manage_initiatives = db.Column(db.Boolean, default=True, nullable=False)
    can_manage_systems = db.Column(db.Boolean, default=True, nullable=False)
    can_manage_kpis = db.Column(db.Boolean, default=True, nullable=False)
    can_view_comments = db.Column(db.Boolean, default=True, nullable=False)
    can_add_comments = db.Column(db.Boolean, default=True, nullable=False)

    # Unique constraint: one user cannot be assigned twice to the same organization
    __table_args__ = (db.UniqueConstraint("user_id", "organization_id", name="uq_user_org"),)

    # Relationships
    user = db.relationship("User", back_populates="organization_memberships")
    organization = db.relationship("Organization", back_populates="user_memberships")

    def __repr__(self):
        return f"<UserOrganizationMembership user_id={self.user_id} org_id={self.organization_id}>"
