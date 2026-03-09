"""
Initiative models
"""
from datetime import datetime
from app.extensions import db


class Initiative(db.Model):
    """
    Initiative model.

    Initiatives are organization-level objects that can be reused across multiple challenges.
    They are linked to challenges via ChallengeInitiativeLink.
    They are linked to systems via InitiativeSystemLink.
    """
    __tablename__ = 'initiatives'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship('Organization', back_populates='initiatives')
    challenge_links = db.relationship('ChallengeInitiativeLink',
                                      back_populates='initiative',
                                      cascade='all, delete-orphan')
    system_links = db.relationship('InitiativeSystemLink',
                                   back_populates='initiative',
                                   cascade='all, delete-orphan')

    def get_rollup_value(self, value_type_id):
        """Get rolled-up value from systems for this initiative"""
        from app.services import AggregationService
        try:
            result = AggregationService.get_system_to_initiative_rollup(self.id, value_type_id)
            return result
        except Exception:
            return None

    def get_color_config(self, value_type_id):
        """Get a representative KPIValueTypeConfig for coloring and scaling rollups

        Returns the config with the largest display scale (millions > thousands > default)
        to ensure rollups show appropriate precision
        """
        scale_priority = {'millions': 3, 'thousands': 2, 'default': 1, None: 0}
        best_config = None
        best_scale = 0

        for sys_link in self.system_links:
            for kpi in sys_link.kpis:
                for config in kpi.value_type_configs:
                    if config.value_type_id == value_type_id:
                        current_scale = scale_priority.get(config.display_scale, 0)
                        if current_scale > best_scale:
                            best_scale = current_scale
                            best_config = config
                        elif not best_config:
                            best_config = config

        return best_config

    def __repr__(self):
        return f'<Initiative {self.name}>'


class ChallengeInitiativeLink(db.Model):
    """
    Link between a Challenge and an Initiative.

    One initiative can address multiple challenges.
    Roll-up configuration from initiative to challenge is stored here.
    """
    __tablename__ = 'challenge_initiative_links'

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id', ondelete='CASCADE'), nullable=False)
    initiative_id = db.Column(db.Integer, db.ForeignKey('initiatives.id', ondelete='CASCADE'), nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Unique constraint: same initiative cannot be linked twice to the same challenge
    __table_args__ = (
        db.UniqueConstraint('challenge_id', 'initiative_id', name='uq_challenge_initiative'),
    )

    # Relationships
    challenge = db.relationship('Challenge', back_populates='initiative_links')
    initiative = db.relationship('Initiative', back_populates='challenge_links')
    rollup_rules = db.relationship('RollupRule',
                                   foreign_keys='RollupRule.source_id',
                                   primaryjoin='and_(RollupRule.source_id==ChallengeInitiativeLink.id, '
                                               'RollupRule.source_type=="challenge_initiative")',
                                   cascade='all, delete-orphan',
                                   viewonly=True)

    def __repr__(self):
        return f'<ChallengeInitiativeLink challenge_id={self.challenge_id} initiative_id={self.initiative_id}>'
