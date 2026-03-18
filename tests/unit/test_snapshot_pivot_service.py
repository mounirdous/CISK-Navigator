"""
Unit tests for SnapshotPivotService
"""

import uuid
from datetime import date

from app.models import (
    KPI,
    Challenge,
    ChallengeInitiativeLink,
    Initiative,
    InitiativeSystemLink,
    KPISnapshot,
    KPIValueTypeConfig,
    Space,
    System,
    ValueType,
)
from app.services.snapshot_pivot_service import SnapshotPivotService


class TestSnapshotPivotService:
    """Tests for SnapshotPivotService"""

    def test_get_available_years(self, db, sample_organization, sample_user):
        """Test getting available years from snapshots"""
        # Create structure
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

        # Create snapshots in different years
        snapshot1 = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2025, 1, 15),
            year=2025,
            quarter=1,
            month=1,
            consensus_value=100,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        snapshot2 = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2026, 6, 20),
            year=2026,
            quarter=2,
            month=6,
            consensus_value=200,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        db.session.add_all([snapshot1, snapshot2])
        db.session.commit()

        years = SnapshotPivotService.get_available_years(sample_organization.id)

        assert 2026 in years
        assert 2025 in years
        assert years[0] > years[-1]  # Descending order

    def test_get_pivot_data_weekly_view(self, db, sample_organization, sample_user):
        """Test weekly pivot view groups snapshots by ISO week"""
        # Create structure
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

        kpi = KPI(name="Test KPI", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Count", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.flush()

        # Create snapshots in different weeks of March 2026
        # Week 11: March 9-15 (Monday to Sunday)
        snapshot_week11_mon = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2026, 3, 9),
            year=2026,
            quarter=1,
            month=3,
            consensus_value=100,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        snapshot_week11_fri = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2026, 3, 13),
            year=2026,
            quarter=1,
            month=3,
            consensus_value=150,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        # Week 12: March 16-22
        snapshot_week12 = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2026, 3, 18),
            year=2026,
            quarter=1,
            month=3,
            consensus_value=200,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        db.session.add_all([snapshot_week11_mon, snapshot_week11_fri, snapshot_week12])
        db.session.commit()

        # Get weekly pivot data
        pivot_data = SnapshotPivotService.get_pivot_data(
            organization_id=sample_organization.id, year_start=2026, year_end=2026, view_type="weekly"
        )

        # Verify periods
        assert "Week 11 2026" in pivot_data["periods"]
        assert "Week 12 2026" in pivot_data["periods"]

        # Verify KPI data
        assert len(pivot_data["kpis"]) == 1
        kpi_data = pivot_data["kpis"][0]
        assert kpi_data["kpi_name"] == "Test KPI"

        # Week 11 should have the most recent snapshot (Friday, value=150)
        assert "Week 11 2026" in kpi_data["values"]
        assert kpi_data["values"]["Week 11 2026"]["value"] == 150

        # Week 12 should have value=200
        assert "Week 12 2026" in kpi_data["values"]
        assert kpi_data["values"]["Week 12 2026"]["value"] == 200

    def test_get_pivot_data_quarterly_view(self, db, sample_organization, sample_user):
        """Test quarterly pivot view"""
        # Create structure
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

        kpi = KPI(name="Revenue", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="USD", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.flush()

        # Create snapshots in Q1 and Q2
        snapshot_q1 = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2026, 3, 15),
            year=2026,
            quarter=1,
            month=3,
            consensus_value=10000,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        snapshot_q2 = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2026, 6, 15),
            year=2026,
            quarter=2,
            month=6,
            consensus_value=15000,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        db.session.add_all([snapshot_q1, snapshot_q2])
        db.session.commit()

        # Get quarterly pivot data
        pivot_data = SnapshotPivotService.get_pivot_data(
            organization_id=sample_organization.id, year_start=2026, year_end=2026, view_type="quarterly"
        )

        # Verify periods
        assert "Q1 2026" in pivot_data["periods"]
        assert "Q2 2026" in pivot_data["periods"]

        # Verify values
        kpi_data = pivot_data["kpis"][0]
        assert kpi_data["values"]["Q1 2026"]["value"] == 10000
        assert kpi_data["values"]["Q2 2026"]["value"] == 15000

    def test_get_pivot_data_monthly_view(self, db, sample_organization, sample_user):
        """Test monthly pivot view"""
        # Create structure
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

        kpi = KPI(name="Sales", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Units", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.flush()

        # Create snapshots in January and February
        snapshot_jan = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2026, 1, 15),
            year=2026,
            quarter=1,
            month=1,
            consensus_value=500,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        snapshot_feb = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2026, 2, 15),
            year=2026,
            quarter=1,
            month=2,
            consensus_value=600,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        db.session.add_all([snapshot_jan, snapshot_feb])
        db.session.commit()

        # Get monthly pivot data
        pivot_data = SnapshotPivotService.get_pivot_data(
            organization_id=sample_organization.id, year_start=2026, year_end=2026, view_type="monthly"
        )

        # Verify periods
        assert "January 2026" in pivot_data["periods"]
        assert "February 2026" in pivot_data["periods"]

        # Verify values
        kpi_data = pivot_data["kpis"][0]
        assert kpi_data["values"]["January 2026"]["value"] == 500
        assert kpi_data["values"]["February 2026"]["value"] == 600

    def test_get_pivot_data_daily_view(self, db, sample_organization, sample_user):
        """Test daily pivot view"""
        # Create structure
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

        kpi = KPI(name="Traffic", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Visitors", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.flush()

        # Create snapshots on specific dates
        snapshot_day1 = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2026, 3, 10),
            year=2026,
            quarter=1,
            month=3,
            consensus_value=1000,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        snapshot_day2 = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2026, 3, 11),
            year=2026,
            quarter=1,
            month=3,
            consensus_value=1200,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        db.session.add_all([snapshot_day1, snapshot_day2])
        db.session.commit()

        # Get daily pivot data
        pivot_data = SnapshotPivotService.get_pivot_data(
            organization_id=sample_organization.id, year_start=2026, year_end=2026, view_type="daily"
        )

        # Verify periods
        assert "2026-03-10" in pivot_data["periods"]
        assert "2026-03-11" in pivot_data["periods"]

        # Verify values
        kpi_data = pivot_data["kpis"][0]
        assert kpi_data["values"]["2026-03-10"]["value"] == 1000
        assert kpi_data["values"]["2026-03-11"]["value"] == 1200

    def test_get_pivot_data_yearly_view(self, db, sample_organization, sample_user):
        """Test yearly pivot view"""
        # Create structure
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

        kpi = KPI(name="Annual Revenue", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="USD", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.flush()

        # Create snapshots in 2025 and 2026
        snapshot_2025 = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2025, 12, 31),
            year=2025,
            quarter=4,
            month=12,
            consensus_value=100000,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        snapshot_2026 = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2026, 12, 31),
            year=2026,
            quarter=4,
            month=12,
            consensus_value=120000,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        db.session.add_all([snapshot_2025, snapshot_2026])
        db.session.commit()

        # Get yearly pivot data
        pivot_data = SnapshotPivotService.get_pivot_data(
            organization_id=sample_organization.id, year_start=2025, year_end=2026, view_type="yearly"
        )

        # Verify periods
        assert "2025" in pivot_data["periods"]
        assert "2026" in pivot_data["periods"]

        # Verify values
        kpi_data = pivot_data["kpis"][0]
        assert kpi_data["values"]["2025"]["value"] == 100000
        assert kpi_data["values"]["2026"]["value"] == 120000

    def test_weekly_view_iso_week_boundary(self, db, sample_organization, sample_user):
        """Test weekly view handles ISO week boundaries correctly"""
        # Create structure
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

        kpi = KPI(name="Test", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Value", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.flush()

        # December 29, 2025 is Monday of Week 1 of 2026 in ISO calendar
        # This tests year boundary edge case
        snapshot_week1_2026 = KPISnapshot(
            kpi_value_type_config_id=config.id,
            snapshot_date=date(2025, 12, 29),
            year=2025,
            quarter=4,
            month=12,
            consensus_value=999,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        db.session.add(snapshot_week1_2026)
        db.session.commit()

        # Get weekly pivot data for 2025
        pivot_data = SnapshotPivotService.get_pivot_data(
            organization_id=sample_organization.id, year_start=2025, year_end=2025, view_type="weekly"
        )

        # The snapshot should appear as Week 1 2026 (ISO calendar)
        # because Dec 29, 2025 is in ISO week 1 of 2026
        assert "Week 1 2026" in pivot_data["periods"]

    def test_pivot_data_space_filter(self, db, sample_organization, sample_user):
        """Test pivot data filtering by space"""
        # Create two spaces
        space1 = Space(name="Space 1", organization_id=sample_organization.id, display_order=1)
        space2 = Space(name="Space 2", organization_id=sample_organization.id, display_order=2)
        db.session.add_all([space1, space2])
        db.session.flush()

        # Create challenges in each space
        challenge1 = Challenge(
            name="Challenge 1", organization_id=sample_organization.id, space_id=space1.id, display_order=1
        )
        challenge2 = Challenge(
            name="Challenge 2", organization_id=sample_organization.id, space_id=space2.id, display_order=1
        )
        db.session.add_all([challenge1, challenge2])
        db.session.flush()

        # Create initiatives and link to challenges
        initiative1 = Initiative(name="Initiative 1", organization_id=sample_organization.id)
        initiative2 = Initiative(name="Initiative 2", organization_id=sample_organization.id)
        system = System(name="System", organization_id=sample_organization.id)
        db.session.add_all([initiative1, initiative2, system])
        db.session.flush()

        link1 = InitiativeSystemLink(initiative_id=initiative1.id, system_id=system.id, display_order=1)
        link2 = InitiativeSystemLink(initiative_id=initiative2.id, system_id=system.id, display_order=2)
        db.session.add_all([link1, link2])
        db.session.flush()

        ch_init_link1 = ChallengeInitiativeLink(
            challenge_id=challenge1.id, initiative_id=initiative1.id, display_order=1
        )
        ch_init_link2 = ChallengeInitiativeLink(
            challenge_id=challenge2.id, initiative_id=initiative2.id, display_order=1
        )
        db.session.add_all([ch_init_link1, ch_init_link2])
        db.session.flush()

        # Create KPIs
        kpi1 = KPI(name="KPI 1", initiative_system_link_id=link1.id)
        kpi2 = KPI(name="KPI 2", initiative_system_link_id=link2.id)
        db.session.add_all([kpi1, kpi2])
        db.session.flush()

        value_type = ValueType(name="Value", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config1 = KPIValueTypeConfig(kpi_id=kpi1.id, value_type_id=value_type.id)
        config2 = KPIValueTypeConfig(kpi_id=kpi2.id, value_type_id=value_type.id)
        db.session.add_all([config1, config2])
        db.session.flush()

        # Create snapshots
        snapshot1 = KPISnapshot(
            kpi_value_type_config_id=config1.id,
            snapshot_date=date(2026, 3, 15),
            year=2026,
            quarter=1,
            month=3,
            consensus_value=100,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        snapshot2 = KPISnapshot(
            kpi_value_type_config_id=config2.id,
            snapshot_date=date(2026, 3, 15),
            year=2026,
            quarter=1,
            month=3,
            consensus_value=200,
            consensus_status="strong",
            contributor_count=1,
            owner_user_id=sample_user.id,
            snapshot_batch_id=str(uuid.uuid4()),
        )
        db.session.add_all([snapshot1, snapshot2])
        db.session.commit()

        # Get pivot data filtered by space 1
        pivot_data = SnapshotPivotService.get_pivot_data(
            organization_id=sample_organization.id,
            year_start=2026,
            year_end=2026,
            view_type="quarterly",
            space_id=space1.id,
        )

        # Should only have KPI 1
        assert len(pivot_data["kpis"]) == 1
        assert pivot_data["kpis"][0]["kpi_name"] == "KPI 1"
