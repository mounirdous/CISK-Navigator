"""
Challenge model
"""

from datetime import datetime

from app.extensions import db


class Challenge(db.Model):
    """
    Challenge model.

    A challenge belongs to one space and one organization.
    Challenges can be linked to multiple initiatives via ChallengeInitiativeLink.
    """

    __tablename__ = "challenges"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    space_id = db.Column(db.Integer, db.ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship("Organization", back_populates="challenges")
    space = db.relationship("Space", back_populates="challenges")
    initiative_links = db.relationship(
        "ChallengeInitiativeLink",
        back_populates="challenge",
        cascade="all, delete-orphan",
        order_by="ChallengeInitiativeLink.display_order",
    )
    rollup_rules = db.relationship(
        "RollupRule",
        foreign_keys="RollupRule.source_id",
        primaryjoin="and_(RollupRule.source_id==Challenge.id, " 'RollupRule.source_type=="challenge")',
        cascade="all, delete-orphan",
        viewonly=True,
    )

    def get_rollup_value(self, value_type_id):
        """Get rolled-up value from initiatives for this challenge"""
        from app.services import AggregationService

        try:
            result = AggregationService.get_initiative_to_challenge_rollup(self.id, value_type_id)
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

        for init_link in self.initiative_links:
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
        return f"<Challenge {self.name}>"
