"""
Impact Level model — configurable 3-level impact scale per organization.
"""

from app.extensions import db


class ImpactLevel(db.Model):
    """
    3 fixed impact levels per organization (level 1, 2, 3).
    Each has a customizable label, icon, weight, and color.
    """

    __tablename__ = "impact_levels"
    __table_args__ = (
        db.UniqueConstraint("organization_id", "level", name="uq_impact_level_org_level"),
    )

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    level = db.Column(db.Integer, nullable=False, comment="1, 2, or 3")
    label = db.Column(db.String(50), nullable=False, comment="e.g., Low, Medium, High")
    icon = db.Column(db.String(50), nullable=True, comment="Bootstrap icon class or emoji")
    weight = db.Column(db.Integer, nullable=False, default=1, comment="Integer weight for rollup")
    color = db.Column(db.String(7), nullable=False, default="#3b82f6")

    organization = db.relationship("Organization", backref=db.backref("impact_levels", passive_deletes=True))

    def __repr__(self):
        return f"<ImpactLevel {self.level}: {self.label} (w={self.weight})>"

    @staticmethod
    def get_org_levels(organization_id):
        """Return dict {1: {label, icon, weight, color}, 2: ..., 3: ...} for an org."""
        levels = ImpactLevel.query.filter_by(organization_id=organization_id).order_by(ImpactLevel.level).all()
        return {lv.level: {"label": lv.label, "icon": lv.icon, "weight": lv.weight, "color": lv.color} for lv in levels}

    @staticmethod
    def ensure_defaults(organization_id):
        """Create default impact levels if none exist for this org."""
        existing = ImpactLevel.query.filter_by(organization_id=organization_id).count()
        if existing:
            return
        defaults = [
            {"level": 1, "label": "Low", "icon": "★", "weight": 1, "color": "#94a3b8"},
            {"level": 2, "label": "Medium", "icon": "★★", "weight": 3, "color": "#f59e0b"},
            {"level": 3, "label": "High", "icon": "★★★", "weight": 5, "color": "#ef4444"},
        ]
        for d in defaults:
            db.session.add(ImpactLevel(organization_id=organization_id, **d))
        db.session.flush()
