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
    logo_data = db.Column(db.LargeBinary, nullable=True, comment="Logo image binary data")
    logo_mime_type = db.Column(db.String(50), nullable=True, comment="Logo MIME type")
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
        """Get a representative config for coloring and scaling rollups

        Returns RollupRule if display_scale is configured, or inherits from Initiative level
        """
        from app.models import RollupRule

        # First check if there's a rollup rule with display_scale set for this challenge
        rollup_rule = RollupRule.query.filter_by(
            source_type=RollupRule.SOURCE_CHALLENGE, source_id=self.id, value_type_id=value_type_id
        ).first()

        if rollup_rule and rollup_rule.display_scale:
            return rollup_rule

        # If rollup_rule exists but display_scale is None (inherit mode),
        # delegate to Initiative level to get their effective config
        if rollup_rule and rollup_rule.display_scale is None:
            # Get config from first initiative (they should all have same config if inherit is set)
            if self.initiative_links:
                first_initiative = self.initiative_links[0].initiative
                return first_initiative.get_color_config(value_type_id)

        # Fall back to KPI config (legacy behavior - when no rollup rule exists at all)
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
