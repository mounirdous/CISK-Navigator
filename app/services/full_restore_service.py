"""
Full Restore Service

Restores complete organization from JSON backup.
Includes governance body mapping.
"""

import json
from datetime import datetime

from app.extensions import db
from app.models import (
    KPI,
    Challenge,
    ChallengeInitiativeLink,
    Contribution,
    GovernanceBody,
    Initiative,
    InitiativeSystemLink,
    KPIGovernanceBodyLink,
    KPIValueTypeConfig,
    Space,
    System,
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
        from app.models import Organization, OrganizationMembership, User

        try:
            backup = json.loads(json_string)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {str(e)}"}

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
            "users_created": 0,
            "users_mapped": 0,
            "errors": [],
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
                            membership = OrganizationMembership.query.filter_by(
                                user_id=user.id, organization_id=organization_id
                            ).first()

                            if not membership:
                                # Add user to organization with permissions from backup
                                backup_user = next(
                                    (u for u in backup.get("users", []) if u["login"] == backup_login), None
                                )
                                if backup_user:
                                    membership = OrganizationMembership(
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
                        existing_user = User.query.filter(
                            (User.login == login) | (User.email == email)
                        ).first()

                        if existing_user:
                            # Use existing user instead
                            user_map[backup_login] = existing_user
                            stats["errors"].append(
                                f"User {login} already exists, mapped to existing account"
                            )
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
                            membership = OrganizationMembership(
                                user_id=new_user.id, organization_id=organization_id, **permissions
                            )
                            db.session.add(membership)
                            db.session.flush()

                            user_map[backup_login] = new_user
                            stats["users_created"] += 1

            # Step 1: Create/map governance bodies
            if governance_body_mapping:
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

            # Step 2: Import Value Types
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
                    )
                    db.session.add(vt)
                    db.session.flush()
                    value_type_map[vt.name] = vt
                    stats["value_types"] += 1
                except Exception as e:
                    stats["errors"].append(f"ValueType '{vt_data.get('name')}': {str(e)}")

            # Step 3: Import Spaces with full hierarchy
            for space_data in backup.get("spaces", []):
                try:
                    space_stats = FullRestoreService._restore_space_hierarchy(
                        space_data,
                        organization_id,
                        value_type_map,
                        governance_body_map,
                        initiative_map,
                        system_map,
                    )
                    for key in [
                        "spaces",
                        "challenges",
                        "initiatives",
                        "systems",
                        "kpis",
                        "contributions",
                        "governance_body_links",
                    ]:
                        stats[key] += space_stats.get(key, 0)
                    stats["errors"].extend(space_stats.get("errors", []))
                except Exception as e:
                    stats["errors"].append(f"Space '{space_data.get('name')}': {str(e)}")

            db.session.commit()
            stats["success"] = True

        except Exception as e:
            db.session.rollback()
            stats["success"] = False
            stats["errors"].append(f"Restore failed: {str(e)}")

        return stats

    @staticmethod
    def _restore_space_hierarchy(
        space_data, organization_id, value_type_map, governance_body_map, initiative_map, system_map
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
            "errors": [],
        }

        # Create Space
        space = Space(
            organization_id=organization_id,
            name=space_data["name"],
            description=space_data.get("description"),
            space_label=space_data.get("space_label"),
            is_private=space_data.get("is_private", False),
            display_order=space_data.get("display_order", 0),
        )
        db.session.add(space)
        db.session.flush()
        stats["spaces"] += 1

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
                db.session.add(challenge)
                db.session.flush()
                stats["challenges"] += 1

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
                        )
                        db.session.add(initiative)
                        db.session.flush()
                        initiative_map[init_name] = initiative
                        stats["initiatives"] += 1

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
                            db.session.add(system)
                            db.session.flush()
                            system_map[sys_name] = system
                            stats["systems"] += 1

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
                                    kpi_data, init_sys_link.id, value_type_map, governance_body_map
                                )
                                stats["kpis"] += kpi_stats.get("kpis", 0)
                                stats["contributions"] += kpi_stats.get("contributions", 0)
                                stats["governance_body_links"] += kpi_stats.get("governance_body_links", 0)
                                stats["errors"].extend(kpi_stats.get("errors", []))
                            except Exception as e:
                                stats["errors"].append(f"KPI '{kpi_data.get('name')}': {str(e)}")

            except Exception as e:
                stats["errors"].append(f"Challenge '{challenge_data.get('name')}': {str(e)}")

        return stats

    @staticmethod
    def _restore_kpi_with_data(kpi_data, init_sys_link_id, value_type_map, governance_body_map):
        """Restore KPI with all data"""
        stats = {"kpis": 0, "contributions": 0, "governance_body_links": 0, "errors": []}

        # Create KPI
        kpi = KPI(
            initiative_system_link_id=init_sys_link_id,
            name=kpi_data["name"],
            description=kpi_data.get("description"),
            is_archived=kpi_data.get("is_archived", False),
            display_order=kpi_data.get("display_order", 0),
        )
        db.session.add(kpi)
        db.session.flush()
        stats["kpis"] += 1

        # Restore governance body links
        for gb_name in kpi_data.get("governance_bodies", []):
            if gb_name in governance_body_map:
                gb = governance_body_map[gb_name]
                gb_link = KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=gb.id)
                db.session.add(gb_link)
                stats["governance_body_links"] += 1
            else:
                stats["errors"].append(f"KPI '{kpi_data['name']}': Governance body '{gb_name}' not mapped (skipped)")

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
