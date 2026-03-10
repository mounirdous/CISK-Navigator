"""
Instance-wide SSO Configuration model
"""

from datetime import datetime

from sqlalchemy.ext.hybrid import hybrid_property

from app.extensions import db
from app.utils.encryption import EncryptionService


class SSOConfig(db.Model):
    """
    SSO configuration for the entire CISK Navigator instance.

    This is a singleton model - only one configuration should exist.
    All users authenticate through the same company identity provider.
    """

    __tablename__ = "sso_config"

    id = db.Column(db.Integer, primary_key=True)

    # Provider Configuration
    provider_type = db.Column(db.String(50), nullable=False)  # 'oidc', 'saml', 'google', 'azure', 'okta'
    is_enabled = db.Column(db.Boolean, default=False, nullable=False)

    # OIDC/OAuth 2.0 Configuration
    client_id = db.Column(db.String(255), nullable=True)
    _client_secret_encrypted = db.Column("client_secret", db.Text, nullable=True)  # Encrypted at rest
    discovery_url = db.Column(db.String(500), nullable=True)  # .well-known/openid-configuration URL
    authorization_endpoint = db.Column(db.String(500), nullable=True)
    token_endpoint = db.Column(db.String(500), nullable=True)
    userinfo_endpoint = db.Column(db.String(500), nullable=True)
    jwks_uri = db.Column(db.String(500), nullable=True)

    # User Provisioning Settings
    auto_provision_users = db.Column(db.Boolean, default=True, nullable=False)
    default_permissions = db.Column(db.JSON, nullable=True)  # Default permissions for new users

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relationships
    updater = db.relationship("User", foreign_keys=[updated_by])

    @hybrid_property
    def client_secret(self):
        """Decrypt client secret when reading"""
        if not self._client_secret_encrypted:
            return None
        try:
            return EncryptionService.decrypt(self._client_secret_encrypted)
        except Exception:
            # If decryption fails, might be stored as plaintext (migration case)
            # Return as-is and log warning
            return self._client_secret_encrypted

    @client_secret.setter
    def client_secret(self, value):
        """Encrypt client secret when writing"""
        if value is None:
            self._client_secret_encrypted = None
        else:
            try:
                self._client_secret_encrypted = EncryptionService.encrypt(value)
            except ValueError:
                # If ENCRYPTION_KEY not set, store as plaintext (dev mode)
                self._client_secret_encrypted = value

    def __repr__(self):
        return f"<SSOConfig provider={self.provider_type} enabled={self.is_enabled}>"

    def is_configured(self):
        """Check if SSO is fully configured"""
        if self.provider_type in ["oidc", "google", "azure", "okta"]:
            return bool(self.client_id and self.client_secret and (self.discovery_url or self.authorization_endpoint))
        elif self.provider_type == "saml":
            # SAML not yet implemented
            return False
        return False

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

    @staticmethod
    def get_instance():
        """
        Get the singleton SSO configuration.

        Returns the first (and only) SSO config row, or None if not configured.
        """
        return SSOConfig.query.first()

    @staticmethod
    def get_or_create():
        """
        Get or create the singleton SSO configuration.

        Returns the SSO config, creating a default one if it doesn't exist.
        """
        config = SSOConfig.get_instance()
        if not config:
            config = SSOConfig(
                provider_type="oidc", is_enabled=False, auto_provision_users=True, default_permissions={}
            )
            db.session.add(config)
            db.session.commit()
        return config
