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
    organization = db.relationship("Organization", backref=db.backref("geography_regions", passive_deletes=True))
    countries = db.relationship(
        "GeographyCountry",
        back_populates="region",
        cascade="all, delete-orphan",
        order_by="GeographyCountry.display_order",
    )
    geography_assignments = db.relationship(
        "KPIGeographyAssignment", back_populates="region", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<GeographyRegion {self.name}>"

    def get_kpi_count(self):
        """Get total number of KPIs (direct + from all countries + sites)"""
        # Direct region assignments
        direct_count = len(self.geography_assignments)
        # From all countries in this region (direct + from their sites)
        countries_count = 0
        if self.countries:
            countries_count = sum(country.get_kpi_count() for country in self.countries)
        return direct_count + countries_count


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
    geography_assignments = db.relationship(
        "KPIGeographyAssignment", back_populates="country", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<GeographyCountry {self.name}>"

    def get_kpi_count(self):
        """Get total number of KPIs (direct + inherited from region + from all sites)"""
        # Direct country assignments
        direct_count = len(self.geography_assignments)

        # Inherited from parent region (if region exists)
        region_count = 0
        if self.region and hasattr(self.region, "geography_assignments"):
            region_count = len([a for a in self.region.geography_assignments if a.region_id == self.region_id])

        # From all sites in this country
        sites_count = 0
        if self.sites:
            sites_count = sum(
                len(site.geography_assignments) for site in self.sites if hasattr(site, "geography_assignments")
            )

        return direct_count + region_count + sites_count


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
    # Legacy site assignments (deprecated)
    kpi_assignments = db.relationship("KPISiteAssignment", back_populates="site", cascade="all, delete-orphan")
    # New flexible geography assignments
    geography_assignments = db.relationship(
        "KPIGeographyAssignment", back_populates="site", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<GeographySite {self.name}>"

    def get_kpi_count(self):
        """Get number of KPIs assigned to this site (includes direct + inherited from country/region)"""
        # Direct site assignments
        direct_count = len(self.geography_assignments)

        # Inherited from country level (if country exists)
        country_count = 0
        if self.country and hasattr(self.country, "geography_assignments"):
            country_count = len([a for a in self.country.geography_assignments if a.country_id == self.country_id])

        # Inherited from region level (if country and region exist)
        region_count = 0
        if self.country and self.country.region and hasattr(self.country.region, "geography_assignments"):
            region_count = len(
                [a for a in self.country.region.geography_assignments if a.region_id == self.country.region_id]
            )

        return direct_count + country_count + region_count

    def get_coordinates_dict(self):
        """Get coordinates as dictionary for JSON serialization"""
        if self.latitude is not None and self.longitude is not None:
            return {
                "lat": float(self.latitude),
                "lon": float(self.longitude),
            }
        return None


class KPIGeographyAssignment(db.Model):
    """
    Flexible geography assignment for KPIs.
    A KPI can be assigned to a Region, Country, or Site.
    Exactly ONE of region_id, country_id, or site_id must be set.

    Hierarchy resolution:
    - Region assignment: KPI visible at region level only
    - Country assignment: KPI visible at country + parent region
    - Site assignment: KPI visible at site + parent country + grandparent region
    """

    __tablename__ = "kpi_geography_assignments"

    id = db.Column(db.Integer, primary_key=True)
    kpi_id = db.Column(db.Integer, db.ForeignKey("kpis.id", ondelete="CASCADE"), nullable=False)

    # Flexible assignment - exactly ONE must be set
    region_id = db.Column(
        db.Integer,
        db.ForeignKey("geography_regions.id", ondelete="CASCADE"),
        nullable=True,
    )
    country_id = db.Column(
        db.Integer,
        db.ForeignKey("geography_countries.id", ondelete="CASCADE"),
        nullable=True,
    )
    site_id = db.Column(
        db.Integer,
        db.ForeignKey("geography_sites.id", ondelete="CASCADE"),
        nullable=True,
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    kpi = db.relationship("KPI", backref="geography_assignments")
    region = db.relationship("GeographyRegion", back_populates="geography_assignments")
    country = db.relationship("GeographyCountry", back_populates="geography_assignments")
    site = db.relationship("GeographySite", back_populates="geography_assignments")

    def __repr__(self):
        if self.site_id:
            return f"<KPIGeographyAssignment KPI:{self.kpi_id} Site:{self.site_id}>"
        elif self.country_id:
            return f"<KPIGeographyAssignment KPI:{self.kpi_id} Country:{self.country_id}>"
        else:
            return f"<KPIGeographyAssignment KPI:{self.kpi_id} Region:{self.region_id}>"

    def get_level(self):
        """Return the assignment level: 'region', 'country', or 'site'"""
        if self.site_id:
            return "site"
        elif self.country_id:
            return "country"
        else:
            return "region"

    def get_entity(self):
        """Return the assigned entity (Region, Country, or Site object)"""
        if self.site_id:
            return self.site
        elif self.country_id:
            return self.country
        else:
            return self.region

    def get_hierarchy_path(self):
        """Return the full hierarchy path as string"""
        if self.site_id and self.site:
            return f"{self.site.country.region.name} > {self.site.country.name} > {self.site.name}"
        elif self.country_id and self.country:
            return f"{self.country.region.name} > {self.country.name}"
        elif self.region_id and self.region:
            return self.region.name
        return "Unknown"


# Keep old table name for backward compatibility (will be migrated)
class KPISiteAssignment(db.Model):
    """
    DEPRECATED: Use KPIGeographyAssignment instead.
    Legacy table for migration purposes only.
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
