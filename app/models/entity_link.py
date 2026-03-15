"""
Entity Links model for URLs/resources attached to entities
"""

from datetime import datetime

from app.extensions import db


class EntityLink(db.Model):
    """
    Links/URLs attached to entities (spaces, challenges, initiatives, systems, KPIs).

    Can be public (shared across organization) or private (visible only to creator).
    """

    __tablename__ = "entity_links"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(
        db.String(20), nullable=False, comment="Type: space, challenge, initiative, system, kpi"
    )
    entity_id = db.Column(db.Integer, nullable=False, comment="ID of the entity")
    url = db.Column(db.Text, nullable=False, comment="The URL/link")
    title = db.Column(db.String(200), nullable=True, comment="Optional description")
    is_public = db.Column(
        db.Boolean, nullable=False, default=False, comment="Public (shared) or private link"
    )
    display_order = db.Column(db.Integer, nullable=False, default=0, comment="Sort order")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relationships
    creator = db.relationship("User", foreign_keys=[created_by])

    # Indexes defined in migration

    def __repr__(self):
        return f"<EntityLink {self.entity_type}:{self.entity_id} - {self.title or self.url[:50]}>"

    @staticmethod
    def get_links_for_entity(entity_type, entity_id, user_id=None, include_private=True):
        """
        Get all links for an entity.

        Args:
            entity_type: Type of entity (space, challenge, initiative, system, kpi)
            entity_id: ID of the entity
            user_id: Current user ID (to include their private links)
            include_private: Whether to include private links (default True)

        Returns:
            List of EntityLink objects ordered by display_order
        """
        query = EntityLink.query.filter_by(entity_type=entity_type, entity_id=entity_id)

        if include_private and user_id:
            # Show public links + user's own private links
            query = query.filter(
                db.or_(EntityLink.is_public == True, EntityLink.created_by == user_id)
            )
        else:
            # Show only public links
            query = query.filter_by(is_public=True)

        return query.order_by(EntityLink.display_order, EntityLink.created_at).all()

    @staticmethod
    def validate_url(url):
        """
        Basic URL validation.

        Returns:
            (is_valid, error_message)
        """
        import re

        if not url or not url.strip():
            return False, "URL is required"

        url = url.strip()

        # Basic URL pattern (supports http, https, ftp, etc.)
        url_pattern = re.compile(
            r"^(https?|ftp)://"  # Protocol
            r"([a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+"  # Domain
            r"(:[0-9]{1,5})?"  # Optional port
            r"(/.*)?$",  # Optional path
            re.IGNORECASE,
        )

        if not url_pattern.match(url):
            return False, "Invalid URL format. Must start with http://, https://, or ftp://"

        if len(url) > 2000:
            return False, "URL is too long (max 2000 characters)"

        return True, None

    def get_display_icon(self):
        """Get emoji icon based on URL type"""
        url_lower = self.url.lower()

        if "docs.google" in url_lower or "drive.google" in url_lower:
            return "📄"
        elif "sharepoint" in url_lower or "onedrive" in url_lower:
            return "📁"
        elif "github" in url_lower or "gitlab" in url_lower:
            return "💻"
        elif "confluence" in url_lower or "wiki" in url_lower:
            return "📖"
        elif "youtube" in url_lower or "vimeo" in url_lower:
            return "🎥"
        elif "slack" in url_lower or "teams.microsoft" in url_lower:
            return "💬"
        elif "jira" in url_lower or "trello" in url_lower:
            return "📋"
        else:
            return "🔗"
