"""
Full Backup/Restore Service

Complete data backup including structure AND data.
Uses JSON format for portability and human-readability.

BACKUP FORMAT VERSION: 9.0 (Updated 2026-03-25)

What's backed up:
================
✅ Organization info (name, description)
✅ Users and organization permissions
✅ Value Types (with numeric formats, units, decimals)
✅ Governance Bodies
✅ Full CISK hierarchy:
   - Spaces (with SWOT analysis)
   - Challenges
   - Initiatives (with mission, responsible person, team, deliverables, steps, impact)
   - Systems
   - KPIs (with logos)
✅ Porter's Five Forces (on organization)
✅ KPI Configurations:
   - Value type configs
   - Colors (positive/zero/negative)
   - Display scale and decimals
   - Target tracking (value, date, direction, tolerance)
   - Baseline snapshots
   - **Calculation type** (manual/linked/formula)
   - **Calculation formulas** (JSON config)
   - **Linked KPI references** (cross-org links)
✅ All contributions (actual data!)
✅ Stakeholder Mapping (v2.0+):
   - Stakeholders (with sites)
   - Relationships between stakeholders
   - Entity links (stakeholder → CISK entities)
✅ Stakeholder Maps (v2.0+):
   - Named maps with memberships
   - Visibility settings
✅ Action Items & Memos (v3.0+):
   - All action items and memos
   - Governance body links
   - Entity mentions (by json_id + entity_name fallback — collision-free since v8.0)
✅ URL Links / EntityLinks (v4.0+):
   - All URL links attached to Space, Challenge, Initiative, System, KPI, Action Item
✅ Entity Type Branding (v9.0+):
   - Default colors, icons, display names, descriptions per entity type
   - Default logos for each entity type (if configured)
✅ Saved Views / Filter Presets (v5.0+):
   - All workspace and action register saved views per user
✅ Full Geography hierarchy (v6.0+):
   - Regions (org-scoped), Countries (with coordinates), Sites (with coordinates)
✅ Initiative Execution Tracking (v7.0+):
   - Progress updates (RAG status, accomplishments, next steps, blockers, timestamps)

What's NOT backed up:
=====================
⚠️  User passwords - Users matched by login/email
⚠️  Audit logs - Historical data not portable

Version Compatibility:
=====================
- Backup format v1.0: Original release (before stakeholders, formulas, linked KPIs)
- Backup format v2.0: Added stakeholders, maps, formulas, linked KPIs
- Backup format v3.0: Added action items and memos
- Backup format v4.0: Added EntityLink (URL links) for all CISK entities and action items
- Backup format v5.0: Added saved views (UserFilterPreset) per user
- Backup format v6.0: Full geography hierarchy (was incorrectly treated as global)
- Backup format v7.0: Initiative progress updates (execution tracking)
- Backup format v8.0: json_id cross-references in mentions and stakeholder entity links (collision-free, rename-safe)
- Backup format v9.0: EntityTypeDefault branding (colors, icons, default logos per entity type)
- Always restore to same or newer app version for best compatibility
"""

import json
from datetime import datetime

from app import db
from app.models import EntityLink, GovernanceBody, Space, UserFilterPreset, ValueType


