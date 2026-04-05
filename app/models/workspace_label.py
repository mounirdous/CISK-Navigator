"""
Workspace Label models for organizing and filtering workspaces.
Labels are user-scoped: each user manages their own set of labels.
"""

from datetime import datetime

from app.extensions import db

# Many-to-many join table: organizations ↔ labels (per user, via label.user_id)
organization_label = db.Table(
    "organization_labels",
    db.Column(
        "organization_id",
        db.Integer,
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "label_id",
        db.Integer,
        db.ForeignKey("workspace_labels.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class WorkspaceLabel(db.Model):
    """A user-scoped label/tag for categorizing workspaces."""

    __tablename__ = "workspace_labels"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), nullable=False, default="#6366f1")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Unique label name per user
    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_user_label_name"),)

    # Relationships
    user = db.relationship("User", backref=db.backref("workspace_labels", lazy="select", cascade="all, delete-orphan"))
    organizations = db.relationship(
        "Organization",
        secondary=organization_label,
        backref=db.backref("labels", lazy="select", order_by="WorkspaceLabel.name"),
    )

    def __repr__(self):
        return f"<WorkspaceLabel {self.name} (user={self.user_id})>"
