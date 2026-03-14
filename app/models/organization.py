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
    logo_data = db.Column(db.LargeBinary, nullable=True, comment="Logo image binary data")
    logo_mime_type = db.Column(db.String(50), nullable=True, comment="Logo MIME type (e.g., image/png)")
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Soft delete fields
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Porter's Five Forces Analysis
    porters_new_entrants = db.Column(db.Text, nullable=True, comment="Porter's: Threat of new entrants")
    porters_suppliers = db.Column(db.Text, nullable=True, comment="Porter's: Bargaining power of suppliers")
    porters_buyers = db.Column(db.Text, nullable=True, comment="Porter's: Bargaining power of buyers")
    porters_substitutes = db.Column(db.Text, nullable=True, comment="Porter's: Threat of substitutes")
    porters_rivalry = db.Column(db.Text, nullable=True, comment="Porter's: Competitive rivalry")

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
    deleter = db.relationship("User", foreign_keys=[deleted_by])

    def soft_delete(self, user_id):
        """Soft delete this organization (mark as deleted, don't remove from database)"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = user_id
        self.is_active = False  # Also mark as inactive

    def restore(self):
        """Restore a soft-deleted organization"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.is_active = True  # Restore as active

    @staticmethod
    def get_active_query():
        """Get query for non-deleted organizations"""
        from app.models import Organization

        return Organization.query.filter_by(is_deleted=False)

    def get_porters_completion(self):
        """Get Porter's Five Forces completion status

        Returns:
            tuple: (filled_count, total_count, completion_status)
            completion_status: 'empty', 'partial', 'complete'
        """
        porters_fields = [
            self.porters_new_entrants,
            self.porters_suppliers,
            self.porters_buyers,
            self.porters_substitutes,
            self.porters_rivalry,
        ]
        filled = sum(1 for field in porters_fields if field and field.strip())
        total = len(porters_fields)

        if filled == 0:
            status = "empty"
        elif filled == total:
            status = "complete"
        else:
            status = "partial"

        return (filled, total, status)

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

    # Last used workspace preset (for persistence across sessions)
    last_workspace_preset_id = db.Column(
        db.Integer,
        db.ForeignKey("user_filter_presets.id", ondelete="SET NULL"),
        nullable=True,
        comment="Last workspace preset loaded by this user in this org",
    )

    # Organization Admin Flag
    is_org_admin = db.Column(
        db.Boolean, default=False, nullable=False, comment="Organization administrator with full permissions"
    )

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
    can_contribute = db.Column(db.Boolean, default=True, nullable=False)

    # Unique constraint: one user cannot be assigned twice to the same organization
    __table_args__ = (db.UniqueConstraint("user_id", "organization_id", name="uq_user_org"),)

    # Relationships
    user = db.relationship("User", back_populates="organization_memberships")
    organization = db.relationship("Organization", back_populates="user_memberships")

    def __repr__(self):
        return f"<UserOrganizationMembership user_id={self.user_id} org_id={self.organization_id}>"
