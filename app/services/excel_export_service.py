"""
Excel Export Service

Exports workspace data to Excel with hierarchical structure and row grouping.
"""

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.models import Space, ValueType


class ExcelExportService:
    """Service for exporting workspace data to Excel"""

    # Colors matching workspace UI
    COLOR_SPACE = "D6E9F7"  # Blue
    COLOR_CHALLENGE = "F0F4F8"  # Light gray
    COLOR_INITIATIVE = "E8E8E8"  # Gray
    COLOR_SYSTEM = "E3F2FD"  # Light blue
    COLOR_KPI = "FFF9C4"  # Yellow

    @staticmethod
    def export_workspace(organization_id):
        """
        Export workspace data to Excel file.

        Returns:
            BytesIO: Excel file as bytes
        """
        # Get data
        spaces = Space.query.filter_by(organization_id=organization_id).order_by(Space.display_order, Space.name).all()

        value_types = (
            ValueType.query.filter_by(organization_id=organization_id, is_active=True)
            .order_by(ValueType.display_order)
            .all()
        )

        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Workspace"

        # Set column widths
        ws.column_dimensions["A"].width = 50  # Structure column
        for i, vt in enumerate(value_types, start=2):
            col_letter = get_column_letter(i)
            ws.column_dimensions[col_letter].width = 15

        # Write header
        ExcelExportService._write_header(ws, value_types)

        # Write data with grouping
        current_row = 2
        for space in spaces:
            current_row = ExcelExportService._write_space(ws, space, value_types, current_row)

        # Freeze header row
        ws.freeze_panes = "A2"

        # Save to BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @staticmethod
    def _write_header(ws, value_types):
        """Write header row"""
        # Structure header
        cell = ws.cell(row=1, column=1, value="Structure")
        cell.font = Font(bold=True, size=12)
        cell.fill = PatternFill(start_color="4A4A4A", end_color="4A4A4A", fill_type="solid")
        cell.font = Font(bold=True, size=12, color="FFFFFF")
        cell.alignment = Alignment(horizontal="left", vertical="center")

        # Value type headers
        for i, vt in enumerate(value_types, start=2):
            cell = ws.cell(row=1, column=i, value=vt.name)
            cell.font = Font(bold=True, size=11)
            cell.fill = PatternFill(start_color="4A4A4A", end_color="4A4A4A", fill_type="solid")
            cell.font = Font(bold=True, size=11, color="FFFFFF")
            cell.alignment = Alignment(horizontal="center", vertical="center")

            # Add unit label as comment if available
            if vt.unit_label:
                cell.value = f"{vt.name}\n({vt.unit_label})"

    @staticmethod
    def _write_space(ws, space, value_types, start_row):
        """Write space and all its children"""
        row = start_row

        # Space row
        cell = ws.cell(row=row, column=1, value=f"▼ {space.name}")
        cell.font = Font(bold=True, size=11)
        cell.fill = PatternFill(
            start_color=ExcelExportService.COLOR_SPACE, end_color=ExcelExportService.COLOR_SPACE, fill_type="solid"
        )

        # Space rollup values
        for i, vt in enumerate(value_types, start=2):
            rollup = space.get_rollup_value(vt.id)
            if rollup:
                value_str = ExcelExportService._format_value(rollup["value"], vt)
                status = "✓" if rollup["is_complete"] else "⚠"
                cell = ws.cell(row=row, column=i, value=f"{value_str} {status}")
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.fill = PatternFill(
                    start_color=ExcelExportService.COLOR_SPACE,
                    end_color=ExcelExportService.COLOR_SPACE,
                    fill_type="solid",
                )
                cell.font = Font(bold=True)

        row += 1

        # Challenges
        for challenge in space.challenges:
            row = ExcelExportService._write_challenge(ws, challenge, value_types, row)

        # Group space children rows (Excel outlining)
        if row > start_row + 1:
            ws.row_dimensions.group(start_row + 1, row - 1, outline_level=1)

        return row

    @staticmethod
    def _write_challenge(ws, challenge, value_types, start_row):
        """Write challenge and all its children"""
        row = start_row

        # Challenge row
        cell = ws.cell(row=row, column=1, value=f"  → {challenge.name}")
        cell.font = Font(bold=True, size=10)
        cell.fill = PatternFill(
            start_color=ExcelExportService.COLOR_CHALLENGE,
            end_color=ExcelExportService.COLOR_CHALLENGE,
            fill_type="solid",
        )

        # Challenge rollup values
        for i, vt in enumerate(value_types, start=2):
            rollup = challenge.get_rollup_value(vt.id)
            if rollup:
                value_str = ExcelExportService._format_value(rollup["value"], vt)
                status = "✓" if rollup["is_complete"] else "⚠"
                cell = ws.cell(row=row, column=i, value=f"{value_str} {status}")
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.fill = PatternFill(
                    start_color=ExcelExportService.COLOR_CHALLENGE,
                    end_color=ExcelExportService.COLOR_CHALLENGE,
                    fill_type="solid",
                )

        row += 1

        # Initiatives
        for init_link in challenge.initiative_links:
            row = ExcelExportService._write_initiative(ws, init_link.initiative, value_types, row)

        # Group challenge children
        if row > start_row + 1:
            ws.row_dimensions.group(start_row + 1, row - 1, outline_level=2)

        return row

    @staticmethod
    def _write_initiative(ws, initiative, value_types, start_row):
        """Write initiative and all its children"""
        row = start_row

        # Initiative row
        cell = ws.cell(row=row, column=1, value=f"    ➜ {initiative.name}")
        cell.font = Font(size=10)
        cell.fill = PatternFill(
            start_color=ExcelExportService.COLOR_INITIATIVE,
            end_color=ExcelExportService.COLOR_INITIATIVE,
            fill_type="solid",
        )

        # Initiative rollup values
        for i, vt in enumerate(value_types, start=2):
            rollup = initiative.get_rollup_value(vt.id)
            if rollup:
                value_str = ExcelExportService._format_value(rollup["value"], vt)
                status = "✓" if rollup["is_complete"] else "⚠"
                cell = ws.cell(row=row, column=i, value=f"{value_str} {status}")
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.fill = PatternFill(
                    start_color=ExcelExportService.COLOR_INITIATIVE,
                    end_color=ExcelExportService.COLOR_INITIATIVE,
                    fill_type="solid",
                )

        row += 1

        # Systems
        for sys_link in initiative.system_links:
            row = ExcelExportService._write_system(ws, sys_link, value_types, row)

        # Group initiative children
        if row > start_row + 1:
            ws.row_dimensions.group(start_row + 1, row - 1, outline_level=3)

        return row

    @staticmethod
    def _write_system(ws, sys_link, value_types, start_row):
        """Write system and all its KPIs"""
        row = start_row
        system = sys_link.system

        # System row
        cell = ws.cell(row=row, column=1, value=f"      ⇨ {system.name}")
        cell.font = Font(size=9)
        cell.fill = PatternFill(
            start_color=ExcelExportService.COLOR_SYSTEM, end_color=ExcelExportService.COLOR_SYSTEM, fill_type="solid"
        )

        # System rollup values
        for i, vt in enumerate(value_types, start=2):
            rollup = sys_link.get_rollup_value(vt.id)
            if rollup:
                value_str = ExcelExportService._format_value(rollup["value"], vt)
                status = "✓" if rollup["is_complete"] else "⚠"
                cell = ws.cell(row=row, column=i, value=f"{value_str} {status}")
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.fill = PatternFill(
                    start_color=ExcelExportService.COLOR_SYSTEM,
                    end_color=ExcelExportService.COLOR_SYSTEM,
                    fill_type="solid",
                )

        row += 1

        # KPIs
        for kpi in sys_link.kpis:
            row = ExcelExportService._write_kpi(ws, kpi, value_types, row)

        # Group system children
        if row > start_row + 1:
            ws.row_dimensions.group(start_row + 1, row - 1, outline_level=4)

        return row

    @staticmethod
    def _write_kpi(ws, kpi, value_types, row):
        """Write KPI row"""
        # KPI name
        cell = ws.cell(row=row, column=1, value=f"        ⟶ {kpi.name}")
        cell.font = Font(size=9, italic=True)
        cell.fill = PatternFill(
            start_color=ExcelExportService.COLOR_KPI, end_color=ExcelExportService.COLOR_KPI, fill_type="solid"
        )

        # KPI values
        for i, vt in enumerate(value_types, start=2):
            # Find config for this value type
            config = next((c for c in kpi.value_type_configs if c.value_type_id == vt.id), None)
            if config:
                consensus = config.get_consensus_value()
                if consensus and consensus["value"] is not None:
                    value_str = ExcelExportService._format_value(consensus["value"], vt)
                    cell = ws.cell(row=row, column=i, value=value_str)
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.fill = PatternFill(
                        start_color=ExcelExportService.COLOR_KPI,
                        end_color=ExcelExportService.COLOR_KPI,
                        fill_type="solid",
                    )
                else:
                    cell = ws.cell(row=row, column=i, value="Click to enter")
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.fill = PatternFill(
                        start_color=ExcelExportService.COLOR_KPI,
                        end_color=ExcelExportService.COLOR_KPI,
                        fill_type="solid",
                    )
                    cell.font = Font(color="999999", italic=True, size=8)

        return row + 1

    @staticmethod
    def _format_value(value, value_type):
        """Format value according to value type"""
        if value is None:
            return ""

        if value_type.kind == "numeric":
            if value_type.numeric_format == "integer":
                return str(int(value))
            else:
                decimal_places = value_type.decimal_places if value_type.decimal_places is not None else 2
                formatted = f"{float(value):.{decimal_places}f}"
                if value_type.unit_label:
                    return f"{formatted} {value_type.unit_label}"
                return formatted
        elif value_type.kind == "risk":
            risk_map = {1: "!", 2: "!!", 3: "!!!"}
            return risk_map.get(int(value), "")
        elif value_type.kind == "positive_impact":
            impact_map = {1: "★", 2: "★★", 3: "★★★"}
            return impact_map.get(int(value), "")
        elif value_type.kind == "negative_impact":
            impact_map = {1: "▼", 2: "▼▼", 3: "▼▼▼"}
            return impact_map.get(int(value), "")
        elif value_type.kind == "level":
            level_map = {1: "●", 2: "●●", 3: "●●●"}
            return level_map.get(int(value), "")
        elif value_type.kind == "sentiment":
            sentiment_map = {1: "☹️", 2: "😐", 3: "😊"}
            return sentiment_map.get(int(value), "")

        return str(value)
