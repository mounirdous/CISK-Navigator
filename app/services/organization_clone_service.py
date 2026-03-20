"""
Organization Clone Service

Creates a copy of an organization with all its structure but without contributed data.
"""

from app.extensions import db
from app.models import (
    KPI,
    Challenge,
    ChallengeInitiativeLink,
    Initiative,
    InitiativeSystemLink,
    KPIValueTypeConfig,
    Organization,
    RollupRule,
    Space,
    System,
    UserOrganizationMembership,
    ValueType,
)


class OrganizationCloneService:
    """Service for cloning organizations"""

    @staticmethod
    def clone_organization(source_org_id, new_org_name, new_org_description=None, cloned_by_user_id=None):
        """
        Clone an organization with all its structure.

        Creates a complete copy of:
        - Value Types
        - Spaces, Challenges, Initiatives, Systems, KPIs
        - All links and configurations
        - Rollup rules

        Does NOT copy:
        - User memberships
        - Contributions
        - Consensus values

        Args:
            source_org_id: ID of organization to clone
            new_org_name: Name for the new organization
            new_org_description: Optional description

        Returns:
            dict with clone results and statistics
        """
        source_org = Organization.query.get(source_org_id)
        if not source_org:
            return {"success": False, "error": "Source organization not found"}

        try:
            # Create new organization
            new_org = Organization(
                name=new_org_name, description=new_org_description or f"Clone of {source_org.name}", is_active=True
            )
            db.session.add(new_org)
            db.session.flush()

            stats = {
                "value_types": 0,
                "spaces": 0,
                "challenges": 0,
                "initiatives": 0,
                "systems": 0,
                "kpis": 0,
                "links": 0,
                "configs": 0,
                "rollup_rules": 0,
            }

            # Maps old IDs to new objects for linking
            value_type_map = {}
            space_map = {}
            challenge_map = {}
            initiative_map = {}
            system_map = {}
            kpi_map = {}

            # 1. Clone Value Types
            for old_vt in source_org.value_types:
                new_vt = ValueType(
                    organization_id=new_org.id,
                    name=old_vt.name,
                    kind=old_vt.kind,
                    numeric_format=old_vt.numeric_format,
                    decimal_places=old_vt.decimal_places,
                    unit_label=old_vt.unit_label,
                    default_aggregation_formula=old_vt.default_aggregation_formula,
                    calculation_type=old_vt.calculation_type,
                    calculation_config=old_vt.calculation_config,
                    is_active=old_vt.is_active,
                )
                db.session.add(new_vt)
                db.session.flush()
                value_type_map[old_vt.id] = new_vt
                stats["value_types"] += 1

            # 2. Clone Spaces
            for old_space in source_org.spaces:
                new_space = Space(
                    organization_id=new_org.id,
                    name=old_space.name,
                    description=old_space.description,
                    space_label=old_space.space_label,
                    display_order=old_space.display_order,
                )
                db.session.add(new_space)
                db.session.flush()
                space_map[old_space.id] = new_space
                stats["spaces"] += 1

            # 3. Clone Challenges
            for old_challenge in source_org.challenges:
                new_challenge = Challenge(
                    organization_id=new_org.id,
                    space_id=space_map[old_challenge.space_id].id,
                    name=old_challenge.name,
                    description=old_challenge.description,
                    display_order=old_challenge.display_order,
                )
                db.session.add(new_challenge)
                db.session.flush()
                challenge_map[old_challenge.id] = new_challenge
                stats["challenges"] += 1

            # 4. Clone Initiatives
            for old_init in source_org.initiatives:
                new_init = Initiative(
                    organization_id=new_org.id,
                    name=old_init.name,
                    description=old_init.description,
                )
                db.session.add(new_init)
                db.session.flush()
                initiative_map[old_init.id] = new_init
                stats["initiatives"] += 1

            # 5. Clone Systems
            for old_system in source_org.systems:
                new_system = System(
                    organization_id=new_org.id,
                    name=old_system.name,
                    description=old_system.description,
                )
                db.session.add(new_system)
                db.session.flush()
                system_map[old_system.id] = new_system
                stats["systems"] += 1

            # 6. Clone ChallengeInitiativeLinks
            for old_link in (
                db.session.query(ChallengeInitiativeLink)
                .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
                .filter(Challenge.organization_id == source_org_id)
                .all()
            ):
                new_link = ChallengeInitiativeLink(
                    challenge_id=challenge_map[old_link.challenge_id].id,
                    initiative_id=initiative_map[old_link.initiative_id].id,
                )
                db.session.add(new_link)
                stats["links"] += 1

            db.session.flush()

            # 7. Clone InitiativeSystemLinks
            for old_link in (
                db.session.query(InitiativeSystemLink)
                .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
                .filter(Initiative.organization_id == source_org_id)
                .all()
            ):
                new_link = InitiativeSystemLink(
                    initiative_id=initiative_map[old_link.initiative_id].id, system_id=system_map[old_link.system_id].id
                )
                db.session.add(new_link)
                stats["links"] += 1

            db.session.flush()

            # 8. Clone KPIs and their configs
            for old_kpi in (
                db.session.query(KPI)
                .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
                .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
                .filter(Initiative.organization_id == source_org_id)
                .all()
            ):
                # Find the new init_system_link
                old_link = old_kpi.initiative_system_link
                new_init_id = initiative_map[old_link.initiative_id].id
                new_system_id = system_map[old_link.system_id].id

                new_link = InitiativeSystemLink.query.filter_by(
                    initiative_id=new_init_id, system_id=new_system_id
                ).first()

                new_kpi = KPI(initiative_system_link_id=new_link.id, name=old_kpi.name, description=old_kpi.description)
                db.session.add(new_kpi)
                db.session.flush()
                kpi_map[old_kpi.id] = new_kpi
                stats["kpis"] += 1

                # Clone KPIValueTypeConfigs (colors)
                for old_config in old_kpi.value_type_configs:
                    new_config = KPIValueTypeConfig(
                        kpi_id=new_kpi.id,
                        value_type_id=value_type_map[old_config.value_type_id].id,
                        color_positive=old_config.color_positive,
                        color_zero=old_config.color_zero,
                        color_negative=old_config.color_negative,
                    )
                    db.session.add(new_config)
                    stats["configs"] += 1

            db.session.flush()

            # 9. Clone RollupRules
            # RollupRules are polymorphic - they can be attached to InitiativeSystemLinks, ChallengeInitiativeLinks, or Challenges

            # 9a. Clone RollupRules for InitiativeSystemLinks
            old_init_system_link_ids = [
                link.id
                for link in (
                    db.session.query(InitiativeSystemLink)
                    .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
                    .filter(Initiative.organization_id == source_org_id)
                    .all()
                )
            ]

            for old_rule in (
                db.session.query(RollupRule)
                .filter(
                    RollupRule.source_type == "initiative_system", RollupRule.source_id.in_(old_init_system_link_ids)
                )
                .all()
            ):
                # Find the new InitiativeSystemLink
                old_link = InitiativeSystemLink.query.get(old_rule.source_id)
                new_init_id = initiative_map[old_link.initiative_id].id
                new_system_id = system_map[old_link.system_id].id
                new_link = InitiativeSystemLink.query.filter_by(
                    initiative_id=new_init_id, system_id=new_system_id
                ).first()

                new_rule = RollupRule(
                    source_type="initiative_system",
                    source_id=new_link.id,
                    value_type_id=value_type_map[old_rule.value_type_id].id,
                    rollup_enabled=old_rule.rollup_enabled,
                    formula_override=old_rule.formula_override,
                )
                db.session.add(new_rule)
                stats["rollup_rules"] += 1

            # 9b. Clone RollupRules for ChallengeInitiativeLinks
            old_challenge_init_link_ids = [
                link.id
                for link in (
                    db.session.query(ChallengeInitiativeLink)
                    .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
                    .filter(Challenge.organization_id == source_org_id)
                    .all()
                )
            ]

            for old_rule in (
                db.session.query(RollupRule)
                .filter(
                    RollupRule.source_type == "challenge_initiative",
                    RollupRule.source_id.in_(old_challenge_init_link_ids),
                )
                .all()
            ):
                # Find the new ChallengeInitiativeLink
                old_link = ChallengeInitiativeLink.query.get(old_rule.source_id)
                new_challenge_id = challenge_map[old_link.challenge_id].id
                new_init_id = initiative_map[old_link.initiative_id].id
                new_link = ChallengeInitiativeLink.query.filter_by(
                    challenge_id=new_challenge_id, initiative_id=new_init_id
                ).first()

                new_rule = RollupRule(
                    source_type="challenge_initiative",
                    source_id=new_link.id,
                    value_type_id=value_type_map[old_rule.value_type_id].id,
                    rollup_enabled=old_rule.rollup_enabled,
                    formula_override=old_rule.formula_override,
                )
                db.session.add(new_rule)
                stats["rollup_rules"] += 1

            # 9c. Clone RollupRules for Challenges
            old_challenge_ids = [challenge.id for challenge in source_org.challenges]

            for old_rule in (
                db.session.query(RollupRule)
                .filter(RollupRule.source_type == "challenge", RollupRule.source_id.in_(old_challenge_ids))
                .all()
            ):
                # Find the new Challenge
                new_challenge_id = challenge_map[old_rule.source_id].id

                new_rule = RollupRule(
                    source_type="challenge",
                    source_id=new_challenge_id,
                    value_type_id=value_type_map[old_rule.value_type_id].id,
                    rollup_enabled=old_rule.rollup_enabled,
                    formula_override=old_rule.formula_override,
                )
                db.session.add(new_rule)
                stats["rollup_rules"] += 1

            # Add the cloning user as org admin so the new org is visible in their menu
            if cloned_by_user_id:
                membership = UserOrganizationMembership(
                    user_id=cloned_by_user_id,
                    organization_id=new_org.id,
                    is_org_admin=True,
                )
                db.session.add(membership)

            db.session.commit()

            return {
                "success": True,
                "new_organization_id": new_org.id,
                "new_organization_name": new_org.name,
                "statistics": stats,
            }

        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
