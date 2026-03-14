"""
Entity Type Default Settings - System-wide branding and styling
"""

from datetime import datetime

from app.extensions import db


class EntityTypeDefault(db.Model):
    """
    Store default colors, icons, and styling for entity types.

    This allows super admins to configure the default appearance of
    organizations, spaces, challenges, initiatives, systems, and KPIs
    without code changes. Individual entities can override these defaults.
    """

    __tablename__ = "entity_type_defaults"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(
        db.String(50), unique=True, nullable=False, index=True
    )  # 'organization', 'space', 'challenge', 'initiative', 'system', 'kpi'
    default_color = db.Column(db.String(7), nullable=False)  # Hex color #RRGGBB
    default_icon = db.Column(db.String(10), nullable=False)  # Emoji or icon identifier
    display_name = db.Column(db.String(100), nullable=False)  # Human-readable name
    description = db.Column(db.Text, nullable=True)  # What this entity represents
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # Relationships
    updater = db.relationship("User", foreign_keys=[updated_by], backref="entity_defaults_updated")

    def __repr__(self):
        return f"<EntityTypeDefault {self.entity_type}: {self.default_color} {self.default_icon}>"

    @staticmethod
    def get_defaults(entity_type):
        """Get defaults for a specific entity type"""
        default = EntityTypeDefault.query.filter_by(entity_type=entity_type).first()
        if default:
            return {"color": default.default_color, "icon": default.default_icon}
        # Fallback to hardcoded defaults if not in database
        return EntityTypeDefault.get_hardcoded_defaults().get(entity_type, {"color": "#6b7280", "icon": "📋"})

    @staticmethod
    def get_all_defaults():
        """Get all entity type defaults as a dictionary"""
        defaults = EntityTypeDefault.query.all()
        result = {}
        for default in defaults:
            result[default.entity_type] = {"color": default.default_color, "icon": default.default_icon}
        return result

    @staticmethod
    def get_hardcoded_defaults():
        """Hardcoded fallback defaults"""
        return {
            "organization": {"color": "#3b82f6", "icon": "🏢"},
            "space": {"color": "#10b981", "icon": "🎯"},
            "challenge": {"color": "#f59e0b", "icon": "⚡"},
            "initiative": {"color": "#8b5cf6", "icon": "🚀"},
            "system": {"color": "#ec4899", "icon": "⚙️"},
            "kpi": {"color": "#06b6d4", "icon": "📊"},
        }

    @staticmethod
    def ensure_defaults_exist():
        """Create default entries if they don't exist"""
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
            existing = EntityTypeDefault.query.filter_by(entity_type=entity_type).first()
            if not existing:
                new_default = EntityTypeDefault(
                    entity_type=entity_type,
                    default_color=defaults["color"],
                    default_icon=defaults["icon"],
                    display_name=entity_names.get(entity_type, entity_type.title()),
                    description=entity_descriptions.get(entity_type, ""),
                )
                db.session.add(new_default)

        db.session.commit()
