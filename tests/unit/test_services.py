"""
Unit tests for service classes
"""

import pytest

from app.models import ValueType
from app.services.aggregation_service import AggregationService
from app.services.consensus_service import ConsensusService


class MockContribution:
    """Mock contribution for testing"""

    def __init__(self, numeric_value=None, qualitative_level=None):
        self.numeric_value = numeric_value
        self.qualitative_level = qualitative_level


class TestConsensusService:
    """Tests for ConsensusService"""

    def test_no_data_consensus(self):
        """Test consensus with no contributions"""
        result = ConsensusService.calculate_consensus([])

        assert result["status"] == ConsensusService.STATUS_NO_DATA
        assert result["value"] is None
        assert result["count"] == 0
        assert result["is_rollup_eligible"] is False

    def test_single_contribution_numeric(self):
        """Test consensus with single numeric contribution"""
        contributions = [MockContribution(numeric_value=100)]
        result = ConsensusService.calculate_consensus(contributions)

        assert result["status"] == ConsensusService.STATUS_STRONG
        assert result["value"] == 100
        assert result["count"] == 1
        assert result["is_rollup_eligible"] is True

    def test_single_contribution_qualitative(self):
        """Test consensus with single qualitative contribution"""
        contributions = [MockContribution(qualitative_level="high")]
        result = ConsensusService.calculate_consensus(contributions)

        assert result["status"] == ConsensusService.STATUS_STRONG
        assert result["value"] == "high"
        assert result["count"] == 1
        assert result["is_rollup_eligible"] is True

    def test_strong_consensus_numeric(self):
        """Test strong consensus with multiple identical numeric values"""
        contributions = [
            MockContribution(numeric_value=50),
            MockContribution(numeric_value=50),
            MockContribution(numeric_value=50),
        ]
        result = ConsensusService.calculate_consensus(contributions)

        assert result["status"] == ConsensusService.STATUS_STRONG
        assert result["value"] == 50
        assert result["count"] == 3
        assert result["is_rollup_eligible"] is True

    def test_strong_consensus_qualitative(self):
        """Test strong consensus with identical qualitative values"""
        contributions = [MockContribution(qualitative_level="medium"), MockContribution(qualitative_level="medium")]
        result = ConsensusService.calculate_consensus(contributions)

        assert result["status"] == ConsensusService.STATUS_STRONG
        assert result["value"] == "medium"
        assert result["count"] == 2
        assert result["is_rollup_eligible"] is True

    def test_weak_consensus(self):
        """Test weak consensus with majority but not unanimous"""
        contributions = [
            MockContribution(numeric_value=100),
            MockContribution(numeric_value=100),
            MockContribution(numeric_value=100),
            MockContribution(numeric_value=90),  # Outlier
        ]
        result = ConsensusService.calculate_consensus(contributions)

        assert result["status"] == ConsensusService.STATUS_WEAK
        assert result["value"] == 100  # Majority value
        assert result["count"] == 4
        assert result["is_rollup_eligible"] is False

    def test_no_consensus(self):
        """Test no consensus with equal split"""
        contributions = [
            MockContribution(numeric_value=100),
            MockContribution(numeric_value=100),
            MockContribution(numeric_value=200),
            MockContribution(numeric_value=200),
        ]
        result = ConsensusService.calculate_consensus(contributions)

        assert result["status"] == ConsensusService.STATUS_NO_CONSENSUS
        assert result["value"] is None
        assert result["count"] == 4
        assert result["is_rollup_eligible"] is False

    def test_mixed_values_ignored_none(self):
        """Test that None values don't interfere"""
        contributions = [
            MockContribution(numeric_value=50),
            MockContribution(numeric_value=50),
            MockContribution(),  # No value
        ]
        result = ConsensusService.calculate_consensus(contributions)

        # Should still get strong consensus from the two valid values
        assert result["status"] == ConsensusService.STATUS_STRONG
        assert result["value"] == 50
        assert result["count"] == 2


class TestAggregationService:
    """Tests for AggregationService"""

    def test_aggregate_sum_numeric(self, db, sample_organization):
        """Test sum aggregation for numeric values"""
        value_type = ValueType(
            name="Test Numeric", kind="numeric", numeric_format="decimal", organization_id=sample_organization.id
        )
        db.session.add(value_type)
        db.session.commit()

        values = [10, 20, 30]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        assert result == 60

    def test_aggregate_min(self, db, sample_organization):
        """Test min aggregation"""
        value_type = ValueType(name="Test Numeric", kind="numeric", organization_id=sample_organization.id)
        db.session.add(value_type)
        db.session.commit()

        values = [10, 5, 20, 3]
        result = AggregationService.aggregate_values(values, "min", value_type)

        assert result == 3

    def test_aggregate_max(self, db, sample_organization):
        """Test max aggregation"""
        value_type = ValueType(name="Test Numeric", kind="numeric", organization_id=sample_organization.id)
        db.session.add(value_type)
        db.session.commit()

        values = [10, 5, 20, 3]
        result = AggregationService.aggregate_values(values, "max", value_type)

        assert result == 20

    def test_aggregate_avg(self, db, sample_organization):
        """Test average aggregation"""
        value_type = ValueType(name="Test Numeric", kind="numeric", organization_id=sample_organization.id)
        db.session.add(value_type)
        db.session.commit()

        values = [10, 20, 30]
        result = AggregationService.aggregate_values(values, "avg", value_type)

        assert result == 20

    def test_aggregate_median(self, db, sample_organization):
        """Test median aggregation"""
        value_type = ValueType(name="Test Numeric", kind="numeric", organization_id=sample_organization.id)
        db.session.add(value_type)
        db.session.commit()

        values = [10, 20, 30, 40, 50]
        result = AggregationService.aggregate_values(values, "median", value_type)

        assert result == 30

    def test_aggregate_count(self, db, sample_organization):
        """Test count aggregation"""
        value_type = ValueType(name="Test Numeric", kind="numeric", organization_id=sample_organization.id)
        db.session.add(value_type)
        db.session.commit()

        values = [10, 20, 30, 40]
        result = AggregationService.aggregate_values(values, "count", value_type)

        assert result == 4

    def test_aggregate_empty_values(self, db, sample_organization):
        """Test aggregation with no values returns None"""
        value_type = ValueType(name="Test Numeric", kind="numeric", organization_id=sample_organization.id)
        db.session.add(value_type)
        db.session.commit()

        result = AggregationService.aggregate_values([], "sum", value_type)

        assert result is None

    def test_aggregate_qualitative_avg(self, db, sample_organization):
        """Test average aggregation for qualitative values"""
        value_type = ValueType(
            name="Risk Level", kind="risk", organization_id=sample_organization.id  # risk is a qualitative kind
        )
        db.session.add(value_type)
        db.session.commit()

        # Qualitative values are stored as strings like 'low', 'medium', 'high'
        # but can be mapped to numbers for averaging
        values = [1, 2, 3]  # low=1, medium=2, high=3
        result = AggregationService.aggregate_values(values, "avg", value_type)

        assert result == 2  # Average of 1, 2, 3

    def test_aggregate_qualitative_sum_uses_avg(self, db, sample_organization):
        """Test that sum for qualitative values uses average instead"""
        value_type = ValueType(
            name="Sentiment",
            kind="sentiment",  # sentiment is a qualitative kind
            organization_id=sample_organization.id,
        )
        db.session.add(value_type)
        db.session.commit()

        values = [1, 2, 3]
        result = AggregationService.aggregate_values(values, "sum", value_type)

        # Sum doesn't make sense for qualitative, should use avg
        assert result == 2
