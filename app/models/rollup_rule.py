"""
RollupRule model
"""

from datetime import datetime

from app.extensions import db


class RollupRule(db.Model):
    """
    Roll-up configuration for value types moving upward through the hierarchy.

    Roll-up settings are context-specific:
    - System → Initiative: configured on InitiativeSystemLink
    - Initiative → Challenge: configured on ChallengeInitiativeLink
    - Challenge → Space: configured on Challenge itself

    Each rule specifies:
    - Which value type rolls up
    - Whether roll-up is enabled
    - Which formula to use (or default)
    """

    __tablename__ = "rollup_rules"

    # Source types
    SOURCE_INITIATIVE_SYSTEM = "initiative_system"
    SOURCE_CHALLENGE_INITIATIVE = "challenge_initiative"
    SOURCE_CHALLENGE = "challenge"

    SOURCE_TYPES = [SOURCE_INITIATIVE_SYSTEM, SOURCE_CHALLENGE_INITIATIVE, SOURCE_CHALLENGE]

    # Formula overrides (same as ValueType formulas)
    FORMULA_DEFAULT = "default"
    FORMULA_SUM = "sum"
    FORMULA_MIN = "min"
    FORMULA_MAX = "max"
    FORMULA_AVG = "avg"

    FORMULAS = [FORMULA_DEFAULT, FORMULA_SUM, FORMULA_MIN, FORMULA_MAX, FORMULA_AVG]

    id = db.Column(db.Integer, primary_key=True)
    source_type = db.Column(
        db.String(50), nullable=False, comment="initiative_system, challenge_initiative, or challenge"
    )
    source_id = db.Column(
        db.Integer, nullable=False, comment="ID of InitiativeSystemLink, ChallengeInitiativeLink, or Challenge"
    )
    value_type_id = db.Column(db.Integer, db.ForeignKey("value_types.id", ondelete="CASCADE"), nullable=False)
    rollup_enabled = db.Column(db.Boolean, default=False, nullable=False)
    formula_override = db.Column(
        db.String(20), nullable=True, default=FORMULA_DEFAULT, comment="default, sum, min, max, or avg"
    )

    # Display scale for rollup values (v1.29.0) - independent from KPI display scale
    display_scale = db.Column(
        db.String(20),
        nullable=True,
        default=None,
        comment="Display scale for rollup: inherit, default, thousands, millions",
    )
    display_decimals = db.Column(
        db.Integer, nullable=True, comment="Number of decimals for rollup display (overrides value_type decimals)"
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite index for lookups
    __table_args__ = (db.Index("idx_rollup_source", "source_type", "source_id", "value_type_id"),)

    # Relationships
    value_type = db.relationship("ValueType", back_populates="rollup_rules")

    def get_formula(self):
        """Get the effective formula (returns the value type default if override is 'default')"""
        if self.formula_override == self.FORMULA_DEFAULT or not self.formula_override:
            return self.value_type.default_aggregation_formula
        return self.formula_override

    def get_scale_divisor(self):
        """Get the divisor for the display scale"""
        if self.display_scale == "thousands":
            return 1000
        elif self.display_scale == "millions":
            return 1000000
        else:
            return 1

    def get_scale_suffix(self):
        """Get the suffix for the display scale"""
        if self.display_scale == "thousands":
            return "k"
        elif self.display_scale == "millions":
            return "M"
        else:
            return ""

    def format_display_value(self, value):
        """Format a value for rollup display with the configured scale"""
        if value is None or not self.value_type.is_numeric():
            return value

        try:
            numeric_value = float(value)
            divisor = self.get_scale_divisor()
            scaled_value = numeric_value / divisor

            # Use rollup-specific decimals or value_type decimal places
            decimal_places = (
                self.display_decimals
                if self.display_decimals is not None
                else (self.value_type.decimal_places if self.value_type.decimal_places is not None else 2)
            )

            # If it's integer format and scale is default, show as integer
            if self.value_type.numeric_format == "integer" and self.display_scale in [None, "default"]:
                return int(round(scaled_value))
            else:
                return round(scaled_value, decimal_places)
        except (ValueError, TypeError):
            return value

    def get_value_color(self, value):
        """Get color for a numeric value based on its sign (delegates to default colors)"""
        if not self.value_type.is_numeric() or value is None:
            return None

        try:
            numeric_value = float(value)
            if numeric_value > 0:
                return "#28a745"  # green
            elif numeric_value < 0:
                return "#dc3545"  # red
            else:
                return "#6c757d"  # gray
        except (ValueError, TypeError):
            return None

    def __repr__(self):
        return f"<RollupRule {self.source_type}:{self.source_id} value_type_id={self.value_type_id}>"
