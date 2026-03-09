"""
Unit tests for SnapshotService
"""

from datetime import date, timedelta

import pytest

from app.models import (
    KPI,
    Challenge,
    Contribution,
    Initiative,
    InitiativeSystemLink,
    KPISnapshot,
    KPIValueTypeConfig,
    Space,
    System,
    ValueType,
)
from app.services.snapshot_service import SnapshotService


class TestSnapshotService:
    """Tests for SnapshotService"""

    def test_create_snapshot_with_no_data(self, db, sample_organization):
        """Test creating snapshot with no contributions returns None"""
        # Create minimal KPI structure
        space = Space(name="Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            name="Challenge", organization_id=sample_organization.id, space_id=space.id, display_order=1
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(name="Initiative", organization_id=sample_organization.id)
        system = System(name="System", organization_id=sample_organization.id)
        db.session.add_all([initiative, system])
        db.session.flush()

        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
        db.session.add(link)
        db.session.flush()

        kpi = KPI(name="KPI", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Value", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.commit()

        # Try to create snapshot with no contributions
        snapshot = SnapshotService.create_kpi_snapshot(config.id)

        assert snapshot is None

    def test_create_snapshot_with_single_contribution(self, db, sample_organization, sample_user):
        """Test creating snapshot with one contribution"""
        # Create full structure
        space = Space(name="Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            name="Challenge", organization_id=sample_organization.id, space_id=space.id, display_order=1
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(name="Initiative", organization_id=sample_organization.id)
        system = System(name="System", organization_id=sample_organization.id)
        db.session.add_all([initiative, system])
        db.session.flush()

        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
        db.session.add(link)
        db.session.flush()

        kpi = KPI(name="KPI", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Value", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.flush()

        # Add contribution (using contributor_name, not user_id)
        contribution = Contribution(
            kpi_value_type_config_id=config.id, contributor_name="TestUser", numeric_value=100.0
        )
        db.session.add(contribution)
        db.session.commit()

        # Create snapshot
        snapshot = SnapshotService.create_kpi_snapshot(config.id, label="Test Snapshot", user_id=sample_user.id)

        assert snapshot is not None
        assert float(snapshot.consensus_value) == 100.0
        assert snapshot.consensus_status == "strong"
        assert snapshot.contributor_count == 1
        assert snapshot.snapshot_label == "Test Snapshot"
        assert snapshot.owner_user_id == sample_user.id

    def test_create_snapshot_updates_existing_for_same_date(self, db, sample_organization, sample_user):
        """Test creating snapshot on same date updates existing one"""
        # Setup
        space = Space(name="Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            name="Challenge", organization_id=sample_organization.id, space_id=space.id, display_order=1
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(name="Initiative", organization_id=sample_organization.id)
        system = System(name="System", organization_id=sample_organization.id)
        db.session.add_all([initiative, system])
        db.session.flush()

        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
        db.session.add(link)
        db.session.flush()

        kpi = KPI(name="KPI", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Value", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.flush()

        contribution = Contribution(
            kpi_value_type_config_id=config.id, contributor_name="TestUser", numeric_value=100.0
        )
        db.session.add(contribution)
        db.session.commit()

        # Create first snapshot
        today = date.today()
        snapshot1 = SnapshotService.create_kpi_snapshot(
            config.id, snapshot_date=today, label="First", user_id=sample_user.id
        )

        # Update contribution value
        contribution.numeric_value = 200.0
        db.session.commit()

        # Create second snapshot for same date
        snapshot2 = SnapshotService.create_kpi_snapshot(
            config.id, snapshot_date=today, label="Second", user_id=sample_user.id
        )

        # Should return same snapshot ID with updated values
        assert snapshot2.id == snapshot1.id
        assert snapshot2.consensus_value == 200.0
        assert snapshot2.snapshot_label == "Second"

    def test_create_snapshot_with_allow_duplicates(self, db, sample_organization, sample_user):
        """Test creating multiple snapshots for same date with allow_duplicates=True"""
        # Setup
        space = Space(name="Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            name="Challenge", organization_id=sample_organization.id, space_id=space.id, display_order=1
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(name="Initiative", organization_id=sample_organization.id)
        system = System(name="System", organization_id=sample_organization.id)
        db.session.add_all([initiative, system])
        db.session.flush()

        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
        db.session.add(link)
        db.session.flush()

        kpi = KPI(name="KPI", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Value", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.flush()

        contribution = Contribution(
            kpi_value_type_config_id=config.id, contributor_name="TestUser", numeric_value=100.0
        )
        db.session.add(contribution)
        db.session.commit()

        today = date.today()

        # Create first snapshot
        snapshot1 = SnapshotService.create_kpi_snapshot(
            config.id, snapshot_date=today, user_id=sample_user.id, allow_duplicates=True
        )

        # Create second snapshot for same date
        snapshot2 = SnapshotService.create_kpi_snapshot(
            config.id, snapshot_date=today, user_id=sample_user.id, allow_duplicates=True
        )

        # Should have different IDs
        assert snapshot1.id != snapshot2.id

    def test_create_snapshot_with_qualitative_value(self, db, sample_organization, sample_user):
        """Test creating snapshot with qualitative (risk) value"""
        # Setup
        space = Space(name="Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            name="Challenge", organization_id=sample_organization.id, space_id=space.id, display_order=1
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(name="Initiative", organization_id=sample_organization.id)
        system = System(name="System", organization_id=sample_organization.id)
        db.session.add_all([initiative, system])
        db.session.flush()

        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
        db.session.add(link)
        db.session.flush()

        kpi = KPI(name="KPI", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        # Create risk value type (qualitative)
        value_type = ValueType(name="Risk", kind="risk", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.flush()

        # Add qualitative contribution
        contribution = Contribution(
            kpi_value_type_config_id=config.id, contributor_name="TestUser", qualitative_level=3
        )
        db.session.add(contribution)
        db.session.commit()

        # Create snapshot
        snapshot = SnapshotService.create_kpi_snapshot(config.id, user_id=sample_user.id)

        assert snapshot is not None
        assert snapshot.qualitative_level == 3
        assert snapshot.consensus_value is None  # Qualitative doesn't use numeric value
        assert snapshot.consensus_status == "strong"

    def test_snapshot_privacy_settings(self, db, sample_organization, sample_user):
        """Test public/private snapshot settings"""
        # Setup
        space = Space(name="Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            name="Challenge", organization_id=sample_organization.id, space_id=space.id, display_order=1
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(name="Initiative", organization_id=sample_organization.id)
        system = System(name="System", organization_id=sample_organization.id)
        db.session.add_all([initiative, system])
        db.session.flush()

        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
        db.session.add(link)
        db.session.flush()

        kpi = KPI(name="KPI", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Value", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.flush()

        contribution = Contribution(
            kpi_value_type_config_id=config.id, contributor_name="TestUser", numeric_value=100.0
        )
        db.session.add(contribution)
        db.session.commit()

        # Create private snapshot (default)
        private_snapshot = SnapshotService.create_kpi_snapshot(config.id, user_id=sample_user.id, is_public=False)

        assert private_snapshot.is_public is False
        assert private_snapshot.owner_user_id == sample_user.id

        # Create public snapshot
        contribution.numeric_value = 200.0
        db.session.commit()

        public_snapshot = SnapshotService.create_kpi_snapshot(
            config.id, snapshot_date=date.today() + timedelta(days=1), user_id=sample_user.id, is_public=True
        )

        assert public_snapshot.is_public is True
