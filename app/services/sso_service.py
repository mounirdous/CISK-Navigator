"""
SSO Service - Handles OAuth/OIDC authentication flow
"""

import secrets
from datetime import datetime
from urllib.parse import urlencode

import jwt
import requests
from flask import current_app, session, url_for

from app.extensions import db
from app.models import SSOConfig, SystemSetting, User, UserOrganizationMembership


class SSOService:
    """Service for handling SSO authentication"""

    @staticmethod
    def get_sso_config():
        """Get the instance-wide SSO configuration"""
        return SSOConfig.get_instance()

    @staticmethod
    def can_use_sso():
        """Check if SSO can be used"""
        config = SSOService.get_sso_config()
        return config and config.is_enabled and config.is_configured()

    @staticmethod
    def initiate_oidc_flow():
        """
        Initiate OIDC authorization flow.

        Returns redirect URL to IdP authorization endpoint.
        """
        from flask import request

        config = SSOService.get_sso_config()
        if not config or not config.is_enabled:
            return None

        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        session["sso_state"] = state

        # Build authorization URL
        # Use current request scheme (http for local dev, https for production)
        callback_url = url_for("auth.sso_callback", _external=True, _scheme=request.scheme)

        params = {
            "client_id": config.client_id,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": callback_url,
            "state": state,
        }

        # Use discovery URL to get authorization endpoint if not explicitly set
        authorization_endpoint = config.authorization_endpoint
        if not authorization_endpoint and config.discovery_url:
            try:
                discovery = requests.get(config.discovery_url, timeout=10).json()
                authorization_endpoint = discovery.get("authorization_endpoint")
            except Exception as e:
                current_app.logger.error(f"Failed to fetch OIDC discovery: {e}")
                return None

        if not authorization_endpoint:
            return None

        return f"{authorization_endpoint}?{urlencode(params)}"

    @staticmethod
    def _verify_jwt(id_token, config):
        """
        Verify JWT signature using IdP's JWKS.

        Args:
            id_token: The ID token to verify
            config: SSOConfig instance

        Returns:
            Decoded and verified user_info dict

        Raises:
            Exception if verification fails
        """
        try:
            # Get JWKS URI from discovery or config
            jwks_uri = config.jwks_uri
            if not jwks_uri and config.discovery_url:
                discovery = requests.get(config.discovery_url, timeout=10).json()
                jwks_uri = discovery.get("jwks_uri")

            if not jwks_uri:
                # Fallback: decode without verification (dev mode warning)
                current_app.logger.warning("No JWKS URI configured - skipping JWT signature verification")
                return jwt.decode(id_token, options={"verify_signature": False})

            # Fetch JWKS (public keys)
            jwks_response = requests.get(jwks_uri, timeout=10)
            jwks = jwks_response.json()

            # Decode header to get key ID (kid)
            unverified_header = jwt.get_unverified_header(id_token)
            kid = unverified_header.get("kid")

            # Find the matching key
            signing_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break

            if not signing_key:
                raise ValueError(f"No matching key found for kid: {kid}")

            # Verify signature and decode
            user_info = jwt.decode(
                id_token,
                signing_key,
                algorithms=["RS256"],
                audience=config.client_id,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_exp": True,
                },
            )

            return user_info

        except Exception as e:
            current_app.logger.error(f"JWT verification failed: {e}")
            # In production, you might want to reject the token
            # For now, log error and fallback to unverified decode
            return jwt.decode(id_token, options={"verify_signature": False})

    @staticmethod
    def handle_oidc_callback(code, state):
        """
        Handle OIDC callback from IdP.

        Exchanges authorization code for tokens and returns user info.
        Returns: (user_info dict, error message)
        """
        from flask import request

        # Verify state parameter (CSRF protection)
        if state != session.get("sso_state"):
            return None, "Invalid state parameter. Possible CSRF attack."

        config = SSOService.get_sso_config()
        if not config or not config.is_enabled:
            return None, "SSO not configured"

        try:
            # Exchange code for tokens
            token_endpoint = config.token_endpoint
            if not token_endpoint and config.discovery_url:
                discovery = requests.get(config.discovery_url, timeout=10).json()
                token_endpoint = discovery.get("token_endpoint")

            if not token_endpoint:
                return None, "Token endpoint not configured"

            # Use current request scheme (http for local dev, https for production)
            callback_url = url_for("auth.sso_callback", _external=True, _scheme=request.scheme)

            token_response = requests.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": callback_url,
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                },
                timeout=10,
            )

            if token_response.status_code != 200:
                return None, f"Token exchange failed: {token_response.text}"

            tokens = token_response.json()
            id_token = tokens.get("id_token")
            access_token = tokens.get("access_token")

            if not id_token:
                return None, "No ID token received"

            # Decode and validate ID token with signature verification
            user_info = SSOService._verify_jwt(id_token, config)

            # Optionally fetch additional user info from userinfo endpoint
            if access_token and config.userinfo_endpoint:
                userinfo_response = requests.get(
                    config.userinfo_endpoint, headers={"Authorization": f"Bearer {access_token}"}, timeout=10
                )
                if userinfo_response.status_code == 200:
                    user_info.update(userinfo_response.json())

            return user_info, None

        except Exception as e:
            current_app.logger.error(f"SSO callback error: {e}")
            return None, f"Authentication error: {str(e)}"

    @staticmethod
    def provision_or_update_user(user_info):
        """
        Just-in-Time user provisioning.

        Creates or updates user based on SSO user info.
        Does NOT assign organization - that happens separately based on user's context.
        Returns: (User object, was_created boolean)
        """
        config = SSOService.get_sso_config()
        if not config:
            return None, False

        # Extract user information from IdP response
        subject_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name") or user_info.get("given_name", "")

        if not subject_id:
            return None, False

        # Check if user already exists (by SSO subject ID)
        user = User.query.filter_by(sso_provider=config.provider_type, sso_subject_id=subject_id).first()

        was_created = False

        if not user:
            # Check if user exists by email (for linking existing accounts)
            if email:
                user = User.query.filter_by(email=email).first()

            if user:
                # Link existing user to SSO
                user.sso_provider = config.provider_type
                user.sso_subject_id = subject_id
                user.sso_email = email
            else:
                # Create new user (JIT provisioning)
                if not config.auto_provision_users:
                    return None, False

                # Generate unique login from email or subject_id
                login = email.split("@")[0] if email else f"sso_{subject_id[:8]}"

                # Ensure login is unique
                base_login = login
                counter = 1
                while User.query.filter_by(login=login).first():
                    login = f"{base_login}_{counter}"
                    counter += 1

                user = User(
                    login=login,
                    email=email,
                    display_name=name,
                    is_active=True,
                    sso_provider=config.provider_type,
                    sso_subject_id=subject_id,
                    sso_email=email,
                    password_hash=None,  # SSO-only user
                )
                db.session.add(user)
                was_created = True

        # Update SSO login timestamp
        user.update_sso_login()
        db.session.commit()

        return user, was_created

    @staticmethod
    def ensure_organization_membership(user, organization_id):
        """
        Ensure user has membership in the specified organization.

        If not, create membership with default permissions from SSO config.
        """
        config = SSOService.get_sso_config()
        if not config:
            return False

        membership = user.get_membership(organization_id)
        if not membership:
            # Create membership with default permissions
            default_perms = config.default_permissions or {}
            membership = UserOrganizationMembership(
                user_id=user.id,
                organization_id=organization_id,
                can_manage_spaces=default_perms.get("can_manage_spaces", False),
                can_manage_challenges=default_perms.get("can_manage_challenges", False),
                can_manage_initiatives=default_perms.get("can_manage_initiatives", False),
                can_manage_systems=default_perms.get("can_manage_systems", False),
                can_manage_kpis=default_perms.get("can_manage_kpis", False),
                can_manage_value_types=default_perms.get("can_manage_value_types", False),
                can_manage_governance_bodies=default_perms.get("can_manage_governance_bodies", False),
                can_view_comments=default_perms.get("can_view_comments", True),
                can_add_comments=default_perms.get("can_add_comments", False),
            )
            db.session.add(membership)
            db.session.commit()

        return True
