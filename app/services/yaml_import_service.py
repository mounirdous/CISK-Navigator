"""
YAML Import Service

Imports organizational structure from YAML files into the database.
"""

import yaml

from app.extensions import db
from app.models import (
    KPI,
    Challenge,
    ChallengeInitiativeLink,
    Initiative,
    InitiativeSystemLink,
    KPIValueTypeConfig,
    Space,
    System,
    ValueType,
)


class YAMLImportService:
    """Service for importing organizational structure from YAML"""

    @staticmethod
    def import_from_file(file_path, organization_id, dry_run=False):
        """
        Import structure from YAML file.

        Args:
            file_path: Path to YAML file
            organization_id: Target organization ID
            dry_run: If True, validate but don't save to database

        Returns:
            dict with import results and statistics
        """
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)

        return YAMLImportService.import_from_dict(data, organization_id, dry_run)

    @staticmethod
    def import_from_string(yaml_string, organization_id, dry_run=False):
        """
        Import structure from YAML string.

        Args:
            yaml_string: YAML content as string
            organization_id: Target organization ID
            dry_run: If True, validate but don't save to database

        Returns:
            dict with import results and statistics
        """
        data = yaml.safe_load(yaml_string)
        return YAMLImportService.import_from_dict(data, organization_id, dry_run)

    @staticmethod
    def import_from_dict(data, organization_id, dry_run=False):
        """
        Import structure from parsed YAML dictionary.

        Args:
            data: Parsed YAML data
            organization_id: Target organization ID
            dry_run: If True, validate but don't save to database

        Returns:
            dict with import results and statistics
        """
        stats = {
            "value_types": 0,
            "spaces": 0,
            "challenges": 0,
            "initiatives": 0,
            "systems": 0,
            "kpis": 0,
            "errors": [],
        }

        try:
            # Track created objects for linking
            value_type_map = {}  # name -> ValueType
            initiative_map = {}  # id -> Initiative
            system_map = {}  # id -> System

            # Step 1: Import Value Types
            if "value_types" in data:
                for vt_data in data["value_types"]:
                    try:
                        vt = YAMLImportService._create_value_type(vt_data, organization_id)
                        if not dry_run:
                            db.session.add(vt)
                            db.session.flush()  # Get ID
                        value_type_map[vt.name] = vt
                        stats["value_types"] += 1
                    except Exception as e:
                        stats["errors"].append(f"ValueType '{vt_data.get('name')}': {str(e)}")

            # Step 2: Import Spaces and nested structure
            if "spaces" in data:
                for space_data in data["spaces"]:
                    try:
                        space_stats = YAMLImportService._create_space_and_children(
                            space_data, organization_id, value_type_map, initiative_map, system_map, dry_run
                        )
                        for key in ["spaces", "challenges", "initiatives", "systems", "kpis"]:
                            stats[key] += space_stats.get(key, 0)
                        stats["errors"].extend(space_stats.get("errors", []))
                    except Exception as e:
                        stats["errors"].append(f"Space '{space_data.get('name')}': {str(e)}")

            # Commit if not dry run
            if not dry_run:
                db.session.commit()
                stats["success"] = True
            else:
                db.session.rollback()
                stats["success"] = False
                stats["message"] = "Dry run - no changes committed"

        except Exception as e:
            db.session.rollback()
            stats["success"] = False
            stats["errors"].append(f"Import failed: {str(e)}")

        return stats

    @staticmethod
    def _create_value_type(data, organization_id):
        """Create a ValueType from YAML data"""
        vt = ValueType(
            organization_id=organization_id,
            name=data["name"],
            kind=data["kind"],
            numeric_format=data.get("numeric_format"),
            decimal_places=data.get("decimal_places", 2),
            unit_label=data.get("unit_label"),
            default_aggregation_formula=data.get("default_aggregation_formula", "sum"),
            is_active=True,
        )
        return vt

    @staticmethod
    def _create_space_and_children(space_data, organization_id, value_type_map, initiative_map, system_map, dry_run):
        """Create a Space and all its children recursively"""
        stats = {"spaces": 0, "challenges": 0, "initiatives": 0, "systems": 0, "kpis": 0, "errors": []}

        # Create Space
        space = Space(
            organization_id=organization_id,
            name=space_data["name"],
            description=space_data.get("description"),
            space_label=space_data.get("space_label"),
            display_order=space_data.get("display_order", 0),
        )
        if not dry_run:
            db.session.add(space)
            db.session.flush()
        stats["spaces"] += 1

        # Create Challenges
        for challenge_data in space_data.get("challenges", []):
            try:
                challenge_stats = YAMLImportService._create_challenge_and_children(
                    challenge_data, space.id, organization_id, value_type_map, initiative_map, system_map, dry_run
                )
                for key in ["challenges", "initiatives", "systems", "kpis"]:
                    stats[key] += challenge_stats.get(key, 0)
                stats["errors"].extend(challenge_stats.get("errors", []))
            except Exception as e:
                stats["errors"].append(f"Challenge '{challenge_data.get('name')}': {str(e)}")

        return stats

    @staticmethod
    def _create_challenge_and_children(
        challenge_data, space_id, organization_id, value_type_map, initiative_map, system_map, dry_run
    ):
        """Create a Challenge and all its children"""
        stats = {"challenges": 0, "initiatives": 0, "systems": 0, "kpis": 0, "errors": []}

        # Create Challenge
        challenge = Challenge(
            organization_id=organization_id,
            space_id=space_id,
            name=challenge_data["name"],
            description=challenge_data.get("description"),
            display_order=challenge_data.get("display_order", 0),
        )
        if not dry_run:
            db.session.add(challenge)
            db.session.flush()
        stats["challenges"] += 1

        # Create Initiatives
        for initiative_data in challenge_data.get("initiatives", []):
            try:
                initiative_id = initiative_data.get("id")

                # Check if initiative already exists (reuse)
                if initiative_id in initiative_map:
                    initiative = initiative_map[initiative_id]
                else:
                    # Create new initiative
                    initiative = Initiative(
                        organization_id=organization_id,
                        name=initiative_data["name"],
                        description=initiative_data.get("description"),
                    )
                    if not dry_run:
                        db.session.add(initiative)
                        db.session.flush()
                    initiative_map[initiative_id] = initiative
                    stats["initiatives"] += 1

                # Link Challenge to Initiative
                link = ChallengeInitiativeLink(
                    challenge_id=challenge.id,
                    initiative_id=initiative.id,
                    display_order=initiative_data.get("display_order", 0),
                )
                if not dry_run:
                    db.session.add(link)
                    db.session.flush()

                # Create Systems
                for system_data in initiative_data.get("systems", []):
                    try:
                        system_stats = YAMLImportService._create_system_and_kpis(
                            system_data, initiative.id, organization_id, value_type_map, system_map, dry_run
                        )
                        stats["systems"] += system_stats.get("systems", 0)
                        stats["kpis"] += system_stats.get("kpis", 0)
                        stats["errors"].extend(system_stats.get("errors", []))
                    except Exception as e:
                        stats["errors"].append(f"System '{system_data.get('name')}': {str(e)}")

            except Exception as e:
                stats["errors"].append(f"Initiative '{initiative_data.get('name')}': {str(e)}")

        return stats

    @staticmethod
    def _create_system_and_kpis(system_data, initiative_id, organization_id, value_type_map, system_map, dry_run):
        """Create a System and all its KPIs"""
        stats = {"systems": 0, "kpis": 0, "errors": []}

        system_id = system_data.get("id")

        # Check if system already exists (reuse)
        if system_id in system_map:
            system = system_map[system_id]
        else:
            # Create new system
            system = System(
                organization_id=organization_id, name=system_data["name"], description=system_data.get("description")
            )
            if not dry_run:
                db.session.add(system)
                db.session.flush()
            system_map[system_id] = system
            stats["systems"] += 1

        # Link Initiative to System
        link = InitiativeSystemLink(
            initiative_id=initiative_id, system_id=system.id, display_order=system_data.get("display_order", 0)
        )
        if not dry_run:
            db.session.add(link)
            db.session.flush()

        # Create KPIs
        for kpi_data in system_data.get("kpis", []):
            try:
                kpi = KPI(
                    initiative_system_link_id=link.id,
                    name=kpi_data["name"],
                    description=kpi_data.get("description"),
                    display_order=kpi_data.get("display_order", 0),
                )
                if not dry_run:
                    db.session.add(kpi)
                    db.session.flush()
                stats["kpis"] += 1

                # Create KPI Value Type Configs
                for vt_data in kpi_data.get("value_types", []):
                    vt_name = vt_data["name"]
                    if vt_name in value_type_map:
                        value_type = value_type_map[vt_name]

                        colors = vt_data.get("colors", {})

                        # Parse target date if present
                        target_date = None
                        if vt_data.get("target_date"):
                            from datetime import datetime

                            try:
                                target_date = datetime.strptime(vt_data["target_date"], "%Y-%m-%d").date()
                            except ValueError:
                                pass

                        config = KPIValueTypeConfig(
                            kpi_id=kpi.id,
                            value_type_id=value_type.id,
                            display_order=0,
                            color_positive=colors.get("positive", "#28a745"),
                            color_zero=colors.get("zero", "#6c757d"),
                            color_negative=colors.get("negative", "#dc3545"),
                            display_scale=vt_data.get("display_scale", "default"),
                            display_decimals=vt_data.get("display_decimals"),
                            target_value=vt_data.get("target_value"),
                            target_date=target_date,
                        )
                        if not dry_run:
                            db.session.add(config)
                    else:
                        stats["errors"].append(f"KPI '{kpi_data['name']}': ValueType '{vt_name}' not found")

            except Exception as e:
                stats["errors"].append(f"KPI '{kpi_data.get('name')}': {str(e)}")

        return stats
