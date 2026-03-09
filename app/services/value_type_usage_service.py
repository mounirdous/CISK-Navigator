"""
Value Type Usage Service

Checks whether a value type is in use and where.
"""

from app.models import Contribution, KPIValueTypeConfig, RollupRule, ValueType


class ValueTypeUsageService:
    """
    Service for checking value type usage and generating usage reports.

    A value type cannot be deleted if it's in use.
    """

    @staticmethod
    def check_usage(value_type_id):
        """
        Check if a value type is in use.

        Returns:
            dict with:
                - is_used: boolean
                - usage: dict with detailed usage information
        """
        from app.extensions import db

        value_type = ValueType.query.get(value_type_id)
        if not value_type:
            return None

        usage = {"kpi_configs": [], "contributions_count": 0, "rollup_rules_count": 0}

        # Check KPI configurations
        kpi_configs = KPIValueTypeConfig.query.filter_by(value_type_id=value_type_id).all()

        for config in kpi_configs:
            kpi = config.kpi
            is_link = kpi.initiative_system_link
            initiative = is_link.initiative
            system = is_link.system

            # Find the challenge(s) this appears in
            challenge_names = []
            for ci_link in initiative.challenge_links:
                challenge_names.append(ci_link.challenge.name)

            contrib_count = len(config.contributions)

            usage["kpi_configs"].append(
                {
                    "kpi_id": kpi.id,
                    "kpi_name": kpi.name,
                    "system_name": system.name,
                    "initiative_name": initiative.name,
                    "challenge_names": challenge_names,
                    "contributions_count": contrib_count,
                }
            )

            usage["contributions_count"] += contrib_count

        # Check rollup rules
        rollup_rules = RollupRule.query.filter_by(value_type_id=value_type_id).all()
        usage["rollup_rules_count"] = len(rollup_rules)

        is_used = len(usage["kpi_configs"]) > 0 or usage["contributions_count"] > 0 or usage["rollup_rules_count"] > 0

        return {"is_used": is_used, "usage": usage}

    @staticmethod
    def can_delete(value_type_id):
        """
        Check if a value type can be safely deleted.

        Returns:
            tuple (can_delete: bool, reason: str or None)
        """
        result = ValueTypeUsageService.check_usage(value_type_id)

        if not result:
            return False, "Value type not found"

        if result["is_used"]:
            usage = result["usage"]
            reasons = []

            if len(usage["kpi_configs"]) > 0:
                reasons.append(f"Used in {len(usage['kpi_configs'])} KPI configuration(s)")

            if usage["contributions_count"] > 0:
                reasons.append(f"Has {usage['contributions_count']} contribution record(s)")

            if usage["rollup_rules_count"] > 0:
                reasons.append(f"Referenced by {usage['rollup_rules_count']} roll-up rule(s)")

            return False, "; ".join(reasons)

        return True, None