class FullBackupService:
    """Service for full organization backup and restore with all data"""

    @staticmethod
    def create_full_backup(organization_id):
        """
        Create complete backup including structure and all data.

        Returns:
            dict: Complete backup data including:
                - Metadata (timestamp, version, org info)
                - Value types
                - Governance bodies
                - Spaces/Challenges/Initiatives/Systems/KPIs (structure)
                - Contributions (actual data!)
                - KPI configurations
        """
        from app.models import Organization

        org = Organization.query.get(organization_id)
        if not org:
            return None

        from app import __version__ as app_version
        from app.db_version import DB_SCHEMA_VERSION

        backup = {
            "metadata": {
                "backup_format_version": "9.0",  # Backup format version
                "app_version": app_version,  # CISK Navigator version
                "db_schema_version": DB_SCHEMA_VERSION,  # Database schema version
                "created_at": datetime.utcnow().isoformat(),
                "organization_name": org.name,
                "organization_id": organization_id,
                "backup_type": "full",
                "compatibility_warning": f"This backup was created with CISK Navigator v{app_version} (DB schema v{DB_SCHEMA_VERSION}). "
                "Restore REQUIRES matching DB schema version for data integrity.",
            },
            "organization": FullBackupService._export_organization(org),
            "entity_branding": FullBackupService._export_entity_branding(organization_id),
            "users": FullBackupService._export_users(organization_id),
            "value_types": FullBackupService._export_value_types(organization_id),
            "governance_bodies": FullBackupService._export_governance_bodies(organization_id),
            "spaces": FullBackupService._export_spaces(organization_id),
            "stakeholders": FullBackupService._export_stakeholders(organization_id),
            "stakeholder_maps": FullBackupService._export_stakeholder_maps(organization_id),
            "geography": FullBackupService._export_geography(organization_id),
            "action_items": FullBackupService._export_action_items(organization_id),
            "filter_presets": FullBackupService._export_filter_presets(organization_id),
            "strategic_pillars": FullBackupService._export_strategic_pillars(organization_id),
            "impact_levels": FullBackupService._export_impact_levels(organization_id),
        }

        return backup

    @staticmethod
    def _export_organization(org):
        """Export organization data including logo"""
        import base64

        org_data = {
            "name": org.name,
            "description": org.description,
            "is_active": org.is_active,
            "porters_new_entrants": org.porters_new_entrants,
            "porters_suppliers": org.porters_suppliers,
            "porters_buyers": org.porters_buyers,
            "porters_substitutes": org.porters_substitutes,
            "porters_rivalry": org.porters_rivalry,
        }

        # Export logo if present
        if org.logo_data and org.logo_mime_type:
            org_data["logo"] = {
                "mime_type": org.logo_mime_type,
                "data": base64.b64encode(org.logo_data).decode("utf-8"),
            }

        return org_data

    @staticmethod
    def _export_entity_branding(organization_id):
        """Export EntityTypeDefault branding configuration (colors, icons, logos per entity type)"""
        import base64

        from app.models import EntityTypeDefault

        defaults = EntityTypeDefault.query.filter_by(organization_id=organization_id).all()
        result = []
        for d in defaults:
            entry = {
                "entity_type": d.entity_type,
                "default_color": d.default_color,
                "default_icon": d.default_icon,
                "display_name": d.display_name,
                "description": d.description,
            }
            if d.default_logo_data and d.default_logo_mime_type:
                entry["default_logo"] = {
                    "mime_type": d.default_logo_mime_type,
                    "data": base64.b64encode(d.default_logo_data).decode("utf-8"),
                }
            result.append(entry)
        return result

    @staticmethod
    def _export_users(organization_id):
        """Export all users and their permissions for this organization"""
        from app.models import User, UserOrganizationMembership

        memberships = (
            UserOrganizationMembership.query.filter_by(organization_id=organization_id)
            .join(User)
            .filter(User.is_active.is_(True))
            .all()
        )

        result = []
        for membership in memberships:
            user = membership.user
            user_data = {
                "login": user.login,
                "email": user.email,
                "display_name": user.display_name,
                "is_active": user.is_active,
                "permissions": {
                    "can_manage_spaces": membership.can_manage_spaces,
                    "can_manage_value_types": membership.can_manage_value_types,
                    "can_manage_governance_bodies": membership.can_manage_governance_bodies,
                    "can_manage_challenges": membership.can_manage_challenges,
                    "can_manage_initiatives": membership.can_manage_initiatives,
                    "can_manage_systems": membership.can_manage_systems,
                    "can_manage_kpis": membership.can_manage_kpis,
                    "can_view_comments": membership.can_view_comments,
                    "can_add_comments": membership.can_add_comments,
                    "can_view_snapshots": membership.can_view_snapshots,
                    "can_create_snapshots": membership.can_create_snapshots,
                },
            }
            result.append(user_data)

        return result

    @staticmethod
    def _export_value_types(organization_id):
        """Export all value types"""
        value_types = ValueType.query.filter_by(organization_id=organization_id).order_by(ValueType.display_order).all()

        result = []
        for vt in value_types:
            vt_data = {
                "name": vt.name,
                "description": vt.description,
                "kind": vt.kind,
                "default_aggregation_formula": vt.default_aggregation_formula,
                "is_active": vt.is_active,
                "display_order": vt.display_order,
                "calculation_type": vt.calculation_type,
            }

            # Formula configuration (if formula-based value type)
            if vt.calculation_config:
                # Store formula with both IDs and names for restore compatibility
                config = vt.calculation_config.copy()
                source_vt_ids = config.get("source_value_type_ids", [])

                # Add source value type names for restore
                source_vt_names = []
                for source_vt in value_types:
                    if source_vt.id in source_vt_ids:
                        source_vt_names.append(source_vt.name)

                vt_data["calculation_config"] = config
                vt_data["formula_source_names"] = source_vt_names  # For restore

            if vt.kind == "numeric":
                vt_data["numeric_format"] = vt.numeric_format
                if vt.decimal_places is not None:
                    vt_data["decimal_places"] = vt.decimal_places
                if vt.unit_label:
                    vt_data["unit_label"] = vt.unit_label

            if vt.kind == "list" and vt.list_options:
                vt_data["list_options"] = vt.list_options

            result.append(vt_data)

        return result

    @staticmethod
    def _export_governance_bodies(organization_id):
        """Export all governance bodies"""
        gbs = (
            GovernanceBody.query.filter_by(organization_id=organization_id).order_by(GovernanceBody.display_order).all()
        )

        result = []
        for gb in gbs:
            result.append(
                {
                    "name": gb.name,
                    "abbreviation": gb.abbreviation,
                    "description": gb.description,
                    "color": gb.color,
                    "is_active": gb.is_active,
                    "is_default": gb.is_default,
                    "display_order": gb.display_order,
                }
            )

        return result

    @staticmethod
    def _export_entity_links(entity_type, entity_id):
        """Return serialized EntityLink records for an entity, or empty list."""
        links = (
            EntityLink.query.filter_by(entity_type=entity_type, entity_id=entity_id)
            .order_by(EntityLink.display_order)
            .all()
        )
        return [{"url": lnk.url, "title": lnk.title or "", "is_public": lnk.is_public, "created_by_login": lnk.creator.login if lnk.creator else None} for lnk in links]

    @staticmethod
    def _export_filter_presets(organization_id):
        """Export all saved views (filter presets) for the organization, keyed by user login."""
        presets = UserFilterPreset.query.filter_by(organization_id=organization_id).order_by(UserFilterPreset.id).all()
        result = []
        for p in presets:
            result.append({
                "user_login": p.user.login if p.user else None,
                "feature": p.feature,
                "name": p.name,
                "filters": p.filters,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })
        return result

    @staticmethod
    def _export_impact_levels(organization_id):
        """Export impact level configuration"""
        from app.models import ImpactLevel

        levels = ImpactLevel.query.filter_by(organization_id=organization_id).order_by(ImpactLevel.level).all()
        return [{"level": lv.level, "label": lv.label, "icon": lv.icon, "weight": lv.weight, "color": lv.color} for lv in levels]

    @staticmethod
    def _export_strategic_pillars(organization_id):
        """Export strategic pillars"""
        import base64

        from app.models import StrategicPillar

        pillars = StrategicPillar.query.filter_by(organization_id=organization_id).order_by(StrategicPillar.display_order).all()
        result = []
        for p in pillars:
            data = {
                "name": p.name,
                "description": p.description,
                "accent_color": p.accent_color,
                "bs_icon": p.bs_icon,
                "display_order": p.display_order,
            }
            if p.icon_data and p.icon_mime_type:
                data["icon_b64"] = base64.b64encode(p.icon_data).decode("utf-8")
                data["icon_mime_type"] = p.icon_mime_type
            result.append(data)
        return result

    @staticmethod
    def _export_spaces(organization_id):
        """Export spaces with full hierarchy and data including logos"""
        import base64

        spaces = Space.query.filter_by(organization_id=organization_id).order_by(Space.display_order, Space.name).all()

        result = []
        for space in spaces:
            space_data = {
                "json_id": space.id,
                "name": space.name,
                "description": space.description,
                "space_label": space.space_label,
                "is_private": space.is_private,
                "display_order": space.display_order,
                "impact_level": space.impact_level,
                "swot_strengths": space.swot_strengths,
                "swot_weaknesses": space.swot_weaknesses,
                "swot_opportunities": space.swot_opportunities,
                "swot_threats": space.swot_threats,
                "links": FullBackupService._export_entity_links("space", space.id),
                "challenges": [],
            }

            # Export space logo if present
            if space.logo_data and space.logo_mime_type:
                space_data["logo"] = {
                    "mime_type": space.logo_mime_type,
                    "data": base64.b64encode(space.logo_data).decode("utf-8"),
                }

            # Export challenges
            challenges = sorted(space.challenges, key=lambda c: (c.display_order, c.name))
            for challenge in challenges:
                challenge_data = {
                    "json_id": challenge.id,
                    "name": challenge.name,
                    "description": challenge.description,
                    "display_order": challenge.display_order,
                    "impact_level": challenge.impact_level,
                    "links": FullBackupService._export_entity_links("challenge", challenge.id),
                    "initiatives": [],
                }

                # Export challenge logo if present
                if challenge.logo_data and challenge.logo_mime_type:
                    challenge_data["logo"] = {
                        "mime_type": challenge.logo_mime_type,
                        "data": base64.b64encode(challenge.logo_data).decode("utf-8"),
                    }

                # Get unique initiatives through links
                initiatives_dict = {}
                for link in challenge.initiative_links:
                    init = link.initiative
                    if init.id not in initiatives_dict:
                        initiatives_dict[init.id] = init

                initiatives = sorted(initiatives_dict.values(), key=lambda i: i.name)

                for initiative in initiatives:
                    initiative_data = {
                        "json_id": initiative.id,
                        "name": initiative.name,
                        "description": initiative.description,
                        "group_label": initiative.group_label,
                        "mission": initiative.mission,
                        "responsible_person": initiative.responsible_person,
                        "team_members": initiative.team_members,
                        "handover_organization": initiative.handover_organization,
                        "deliverables": initiative.deliverables,
                        "success_criteria": initiative.success_criteria,
                        "impact_on_challenge": initiative.impact_on_challenge,
                        "impact_rationale": initiative.impact_rationale,
                        "impact_level": initiative.impact_level,
                        "links": FullBackupService._export_entity_links("initiative", initiative.id),
                        "progress_updates": [
                            {
                                "rag_status": upd.rag_status,
                                "accomplishments": upd.accomplishments,
                                "next_steps": upd.next_steps,
                                "blockers": upd.blockers,
                                "created_at": upd.created_at.isoformat(),
                            }
                            for upd in sorted(initiative.progress_updates, key=lambda u: u.created_at)
                        ],
                        "systems": [],
                    }

                    # Export initiative logo if present
                    if initiative.logo_data and initiative.logo_mime_type:
                        initiative_data["logo"] = {
                            "mime_type": initiative.logo_mime_type,
                            "data": base64.b64encode(initiative.logo_data).decode("utf-8"),
                        }

                    # Get unique systems through links
                    systems_dict = {}
                    for link in initiative.system_links:
                        sys = link.system
                        if sys.id not in systems_dict:
                            systems_dict[sys.id] = sys

                    systems = sorted(systems_dict.values(), key=lambda s: s.name)

                    for system in systems:
                        system_data = {
                            "json_id": system.id,
                            "name": system.name,
                            "description": system.description,
                            "impact_level": system.impact_level,
                            "links": FullBackupService._export_entity_links("system", system.id),
                            "kpis": [],
                        }

                        # Export system logo if present
                        if system.logo_data and system.logo_mime_type:
                            system_data["logo"] = {
                                "mime_type": system.logo_mime_type,
                                "data": base64.b64encode(system.logo_data).decode("utf-8"),
                            }

                        # Find the link to get KPIs for this specific initiative-system pair
                        link = next(
                            (lnk for lnk in system.initiative_links if lnk.initiative_id == initiative.id), None
                        )
                        if link and link.kpis:
                            kpis = sorted(link.kpis, key=lambda k: k.name)
                            for kpi in kpis:
                                kpi_data = FullBackupService._export_kpi_with_data(kpi)
                                system_data["kpis"].append(kpi_data)

                        initiative_data["systems"].append(system_data)

                    challenge_data["initiatives"].append(initiative_data)

                space_data["challenges"].append(challenge_data)

            result.append(space_data)

        return result

    @staticmethod
    def _export_kpi_with_data(kpi):
        """Export KPI with all data including contributions, formulas, linked KPIs, and governance bodies"""
        import base64

        kpi_data = {
            "json_id": kpi.id,
            "name": kpi.name,
            "description": kpi.description,
            "is_archived": kpi.is_archived,
            "display_order": kpi.display_order,
            "impact_level": kpi.impact_level,
            "links": FullBackupService._export_entity_links("kpi", kpi.id),
            "governance_bodies": [],
            "geography_assignments": [],
            "value_types": [],
        }

        # Export logo if present
        if kpi.logo_data and kpi.logo_mime_type:
            kpi_data["logo"] = {
                "mime_type": kpi.logo_mime_type,
                "data": base64.b64encode(kpi.logo_data).decode("utf-8"),
            }

        # Export governance body links
        for link in kpi.governance_body_links:
            kpi_data["governance_bodies"].append(link.governance_body.name)

        # Export geography assignments (region/country/site links)
        for geo_assignment in kpi.geography_assignments:
            geo_data = {}
            if geo_assignment.site_id and geo_assignment.site:
                geo_data = {
                    "level": "site",
                    "site_name": geo_assignment.site.name,
                    "country_name": geo_assignment.site.country.name if geo_assignment.site.country else None,
                    "region_name": (
                        geo_assignment.site.country.region.name
                        if geo_assignment.site.country and geo_assignment.site.country.region
                        else None
                    ),
                }
            elif geo_assignment.country_id and geo_assignment.country:
                geo_data = {
                    "level": "country",
                    "country_name": geo_assignment.country.name,
                    "region_name": geo_assignment.country.region.name if geo_assignment.country.region else None,
                }
            elif geo_assignment.region_id and geo_assignment.region:
                geo_data = {
                    "level": "region",
                    "region_name": geo_assignment.region.name,
                }
            if geo_data:
                kpi_data["geography_assignments"].append(geo_data)

        # Export value type configurations with contributions
        configs = sorted(kpi.value_type_configs, key=lambda c: c.value_type.display_order)
        for config in configs:
            vt = config.value_type
            vt_config = {"name": vt.name, "contributions": []}

            # Export configuration settings
            if vt.kind == "numeric":
                if config.color_positive or config.color_zero or config.color_negative:
                    vt_config["colors"] = {
                        "positive": config.color_positive,
                        "zero": config.color_zero,
                        "negative": config.color_negative,
                    }

                if config.display_scale and config.display_scale != "default":
                    vt_config["display_scale"] = config.display_scale
                if config.display_decimals is not None:
                    vt_config["display_decimals"] = config.display_decimals

                # Target tracking
                if config.target_value is not None:
                    vt_config["target_value"] = float(config.target_value)
                if config.target_date:
                    vt_config["target_date"] = config.target_date.strftime("%Y-%m-%d")
                if config.target_direction:
                    vt_config["target_direction"] = config.target_direction
                if config.target_tolerance_pct:
                    vt_config["target_tolerance_pct"] = config.target_tolerance_pct
                if config.baseline_snapshot_id:
                    vt_config["baseline_snapshot_id"] = config.baseline_snapshot_id

            # Calculation type and formula (v1.20.0+)
            vt_config["calculation_type"] = config.calculation_type
            if config.calculation_config:
                vt_config["calculation_config"] = config.calculation_config

            # Linked KPI configuration (v1.18.0+)
            if config.calculation_type == "linked" and config.linked_source_kpi_id:
                from app.models import KPI, Organization

                source_kpi = KPI.query.get(config.linked_source_kpi_id)
                source_org = (
                    Organization.query.get(config.linked_source_org_id) if config.linked_source_org_id else None
                )

                if source_kpi:
                    # Find the source system and initiative to build full path
                    source_system = (
                        source_kpi.initiative_system_link.system if source_kpi.initiative_system_link else None
                    )
                    source_initiative = (
                        source_kpi.initiative_system_link.initiative if source_kpi.initiative_system_link else None
                    )

                    vt_config["linked_kpi"] = {
                        "source_org_name": source_org.name if source_org else None,
                        "source_initiative_name": source_initiative.name if source_initiative else None,
                        "source_system_name": source_system.name if source_system else None,
                        "source_kpi_name": source_kpi.name,
                        "source_value_type_id": config.linked_source_value_type_id,
                        "note": "Linked KPIs must exist in target instance for restore to work properly.",
                    }

            # Target for list types
            if vt.kind == "list" and config.target_list_value:
                vt_config["target_list_value"] = config.target_list_value

            # Export ALL contributions for this value type
            for contrib in config.contributions:
                contrib_data = {
                    "contributor": contrib.contributor_name,
                    "created_at": contrib.created_at.isoformat(),
                }

                if contrib.numeric_value is not None:
                    contrib_data["value"] = float(contrib.numeric_value)
                if contrib.qualitative_level is not None:
                    contrib_data["level"] = contrib.qualitative_level
                if contrib.list_value is not None:
                    contrib_data["list_value"] = contrib.list_value
                if contrib.comment:
                    contrib_data["comment"] = contrib.comment

                vt_config["contributions"].append(contrib_data)

            kpi_data["value_types"].append(vt_config)

        return kpi_data

    @staticmethod
    def _export_stakeholders(organization_id):
        """Export stakeholders, relationships, and entity links"""
        from app.models import Stakeholder

        stakeholders = Stakeholder.query.filter_by(organization_id=organization_id).order_by(Stakeholder.name).all()

        result = []
        for stakeholder in stakeholders:
            stakeholder_data = {
                "name": stakeholder.name,
                "role": stakeholder.role,
                "department": stakeholder.department,
                "email": stakeholder.email,
                "site_name": stakeholder.site.name if stakeholder.site else None,  # Store site name for reference
                "influence_level": stakeholder.influence_level,
                "interest_level": stakeholder.interest_level,
                "support_level": stakeholder.support_level,
                "visibility": stakeholder.visibility,
                "notes": stakeholder.notes,
                "position_x": stakeholder.position_x,
                "position_y": stakeholder.position_y,
                "created_by_login": stakeholder.created_by.login if stakeholder.created_by else None,
                "relationships": [],
                "entity_links": [],
            }

            # Export relationships (only where this stakeholder is "from")
            for rel in stakeholder.outgoing_relationships:
                to_stakeholder = rel.to_stakeholder
                stakeholder_data["relationships"].append(
                    {
                        "to_stakeholder_name": to_stakeholder.name,
                        "relationship_type": rel.relationship_type,
                        "strength": rel.strength,
                        "notes": rel.notes,
                    }
                )

            # Export entity links
            for link in stakeholder.entity_links:
                entity = link.get_entity()
                entity_link_data = {
                    "entity_type": link.entity_type,
                    "json_id": link.entity_id,
                    "entity_name": entity.name if entity else f"Unknown {link.entity_type}",
                    "interest_level": link.interest_level,
                    "impact_level": link.impact_level,
                    "notes": link.notes,
                }
                stakeholder_data["entity_links"].append(entity_link_data)

            result.append(stakeholder_data)

        return result

    @staticmethod
    def _export_stakeholder_maps(organization_id):
        """Export stakeholder maps and their memberships"""
        from app.models import StakeholderMap

        maps = StakeholderMap.query.filter_by(organization_id=organization_id).order_by(StakeholderMap.name).all()

        result = []
        for map_obj in maps:
            map_data = {
                "name": map_obj.name,
                "description": map_obj.description,
                "visibility": map_obj.visibility,
                "created_by_login": map_obj.created_by.login if map_obj.created_by else None,
                "stakeholders": [],
            }

            # Export stakeholder memberships
            for membership in map_obj.memberships:
                stakeholder = membership.stakeholder
                map_data["stakeholders"].append(
                    {
                        "name": stakeholder.name,
                        "role": stakeholder.role,  # Include role to help identify if multiple stakeholders have same name
                    }
                )

            result.append(map_data)

        return result

    @staticmethod
    def _export_geography(organization_id):
        """
        Export full geography hierarchy (Regions → Countries → Sites) for this organization.

        Note: GeographyRegion has organization_id — geography is per-org, not global.
        Full export is required for portability.
        """
        from app.models import GeographyRegion

        regions = (
            GeographyRegion.query
            .filter_by(organization_id=organization_id)
            .order_by(GeographyRegion.display_order, GeographyRegion.name)
            .all()
        )

        result = []
        for region in regions:
            region_data = {
                "name": region.name,
                "code": region.code,
                "display_order": region.display_order,
                "countries": [],
            }
            for country in region.countries:
                country_data = {
                    "name": country.name,
                    "code": country.code,
                    "iso_code": country.iso_code,
                    "latitude": float(country.latitude) if country.latitude is not None else None,
                    "longitude": float(country.longitude) if country.longitude is not None else None,
                    "display_order": country.display_order,
                    "sites": [],
                }
                for site in country.sites:
                    country_data["sites"].append({
                        "name": site.name,
                        "code": site.code,
                        "address": site.address,
                        "latitude": float(site.latitude) if site.latitude is not None else None,
                        "longitude": float(site.longitude) if site.longitude is not None else None,
                        "is_active": site.is_active,
                        "display_order": site.display_order,
                    })
                region_data["countries"].append(country_data)
            result.append(region_data)

        return result

    @staticmethod
    def _export_action_items(organization_id):
        """Export all action items and memos with governance bodies and entity mentions"""
        from app.models import (
            ActionItem,
            Challenge,
            Initiative,
            KPI,
            Space,
            System,
        )

        items = ActionItem.query.filter_by(organization_id=organization_id).order_by(ActionItem.created_at).all()

        result = []
        for item in items:
            item_data = {
                "type": item.type,
                "title": item.title,
                "description": item.description,
                "status": item.status,
                "priority": item.priority,
                "start_date": item.start_date.isoformat() if item.start_date else None,
                "due_date": item.due_date.isoformat() if item.due_date else None,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                "visibility": item.visibility,
                "owner_login": item.owner_user.login if item.owner_user else None,
                "created_by_login": item.created_by_user.login if item.created_by_user else None,
                "created_at": item.created_at.isoformat(),
                "governance_bodies": [gb.name for gb in item.governance_bodies],
                "links": FullBackupService._export_entity_links("action_item", item.id),
                "mentions": [],
            }

            # Export mentions with json_id (stable within-JSON reference, collision-free)
            # entity_name kept as human-readable fallback for debugging / very old restores
            entity_models = {
                "space": Space,
                "challenge": Challenge,
                "initiative": Initiative,
                "system": System,
                "kpi": KPI,
            }
            for mention in item.mentions:
                model = entity_models.get(mention.entity_type)
                entity = model.query.get(mention.entity_id) if model else None
                item_data["mentions"].append({
                    "entity_type": mention.entity_type,
                    "json_id": mention.entity_id,      # stable cross-ref within this backup
                    "entity_name": entity.name if entity else None,  # fallback for old restores
                    "mention_text": mention.mention_text,
                })

            result.append(item_data)

        return result

    @staticmethod
    def export_to_json_string(organization_id):
        """Export to JSON string"""
        backup = FullBackupService.create_full_backup(organization_id)
        return json.dumps(backup, indent=2, ensure_ascii=False)

    @staticmethod
    def export_to_file(organization_id, file_path):
        """Export to JSON file"""
        backup = FullBackupService.create_full_backup(organization_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(backup, f, indent=2, ensure_ascii=False)

    @staticmethod
    def extract_governance_bodies_from_backup(json_string):
        """
        Extract all unique governance body names from backup.

        Args:
            json_string: JSON backup content

        Returns:
            list: Sorted list of unique governance body names
        """
        try:
            backup = json.loads(json_string)
            return sorted(backup.get("governance_bodies", []))
        except Exception:
            return []
