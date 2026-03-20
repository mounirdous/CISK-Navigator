"""
Unit tests for OrganizationCloneService
"""

import pytest

from app.models import (
    Challenge,
    Initiative,
    Organization,
    Space,
    System,
    ValueType,
)
from app.services.organization_clone_service import OrganizationCloneService


@pytest.fixture
def source_org(db):
    """Create a source organization with full structure for cloning."""
    org = Organization(name="Source Org", description="Original org", is_active=True)
    db.session.add(org)
    db.session.flush()

    # Value Types
    vt1 = ValueType(
        organization_id=org.id,
        name="Revenue",
        kind="numeric",
        numeric_format="currency",
        decimal_places=2,
        unit_label="USD",
        default_aggregation_formula="sum",
        calculation_type=None,
        calculation_config=None,
        is_active=True,
    )
    vt2 = ValueType(
        organization_id=org.id,
        name="Growth Rate",
        kind="numeric",
        numeric_format="percent",
        decimal_places=1,
        unit_label="%",
        default_aggregation_formula="avg",
        calculation_type="formula",
        calculation_config={"formula": "a/b*100"},
        is_active=True,
    )
    db.session.add_all([vt1, vt2])
    db.session.flush()

    # Space
    space = Space(
        organization_id=org.id,
        name="Strategy",
        description="Strategic space",
        space_label="SP",
        display_order=1,
    )
    db.session.add(space)
    db.session.flush()

    # Challenge
    challenge = Challenge(
        organization_id=org.id,
        space_id=space.id,
        name="Growth Challenge",
        description="Grow revenue",
        display_order=1,
    )
    db.session.add(challenge)
    db.session.flush()

    # Initiative
    initiative = Initiative(
        organization_id=org.id,
        name="Market Expansion",
        description="Expand to new markets",
    )
    db.session.add(initiative)
    db.session.flush()

    # System
    system = System(
        organization_id=org.id,
        name="Sales System",
        description="Sales tracking",
    )
    db.session.add(system)
    db.session.flush()

    db.session.commit()
    return org


class TestOrganizationCloneService:

    def test_clone_creates_new_organization(self, db, source_org):
        result = OrganizationCloneService.clone_organization(source_org.id, "Cloned Org")

        assert result["success"] is True
        assert result["new_organization_name"] == "Cloned Org"
        new_org = Organization.query.get(result["new_organization_id"])
        assert new_org is not None
        assert new_org.name == "Cloned Org"

    def test_clone_copies_value_types(self, db, source_org):
        result = OrganizationCloneService.clone_organization(source_org.id, "Cloned Org")

        assert result["success"] is True
        assert result["statistics"]["value_types"] == 2

        new_org = Organization.query.get(result["new_organization_id"])
        cloned_vts = {vt.name: vt for vt in new_org.value_types}

        assert "Revenue" in cloned_vts
        assert "Growth Rate" in cloned_vts

        revenue = cloned_vts["Revenue"]
        assert revenue.kind == "numeric"
        assert revenue.numeric_format == "currency"
        assert revenue.decimal_places == 2
        assert revenue.unit_label == "USD"
        assert revenue.calculation_type is None
        assert revenue.calculation_config is None

        growth = cloned_vts["Growth Rate"]
        assert growth.calculation_type == "formula"
        assert growth.calculation_config == {"formula": "a/b*100"}

    def test_clone_value_types_belong_to_new_org(self, db, source_org):
        result = OrganizationCloneService.clone_organization(source_org.id, "Cloned Org")

        new_org = Organization.query.get(result["new_organization_id"])
        for vt in new_org.value_types:
            assert vt.organization_id == new_org.id

    def test_clone_copies_spaces(self, db, source_org):
        result = OrganizationCloneService.clone_organization(source_org.id, "Cloned Org")

        assert result["statistics"]["spaces"] == 1
        new_org = Organization.query.get(result["new_organization_id"])
        assert len(new_org.spaces) == 1
        assert new_org.spaces[0].name == "Strategy"

    def test_clone_copies_challenges(self, db, source_org):
        result = OrganizationCloneService.clone_organization(source_org.id, "Cloned Org")

        assert result["statistics"]["challenges"] == 1
        new_org = Organization.query.get(result["new_organization_id"])
        assert len(new_org.challenges) == 1
        assert new_org.challenges[0].name == "Growth Challenge"

    def test_clone_copies_initiatives(self, db, source_org):
        result = OrganizationCloneService.clone_organization(source_org.id, "Cloned Org")

        assert result["statistics"]["initiatives"] == 1
        new_org = Organization.query.get(result["new_organization_id"])
        assert len(new_org.initiatives) == 1
        assert new_org.initiatives[0].name == "Market Expansion"

    def test_clone_copies_systems(self, db, source_org):
        result = OrganizationCloneService.clone_organization(source_org.id, "Cloned Org")

        assert result["statistics"]["systems"] == 1
        new_org = Organization.query.get(result["new_organization_id"])
        assert len(new_org.systems) == 1
        assert new_org.systems[0].name == "Sales System"

    def test_clone_does_not_share_ids_with_source(self, db, source_org):
        result = OrganizationCloneService.clone_organization(source_org.id, "Cloned Org")

        new_org = Organization.query.get(result["new_organization_id"])
        source_vt_ids = {vt.id for vt in source_org.value_types}
        cloned_vt_ids = {vt.id for vt in new_org.value_types}
        assert source_vt_ids.isdisjoint(cloned_vt_ids)

    def test_clone_source_not_found(self, db):
        result = OrganizationCloneService.clone_organization(99999, "Ghost Clone")

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_clone_default_description(self, db, source_org):
        result = OrganizationCloneService.clone_organization(source_org.id, "New Org")

        new_org = Organization.query.get(result["new_organization_id"])
        assert "Clone of" in new_org.description
        assert source_org.name in new_org.description

    def test_clone_custom_description(self, db, source_org):
        result = OrganizationCloneService.clone_organization(source_org.id, "New Org", "Custom desc")

        new_org = Organization.query.get(result["new_organization_id"])
        assert new_org.description == "Custom desc"
