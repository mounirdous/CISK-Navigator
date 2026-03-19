"""
Test Value Type Formula Service for KPI calculations
"""

from decimal import Decimal

import pytest

from app.models import KPI, Initiative, KPISnapshot, KPIValueTypeConfig, Space, System, ValueType
from app.services.value_type_formula_service import ValueTypeFormulaService


class TestValueTypeFormulaService:
    """Test formula calculation service"""

    @pytest.fixture
    def kpi_with_formula(self, db, sample_organization):
        """Create KPI with manual and formula value types"""
        from app.models import Challenge, InitiativeSystemLink

        # Create organizational hierarchy
        space = Space(organization_id=sample_organization.id, name="Test Space", description="Test")
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            organization_id=sample_organization.id, space_id=space.id, name="Test Challenge", description="Test"
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(
            organization_id=sample_organization.id,
            challenge_id=challenge.id,
            name="Test Initiative",
            description="Test",
        )
        db.session.add(initiative)
        db.session.flush()

        system = System(organization_id=sample_organization.id, name="Test System", description="Test")
        db.session.add(system)
        db.session.flush()

        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id)
        db.session.add(link)
        db.session.flush()

        kpi = KPI(initiative_system_link_id=link.id, name="Test KPI", description="")
        db.session.add(kpi)
        db.session.flush()

        # Create manual value types (Revenue and Cost)
        revenue_vt = ValueType(
            organization_id=sample_organization.id,
            name="Revenue",
            unit="USD",
            calculation_type=ValueType.CALC_MANUAL,
        )
        db.session.add(revenue_vt)
        db.session.flush()

        cost_vt = ValueType(
            organization_id=sample_organization.id, name="Cost", unit="USD", calculation_type=ValueType.CALC_MANUAL
        )
        db.session.add(cost_vt)
        db.session.flush()

        # Create formula value type (Net = Revenue - Cost)
        net_vt = ValueType(
            organization_id=sample_organization.id,
            name="Net",
            unit="USD",
            calculation_type=ValueType.CALC_FORMULA,
            calculation_config={
                "operation": ValueType.OP_SUBTRACT,
                "source_value_type_ids": [revenue_vt.id, cost_vt.id],
            },
        )
        db.session.add(net_vt)
        db.session.flush()

        # Create configs
        revenue_config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=revenue_vt.id, is_primary=True)
        db.session.add(revenue_config)
        db.session.flush()

        cost_config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=cost_vt.id, is_primary=False)
        db.session.add(cost_config)
        db.session.flush()

        net_config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=net_vt.id, is_primary=False)
        db.session.add(net_config)
        db.session.commit()

        return {
            "kpi": kpi,
            "revenue_vt": revenue_vt,
            "cost_vt": cost_vt,
            "net_vt": net_vt,
            "revenue_config": revenue_config,
            "cost_config": cost_config,
            "net_config": net_config,
        }

    def test_calculate_subtract_formula(self, app, db, kpi_with_formula):
        """Test basic subtraction formula: Net = Revenue - Cost"""
        with app.app_context():
            # Create snapshots for Revenue and Cost
            revenue_snapshot = KPISnapshot(
                kpi_value_type_config_id=kpi_with_formula["revenue_config"].id,
                snapshot_date="2024-01-01",
                value=Decimal("1000.00"),
            )
            db.session.add(revenue_snapshot)

            cost_snapshot = KPISnapshot(
                kpi_value_type_config_id=kpi_with_formula["cost_config"].id,
                snapshot_date="2024-01-01",
                value=Decimal("400.00"),
            )
            db.session.add(cost_snapshot)
            db.session.commit()

            # Calculate Net
            result = ValueTypeFormulaService.calculate_formula_value(
                kpi_id=kpi_with_formula["kpi"].id,
                formula_value_type=kpi_with_formula["net_vt"],
                snapshot_date="2024-01-01",
            )

            assert result == Decimal("600.00")

    def test_calculate_add_formula(self, app, db, sample_organization):
        """Test addition formula"""
        with app.app_context():
            # Create simple KPI structure
            from app.models import Challenge, InitiativeSystemLink

            space = Space(organization_id=sample_organization.id, name="Test Space", description="Test")
            db.session.add(space)
            db.session.flush()

            challenge = Challenge(
                organization_id=sample_organization.id, space_id=space.id, name="Test Challenge", description="Test"
            )
            db.session.add(challenge)
            db.session.flush()

            initiative = Initiative(
                organization_id=sample_organization.id,
                challenge_id=challenge.id,
                name="Test Initiative",
                description="Test",
            )
            db.session.add(initiative)
            db.session.flush()

            system = System(organization_id=sample_organization.id, name="Test System", description="Test")
            db.session.add(system)
            db.session.flush()

            link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id)
            db.session.add(link)
            db.session.flush()

            kpi = KPI(initiative_system_link_id=link.id, name="Test KPI", description="")
            db.session.add(kpi)
            db.session.flush()

            # Create manual value types
            a_vt = ValueType(
                organization_id=sample_organization.id, name="A", unit="units", calculation_type=ValueType.CALC_MANUAL
            )
            db.session.add(a_vt)
            db.session.flush()

            b_vt = ValueType(
                organization_id=sample_organization.id, name="B", unit="units", calculation_type=ValueType.CALC_MANUAL
            )
            db.session.add(b_vt)
            db.session.flush()

            # Create formula: Total = A + B
            total_vt = ValueType(
                organization_id=sample_organization.id,
                name="Total",
                unit="units",
                calculation_type=ValueType.CALC_FORMULA,
                calculation_config={"operation": ValueType.OP_ADD, "source_value_type_ids": [a_vt.id, b_vt.id]},
            )
            db.session.add(total_vt)
            db.session.flush()

            # Create configs
            a_config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=a_vt.id, is_primary=True)
            db.session.add(a_config)
            db.session.flush()

            b_config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=b_vt.id, is_primary=False)
            db.session.add(b_config)
            db.session.flush()

            # Create snapshots
            a_snapshot = KPISnapshot(
                kpi_value_type_config_id=a_config.id, snapshot_date="2024-01-01", value=Decimal("100")
            )
            db.session.add(a_snapshot)

            b_snapshot = KPISnapshot(
                kpi_value_type_config_id=b_config.id, snapshot_date="2024-01-01", value=Decimal("50")
            )
            db.session.add(b_snapshot)
            db.session.commit()

            # Calculate Total
            result = ValueTypeFormulaService.calculate_formula_value(
                kpi_id=kpi.id, formula_value_type=total_vt, snapshot_date="2024-01-01"
            )

            assert result == Decimal("150")

    def test_calculate_multiply_formula(self, app, db, sample_organization):
        """Test multiplication formula"""
        with app.app_context():
            # Create simple KPI structure
            from app.models import Challenge, InitiativeSystemLink

            space = Space(organization_id=sample_organization.id, name="Test Space", description="Test")
            db.session.add(space)
            db.session.flush()

            challenge = Challenge(
                organization_id=sample_organization.id, space_id=space.id, name="Test Challenge", description="Test"
            )
            db.session.add(challenge)
            db.session.flush()

            initiative = Initiative(
                organization_id=sample_organization.id,
                challenge_id=challenge.id,
                name="Test Initiative",
                description="Test",
            )
            db.session.add(initiative)
            db.session.flush()

            system = System(organization_id=sample_organization.id, name="Test System", description="Test")
            db.session.add(system)
            db.session.flush()

            link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id)
            db.session.add(link)
            db.session.flush()

            kpi = KPI(initiative_system_link_id=link.id, name="Test KPI", description="")
            db.session.add(kpi)
            db.session.flush()

            # Create manual value types (Quantity and Price)
            qty_vt = ValueType(
                organization_id=sample_organization.id,
                name="Quantity",
                unit="units",
                calculation_type=ValueType.CALC_MANUAL,
            )
            db.session.add(qty_vt)
            db.session.flush()

            price_vt = ValueType(
                organization_id=sample_organization.id, name="Price", unit="USD", calculation_type=ValueType.CALC_MANUAL
            )
            db.session.add(price_vt)
            db.session.flush()

            # Create formula: Revenue = Quantity * Price
            revenue_vt = ValueType(
                organization_id=sample_organization.id,
                name="Revenue",
                unit="USD",
                calculation_type=ValueType.CALC_FORMULA,
                calculation_config={
                    "operation": ValueType.OP_MULTIPLY,
                    "source_value_type_ids": [qty_vt.id, price_vt.id],
                },
            )
            db.session.add(revenue_vt)
            db.session.flush()

            # Create configs
            qty_config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=qty_vt.id, is_primary=True)
            db.session.add(qty_config)
            db.session.flush()

            price_config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=price_vt.id, is_primary=False)
            db.session.add(price_config)
            db.session.flush()

            # Create snapshots
            qty_snapshot = KPISnapshot(
                kpi_value_type_config_id=qty_config.id, snapshot_date="2024-01-01", value=Decimal("10")
            )
            db.session.add(qty_snapshot)

            price_snapshot = KPISnapshot(
                kpi_value_type_config_id=price_config.id, snapshot_date="2024-01-01", value=Decimal("25.50")
            )
            db.session.add(price_snapshot)
            db.session.commit()

            # Calculate Revenue
            result = ValueTypeFormulaService.calculate_formula_value(
                kpi_id=kpi.id, formula_value_type=revenue_vt, snapshot_date="2024-01-01"
            )

            assert result == Decimal("255.00")

    def test_calculate_divide_formula(self, app, db, sample_organization):
        """Test division formula"""
        with app.app_context():
            # Create simple KPI structure
            from app.models import Challenge, InitiativeSystemLink

            space = Space(organization_id=sample_organization.id, name="Test Space", description="Test")
            db.session.add(space)
            db.session.flush()

            challenge = Challenge(
                organization_id=sample_organization.id, space_id=space.id, name="Test Challenge", description="Test"
            )
            db.session.add(challenge)
            db.session.flush()

            initiative = Initiative(
                organization_id=sample_organization.id,
                challenge_id=challenge.id,
                name="Test Initiative",
                description="Test",
            )
            db.session.add(initiative)
            db.session.flush()

            system = System(organization_id=sample_organization.id, name="Test System", description="Test")
            db.session.add(system)
            db.session.flush()

            link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id)
            db.session.add(link)
            db.session.flush()

            kpi = KPI(initiative_system_link_id=link.id, name="Test KPI", description="")
            db.session.add(kpi)
            db.session.flush()

            # Create manual value types
            total_vt = ValueType(
                organization_id=sample_organization.id, name="Total", unit="USD", calculation_type=ValueType.CALC_MANUAL
            )
            db.session.add(total_vt)
            db.session.flush()

            count_vt = ValueType(
                organization_id=sample_organization.id,
                name="Count",
                unit="units",
                calculation_type=ValueType.CALC_MANUAL,
            )
            db.session.add(count_vt)
            db.session.flush()

            # Create formula: Average = Total / Count
            avg_vt = ValueType(
                organization_id=sample_organization.id,
                name="Average",
                unit="USD",
                calculation_type=ValueType.CALC_FORMULA,
                calculation_config={
                    "operation": ValueType.OP_DIVIDE,
                    "source_value_type_ids": [total_vt.id, count_vt.id],
                },
            )
            db.session.add(avg_vt)
            db.session.flush()

            # Create configs
            total_config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=total_vt.id, is_primary=True)
            db.session.add(total_config)
            db.session.flush()

            count_config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=count_vt.id, is_primary=False)
            db.session.add(count_config)
            db.session.flush()

            # Create snapshots
            total_snapshot = KPISnapshot(
                kpi_value_type_config_id=total_config.id, snapshot_date="2024-01-01", value=Decimal("1000")
            )
            db.session.add(total_snapshot)

            count_snapshot = KPISnapshot(
                kpi_value_type_config_id=count_config.id, snapshot_date="2024-01-01", value=Decimal("4")
            )
            db.session.add(count_snapshot)
            db.session.commit()

            # Calculate Average
            result = ValueTypeFormulaService.calculate_formula_value(
                kpi_id=kpi.id, formula_value_type=avg_vt, snapshot_date="2024-01-01"
            )

            assert result == Decimal("250")

    def test_formula_with_missing_data_returns_none(self, app, db, kpi_with_formula):
        """Test that formula returns None when source data is missing"""
        with app.app_context():
            # Only create Revenue snapshot, not Cost
            revenue_snapshot = KPISnapshot(
                kpi_value_type_config_id=kpi_with_formula["revenue_config"].id,
                snapshot_date="2024-01-01",
                value=Decimal("1000.00"),
            )
            db.session.add(revenue_snapshot)
            db.session.commit()

            # Calculate Net - should return None because Cost is missing
            result = ValueTypeFormulaService.calculate_formula_value(
                kpi_id=kpi_with_formula["kpi"].id,
                formula_value_type=kpi_with_formula["net_vt"],
                snapshot_date="2024-01-01",
            )

            assert result is None

    def test_division_by_zero_returns_none(self, app, db, sample_organization):
        """Test that division by zero returns None"""
        with app.app_context():
            # Create KPI structure
            space = Space(organization_id=sample_organization.id, name="Test Space", description="Test")
            db.session.add(space)
            db.session.flush()

            system = System(
                organization_id=sample_organization.id, space_id=space.id, name="Test System", description="Test"
            )
            db.session.add(system)
            db.session.flush()

            initiative = Initiative(
                organization_id=sample_organization.id, system_id=system.id, name="Test Initiative", description="Test"
            )
            db.session.add(initiative)
            db.session.flush()

            kpi = KPI(
                organization_id=sample_organization.id, initiative_id=initiative.id, name="Test KPI", description=""
            )
            db.session.add(kpi)
            db.session.flush()

            # Create value types
            numerator_vt = ValueType(
                organization_id=sample_organization.id,
                name="Numerator",
                unit="units",
                calculation_type=ValueType.CALC_MANUAL,
            )
            db.session.add(numerator_vt)
            db.session.flush()

            denominator_vt = ValueType(
                organization_id=sample_organization.id,
                name="Denominator",
                unit="units",
                calculation_type=ValueType.CALC_MANUAL,
            )
            db.session.add(denominator_vt)
            db.session.flush()

            # Create formula with division
            result_vt = ValueType(
                organization_id=sample_organization.id,
                name="Result",
                unit="units",
                calculation_type=ValueType.CALC_FORMULA,
                calculation_config={
                    "operation": ValueType.OP_DIVIDE,
                    "source_value_type_ids": [numerator_vt.id, denominator_vt.id],
                },
            )
            db.session.add(result_vt)
            db.session.flush()

            # Create configs
            numerator_config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=numerator_vt.id, is_primary=True)
            db.session.add(numerator_config)
            db.session.flush()

            denominator_config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=denominator_vt.id, is_primary=False)
            db.session.add(denominator_config)
            db.session.flush()

            # Create snapshots with denominator = 0
            numerator_snapshot = KPISnapshot(
                kpi_value_type_config_id=numerator_config.id, snapshot_date="2024-01-01", value=Decimal("100")
            )
            db.session.add(numerator_snapshot)

            denominator_snapshot = KPISnapshot(
                kpi_value_type_config_id=denominator_config.id, snapshot_date="2024-01-01", value=Decimal("0")
            )
            db.session.add(denominator_snapshot)
            db.session.commit()

            # Calculate - should return None due to division by zero
            result = ValueTypeFormulaService.calculate_formula_value(
                kpi_id=kpi.id, formula_value_type=result_vt, snapshot_date="2024-01-01"
            )

            assert result is None

    def test_get_kpi_values_for_formula_calculation(self, app, db, kpi_with_formula):
        """Test pre-fetching manual values for performance"""
        with app.app_context():
            # Create snapshots
            revenue_snapshot = KPISnapshot(
                kpi_value_type_config_id=kpi_with_formula["revenue_config"].id,
                snapshot_date="2024-01-01",
                value=Decimal("1000.00"),
            )
            db.session.add(revenue_snapshot)

            cost_snapshot = KPISnapshot(
                kpi_value_type_config_id=kpi_with_formula["cost_config"].id,
                snapshot_date="2024-01-01",
                value=Decimal("400.00"),
            )
            db.session.add(cost_snapshot)
            db.session.commit()

            # Get pre-fetched values
            values = ValueTypeFormulaService.get_kpi_values_for_formula_calculation(
                kpi_with_formula["kpi"].id, "2024-01-01"
            )

            assert values[kpi_with_formula["revenue_vt"].id] == Decimal("1000.00")
            assert values[kpi_with_formula["cost_vt"].id] == Decimal("400.00")
            # Formula value type should NOT be in the dict (it's not manual)
            assert kpi_with_formula["net_vt"].id not in values
