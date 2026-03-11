"""
Space model
"""

from datetime import datetime

from app.extensions import db


class Space(db.Model):
    """
    Space model.

    A space is a flexible grouping concept such as season, site, customer, supplier, etc.
    It belongs to one organization and contains challenges.
    """

    __tablename__ = "spaces"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    space_label = db.Column(db.String(100), nullable=True, comment="e.g., Season, Site, Customer, Supplier")
    display_order = db.Column(db.Integer, default=0, nullable=False)
    is_private = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="Private spaces are only visible to users with appropriate permissions",
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship("Organization", back_populates="spaces")
    challenges = db.relationship(
        "Challenge", back_populates="space", cascade="all, delete-orphan", order_by="Challenge.display_order"
    )

    def get_rollup_value(self, value_type_id):
        """Get rolled-up value from challenges for this space"""
        from app.services import AggregationService

        try:
            result = AggregationService.get_challenge_to_space_rollup(self.id, value_type_id)
            return result
        except Exception:
            return None

    def get_color_config(self, value_type_id):
        """Get a representative KPIValueTypeConfig for coloring and scaling rollups

        Returns the config with the largest display scale (millions > thousands > default)
        to ensure rollups show appropriate precision
        """
        scale_priority = {"millions": 3, "thousands": 2, "default": 1, None: 0}
        best_config = None
        best_scale = 0

        for challenge in self.challenges:
            for init_link in challenge.initiative_links:
                for sys_link in init_link.initiative.system_links:
                    for kpi in sys_link.kpis:
                        for config in kpi.value_type_configs:
                            if config.value_type_id == value_type_id:
                                current_scale = scale_priority.get(config.display_scale, 0)
                                if current_scale > best_scale:
                                    best_scale = current_scale
                                    best_config = config
                                elif not best_config:
                                    best_config = config

        return best_config

    def __repr__(self):
        return f"<Space {self.name}>"
