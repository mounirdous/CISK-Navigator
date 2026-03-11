"""
Full Backup/Restore Service

Complete data backup including structure AND data.
Uses JSON format for portability and human-readability.
"""

import json
from datetime import datetime

from app.models import GovernanceBody, Space, ValueType


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

        backup = {
            "metadata": {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "organization_name": org.name,
                "organization_id": organization_id,
                "backup_type": "full",
            },
            "value_types": FullBackupService._export_value_types(organization_id),
            "governance_bodies": FullBackupService._export_governance_bodies(organization_id),
            "spaces": FullBackupService._export_spaces(organization_id),
        }

        return backup

    @staticmethod
    def _export_value_types(organization_id):
        """Export all value types"""
        value_types = ValueType.query.filter_by(organization_id=organization_id).order_by(ValueType.display_order).all()

        result = []
        for vt in value_types:
            vt_data = {
                "name": vt.name,
                "kind": vt.kind,
                "default_aggregation_formula": vt.default_aggregation_formula,
                "is_active": vt.is_active,
                "display_order": vt.display_order,
            }

            if vt.kind == "numeric":
                vt_data["numeric_format"] = vt.numeric_format
                if vt.decimal_places is not None:
                    vt_data["decimal_places"] = vt.decimal_places
                if vt.unit_label:
                    vt_data["unit_label"] = vt.unit_label

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
                    "description": gb.description,
                    "is_active": gb.is_active,
                    "display_order": gb.display_order,
                }
            )

        return result

    @staticmethod
    def _export_spaces(organization_id):
        """Export spaces with full hierarchy and data"""
        spaces = Space.query.filter_by(organization_id=organization_id).order_by(Space.display_order, Space.name).all()

        result = []
        for space in spaces:
            space_data = {
                "name": space.name,
                "description": space.description,
                "space_label": space.space_label,
                "is_private": space.is_private,
                "display_order": space.display_order,
                "challenges": [],
            }

            # Export challenges
            challenges = sorted(space.challenges, key=lambda c: (c.display_order, c.name))
            for challenge in challenges:
                challenge_data = {
                    "name": challenge.name,
                    "description": challenge.description,
                    "display_order": challenge.display_order,
                    "initiatives": [],
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
                        "name": initiative.name,
                        "description": initiative.description,
                        "systems": [],
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
                            "name": system.name,
                            "description": system.description,
                            "kpis": [],
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
        """Export KPI with all data including contributions and governance bodies"""
        kpi_data = {
            "name": kpi.name,
            "description": kpi.description,
            "is_archived": kpi.is_archived,
            "display_order": kpi.display_order,
            "governance_bodies": [],
            "value_types": [],
        }

        # Export governance body links
        for link in kpi.governance_body_links:
            kpi_data["governance_bodies"].append(link.governance_body.name)

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
                if contrib.comment:
                    contrib_data["comment"] = contrib.comment

                vt_config["contributions"].append(contrib_data)

            kpi_data["value_types"].append(vt_config)

        return kpi_data

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
