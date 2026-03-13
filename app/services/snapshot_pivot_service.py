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
        year: int = None,
        view_type: str = "quarterly",
        space_id: int = None,
        challenge_id: int = None,
        value_type_id: int = None,
        year_start: int = None,
        year_end: int = None,
        periods: List[int] = None,
        custom_months: List[tuple] = None,
    ) -> Dict:
        """
        Get pivot table data: KPIs as rows, periods as columns

        Args:
            organization_id: Organization ID
            year: Year to analyze (legacy - use year_start/year_end instead)
            view_type: 'monthly', 'quarterly', or 'yearly'
            space_id: Optional space filter
            value_type_id: Optional value type filter
            year_start: Start year for range
            year_end: End year for range
            periods: List of quarters (1-4) or months (1-12) to include

        Returns:
            Dict with structure:
            {
                'periods': ['Q1 2026', 'Q2 2026', ...],
                'kpis': [...]
            }
        """
        # Handle legacy year parameter
        if year_start is None:
            year_start = year
        if year_end is None:
            year_end = year_start

        # Build query for snapshots
        query = (
            db.session.query(KPISnapshot, KPIValueTypeConfig, KPI, ValueType)
            .join(KPIValueTypeConfig, KPISnapshot.kpi_value_type_config_id == KPIValueTypeConfig.id)
            .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
            .join(ValueType, KPIValueTypeConfig.value_type_id == ValueType.id)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .filter(
                Initiative.organization_id == organization_id,
                KPISnapshot.year >= year_start,
                KPISnapshot.year <= year_end,
            )
        )

        # Apply filters
        if space_id or challenge_id:
            # Filter by space/challenge through the hierarchy
            from app.models import Challenge, ChallengeInitiativeLink

            query = query.join(ChallengeInitiativeLink, Initiative.challenge_links).join(
                Challenge, ChallengeInitiativeLink.challenge
            )

            if space_id:
                query = query.filter(Challenge.space_id == space_id)
            if challenge_id:
                query = query.filter(Challenge.id == challenge_id)

        if value_type_id:
            query = query.filter(ValueType.id == value_type_id)

        # Filter by specific periods (quarters or months) or custom month range
        if custom_months:
            # Custom date range: filter by specific (year, month) tuples
            from sqlalchemy import and_, or_

            month_conditions = [and_(KPISnapshot.year == y, KPISnapshot.month == m) for y, m in custom_months]
            query = query.filter(or_(*month_conditions))
        elif periods:
            if view_type == "quarterly":
                query = query.filter(KPISnapshot.quarter.in_(periods))
            elif view_type == "monthly":
                query = query.filter(KPISnapshot.month.in_(periods))

        # Fetch all snapshots - order by snapshot_date DESC to get most recent first
        results = query.order_by(KPISnapshot.snapshot_date.desc()).all()

        # Generate period labels based on view type and custom_months
        all_periods = []
        if custom_months:
            # Custom range: show based on view_type
            if view_type == "monthly":
                all_periods = [f"{SnapshotPivotService._month_name(m)} {y}" for y, m in custom_months]
            elif view_type == "quarterly":
                # Convert months to quarters and dedupe
                quarters_set = set()
                for y, m in custom_months:
                    q = (m - 1) // 3 + 1
                    quarters_set.add((y, q))
                for y, q in sorted(quarters_set):
                    all_periods.append(f"Q{q} {y}")
            else:  # yearly
                years_set = {y for y, m in custom_months}
                all_periods = [str(y) for y in sorted(years_set)]
        elif view_type == "monthly":
            for y in range(year_start, year_end + 1):
                month_list = periods if periods else range(1, 13)
                for m in month_list:
                    all_periods.append(f"{SnapshotPivotService._month_name(m)} {y}")
        elif view_type == "quarterly":
            for y in range(year_start, year_end + 1):
                quarter_list = periods if periods else range(1, 5)
                for q in quarter_list:
                    all_periods.append(f"Q{q} {y}")
        else:  # yearly
            all_periods = [str(y) for y in range(year_start, year_end + 1)]

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
            kpi_data[key]["config"] = config

            # Determine period key
            if view_type == "monthly":
                period_label = f"{SnapshotPivotService._month_name(snapshot.month)} {snapshot.year}"
            elif view_type == "quarterly":
                period_label = f"Q{snapshot.quarter} {snapshot.year}"
            else:  # yearly
                period_label = str(snapshot.year)

            # Store value (only if not already present - keeps most recent due to DESC ordering)
            if period_label not in kpi_data[key]["values"]:
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
                    "config": data["config"],
                    "values": data["values"],
                }
            )

        # Sort KPIs by name
        kpis.sort(key=lambda x: x["kpi_name"])

        return {
            "periods": all_periods,
            "kpis": kpis,
            "view_type": view_type,
            "year": year_start,
            "year_start": year_start,
            "year_end": year_end,
        }

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
        organization_id: int, year: int, kpi_config_ids: List[int], view_type: str = "quarterly", show_targets: bool = False
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

            # Add target line if show_targets is True and target exists
            if show_targets and kpi.get("config") and kpi["config"].target_value:
                target_value = float(kpi["config"].target_value)
                target_data = [target_value] * len(pivot["periods"])
                target_direction = kpi["config"].target_direction or "maximize"
                tolerance_pct = kpi["config"].target_tolerance_pct or 10

                # Target direction indicators
                if target_direction == "maximize":
                    label_suffix = "↑"  # Arrow up for maximize
                elif target_direction == "minimize":
                    label_suffix = "↓"  # Arrow down for minimize
                else:  # exact
                    label_suffix = f"±{tolerance_pct}%"

                datasets.append(
                    {
                        "label": f"{kpi['kpi_name']} - Target {label_suffix}",
                        "data": target_data,
                        "borderColor": color,
                        "backgroundColor": "transparent",
                        "borderDash": [5, 5],
                        "borderWidth": 2,
                        "pointRadius": 0,
                        "tension": 0,
                        "fill": False,
                    }
                )

                # Add band for "exact" targets
                if target_direction == "exact":
                    # Calculate upper and lower bounds
                    upper_bound = target_value * (1 + tolerance_pct / 100)
                    lower_bound = target_value * (1 - tolerance_pct / 100)

                    upper_data = [upper_bound] * len(pivot["periods"])
                    lower_data = [lower_bound] * len(pivot["periods"])

                    # Add upper bound (invisible line)
                    datasets.append(
                        {
                            "label": f"{kpi['kpi_name']} - Upper Bound",
                            "data": upper_data,
                            "borderColor": "transparent",
                            "backgroundColor": f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.15)",
                            "borderWidth": 0,
                            "pointRadius": 0,
                            "tension": 0,
                            "fill": False,
                        }
                    )

                    # Add lower bound with fill to upper
                    datasets.append(
                        {
                            "label": f"{kpi['kpi_name']} - Lower Bound",
                            "data": lower_data,
                            "borderColor": "transparent",
                            "backgroundColor": f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.15)",
                            "borderWidth": 0,
                            "pointRadius": 0,
                            "tension": 0,
                            "fill": "-1",  # Fill to previous dataset (upper bound)
                        }
                    )

        return {"labels": pivot["periods"], "datasets": datasets}
