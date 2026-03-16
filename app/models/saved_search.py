"""
Saved Search Model

Stores user-defined search queries and filters for quick access.
"""

from datetime import datetime

from app.extensions import db


class SavedSearch(db.Model):
    """User-saved search query with filters"""

    __tablename__ = "saved_search"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    name = db.Column(db.String(200), nullable=False)
    query = db.Column(db.Text, nullable=False)
    filters = db.Column(db.JSON)  # Store filters as JSON (entity_types, date_range, status, etc.)

    is_default = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship("User", backref="saved_searches")
    organization = db.relationship("Organization", backref="saved_searches")

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "query": self.query,
            "filters": self.filters or {},
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def get_user_searches(user_id, organization_id):
        """Get all saved searches for a user in an organization"""
        return (
            db.session.query(SavedSearch)
            .filter_by(user_id=user_id, organization_id=organization_id)
            .order_by(SavedSearch.name)
            .all()
        )

    @staticmethod
    def get_default_search(user_id, organization_id):
        """Get the default search for a user in an organization"""
        return (
            db.session.query(SavedSearch)
            .filter_by(user_id=user_id, organization_id=organization_id, is_default=True)
            .first()
        )

    def set_as_default(self):
        """Set this search as the default (unsets others)"""
        # Unset all other defaults for this user/org
        db.session.query(SavedSearch).filter_by(
            user_id=self.user_id, organization_id=self.organization_id, is_default=True
        ).update({"is_default": False})
        # Set this one as default
        self.is_default = True
        db.session.commit()
