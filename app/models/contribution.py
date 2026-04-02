"""
Contribution model
"""

from datetime import datetime

from app.extensions import db


class Contribution(db.Model):
    """
    Contribution model for consensus-based data entry.

    Each contribution represents one contributor's opinion for a specific KPI/value-type cell.
    Final cell values are derived from contributor consensus.

    Contributors are identified by free-text names (no user account required).
    """

    __tablename__ = "contributions"

    id = db.Column(db.Integer, primary_key=True)
    kpi_value_type_config_id = db.Column(
        db.Integer, db.ForeignKey("kpi_value_type_configs.id", ondelete="CASCADE"), nullable=False
    )
    contributor_name = db.Column(db.String(200), nullable=False, comment="Free text, e.g., Simon, Paul, Jacques")
    stakeholder_id = db.Column(
        db.Integer, db.ForeignKey("stakeholders.id", ondelete="SET NULL"), nullable=True,
        comment="Optional link to stakeholder record for traceability"
    )
    numeric_value = db.Column(db.Numeric(precision=20, scale=6), nullable=True, comment="For numeric value types")
    qualitative_level = db.Column(db.Integer, nullable=True, comment="1, 2, or 3 for qualitative value types")
    list_value = db.Column(db.String(255), nullable=True, comment="Selected option key for list value types")
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    kpi_value_type_config = db.relationship("KPIValueTypeConfig", back_populates="contributions")
    stakeholder = db.relationship("Stakeholder", backref="contributions", foreign_keys=[stakeholder_id])

    def __repr__(self):
        return f"<Contribution {self.contributor_name} for config_id={self.kpi_value_type_config_id}>"
