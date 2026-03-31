"""
Rollup Cache — pre-computed rollup values for fast workspace loading.

When pre-compute rollups is enabled (Super Admin setting), workspace reads
from this table instead of computing aggregations on the fly.
"""

from datetime import datetime

from app.extensions import db


class RollupCacheEntry(db.Model):
    """Pre-computed rollup value for a specific (entity, value_type) pair."""

    __tablename__ = "rollup_cache"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Entity identification
    entity_type = db.Column(db.String(20), nullable=False, index=True)  # space, challenge, initiative, system, kpi
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    value_type_id = db.Column(db.Integer, db.ForeignKey("value_types.id", ondelete="CASCADE"), nullable=False, index=True)

    # Computed values (mirrors what _build_workspace_data produces)
    value = db.Column(db.Float, nullable=True)  # The numeric/consensus value
    formatted_value = db.Column(db.String(100), nullable=True)  # Display-formatted string
    unit_label = db.Column(db.String(50), nullable=True)
    color = db.Column(db.String(20), nullable=True)  # Hex color for display
    formula = db.Column(db.String(20), nullable=True)  # Aggregation formula used (sum, avg, max, etc.)
    is_complete = db.Column(db.Boolean, default=False)  # All children contributed?
    count_total = db.Column(db.Integer, default=0)  # Total children
    count_included = db.Column(db.Integer, default=0)  # Children with data

    # For list value types
    list_label = db.Column(db.String(200), nullable=True)
    list_color = db.Column(db.String(20), nullable=True)

    # For KPI-level entries (consensus data)
    consensus_status = db.Column(db.String(20), nullable=True)  # strong, weak, no_consensus, no_data
    consensus_count = db.Column(db.Integer, nullable=True)
    calculation_type = db.Column(db.String(20), nullable=True)  # manual, linked, formula
    has_target = db.Column(db.Boolean, default=False)
    target_value_formatted = db.Column(db.String(100), nullable=True)
    target_date = db.Column(db.String(20), nullable=True)
    target_direction = db.Column(db.String(20), nullable=True)
    target_progress = db.Column(db.Integer, nullable=True)
    target_color = db.Column(db.String(20), nullable=True)
    comments_tooltip = db.Column(db.Text, nullable=True)

    # Metadata
    computed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Unique constraint: one cache entry per (org, entity_type, entity_id, value_type)
    __table_args__ = (
        db.UniqueConstraint("organization_id", "entity_type", "entity_id", "value_type_id", name="uq_rollup_cache_entity_vt"),
        db.Index("ix_rollup_cache_org_entity", "organization_id", "entity_type", "entity_id"),
    )

    def __repr__(self):
        return f"<RollupCacheEntry {self.entity_type}:{self.entity_id} vt:{self.value_type_id}>"
