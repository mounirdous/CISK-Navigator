"""
Action Items Service

Centralized logic for calculating action items that need attention.
"""

from app.extensions import db
from app.models import KPI, Initiative, InitiativeSystemLink, Space, System


class ActionItemsService:
    """Service for calculating action items across the organization"""

    @staticmethod
    def get_action_items_count(organization_id):
        """
        Calculate total count of action items requiring attention.

        Args:
            organization_id (int): Organization ID

        Returns:
            dict: Action items breakdown
                {
                    "initiatives_no_consensus": int,
                    "initiatives_incomplete": int,
                    "spaces_incomplete": int,
                    "systems_without_kpis": int,
                    "kpis_without_governance": int,
                    "unique_initiatives": int,  # Deduplicated count
                    "total": int  # Total unique items
                }
        """
        # Get initiatives with no consensus
        no_consensus_initiatives = Initiative.query.filter_by(
            organization_id=organization_id, impact_on_challenge="no_consensus"
        ).all()

        # Get initiatives with incomplete forms
        all_initiatives = Initiative.query.filter_by(organization_id=organization_id).all()
        incomplete_initiatives = []
        for initiative in all_initiatives:
            filled, total, status = initiative.get_form_completion()
            if status != "complete":
                incomplete_initiatives.append(initiative)

        # Get spaces without SWOT (empty or partial)
        all_spaces = Space.query.filter_by(organization_id=organization_id).all()
        incomplete_spaces = []
        for space in all_spaces:
            filled, total, status = space.get_swot_completion()
            if status != "complete":
                incomplete_spaces.append(space)

        # Get systems without KPIs
        systems_without_kpis_count = (
            db.session.query(System)
            .join(InitiativeSystemLink, System.id == InitiativeSystemLink.system_id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .outerjoin(KPI, InitiativeSystemLink.id == KPI.initiative_system_link_id)
            .filter(Initiative.organization_id == organization_id, KPI.id.is_(None))
            .distinct()
            .count()
        )

        # Get KPIs without governance bodies
        from app.models import KPIGovernanceBodyLink

        kpis_without_governance_count = (
            db.session.query(KPI)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .outerjoin(KPIGovernanceBodyLink, KPI.id == KPIGovernanceBodyLink.kpi_id)
            .filter(Initiative.organization_id == organization_id, KPIGovernanceBodyLink.id.is_(None))
            .count()
        )

        # Count unique initiatives (avoid double-counting)
        unique_initiative_ids = set()
        for init in no_consensus_initiatives:
            unique_initiative_ids.add(init.id)
        for init in incomplete_initiatives:
            unique_initiative_ids.add(init.id)

        # Calculate total (unique items only)
        total = (
            len(unique_initiative_ids)
            + len(incomplete_spaces)
            + systems_without_kpis_count
            + kpis_without_governance_count
        )

        return {
            "initiatives_no_consensus": len(no_consensus_initiatives),
            "initiatives_incomplete": len(incomplete_initiatives),
            "spaces_incomplete": len(incomplete_spaces),
            "systems_without_kpis": systems_without_kpis_count,
            "kpis_without_governance": kpis_without_governance_count,
            "unique_initiatives": len(unique_initiative_ids),
            "total": total,
        }

    @staticmethod
    def get_action_items_details(organization_id):
        """
        Get detailed action items with full objects for display.

        Args:
            organization_id (int): Organization ID

        Returns:
            dict: Action items with full details
                {
                    "initiatives_no_consensus": [Initiative],
                    "initiatives_incomplete": [{"initiative": Initiative, "filled": int, "total": int, ...}],
                    "spaces_incomplete": [{"space": Space, "filled": int, "total": int, ...}],
                    "systems_without_kpis": [System],
                    "kpis_without_governance": [KPI],
                    "total": int
                }
        """
        # Get initiatives with no consensus
        initiatives_no_consensus = (
            Initiative.query.filter_by(organization_id=organization_id, impact_on_challenge="no_consensus")
            .order_by(Initiative.name)
            .all()
        )

        # Get initiatives with incomplete forms
        all_initiatives = Initiative.query.filter_by(organization_id=organization_id).order_by(Initiative.name).all()
        initiatives_incomplete = []
        for initiative in all_initiatives:
            filled, total, status = initiative.get_form_completion()
            if status != "complete":
                initiatives_incomplete.append(
                    {
                        "initiative": initiative,
                        "filled": filled,
                        "total": total,
                        "status": status,
                        "completion_percent": int((filled / total) * 100) if total > 0 else 0,
                    }
                )

        # Get spaces without SWOT (empty or partial)
        all_spaces = Space.query.filter_by(organization_id=organization_id).order_by(Space.name).all()
        spaces_no_swot = []
        for space in all_spaces:
            filled, total, status = space.get_swot_completion()
            if status != "complete":
                spaces_no_swot.append(
                    {
                        "space": space,
                        "filled": filled,
                        "total": total,
                        "status": status,
                        "completion_percent": int((filled / total) * 100) if total > 0 else 0,
                    }
                )

        # Get systems without KPIs
        systems_without_kpis = (
            db.session.query(System)
            .join(InitiativeSystemLink, System.id == InitiativeSystemLink.system_id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .outerjoin(KPI, InitiativeSystemLink.id == KPI.initiative_system_link_id)
            .filter(Initiative.organization_id == organization_id, KPI.id.is_(None))
            .distinct()
            .order_by(System.name)
            .all()
        )

        # Get KPIs without governance bodies
        from app.models import KPIGovernanceBodyLink

        kpis_without_gb = (
            db.session.query(KPI)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .outerjoin(KPIGovernanceBodyLink, KPI.id == KPIGovernanceBodyLink.kpi_id)
            .filter(Initiative.organization_id == organization_id, KPIGovernanceBodyLink.id.is_(None))
            .order_by(KPI.name)
            .all()
        )

        # Calculate totals - count unique initiatives only (avoid double-counting)
        unique_initiative_ids = set()
        for init in initiatives_no_consensus:
            unique_initiative_ids.add(init.id)
        for init_dict in initiatives_incomplete:
            unique_initiative_ids.add(init_dict["initiative"].id)

        total_issues = (
            len(unique_initiative_ids) + len(spaces_no_swot) + len(systems_without_kpis) + len(kpis_without_gb)
        )

        return {
            "initiatives_no_consensus": initiatives_no_consensus,
            "initiatives_incomplete": initiatives_incomplete,
            "spaces_no_swot": spaces_no_swot,
            "systems_without_kpis": systems_without_kpis,
            "kpis_without_gb": kpis_without_gb,
            "total": total_issues,
        }
