"""
System-wide settings and feature flags model
"""

from datetime import datetime

from app.extensions import db


class SystemSetting(db.Model):
    """
    System-wide settings and feature flags.

    Provides a database-backed configuration system for runtime settings
    that can be modified through the Super Admin interface without code changes.

    Settings are categorized and typed for proper validation.
    """

    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    value_type = db.Column(db.String(20), nullable=True)  # 'boolean', 'string', 'integer', 'json'
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)  # 'authentication', 'system', 'security', 'features'
    is_public = db.Column(db.Boolean, default=False, nullable=False)  # Can non-admins read this?
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # Relationships
    updater = db.relationship("User", foreign_keys=[updated_by], backref="system_settings_updated")

    def __repr__(self):
        return f"<SystemSetting {self.key}={self.value}>"

    @staticmethod
    def get_value(key, default=None):
        """Get a setting value by key, return default if not found"""
        setting = SystemSetting.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def get_bool(key, default=False):
        """Get a boolean setting value"""
        value = SystemSetting.get_value(key)
        if value is None:
            return default
        return str(value).lower() in ("true", "1", "yes", "on")

    @staticmethod
    def get_int(key, default=0):
        """Get an integer setting value"""
        value = SystemSetting.get_value(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def get_string(key, default=""):
        """Get a string setting value"""
        value = SystemSetting.get_value(key)
        return value if value is not None else default

    @staticmethod
    def set_value(key, value, updated_by_user_id=None):
        """
        Set a setting value. Creates the setting if it doesn't exist.

        Args:
            key: Setting key
            value: Setting value (will be converted to string)
            updated_by_user_id: ID of user making the change
        """
        setting = SystemSetting.query.filter_by(key=key).first()
        if not setting:
            setting = SystemSetting(key=key)
            db.session.add(setting)

        setting.value = str(value)
        setting.updated_by = updated_by_user_id
        setting.updated_at = datetime.utcnow()

    @staticmethod
    def is_sso_enabled():
        """Check if SSO is enabled system-wide"""
        return SystemSetting.get_bool("sso_enabled", default=False)

    @staticmethod
    def is_maintenance_mode():
        """Check if system is in maintenance mode"""
        return SystemSetting.get_bool("maintenance_mode", default=False)

    @staticmethod
    def is_beta_enabled():
        """Check if beta testing program is enabled system-wide"""
        return SystemSetting.get_bool("beta_enabled", default=False)

    @staticmethod
    def is_rollup_cache_stale(organization_id):
        """Check if rollup cache is stale for an organization."""
        val = SystemSetting.get_value(f"rollup_cache_stale_{organization_id}")
        if val is None:
            return True  # Default stale (never computed)
        return val not in ("false", "0")

    @staticmethod
    def get_rollup_stale_info(organization_id):
        """Get stale info — returns None (fresh), 'full' (full recompute), or list of changed entity paths."""
        import json
        val = SystemSetting.get_value(f"rollup_cache_stale_{organization_id}")
        if val is None or val == "true":
            return "full"
        if val == "false":
            return None
        try:
            return json.loads(val)  # List of changed paths
        except (ValueError, TypeError):
            return "full"

    @staticmethod
    def mark_rollup_cache_stale(organization_id, changed_path=None):
        """Mark rollup cache as stale. If changed_path provided, store for incremental recompute."""
        import json
        current = SystemSetting.get_value(f"rollup_cache_stale_{organization_id}")
        if current == "false" or current is None:
            # Fresh → stale with specific change
            if changed_path:
                SystemSetting.set_value(f"rollup_cache_stale_{organization_id}", json.dumps([changed_path]))
            else:
                SystemSetting.set_value(f"rollup_cache_stale_{organization_id}", "true")
        elif current == "true":
            pass  # Already full stale
        else:
            # Already has incremental changes — append or escalate to full
            try:
                changes = json.loads(current)
                if isinstance(changes, list):
                    if changed_path:
                        changes.append(changed_path)
                    if len(changes) > 20:
                        # Too many incremental changes — escalate to full recompute
                        SystemSetting.set_value(f"rollup_cache_stale_{organization_id}", "true")
                    else:
                        SystemSetting.set_value(f"rollup_cache_stale_{organization_id}", json.dumps(changes))
                else:
                    SystemSetting.set_value(f"rollup_cache_stale_{organization_id}", "true")
            except (ValueError, TypeError):
                SystemSetting.set_value(f"rollup_cache_stale_{organization_id}", "true")

    @staticmethod
    def mark_rollup_cache_fresh(organization_id):
        """Mark rollup cache as fresh after recomputation."""
        SystemSetting.set_value(f"rollup_cache_stale_{organization_id}", "false")

    @staticmethod
    def is_precompute_rollups_enabled():
        """Check if rollup pre-computation is enabled.
        When ON, workspace reads from rollup_cache table (fast).
        When OFF (default), computes on the fly (slow but always fresh)."""
        return SystemSetting.get_bool("precompute_rollups_enabled", default=False)

    @staticmethod
    def is_tree_cache_enabled():
        """Check if workspace tree data caching is enabled (localStorage).
        When OFF, workspace always fetches fresh data from server.
        When ON (default), data is cached in localStorage for up to 20 minutes."""
        return SystemSetting.get_bool("tree_cache_enabled", default=True)

    @staticmethod
    def get_session_timeout():
        """Get session timeout in seconds"""
        return SystemSetting.get_int("session_timeout_seconds", default=3600)

    @staticmethod
    def get_settings_by_category(category):
        """Get all settings in a category"""
        return SystemSetting.query.filter_by(category=category).order_by(SystemSetting.key).all()

    @staticmethod
    def get_all_settings_grouped():
        """Get all settings grouped by category"""
        all_settings = SystemSetting.query.order_by(SystemSetting.category, SystemSetting.key).all()
        grouped = {}
        for setting in all_settings:
            category = setting.category or "other"
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(setting)
        return grouped

    @staticmethod
    def get_entity_defaults():
        """Get default colors and icons for entity types"""
        import json

        value = SystemSetting.get_value("entity_defaults")
        if not value:
            # Return hardcoded defaults if not configured
            return {
                "organization": {"color": "#3b82f6", "icon": "🏢"},
                "space": {"color": "#10b981", "icon": "🎯"},
                "challenge": {"color": "#f59e0b", "icon": "⚡"},
                "initiative": {"color": "#8b5cf6", "icon": "🚀"},
                "system": {"color": "#ec4899", "icon": "⚙️"},
                "kpi": {"color": "#06b6d4", "icon": "📊"},
            }
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            # Fallback to defaults if JSON is invalid
            return {
                "organization": {"color": "#3b82f6", "icon": "🏢"},
                "space": {"color": "#10b981", "icon": "🎯"},
                "challenge": {"color": "#f59e0b", "icon": "⚡"},
                "initiative": {"color": "#8b5cf6", "icon": "🚀"},
                "system": {"color": "#ec4899", "icon": "⚙️"},
                "kpi": {"color": "#06b6d4", "icon": "📊"},
            }

    @staticmethod
    def set_entity_defaults(defaults_dict, updated_by_user_id=None):
        """Set default colors and icons for entity types"""
        import json

        SystemSetting.set_value("entity_defaults", json.dumps(defaults_dict), updated_by_user_id)
