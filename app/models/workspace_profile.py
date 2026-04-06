"""
User Workspace Profile — persistent named configurations that control
which labels (and in the future: startup page, display mode, etc.)
are active for a user.

Each user can have multiple profiles but only one is active at a time.
"""

from datetime import datetime

from app.extensions import db


class UserWorkspaceProfile(db.Model):
    """A named configuration/persona for filtering and displaying workspaces."""

    __tablename__ = "user_workspace_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(10), nullable=False, default="briefcase")  # Bootstrap icon name
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    config = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique profile name per user
    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_user_profile_name"),)

    # Relationships
    user = db.relationship("User", backref=db.backref("workspace_profiles", lazy="select", cascade="all, delete-orphan"))

    @property
    def label_ids(self):
        """Get the label IDs this profile filters by."""
        return self.config.get("label_ids", [])

    @label_ids.setter
    def label_ids(self, ids):
        cfg = dict(self.config or {})
        cfg["label_ids"] = ids
        self.config = cfg

    @property
    def space_visibility(self):
        """Get space visibility setting: 'all' or 'public'."""
        return self.config.get("space_visibility", "all")

    @space_visibility.setter
    def space_visibility(self, value):
        cfg = dict(self.config or {})
        cfg["space_visibility"] = value
        self.config = cfg

    @property
    def action_scope(self):
        """Get action item scope: 'all' (show global from other orgs) or 'workspace' (own org only)."""
        return self.config.get("action_scope", "all")

    @action_scope.setter
    def action_scope(self, value):
        cfg = dict(self.config or {})
        cfg["action_scope"] = value
        self.config = cfg

    def __repr__(self):
        return f"<UserWorkspaceProfile {self.name} (user={self.user_id}, active={self.is_active})>"
