"""
KPI Snapshot Model

Stores historical snapshots of KPI consensus values for time-series tracking.
"""

from datetime import date, datetime
from decimal import Decimal

from app.extensions import db


class KPISnapshot(db.Model):
    """
    Historical snapshot of a KPI value at a specific point in time.

    Snapshots capture the consensus state of a KPI-ValueType cell,
    allowing historical tracking and trend analysis.
    """

    __tablename__ = "kpi_snapshots"

    id = db.Column(db.Integer, primary_key=True)

    # Link to KPI-ValueType configuration
    kpi_value_type_config_id = db.Column(
        db.Integer, db.ForeignKey("kpi_value_type_configs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Snapshot metadata
    snapshot_date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    snapshot_label = db.Column(db.String(100))  # Optional: "Q1 2026", "Baseline", "End of Season 1"

    # Batch tracking - groups all KPIs/rollups created in same snapshot operation
    snapshot_batch_id = db.Column(db.String(36), nullable=False, index=True)

    # Privacy and ownership
    is_public = db.Column(db.Boolean, default=True, nullable=False, index=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Snapshot data (denormalized for historical preservation)
    consensus_status = db.Column(db.String(50), nullable=False)  # 'strong_consensus', 'weak_consensus', etc.
    consensus_value = db.Column(db.Numeric(precision=20, scale=6))  # Numeric value
    qualitative_level = db.Column(db.Integer)  # For qualitative types (1, 2, 3)
    contributor_count = db.Column(db.Integer, default=0)
    is_rollup_eligible = db.Column(db.Boolean, default=False)

    # Optional: Store contributing values for analysis
    contributing_values = db.Column(db.JSON)  # Array of values that formed consensus

    # Notes about this snapshot
    notes = db.Column(db.Text)

    # Relationships
    config = db.relationship("KPIValueTypeConfig", back_populates="snapshots")
    created_by = db.relationship("User", foreign_keys=[created_by_user_id], backref="created_snapshots")
    owner = db.relationship("User", foreign_keys=[owner_user_id], backref="owned_snapshots")

    # Indexes for efficient querying
    __table_args__ = (
        db.Index("idx_snapshot_config_date", "kpi_value_type_config_id", "snapshot_date"),
        db.Index("idx_snapshot_date", "snapshot_date"),
    )

    def __repr__(self):
        return f"<KPISnapshot {self.id} config={self.kpi_value_type_config_id} date={self.snapshot_date}>"

    def get_value(self):
        """Get the appropriate value (numeric or qualitative)"""
        if self.consensus_value is not None:
            return float(self.consensus_value)
        return self.qualitative_level

    def to_dict(self):
        """Convert snapshot to dictionary for API responses"""
        return {
            "id": self.id,
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "snapshot_label": self.snapshot_label,
            "consensus_status": self.consensus_status,
            "consensus_value": float(self.consensus_value) if self.consensus_value else None,
            "qualitative_level": self.qualitative_level,
            "contributor_count": self.contributor_count,
            "is_rollup_eligible": self.is_rollup_eligible,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "snapshot_batch_id": self.snapshot_batch_id,
            "is_public": self.is_public,
            "owner_user_id": self.owner_user_id,
        }


class RollupSnapshot(db.Model):
    """
    Historical snapshot of rollup values at Space/Challenge/Initiative/System levels.

    Stores aggregated values at higher hierarchy levels for historical tracking.
    """

    __tablename__ = "rollup_snapshots"

    id = db.Column(db.Integer, primary_key=True)

    # Snapshot metadata
    snapshot_date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    snapshot_label = db.Column(db.String(100))

    # Batch tracking - groups all KPIs/rollups created in same snapshot operation
    snapshot_batch_id = db.Column(db.String(36), nullable=False, index=True)

    # Privacy and ownership
    is_public = db.Column(db.Boolean, default=True, nullable=False, index=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Entity being tracked (polymorphic)
    entity_type = db.Column(db.String(50), nullable=False)  # 'space', 'challenge', 'initiative', 'system'
    entity_id = db.Column(db.Integer, nullable=False)
    value_type_id = db.Column(db.Integer, db.ForeignKey("value_types.id"), nullable=False)

    # Rollup data
    rollup_value = db.Column(db.Numeric(precision=20, scale=6))
    qualitative_level = db.Column(db.Integer)
    is_complete = db.Column(db.Boolean, default=False)  # All children had values?
    child_count = db.Column(db.Integer, default=0)  # How many children contributed

    # Relationships
    value_type = db.relationship("ValueType", backref="rollup_snapshots")
    owner = db.relationship("User", foreign_keys=[owner_user_id], backref="owned_rollup_snapshots")

    # Indexes
    __table_args__ = (
        db.Index("idx_rollup_entity_date", "entity_type", "entity_id", "value_type_id", "snapshot_date"),
        db.Index("idx_rollup_date", "snapshot_date"),
    )

    def __repr__(self):
        return f"<RollupSnapshot {self.entity_type}:{self.entity_id} vt={self.value_type_id} date={self.snapshot_date}>"

    def get_value(self):
        """Get the appropriate value"""
        if self.rollup_value is not None:
            return float(self.rollup_value)
        return self.qualitative_level

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "snapshot_label": self.snapshot_label,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "value_type_id": self.value_type_id,
            "rollup_value": float(self.rollup_value) if self.rollup_value else None,
            "qualitative_level": self.qualitative_level,
            "is_complete": self.is_complete,
            "child_count": self.child_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "snapshot_batch_id": self.snapshot_batch_id,
            "is_public": self.is_public,
            "owner_user_id": self.owner_user_id,
        }
