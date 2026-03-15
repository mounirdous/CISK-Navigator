"""
User management forms
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectMultipleField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class UserCreateForm(FlaskForm):
    """Form for creating a new user"""

    login = StringField("Login", validators=[DataRequired(), Length(max=80)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=120)])
    display_name = StringField("Display Name", validators=[Optional(), Length(max=120)])
    password = PasswordField("Temporary Password", validators=[DataRequired(), Length(min=8)])
    is_active = BooleanField("Active", default=True)
    is_global_admin = BooleanField("Instance Administrator")
    is_super_admin = BooleanField("Super Administrator (System-wide)")
    beta_tester = BooleanField("Enable Beta Testing")
    organizations = SelectMultipleField("Assigned Organizations", coerce=int)
    submit = SubmitField("Create User")


class UserEditForm(FlaskForm):
    """Form for editing an existing user"""

    login = StringField("Login", validators=[DataRequired(), Length(max=80)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=120)])
    display_name = StringField("Display Name", validators=[Optional(), Length(max=120)])
    is_active = BooleanField("Active")
    is_global_admin = BooleanField("Instance Administrator")
    is_super_admin = BooleanField("Super Administrator (System-wide)")
    must_change_password = BooleanField("Force Password Change on Next Login")
    beta_tester = BooleanField("Enable Beta Testing")
    organizations = SelectMultipleField("Assigned Organizations", coerce=int)
    reset_password = PasswordField(
        "Reset Password (leave blank to keep current)", validators=[Optional(), Length(min=8)]
    )
    submit = SubmitField("Save Changes")
