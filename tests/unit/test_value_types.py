"""
Unit tests for ValueType model and related functionality
"""

import pytest

from app.models import ValueType


class TestValueTypeModel:
    """Tests for ValueType model"""

    def test_create_numeric_value_type(self, db, sample_organization):
        """Test creating numeric value type"""
        vt = ValueType(
            name="Cost (USD)",
            kind="numeric",
            numeric_format="decimal",
            decimal_places=2,
            unit_label="USD",
            organization_id=sample_organization.id,
            is_active=True,
        )
        db.session.add(vt)
        db.session.commit()

        assert vt.id is not None
        assert vt.name == "Cost (USD)"
        assert vt.kind == "numeric"
        assert vt.numeric_format == "decimal"
        assert vt.decimal_places == 2
        assert vt.unit_label == "USD"

    def test_create_risk_value_type(self, db, sample_organization):
        """Test creating risk (qualitative) value type"""
        vt = ValueType(name="Risk Level", kind="risk", organization_id=sample_organization.id, is_active=True)
        db.session.add(vt)
        db.session.commit()

        assert vt.kind == "risk"
        assert vt.is_qualitative() is True
        assert vt.is_numeric() is False

    def test_create_impact_value_type(self, db, sample_organization):
        """Test creating positive impact value type"""
        vt = ValueType(
            name="Positive Impact", kind="positive_impact", organization_id=sample_organization.id, is_active=True
        )
        db.session.add(vt)
        db.session.commit()

        assert vt.kind == "positive_impact"
        assert vt.is_qualitative() is True

    def test_create_level_value_type(self, db, sample_organization):
        """Test creating level value type"""
        vt = ValueType(name="Maturity Level", kind="level", organization_id=sample_organization.id, is_active=True)
        db.session.add(vt)
        db.session.commit()

        assert vt.kind == "level"
        assert vt.is_qualitative() is True

    def test_create_sentiment_value_type(self, db, sample_organization):
        """Test creating sentiment value type"""
        vt = ValueType(name="Sentiment", kind="sentiment", organization_id=sample_organization.id, is_active=True)
        db.session.add(vt)
        db.session.commit()

        assert vt.kind == "sentiment"
        assert vt.is_qualitative() is True

    def test_is_numeric_check(self, db, sample_organization):
        """Test is_numeric() method"""
        numeric_vt = ValueType(
            name="Count", kind="numeric", numeric_format="integer", organization_id=sample_organization.id
        )
        db.session.add(numeric_vt)
        db.session.commit()

        assert numeric_vt.is_numeric() is True
        assert numeric_vt.is_qualitative() is False

    def test_is_qualitative_check(self, db, sample_organization):
        """Test is_qualitative() method for all qualitative kinds"""
        qualitative_kinds = ["risk", "positive_impact", "negative_impact", "level", "sentiment"]

        for kind in qualitative_kinds:
            vt = ValueType(name=f"Test {kind}", kind=kind, organization_id=sample_organization.id)
            db.session.add(vt)
            db.session.flush()

            assert vt.is_qualitative() is True
            assert vt.is_numeric() is False

        db.session.commit()

    def test_default_aggregation_formula(self, db, sample_organization):
        """Test default aggregation formula"""
        vt = ValueType(
            name="Revenue", kind="numeric", default_aggregation_formula="sum", organization_id=sample_organization.id
        )
        db.session.add(vt)
        db.session.commit()

        assert vt.default_aggregation_formula == "sum"

    def test_value_type_display_order(self, db, sample_organization):
        """Test display ordering of value types"""
        vt1 = ValueType(name="First", kind="numeric", display_order=1, organization_id=sample_organization.id)
        vt2 = ValueType(name="Second", kind="numeric", display_order=2, organization_id=sample_organization.id)
        db.session.add_all([vt1, vt2])
        db.session.commit()

        # Query in order
        value_types = (
            ValueType.query.filter_by(organization_id=sample_organization.id).order_by(ValueType.display_order).all()
        )

        assert value_types[0].name == "First"
        assert value_types[1].name == "Second"

    def test_inactive_value_type(self, db, sample_organization):
        """Test marking value type as inactive"""
        vt = ValueType(name="Deprecated", kind="numeric", organization_id=sample_organization.id, is_active=False)
        db.session.add(vt)
        db.session.commit()

        assert vt.is_active is False

    def test_integer_numeric_format(self, db, sample_organization):
        """Test integer numeric format"""
        vt = ValueType(
            name="Count",
            kind="numeric",
            numeric_format="integer",
            decimal_places=0,
            organization_id=sample_organization.id,
        )
        db.session.add(vt)
        db.session.commit()

        assert vt.numeric_format == "integer"
        assert vt.decimal_places == 0

    def test_decimal_numeric_format(self, db, sample_organization):
        """Test decimal numeric format with places"""
        vt = ValueType(
            name="Percentage",
            kind="numeric",
            numeric_format="decimal",
            decimal_places=1,
            organization_id=sample_organization.id,
        )
        db.session.add(vt)
        db.session.commit()

        assert vt.numeric_format == "decimal"
        assert vt.decimal_places == 1

    def test_value_type_with_unit_label(self, db, sample_organization):
        """Test value type with unit label"""
        vt = ValueType(
            name="CO2 Emissions",
            kind="numeric",
            numeric_format="decimal",
            decimal_places=2,
            unit_label="tons",
            organization_id=sample_organization.id,
        )
        db.session.add(vt)
        db.session.commit()

        assert vt.unit_label == "tons"

    def test_value_type_belongs_to_organization(self, db, sample_organization):
        """Test value type is scoped to organization"""
        vt = ValueType(name="Org-specific", kind="numeric", organization_id=sample_organization.id)
        db.session.add(vt)
        db.session.commit()

        assert vt.organization_id == sample_organization.id
        assert vt.organization == sample_organization
