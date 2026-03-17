"""
Email Configuration Forms
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, NumberRange, Optional


class EmailConfigForm(FlaskForm):
    """Form for configuring email/SMTP settings"""

    # SMTP Server Settings
    smtp_host = StringField(
        "SMTP Host",
        validators=[DataRequired()],
        description="e.g., smtp.gmail.com, smtp.sendgrid.net, smtp.mailgun.org",
    )

    smtp_port = IntegerField(
        "SMTP Port",
        validators=[DataRequired(), NumberRange(min=1, max=65535)],
        default=587,
        description="Common ports: 587 (TLS), 465 (SSL), 25 (unencrypted)",
    )

    smtp_username = StringField("SMTP Username", validators=[DataRequired()], description="Your email or SMTP username")

    smtp_password = PasswordField(
        "SMTP Password", validators=[Optional()], description="Leave blank to keep existing password"
    )

    smtp_use_tls = BooleanField(
        "Use TLS (STARTTLS)",
        default=True,
        description="Recommended for port 587 - encrypts connection after initial handshake",
    )

    smtp_use_ssl = BooleanField(
        "Use SSL",
        default=False,
        description="Recommended for port 465 - encrypted from the start (mutually exclusive with TLS)",
    )

    # From Address Settings
    smtp_from_email = StringField(
        "From Email Address", validators=[DataRequired(), Email()], description="Email address that appears as sender"
    )

    smtp_from_name = StringField("From Name", default="CISK Navigator", description="Display name for sender")

    # Email Notification Settings
    enable_mention_notifications = BooleanField("Send Email on @Mentions", default=False)

    enable_action_notifications = BooleanField("Send Email on Action Item Assignment", default=False)

    # Test Email
    test_email = StringField(
        "Test Email Address", validators=[Optional(), Email()], description="Send a test email to verify configuration"
    )

    submit = SubmitField("Save Configuration")
