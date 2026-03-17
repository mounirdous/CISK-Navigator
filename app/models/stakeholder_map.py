"""Models for stakeholder maps (collections of stakeholders)."""

from datetime import datetime

from app import db


class StakeholderMap(db.Model):
    """A named collection of stakeholders with privacy settings."""

    __tablename__ = "stakeholder_maps"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    visibility = db.Column(db.String(20), nullable=False, default="shared", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = db.relationship("Organization", backref=db.backref("stakeholder_maps", passive_deletes=True))
    created_by = db.relationship("User", backref="created_stakeholder_maps")
    memberships = db.relationship(
        "StakeholderMapMembership", backref="map", cascade="all, delete-orphan", lazy="dynamic"
    )

    def is_visible_to_user(self, user):
        """Check if this map is visible to the given user."""
        if user.is_super_admin or user.is_global_admin:
            return True

        if user.is_org_admin(self.organization_id):
            return True

        if self.visibility == "shared":
            return True

        if self.visibility == "private":
            return self.created_by_user_id == user.id

        return False

    def get_stakeholders(self):
        """Get all stakeholders in this map."""
        from app.models import Stakeholder

        stakeholder_ids = [m.stakeholder_id for m in self.memberships.all()]
        return Stakeholder.query.filter(Stakeholder.id.in_(stakeholder_ids)).all() if stakeholder_ids else []

    def add_stakeholder(self, stakeholder_id):
        """Add a stakeholder to this map."""
        membership = StakeholderMapMembership(map_id=self.id, stakeholder_id=stakeholder_id)
        db.session.add(membership)

    def remove_stakeholder(self, stakeholder_id):
        """Remove a stakeholder from this map."""
        membership = StakeholderMapMembership.query.filter_by(map_id=self.id, stakeholder_id=stakeholder_id).first()
        if membership:
            db.session.delete(membership)

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "created_by_user_id": self.created_by_user_id,
            "name": self.name,
            "description": self.description,
            "visibility": self.visibility,
            "stakeholder_count": self.memberships.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StakeholderMapMembership(db.Model):
    """Many-to-many relationship between maps and stakeholders."""

    __tablename__ = "stakeholder_map_memberships"

    id = db.Column(db.Integer, primary_key=True)
    map_id = db.Column(db.Integer, db.ForeignKey("stakeholder_maps.id", ondelete="CASCADE"), nullable=False, index=True)
    stakeholder_id = db.Column(
        db.Integer, db.ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Unique constraint to prevent duplicate memberships
    __table_args__ = (db.UniqueConstraint("map_id", "stakeholder_id", name="uq_map_stakeholder"),)

    stakeholder = db.relationship("Stakeholder")

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "map_id": self.map_id,
            "stakeholder_id": self.stakeholder_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
