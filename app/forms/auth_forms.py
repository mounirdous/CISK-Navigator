"""
Authentication forms
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class LoginForm(FlaskForm):
    """Login form - Step 1: username and password only"""

    login = StringField("Login", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Continue")


class ChangePasswordForm(FlaskForm):
    """Form for changing password"""

    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirm New Password", validators=[DataRequired()])
    submit = SubmitField("Change Password")


class ProfileEditForm(FlaskForm):
    """Form for editing user profile"""

    display_name = StringField("Display Name", validators=[Optional(), Length(max=120)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=120)])
    dark_mode = BooleanField("Dark Mode")
    navbar_position = SelectField(
        "Navigation Bar Position",
        choices=[("top", "Top (Horizontal)"), ("left", "Left Sidebar (Vertical)")],
        validators=[DataRequired()],
    )
    navbar_autohide = BooleanField("Auto-collapse Navigation (icons only, expands on hover)")
    default_organization = SelectField("Default Organization", coerce=int, validators=[Optional()])
    submit = SubmitField("Save Changes")
