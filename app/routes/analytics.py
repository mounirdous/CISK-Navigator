"""
Analytics and Dashboard routes
"""

from datetime import datetime, timedelta

from flask import Blueprint, redirect, render_template, session, url_for
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models import (
    KPI,
    CellComment,
    Contribution,
    Initiative,
    InitiativeSystemLink,
    KPIValueTypeConfig,
    Space,
    System,
)

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@bp.route("/dashboard")
@login_required
def dashboard():
    """Analytics dashboard with KPI health, trends, and activity"""
    org_id = session.get("organization_id")
    if not org_id:
        return redirect(url_for("auth.login"))

    # Date range for trends
    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)

    # ==== KPI Statistics ====

    # Total KPIs in organization
    total_kpis = (
        db.session.query(KPI).join(InitiativeSystemLink).join(System).filter(System.organization_id == org_id).count()
    )

    # Active (not archived) KPIs
    active_kpis = (
        db.session.query(KPI)
        .join(InitiativeSystemLink)
        .join(System)
        .filter(System.organization_id == org_id, KPI.is_archived.is_(False))
        .count()
    )

    # KPIs with recent activity (contributions in last 7 days)
    recent_kpi_ids = (
        db.session.query(KPI.id.distinct())
        .join(KPIValueTypeConfig, KPI.id == KPIValueTypeConfig.kpi_id)
        .join(Contribution, KPIValueTypeConfig.id == Contribution.kpi_value_type_config_id)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(System, InitiativeSystemLink.system_id == System.id)
        .filter(System.organization_id == org_id, Contribution.created_at >= seven_days_ago)
        .all()
    )
    kpis_with_recent_activity = len(recent_kpi_ids)

    # KPIs with no contributions ever (potentially stale)
    stale_kpis = (
        db.session.query(KPI)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(System, InitiativeSystemLink.system_id == System.id)
        .outerjoin(KPIValueTypeConfig, KPI.id == KPIValueTypeConfig.kpi_id)
        .outerjoin(Contribution, KPIValueTypeConfig.id == Contribution.kpi_value_type_config_id)
        .filter(System.organization_id == org_id, KPI.is_archived.is_(False), Contribution.id.is_(None))
        .count()
    )

    # ==== Contribution Trends ====

    # Contributions per day for last 30 days
    contributions_by_day = (
        db.session.query(func.date(Contribution.created_at).label("date"), func.count(Contribution.id).label("count"))
        .join(KPIValueTypeConfig, Contribution.kpi_value_type_config_id == KPIValueTypeConfig.id)
        .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(System, InitiativeSystemLink.system_id == System.id)
        .filter(System.organization_id == org_id, Contribution.created_at >= thirty_days_ago)
        .group_by(func.date(Contribution.created_at))
        .order_by("date")
        .all()
    )

    # Format for chart
    trend_labels = [str(row.date) for row in contributions_by_day]
    trend_values = [row.count for row in contributions_by_day]

    # ==== User Activity ====

    # Most active contributors (by contribution count)
    # Note: Contributors are free-text names, not user accounts
    top_contributors = (
        db.session.query(Contribution.contributor_name, func.count(Contribution.id).label("contribution_count"))
        .join(KPIValueTypeConfig, Contribution.kpi_value_type_config_id == KPIValueTypeConfig.id)
        .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(System, InitiativeSystemLink.system_id == System.id)
        .filter(System.organization_id == org_id)
        .group_by(Contribution.contributor_name)
        .order_by(func.count(Contribution.id).desc())
        .limit(10)
        .all()
    )

    # ==== Comment Activity ====

    # Total comments in organization
    total_comments = (
        db.session.query(CellComment)
        .join(KPIValueTypeConfig, CellComment.kpi_value_type_config_id == KPIValueTypeConfig.id)
        .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(System, InitiativeSystemLink.system_id == System.id)
        .filter(System.organization_id == org_id)
        .count()
    )

    # Most commented KPIs
    most_commented_kpis = (
        db.session.query(
            KPI.name,
            Initiative.name.label("initiative_name"),
            System.name.label("system_name"),
            func.count(CellComment.id).label("comment_count"),
        )
        .join(KPIValueTypeConfig, CellComment.kpi_value_type_config_id == KPIValueTypeConfig.id)
        .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
        .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
        .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
        .join(System, InitiativeSystemLink.system_id == System.id)
        .filter(System.organization_id == org_id)
        .group_by(KPI.id, KPI.name, Initiative.name, System.name)
        .order_by(func.count(CellComment.id).desc())
        .limit(10)
        .all()
    )

    # ==== Space Statistics ====

    spaces_count = Space.query.filter_by(organization_id=org_id).count()
    private_spaces_count = Space.query.filter_by(organization_id=org_id, is_private=True).count()

    return render_template(
        "analytics/dashboard.html",
        # KPI Stats
        total_kpis=total_kpis,
        active_kpis=active_kpis,
        kpis_with_recent_activity=kpis_with_recent_activity,
        stale_kpis=stale_kpis,
        # Trends
        trend_labels=trend_labels,
        trend_values=trend_values,
        # User Activity
        top_contributors=top_contributors,
        # Comments
        total_comments=total_comments,
        most_commented_kpis=most_commented_kpis,
        # Spaces
        spaces_count=spaces_count,
        private_spaces_count=private_spaces_count,
    )
