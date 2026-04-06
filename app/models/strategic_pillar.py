"""
Strategic Pillar model
"""

from datetime import datetime

from app.extensions import db


class StrategicPillar(db.Model):
    """
    Strategic Pillar — one pillar of the organization's strategy.

    Each pillar has a name, description (bullet points as lines),
    an optional image or Bootstrap icon, and an accent color.
    """

    __tablename__ = "strategic_pillars"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True, comment="Bullet points (one per line)")
    display_order = db.Column(db.Integer, default=0, nullable=False)
    accent_color = db.Column(db.String(7), nullable=False, default="#3b82f6")

    # Icon: either an uploaded image or a Bootstrap icon class
    icon_data = db.Column(db.LargeBinary, nullable=True, comment="Uploaded icon/image binary")
    icon_mime_type = db.Column(db.String(50), nullable=True)
    bs_icon = db.Column(db.String(50), nullable=True, comment="Bootstrap icon class e.g. bi-rocket-takeoff")

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship("Organization", backref=db.backref("strategic_pillars", passive_deletes=True))

    def __repr__(self):
        return f"<StrategicPillar {self.name}>"

    def get_bullets(self):
        """Return description as a list of bullet points"""
        if not self.description:
            return []
        return [line.strip() for line in self.description.strip().split("\n") if line.strip()]

    def get_icon_url(self):
        """Return data URL for uploaded icon, or None"""
        if self.icon_data and self.icon_mime_type:
            import base64

            return f"data:{self.icon_mime_type};base64,{base64.b64encode(self.icon_data).decode('utf-8')}"
        return None
