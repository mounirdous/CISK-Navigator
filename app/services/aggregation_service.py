"""
Aggregation Service

Handles upward roll-up of values through the hierarchy.
"""

import logging
from statistics import median

from app.models import (
    Challenge,
    ChallengeInitiativeLink,
    InitiativeSystemLink,
    KPIValueTypeConfig,
    RollupRule,
    ValueType,
)
from app.services.consensus_service import ConsensusService

logger = logging.getLogger(__name__)


class AggregationService:
    """
    Service for aggregating values upward through the hierarchy.

    Roll-up flow:
    KPI → System → Initiative → Challenge → Space

    Only values in strong consensus are eligible for roll-up.
    """

    @staticmethod
    def aggregate_values(values, formula, value_type):
        """
        Aggregate a list of values using the specified formula.

        Args:
            values: list of numeric or qualitative values
            formula: sum, min, max, avg, median, or count
            value_type: ValueType object to determine handling

        Returns:
            aggregated value
        """
        if not values:
            return None

        if formula == "sum":
            if value_type.is_qualitative():
                # Sum doesn't make sense for qualitative, use avg instead
                return AggregationService.aggregate_values(values, "avg", value_type)
            # Convert all to float to handle mixed Decimal/float types
            return float(sum(float(v) for v in values))

        elif formula == "min":
            # Convert to float to handle mixed Decimal/float types
            return float(min(float(v) for v in values))

        elif formula == "max":
            # Convert to float to handle mixed Decimal/float types
            return float(max(float(v) for v in values))

        elif formula == "avg":
            # Convert to float to handle mixed Decimal/float types
            avg = sum(float(v) for v in values) / len(values)
            if value_type.is_qualitative():
                # For qualitative, round to nearest integer (1, 2, or 3)
                # Example: 2.5 → 3 (round up), 2.4 → 2 (round down)
                return round(avg)
            return avg

        elif formula == "median":
            # Median: middle value when sorted, ignores outliers
            # Convert to float to handle mixed Decimal/float types
            return float(median(float(v) for v in values))

        elif formula == "count":
            # Count: number of values (useful for "how many" questions)
            return len(values)

        return None

    @staticmethod
    def get_kpi_to_system_rollup(initiative_system_link, value_type_id):
        """
        Aggregate KPI values up to the System level for a specific value type.

        This is the first roll-up step and always uses the value type's default formula.

        Args:
            initiative_system_link: InitiativeSystemLink object
            value_type_id: ID of the value type to aggregate

        Returns:
            dict with:
                - value: aggregated value
                - count_total: total KPIs with this value type
                - count_included: KPIs in strong consensus included in aggregation
                - is_complete: whether all KPIs contributed
        """
        logger.info(f"🔄 [KPI→System] Link ID={initiative_system_link.id}, ValueType ID={value_type_id}")

        # Get all KPIs under this initiative-system link
        kpis = initiative_system_link.kpis
        logger.info(f"  Found {len(kpis)} KPIs under this system link")

        # Get the value type
        value_type = ValueType.query.get(value_type_id)
        if not value_type:
            logger.warning(f"  ❌ ValueType {value_type_id} not found!")
            return None

        logger.info(f"  ValueType: {value_type.name}, Formula: {value_type.default_aggregation_formula}")

        # Collect values from KPIs in strong consensus
        eligible_values = []
        total_with_type = 0

        for kpi in kpis:
            # Check if this KPI uses this value type
            config = KPIValueTypeConfig.query.filter_by(kpi_id=kpi.id, value_type_id=value_type_id).first()

            if not config:
                logger.debug(f"    KPI {kpi.id} ({kpi.name}): No config for this value type")
                continue

            total_with_type += 1

            # Get consensus for this cell
            consensus = ConsensusService.get_cell_value(config)
            logger.info(
                f"    KPI {kpi.id} ({kpi.name}): status={consensus['status']}, value={consensus['value']}, rollup_eligible={consensus['is_rollup_eligible']}"
            )

            if consensus["is_rollup_eligible"] and consensus["value"] is not None:
                eligible_values.append(consensus["value"])
                logger.info(f"      ✅ Added value: {consensus['value']}")
            else:
                logger.info("      ❌ Skipped (not eligible or null)")

        # Get formula (even if no values, for consistent return structure)
        formula = value_type.default_aggregation_formula

        if not eligible_values:
            logger.warning(f"  ❌ No eligible values found! Total with type: {total_with_type}")
            return {
                "value": None,
                "count_total": total_with_type,
                "count_included": 0,
                "is_complete": False,
                "formula": formula,
            }

        # Aggregate using the formula
        aggregated = AggregationService.aggregate_values(eligible_values, formula, value_type)
        logger.info(f"  ✅ Aggregated {len(eligible_values)} values using {formula} = {aggregated}")

        return {
            "value": aggregated,
            "count_total": total_with_type,
            "count_included": len(eligible_values),
            "is_complete": len(eligible_values) == total_with_type and total_with_type > 0,
            "formula": formula,
        }

    @staticmethod
    def get_system_to_initiative_rollup(initiative_id, value_type_id):
        """
        Aggregate System values up to the Initiative level for a specific value type.

        Only values from enabled roll-up rules are included.

        Args:
            initiative_id: Initiative ID
            value_type_id: Value type ID

        Returns:
            dict with value, count_total, count_included, is_complete
        """
        logger.info(f"🔄 [System→Initiative] Initiative ID={initiative_id}, ValueType ID={value_type_id}")

        # Get all initiative-system links for this initiative
        links = InitiativeSystemLink.query.filter_by(initiative_id=initiative_id).all()
        logger.info(f"  Found {len(links)} system links for this initiative")

        # Get the value type
        value_type = ValueType.query.get(value_type_id)
        if not value_type:
            logger.warning(f"  ❌ ValueType {value_type_id} not found!")
            return None

        eligible_values = []
        total_systems = 0

        for link in links:
            # Check if roll-up is enabled for this value type at this link
            rollup_rule = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM, source_id=link.id, value_type_id=value_type_id
            ).first()

            # If no rule exists, default to enabled (backward compatibility)
            # If rule exists but disabled, skip
            if rollup_rule and not rollup_rule.rollup_enabled:
                logger.info(f"    System Link {link.id}: Rollup DISABLED by rule")
                continue

            # Get the system-level aggregation (KPIs → System)
            system_agg = AggregationService.get_kpi_to_system_rollup(link, value_type_id)

            # Only count this system if it actually has KPIs configured for this VT
            if not system_agg or system_agg.get("count_total", 0) == 0:
                logger.info(f"    ⏭ System Link {link.id}: No KPIs for this value type — skipped")
                continue

            total_systems += 1

            if system_agg["value"] is not None:
                eligible_values.append(system_agg["value"])
                status = "✓" if system_agg["is_complete"] else "⚠"
                logger.info(
                    f"    {status} System Link {link.id}: Added value {system_agg['value']} ({'complete' if system_agg['is_complete'] else 'partial'})"
                )
            else:
                logger.info(
                    f"    ❌ System Link {link.id}: value={system_agg.get('value')}, is_complete={system_agg.get('is_complete')}"
                )

        # Determine formula (even if no values, for consistent return structure)
        formula = None
        rule = RollupRule.query.filter_by(
            source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM, value_type_id=value_type_id, rollup_enabled=True
        ).first()

        if rule:
            formula = rule.get_formula()
        else:
            formula = value_type.default_aggregation_formula

        if not eligible_values:
            logger.warning(f"  ❌ No eligible system values found! Total systems: {total_systems}")
            return {
                "value": None,
                "count_total": total_systems,
                "count_included": 0,
                "is_complete": False,
                "formula": formula,
            }

        aggregated = AggregationService.aggregate_values(eligible_values, formula, value_type)
        logger.info(f"  ✅ Aggregated {len(eligible_values)} system values using {formula} = {aggregated}")

        return {
            "value": aggregated,
            "count_total": total_systems,
            "count_included": len(eligible_values),
            "is_complete": len(eligible_values) == total_systems and total_systems > 0,
            "formula": formula,
        }

    @staticmethod
    def get_initiative_to_challenge_rollup(challenge_id, value_type_id):
        """
        Aggregate Initiative values up to the Challenge level for a specific value type.
        """
        logger.info(f"🔄 [Initiative→Challenge] Challenge ID={challenge_id}, ValueType ID={value_type_id}")

        # Get all challenge-initiative links for this challenge
        links = ChallengeInitiativeLink.query.filter_by(challenge_id=challenge_id).all()
        logger.info(f"  Found {len(links)} initiative links for this challenge")

        value_type = ValueType.query.get(value_type_id)
        if not value_type:
            logger.warning(f"  ❌ ValueType {value_type_id} not found!")
            return None

        eligible_values = []
        total_initiatives = 0

        for link in links:
            # Check if roll-up is enabled
            rollup_rule = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE, source_id=link.id, value_type_id=value_type_id
            ).first()

            # If no rule exists, default to enabled (backward compatibility)
            # If rule exists but disabled, skip
            if rollup_rule and not rollup_rule.rollup_enabled:
                logger.info(f"    Initiative Link {link.id}: Rollup DISABLED by rule")
                continue

            # Get the initiative-level aggregation
            initiative_agg = AggregationService.get_system_to_initiative_rollup(link.initiative_id, value_type_id)

            # Only count this initiative if it actually has systems with KPIs for this VT
            if not initiative_agg or initiative_agg.get("count_total", 0) == 0:
                logger.info(f"    ⏭ Initiative {link.initiative_id}: No systems with this value type — skipped")
                continue

            total_initiatives += 1

            if initiative_agg["value"] is not None:
                eligible_values.append(initiative_agg["value"])
                status = "✓" if initiative_agg["is_complete"] else "⚠"
                logger.info(
                    f"    {status} Initiative {link.initiative_id}: Added value {initiative_agg['value']} ({'complete' if initiative_agg['is_complete'] else 'partial'})"
                )
            else:
                logger.info(
                    f"    ❌ Initiative {link.initiative_id}: value={initiative_agg.get('value')}, is_complete={initiative_agg.get('is_complete')}"
                )

        # Determine formula (even if no values, for consistent return structure)
        formula = value_type.default_aggregation_formula
        rule = RollupRule.query.filter_by(
            source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE, value_type_id=value_type_id, rollup_enabled=True
        ).first()

        if rule:
            formula = rule.get_formula()

        if not eligible_values:
            logger.warning(f"  ❌ No eligible initiative values found! Total initiatives: {total_initiatives}")
            return {
                "value": None,
                "count_total": total_initiatives,
                "count_included": 0,
                "is_complete": False,
                "formula": formula,
            }

        aggregated = AggregationService.aggregate_values(eligible_values, formula, value_type)
        logger.info(f"  ✅ Aggregated {len(eligible_values)} initiative values using {formula} = {aggregated}")

        return {
            "value": aggregated,
            "count_total": total_initiatives,
            "count_included": len(eligible_values),
            "is_complete": len(eligible_values) == total_initiatives and total_initiatives > 0,
            "formula": formula,
        }

    @staticmethod
    def get_challenge_to_space_rollup(space_id, value_type_id):
        """
        Aggregate Challenge values up to the Space level for a specific value type.
        """
        logger.info(f"🔄 [Challenge→Space] Space ID={space_id}, ValueType ID={value_type_id}")

        # Get all challenges in this space
        challenges = Challenge.query.filter_by(space_id=space_id).all()
        logger.info(f"  Found {len(challenges)} challenges in this space")

        value_type = ValueType.query.get(value_type_id)
        if not value_type:
            logger.warning(f"  ❌ ValueType {value_type_id} not found!")
            return None

        eligible_values = []
        total_challenges = 0

        for challenge in challenges:
            # Check if roll-up is enabled for this challenge
            rollup_rule = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_CHALLENGE, source_id=challenge.id, value_type_id=value_type_id
            ).first()

            # If no rule exists, default to enabled (backward compatibility)
            # If rule exists but disabled, skip
            if rollup_rule and not rollup_rule.rollup_enabled:
                logger.info(f"    Challenge {challenge.id} ({challenge.name}): Rollup DISABLED by rule")
                continue

            # Get the challenge-level aggregation
            challenge_agg = AggregationService.get_initiative_to_challenge_rollup(challenge.id, value_type_id)

            # Only count this challenge if it actually has initiatives with this VT
            if not challenge_agg or challenge_agg.get("count_total", 0) == 0:
                logger.info(f"    ⏭ Challenge {challenge.id} ({challenge.name}): No initiatives with this value type — skipped")
                continue

            total_challenges += 1

            if challenge_agg["value"] is not None:
                eligible_values.append(challenge_agg["value"])
                status = "✓" if challenge_agg["is_complete"] else "⚠"
                logger.info(
                    f"    {status} Challenge {challenge.id} ({challenge.name}): Added value {challenge_agg['value']} ({'complete' if challenge_agg['is_complete'] else 'partial'})"
                )
            else:
                logger.info(
                    f"    ❌ Challenge {challenge.id} ({challenge.name}): value={challenge_agg.get('value')}, is_complete={challenge_agg.get('is_complete')}"
                )

        # Determine formula (even if no values, for consistent return structure)
        formula = value_type.default_aggregation_formula
        rule = RollupRule.query.filter_by(
            source_type=RollupRule.SOURCE_CHALLENGE, value_type_id=value_type_id, rollup_enabled=True
        ).first()

        if rule:
            formula = rule.get_formula()

        if not eligible_values:
            logger.warning(f"  ❌ No eligible challenge values found! Total challenges: {total_challenges}")
            return {
                "value": None,
                "count_total": total_challenges,
                "count_included": 0,
                "is_complete": False,
                "formula": formula,
            }

        aggregated = AggregationService.aggregate_values(eligible_values, formula, value_type)
        logger.info(f"  ✅ Aggregated {len(eligible_values)} challenge values using {formula} = {aggregated}")

        return {
            "value": aggregated,
            "count_total": total_challenges,
            "count_included": len(eligible_values),
            "is_complete": len(eligible_values) == total_challenges and total_challenges > 0,
            "formula": formula,
        }
