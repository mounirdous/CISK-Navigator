"""
Value Type models
"""

from datetime import datetime

from app.extensions import db


class ValueType(db.Model):
    """
    Value Type model.

    Value types are defined per organization.
    They define what kind of values can be tracked (Cost, CO2, Risk, Impact, etc.).

    Two main families:
    - Numeric: cost, net value, CO2, number of licenses, etc.
    - Qualitative: risk (!, !!, !!!), positive impact (★), negative impact (▼)
    """

    __tablename__ = "value_types"

    # Value type kinds
    KIND_NUMERIC = "numeric"
    KIND_RISK = "risk"
    KIND_POSITIVE_IMPACT = "positive_impact"
    KIND_NEGATIVE_IMPACT = "negative_impact"
    KIND_LEVEL = "level"
    KIND_SENTIMENT = "sentiment"

    KINDS = [KIND_NUMERIC, KIND_RISK, KIND_POSITIVE_IMPACT, KIND_NEGATIVE_IMPACT, KIND_LEVEL, KIND_SENTIMENT]

    # Numeric formats
    FORMAT_INTEGER = "integer"
    FORMAT_DECIMAL = "decimal"

    # Aggregation formulas
    FORMULA_SUM = "sum"
    FORMULA_MIN = "min"
    FORMULA_MAX = "max"
    FORMULA_AVG = "avg"
    FORMULA_MEDIAN = "median"
    FORMULA_COUNT = "count"

    FORMULAS = [FORMULA_SUM, FORMULA_MIN, FORMULA_MAX, FORMULA_AVG, FORMULA_MEDIAN, FORMULA_COUNT]

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(50), nullable=False, comment="numeric, risk, positive_impact, negative_impact")
    numeric_format = db.Column(db.String(20), nullable=True, comment="integer or decimal for numeric types")
    decimal_places = db.Column(db.Integer, nullable=True, default=2)
    unit_label = db.Column(db.String(50), nullable=True, comment="€, tCO2e, licenses, people, etc.")
    default_aggregation_formula = db.Column(db.String(20), nullable=False, default=FORMULA_SUM)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship("Organization", back_populates="value_types")
    kpi_configs = db.relationship(
        "KPIValueTypeConfig",
        foreign_keys="KPIValueTypeConfig.value_type_id",
        back_populates="value_type",
        cascade="all, delete-orphan",
    )
    rollup_rules = db.relationship("RollupRule", back_populates="value_type", cascade="all, delete-orphan")
    rollup_snapshots = db.relationship("RollupSnapshot", back_populates="value_type", cascade="all, delete-orphan")

    def is_numeric(self):
        """Check if this is a numeric value type"""
        return self.kind == self.KIND_NUMERIC

    def is_qualitative(self):
        """Check if this is a qualitative value type"""
        return self.kind in [
            self.KIND_RISK,
            self.KIND_POSITIVE_IMPACT,
            self.KIND_NEGATIVE_IMPACT,
            self.KIND_LEVEL,
            self.KIND_SENTIMENT,
        ]

    @classmethod
    def get_smart_default_formula(cls, kind):
        """Get smart default aggregation formula based on value type kind

        Returns:
            str: Recommended formula for the given kind
        """
        smart_defaults = {
            cls.KIND_NUMERIC: cls.FORMULA_SUM,  # Cost, CO2 → add them up
            cls.KIND_RISK: cls.FORMULA_MAX,  # Risk → worst case
            cls.KIND_POSITIVE_IMPACT: cls.FORMULA_MAX,  # Impact → highest impact
            cls.KIND_NEGATIVE_IMPACT: cls.FORMULA_MAX,  # Negative → worst case
            cls.KIND_LEVEL: cls.FORMULA_MAX,  # Level → highest level
            cls.KIND_SENTIMENT: cls.FORMULA_AVG,  # Sentiment → average mood
        }
        return smart_defaults.get(kind, cls.FORMULA_SUM)

    def get_smart_formula_explanation(self):
        """Get user-friendly explanation of why this formula makes sense"""
        explanations = {
            self.KIND_NUMERIC: f"{self.name} values add up (total {self.unit_label or 'amount'})",
            self.KIND_RISK: f"{self.name} shows worst-case risk across all items",
            self.KIND_POSITIVE_IMPACT: f"{self.name} shows highest positive impact achieved",
            self.KIND_NEGATIVE_IMPACT: f"{self.name} shows worst negative impact",
            self.KIND_LEVEL: f"{self.name} shows highest level reached",
            self.KIND_SENTIMENT: f"{self.name} averages sentiment across all items",
        }
        return explanations.get(self.kind, f"{self.name} aggregates using {self.default_aggregation_formula}")

    @classmethod
    def get_smart_default_formula(cls, kind):
        """
        Get the smart default aggregation formula based on value type kind.

        For qualitative types, SUM doesn't make sense, so we use sensible defaults:
        - risk: MAX (show worst case risk)
        - positive_impact: MAX (show best case impact)
        - negative_impact: MAX (show worst case harm)
        - level: MAX (show highest level achieved)
        - sentiment: AVG (average mood/sentiment)
        - numeric: SUM (default)
        """
        qualitative_defaults = {
            cls.KIND_RISK: cls.FORMULA_MAX,
            cls.KIND_POSITIVE_IMPACT: cls.FORMULA_MAX,
            cls.KIND_NEGATIVE_IMPACT: cls.FORMULA_MAX,
            cls.KIND_LEVEL: cls.FORMULA_MAX,
            cls.KIND_SENTIMENT: cls.FORMULA_AVG,
        }
        return qualitative_defaults.get(kind, cls.FORMULA_SUM)

    def get_valid_formulas(self):
        """
        Get list of valid aggregation formulas for this value type.

        For qualitative types, SUM is not valid (you can't sum risk levels).
        """
        if self.is_numeric():
            # Numeric types can use all formulas
            return [self.FORMULA_SUM, self.FORMULA_MIN, self.FORMULA_MAX, self.FORMULA_AVG]
        else:
            # Qualitative types cannot use SUM
            return [self.FORMULA_MIN, self.FORMULA_MAX, self.FORMULA_AVG]

    def get_display_symbol(self, level):
        """Get display symbol for qualitative types"""
        if self.kind == self.KIND_RISK:
            return "!" * level
        elif self.kind == self.KIND_POSITIVE_IMPACT:
            return "★" * level
        elif self.kind == self.KIND_NEGATIVE_IMPACT:
            return "▼" * level
        return str(level)

    def __repr__(self):
        return f"<ValueType {self.name}>"


