"""
Governance Body models
"""

from datetime import datetime

from app.extensions import db


class GovernanceBody(db.Model):
    """
    Governance Body model.

    Represents committees, boards, teams, or other bodies that review and track KPIs.
    Organization-specific, many-to-many with KPIs.
    """

    __tablename__ = "governance_bodies"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    abbreviation = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), nullable=False, default="#3498db")  # Hex color
    display_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)  # Default body cannot be deleted
    is_global = db.Column(db.Boolean, default=False, nullable=False, comment="Visible across all workspaces")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship("Organization", back_populates="governance_bodies")
    kpi_links = db.relationship("KPIGovernanceBodyLink", back_populates="governance_body", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GovernanceBody {self.abbreviation}: {self.name}>"

    @classmethod
    def for_org(cls, org_id, active_only=True):
        """Get all GBs for an org, including global GBs from other orgs."""
        from sqlalchemy import or_
        q = cls.query.filter(or_(cls.organization_id == org_id, cls.is_global.is_(True)))
        if active_only:
            q = q.filter(cls.is_active.is_(True))
        return q.order_by(cls.display_order, cls.name).all()


class KPIGovernanceBodyLink(db.Model):
    """
    Link between a KPI and a Governance Body.

    A KPI can belong to multiple governance bodies.
    A governance body tracks multiple KPIs.
    """

    __tablename__ = "kpi_governance_body_links"

    id = db.Column(db.Integer, primary_key=True)
    kpi_id = db.Column(db.Integer, db.ForeignKey("kpis.id", ondelete="CASCADE"), nullable=False)
    governance_body_id = db.Column(
        db.Integer, db.ForeignKey("governance_bodies.id", ondelete="CASCADE"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Unique constraint: same governance body cannot be linked twice to the same KPI
    __table_args__ = (db.UniqueConstraint("kpi_id", "governance_body_id", name="uq_kpi_governance_body"),)

    # Relationships
    kpi = db.relationship("KPI", back_populates="governance_body_links")
    governance_body = db.relationship("GovernanceBody", back_populates="kpi_links")

    def __repr__(self):
        return f"<KPIGovernanceBodyLink kpi_id={self.kpi_id} governance_body_id={self.governance_body_id}>"
