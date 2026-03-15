"""
Geography models for regional/country/site tracking
"""

from datetime import datetime

from app.extensions import db


class GeographyRegion(db.Model):
    """
    Geography Region (e.g., EMEA, Americas, APAC).
    Top level of geography hierarchy.
    """

    __tablename__ = "geography_regions"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=True, comment="Short code (e.g., EMEA, AMER)")
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = db.relationship("Organization", backref="geography_regions")
    countries = db.relationship(
        "GeographyCountry",
        back_populates="region",
        cascade="all, delete-orphan",
        order_by="GeographyCountry.display_order",
    )

    def __repr__(self):
        return f"<GeographyRegion {self.name}>"

    def get_kpi_count(self):
        """Get total number of KPIs associated with sites in this region"""
        count = 0
        for country in self.countries:
            count += country.get_kpi_count()
        return count


class GeographyCountry(db.Model):
    """
    Geography Country (e.g., France, Germany, Spain).
    Belongs to a region, contains sites.
    """

    __tablename__ = "geography_countries"

    id = db.Column(db.Integer, primary_key=True)
    region_id = db.Column(
        db.Integer,
        db.ForeignKey("geography_regions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), nullable=True, comment="Short code (e.g., FR, DE, ES)")
    iso_code = db.Column(db.String(3), nullable=True, comment="ISO 3166-1 alpha-2/3 code")
    # Country centroid coordinates (for map display)
    latitude = db.Column(db.Numeric(precision=10, scale=8), nullable=True)
    longitude = db.Column(db.Numeric(precision=11, scale=8), nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    # GeoJSON polygon for map display (stored as JSON)
    geojson = db.Column(db.JSON, nullable=True, comment="GeoJSON polygon for country borders")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    region = db.relationship("GeographyRegion", back_populates="countries")
    sites = db.relationship(
        "GeographySite",
        back_populates="country",
        cascade="all, delete-orphan",
        order_by="GeographySite.display_order",
    )

    def __repr__(self):
        return f"<GeographyCountry {self.name}>"

    def get_kpi_count(self):
        """Get total number of KPIs associated with sites in this country"""
        count = 0
        for site in self.sites:
            count += site.get_kpi_count()
        return count


class GeographySite(db.Model):
    """
    Geography Site (e.g., Paris HQ, Lyon Office, Berlin Lab).
    Physical location where KPIs are measured.
    """

    __tablename__ = "geography_sites"

    id = db.Column(db.Integer, primary_key=True)
    country_id = db.Column(
        db.Integer,
        db.ForeignKey("geography_countries.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), nullable=True, comment="Short code for display (e.g., PAR-HQ)")
    address = db.Column(db.Text, nullable=True, comment="Physical address")
    latitude = db.Column(db.Numeric(precision=10, scale=8), nullable=True, comment="Latitude for map display")
    longitude = db.Column(db.Numeric(precision=11, scale=8), nullable=True, comment="Longitude for map display")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    country = db.relationship("GeographyCountry", back_populates="sites")
    kpi_assignments = db.relationship("KPISiteAssignment", back_populates="site", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GeographySite {self.name}>"

    def get_kpi_count(self):
        """Get number of KPIs assigned to this site"""
        return len(self.kpi_assignments)

    def get_coordinates_dict(self):
        """Get coordinates as dictionary for JSON serialization"""
        if self.latitude is not None and self.longitude is not None:
            return {
                "lat": float(self.latitude),
                "lon": float(self.longitude),
            }
        return None


class KPISiteAssignment(db.Model):
    """
    Many-to-many junction table linking KPIs to Sites.
    One KPI can be measured at multiple sites.
    """

    __tablename__ = "kpi_site_assignments"

    id = db.Column(db.Integer, primary_key=True)
    kpi_id = db.Column(db.Integer, db.ForeignKey("kpis.id", ondelete="CASCADE"), nullable=False)
    site_id = db.Column(
        db.Integer,
        db.ForeignKey("geography_sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    kpi = db.relationship("KPI", backref="site_assignments")
    site = db.relationship("GeographySite", back_populates="kpi_assignments")

    # Ensure unique KPI-Site pairs
    __table_args__ = (db.UniqueConstraint("kpi_id", "site_id", name="uq_kpi_site"),)

    def __repr__(self):
        return f"<KPISiteAssignment KPI:{self.kpi_id} Site:{self.site_id}>"
