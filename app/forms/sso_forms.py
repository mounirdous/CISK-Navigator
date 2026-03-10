"""
SSO Configuration Forms
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, TextAreaField
from wtforms.validators import URL, DataRequired, Length, Optional


class OrganizationSSOConfigForm(FlaskForm):
    """Form for configuring instance-wide SSO settings"""

    provider_type = SelectField(
        "SSO Provider Type",
        choices=[
            ("", "-- Select Provider --"),
            ("oidc", "Generic OIDC/OAuth 2.0"),
            ("google", "Google Workspace"),
            ("azure", "Microsoft Azure AD"),
            ("okta", "Okta"),
        ],
        validators=[DataRequired()],
    )

    is_enabled = BooleanField("Enable SSO", default=False)

    # OIDC Configuration
    client_id = StringField(
        "Client ID",
        validators=[Optional(), Length(max=255)],
        description="OAuth 2.0 Client ID from your identity provider",
    )

    client_secret = TextAreaField(
        "Client Secret",
        validators=[Optional()],
        description="OAuth 2.0 Client Secret (will be encrypted)",
        render_kw={"rows": 3},
    )

    discovery_url = StringField(
        "Discovery URL",
        validators=[Optional(), URL()],
        description="OIDC Discovery URL (e.g., https://accounts.google.com/.well-known/openid-configuration)",
        render_kw={"placeholder": "https://your-idp.com/.well-known/openid-configuration"},
    )

    authorization_endpoint = StringField(
        "Authorization Endpoint (Optional)",
        validators=[Optional(), URL()],
        description="Leave empty to use discovery URL",
        render_kw={"placeholder": "https://your-idp.com/oauth/authorize"},
    )

    token_endpoint = StringField(
        "Token Endpoint (Optional)",
        validators=[Optional(), URL()],
        description="Leave empty to use discovery URL",
        render_kw={"placeholder": "https://your-idp.com/oauth/token"},
    )

    userinfo_endpoint = StringField(
        "UserInfo Endpoint (Optional)",
        validators=[Optional(), URL()],
        description="Leave empty to use discovery URL",
        render_kw={"placeholder": "https://your-idp.com/oauth/userinfo"},
    )

    # User Provisioning
    auto_provision_users = BooleanField(
        "Auto-provision users (JIT)",
        default=True,
        description="Automatically create user accounts on first SSO login",
    )

    # Default Permissions for new users
    default_can_manage_spaces = BooleanField("Can manage spaces", default=False)
    default_can_manage_challenges = BooleanField("Can manage challenges", default=False)
    default_can_manage_initiatives = BooleanField("Can manage initiatives", default=False)
    default_can_manage_systems = BooleanField("Can manage systems", default=False)
    default_can_manage_kpis = BooleanField("Can manage KPIs", default=False)
    default_can_manage_value_types = BooleanField("Can manage value types", default=False)
    default_can_manage_governance_bodies = BooleanField("Can manage governance bodies", default=False)
    default_can_view_comments = BooleanField("Can view comments", default=True)
    default_can_add_comments = BooleanField("Can add comments", default=False)
