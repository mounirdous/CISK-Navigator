"""
Snapshot Pivot Service

Provides pivot table and time-series analysis of snapshots.
"""

from collections import defaultdict
from typing import Dict, List

from app.extensions import db
from app.models import KPI, Initiative, InitiativeSystemLink, KPISnapshot, KPIValueTypeConfig, ValueType


class SnapshotPivotService:
    """Service for pivot table analysis of snapshots"""

    @staticmethod
    def get_available_years(organization_id: int) -> List[int]:
        """Get all years that have snapshots for an organization"""
        years = (
            db.session.query(KPISnapshot.year)
            .distinct()
            .join(KPIValueTypeConfig, KPISnapshot.kpi_value_type_config_id == KPIValueTypeConfig.id)
            .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .filter(Initiative.organization_id == organization_id, KPISnapshot.year.isnot(None))
            .order_by(KPISnapshot.year.desc())
            .all()
        )
        return [y[0] for y in years if y[0]]

    @staticmethod
    def get_pivot_data(
        organization_id: int,
        year: int,
        view_type: str = "quarterly",  # 'monthly', 'quarterly', 'yearly'
        space_id: int = None,
        value_type_id: int = None,
    ) -> Dict:
        """
        Get pivot table data: KPIs as rows, periods as columns

        Args:
            organization_id: Organization ID
            year: Year to analyze
            view_type: 'monthly', 'quarterly', or 'yearly'
            space_id: Optional space filter
            value_type_id: Optional value type filter

        Returns:
            Dict with structure:
            {
                'periods': ['Q1 2026', 'Q2 2026', ...],
                'kpis': [
                    {
                        'kpi_id': 1,
                        'kpi_name': 'Finance Cost',
                        'value_type': 'Cost (CHF)',
                        'values': {
                            'Q1 2026': {'value': 210000, 'status': 'strong'},
                            'Q2 2026': {'value': 225000, 'status': 'strong'},
                            ...
                        }
                    },
                    ...
                ]
            }
        """
        # Build query for snapshots
        query = (
            db.session.query(KPISnapshot, KPIValueTypeConfig, KPI, ValueType)
            .join(KPIValueTypeConfig, KPISnapshot.kpi_value_type_config_id == KPIValueTypeConfig.id)
            .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
            .join(ValueType, KPIValueTypeConfig.value_type_id == ValueType.id)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .filter(Initiative.organization_id == organization_id, KPISnapshot.year == year)
        )

        # Apply filters
        if space_id:
            # Filter by space through the hierarchy
            from app.models import Challenge

            query = query.join(Challenge, Initiative.challenge_links).filter(Challenge.space_id == space_id)

        if value_type_id:
            query = query.filter(ValueType.id == value_type_id)

        # Fetch all snapshots
        results = query.all()

        # Generate period labels based on view type
        if view_type == "monthly":
            periods = [f"{SnapshotPivotService._month_name(m)} {year}" for m in range(1, 13)]
        elif view_type == "quarterly":
            periods = [f"Q{q} {year}" for q in range(1, 5)]
        else:  # yearly
            # For yearly view, show multiple years
            min_year = min([r[0].year for r in results]) if results else year
            max_year = max([r[0].year for r in results]) if results else year
            periods = [str(y) for y in range(min_year, max_year + 1)]

        # Group data by KPI config
        kpi_data = defaultdict(lambda: {"kpi_name": "", "value_type_name": "", "values": {}})

        for snapshot, config, kpi, value_type in results:
            key = config.id

            # Store KPI metadata
            kpi_data[key]["kpi_id"] = kpi.id
            kpi_data[key]["kpi_name"] = kpi.name
            unit = value_type.unit_label if value_type.unit_label else ""
            kpi_data[key]["value_type_name"] = f"{value_type.name} ({unit})" if unit else value_type.name
            kpi_data[key]["value_type"] = value_type

            # Determine period key
            if view_type == "monthly":
                period_label = f"{SnapshotPivotService._month_name(snapshot.month)} {snapshot.year}"
            elif view_type == "quarterly":
                period_label = f"Q{snapshot.quarter} {snapshot.year}"
            else:  # yearly
                period_label = str(snapshot.year)

            # Store value
            kpi_data[key]["values"][period_label] = {
                "value": snapshot.get_value(),
                "status": snapshot.consensus_status,
                "snapshot_id": snapshot.id,
            }

        # Convert to list format
        kpis = []
        for config_id, data in kpi_data.items():
            kpis.append(
                {
                    "config_id": config_id,
                    "kpi_id": data["kpi_id"],
                    "kpi_name": data["kpi_name"],
                    "value_type_name": data["value_type_name"],
                    "value_type": data["value_type"],
                    "values": data["values"],
                }
            )

        # Sort KPIs by name
        kpis.sort(key=lambda x: x["kpi_name"])

        return {"periods": periods, "kpis": kpis, "view_type": view_type, "year": year}

    @staticmethod
    def _month_name(month: int) -> str:
        """Get month name from number"""
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        return months[month - 1] if 1 <= month <= 12 else str(month)

    @staticmethod
    def get_chart_data(
        organization_id: int, year: int, kpi_config_ids: List[int], view_type: str = "quarterly"
    ) -> Dict:
        """
        Get data formatted for charting

        Args:
            organization_id: Organization ID
            year: Year to analyze
            kpi_config_ids: List of KPI config IDs to include
            view_type: 'monthly', 'quarterly', or 'yearly'

        Returns:
            Dict with structure suitable for Chart.js:
            {
                'labels': ['Q1 2026', 'Q2 2026', ...],
                'datasets': [
                    {
                        'label': 'Finance Cost',
                        'data': [210000, 225000, 240000, null],
                        'borderColor': '#007bff',
                        'backgroundColor': 'rgba(0, 123, 255, 0.1)'
                    },
                    ...
                ]
            }
        """
        # Get pivot data
        pivot = SnapshotPivotService.get_pivot_data(organization_id, year, view_type)

        # Filter to selected KPIs
        selected_kpis = [kpi for kpi in pivot["kpis"] if kpi["config_id"] in kpi_config_ids]

        # Build chart datasets
        datasets = []
        colors = [
            "#007bff",  # Blue
            "#28a745",  # Green
            "#dc3545",  # Red
            "#ffc107",  # Yellow
            "#17a2b8",  # Cyan
            "#6610f2",  # Purple
            "#fd7e14",  # Orange
            "#20c997",  # Teal
        ]

        for idx, kpi in enumerate(selected_kpis):
            color = colors[idx % len(colors)]

            # Build data array matching periods
            data = []
            for period in pivot["periods"]:
                value_data = kpi["values"].get(period)
                data.append(value_data["value"] if value_data else None)

            datasets.append(
                {
                    "label": f"{kpi['kpi_name']} ({kpi['value_type_name']})",
                    "data": data,
                    "borderColor": color,
                    "backgroundColor": f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)",
                    "tension": 0.1,
                }
            )

        return {"labels": pivot["periods"], "datasets": datasets}
