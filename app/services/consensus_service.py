"""
Consensus Service

Calculates consensus status for KPI cells based on contributor opinions.
"""

from collections import Counter
from decimal import Decimal


class ConsensusService:
    """
    Service for calculating consensus status from contributions.

    Consensus statuses:
    - NO_DATA: No contributions
    - PENDING_CONFIRMATION: Only one contribution
    - STRONG_CONSENSUS: 2+ contributions, all same value
    - WEAK_CONSENSUS: 2+ contributions, majority exists but not unanimous
    - NO_CONSENSUS: 2+ contributions, no reliable agreement
    """

    STATUS_NO_DATA = "no_data"
    STATUS_PENDING = "pending"
    STATUS_STRONG = "strong"
    STATUS_WEAK = "weak"
    STATUS_NO_CONSENSUS = "no_consensus"

    @staticmethod
    def calculate_consensus(contributions):
        """
        Calculate consensus status and derived value from contributions.

        Returns:
            dict with:
                - status: consensus status
                - value: consensus value (numeric or qualitative level)
                - count: number of contributions
                - is_rollup_eligible: whether this can participate in roll-ups
        """
        if not contributions:
            return {"status": ConsensusService.STATUS_NO_DATA, "value": None, "count": 0, "is_rollup_eligible": False}

        if len(contributions) == 1:
            contrib = contributions[0]
            value = contrib.numeric_value if contrib.numeric_value is not None else contrib.qualitative_level
            return {
                "status": ConsensusService.STATUS_STRONG,
                "value": value,
                "count": 1,
                "is_rollup_eligible": True,  # Single contribution is valid!
            }

        # Extract values from contributions
        values = []
        for contrib in contributions:
            if contrib.numeric_value is not None:
                values.append(float(contrib.numeric_value))
            elif contrib.qualitative_level is not None:
                values.append(contrib.qualitative_level)

        if not values:
            return {
                "status": ConsensusService.STATUS_NO_DATA,
                "value": None,
                "count": len(contributions),
                "is_rollup_eligible": False,
            }

        # Count occurrences
        counter = Counter(values)
        most_common = counter.most_common()

        # Check for strong consensus (all same)
        if len(most_common) == 1:
            return {
                "status": ConsensusService.STATUS_STRONG,
                "value": most_common[0][0],
                "count": len(values),
                "is_rollup_eligible": True,  # Only strong consensus is eligible
            }

        # Check for weak consensus (majority > 50%)
        total = len(values)
        majority_value, majority_count = most_common[0]

        if majority_count > total / 2:
            return {
                "status": ConsensusService.STATUS_WEAK,
                "value": majority_value,
                "count": total,
                "is_rollup_eligible": False,
            }

        # No consensus
        return {
            "status": ConsensusService.STATUS_NO_CONSENSUS,
            "value": None,
            "count": total,
            "is_rollup_eligible": False,
        }

    @staticmethod
    def get_cell_value(kpi_value_type_config):
        """
        Get the consensus value for a KPI cell.

        Args:
            kpi_value_type_config: KPIValueTypeConfig object with contributions loaded

        Returns:
            consensus dict from calculate_consensus
        """
        return ConsensusService.calculate_consensus(kpi_value_type_config.contributions)
