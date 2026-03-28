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
    logo_data = db.Column(db.LargeBinary, nullable=True, comment="Logo image binary data")
    logo_mime_type = db.Column(db.String(50), nullable=True, comment="Logo MIME type")
    space_label = db.Column(db.String(100), nullable=True, comment="e.g., Season, Site, Customer, Supplier")
    display_order = db.Column(db.Integer, default=0, nullable=False)
    impact_level = db.Column(db.Integer, nullable=True, comment="1/2/3 = org impact levels, NULL = not assessed")
    is_private = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="Private spaces are only visible to users with appropriate permissions",
    )
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this space (owner for private spaces)",
    )

    # SWOT Analysis
    swot_strengths = db.Column(db.Text, nullable=True, comment="SWOT: Internal positive attributes")
    swot_weaknesses = db.Column(db.Text, nullable=True, comment="SWOT: Internal negative attributes")
    swot_opportunities = db.Column(db.Text, nullable=True, comment="SWOT: External positive factors")
    swot_threats = db.Column(db.Text, nullable=True, comment="SWOT: External negative factors")

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship("Organization", back_populates="spaces")
    creator = db.relationship("User", foreign_keys=[created_by])
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
        """Get a representative config for coloring and scaling rollups

        Returns RollupRule if display_scale is configured, or inherits from Challenge level
        """
        from app.models import RollupRule

        # First check if there's a rollup rule with display_scale set on any challenge
        for challenge in self.challenges:
            rollup_rule = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_CHALLENGE, source_id=challenge.id, value_type_id=value_type_id
            ).first()

            if rollup_rule and rollup_rule.display_scale:
                return rollup_rule

            # If rollup_rule exists but display_scale is None (inherit mode),
            # return challenge's effective config (which will delegate further if needed)
            if rollup_rule and rollup_rule.display_scale is None:
                return challenge.get_color_config(value_type_id)

        # Fall back to KPI config (legacy behavior)
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

    def get_swot_completion(self):
        """Get SWOT completion status

        Returns:
            tuple: (filled_count, total_count, completion_status)
            completion_status: 'empty', 'partial', 'complete'
        """
        swot_fields = [
            self.swot_strengths,
            self.swot_weaknesses,
            self.swot_opportunities,
            self.swot_threats,
        ]
        filled = sum(1 for field in swot_fields if field and field.strip())
        total = len(swot_fields)

        if filled == 0:
            status = "empty"
        elif filled == total:
            status = "complete"
        else:
            status = "partial"

        return (filled, total, status)

    def __repr__(self):
        return f"<Space {self.name}>"
