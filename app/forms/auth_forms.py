"""
Authentication forms
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SubmitField
from wtforms.validators import DataRequired, InputRequired, Length


class LoginForm(FlaskForm):
    """Login form - Step 1: username and password only"""
    login = StringField('Login', validators=[DataRequired(), Length(max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Continue')


class ChangePasswordForm(FlaskForm):
    """Form for changing password"""
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired()])
    submit = SubmitField('Change Password')
