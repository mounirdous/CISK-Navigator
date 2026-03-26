"""
Full Restore Service - v6.0

Restores complete organization from JSON backup format v6.0.

Features:
=========
✅ DB schema version checking (blocks incompatible restores)
✅ User mapping (map to existing or create new)
✅ Governance body mapping
✅ Full CISK hierarchy (Spaces → Challenges → Initiatives → Systems → KPIs)
✅ Value types with all configurations
✅ KPI contributions (actual data)
✅ **Logos** (Organization, Space, Challenge, Initiative, System, KPI)
✅ **KPI Formulas** (calculation_type + calculation_config)
✅ **Linked KPIs** (referenced but require manual re-linking after restore)
✅ **Stakeholders** with site assignments
✅ **Stakeholder Relationships** (reports_to, influences, etc.)
✅ **Stakeholder Entity Links** (stakeholder → CISK entities)
✅ **Stakeholder Maps** with memberships
✅ **Action Items & Memos** (v3.0+):
   - All action items and memos restored
   - Governance body links restored
   - Entity mentions resolved by json_id (collision-free); falls back to name for old backups
✅ **Saved Views / Filter Presets** (v5.0+):
   - Workspace and action register presets restored per user
✅ **Full Geography hierarchy** (v6.0+):
   - Regions (org-scoped), Countries, Sites created on restore
   - KPI geography assignments and stakeholder sites resolved from restored hierarchy

Important Notes:
================
- Restore REQUIRES matching DB schema version
- Linked KPIs are flagged but not automatically linked (manual step required)
- Users can be mapped to existing accounts or created new
- All logos are base64 encoded in backup and restored as binary data
- Action item owners are matched by login; items skipped if owner not found
- Filter presets are matched by user login; skipped if user not in user_map
"""

import json
from datetime import datetime

from app.extensions import db
from app.models import (
    KPI,
    ActionItem,
    ActionItemMention,
    Challenge,
    ChallengeInitiativeLink,
    Contribution,
    EntityLink,
    GeographySite,
    GovernanceBody,
    Initiative,
    InitiativeProgressUpdate,
    InitiativeSystemLink,
    KPIGovernanceBodyLink,
    KPIValueTypeConfig,
    Space,
    Stakeholder,
    StakeholderEntityLink,
    StakeholderMap,
    StakeholderMapMembership,
    StakeholderRelationship,
    System,
    UserFilterPreset,
    ValueType,
)


