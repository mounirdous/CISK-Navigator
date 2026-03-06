"""
KPI model
"""
from datetime import datetime
from app.extensions import db


class KPI(db.Model):
    """
    KPI model.

    A KPI belongs to one specific Initiative-System Link.
    This allows the same system to have different KPI sets in different initiatives.

    A KPI can have multiple value types configured via KPIValueTypeConfig.
    """
    __tablename__ = 'kpis'

    id = db.Column(db.Integer, primary_key=True)
    initiative_system_link_id = db.Column(db.Integer,
                                          db.ForeignKey('initiative_system_links.id', ondelete='CASCADE'),
                                          nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    initiative_system_link = db.relationship('InitiativeSystemLink', back_populates='kpis')
    value_type_configs = db.relationship('KPIValueTypeConfig',
                                         back_populates='kpi',
                                         cascade='all, delete-orphan')

    def __repr__(self):
        return f'<KPI {self.name}>'
