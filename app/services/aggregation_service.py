"""
Aggregation Service

Handles upward roll-up of values through the hierarchy.
"""
from decimal import Decimal
from sqlalchemy import and_
from app.models import (
    KPI, KPIValueTypeConfig, InitiativeSystemLink, ChallengeInitiativeLink,
    Challenge, RollupRule, ValueType
)
from app.services.consensus_service import ConsensusService


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
            formula: sum, min, max, or avg
            value_type: ValueType object to determine handling

        Returns:
            aggregated value
        """
        if not values:
            return None

        if formula == 'sum':
            if value_type.is_qualitative():
                # Sum doesn't make sense for qualitative, use avg instead
                return AggregationService.aggregate_values(values, 'avg', value_type)
            return sum(values)

        elif formula == 'min':
            return min(values)

        elif formula == 'max':
            return max(values)

        elif formula == 'avg':
            avg = sum(values) / len(values)
            if value_type.is_qualitative():
                # For qualitative, store raw average but can be rounded for display
                return avg
            return avg

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
        from app.extensions import db

        # Get all KPIs under this initiative-system link
        kpis = initiative_system_link.kpis

        # Get the value type
        value_type = ValueType.query.get(value_type_id)
        if not value_type:
            return None

        # Collect values from KPIs in strong consensus
        eligible_values = []
        total_with_type = 0

        for kpi in kpis:
            # Check if this KPI uses this value type
            config = KPIValueTypeConfig.query.filter_by(
                kpi_id=kpi.id,
                value_type_id=value_type_id
            ).first()

            if not config:
                continue

            total_with_type += 1

            # Get consensus for this cell
            consensus = ConsensusService.get_cell_value(config)

            if consensus['is_rollup_eligible'] and consensus['value'] is not None:
                eligible_values.append(consensus['value'])

        if not eligible_values:
            return {
                'value': None,
                'count_total': total_with_type,
                'count_included': 0,
                'is_complete': False
            }

        # Aggregate using the value type's default formula
        aggregated = AggregationService.aggregate_values(
            eligible_values,
            value_type.default_aggregation_formula,
            value_type
        )

        return {
            'value': aggregated,
            'count_total': total_with_type,
            'count_included': len(eligible_values),
            'is_complete': len(eligible_values) == total_with_type and total_with_type > 0
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
        from app.extensions import db

        # Get all initiative-system links for this initiative
        links = InitiativeSystemLink.query.filter_by(initiative_id=initiative_id).all()

        # Get the value type
        value_type = ValueType.query.get(value_type_id)
        if not value_type:
            return None

        eligible_values = []
        total_systems = 0

        for link in links:
            # Check if roll-up is enabled for this value type at this link
            rollup_rule = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM,
                source_id=link.id,
                value_type_id=value_type_id,
                rollup_enabled=True
            ).first()

            if not rollup_rule:
                continue

            total_systems += 1

            # Get the system-level aggregation (KPIs → System)
            system_agg = AggregationService.get_kpi_to_system_rollup(link, value_type_id)

            if system_agg and system_agg['value'] is not None and system_agg['is_complete']:
                eligible_values.append(system_agg['value'])

        if not eligible_values:
            return {
                'value': None,
                'count_total': total_systems,
                'count_included': 0,
                'is_complete': False
            }

        # Use the first rollup rule's formula (they should all be the same for this step)
        formula = None
        rule = RollupRule.query.filter_by(
            source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM,
            value_type_id=value_type_id,
            rollup_enabled=True
        ).first()

        if rule:
            formula = rule.get_formula()
        else:
            formula = value_type.default_aggregation_formula

        aggregated = AggregationService.aggregate_values(eligible_values, formula, value_type)

        return {
            'value': aggregated,
            'count_total': total_systems,
            'count_included': len(eligible_values),
            'is_complete': len(eligible_values) == total_systems and total_systems > 0
        }

    @staticmethod
    def get_initiative_to_challenge_rollup(challenge_id, value_type_id):
        """
        Aggregate Initiative values up to the Challenge level for a specific value type.
        """
        from app.extensions import db

        # Get all challenge-initiative links for this challenge
        links = ChallengeInitiativeLink.query.filter_by(challenge_id=challenge_id).all()

        value_type = ValueType.query.get(value_type_id)
        if not value_type:
            return None

        eligible_values = []
        total_initiatives = 0

        for link in links:
            # Check if roll-up is enabled
            rollup_rule = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE,
                source_id=link.id,
                value_type_id=value_type_id,
                rollup_enabled=True
            ).first()

            if not rollup_rule:
                continue

            total_initiatives += 1

            # Get the initiative-level aggregation
            initiative_agg = AggregationService.get_system_to_initiative_rollup(
                link.initiative_id, value_type_id
            )

            if initiative_agg and initiative_agg['value'] is not None and initiative_agg['is_complete']:
                eligible_values.append(initiative_agg['value'])

        if not eligible_values:
            return {
                'value': None,
                'count_total': total_initiatives,
                'count_included': 0,
                'is_complete': False
            }

        # Get formula from rollup rule
        formula = value_type.default_aggregation_formula
        rule = RollupRule.query.filter_by(
            source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE,
            value_type_id=value_type_id,
            rollup_enabled=True
        ).first()

        if rule:
            formula = rule.get_formula()

        aggregated = AggregationService.aggregate_values(eligible_values, formula, value_type)

        return {
            'value': aggregated,
            'count_total': total_initiatives,
            'count_included': len(eligible_values),
            'is_complete': len(eligible_values) == total_initiatives and total_initiatives > 0
        }

    @staticmethod
    def get_challenge_to_space_rollup(space_id, value_type_id):
        """
        Aggregate Challenge values up to the Space level for a specific value type.
        """
        from app.extensions import db

        # Get all challenges in this space
        challenges = Challenge.query.filter_by(space_id=space_id).all()

        value_type = ValueType.query.get(value_type_id)
        if not value_type:
            return None

        eligible_values = []
        total_challenges = 0

        for challenge in challenges:
            # Check if roll-up is enabled for this challenge
            rollup_rule = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_CHALLENGE,
                source_id=challenge.id,
                value_type_id=value_type_id,
                rollup_enabled=True
            ).first()

            if not rollup_rule:
                continue

            total_challenges += 1

            # Get the challenge-level aggregation
            challenge_agg = AggregationService.get_initiative_to_challenge_rollup(
                challenge.id, value_type_id
            )

            if challenge_agg and challenge_agg['value'] is not None and challenge_agg['is_complete']:
                eligible_values.append(challenge_agg['value'])

        if not eligible_values:
            return {
                'value': None,
                'count_total': total_challenges,
                'count_included': 0,
                'is_complete': False
            }

        # Get formula
        formula = value_type.default_aggregation_formula
        rule = RollupRule.query.filter_by(
            source_type=RollupRule.SOURCE_CHALLENGE,
            value_type_id=value_type_id,
            rollup_enabled=True
        ).first()

        if rule:
            formula = rule.get_formula()

        aggregated = AggregationService.aggregate_values(eligible_values, formula, value_type)

        return {
            'value': aggregated,
            'count_total': total_challenges,
            'count_included': len(eligible_values),
            'is_complete': len(eligible_values) == total_challenges and total_challenges > 0
        }
