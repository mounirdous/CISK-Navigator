"""
Value Type Usage Service

Checks whether a value type is in use and where.
"""

from app.models import KPIValueTypeConfig, RollupRule, ValueType


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
        value_type = ValueType.query.get(value_type_id)
        if not value_type:
            return None

        usage = {"kpi_configs": [], "contributions_count": 0, "rollup_rules_count": 0, "linked_consumers": []}

        # Check if this value type is being used as a linked source by other KPIs
        linked_consumers = KPIValueTypeConfig.query.filter_by(linked_source_value_type_id=value_type_id).all()
        for consumer_config in linked_consumers:
            consumer_kpi = consumer_config.kpi
            is_link = consumer_kpi.initiative_system_link
            initiative = is_link.initiative
            org = initiative.organization
            usage["linked_consumers"].append(
                {
                    "kpi_id": consumer_kpi.id,
                    "kpi_name": consumer_kpi.name,
                    "org_name": org.name,
                    "initiative_name": initiative.name,
                }
            )

        # Check KPI configurations
        kpi_configs = KPIValueTypeConfig.query.filter_by(value_type_id=value_type_id).all()

        for config in kpi_configs:
            kpi = config.kpi
            is_link = kpi.initiative_system_link
            initiative = is_link.initiative
            system = is_link.system

            # Find the challenge(s) and space(s) this appears in
            challenge_names = []
            space_names = []
            for ci_link in initiative.challenge_links:
                challenge_names.append(ci_link.challenge.name)
                if ci_link.challenge.space and ci_link.challenge.space.name not in space_names:
                    space_names.append(ci_link.challenge.space.name)

            contrib_count = len(config.contributions)

            usage["kpi_configs"].append(
                {
                    "kpi_id": kpi.id,
                    "kpi_name": kpi.name,
                    "system_name": system.name,
                    "initiative_name": initiative.name,
                    "challenge_names": challenge_names,
                    "space_names": space_names,
                    "contributions_count": contrib_count,
                }
            )

            usage["contributions_count"] += contrib_count

        # Check rollup rules
        rollup_rules = RollupRule.query.filter_by(value_type_id=value_type_id).all()
        usage["rollup_rules_count"] = len(rollup_rules)

        is_used = (
            len(usage["kpi_configs"]) > 0
            or usage["contributions_count"] > 0
            or usage["rollup_rules_count"] > 0
            or len(usage["linked_consumers"]) > 0
        )

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

            if len(usage["linked_consumers"]) > 0:
                consumer_names = [f"{c['kpi_name']} ({c['org_name']})" for c in usage["linked_consumers"][:3]]
                more = "..." if len(usage["linked_consumers"]) > 3 else ""
                reasons.append(
                    f"Being used as linked source by {len(usage['linked_consumers'])} KPI(s): {', '.join(consumer_names)}{more}"
                )

            return False, "; ".join(reasons)

        return True, None
