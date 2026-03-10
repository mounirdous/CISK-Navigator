"""
Organization SSO Configuration model
"""

from datetime import datetime

from app.extensions import db


class OrganizationSSOConfig(db.Model):
    """
    SSO configuration for an organization.

    Each organization can have its own SSO identity provider configuration.
    Supports both OIDC and SAML protocols.
    """

    __tablename__ = "organization_sso_configs"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False, index=True)

    # Provider Configuration
    provider_type = db.Column(db.String(50), nullable=False)  # 'oidc', 'saml', 'google', 'azure', 'okta'
    is_enabled = db.Column(db.Boolean, default=False, nullable=False)

    # OIDC/OAuth 2.0 Configuration
    client_id = db.Column(db.String(255), nullable=True)
    client_secret = db.Column(db.Text, nullable=True)  # TODO: Encrypt this
    discovery_url = db.Column(db.String(500), nullable=True)  # .well-known/openid-configuration URL
    authorization_endpoint = db.Column(db.String(500), nullable=True)
    token_endpoint = db.Column(db.String(500), nullable=True)
    userinfo_endpoint = db.Column(db.String(500), nullable=True)
    jwks_uri = db.Column(db.String(500), nullable=True)

    # SAML Configuration
    idp_entity_id = db.Column(db.String(500), nullable=True)
    sso_url = db.Column(db.String(500), nullable=True)
    x509_cert = db.Column(db.Text, nullable=True)

    # User Provisioning Settings
    email_domains = db.Column(db.JSON, nullable=True)  # ['example.com', 'example.org']
    auto_provision_users = db.Column(db.Boolean, default=True, nullable=False)
    default_permissions = db.Column(db.JSON, nullable=True)  # Default permissions for new users

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relationships
    organization = db.relationship("Organization", backref="sso_config")
    updater = db.relationship("User", foreign_keys=[updated_by])

    def __repr__(self):
        return f"<OrganizationSSOConfig org={self.organization_id} provider={self.provider_type}>"

    def is_configured(self):
        """Check if SSO is fully configured"""
        if self.provider_type in ["oidc", "google", "azure", "okta"]:
            return bool(self.client_id and self.client_secret and (self.discovery_url or self.authorization_endpoint))
        elif self.provider_type == "saml":
            return bool(self.idp_entity_id and self.sso_url and self.x509_cert)
        return False

    def matches_email_domain(self, email):
        """Check if an email address matches this org's configured domains"""
        if not self.email_domains or not email:
            return False

        domain = email.split("@")[-1].lower()
        return domain in [d.lower() for d in self.email_domains]

    def get_oidc_config(self):
        """Get OIDC configuration as dict"""
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "discovery_url": self.discovery_url,
            "authorization_endpoint": self.authorization_endpoint,
            "token_endpoint": self.token_endpoint,
            "userinfo_endpoint": self.userinfo_endpoint,
            "jwks_uri": self.jwks_uri,
        }

    def get_saml_config(self):
        """Get SAML configuration as dict"""
        return {
            "idp_entity_id": self.idp_entity_id,
            "sso_url": self.sso_url,
            "x509_cert": self.x509_cert,
        }

    @staticmethod
    def get_by_organization(organization_id):
        """Get SSO config for an organization"""
        return OrganizationSSOConfig.query.filter_by(organization_id=organization_id).first()

    @staticmethod
    def find_by_email_domain(email):
        """Find organization SSO config matching an email domain"""
        if not email or "@" not in email:
            return None

        domain = email.split("@")[-1].lower()

        # Query all enabled SSO configs
        configs = OrganizationSSOConfig.query.filter_by(is_enabled=True).all()

        for config in configs:
            if config.email_domains and domain in [d.lower() for d in config.email_domains]:
                return config

        return None
