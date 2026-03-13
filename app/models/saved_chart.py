"""
Saved Chart Model

Stores user-defined chart configurations for quick access.
"""

from datetime import datetime

from app.extensions import db


class SavedChart(db.Model):
    """User-saved chart configuration"""

    __tablename__ = "saved_charts"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Chart configuration
    year_start = db.Column(db.Integer, nullable=False)
    year_end = db.Column(db.Integer, nullable=False)
    view_type = db.Column(db.String(20), nullable=False)  # monthly, quarterly, yearly
    chart_type = db.Column(db.String(20), nullable=False, default="line")  # line, bar
    space_id = db.Column(db.Integer, db.ForeignKey("spaces.id"))
    value_type_id = db.Column(db.Integer, db.ForeignKey("value_types.id"))

    # Period range filters (optional - for monthly/quarterly views)
    # Format: "1,2,3" for Q1-Q3 or "1,2,3,4,5,6" for Jan-Jun
    period_filter = db.Column(db.String(50))

    # Selected KPI config IDs and colors (stored as JSON: {"114": "#007bff", "115": "#28a745"})
    config_ids_colors = db.Column(db.Text, nullable=False)  # JSON mapping config_id to color

    is_shared = db.Column(db.Boolean, default=False)  # Share with org or personal
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = db.relationship("Organization", backref="saved_charts")
    created_by = db.relationship("User", backref="saved_charts")
    space = db.relationship("Space")
    value_type = db.relationship("ValueType")

    def get_config_colors(self):
        """Parse config_ids_colors JSON to dict"""
        import json

        if not self.config_ids_colors:
            return {}
        try:
            return json.loads(self.config_ids_colors)
        except Exception:
            return {}

    def set_config_colors(self, config_colors):
        """Set config_ids_colors from dict {config_id: color}"""
        import json

        self.config_ids_colors = json.dumps(config_colors)
