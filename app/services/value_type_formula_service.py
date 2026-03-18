"""
Value Type Formula Service

Calculates formula-based value types (e.g., Net = Revenue - Cost).
"""

from decimal import Decimal
from typing import Dict, List, Optional

from app.models import KPI, KPISnapshot, KPIValueTypeConfig, ValueType


class ValueTypeFormulaService:
    """Service for calculating formula-based value type values"""

    @staticmethod
    def calculate_formula_value(
        kpi_id: int,
        formula_value_type: ValueType,
        snapshot_date: str,
        kpi_values: Optional[Dict[int, Decimal]] = None,
    ) -> Optional[Decimal]:
        """
        Calculate formula value for a specific KPI and snapshot date.

        Args:
            kpi_id: KPI ID
            formula_value_type: Formula-based ValueType
            snapshot_date: Snapshot date (YYYY-MM-DD)
            kpi_values: Pre-fetched KPI values dict {value_type_id: value}
                       (optional, for performance optimization)

        Returns:
            Calculated value or None if insufficient data
        """
        if not formula_value_type.is_formula() or not formula_value_type.calculation_config:
            return None

        operation = formula_value_type.calculation_config.get("operation")
        source_value_type_ids = formula_value_type.calculation_config.get("source_value_type_ids", [])

        if not source_value_type_ids:
            return None

        # Get source values
        source_values = []
        for source_vt_id in source_value_type_ids:
            # Use pre-fetched values if available
            if kpi_values is not None and source_vt_id in kpi_values:
                value = kpi_values[source_vt_id]
            else:
                # Otherwise fetch from database
                value = ValueTypeFormulaService._get_value_for_kpi(kpi_id, source_vt_id, snapshot_date)

            # If any source value is missing, we can't calculate
            if value is None:
                return None

            source_values.append(value)

        # Perform calculation
        return ValueTypeFormulaService._apply_operation(operation, source_values)

    @staticmethod
    def _get_value_for_kpi(kpi_id: int, value_type_id: int, snapshot_date: str) -> Optional[Decimal]:
        """
        Get value for a specific KPI, value type, and snapshot date.

        Handles both manual and formula-based value types recursively.
        """
        # Get the config for this KPI + value type
        config = KPIValueTypeConfig.query.filter_by(kpi_id=kpi_id, value_type_id=value_type_id).first()

        if not config:
            return None

        value_type = config.value_type

        # If this is a manual value type, get the snapshot value
        if not value_type.is_formula():
            snapshot = KPISnapshot.query.filter_by(
                kpi_value_type_config_id=config.id, snapshot_date=snapshot_date
            ).first()
            return snapshot.value if snapshot else None

        # If this is a formula value type, calculate it recursively
        return ValueTypeFormulaService.calculate_formula_value(
            kpi_id, value_type, snapshot_date, kpi_values=None  # Recursive call fetches its own data
        )

    @staticmethod
    def _apply_operation(operation: str, values: List[Decimal]) -> Optional[Decimal]:
        """
        Apply operation to list of values.

        Args:
            operation: 'add', 'subtract', 'multiply', 'divide'
            values: List of Decimal values

        Returns:
            Result of operation or None if error
        """
        if not values:
            return None

        try:
            if operation == ValueType.OP_ADD:
                return sum(values)

            elif operation == ValueType.OP_SUBTRACT:
                # Subtract all subsequent values from first value
                result = values[0]
                for val in values[1:]:
                    result -= val
                return result

            elif operation == ValueType.OP_MULTIPLY:
                result = values[0]
                for val in values[1:]:
                    result *= val
                return result

            elif operation == ValueType.OP_DIVIDE:
                # Divide first value by all subsequent values
                result = values[0]
                for val in values[1:]:
                    if val == 0:
                        return None  # Division by zero
                    result /= val
                return result

            else:
                return None

        except Exception:
            return None

    @staticmethod
    def get_kpi_values_for_formula_calculation(kpi_id: int, snapshot_date: str) -> Dict[int, Decimal]:
        """
        Get all manual value type values for a KPI on a specific date.

        This is used for batch calculation to avoid N+1 queries.

        Args:
            kpi_id: KPI ID
            snapshot_date: Snapshot date

        Returns:
            Dict mapping value_type_id to value
        """
        # Get all configs for this KPI (only manual ones have snapshots)
        configs = (
            KPIValueTypeConfig.query.filter_by(kpi_id=kpi_id)
            .join(ValueType)
            .filter(ValueType.calculation_type == ValueType.CALC_MANUAL)
            .all()
        )

        values = {}
        for config in configs:
            snapshot = KPISnapshot.query.filter_by(
                kpi_value_type_config_id=config.id, snapshot_date=snapshot_date
            ).first()

            if snapshot and snapshot.value is not None:
                values[config.value_type_id] = snapshot.value

        return values

    @staticmethod
    def bulk_calculate_formula_values_for_kpis(
        kpis: List[KPI], formula_value_types: List[ValueType], snapshot_date: str
    ) -> Dict[int, Dict[int, Optional[Decimal]]]:
        """
        Bulk calculate formula values for multiple KPIs.

        Optimized for performance when rendering workspace grid.

        Args:
            kpis: List of KPI objects
            formula_value_types: List of formula-based ValueType objects
            snapshot_date: Snapshot date

        Returns:
            Dict: {kpi_id: {value_type_id: calculated_value}}
        """
        results = {}

        for kpi in kpis:
            kpi_results = {}

            # Pre-fetch all manual values for this KPI
            manual_values = ValueTypeFormulaService.get_kpi_values_for_formula_calculation(kpi.id, snapshot_date)

            # Calculate each formula value type
            for formula_vt in formula_value_types:
                value = ValueTypeFormulaService.calculate_formula_value(
                    kpi.id, formula_vt, snapshot_date, kpi_values=manual_values
                )
                kpi_results[formula_vt.id] = value

            results[kpi.id] = kpi_results

        return results
