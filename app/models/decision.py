"""
Standalone Decision model — decisions created outside of initiative progress updates.
"""

from datetime import datetime

from app.extensions import db


class Decision(db.Model):
    """A standalone decision, not tied to a progress update."""

    __tablename__ = "decisions"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    what = db.Column(db.Text, nullable=False, comment="Decision description")
    who = db.Column(db.String(200), nullable=True, comment="Decision maker / owner")
    tags = db.Column(db.JSON, nullable=True, comment="Tag categories: ['scope', 'budget', ...]")
    entity_mentions = db.Column(db.JSON, nullable=True, comment="[{entity_type, entity_id, entity_name}]")
    governance_body_id = db.Column(db.Integer, db.ForeignKey("governance_bodies.id", ondelete="SET NULL"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship("Organization")
    created_by = db.relationship("User")
    governance_body = db.relationship("GovernanceBody")

    def mentions_entity(self, entity_type, entity_id):
        """Check if this decision mentions a specific entity."""
        if not self.entity_mentions:
            return False
        return any(
            m.get("entity_type") == entity_type and m.get("entity_id") == entity_id
            for m in self.entity_mentions
        )

    def __repr__(self):
        return f"<Decision {self.id}: {self.what[:50]}>"
