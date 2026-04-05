"""
Organization Clone Service

Creates a copy of an organization with all its structure but without contributed data.
"""

from app.extensions import db
from app.models import (
    KPI,
    Challenge,
    ChallengeInitiativeLink,
    EntityLink,
    EntityTypeDefault,
    GeographyRegion,
    GovernanceBody,
    ImpactLevel,
    Initiative,
    InitiativeSystemLink,
    KPIGeographyAssignment,
    KPIGovernanceBodyLink,
    KPIValueTypeConfig,
    Organization,
    RollupRule,
    Space,
    StrategicPillar,
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
        - Organization settings (logo, colors, Porter's, impact config, tags)
        - Impact Levels, Entity Type Defaults, Strategic Pillars
        - Governance Bodies + KPI links
        - Geography hierarchy (Regions, Countries, Sites) + KPI assignments
        - Value Types
        - Spaces, Challenges, Initiatives, Systems, KPIs (with all fields)
        - All links and configurations (with all fields)
        - Rollup rules
        - Entity Links (public only)

        Does NOT copy:
        - User memberships (except cloning user)
        - Contributions, Consensus values, Snapshots
        - Comments, Mentions, Audit logs
        - Action Items, Stakeholders, Decisions
        - User Filter Presets, Saved Charts

        Returns:
            dict with clone results and statistics
        """
        source_org = Organization.query.get(source_org_id)
        if not source_org:
            return {"success": False, "error": "Source organization not found"}

        try:
            # Create new organization with all settings
            new_org = Organization(
                name=new_org_name,
                description=new_org_description or f"Clone of {source_org.name}",
                is_active=True,
                logo_data=source_org.logo_data,
                logo_mime_type=source_org.logo_mime_type,
                map_country_color_with_kpis=source_org.map_country_color_with_kpis,
                map_country_color_no_kpis=source_org.map_country_color_no_kpis,
                impact_calc_method=source_org.impact_calc_method,
                impact_qfd_matrix=source_org.impact_qfd_matrix,
                impact_reinforce_weights=source_org.impact_reinforce_weights,
                impact_no_consensus_color=source_org.impact_no_consensus_color,
                impact_not_set_color=source_org.impact_not_set_color,
                strategy_enabled=source_org.strategy_enabled,
                decision_tags=source_org.decision_tags,
                action_tags=source_org.action_tags,
                porters_new_entrants=source_org.porters_new_entrants,
                porters_suppliers=source_org.porters_suppliers,
                porters_buyers=source_org.porters_buyers,
                porters_substitutes=source_org.porters_substitutes,
                porters_rivalry=source_org.porters_rivalry,
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
                "governance_bodies": 0,
                "governance_body_links": 0,
                "strategic_pillars": 0,
                "impact_levels": 0,
                "entity_type_defaults": 0,
                "geography": 0,
                "geography_assignments": 0,
                "entity_links": 0,
            }

            # Maps old IDs to new objects for linking
            value_type_map = {}
            space_map = {}
            challenge_map = {}
            initiative_map = {}
            system_map = {}
            kpi_map = {}
            governance_body_map = {}
            geo_region_map = {}
            geo_country_map = {}
            geo_site_map = {}

            # 0a. Clone Impact Levels
            for old_il in ImpactLevel.query.filter_by(organization_id=source_org_id).all():
                new_il = ImpactLevel(
                    organization_id=new_org.id,
                    level=old_il.level,
                    label=old_il.label,
                    icon=old_il.icon,
                    weight=old_il.weight,
                    color=old_il.color,
                )
                db.session.add(new_il)
                stats["impact_levels"] += 1

            # 0b. Clone Entity Type Defaults
            for old_etd in EntityTypeDefault.query.filter_by(organization_id=source_org_id).all():
                new_etd = EntityTypeDefault(
                    organization_id=new_org.id,
                    entity_type=old_etd.entity_type,
                    default_color=old_etd.default_color,
                    default_icon=old_etd.default_icon,
                    default_logo_data=old_etd.default_logo_data,
                    default_logo_mime_type=old_etd.default_logo_mime_type,
                    display_name=old_etd.display_name,
                    description=old_etd.description,
                )
                db.session.add(new_etd)
                stats["entity_type_defaults"] += 1

            # 0c. Clone Strategic Pillars
            for old_sp in StrategicPillar.query.filter_by(organization_id=source_org_id).order_by(StrategicPillar.display_order).all():
                new_sp = StrategicPillar(
                    organization_id=new_org.id,
                    name=old_sp.name,
                    description=old_sp.description,
                    display_order=old_sp.display_order,
                    accent_color=old_sp.accent_color,
                    icon_data=old_sp.icon_data,
                    icon_mime_type=old_sp.icon_mime_type,
                    bs_icon=old_sp.bs_icon,
                )
                db.session.add(new_sp)
                stats["strategic_pillars"] += 1

            # 0d. Clone Governance Bodies
            for old_gb in GovernanceBody.query.filter_by(organization_id=source_org_id).all():
                new_gb = GovernanceBody(
                    organization_id=new_org.id,
                    name=old_gb.name,
                    abbreviation=old_gb.abbreviation,
                    description=old_gb.description,
                    color=old_gb.color,
                    display_order=old_gb.display_order,
                    is_active=old_gb.is_active,
                    is_default=old_gb.is_default,
                    is_global=old_gb.is_global,
                )
                db.session.add(new_gb)
                db.session.flush()
                governance_body_map[old_gb.id] = new_gb
                stats["governance_bodies"] += 1

            # 0e. Clone Geography hierarchy
            for old_region in GeographyRegion.query.filter_by(organization_id=source_org_id).order_by(GeographyRegion.display_order).all():
                new_region = GeographyRegion(
                    organization_id=new_org.id,
                    name=old_region.name,
                    code=old_region.code,
                    display_order=old_region.display_order,
                )
                db.session.add(new_region)
                db.session.flush()
                geo_region_map[old_region.id] = new_region
                stats["geography"] += 1

                for old_country in old_region.countries:
                    new_country = type(old_country)(
                        region_id=new_region.id,
                        name=old_country.name,
                        code=old_country.code,
                        iso_code=old_country.iso_code,
                        latitude=old_country.latitude,
                        longitude=old_country.longitude,
                        display_order=old_country.display_order,
                    )
                    db.session.add(new_country)
                    db.session.flush()
                    geo_country_map[old_country.id] = new_country
                    stats["geography"] += 1

                    for old_site in old_country.sites:
                        new_site = type(old_site)(
                            country_id=new_country.id,
                            name=old_site.name,
                            code=old_site.code,
                            address=old_site.address,
                            latitude=old_site.latitude,
                            longitude=old_site.longitude,
                            is_active=old_site.is_active,
                            display_order=old_site.display_order,
                        )
                        db.session.add(new_site)
                        db.session.flush()
                        geo_site_map[old_site.id] = new_site
                        stats["geography"] += 1

            db.session.flush()

            # 1. Clone Value Types
            for old_vt in source_org.value_types:
                new_vt = ValueType(
                    organization_id=new_org.id,
                    name=old_vt.name,
                    description=old_vt.description,
                    kind=old_vt.kind,
                    numeric_format=old_vt.numeric_format,
                    decimal_places=old_vt.decimal_places,
                    unit_label=old_vt.unit_label,
                    default_aggregation_formula=old_vt.default_aggregation_formula,
                    calculation_type=old_vt.calculation_type,
                    calculation_config=old_vt.calculation_config,
                    display_order=old_vt.display_order,
                    is_active=old_vt.is_active,
                )
                db.session.add(new_vt)
                db.session.flush()
                value_type_map[old_vt.id] = new_vt
                stats["value_types"] += 1

            # 2. Clone Spaces (with all fields)
            for old_space in source_org.spaces:
                new_space = Space(
                    organization_id=new_org.id,
                    name=old_space.name,
                    description=old_space.description,
                    space_label=old_space.space_label,
                    display_order=old_space.display_order,
                    is_private=old_space.is_private,
                    logo_data=old_space.logo_data,
                    logo_mime_type=old_space.logo_mime_type,
                    impact_level=old_space.impact_level,
                    impact_no_consensus=old_space.impact_no_consensus,
                    impact_no_consensus_note=old_space.impact_no_consensus_note,
                    swot_strengths=old_space.swot_strengths,
                    swot_weaknesses=old_space.swot_weaknesses,
                    swot_opportunities=old_space.swot_opportunities,
                    swot_threats=old_space.swot_threats,
                )
                db.session.add(new_space)
                db.session.flush()
                space_map[old_space.id] = new_space
                stats["spaces"] += 1

            # 3. Clone Challenges (with all fields)
            for old_challenge in source_org.challenges:
                new_challenge = Challenge(
                    organization_id=new_org.id,
                    space_id=space_map[old_challenge.space_id].id,
                    name=old_challenge.name,
                    description=old_challenge.description,
                    display_order=old_challenge.display_order,
                    logo_data=old_challenge.logo_data,
                    logo_mime_type=old_challenge.logo_mime_type,
                    impact_level=old_challenge.impact_level,
                    impact_no_consensus=old_challenge.impact_no_consensus,
                    impact_no_consensus_note=old_challenge.impact_no_consensus_note,
                )
                db.session.add(new_challenge)
                db.session.flush()
                challenge_map[old_challenge.id] = new_challenge
                stats["challenges"] += 1

            # 4. Clone Initiatives (with all fields)
            for old_init in source_org.initiatives:
                new_init = Initiative(
                    organization_id=new_org.id,
                    name=old_init.name,
                    description=old_init.description,
                    logo_data=old_init.logo_data,
                    logo_mime_type=old_init.logo_mime_type,
                    mission=old_init.mission,
                    success_criteria=old_init.success_criteria,
                    responsible_person=old_init.responsible_person,
                    team_members=old_init.team_members,
                    handover_organization=old_init.handover_organization,
                    deliverables=old_init.deliverables,
                    group_label=old_init.group_label,
                    impact_level=old_init.impact_level,
                    impact_no_consensus=old_init.impact_no_consensus,
                    impact_no_consensus_note=old_init.impact_no_consensus_note,
                )
                db.session.add(new_init)
                db.session.flush()
                initiative_map[old_init.id] = new_init
                stats["initiatives"] += 1

            # 5. Clone Systems (with all fields)
            for old_system in source_org.systems:
                new_system = System(
                    organization_id=new_org.id,
                    name=old_system.name,
                    description=old_system.description,
                    logo_data=old_system.logo_data,
                    logo_mime_type=old_system.logo_mime_type,
                    linked_organization_id=old_system.linked_organization_id,
                    impact_level=old_system.impact_level,
                    impact_no_consensus=old_system.impact_no_consensus,
                    impact_no_consensus_note=old_system.impact_no_consensus_note,
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

            # 8. Clone KPIs and their configs (with all fields)
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

                new_kpi = KPI(
                    initiative_system_link_id=new_link.id,
                    name=old_kpi.name,
                    description=old_kpi.description,
                    logo_data=old_kpi.logo_data,
                    logo_mime_type=old_kpi.logo_mime_type,
                    display_order=old_kpi.display_order,
                    impact_level=old_kpi.impact_level,
                    impact_no_consensus=old_kpi.impact_no_consensus,
                    impact_no_consensus_note=old_kpi.impact_no_consensus_note,
                    is_archived=old_kpi.is_archived,
                )
                db.session.add(new_kpi)
                db.session.flush()
                kpi_map[old_kpi.id] = new_kpi
                stats["kpis"] += 1

                # Clone KPIValueTypeConfigs (with all fields)
                for old_config in old_kpi.value_type_configs:
                    if old_config.value_type_id not in value_type_map:
                        continue
                    new_config = KPIValueTypeConfig(
                        kpi_id=new_kpi.id,
                        value_type_id=value_type_map[old_config.value_type_id].id,
                        display_order=old_config.display_order,
                        color_positive=old_config.color_positive,
                        color_zero=old_config.color_zero,
                        color_negative=old_config.color_negative,
                        target_value=old_config.target_value,
                        target_date=old_config.target_date,
                        target_direction=old_config.target_direction,
                        target_tolerance_pct=old_config.target_tolerance_pct,
                        target_list_value=old_config.target_list_value,
                        display_scale=old_config.display_scale,
                        display_decimals=old_config.display_decimals,
                        calculation_type=old_config.calculation_type if old_config.calculation_type != 'linked' else 'manual',
                        calculation_config=old_config.calculation_config if old_config.calculation_type != 'linked' else None,
                    )
                    db.session.add(new_config)
                    stats["configs"] += 1

                # Clone KPI Governance Body Links
                for old_gb_link in old_kpi.governance_body_links:
                    if old_gb_link.governance_body_id in governance_body_map:
                        new_gb_link = KPIGovernanceBodyLink(
                            kpi_id=new_kpi.id,
                            governance_body_id=governance_body_map[old_gb_link.governance_body_id].id,
                        )
                        db.session.add(new_gb_link)
                        stats["governance_body_links"] += 1

                # Clone KPI Geography Assignments
                for old_ga in KPIGeographyAssignment.query.filter_by(kpi_id=old_kpi.id).all():
                    new_ga = KPIGeographyAssignment(kpi_id=new_kpi.id)
                    if old_ga.region_id and old_ga.region_id in geo_region_map:
                        new_ga.region_id = geo_region_map[old_ga.region_id].id
                    if old_ga.country_id and old_ga.country_id in geo_country_map:
                        new_ga.country_id = geo_country_map[old_ga.country_id].id
                    if old_ga.site_id and old_ga.site_id in geo_site_map:
                        new_ga.site_id = geo_site_map[old_ga.site_id].id
                    db.session.add(new_ga)
                    stats["geography_assignments"] += 1

            db.session.flush()

            # 9. Clone RollupRules

            # 9a. RollupRules for InitiativeSystemLinks
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

            # 9b. RollupRules for ChallengeInitiativeLinks
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

            # 9c. RollupRules for Challenges
            old_challenge_ids = [challenge.id for challenge in source_org.challenges]

            for old_rule in (
                db.session.query(RollupRule)
                .filter(RollupRule.source_type == "challenge", RollupRule.source_id.in_(old_challenge_ids))
                .all()
            ):
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

            # 10. Clone Entity Links (public only)
            entity_type_map = {
                "space": space_map,
                "challenge": challenge_map,
                "initiative": initiative_map,
                "system": system_map,
                "kpi": kpi_map,
            }
            for entity_type, id_map in entity_type_map.items():
                for old_id, new_obj in id_map.items():
                    for old_link in EntityLink.query.filter_by(entity_type=entity_type, entity_id=old_id, is_public=True).all():
                        new_el = EntityLink(
                            entity_type=entity_type,
                            entity_id=new_obj.id,
                            url=old_link.url,
                            title=old_link.title,
                            is_public=True,
                            display_order=old_link.display_order,
                            created_by=cloned_by_user_id,
                        )
                        db.session.add(new_el)
                        stats["entity_links"] += 1

            # Add the cloning user as org admin
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
