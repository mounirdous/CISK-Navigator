"""
YAML Export Service

Exports organizational structure to YAML files.
"""
import yaml
from io import StringIO
from app.models import Space, ValueType


class YAMLExportService:
    """Service for exporting organizational structure to YAML"""

    @staticmethod
    def export_to_yaml(organization_id):
        """
        Export organization structure to YAML.

        Args:
            organization_id: Organization ID to export

        Returns:
            str: YAML content
        """
        # Get all data
        value_types = ValueType.query.filter_by(organization_id=organization_id).order_by(
            ValueType.display_order
        ).all()

        spaces = Space.query.filter_by(organization_id=organization_id).order_by(
            Space.display_order, Space.name
        ).all()

        # Build data structure
        data = {
            'value_types': YAMLExportService._export_value_types(value_types),
            'spaces': YAMLExportService._export_spaces(spaces)
        }

        # Convert to YAML
        return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)

    @staticmethod
    def _export_value_types(value_types):
        """Export value types to dict"""
        result = []
        for vt in value_types:
            vt_data = {
                'name': vt.name,
                'kind': vt.kind,
                'default_aggregation_formula': vt.default_aggregation_formula,
            }

            if vt.kind == 'numeric':
                vt_data['numeric_format'] = vt.numeric_format
                if vt.decimal_places is not None:
                    vt_data['decimal_places'] = vt.decimal_places
                if vt.unit_label:
                    vt_data['unit_label'] = vt.unit_label

            result.append(vt_data)

        return result

    @staticmethod
    def _export_spaces(spaces):
        """Export spaces and their hierarchy"""
        result = []

        for idx, space in enumerate(spaces, start=1):
            space_data = {
                'id': f'S{idx}',
                'name': space.name,
                'display_order': space.display_order,
            }

            if space.description:
                space_data['description'] = space.description
            if space.space_label:
                space_data['space_label'] = space.space_label

            # Export challenges
            challenges = sorted(space.challenges, key=lambda c: (c.display_order, c.name))
            if challenges:
                space_data['challenges'] = YAMLExportService._export_challenges(challenges)

            result.append(space_data)

        return result

    @staticmethod
    def _export_challenges(challenges):
        """Export challenges"""
        result = []

        for idx, challenge in enumerate(challenges, start=1):
            challenge_data = {
                'id': f'C{idx}',
                'name': challenge.name,
                'display_order': challenge.display_order,
            }

            if challenge.description:
                challenge_data['description'] = challenge.description

            # Get unique initiatives through links
            initiatives_dict = {}
            for link in challenge.initiative_links:
                init = link.initiative
                if init.id not in initiatives_dict:
                    initiatives_dict[init.id] = init

            initiatives = sorted(initiatives_dict.values(), key=lambda i: i.name)

            if initiatives:
                challenge_data['initiatives'] = YAMLExportService._export_initiatives(initiatives)

            result.append(challenge_data)

        return result

    @staticmethod
    def _export_initiatives(initiatives):
        """Export initiatives"""
        result = []

        for idx, initiative in enumerate(initiatives, start=1):
            init_data = {
                'id': f'I{idx}',
                'name': initiative.name,
            }

            if initiative.description:
                init_data['description'] = initiative.description

            # Get unique systems through links
            systems_dict = {}
            for link in initiative.system_links:
                sys = link.system
                if sys.id not in systems_dict:
                    systems_dict[sys.id] = sys

            systems = sorted(systems_dict.values(), key=lambda s: s.name)

            if systems:
                init_data['systems'] = YAMLExportService._export_systems(systems, initiative.id)

            result.append(init_data)

        return result

    @staticmethod
    def _export_systems(systems, initiative_id):
        """Export systems"""
        result = []

        for idx, system in enumerate(systems, start=1):
            sys_data = {
                'id': f'SYS{idx}',
                'name': system.name,
            }

            if system.description:
                sys_data['description'] = system.description

            # Find the link to get KPIs for this specific initiative-system pair
            link = next((l for l in system.initiative_links if l.initiative_id == initiative_id), None)
            if link and link.kpis:
                kpis = sorted(link.kpis, key=lambda k: k.name)
                sys_data['kpis'] = YAMLExportService._export_kpis(kpis)

            result.append(sys_data)

        return result

    @staticmethod
    def _export_kpis(kpis):
        """Export KPIs with their value type configurations"""
        result = []

        for kpi in kpis:
            kpi_data = {
                'name': kpi.name,
            }

            if kpi.description:
                kpi_data['description'] = kpi.description

            # Export value type configurations
            if kpi.value_type_configs:
                configs = sorted(kpi.value_type_configs,
                               key=lambda c: c.value_type.display_order)
                value_types_data = []

                for config in configs:
                    vt_config = {
                        'name': config.value_type.name
                    }

                    # Add colors if configured and value type is numeric
                    if config.value_type.kind == 'numeric':
                        if config.color_positive or config.color_zero or config.color_negative:
                            colors = {}
                            if config.color_positive:
                                colors['positive'] = config.color_positive
                            if config.color_zero:
                                colors['zero'] = config.color_zero
                            if config.color_negative:
                                colors['negative'] = config.color_negative
                            vt_config['colors'] = colors

                    value_types_data.append(vt_config)

                kpi_data['value_types'] = value_types_data

            result.append(kpi_data)

        return result

    @staticmethod
    def export_to_string(organization_id):
        """Export to YAML string (alias for export_to_yaml)"""
        return YAMLExportService.export_to_yaml(organization_id)
