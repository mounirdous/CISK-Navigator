"""
Action Item and Memo models for organization-level task tracking
"""

from datetime import datetime

from sqlalchemy import Enum

from app.extensions import db


class ActionItem(db.Model):
    """Action items and memos at organization level"""

    __tablename__ = "action_items"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    # Type and content
    type = db.Column(Enum("memo", "action", name="action_item_type"), nullable=False, default="action")
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Action-specific fields
    status = db.Column(
        Enum("draft", "active", "completed", "cancelled", name="action_item_status"),
        nullable=False,
        default="active",
    )
    priority = db.Column(
        Enum("low", "medium", "high", "urgent", name="action_item_priority"),
        nullable=False,
        default="medium",
    )
    due_date = db.Column(db.Date)
    completed_at = db.Column(db.DateTime)

    # Ownership and visibility
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    visibility = db.Column(Enum("private", "shared", name="action_item_visibility"), nullable=False, default="shared")

    # Audit fields
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = db.relationship("Organization", back_populates="action_items")
    owner_user = db.relationship("User", foreign_keys=[owner_user_id], back_populates="owned_action_items")
    created_by_user = db.relationship("User", foreign_keys=[created_by_user_id], back_populates="created_action_items")
    mentions = db.relationship(
        "ActionItemMention",
        back_populates="action_item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<ActionItem {self.id}: {self.title}>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "owner_user_id": self.owner_user_id,
            "owner_name": self.owner_user.display_name or self.owner_user.login if self.owner_user else None,
            "visibility": self.visibility,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "mention_count": len(self.mentions),
        }

    @property
    def is_overdue(self):
        """Check if action is overdue"""
        if self.type != "action" or self.status in ("completed", "cancelled"):
            return False
        if not self.due_date:
            return False
        return self.due_date < datetime.now().date()


class ActionItemMention(db.Model):
    """Entity mentions within action item descriptions"""

    __tablename__ = "action_item_mentions"

    id = db.Column(db.Integer, primary_key=True)
    action_item_id = db.Column(db.Integer, db.ForeignKey("action_items.id", ondelete="CASCADE"), nullable=False)

    # Entity reference
    entity_type = db.Column(
        Enum("space", "challenge", "initiative", "system", "kpi", name="action_item_mention_entity_type"),
        nullable=False,
    )
    entity_id = db.Column(db.Integer, nullable=False)
    mention_text = db.Column(db.String(255), nullable=False)  # What was typed, e.g. "@Energy Efficiency"

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    action_item = db.relationship("ActionItem", back_populates="mentions")

    def __repr__(self):
        return f"<ActionItemMention {self.id}: {self.entity_type}#{self.entity_id}>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "action_item_id": self.action_item_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "mention_text": self.mention_text,
            "created_at": self.created_at.isoformat(),
        }

    def get_entity_url(self):
        """Get URL for the mentioned entity"""
        from flask import url_for

        url_map = {
            "space": lambda: url_for("workspace.index", space_id=self.entity_id),
            "challenge": lambda: url_for("workspace.index", challenge_id=self.entity_id),
            "initiative": lambda: url_for("workspace.index", initiative_id=self.entity_id),
            "system": lambda: url_for("workspace.index", system_id=self.entity_id),
            "kpi": lambda: url_for("workspace.index", kpi_id=self.entity_id),
        }

        return url_map.get(self.entity_type, lambda: "#")()
