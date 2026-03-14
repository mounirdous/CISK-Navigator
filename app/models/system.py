"""
System models
"""

from datetime import datetime

from app.extensions import db


class System(db.Model):
    """
    System model.

    Systems are organization-level objects that can be reused across multiple initiatives.
    They are linked to initiatives via InitiativeSystemLink.
    """

    __tablename__ = "systems"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    logo_data = db.Column(db.LargeBinary, nullable=True, comment="Logo image binary data")
    logo_mime_type = db.Column(db.String(50), nullable=True, comment="Logo MIME type")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship("Organization", back_populates="systems")
    initiative_links = db.relationship("InitiativeSystemLink", back_populates="system", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<System {self.name}>"


class InitiativeSystemLink(db.Model):
    """
    Link between an Initiative and a System.

    One system can address multiple initiatives.
    KPIs belong to this context, not to the master System.
    Roll-up configuration from system to initiative is stored here.
    """

    __tablename__ = "initiative_system_links"

    id = db.Column(db.Integer, primary_key=True)
    initiative_id = db.Column(db.Integer, db.ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False)
    system_id = db.Column(db.Integer, db.ForeignKey("systems.id", ondelete="CASCADE"), nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Unique constraint: same system cannot be linked twice to the same initiative
    __table_args__ = (db.UniqueConstraint("initiative_id", "system_id", name="uq_initiative_system"),)

    # Relationships
    initiative = db.relationship("Initiative", back_populates="system_links")
    system = db.relationship("System", back_populates="initiative_links")
    kpis = db.relationship(
        "KPI", back_populates="initiative_system_link", cascade="all, delete-orphan", order_by="KPI.display_order"
    )
    rollup_rules = db.relationship(
        "RollupRule",
        foreign_keys="RollupRule.source_id",
        primaryjoin="and_(RollupRule.source_id==InitiativeSystemLink.id, "
        'RollupRule.source_type=="initiative_system")',
        cascade="all, delete-orphan",
        viewonly=True,
    )

    def get_rollup_value(self, value_type_id):
        """Get rolled-up value from KPIs for this system-initiative link"""
        from app.services import AggregationService

        try:
            result = AggregationService.get_kpi_to_system_rollup(self, value_type_id)
            return result
        except Exception:
            return None

    def get_color_config(self, value_type_id):
        """Get a representative config for coloring and scaling rollups

        Returns RollupRule if display_scale is configured, otherwise falls back to
        KPIValueTypeConfig with the largest display scale
        """
        from app.models import RollupRule

        # First check if there's a rollup rule with display_scale set
        rollup_rule = RollupRule.query.filter_by(
            source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM, source_id=self.id, value_type_id=value_type_id
        ).first()

        if rollup_rule and rollup_rule.display_scale:
            return rollup_rule

        # Fall back to KPI config (legacy behavior)
        scale_priority = {"millions": 3, "thousands": 2, "default": 1, None: 0}
        best_config = None
        best_scale = 0

        for kpi in self.kpis:
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
        return f"<InitiativeSystemLink initiative_id={self.initiative_id} system_id={self.system_id}>"
