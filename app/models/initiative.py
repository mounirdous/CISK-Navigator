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
    logo_data = db.Column(db.LargeBinary, nullable=True, comment="Logo image binary data")
    logo_mime_type = db.Column(db.String(50), nullable=True, comment="Logo MIME type")

    # Initiative Form Fields (v1.19.0)
    mission = db.Column(db.Text, nullable=True, comment="Mission/objectives of the initiative")
    success_criteria = db.Column(db.Text, nullable=True, comment="Success criteria and metrics")
    responsible_person = db.Column(db.String(200), nullable=True, comment="Person responsible for the initiative")
    team_members = db.Column(db.Text, nullable=True, comment="Team members involved (one per line)")
    handover_organization = db.Column(db.String(200), nullable=True, comment="Handover organization/department")
    deliverables = db.Column(db.Text, nullable=True, comment="Deliverables and milestones (JSON format)")
    group_label = db.Column(db.String(1), nullable=True, comment="Group label for filtering (A, B, C, or D)")

    # Impact Assessment (v1.32.0 — legacy)
    impact_on_challenge = db.Column(
        db.String(20),
        nullable=True,
        default="not_assessed",
        comment="Legacy: not_assessed, low, medium, high, no_consensus",
    )
    impact_rationale = db.Column(
        db.Text, nullable=True, comment="Rationale and opinions about the impact assessment"
    )

    # Impact Level (v4.6.0 — new configurable system)
    impact_level = db.Column(db.Integer, nullable=True, comment="1/2/3 = org impact levels, NULL = not assessed")

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship("Organization", back_populates="initiatives")
    progress_updates = db.relationship(
        "InitiativeProgressUpdate",
        back_populates="initiative",
        cascade="all, delete-orphan",
        order_by="InitiativeProgressUpdate.created_at.desc()",
    )
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
        """Get a representative config for coloring and scaling rollups

        Returns RollupRule if display_scale is configured, or inherits from System level
        """
        from app.models import RollupRule

        # First check if there's a rollup rule with display_scale set on any challenge link
        for challenge_link in self.challenge_links:
            rollup_rule = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE,
                source_id=challenge_link.id,
                value_type_id=value_type_id,
            ).first()

            if rollup_rule and rollup_rule.display_scale:
                return rollup_rule

            # If rollup_rule exists but display_scale is None (inherit mode),
            # delegate to System level
            if rollup_rule and rollup_rule.display_scale is None:
                # Get config from first system link (they should all have same config if inherit is set)
                if self.system_links:
                    first_sys_link = self.system_links[0]
                    return first_sys_link.get_color_config(value_type_id)

        # Fall back to KPI config (legacy behavior)
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
            self.impact_rationale,
        ]
        filled = sum(1 for field in form_fields if field and field.strip())
        # Impact level counts as a separate field (integer, not string)
        if self.impact_level is not None:
            filled += 1
        total = len(form_fields) + 1

        if filled == 0:
            status = "empty"
        elif filled == total:
            status = "complete"
        else:
            status = "partial"

        return (filled, total, status)

    @property
    def latest_progress_update(self):
        return self.progress_updates[0] if self.progress_updates else None

    @property
    def execution_rag(self):
        """Latest RAG status, or None if never updated."""
        upd = self.latest_progress_update
        return upd.rag_status if upd else None

    @property
    def days_since_execution_update(self):
        upd = self.latest_progress_update
        if not upd:
            return None
        return (datetime.utcnow() - upd.created_at).days

    def __repr__(self):
        return f"<Initiative {self.name}>"


class InitiativeProgressUpdate(db.Model):
    """
    Periodic progress update for an initiative (execution tracking).

    Captures a manual RAG status + narrative at a point in time,
    building a chronological log of how execution is progressing.
    """

    __tablename__ = "initiative_progress_updates"

    id = db.Column(db.Integer, primary_key=True)
    initiative_id = db.Column(
        db.Integer, db.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rag_status = db.Column(db.String(10), nullable=False)  # green | amber | red
    accomplishments = db.Column(db.Text, nullable=True)
    next_steps = db.Column(db.Text, nullable=True)
    blockers = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    initiative = db.relationship("Initiative", back_populates="progress_updates")
    author = db.relationship("User", foreign_keys=[created_by])

    @property
    def days_ago(self):
        return (datetime.utcnow() - self.created_at).days

    @property
    def freshness_class(self):
        """CSS class based on staleness: fresh / aging / stale"""
        d = self.days_ago
        if d <= 7:
            return "fresh"
        elif d <= 21:
            return "aging"
        return "stale"

    def __repr__(self):
        return f"<InitiativeProgressUpdate initiative_id={self.initiative_id} rag={self.rag_status}>"


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
