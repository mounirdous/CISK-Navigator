"""
Unit tests for KPI rollup functionality with type safety
Tests aggregation across the hierarchy: KPI → System → Initiative → Challenge → Space
"""

from decimal import Decimal

from app.models import ValueType
from app.services.aggregation_service import AggregationService
from app.services.consensus_service import ConsensusService


class MockContribution:
    """Mock contribution for testing"""

    def __init__(self, numeric_value=None, qualitative_level=None):
        self.numeric_value = numeric_value
        self.qualitative_level = qualitative_level


class TestRollupTypeMixing:
    """Test that rollup handles mixed types (Decimal, int, float) correctly"""

    def test_sum_with_decimal_and_float(self, db, sample_organization):
        """Test sum aggregation with mixed Decimal and float values"""
        value_type = ValueType(
            name="Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        # Mix Decimal, float, and int values (simulating real-world scenario)
        values = [Decimal("100.50"), 200.75, 50, Decimal("300.25")]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        # Should convert all to float and sum correctly
        assert result == 651.5
        assert isinstance(result, float)

    def test_sum_with_all_decimals(self, db, sample_organization):
        """Test sum with pure Decimal values"""
        value_type = ValueType(
            name="Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("100.50"), Decimal("200.75"), Decimal("50.25")]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        assert result == 351.5
        assert isinstance(result, float)

    def test_sum_with_all_integers(self, db, sample_organization):
        """Test sum with pure integer values"""
        value_type = ValueType(
            name="Count", kind="numeric", numeric_format="integer", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [10, 20, 30, 40]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        assert result == 100.0
        assert isinstance(result, float)

    def test_min_with_mixed_types(self, db, sample_organization):
        """Test min aggregation with mixed types"""
        value_type = ValueType(
            name="Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("100.50"), 50.25, 75, Decimal("25.75")]
        result = AggregationService.aggregate_values(values, "min", value_type)

        assert result == 25.75
        assert isinstance(result, float)

    def test_max_with_mixed_types(self, db, sample_organization):
        """Test max aggregation with mixed types"""
        value_type = ValueType(
            name="Revenue", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("100.50"), 200.75, 150, Decimal("175.25")]
        result = AggregationService.aggregate_values(values, "max", value_type)

        assert result == 200.75
        assert isinstance(result, float)

    def test_avg_with_mixed_types(self, db, sample_organization):
        """Test average aggregation with mixed types"""
        value_type = ValueType(
            name="Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("100"), 200, 300.0, Decimal("400")]
        result = AggregationService.aggregate_values(values, "avg", value_type)

        assert result == 250.0
        assert isinstance(result, float)

    def test_median_with_mixed_types(self, db, sample_organization):
        """Test median aggregation with mixed types"""
        value_type = ValueType(
            name="Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("10"), 20, 30.0, Decimal("40"), 50]
        result = AggregationService.aggregate_values(values, "median", value_type)

        assert result == 30.0
        assert isinstance(result, float)

    def test_large_decimal_precision(self, db, sample_organization):
        """Test handling of high-precision Decimal values"""
        value_type = ValueType(
            name="Precise Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [
            Decimal("1234567.891234"),
            Decimal("9876543.219876"),
            Decimal("5555555.555555"),
        ]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        # Should handle precision conversion to float
        assert isinstance(result, float)
        assert abs(result - 16666666.666665) < 0.01  # Allow small floating point error


class TestRollupConsensus:
    """Test consensus calculation with different contribution types"""

    def test_consensus_with_decimal_contributions(self):
        """Test consensus with Decimal numeric values"""
        contributions = [
            MockContribution(numeric_value=Decimal("100.50")),
            MockContribution(numeric_value=Decimal("100.50")),
            MockContribution(numeric_value=Decimal("100.50")),
        ]
        result = ConsensusService.calculate_consensus(contributions)

        assert result["status"] == ConsensusService.STATUS_STRONG
        assert result["value"] == 100.50
        assert result["is_rollup_eligible"] is True

    def test_consensus_with_mixed_numeric_types(self):
        """Test consensus with mixed Decimal/float/int contributions"""
        contributions = [
            MockContribution(numeric_value=Decimal("100")),
            MockContribution(numeric_value=100.0),
            MockContribution(numeric_value=100),
        ]
        result = ConsensusService.calculate_consensus(contributions)

        # All should be considered equal (100)
        assert result["status"] == ConsensusService.STATUS_STRONG
        assert result["value"] == 100.0
        assert result["is_rollup_eligible"] is True

    def test_single_contribution_eligible_for_rollup(self):
        """Test that single contribution is eligible for rollup"""
        contributions = [MockContribution(numeric_value=Decimal("500.25"))]
        result = ConsensusService.calculate_consensus(contributions)

        assert result["status"] == ConsensusService.STATUS_STRONG
        assert result["value"] == 500.25
        assert result["count"] == 1
        assert result["is_rollup_eligible"] is True

    def test_weak_consensus_not_eligible(self):
        """Test that weak consensus is not eligible for rollup"""
        contributions = [
            MockContribution(numeric_value=100),
            MockContribution(numeric_value=100),
            MockContribution(numeric_value=100),
            MockContribution(numeric_value=90),
        ]
        result = ConsensusService.calculate_consensus(contributions)

        assert result["status"] == ConsensusService.STATUS_WEAK
        assert result["is_rollup_eligible"] is False


class TestRollupAggregationFormulas:
    """Test all aggregation formulas with realistic scenarios"""

    def test_sum_formula_mixed_values(self, db, sample_organization):
        """Test sum formula with mixed Decimal and float values"""
        value_type = ValueType(
            name="Total Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        # Simulate KPI values: manual entries (Decimal) + formula results (float)
        values = [
            Decimal("210000"),  # Manual entry: 210k CHF
            200.0,  # Formula result: 200
            900.0,  # Formula result: 900
            Decimal("1375000"),  # Manual entry: 1375k CHF
            Decimal("105000"),  # Manual entry: 105k CHF
        ]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        assert result == 1691100.0
        assert isinstance(result, float)

    def test_avg_formula_with_decimals(self, db, sample_organization):
        """Test average formula with Decimal values"""
        value_type = ValueType(
            name="Average Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("100"), Decimal("200"), Decimal("300")]
        result = AggregationService.aggregate_values(values, "avg", value_type)

        assert result == 200.0
        assert isinstance(result, float)

    def test_min_formula_finds_smallest(self, db, sample_organization):
        """Test min formula correctly identifies smallest value"""
        value_type = ValueType(
            name="Min Value", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("1000"), 500.5, 250, Decimal("750.25")]
        result = AggregationService.aggregate_values(values, "min", value_type)

        assert result == 250.0
        assert isinstance(result, float)

    def test_max_formula_finds_largest(self, db, sample_organization):
        """Test max formula correctly identifies largest value"""
        value_type = ValueType(
            name="Max Value", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("1000"), 2000.5, 1500, Decimal("1750.75")]
        result = AggregationService.aggregate_values(values, "max", value_type)

        assert result == 2000.5
        assert isinstance(result, float)

    def test_median_formula_odd_count(self, db, sample_organization):
        """Test median with odd number of values"""
        value_type = ValueType(
            name="Median Value", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("10"), 20, 30.0, Decimal("40"), 50]
        result = AggregationService.aggregate_values(values, "median", value_type)

        assert result == 30.0
        assert isinstance(result, float)

    def test_median_formula_even_count(self, db, sample_organization):
        """Test median with even number of values"""
        value_type = ValueType(
            name="Median Value", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("10"), 20, 30.0, Decimal("40")]
        result = AggregationService.aggregate_values(values, "median", value_type)

        assert result == 25.0  # Average of 20 and 30
        assert isinstance(result, float)

    def test_count_formula(self, db, sample_organization):
        """Test count formula returns number of values"""
        value_type = ValueType(
            name="Count", kind="numeric", numeric_format="integer", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("10"), 20, 30.0, Decimal("40"), 50]
        result = AggregationService.aggregate_values(values, "count", value_type)

        assert result == 5
        assert isinstance(result, int)


class TestRollupPartialData:
    """Test rollup behavior with partial/missing data"""

    def test_rollup_with_some_missing_kpis(self, db, sample_organization):
        """Test that rollup works when some KPIs have no data"""
        value_type = ValueType(
            name="Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        # 3 KPIs with data, 2 without (simulating 5/6 scenario)
        values = [Decimal("100"), 200.0, Decimal("300")]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        # Should aggregate available values
        assert result == 600.0
        assert isinstance(result, float)

    def test_rollup_with_single_value(self, db, sample_organization):
        """Test that rollup works with just one value"""
        value_type = ValueType(
            name="Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("210000")]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        assert result == 210000.0
        assert isinstance(result, float)

    def test_rollup_with_no_values_returns_none(self, db, sample_organization):
        """Test that rollup returns None when no values available"""
        value_type = ValueType(
            name="Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = []
        result = AggregationService.aggregate_values(values, "sum", value_type)

        assert result is None


class TestRollupQualitativeValues:
    """Test rollup with qualitative value types"""

    def test_qualitative_sum_uses_avg(self, db, sample_organization):
        """Test that sum for qualitative values uses average"""
        value_type = ValueType(
            name="Risk Level", kind="risk", organization_id=sample_organization.id  # risk is qualitative
        )
        db.session.add(value_type)
        db.session.commit()

        # Risk levels: 1=low, 2=medium, 3=high
        values = [1, 2, 3, 2, 1]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        # Should use average, not sum - qualitative values round to nearest int
        assert result == 2  # (1+2+3+2+1)/5 = 1.8 → rounds to 2
        assert isinstance(result, int)

    def test_qualitative_avg_rounds(self, db, sample_organization):
        """Test that average for qualitative values rounds to nearest level"""
        value_type = ValueType(
            name="Sentiment", kind="sentiment", organization_id=sample_organization.id  # qualitative
        )
        db.session.add(value_type)
        db.session.commit()

        values = [1, 2, 3]
        result = AggregationService.aggregate_values(values, "avg", value_type)

        # Should round to nearest integer for qualitative
        assert result == 2
        assert isinstance(result, int)


class TestRollupEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zero_values_in_aggregation(self, db, sample_organization):
        """Test that zero values are handled correctly"""
        value_type = ValueType(
            name="Cost", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("0"), 0, 0.0, Decimal("100")]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        assert result == 100.0

    def test_negative_values_in_aggregation(self, db, sample_organization):
        """Test that negative values are handled correctly"""
        value_type = ValueType(
            name="Profit", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("-100"), 50, Decimal("-25"), 75.0]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        assert result == 0.0

    def test_very_large_values(self, db, sample_organization):
        """Test handling of very large numbers"""
        value_type = ValueType(
            name="Large Value", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("1000000000"), 2000000000.0, Decimal("3000000000")]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        assert result == 6000000000.0
        assert isinstance(result, float)

    def test_very_small_decimal_values(self, db, sample_organization):
        """Test handling of very small decimal values"""
        value_type = ValueType(
            name="Small Value", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [Decimal("0.001"), Decimal("0.002"), Decimal("0.003")]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        assert abs(result - 0.006) < 0.0001  # Allow small floating point error
        assert isinstance(result, float)
