"""
Initiative models
"""

from datetime import datetime

from app.extensions import db


class Initiative(db.Model):
    """
    Initiative model.

    Initiatives are organization-level objects that can be reused across multiple challenges.
    They are linked to challenges via ChallengeInitiativeLink.
    They are linked to systems via InitiativeSystemLink.
    """

    __tablename__ = "initiatives"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Initiative Form Fields (v1.19.0)
    mission = db.Column(db.Text, nullable=True, comment="Mission/objectives of the initiative")
    success_criteria = db.Column(db.Text, nullable=True, comment="Success criteria and metrics")
    responsible_person = db.Column(db.String(200), nullable=True, comment="Person responsible for the initiative")
    team_members = db.Column(db.Text, nullable=True, comment="Team members involved (one per line)")
    handover_organization = db.Column(db.String(200), nullable=True, comment="Handover organization/department")
    deliverables = db.Column(db.Text, nullable=True, comment="Deliverables and milestones (JSON format)")
    group_label = db.Column(db.String(1), nullable=True, comment="Group label for filtering (A, B, C, or D)")

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship("Organization", back_populates="initiatives")
    challenge_links = db.relationship(
        "ChallengeInitiativeLink", back_populates="initiative", cascade="all, delete-orphan"
    )
    system_links = db.relationship(
        "InitiativeSystemLink",
        back_populates="initiative",
        cascade="all, delete-orphan",
        order_by="InitiativeSystemLink.display_order",
    )

    def get_rollup_value(self, value_type_id):
        """Get rolled-up value from systems for this initiative"""
        from app.services import AggregationService

        try:
            result = AggregationService.get_system_to_initiative_rollup(self.id, value_type_id)
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

        for sys_link in self.system_links:
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

    def get_form_completion(self):
        """Get initiative form completion status

        Returns:
            tuple: (filled_count, total_count, completion_status)
            completion_status: 'empty', 'partial', 'complete'
        """
        form_fields = [
            self.mission,
            self.success_criteria,
            self.responsible_person,
            self.team_members,
            self.handover_organization,
            self.deliverables,
        ]
        filled = sum(1 for field in form_fields if field and field.strip())
        total = len(form_fields)

        if filled == 0:
            status = "empty"
        elif filled == total:
            status = "complete"
        else:
            status = "partial"

        return (filled, total, status)

    def __repr__(self):
        return f"<Initiative {self.name}>"


class ChallengeInitiativeLink(db.Model):
    """
    Link between a Challenge and an Initiative.

    One initiative can address multiple challenges.
    Roll-up configuration from initiative to challenge is stored here.
    """

    __tablename__ = "challenge_initiative_links"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    initiative_id = db.Column(db.Integer, db.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Unique constraint: same initiative cannot be linked twice to the same challenge
    __table_args__ = (db.UniqueConstraint("challenge_id", "initiative_id", name="uq_challenge_initiative"),)

    # Relationships
    challenge = db.relationship("Challenge", back_populates="initiative_links")
    initiative = db.relationship("Initiative", back_populates="challenge_links")
    rollup_rules = db.relationship(
        "RollupRule",
        foreign_keys="RollupRule.source_id",
        primaryjoin="and_(RollupRule.source_id==ChallengeInitiativeLink.id, "
        'RollupRule.source_type=="challenge_initiative")',
        cascade="all, delete-orphan",
        viewonly=True,
    )

    def __repr__(self):
        return f"<ChallengeInitiativeLink challenge_id={self.challenge_id} initiative_id={self.initiative_id}>"
