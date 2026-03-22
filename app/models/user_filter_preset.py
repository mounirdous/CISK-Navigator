"""
User Filter Preset Model

Stores saved filter configurations for workspace views.
Users can save, load, and manage multiple filter presets per organization.
"""

from datetime import datetime

from app.extensions import db


class UserFilterPreset(db.Model):
    """
    Saved filter preset for a user in an organization.

    Allows users to save their frequently used filter combinations
    and quickly switch between them.
    """

    __tablename__ = "user_filter_presets"

    id = db.Column(db.Integer, primary_key=True)

    # Ownership
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Preset metadata
    name = db.Column(db.String(100), nullable=False, comment="User-defined name for this filter preset")
    feature = db.Column(
        db.String(50), nullable=False, default="workspace",
        comment="Feature this preset belongs to: 'workspace' or 'action_items'"
    )

    # Filter configuration (JSON)
    filters = db.Column(
        db.JSON,
        nullable=False,
        comment="Complete filter state as JSON dict",
    )

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", backref="filter_presets")
    organization = db.relationship("Organization", back_populates="filter_presets")

    # Constraints and indexes
    __table_args__ = (
        db.UniqueConstraint("user_id", "organization_id", "feature", "name", name="uq_user_org_feature_preset_name"),
    )

    def __repr__(self):
        return f"<UserFilterPreset {self.id} user={self.user_id} org={self.organization_id} name='{self.name}'>"

    def to_dict(self):
        """Convert preset to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "filters": self.filters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
