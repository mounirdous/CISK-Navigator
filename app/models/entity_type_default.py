"""
Entity Type Default Settings - System-wide branding and styling
"""

from datetime import datetime

from app.extensions import db


class EntityTypeDefault(db.Model):
    """
    Store default colors, icons, and styling for entity types per organization.

    This allows organization admins to configure the default appearance of
    spaces, challenges, initiatives, systems, and KPIs for their organization.
    Each organization can have different branding.
    """

    __tablename__ = "entity_type_defaults"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    entity_type = db.Column(
        db.String(50), nullable=False, index=True
    )  # 'organization', 'space', 'challenge', 'initiative', 'system', 'kpi'
    default_color = db.Column(db.String(7), nullable=False)  # Hex color #RRGGBB
    default_icon = db.Column(db.String(10), nullable=False)  # Emoji or icon identifier
    default_logo_data = db.Column(
        db.LargeBinary, nullable=True, comment="Default logo image binary data for this entity type"
    )
    default_logo_mime_type = db.Column(db.String(50), nullable=True, comment="Default logo MIME type")
    display_name = db.Column(db.String(100), nullable=False)  # Human-readable name
    description = db.Column(db.Text, nullable=True)  # What this entity represents
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # Unique constraint: one set of defaults per organization per entity type
    __table_args__ = (db.UniqueConstraint("organization_id", "entity_type", name="uq_entity_type_defaults_org_type"),)

    # Relationships
    organization = db.relationship("Organization", backref="entity_defaults")
    updater = db.relationship("User", foreign_keys=[updated_by], backref="entity_defaults_updated")

    def __repr__(self):
        return f"<EntityTypeDefault {self.entity_type}: {self.default_color} {self.default_icon}>"

    @staticmethod
    def get_defaults(organization_id, entity_type):
        """Get defaults for a specific entity type in an organization"""
        default = EntityTypeDefault.query.filter_by(organization_id=organization_id, entity_type=entity_type).first()
        if default:
            return {"color": default.default_color, "icon": default.default_icon}
        # Fallback to hardcoded defaults if not in database
        return EntityTypeDefault.get_hardcoded_defaults().get(entity_type, {"color": "#6b7280", "icon": "📋"})

    @staticmethod
    def get_all_defaults(organization_id):
        """Get all entity type defaults as a dictionary for an organization"""
        defaults = EntityTypeDefault.query.filter_by(organization_id=organization_id).all()
        result = {}
        for default in defaults:
            result[default.entity_type] = {"color": default.default_color, "icon": default.default_icon}
        return result

    @staticmethod
    def get_hardcoded_defaults():
        """Hardcoded fallback defaults"""
        return {
            "organization": {"color": "#3b82f6", "icon": "🏢"},
            "space": {"color": "#10b981", "icon": "🏢"},
            "challenge": {"color": "#f59e0b", "icon": "ƒ"},
            "initiative": {"color": "#8b5cf6", "icon": "δ"},
            "system": {"color": "#ec4899", "icon": "Φ"},
            "kpi": {"color": "#06b6d4", "icon": "Ψ"},
        }

    @staticmethod
    def ensure_defaults_exist(organization_id):
        """Create default entries for an organization if they don't exist"""
        hardcoded = EntityTypeDefault.get_hardcoded_defaults()
        entity_names = {
            "organization": "Organization",
            "space": "Space",
            "challenge": "Challenge",
            "initiative": "Initiative",
            "system": "System",
            "kpi": "KPI",
        }
        entity_descriptions = {
            "organization": "Top-level business unit or company",
            "space": "Strategic grouping (seasons, sites, customers)",
            "challenge": "High-level business challenge or theme",
            "initiative": "Strategic initiative or project",
            "system": "Functional area or capability",
            "kpi": "Key Performance Indicator",
        }

        for entity_type, defaults in hardcoded.items():
            existing = EntityTypeDefault.query.filter_by(
                organization_id=organization_id, entity_type=entity_type
            ).first()
            if not existing:
                new_default = EntityTypeDefault(
                    organization_id=organization_id,
                    entity_type=entity_type,
                    default_color=defaults["color"],
                    default_icon=defaults["icon"],
                    display_name=entity_names.get(entity_type, entity_type.title()),
                    description=entity_descriptions.get(entity_type, ""),
                )
                db.session.add(new_default)

        db.session.commit()
