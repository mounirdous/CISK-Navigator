"""
Space model
"""
from datetime import datetime
from app.extensions import db


class Space(db.Model):
    """
    Space model.

    A space is a flexible grouping concept such as season, site, customer, supplier, etc.
    It belongs to one organization and contains challenges.
    """
    __tablename__ = 'spaces'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    space_label = db.Column(db.String(100), nullable=True, comment='e.g., Season, Site, Customer, Supplier')
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship('Organization', back_populates='spaces')
    challenges = db.relationship('Challenge', back_populates='space', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Space {self.name}>'
