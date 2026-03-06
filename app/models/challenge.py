"""
Challenge model
"""
from datetime import datetime
from app.extensions import db


class Challenge(db.Model):
    """
    Challenge model.

    A challenge belongs to one space and one organization.
    Challenges can be linked to multiple initiatives via ChallengeInitiativeLink.
    """
    __tablename__ = 'challenges'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    space_id = db.Column(db.Integer, db.ForeignKey('spaces.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship('Organization', back_populates='challenges')
    space = db.relationship('Space', back_populates='challenges')
    initiative_links = db.relationship('ChallengeInitiativeLink',
                                       back_populates='challenge',
                                       cascade='all, delete-orphan')

    def get_rollup_value(self, value_type_id):
        """Get rolled-up value from initiatives for this challenge"""
        from app.services import AggregationService
        try:
            result = AggregationService.get_initiative_to_challenge_rollup(self.id, value_type_id)
            return result
        except Exception:
            return None

    def __repr__(self):
        return f'<Challenge {self.name}>'