class FullRestoreService:
    """Service for restoring full organization backup with data"""

    @staticmethod
    def restore_from_json(json_string, organization_id, governance_body_mapping=None, user_mapping=None):
        """
        Restore organization from JSON backup.

        Args:
            json_string: JSON backup content
            organization_id: Target organization ID
            governance_body_mapping: Dict mapping backup GB names to target GB IDs or "create"
            user_mapping: Dict mapping backup user logins to actions:
                         {"login": {"action": "map", "user_id": 123}} or
                         {"login": {"action": "create", "login": "...", "email": "...", "permissions": {...}}}

        Returns:
            dict with restore results and statistics
        """
        from app.db_version import DB_SCHEMA_VERSION
        from app.models import Organization, User, UserOrganizationMembership

        try:
            backup = json.loads(json_string)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {str(e)}"}

        # VERSION CHECKING: Critical for data integrity
        metadata = backup.get("metadata", {})
        backup_db_version = metadata.get("db_schema_version", "unknown")
        backup_app_version = metadata.get("app_version", "unknown")

        if backup_db_version != DB_SCHEMA_VERSION:
            return {
                "success": False,
                "error": f"Database schema version mismatch!\n\n"
                f"Backup DB version: {backup_db_version}\n"
                f"Current DB version: {DB_SCHEMA_VERSION}\n\n"
                f"Restore is BLOCKED to prevent data corruption.\n"
                f"The backup must be created with the same database schema version.\n\n"
                f"Backup app version: {backup_app_version}\n"
                f"Backup created: {metadata.get('created_at', 'unknown')}",
                "version_mismatch": True,
            }

        stats = {
            "value_types": 0,
            "governance_bodies": 0,
            "spaces": 0,
            "challenges": 0,
            "initiatives": 0,
            "systems": 0,
            "kpis": 0,
            "contributions": 0,
            "governance_body_links": 0,
            "geography_assignments": 0,
            "users_created": 0,
            "users_mapped": 0,
            "stakeholders": 0,
            "stakeholder_relationships": 0,
            "stakeholder_maps": 0,
            "stakeholder_entity_links": 0,
            "action_items": 0,
            "geography_regions": 0,
            "geography_countries": 0,
            "geography_sites": 0,
            "filter_presets_restored": 0,
            "entity_branding_restored": 0,
            "entity_links_restored": 0,
            "logos_restored": 0,
            "formulas_restored": 0,
            "linked_kpis_restored": 0,
            "errors": [],
            "warnings": [],
        }

        try:
            # Maps for tracking created objects
            value_type_map = {}  # name -> ValueType
            governance_body_map = {}  # backup name -> GovernanceBody object
            initiative_map = {}  # name -> Initiative
            system_map = {}  # name -> System
            user_map = {}  # backup login -> User object

            # Step 0: Handle user mapping/creation
            if user_mapping:
                for backup_login, mapping_info in user_mapping.items():
                    action = mapping_info.get("action")

                    if action == "map":
                        # Map to existing user
                        user_id = mapping_info.get("user_id")
                        user = User.query.get(user_id)
                        if user:
                            user_map[backup_login] = user

                            # Ensure user is a member of target organization
                            membership = UserOrganizationMembership.query.filter_by(
                                user_id=user.id, organization_id=organization_id
                            ).first()

                            if not membership:
                                # Add user to organization with permissions from backup
                                backup_user = next(
                                    (u for u in backup.get("users", []) if u["login"] == backup_login), None
                                )
                                if backup_user:
                                    membership = UserOrganizationMembership(
                                        user_id=user.id,
                                        organization_id=organization_id,
                                        **backup_user["permissions"],
                                    )
                                    db.session.add(membership)
                                    db.session.flush()

                            stats["users_mapped"] += 1

                    elif action == "create":
                        # Create new user
                        login = mapping_info.get("login")
                        email = mapping_info.get("email")
                        display_name = mapping_info.get("display_name")
                        permissions = mapping_info.get("permissions", {})

                        # Check if user already exists (by login or email)
                        existing_user = User.query.filter((User.login == login) | (User.email == email)).first()

                        if existing_user:
                            # Use existing user instead
                            user_map[backup_login] = existing_user
                            stats["errors"].append(f"User {login} already exists, mapped to existing account")
                        else:
                            # Create new user with default password
                            new_user = User(
                                login=login,
                                email=email,
                                display_name=display_name,
                                is_active=True,
                                must_change_password=True,
                            )
                            new_user.set_password("ChangeMe123!")
                            db.session.add(new_user)
                            db.session.flush()

                            # Add to organization with permissions
                            membership = UserOrganizationMembership(
                                user_id=new_user.id, organization_id=organization_id, **permissions
                            )
                            db.session.add(membership)
                            db.session.flush()

                            user_map[backup_login] = new_user
                            stats["users_created"] += 1

            # Step 1: Create/map governance bodies
            # If no mapping provided, auto-create all governance bodies
            if not governance_body_mapping:
                governance_body_mapping = {}
                for gb_data in backup.get("governance_bodies", []):
                    governance_body_mapping[gb_data["name"]] = "create"

            for gb_data in backup.get("governance_bodies", []):
                gb_name = gb_data["name"]
                action = governance_body_mapping.get(gb_name)

                if action == "create":
                    # Create new governance body
                    gb = GovernanceBody(
                        organization_id=organization_id,
                        name=gb_name,
                        abbreviation=gb_data.get("abbreviation", gb_name[:20]),
                        description=gb_data.get("description"),
                        color=gb_data.get("color", "#3498db"),
                        display_order=gb_data.get("display_order", 0),
                        is_active=gb_data.get("is_active", True),
                        is_default=gb_data.get("is_default", False),
                    )
                    db.session.add(gb)
                    db.session.flush()
                    governance_body_map[gb_name] = gb
                    stats["governance_bodies"] += 1
                elif isinstance(action, int):
                    # Map to existing governance body
                    gb = GovernanceBody.query.get(action)
                    if gb:
                        governance_body_map[gb_name] = gb
                    else:
                        stats["errors"].append(f"Governance body ID {action} not found for '{gb_name}'")

            # Step 1.5: Restore organization logo and Porter's Five Forces
            org_data = backup.get("organization", {})
            org = Organization.query.get(organization_id)
            if "logo" in org_data:
                try:
                    import base64

                    org.logo_data = base64.b64decode(org_data["logo"]["data"])
                    org.logo_mime_type = org_data["logo"]["mime_type"]
                    db.session.flush()
                    stats["logos_restored"] += 1
                except Exception as e:
                    stats["warnings"].append(f"Failed to restore organization logo: {str(e)}")

            # Restore organization description
            if "description" in org_data:
                org.description = org_data["description"]

            # Restore Porter's Five Forces
            for field in ("porters_new_entrants", "porters_suppliers", "porters_buyers", "porters_substitutes", "porters_rivalry"):
                if field in org_data:
                    setattr(org, field, org_data[field])
            db.session.flush()

            # Step 1.6: Restore entity branding (EntityTypeDefault)
            branding_count, branding_warnings = FullRestoreService._restore_entity_branding(backup, organization_id)
            stats["entity_branding_restored"] = branding_count
            stats["warnings"].extend(branding_warnings)

            # Step 2: Import Value Types
            # First pass: Create all value types without formulas
            for vt_data in backup.get("value_types", []):
                try:
                    vt = ValueType(
                        organization_id=organization_id,
                        name=vt_data["name"],
                        kind=vt_data["kind"],
                        numeric_format=vt_data.get("numeric_format"),
                        decimal_places=vt_data.get("decimal_places", 2),
                        unit_label=vt_data.get("unit_label"),
                        default_aggregation_formula=vt_data.get("default_aggregation_formula", "sum"),
                        is_active=vt_data.get("is_active", True),
                        display_order=vt_data.get("display_order", 0),
                        calculation_type=vt_data.get("calculation_type", "manual"),
                    )
                    db.session.add(vt)
                    db.session.flush()
                    value_type_map[vt.name] = vt
                    stats["value_types"] += 1
                except Exception as e:
                    stats["errors"].append(f"ValueType '{vt_data.get('name')}': {str(e)}")

            # Second pass: Configure formulas (now that all value types exist with new IDs)
            for vt_data in backup.get("value_types", []):
                if vt_data.get("calculation_config") and vt_data.get("formula_source_names"):
                    try:
                        vt = value_type_map.get(vt_data["name"])
                        if vt:
                            # Reconstruct formula config with new IDs
                            old_config = vt_data["calculation_config"]
                            operation = old_config.get("operation")
                            source_names = vt_data["formula_source_names"]

                            # Map source names to new IDs
                            new_source_ids = []
                            for source_name in source_names:
                                source_vt = value_type_map.get(source_name)
                                if source_vt:
                                    new_source_ids.append(source_vt.id)

                            if len(new_source_ids) == len(source_names):
                                # All sources found, configure formula
                                vt.calculation_config = {
                                    "operation": operation,
                                    "source_value_type_ids": new_source_ids,
                                }
                                db.session.add(vt)
                            else:
                                stats["errors"].append(
                                    f"ValueType formula '{vt.name}': Could not find all source value types"
                                )
                    except Exception as e:
                        stats["errors"].append(f"ValueType formula '{vt_data.get('name')}': {str(e)}")

            # Step 2.5: Restore Geography hierarchy (regions → countries → sites)
            geo_map, geo_stats = FullRestoreService._restore_geography(backup, organization_id)
            stats["geography_regions"] += geo_stats.get("regions", 0)
            stats["geography_countries"] += geo_stats.get("countries", 0)
            stats["geography_sites"] += geo_stats.get("sites", 0)
            stats["warnings"].extend(geo_stats.get("warnings", []))

            # Step 3: Import Spaces with full hierarchy
            # json_id_map accumulates source_entity_id → new_db_id for all entity types
            json_id_map = {}  # {entity_type: {source_json_id: new_db_id}}
            for space_data in backup.get("spaces", []):
                try:
                    space_stats = FullRestoreService._restore_space_hierarchy(
                        space_data,
                        organization_id,
                        value_type_map,
                        governance_body_map,
                        initiative_map,
                        system_map,
                        geo_map,
                    )
                    for key in [
                        "spaces",
                        "challenges",
                        "initiatives",
                        "systems",
                        "kpis",
                        "contributions",
                        "governance_body_links",
                        "geography_assignments",
                        "entity_links_restored",
                        "logos_restored",
                        "formulas_restored",
                        "linked_kpis_restored",
                    ]:
                        stats[key] += space_stats.get(key, 0)
                    stats["errors"].extend(space_stats.get("errors", []))
                    # Merge json_id_map from this space into the global map
                    for entity_type, id_map in space_stats.get("json_id_map", {}).items():
                        json_id_map.setdefault(entity_type, {}).update(id_map)
                except Exception as e:
                    stats["errors"].append(f"Space '{space_data.get('name')}': {str(e)}")

            # Step 4: Restore Stakeholders and Maps
            stakeholder_stats = FullRestoreService._restore_stakeholders(
                backup, organization_id, user_map, geo_map, json_id_map
            )
            stats["stakeholders"] += stakeholder_stats.get("stakeholders", 0)
            stats["stakeholder_relationships"] += stakeholder_stats.get("stakeholder_relationships", 0)
            stats["stakeholder_entity_links"] += stakeholder_stats.get("stakeholder_entity_links", 0)
            stats["warnings"].extend(stakeholder_stats.get("warnings", []))

            # Step 5: Restore Stakeholder Maps
            map_stats = FullRestoreService._restore_stakeholder_maps(backup, organization_id, user_map)
            stats["stakeholder_maps"] += map_stats.get("maps", 0)
            stats["warnings"].extend(map_stats.get("warnings", []))

            # Step 6: Restore Action Items and Memos
            ai_stats = FullRestoreService._restore_action_items(
                backup, organization_id, user_map, governance_body_map, json_id_map
            )
            stats["action_items"] += ai_stats.get("action_items", 0)
            stats["entity_links_restored"] += ai_stats.get("entity_links_restored", 0)
            stats["warnings"].extend(ai_stats.get("warnings", []))

            # Step 7: Restore Saved Views (Filter Presets)
            preset_count, preset_warnings = FullRestoreService._restore_filter_presets(backup, organization_id, user_map)
            stats["filter_presets_restored"] += preset_count
            stats["warnings"].extend(preset_warnings)

            db.session.commit()
            stats["success"] = True

        except Exception as e:
            db.session.rollback()
            stats["success"] = False
            stats["errors"].append(f"Restore failed: {str(e)}")

        return stats

    @staticmethod
    def _restore_entity_branding(backup, organization_id):
        """Restore EntityTypeDefault branding (colors, icons, logos per entity type). Returns (count, warnings)."""
        import base64

        from app.models import EntityTypeDefault

        count = 0
        warnings = []
        for entry in backup.get("entity_branding", []):
            entity_type = entry.get("entity_type")
            if not entity_type:
                continue
            existing = EntityTypeDefault.query.filter_by(
                organization_id=organization_id, entity_type=entity_type
            ).first()
            if existing:
                # Update existing record
                existing.default_color = entry.get("default_color", existing.default_color)
                existing.default_icon = entry.get("default_icon", existing.default_icon)
                existing.display_name = entry.get("display_name", existing.display_name)
                existing.description = entry.get("description", existing.description)
                if "default_logo" in entry:
                    try:
                        existing.default_logo_data = base64.b64decode(entry["default_logo"]["data"])
                        existing.default_logo_mime_type = entry["default_logo"]["mime_type"]
                    except Exception as e:
                        warnings.append(f"Failed to restore default logo for '{entity_type}': {e}")
                count += 1
            else:
                logo_data = None
                logo_mime = None
                if "default_logo" in entry:
                    try:
                        logo_data = base64.b64decode(entry["default_logo"]["data"])
                        logo_mime = entry["default_logo"]["mime_type"]
                    except Exception as e:
                        warnings.append(f"Failed to decode default logo for '{entity_type}': {e}")
                db.session.add(EntityTypeDefault(
                    organization_id=organization_id,
                    entity_type=entity_type,
                    default_color=entry.get("default_color", "#6b7280"),
                    default_icon=entry.get("default_icon", "📋"),
                    display_name=entry.get("display_name", entity_type.title()),
                    description=entry.get("description"),
                    default_logo_data=logo_data,
                    default_logo_mime_type=logo_mime,
                ))
                count += 1
        if count:
            db.session.flush()
        return count, warnings

    @staticmethod
    def _restore_entity_links(entity_type, entity_id, data):
        """Create EntityLink records from a backup entity dict. Returns count created."""
        count = 0
        for link_data in data.get("links", []):
            url = (link_data.get("url") or "").strip()
            is_valid, _ = EntityLink.validate_url(url)
            if is_valid:
                from app.models import User
                creator_login = link_data.get("created_by_login")
                creator = User.query.filter_by(login=creator_login).first() if creator_login else None
                db.session.add(
                    EntityLink(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        url=url,
                        title=link_data.get("title") or None,
                        is_public=bool(link_data.get("is_public", True)),
                        created_by=creator.id if creator else None,
                    )
                )
                count += 1
        return count

    @staticmethod
    def _restore_filter_presets(backup, organization_id, user_map):
        """Restore saved views (filter presets) from backup. Returns (count, warnings)."""
        from app.models import User

        count = 0
        warnings = []
        for p in backup.get("filter_presets", []):
            login = p.get("user_login")
            user = user_map.get(login) if login else None
            if not user and login:
                # Not in explicit mapping — try to find by login in DB
                user = User.query.filter_by(login=login).first()
            if not user:
                warnings.append(f"Filter preset '{p.get('name')}' skipped: user '{login}' not found")
                continue
            # Skip if duplicate (same user+org+feature+name already exists)
            existing = UserFilterPreset.query.filter_by(
                user_id=user.id,
                organization_id=organization_id,
                feature=p.get("feature", "workspace"),
                name=p.get("name"),
            ).first()
            if existing:
                warnings.append(f"Filter preset '{p.get('name')}' ({p.get('feature')}) for '{login}' already exists, skipped")
                continue
            db.session.add(UserFilterPreset(
                user_id=user.id,
                organization_id=organization_id,
                feature=p.get("feature", "workspace"),
                name=p.get("name"),
                filters=p.get("filters", {}),
            ))
            count += 1
        if count:
            db.session.flush()
        return count, warnings

    @staticmethod
    def _restore_geography(backup, organization_id):
        """
        Restore full geography hierarchy (Regions → Countries → Sites) for the org.

        Reads from backup["geography"] (v6.0+). Falls back to backup["geography_references"]
        for older backups (v4/v5) — those only had site names, so no hierarchy can be created.

        Returns:
            geo_map: {"region:Name": Region, "country:Name": Country, "site:Name": Site}
            stats dict
        """
        from app.models import GeographyCountry, GeographyRegion, GeographySite

        geo_map = {}
        stats = {"regions": 0, "countries": 0, "sites": 0, "warnings": []}

        for region_data in backup.get("geography", []):
            region_name = region_data.get("name")
            if not region_name:
                continue

            region = GeographyRegion.query.filter_by(organization_id=organization_id, name=region_name).first()
            if not region:
                region = GeographyRegion(
                    organization_id=organization_id,
                    name=region_name,
                    code=region_data.get("code"),
                    display_order=region_data.get("display_order", 0),
                )
                db.session.add(region)
                db.session.flush()
                stats["regions"] += 1

            geo_map[f"region:{region_name}"] = region

            for country_data in region_data.get("countries", []):
                country_name = country_data.get("name")
                if not country_name:
                    continue

                country = GeographyCountry.query.filter_by(region_id=region.id, name=country_name).first()
                if not country:
                    country = GeographyCountry(
                        region_id=region.id,
                        name=country_name,
                        code=country_data.get("code"),
                        iso_code=country_data.get("iso_code"),
                        latitude=country_data.get("latitude"),
                        longitude=country_data.get("longitude"),
                        display_order=country_data.get("display_order", 0),
                    )
                    db.session.add(country)
                    db.session.flush()
                    stats["countries"] += 1

                geo_map[f"country:{country_name}"] = country

                for site_data in country_data.get("sites", []):
                    site_name = site_data.get("name")
                    if not site_name:
                        continue

                    site = GeographySite.query.filter_by(country_id=country.id, name=site_name).first()
                    if not site:
                        site = GeographySite(
                            country_id=country.id,
                            name=site_name,
                            code=site_data.get("code"),
                            address=site_data.get("address"),
                            latitude=site_data.get("latitude"),
                            longitude=site_data.get("longitude"),
                            is_active=site_data.get("is_active", True),
                            display_order=site_data.get("display_order", 0),
                        )
                        db.session.add(site)
                        db.session.flush()
                        stats["sites"] += 1

                    geo_map[f"site:{site_name}"] = site

        return geo_map, stats

    @staticmethod
    def _restore_space_hierarchy(
        space_data, organization_id, value_type_map, governance_body_map, initiative_map, system_map, geo_map=None
    ):
        """Restore space with full hierarchy"""
        stats = {
            "spaces": 0,
            "challenges": 0,
            "initiatives": 0,
            "systems": 0,
            "kpis": 0,
            "contributions": 0,
            "governance_body_links": 0,
            "geography_assignments": 0,
            "entity_links_restored": 0,
            "logos_restored": 0,
            "formulas_restored": 0,
            "linked_kpis_restored": 0,
            "errors": [],
            # json_id → new DB id map, built as entities are created
            # {entity_type: {json_id: new_db_id}}
            "json_id_map": {},
        }

        # Create Space
        import base64

        space = Space(
            organization_id=organization_id,
            name=space_data["name"],
            description=space_data.get("description"),
            space_label=space_data.get("space_label"),
            is_private=space_data.get("is_private", False),
            display_order=space_data.get("display_order", 0),
            swot_strengths=space_data.get("swot_strengths"),
            swot_weaknesses=space_data.get("swot_weaknesses"),
            swot_opportunities=space_data.get("swot_opportunities"),
            swot_threats=space_data.get("swot_threats"),
        )

        # Restore space logo if present
        if "logo" in space_data:
            try:
                space.logo_data = base64.b64decode(space_data["logo"]["data"])
                space.logo_mime_type = space_data["logo"]["mime_type"]
                stats["logos_restored"] += 1
            except Exception as e:
                stats["errors"].append(f"Failed to restore logo for space '{space_data['name']}': {str(e)}")

        db.session.add(space)
        db.session.flush()
        stats["spaces"] += 1
        if "json_id" in space_data:
            stats["json_id_map"].setdefault("space", {})[space_data["json_id"]] = space.id
        stats["entity_links_restored"] += FullRestoreService._restore_entity_links("space", space.id, space_data)

        # Restore challenges
        for challenge_data in space_data.get("challenges", []):
            try:
                challenge = Challenge(
                    organization_id=organization_id,
                    space_id=space.id,
                    name=challenge_data["name"],
                    description=challenge_data.get("description"),
                    display_order=challenge_data.get("display_order", 0),
                )

                # Restore challenge logo if present
                if "logo" in challenge_data:
                    try:
                        challenge.logo_data = base64.b64decode(challenge_data["logo"]["data"])
                        challenge.logo_mime_type = challenge_data["logo"]["mime_type"]
                        stats["logos_restored"] += 1
                    except Exception as e:
                        stats["errors"].append(
                            f"Failed to restore logo for challenge '{challenge_data['name']}': {str(e)}"
                        )

                db.session.add(challenge)
                db.session.flush()
                stats["challenges"] += 1
                if "json_id" in challenge_data:
                    stats["json_id_map"].setdefault("challenge", {})[challenge_data["json_id"]] = challenge.id
                stats["entity_links_restored"] += FullRestoreService._restore_entity_links("challenge", challenge.id, challenge_data)

                # Restore initiatives
                for initiative_data in challenge_data.get("initiatives", []):
                    init_name = initiative_data["name"]

                    # Check if initiative already exists (reuse)
                    if init_name in initiative_map:
                        initiative = initiative_map[init_name]
                    else:
                        initiative = Initiative(
                            organization_id=organization_id,
                            name=init_name,
                            description=initiative_data.get("description"),
                            group_label=initiative_data.get("group_label"),
                            mission=initiative_data.get("mission"),
                            responsible_person=initiative_data.get("responsible_person"),
                            team_members=initiative_data.get("team_members"),
                            handover_organization=initiative_data.get("handover_organization"),
                            deliverables=initiative_data.get("deliverables"),
                            success_criteria=initiative_data.get("success_criteria"),
                            impact_on_challenge=initiative_data.get("impact_on_challenge"),
                            impact_rationale=initiative_data.get("impact_rationale"),
                        )

                        # Restore initiative logo if present
                        if "logo" in initiative_data:
                            try:
                                initiative.logo_data = base64.b64decode(initiative_data["logo"]["data"])
                                initiative.logo_mime_type = initiative_data["logo"]["mime_type"]
                                stats["logos_restored"] += 1
                            except Exception as e:
                                stats["errors"].append(f"Failed to restore logo for initiative '{init_name}': {str(e)}")

                        db.session.add(initiative)
                        db.session.flush()
                        initiative_map[init_name] = initiative
                        stats["initiatives"] += 1
                        if "json_id" in initiative_data:
                            stats["json_id_map"].setdefault("initiative", {})[initiative_data["json_id"]] = initiative.id
                        stats["entity_links_restored"] += FullRestoreService._restore_entity_links("initiative", initiative.id, initiative_data)

                        # Restore progress updates
                        for upd_data in initiative_data.get("progress_updates", []):
                            try:
                                upd = InitiativeProgressUpdate(
                                    initiative_id=initiative.id,
                                    rag_status=upd_data["rag_status"],
                                    accomplishments=upd_data.get("accomplishments"),
                                    next_steps=upd_data.get("next_steps"),
                                    blockers=upd_data.get("blockers"),
                                    created_at=datetime.fromisoformat(upd_data["created_at"]),
                                )
                                db.session.add(upd)
                            except Exception:
                                pass  # Skip malformed progress update entries

                    # Link Challenge to Initiative
                    link = ChallengeInitiativeLink(challenge_id=challenge.id, initiative_id=initiative.id)
                    db.session.add(link)

                    # Restore systems
                    for system_data in initiative_data.get("systems", []):
                        sys_name = system_data["name"]

                        # Check if system already exists (reuse)
                        if sys_name in system_map:
                            system = system_map[sys_name]
                        else:
                            system = System(
                                organization_id=organization_id,
                                name=sys_name,
                                description=system_data.get("description"),
                            )

                            # Restore system logo if present
                            if "logo" in system_data:
                                try:
                                    system.logo_data = base64.b64decode(system_data["logo"]["data"])
                                    system.logo_mime_type = system_data["logo"]["mime_type"]
                                    stats["logos_restored"] += 1
                                except Exception as e:
                                    stats["errors"].append(f"Failed to restore logo for system '{sys_name}': {str(e)}")

                            db.session.add(system)
                            db.session.flush()
                            system_map[sys_name] = system
                            stats["systems"] += 1
                            if "json_id" in system_data:
                                stats["json_id_map"].setdefault("system", {})[system_data["json_id"]] = system.id
                            stats["entity_links_restored"] += FullRestoreService._restore_entity_links("system", system.id, system_data)

                        # Link Initiative to System
                        init_sys_link = InitiativeSystemLink.query.filter_by(
                            initiative_id=initiative.id, system_id=system.id
                        ).first()

                        if not init_sys_link:
                            init_sys_link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id)
                            db.session.add(init_sys_link)
                            db.session.flush()

                        # Restore KPIs with data
                        for kpi_data in system_data.get("kpis", []):
                            try:
                                kpi_stats = FullRestoreService._restore_kpi_with_data(
                                    kpi_data, init_sys_link.id, value_type_map, governance_body_map, geo_map
                                )
                                if "json_id" in kpi_data and kpi_stats.get("kpi_id"):
                                    stats["json_id_map"].setdefault("kpi", {})[kpi_data["json_id"]] = kpi_stats["kpi_id"]
                                stats["kpis"] += kpi_stats.get("kpis", 0)
                                stats["contributions"] += kpi_stats.get("contributions", 0)
                                stats["governance_body_links"] += kpi_stats.get("governance_body_links", 0)
                                stats["geography_assignments"] += kpi_stats.get("geography_assignments", 0)
                                stats["entity_links_restored"] += kpi_stats.get("entity_links_restored", 0)
                                stats["logos_restored"] += kpi_stats.get("logos_restored", 0)
                                stats["formulas_restored"] += kpi_stats.get("formulas_restored", 0)
                                stats["linked_kpis_restored"] += kpi_stats.get("linked_kpis_restored", 0)
                                stats["errors"].extend(kpi_stats.get("errors", []))
                            except Exception as e:
                                stats["errors"].append(f"KPI '{kpi_data.get('name')}': {str(e)}")

            except Exception as e:
                stats["errors"].append(f"Challenge '{challenge_data.get('name')}': {str(e)}")

        return stats

    @staticmethod
    def _restore_kpi_with_data(kpi_data, init_sys_link_id, value_type_map, governance_body_map, geo_map=None):
        """Restore KPI with all data including logo, formulas, and linked KPIs"""
        import base64

        stats = {
            "kpis": 0,
            "contributions": 0,
            "governance_body_links": 0,
            "geography_assignments": 0,
            "entity_links_restored": 0,
            "logos_restored": 0,
            "formulas_restored": 0,
            "linked_kpis_restored": 0,
            "errors": [],
        }

        # Create KPI
        kpi = KPI(
            initiative_system_link_id=init_sys_link_id,
            name=kpi_data["name"],
            description=kpi_data.get("description"),
            is_archived=kpi_data.get("is_archived", False),
            display_order=kpi_data.get("display_order", 0),
        )

        # Restore KPI logo if present
        if "logo" in kpi_data:
            try:
                kpi.logo_data = base64.b64decode(kpi_data["logo"]["data"])
                kpi.logo_mime_type = kpi_data["logo"]["mime_type"]
                stats["logos_restored"] += 1
            except Exception as e:
                stats["errors"].append(f"Failed to restore logo for KPI '{kpi_data['name']}': {str(e)}")

        db.session.add(kpi)
        db.session.flush()
        stats["kpis"] += 1
        stats["kpi_id"] = kpi.id  # Returned so callers can build json_id_map
        stats["entity_links_restored"] += FullRestoreService._restore_entity_links("kpi", kpi.id, kpi_data)

        # Restore governance body links
        for gb_name in kpi_data.get("governance_bodies", []):
            if gb_name in governance_body_map:
                gb = governance_body_map[gb_name]
                gb_link = KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=gb.id)
                db.session.add(gb_link)
                stats["governance_body_links"] += 1
            else:
                stats["errors"].append(f"KPI '{kpi_data['name']}': Governance body '{gb_name}' not mapped (skipped)")

        # Restore geography assignments (region/country/site links)
        from app.models import KPIGeographyAssignment

        _geo = geo_map or {}
        for geo_data in kpi_data.get("geography_assignments", []):
            try:
                level = geo_data.get("level")
                geo_assignment = KPIGeographyAssignment(kpi_id=kpi.id)

                if level == "site":
                    site_name = geo_data.get("site_name")
                    site = _geo.get(f"site:{site_name}")
                    if site:
                        geo_assignment.site_id = site.id
                        db.session.add(geo_assignment)
                        stats["geography_assignments"] = stats.get("geography_assignments", 0) + 1
                    else:
                        stats["errors"].append(f"KPI '{kpi_data['name']}': Site '{site_name}' not found in geography (skipped)")
                elif level == "country":
                    country_name = geo_data.get("country_name")
                    country = _geo.get(f"country:{country_name}")
                    if country:
                        geo_assignment.country_id = country.id
                        db.session.add(geo_assignment)
                        stats["geography_assignments"] = stats.get("geography_assignments", 0) + 1
                    else:
                        stats["errors"].append(f"KPI '{kpi_data['name']}': Country '{country_name}' not found in geography (skipped)")
                elif level == "region":
                    region_name = geo_data.get("region_name")
                    region = _geo.get(f"region:{region_name}")
                    if region:
                        geo_assignment.region_id = region.id
                        db.session.add(geo_assignment)
                        stats["geography_assignments"] = stats.get("geography_assignments", 0) + 1
                    else:
                        stats["errors"].append(f"KPI '{kpi_data['name']}': Region '{region_name}' not found in geography (skipped)")
            except Exception as e:
                stats["errors"].append(f"KPI '{kpi_data['name']}': Failed to restore geography assignment: {str(e)}")

        # Restore value type configurations and contributions
        for vt_config_data in kpi_data.get("value_types", []):
            vt_name = vt_config_data["name"]

            if vt_name not in value_type_map:
                stats["errors"].append(f"KPI '{kpi_data['name']}': ValueType '{vt_name}' not found")
                continue

            value_type = value_type_map[vt_name]

            # Parse target date if present
            target_date = None
            if vt_config_data.get("target_date"):
                try:
                    target_date = datetime.strptime(vt_config_data["target_date"], "%Y-%m-%d").date()
                except ValueError:
                    pass

            # Create KPI Value Type Config
            colors = vt_config_data.get("colors", {})
            config = KPIValueTypeConfig(
                kpi_id=kpi.id,
                value_type_id=value_type.id,
                display_order=0,
                color_positive=colors.get("positive", "#28a745"),
                color_zero=colors.get("zero", "#6c757d"),
                color_negative=colors.get("negative", "#dc3545"),
                display_scale=vt_config_data.get("display_scale", "default"),
                display_decimals=vt_config_data.get("display_decimals"),
                target_value=vt_config_data.get("target_value"),
                target_date=target_date,
                target_direction=vt_config_data.get("target_direction"),
                target_tolerance_pct=vt_config_data.get("target_tolerance_pct"),
                baseline_snapshot_id=vt_config_data.get("baseline_snapshot_id"),
                # Formula support
                calculation_type=vt_config_data.get("calculation_type", "manual"),
                calculation_config=vt_config_data.get("calculation_config"),
            )

            # Track formulas
            if config.calculation_type == "formula":
                stats["formulas_restored"] += 1

            # Note: Linked KPIs cannot be fully restored in first pass
            # because they reference other KPIs that may not exist yet.
            # The linked_kpi data is stored for reference but links must be
            # manually re-established after all KPIs are restored.
            if config.calculation_type == "linked" and "linked_kpi" in vt_config_data:
                stats["linked_kpis_restored"] += 1
                linked_info = vt_config_data["linked_kpi"]
                stats["errors"].append(
                    f"KPI '{kpi_data['name']}' - ValueType '{vt_name}': "
                    f"Linked KPI detected (source: {linked_info.get('source_kpi_name')}). "
                    f"Link must be manually re-established after restore."
                )

            db.session.add(config)
            db.session.flush()

            # Restore ALL contributions
            for contrib_data in vt_config_data.get("contributions", []):
                contribution = Contribution(
                    kpi_value_type_config_id=config.id,
                    contributor_name=contrib_data["contributor"],
                    numeric_value=contrib_data.get("value"),
                    qualitative_level=contrib_data.get("level"),
                    comment=contrib_data.get("comment"),
                )
                db.session.add(contribution)
                stats["contributions"] += 1

        return stats

    @staticmethod
    def _restore_stakeholders(backup, organization_id, user_map, geo_map=None, json_id_map=None):
        """Restore stakeholders with relationships and entity links.

        json_id_map: {entity_type: {source_json_id: new_db_id}} — used first for entity links.
        Falls back to name-based lookup for old backups without json_id.
        """
        from app.models import KPI, Challenge, Initiative, Space, System

        stats = {
            "stakeholders": 0,
            "stakeholder_relationships": 0,
            "stakeholder_entity_links": 0,
            "warnings": [],
        }

        stakeholder_map = {}  # name -> Stakeholder object (for relationships)

        # Step 1: Create all stakeholders first (relationships come after)
        for stakeholder_data in backup.get("stakeholders", []):
            try:
                created_by_user = None
                if stakeholder_data.get("created_by_login"):
                    created_by_user = user_map.get(stakeholder_data["created_by_login"])

                # Find site via geo_map (restored geography hierarchy)
                site = None
                if stakeholder_data.get("site_name"):
                    site_name = stakeholder_data["site_name"]
                    site = (geo_map or {}).get(f"site:{site_name}")
                    if not site:
                        stats["warnings"].append(
                            f"Stakeholder '{stakeholder_data['name']}': Site '{site_name}' not found in geography. "
                            "Stakeholder will be created without site assignment."
                        )

                stakeholder = Stakeholder(
                    organization_id=organization_id,
                    created_by_user_id=created_by_user.id if created_by_user else None,
                    site_id=site.id if site else None,
                    name=stakeholder_data["name"],
                    role=stakeholder_data.get("role"),
                    department=stakeholder_data.get("department"),
                    email=stakeholder_data.get("email"),
                    influence_level=stakeholder_data.get("influence_level", 50),
                    interest_level=stakeholder_data.get("interest_level", 50),
                    support_level=stakeholder_data.get("support_level", "neutral"),
                    visibility=stakeholder_data.get("visibility", "shared"),
                    notes=stakeholder_data.get("notes"),
                    position_x=stakeholder_data.get("position_x"),
                    position_y=stakeholder_data.get("position_y"),
                )

                db.session.add(stakeholder)
                db.session.flush()

                stakeholder_map[stakeholder_data["name"]] = stakeholder
                stats["stakeholders"] += 1

            except Exception as e:
                stats["warnings"].append(f"Failed to restore stakeholder '{stakeholder_data.get('name')}': {str(e)}")

        # Step 2: Create relationships (now that all stakeholders exist)
        for stakeholder_data in backup.get("stakeholders", []):
            from_stakeholder = stakeholder_map.get(stakeholder_data["name"])
            if not from_stakeholder:
                continue

            for rel_data in stakeholder_data.get("relationships", []):
                try:
                    to_stakeholder = stakeholder_map.get(rel_data["to_stakeholder_name"])
                    if not to_stakeholder:
                        stats["warnings"].append(
                            f"Relationship from '{stakeholder_data['name']}' to '{rel_data['to_stakeholder_name']}': "
                            "Target stakeholder not found"
                        )
                        continue

                    relationship = StakeholderRelationship(
                        from_stakeholder_id=from_stakeholder.id,
                        to_stakeholder_id=to_stakeholder.id,
                        relationship_type=rel_data["relationship_type"],
                        strength=rel_data.get("strength", 50),
                        notes=rel_data.get("notes"),
                    )
                    db.session.add(relationship)
                    stats["stakeholder_relationships"] += 1

                except Exception as e:
                    stats["warnings"].append(
                        f"Failed to restore relationship from '{stakeholder_data['name']}': {str(e)}"
                    )

        # Step 3: Create entity links
        _json_id_map = json_id_map or {}
        for stakeholder_data in backup.get("stakeholders", []):
            stakeholder = stakeholder_map.get(stakeholder_data["name"])
            if not stakeholder:
                continue

            for link_data in stakeholder_data.get("entity_links", []):
                try:
                    entity_type = link_data["entity_type"]

                    # Prefer json_id (collision-free); fall back to name for old backups
                    resolved_id = None
                    source_json_id = link_data.get("json_id")
                    if source_json_id is not None:
                        resolved_id = _json_id_map.get(entity_type, {}).get(source_json_id)

                    if resolved_id is None:
                        entity_name = link_data.get("entity_name")
                        if entity_name:
                            if entity_type == "space":
                                row = Space.query.filter_by(organization_id=organization_id, name=entity_name).first()
                            elif entity_type == "challenge":
                                row = Challenge.query.filter_by(organization_id=organization_id, name=entity_name).first()
                            elif entity_type == "initiative":
                                row = Initiative.query.filter_by(organization_id=organization_id, name=entity_name).first()
                            elif entity_type == "system":
                                row = System.query.filter_by(organization_id=organization_id, name=entity_name).first()
                            elif entity_type == "kpi":
                                row = (
                                    KPI.query.join(KPI.initiative_system_link)
                                    .join(InitiativeSystemLink.initiative)
                                    .filter(Initiative.organization_id == organization_id, KPI.name == entity_name)
                                    .first()
                                )
                            else:
                                row = None
                            if row:
                                resolved_id = row.id

                    if not resolved_id:
                        label = link_data.get("entity_name") or link_data.get("json_id", "?")
                        stats["warnings"].append(
                            f"Entity link for stakeholder '{stakeholder_data['name']}': "
                            f"{entity_type} '{label}' not found"
                        )
                        continue

                    entity_link = StakeholderEntityLink(
                        stakeholder_id=stakeholder.id,
                        entity_type=entity_type,
                        entity_id=resolved_id,
                        interest_level=link_data.get("interest_level", 50),
                        impact_level=link_data.get("impact_level", 50),
                        notes=link_data.get("notes"),
                    )
                    db.session.add(entity_link)
                    stats["stakeholder_entity_links"] += 1

                except Exception as e:
                    stats["warnings"].append(
                        f"Failed to restore entity link for stakeholder '{stakeholder_data['name']}': {str(e)}"
                    )

        db.session.flush()
        return stats

    @staticmethod
    def _restore_action_items(backup, organization_id, user_map, governance_body_map, json_id_map=None):
        """Restore action items and memos with governance body links and entity mentions.

        json_id_map: {entity_type: {source_json_id: new_db_id}} — built during hierarchy restore.
        Used first; falls back to name-based lookup for old backups without json_id.
        """
        from app.models import User

        stats = {"action_items": 0, "entity_links_restored": 0, "warnings": []}
        json_id_map = json_id_map or {}

        # Name-based fallback lookup (for old backups without json_id)
        entity_lookup = {
            "space": {s.name: s.id for s in Space.query.filter_by(organization_id=organization_id).all()},
            "challenge": {c.name: c.id for c in Challenge.query.filter_by(organization_id=organization_id).all()},
            "initiative": {i.name: i.id for i in Initiative.query.filter_by(organization_id=organization_id).all()},
            "system": {s.name: s.id for s in System.query.filter_by(organization_id=organization_id).all()},
            "kpi": {
                k.name: k.id
                for k in KPI.query.join(KPI.initiative_system_link)
                .join(InitiativeSystemLink.initiative)
                .filter(Initiative.organization_id == organization_id)
                .all()
            },
        }

        for item_data in backup.get("action_items", []):
            try:
                # Resolve owner by login
                owner_login = item_data.get("owner_login")
                owner_user = user_map.get(owner_login) if owner_login else None
                if not owner_user and owner_login:
                    owner_user = User.query.filter_by(login=owner_login).first()
                if not owner_user:
                    stats["warnings"].append(
                        f"Action item '{item_data.get('title')}': owner '{owner_login}' not found, skipped."
                    )
                    continue

                # Resolve optional created_by
                created_by_login = item_data.get("created_by_login")
                created_by_user = user_map.get(created_by_login) if created_by_login else None
                if not created_by_user and created_by_login:
                    created_by_user = User.query.filter_by(login=created_by_login).first()

                # Parse dates
                start_date = None
                if item_data.get("start_date"):
                    try:
                        start_date = datetime.strptime(item_data["start_date"], "%Y-%m-%d").date()
                    except ValueError:
                        pass

                due_date = None
                if item_data.get("due_date"):
                    try:
                        due_date = datetime.strptime(item_data["due_date"], "%Y-%m-%d").date()
                    except ValueError:
                        pass

                completed_at = None
                if item_data.get("completed_at"):
                    try:
                        completed_at = datetime.fromisoformat(item_data["completed_at"])
                    except ValueError:
                        pass

                action_item = ActionItem(
                    organization_id=organization_id,
                    owner_user_id=owner_user.id,
                    created_by_user_id=created_by_user.id if created_by_user else owner_user.id,
                    type=item_data.get("type", "action"),
                    title=item_data["title"],
                    description=item_data.get("description"),
                    status=item_data.get("status", "active"),
                    priority=item_data.get("priority", "medium"),
                    start_date=start_date,
                    due_date=due_date,
                    completed_at=completed_at,
                    visibility=item_data.get("visibility", "shared"),
                )
                db.session.add(action_item)
                db.session.flush()

                # Restore governance body links
                for gb_name in item_data.get("governance_bodies", []):
                    gb = governance_body_map.get(gb_name)
                    if gb:
                        action_item.governance_bodies.append(gb)
                    else:
                        stats["warnings"].append(
                            f"Action item '{item_data['title']}': governance body '{gb_name}' not mapped (skipped)"
                        )

                # Restore entity mentions
                for mention_data in item_data.get("mentions", []):
                    entity_type = mention_data.get("entity_type")
                    if not entity_type:
                        continue

                    # Prefer json_id (collision-free); fall back to entity_name for old backups
                    entity_id = None
                    source_json_id = mention_data.get("json_id")
                    if source_json_id is not None:
                        entity_id = json_id_map.get(entity_type, {}).get(source_json_id)

                    if entity_id is None:
                        entity_name = mention_data.get("entity_name")
                        if entity_name:
                            entity_id = entity_lookup.get(entity_type, {}).get(entity_name)

                    if not entity_id:
                        label = mention_data.get("entity_name") or mention_data.get("json_id", "?")
                        stats["warnings"].append(
                            f"Action item '{item_data['title']}': mention '{label}' ({entity_type}) not found (skipped)"
                        )
                        continue
                    mention = ActionItemMention(
                        action_item_id=action_item.id,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        mention_text=mention_data.get("mention_text", ""),
                    )
                    db.session.add(mention)

                stats["entity_links_restored"] += FullRestoreService._restore_entity_links("action_item", action_item.id, item_data)
                db.session.flush()
                stats["action_items"] += 1

            except Exception as e:
                stats["warnings"].append(f"Failed to restore action item '{item_data.get('title')}': {str(e)}")

        return stats

    @staticmethod
    def _restore_stakeholder_maps(backup, organization_id, user_map):
        """Restore stakeholder maps with memberships"""
        stats = {"maps": 0, "warnings": []}

        for map_data in backup.get("stakeholder_maps", []):
            try:
                created_by_user = None
                if map_data.get("created_by_login"):
                    created_by_user = user_map.get(map_data["created_by_login"])

                stakeholder_map = StakeholderMap(
                    organization_id=organization_id,
                    created_by_user_id=created_by_user.id if created_by_user else None,
                    name=map_data["name"],
                    description=map_data.get("description"),
                    visibility=map_data.get("visibility", "shared"),
                )

                db.session.add(stakeholder_map)
                db.session.flush()
                stats["maps"] += 1

                # Add stakeholder memberships
                for stakeholder_ref in map_data.get("stakeholders", []):
                    stakeholder_name = stakeholder_ref["name"]

                    # Find stakeholder by name (and optionally role for disambiguation)
                    query = Stakeholder.query.filter_by(organization_id=organization_id, name=stakeholder_name)
                    if stakeholder_ref.get("role"):
                        query = query.filter_by(role=stakeholder_ref["role"])

                    stakeholder = query.first()

                    if not stakeholder:
                        stats["warnings"].append(
                            f"Map '{map_data['name']}': Stakeholder '{stakeholder_name}' not found"
                        )
                        continue

                    membership = StakeholderMapMembership(
                        stakeholder_map_id=stakeholder_map.id, stakeholder_id=stakeholder.id
                    )
                    db.session.add(membership)

            except Exception as e:
                stats["warnings"].append(f"Failed to restore stakeholder map '{map_data.get('name')}': {str(e)}")

        db.session.flush()
        return stats