class KPIValueTypeConfig(db.Model):
    """
    Configuration of a value type for a specific KPI.

    One KPI can have multiple value types.
    Sign-based colors are configured here (for numeric types only).
    """

    __tablename__ = "kpi_value_type_configs"

    # Calculation types
    CALC_TYPE_MANUAL = "manual"
    CALC_TYPE_LINKED = "linked"
    CALC_TYPE_FORMULA = "formula"

    id = db.Column(db.Integer, primary_key=True)
    kpi_id = db.Column(db.Integer, db.ForeignKey("kpis.id", ondelete="CASCADE"), nullable=False)
    value_type_id = db.Column(db.Integer, db.ForeignKey("value_types.id", ondelete="CASCADE"), nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    color_negative = db.Column(db.String(20), nullable=True, comment="Color for negative values (numeric only)")
    color_zero = db.Column(db.String(20), nullable=True, comment="Color for zero values (numeric only)")
    color_positive = db.Column(db.String(20), nullable=True, comment="Color for positive values (numeric only)")

    # Target tracking (v2.2)
    target_value = db.Column(
        db.Numeric(precision=20, scale=6), nullable=True, comment="Target value to achieve (numeric only)"
    )
    target_date = db.Column(db.Date, nullable=True, comment="Date by which target should be achieved")
    target_direction = db.Column(
        db.String(20),
        nullable=True,
        default="maximize",
        comment="Target direction: maximize (higher is better), minimize (lower is better), or exact (at target)",
    )
    target_tolerance_pct = db.Column(
        db.Integer, nullable=True, default=10, comment="Tolerance percentage for 'exact' target direction"
    )
    baseline_snapshot_id = db.Column(
        db.Integer,
        nullable=True,
        comment="Snapshot ID to use as baseline (no FK constraint to avoid circular dependency)",
    )

    # Display scale (v1.14.6)
    display_scale = db.Column(
        db.String(20), nullable=True, default="default", comment="Display scale: default, thousands, millions"
    )
    display_decimals = db.Column(
        db.Integer, nullable=True, comment="Number of decimals when using display scale (overrides value_type decimals)"
    )

    # Linked KPI Value Support (v1.18.0) - Live read from another org or same org
    linked_source_org_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Source organization for linked KPI values (can be same org or different org)",
    )
    linked_source_kpi_id = db.Column(
        db.Integer,
        db.ForeignKey("kpis.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Source KPI to read values from (deletion blocked while linked)",
    )
    linked_source_value_type_id = db.Column(
        db.Integer,
        db.ForeignKey("value_types.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Source value type to read from (must match type/unit)",
    )

    # Formula calculation support (v1.20.0)
    calculation_type = db.Column(
        db.String(20),
        nullable=False,
        default=CALC_TYPE_MANUAL,
        comment="How value is determined: manual (contributions), linked (from another KPI), formula (calculated)",
    )
    calculation_config = db.Column(
        db.JSON,
        nullable=True,
        comment="Configuration for formula calculations: {operation: sum, kpi_config_ids: [1, 2, 3]}",
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    kpi = db.relationship("KPI", foreign_keys=[kpi_id], back_populates="value_type_configs")
    value_type = db.relationship("ValueType", foreign_keys=[value_type_id], back_populates="kpi_configs")
    contributions = db.relationship(
        "Contribution", back_populates="kpi_value_type_config", cascade="all, delete-orphan"
    )
    snapshots = db.relationship("KPISnapshot", back_populates="config", cascade="all, delete-orphan")

    # Linked KPI relationships (for live value read-through)
    linked_source_org = db.relationship(
        "Organization", foreign_keys=[linked_source_org_id], backref="linked_kpi_consumers"
    )
    linked_source_kpi = db.relationship("KPI", foreign_keys=[linked_source_kpi_id], backref="linked_value_consumers")
    linked_source_value_type = db.relationship(
        "ValueType", foreign_keys=[linked_source_value_type_id], backref="linked_kpi_value_consumers"
    )

    # Baseline snapshot for progress tracking (no FK constraint, just a reference)
    @property
    def baseline_snapshot(self):
        """Get the baseline snapshot if set"""
        if self.baseline_snapshot_id:
            from app.models import KPISnapshot

            return KPISnapshot.query.get(self.baseline_snapshot_id)
        return None

    def is_linked(self):
        """Check if this config is linked to read values from another KPI"""
        return self.calculation_type == self.CALC_TYPE_LINKED or (
            self.linked_source_org_id is not None
            and self.linked_source_kpi_id is not None
            and self.linked_source_value_type_id is not None
        )

    def is_formula(self):
        """Check if this config uses formula calculation"""
        return self.calculation_type == self.CALC_TYPE_FORMULA and self.calculation_config is not None

    def get_formula_source_configs(self):
        """
        Get the list of source KPIValueTypeConfig objects referenced in the formula.
        Returns empty list if not a formula or config is invalid.
        """
        if not self.is_formula():
            return []

        config_ids = self.calculation_config.get("kpi_config_ids", [])
        if not config_ids:
            return []

        # Fetch all configs in one query
        return KPIValueTypeConfig.query.filter(KPIValueTypeConfig.id.in_(config_ids)).all()

    def get_linked_source_config(self):
        """
        Get the source KPIValueTypeConfig that this config is linked to.
        Returns None if not linked.
        """
        if not self.is_linked():
            return None

        # Find the config on the source KPI with the matching value type
        return KPIValueTypeConfig.query.filter_by(
            kpi_id=self.linked_source_kpi_id, value_type_id=self.linked_source_value_type_id
        ).first()

    def get_consensus_value(self, _visited=None):
        """
        Get consensus calculation for this KPI cell.
        Handles manual contributions, linked KPIs, and formula calculations.

        Args:
            _visited: Internal parameter to track visited configs and prevent circular references

        Returns:
            dict with keys: status, value, count, is_rollup_eligible
            OR just the raw value if called recursively within formula calculation
        """
        # Initialize visited set on first call
        if _visited is None:
            _visited = set()

        # Detect circular reference
        if self.id in _visited:
            # Circular link detected - return None to break the cycle
            return None

        # Add current config to visited set
        _visited.add(self.id)

        # If this is a formula KPI, calculate from other KPIs
        if self.is_formula():
            calculated_value = self._calculate_formula_value(_visited=_visited)
            # Wrap in consensus-like dict for consistency
            if calculated_value is not None:
                return {
                    "status": "strong",
                    "value": calculated_value,
                    "count": 1,
                    "is_rollup_eligible": True,
                }
            else:
                return {
                    "status": "no_data",
                    "value": None,
                    "count": 0,
                    "is_rollup_eligible": False,
                }

        # If this is a linked KPI, read from the source
        if self.is_linked():
            source_config = self.get_linked_source_config()
            if source_config:
                # Read value from the source config
                return source_config.get_consensus_value(_visited=_visited)
            # If source not found, return no data dict
            return {
                "status": "no_data",
                "value": None,
                "count": 0,
                "is_rollup_eligible": False,
            }

        # Normal behavior: calculate consensus from local contributions
        from app.services import ConsensusService

        return ConsensusService.get_cell_value(self)

    def _calculate_formula_value(self, _visited=None):
        """
        Calculate value based on formula configuration.
        Supports two modes:
        1. Simple mode: operation-based (sum, avg, min, max, multiply, subtract, divide)
        2. Advanced mode: Python expression with safe evaluation

        Args:
            _visited: Set of visited config IDs to prevent circular dependencies

        Returns:
            Calculated numeric value or None if calculation fails
        """
        if not self.is_formula():
            return None

        # Get source configs
        source_configs = self.get_formula_source_configs()
        if not source_configs:
            return None

        # Get mode (default to simple for backwards compatibility)
        mode = self.calculation_config.get("mode", "simple")

        import logging

        logging.info(f"Formula config {self.id}: mode={mode}, source_configs={len(source_configs)}")

        # Build namespace with KPI values
        namespace = {}
        values = []  # For simple mode

        for source_config in source_configs:
            consensus_result = source_config.get_consensus_value(_visited=_visited)

            # Handle both dict and raw value returns for backwards compatibility
            if isinstance(consensus_result, dict):
                value = consensus_result.get("value")
            else:
                value = consensus_result

            logging.info(f"Formula config {self.id}: source_config={source_config.id}, value={value}")

            if value is not None:
                try:
                    float_value = float(value)
                    values.append(float_value)
                    # Make available as kpi_<id> for expression mode
                    namespace[f"kpi_{source_config.id}"] = float_value
                except (ValueError, TypeError):
                    # Skip non-numeric values
                    pass

        if not values:
            logging.warning(f"Formula config {self.id}: No values retrieved from source KPIs")
            return None

        # Advanced mode: Python expression
        if mode == "advanced":
            expression = self.calculation_config.get("expression")
            if not expression:
                import logging

                logging.warning(f"Formula config {self.id}: mode=advanced but no expression")
                return None

            try:
                import logging

                from simpleeval import FunctionNotDefined, InvalidExpression, simple_eval

                logging.info(
                    f"Formula config {self.id}: Evaluating expression '{expression}' with namespace {namespace}"
                )

                # Safe evaluation with math functions
                result = simple_eval(
                    expression,
                    names=namespace,
                    functions={
                        "abs": abs,
                        "round": round,
                        "max": max,
                        "min": min,
                        "sum": sum,
                    },
                )

                logging.info(f"Formula config {self.id}: Result = {result}")
                return float(result) if result is not None else None

            except ZeroDivisionError:
                import logging

                logging.error(f"Division by zero in formula for config {self.id}: {expression}")
                return None

            except (ValueError, TypeError) as e:
                import logging

                logging.error(f"Invalid value in formula for config {self.id}: {e}")
                return None

            except (InvalidExpression, FunctionNotDefined) as e:
                import logging

                logging.error(f"Invalid expression in formula for config {self.id}: {e}")
                return None

            except Exception as e:
                import logging

                logging.error(f"Formula calculation error for config {self.id}: {e}")
                return None

        # Simple mode: operation-based (backwards compatible)
        operation = self.calculation_config.get("operation", "sum")

        try:
            if operation == "sum":
                return sum(values)
            elif operation == "avg":
                return sum(values) / len(values)
            elif operation == "min":
                return min(values)
            elif operation == "max":
                return max(values)
            elif operation == "multiply":
                result = 1
                for v in values:
                    result *= v
                return result
            elif operation == "subtract":
                # Subtract all subsequent values from first
                if len(values) < 2:
                    return values[0] if values else None
                result = values[0]
                for v in values[1:]:
                    result -= v
                return result
            elif operation == "divide":
                # Divide first value by all subsequent values
                if len(values) < 2:
                    return values[0] if values else None
                result = values[0]
                for v in values[1:]:
                    if v == 0:
                        return None  # Division by zero
                    result /= v
                return result

            # Default to sum if operation not recognized
            return sum(values)

        except ZeroDivisionError:
            return None
        except Exception:
            return None

    def get_value_color(self, value):
        """Get color for a numeric value based on its sign"""
        if not self.value_type.is_numeric() or value is None:
            return None

        try:
            numeric_value = float(value)
            if numeric_value > 0:
                return self.color_positive or "#28a745"
            elif numeric_value < 0:
                return self.color_negative or "#dc3545"
            else:
                return self.color_zero or "#6c757d"
        except (ValueError, TypeError):
            return None

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
        """Format a value for display with the configured scale"""
        if value is None or not self.value_type.is_numeric():
            return value

        try:
            numeric_value = float(value)
            divisor = self.get_scale_divisor()
            scaled_value = numeric_value / divisor

            # Use value_type decimal places
            decimal_places = self.value_type.decimal_places if self.value_type.decimal_places is not None else 2

            # If it's integer format, show as integer after scaling
            if self.value_type.numeric_format == "integer":
                return int(round(scaled_value))
            else:
                return round(scaled_value, decimal_places)
        except (ValueError, TypeError):
            return value

    def __repr__(self):
        return f"<KPIValueTypeConfig kpi_id={self.kpi_id} value_type_id={self.value_type_id}>"
