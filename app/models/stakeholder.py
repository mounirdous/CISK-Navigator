"""Stakeholder mapping models for network analysis and sponsor identification."""

from datetime import datetime

from app import db


class Stakeholder(db.Model):
    """Represents a stakeholder in the organization's network."""

    __tablename__ = "stakeholders"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    visibility = db.Column(db.String(20), nullable=False, default="shared", index=True)  # 'private' or 'shared'
    name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(200))
    department = db.Column(db.String(200), index=True)
    email = db.Column(db.String(255))
    influence_level = db.Column(db.Integer, nullable=False, default=50)  # 1-100
    interest_level = db.Column(db.Integer, nullable=False, default=50)  # 1-100
    support_level = db.Column(
        db.String(20),
        nullable=False,
        default="neutral",
        index=True,
    )
    notes = db.Column(db.Text)
    position_x = db.Column(db.Float)  # For saved graph positions
    position_y = db.Column(db.Float)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = db.relationship("Organization", backref="stakeholders")
    created_by = db.relationship("User", foreign_keys=[created_by_user_id], backref="created_stakeholders")
    outgoing_relationships = db.relationship(
        "StakeholderRelationship",
        foreign_keys="StakeholderRelationship.from_stakeholder_id",
        backref="from_stakeholder",
        cascade="all, delete-orphan",
    )
    incoming_relationships = db.relationship(
        "StakeholderRelationship",
        foreign_keys="StakeholderRelationship.to_stakeholder_id",
        backref="to_stakeholder",
        cascade="all, delete-orphan",
    )
    entity_links = db.relationship("StakeholderEntityLink", backref="stakeholder", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Stakeholder {self.name}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "department": self.department,
            "email": self.email,
            "influence_level": self.influence_level,
            "interest_level": self.interest_level,
            "support_level": self.support_level,
            "notes": self.notes,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "visibility": self.visibility,
            "created_by_user_id": self.created_by_user_id,
        }

    def is_visible_to_user(self, user):
        """Check if this stakeholder is visible to the given user."""
        # Super admins and global admins see everything
        if user.is_super_admin or user.is_global_admin:
            return True

        # Org admins see everything in their org
        if user.is_org_admin(self.organization_id):
            return True

        # Shared stakeholders are visible to all in organization
        if self.visibility == "shared":
            return True

        # Private stakeholders only visible to creator
        if self.visibility == "private":
            return self.created_by_user_id == user.id

        return False

    def get_all_relationships(self):
        """Get all relationships (both incoming and outgoing)."""
        return self.outgoing_relationships + self.incoming_relationships

    def get_connected_stakeholders(self):
        """Get all directly connected stakeholders."""
        connected = []
        for rel in self.outgoing_relationships:
            connected.append(rel.to_stakeholder)
        for rel in self.incoming_relationships:
            connected.append(rel.from_stakeholder)
        return list(set(connected))  # Remove duplicates

    def get_linked_entities(self):
        """Get all linked CISK entities grouped by type."""
        from app.models import KPI, Challenge, Initiative, Space, System

        entity_map = {"space": Space, "challenge": Challenge, "initiative": Initiative, "system": System, "kpi": KPI}

        linked = {"space": [], "challenge": [], "initiative": [], "system": [], "kpi": []}

        for link in self.entity_links:
            entity_class = entity_map.get(link.entity_type)
            if entity_class:
                entity = entity_class.query.get(link.entity_id)
                if entity:
                    linked[link.entity_type].append(
                        {"entity": entity, "interest_level": link.interest_level, "impact_level": link.impact_level}
                    )

        return linked


class StakeholderRelationship(db.Model):
    """Represents a relationship between two stakeholders."""

    __tablename__ = "stakeholder_relationships"

    id = db.Column(db.Integer, primary_key=True)
    from_stakeholder_id = db.Column(
        db.Integer, db.ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_stakeholder_id = db.Column(
        db.Integer, db.ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type = db.Column(db.String(20), nullable=False)
    strength = db.Column(db.Integer, nullable=False, default=50)  # 1-100
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<StakeholderRelationship {self.from_stakeholder.name} -> {self.to_stakeholder.name}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "from": self.from_stakeholder_id,
            "to": self.to_stakeholder_id,
            "relationship_type": self.relationship_type,
            "strength": self.strength,
            "notes": self.notes,
        }


class StakeholderEntityLink(db.Model):
    """Links stakeholders to CISK entities (spaces, challenges, initiatives, systems, KPIs)."""

    __tablename__ = "stakeholder_entity_links"

    id = db.Column(db.Integer, primary_key=True)
    stakeholder_id = db.Column(
        db.Integer, db.ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type = db.Column(db.String(50), nullable=False, index=True)  # space, challenge, initiative, system, kpi
    entity_id = db.Column(db.Integer, nullable=False)
    interest_level = db.Column(db.Integer, nullable=False, default=50)  # How interested the stakeholder is
    impact_level = db.Column(db.Integer, nullable=False, default=50)  # How much the entity impacts the stakeholder
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (db.Index("ix_stakeholder_entity_links_entity", "entity_type", "entity_id"),)

    def __repr__(self):
        return f"<StakeholderEntityLink {self.stakeholder.name} -> {self.entity_type}:{self.entity_id}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "stakeholder_id": self.stakeholder_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "interest_level": self.interest_level,
            "impact_level": self.impact_level,
            "notes": self.notes,
        }

    def get_entity(self):
        """Get the actual entity object."""
        from app.models import KPI, Challenge, Initiative, Space, System

        entity_map = {"space": Space, "challenge": Challenge, "initiative": Initiative, "system": System, "kpi": KPI}

        entity_class = entity_map.get(self.entity_type)
        if entity_class:
            return entity_class.query.get(self.entity_id)
        return None
