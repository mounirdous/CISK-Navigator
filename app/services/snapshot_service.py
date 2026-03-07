"""
Snapshot Service

Creates and retrieves historical snapshots of KPI values for time-series tracking.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Optional
from app.extensions import db
from app.models import (
    KPISnapshot, RollupSnapshot, KPIValueTypeConfig, KPI, Space, Challenge,
    Initiative, InitiativeSystemLink, ValueType
)
from app.services.consensus_service import ConsensusService
from app.services.aggregation_service import AggregationService


class SnapshotService:
    """Service for managing KPI snapshots and historical tracking"""

    @staticmethod
    def create_kpi_snapshot(config_id: int, snapshot_date: date = None,
                           label: str = None, notes: str = None,
                           user_id: int = None) -> Optional[KPISnapshot]:
        """
        Create a snapshot of the current KPI consensus value.

        Args:
            config_id: KPIValueTypeConfig ID
            snapshot_date: Date of snapshot (default: today)
            label: Optional label like "Q1 2026" or "Baseline"
            notes: Optional notes about this snapshot
            user_id: User creating the snapshot

        Returns:
            KPISnapshot object or None if no consensus
        """
        config = KPIValueTypeConfig.query.get(config_id)
        if not config:
            return None

        # Get current consensus
        consensus = ConsensusService.get_cell_value(config)

        if not consensus or consensus.get('status') == 'no_data':
            return None

        # Check if snapshot already exists for this date
        if snapshot_date is None:
            snapshot_date = date.today()

        existing = KPISnapshot.query.filter_by(
            kpi_value_type_config_id=config_id,
            snapshot_date=snapshot_date
        ).first()

        if existing:
            # Update existing snapshot
            existing.consensus_status = consensus['status']
            existing.consensus_value = consensus.get('value') if config.value_type.is_numeric() else None
            existing.qualitative_level = consensus.get('value') if not config.value_type.is_numeric() else None
            existing.contributor_count = consensus.get('count', 0)
            existing.is_rollup_eligible = consensus.get('is_rollup_eligible', False)
            existing.snapshot_label = label or existing.snapshot_label
            existing.notes = notes or existing.notes
            existing.created_at = datetime.utcnow()
            db.session.commit()
            return existing

        # Create new snapshot
        snapshot = KPISnapshot(
            kpi_value_type_config_id=config_id,
            snapshot_date=snapshot_date,
            snapshot_label=label,
            consensus_status=consensus['status'],
            consensus_value=consensus.get('value') if config.value_type.is_numeric() else None,
            qualitative_level=consensus.get('value') if not config.value_type.is_numeric() else None,
            contributor_count=consensus.get('count', 0),
            is_rollup_eligible=consensus.get('is_rollup_eligible', False),
            notes=notes,
            created_by_user_id=user_id
        )

        db.session.add(snapshot)
        db.session.commit()
        return snapshot

    @staticmethod
    def create_organization_snapshot(organization_id: int, snapshot_date: date = None,
                                    label: str = None, user_id: int = None) -> Dict:
        """
        Create snapshots for all KPIs in an organization.

        Args:
            organization_id: Organization ID
            snapshot_date: Date of snapshot (default: today)
            label: Label for this snapshot
            user_id: User creating snapshots

        Returns:
            Dict with counts of created snapshots
        """
        if snapshot_date is None:
            snapshot_date = date.today()

        # Get all KPI configs for this organization
        configs = db.session.query(KPIValueTypeConfig).join(
            KPI, KPIValueTypeConfig.kpi_id == KPI.id
        ).join(
            InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id
        ).join(
            Initiative, InitiativeSystemLink.initiative_id == Initiative.id
        ).filter(
            Initiative.organization_id == organization_id
        ).all()

        created_count = 0
        skipped_count = 0

        for config in configs:
            snapshot = SnapshotService.create_kpi_snapshot(
                config.id,
                snapshot_date=snapshot_date,
                label=label,
                user_id=user_id
            )
            if snapshot:
                created_count += 1
            else:
                skipped_count += 1

        # Also create rollup snapshots
        rollup_count = SnapshotService.create_rollup_snapshots(
            organization_id, snapshot_date, label
        )

        return {
            'kpi_snapshots': created_count,
            'skipped': skipped_count,
            'rollup_snapshots': rollup_count,
            'snapshot_date': snapshot_date.isoformat(),
            'label': label
        }

    @staticmethod
    def create_rollup_snapshots(organization_id: int, snapshot_date: date,
                               label: str = None) -> int:
        """
        Create rollup snapshots for all hierarchy levels.

        Returns:
            Count of created rollup snapshots
        """
        count = 0

        # Get all value types for this organization
        value_types = ValueType.query.filter_by(
            organization_id=organization_id,
            is_active=True
        ).all()

        # Snapshot all spaces
        spaces = Space.query.filter_by(organization_id=organization_id).all()
        for space in spaces:
            for vt in value_types:
                rollup = space.get_rollup_value(vt.id)
                if rollup and rollup['value'] is not None:
                    snapshot = SnapshotService._create_rollup_snapshot(
                        'space', space.id, vt.id, rollup, snapshot_date, label
                    )
                    if snapshot:
                        count += 1

        # Snapshot all challenges
        challenges = Challenge.query.join(Space).filter(
            Space.organization_id == organization_id
        ).all()
        for challenge in challenges:
            for vt in value_types:
                rollup = challenge.get_rollup_value(vt.id)
                if rollup and rollup['value'] is not None:
                    snapshot = SnapshotService._create_rollup_snapshot(
                        'challenge', challenge.id, vt.id, rollup, snapshot_date, label
                    )
                    if snapshot:
                        count += 1

        # Snapshot all initiatives
        initiatives = Initiative.query.filter_by(organization_id=organization_id).all()
        for initiative in initiatives:
            for vt in value_types:
                rollup = initiative.get_rollup_value(vt.id)
                if rollup and rollup['value'] is not None:
                    snapshot = SnapshotService._create_rollup_snapshot(
                        'initiative', initiative.id, vt.id, rollup, snapshot_date, label
                    )
                    if snapshot:
                        count += 1

        # Snapshot all systems (via initiative-system links)
        sys_links = db.session.query(InitiativeSystemLink).join(
            Initiative
        ).filter(
            Initiative.organization_id == organization_id
        ).all()
        for link in sys_links:
            for vt in value_types:
                rollup = link.get_rollup_value(vt.id)
                if rollup and rollup['value'] is not None:
                    snapshot = SnapshotService._create_rollup_snapshot(
                        'system', link.id, vt.id, rollup, snapshot_date, label
                    )
                    if snapshot:
                        count += 1

        return count

    @staticmethod
    def _create_rollup_snapshot(entity_type: str, entity_id: int, value_type_id: int,
                               rollup: Dict, snapshot_date: date, label: str = None) -> Optional[RollupSnapshot]:
        """Create a single rollup snapshot"""
        # Check if exists
        existing = RollupSnapshot.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id,
            value_type_id=value_type_id,
            snapshot_date=snapshot_date
        ).first()

        value_type = ValueType.query.get(value_type_id)

        if existing:
            # Update
            existing.rollup_value = rollup['value'] if value_type.is_numeric() else None
            existing.qualitative_level = rollup['value'] if not value_type.is_numeric() else None
            existing.is_complete = rollup.get('is_complete', False)
            existing.snapshot_label = label or existing.snapshot_label
            existing.created_at = datetime.utcnow()
            db.session.commit()
            return existing

        # Create new
        snapshot = RollupSnapshot(
            entity_type=entity_type,
            entity_id=entity_id,
            value_type_id=value_type_id,
            snapshot_date=snapshot_date,
            snapshot_label=label,
            rollup_value=rollup['value'] if value_type.is_numeric() else None,
            qualitative_level=rollup['value'] if not value_type.is_numeric() else None,
            is_complete=rollup.get('is_complete', False)
        )

        db.session.add(snapshot)
        db.session.commit()
        return snapshot

    @staticmethod
    def get_kpi_history(config_id: int, limit: int = None) -> List[KPISnapshot]:
        """
        Get historical snapshots for a KPI.

        Args:
            config_id: KPIValueTypeConfig ID
            limit: Optional limit on number of snapshots

        Returns:
            List of KPISnapshot objects, ordered by date descending
        """
        query = KPISnapshot.query.filter_by(
            kpi_value_type_config_id=config_id
        ).order_by(KPISnapshot.snapshot_date.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def get_rollup_history(entity_type: str, entity_id: int,
                          value_type_id: int, limit: int = None) -> List[RollupSnapshot]:
        """Get historical rollup snapshots"""
        query = RollupSnapshot.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id,
            value_type_id=value_type_id
        ).order_by(RollupSnapshot.snapshot_date.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def calculate_trend(config_id: int, periods: int = 2) -> Optional[Dict]:
        """
        Calculate trend direction for a KPI.

        Args:
            config_id: KPIValueTypeConfig ID
            periods: Number of periods to analyze (default: 2 for simple up/down)

        Returns:
            Dict with trend info: {'direction': 'up'|'down'|'stable', 'change': value, 'percent_change': percent}
        """
        snapshots = SnapshotService.get_kpi_history(config_id, limit=periods)

        if len(snapshots) < 2:
            return None

        latest = snapshots[0]
        previous = snapshots[1]

        latest_value = latest.get_value()
        previous_value = previous.get_value()

        if latest_value is None or previous_value is None:
            return None

        change = latest_value - previous_value
        percent_change = (change / previous_value * 100) if previous_value != 0 else 0

        # Determine direction
        if abs(change) < 0.01:  # Threshold for "stable"
            direction = 'stable'
        elif change > 0:
            direction = 'up'
        else:
            direction = 'down'

        return {
            'direction': direction,
            'change': float(change),
            'percent_change': float(percent_change),
            'latest_value': float(latest_value),
            'previous_value': float(previous_value),
            'latest_date': latest.snapshot_date.isoformat(),
            'previous_date': previous.snapshot_date.isoformat()
        }

    @staticmethod
    def get_available_snapshot_dates(organization_id: int, limit: int = None) -> List[date]:
        """
        Get all unique snapshot dates for an organization.

        Args:
            organization_id: Organization ID
            limit: Optional limit on number of dates to return

        Returns:
            List of dates, ordered descending (most recent first)
        """
        # Query distinct snapshot dates from both tables
        kpi_dates = db.session.query(KPISnapshot.snapshot_date).distinct().join(
            KPIValueTypeConfig, KPISnapshot.kpi_value_type_config_id == KPIValueTypeConfig.id
        ).join(
            KPI, KPIValueTypeConfig.kpi_id == KPI.id
        ).join(
            InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id
        ).join(
            Initiative, InitiativeSystemLink.initiative_id == Initiative.id
        ).filter(
            Initiative.organization_id == organization_id
        )

        rollup_dates = db.session.query(RollupSnapshot.snapshot_date).distinct().join(
            ValueType
        ).filter(
            ValueType.organization_id == organization_id
        )

        # Combine and deduplicate
        all_dates = set([d[0] for d in kpi_dates.all()] + [d[0] for d in rollup_dates.all()])

        # Sort descending and apply limit if provided
        sorted_dates = sorted(list(all_dates), reverse=True)
        return sorted_dates[:limit] if limit else sorted_dates
