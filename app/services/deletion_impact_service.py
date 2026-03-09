"""
Deletion Impact Service

Analyzes the impact of deleting entities and provides impact preview.
"""

from app.models import (
    KPI,
    Challenge,
    ChallengeInitiativeLink,
    Contribution,
    Initiative,
    InitiativeSystemLink,
    KPIValueTypeConfig,
    RollupRule,
    Space,
    System,
)


class DeletionImpactService:
    """
    Service for analyzing deletion impact and generating impact reports.
    """

    @staticmethod
    def analyze_challenge_deletion(challenge_id):
        """
        Analyze the impact of deleting a challenge.

        Returns:
            dict with counts of entities that will be deleted or affected
        """
        from app.extensions import db

        challenge = Challenge.query.get(challenge_id)
        if not challenge:
            return None

        impact = {
            "challenges": 1,
            "challenge_initiative_links": 0,
            "orphaned_initiatives": 0,
            "preserved_initiatives": 0,
            "initiative_system_links": 0,
            "orphaned_systems": 0,
            "preserved_systems": 0,
            "kpis": 0,
            "kpi_value_type_configs": 0,
            "contributions": 0,
            "rollup_rules": 0,
        }

        # Get challenge-initiative links
        ci_links = ChallengeInitiativeLink.query.filter_by(challenge_id=challenge_id).all()
        impact["challenge_initiative_links"] = len(ci_links)

        for ci_link in ci_links:
            initiative = ci_link.initiative

            # Check if this initiative has other challenge links
            other_links = ChallengeInitiativeLink.query.filter(
                ChallengeInitiativeLink.initiative_id == initiative.id,
                ChallengeInitiativeLink.challenge_id != challenge_id,
            ).count()

            if other_links == 0:
                # This initiative will be orphaned and deleted
                impact["orphaned_initiatives"] += 1

                # Count its system links and dependent data
                is_links = InitiativeSystemLink.query.filter_by(initiative_id=initiative.id).all()
                impact["initiative_system_links"] += len(is_links)

                for is_link in is_links:
                    system = is_link.system

                    # Check if this system has other initiative links
                    other_sys_links = InitiativeSystemLink.query.filter(
                        InitiativeSystemLink.system_id == system.id, InitiativeSystemLink.initiative_id != initiative.id
                    ).count()

                    if other_sys_links == 0:
                        impact["orphaned_systems"] += 1
                    else:
                        impact["preserved_systems"] += 1

                    # Count KPIs and dependent data
                    kpis = is_link.kpis
                    impact["kpis"] += len(kpis)

                    for kpi in kpis:
                        configs = kpi.value_type_configs
                        impact["kpi_value_type_configs"] += len(configs)

                        for config in configs:
                            impact["contributions"] += len(config.contributions)

                    # Count rollup rules for this link
                    rollup_rules = RollupRule.query.filter_by(
                        source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM, source_id=is_link.id
                    ).count()
                    impact["rollup_rules"] += rollup_rules
            else:
                impact["preserved_initiatives"] += 1

            # Count rollup rules for the challenge-initiative link
            ci_rollup_rules = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE, source_id=ci_link.id
            ).count()
            impact["rollup_rules"] += ci_rollup_rules

        # Count rollup rules for the challenge itself
        challenge_rollup_rules = RollupRule.query.filter_by(
            source_type=RollupRule.SOURCE_CHALLENGE, source_id=challenge_id
        ).count()
        impact["rollup_rules"] += challenge_rollup_rules

        return impact

    @staticmethod
    def analyze_space_deletion(space_id):
        """
        Analyze the impact of deleting a space.

        This includes all challenges and their cascading deletions.
        """
        space = Space.query.get(space_id)
        if not space:
            return None

        total_impact = {
            "spaces": 1,
            "challenges": 0,
            "challenge_initiative_links": 0,
            "orphaned_initiatives": 0,
            "preserved_initiatives": 0,
            "initiative_system_links": 0,
            "orphaned_systems": 0,
            "preserved_systems": 0,
            "kpis": 0,
            "kpi_value_type_configs": 0,
            "contributions": 0,
            "rollup_rules": 0,
        }

        # Get all challenges in this space
        challenges = Challenge.query.filter_by(space_id=space_id).all()
        total_impact["challenges"] = len(challenges)

        for challenge in challenges:
            challenge_impact = DeletionImpactService.analyze_challenge_deletion(challenge.id)
            if challenge_impact:
                # Aggregate impacts (don't double-count challenges)
                for key, value in challenge_impact.items():
                    if key != "challenges":
                        total_impact[key] += value

        return total_impact

    @staticmethod
    def analyze_initiative_deletion(initiative_id, detach_from_challenge_id=None):
        """
        Analyze the impact of deleting an initiative.

        Args:
            initiative_id: Initiative to analyze
            detach_from_challenge_id: If provided, only detach from this challenge (not delete)

        Returns:
            dict with deletion impact
        """
        initiative = Initiative.query.get(initiative_id)
        if not initiative:
            return None

        if detach_from_challenge_id:
            # Just detaching, minimal impact
            link = ChallengeInitiativeLink.query.filter_by(
                challenge_id=detach_from_challenge_id, initiative_id=initiative_id
            ).first()

            if link:
                rollup_rules = RollupRule.query.filter_by(
                    source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE, source_id=link.id
                ).count()

                return {"detach_only": True, "challenge_initiative_links": 1, "rollup_rules": rollup_rules}
            return None

        # Full deletion
        impact = {
            "initiatives": 1,
            "challenge_initiative_links": 0,
            "initiative_system_links": 0,
            "orphaned_systems": 0,
            "preserved_systems": 0,
            "kpis": 0,
            "kpi_value_type_configs": 0,
            "contributions": 0,
            "rollup_rules": 0,
        }

        # Challenge links
        ci_links = ChallengeInitiativeLink.query.filter_by(initiative_id=initiative_id).all()
        impact["challenge_initiative_links"] = len(ci_links)

        for ci_link in ci_links:
            rollup_rules = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_CHALLENGE_INITIATIVE, source_id=ci_link.id
            ).count()
            impact["rollup_rules"] += rollup_rules

        # System links
        is_links = InitiativeSystemLink.query.filter_by(initiative_id=initiative_id).all()
        impact["initiative_system_links"] = len(is_links)

        for is_link in is_links:
            system = is_link.system

            # Check if system has other links
            other_links = InitiativeSystemLink.query.filter(
                InitiativeSystemLink.system_id == system.id, InitiativeSystemLink.initiative_id != initiative_id
            ).count()

            if other_links == 0:
                impact["orphaned_systems"] += 1
            else:
                impact["preserved_systems"] += 1

            # KPIs
            kpis = is_link.kpis
            impact["kpis"] += len(kpis)

            for kpi in kpis:
                configs = kpi.value_type_configs
                impact["kpi_value_type_configs"] += len(configs)

                for config in configs:
                    impact["contributions"] += len(config.contributions)

            # Rollup rules
            rollup_rules = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM, source_id=is_link.id
            ).count()
            impact["rollup_rules"] += rollup_rules

        return impact

    @staticmethod
    def analyze_system_deletion(system_id, detach_from_initiative_id=None):
        """
        Analyze the impact of deleting a system.

        Args:
            system_id: System to analyze
            detach_from_initiative_id: If provided, only detach from this initiative

        Returns:
            dict with deletion impact
        """
        system = System.query.get(system_id)
        if not system:
            return None

        if detach_from_initiative_id:
            # Just detaching
            link = InitiativeSystemLink.query.filter_by(
                initiative_id=detach_from_initiative_id, system_id=system_id
            ).first()

            if link:
                kpis = link.kpis
                kpi_configs = sum(len(kpi.value_type_configs) for kpi in kpis)
                contributions = sum(len(config.contributions) for kpi in kpis for config in kpi.value_type_configs)
                rollup_rules = RollupRule.query.filter_by(
                    source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM, source_id=link.id
                ).count()

                return {
                    "detach_only": True,
                    "initiative_system_links": 1,
                    "kpis": len(kpis),
                    "kpi_value_type_configs": kpi_configs,
                    "contributions": contributions,
                    "rollup_rules": rollup_rules,
                }
            return None

        # Full deletion
        impact = {
            "systems": 1,
            "initiative_system_links": 0,
            "kpis": 0,
            "kpi_value_type_configs": 0,
            "contributions": 0,
            "rollup_rules": 0,
        }

        is_links = InitiativeSystemLink.query.filter_by(system_id=system_id).all()
        impact["initiative_system_links"] = len(is_links)

        for is_link in is_links:
            kpis = is_link.kpis
            impact["kpis"] += len(kpis)

            for kpi in kpis:
                configs = kpi.value_type_configs
                impact["kpi_value_type_configs"] += len(configs)

                for config in configs:
                    impact["contributions"] += len(config.contributions)

            rollup_rules = RollupRule.query.filter_by(
                source_type=RollupRule.SOURCE_INITIATIVE_SYSTEM, source_id=is_link.id
            ).count()
            impact["rollup_rules"] += rollup_rules

        return impact
