"""
System Announcement forms
"""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateTimeField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional


class AnnouncementCreateForm(FlaskForm):
    """Form for creating a system announcement"""

    title = StringField(
        "Title", validators=[DataRequired(), Length(max=200)], description="Short, attention-grabbing title"
    )
    message = TextAreaField(
        "Message",
        validators=[DataRequired()],
        description="Full announcement message. You can use **bold** for emphasis and [links](url) for clickable links.",
    )
    banner_type = SelectField(
        "Banner Type",
        choices=[
            ("info", "Info (Blue) - General information"),
            ("success", "Success (Green) - Positive updates"),
            ("warning", "Warning (Yellow) - Important notices"),
            ("alert", "Alert (Red) - Critical/urgent"),
        ],
        default="info",
        validators=[DataRequired()],
    )
    is_dismissible = BooleanField("Allow users to dismiss", default=True)

    target_type = SelectField(
        "Target Audience",
        choices=[
            ("all", "All Users"),
            ("organization", "Specific Organization"),
            ("users", "Specific Users"),
        ],
        default="all",
        validators=[DataRequired()],
    )
    target_organization_id = SelectField("Target Organization", coerce=int, validators=[Optional()])
    target_user_ids = SelectMultipleField("Target Users", coerce=int, validators=[Optional()])

    start_date = DateTimeField("Start Date (optional)", format="%Y-%m-%d %H:%M", validators=[Optional()])
    end_date = DateTimeField("End Date (optional)", format="%Y-%m-%d %H:%M", validators=[Optional()])

    is_active = BooleanField("Active", default=True, description="Uncheck to save as draft")

    submit = SubmitField("Create Announcement")


class AnnouncementEditForm(FlaskForm):
    """Form for editing a system announcement"""

    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    message = TextAreaField("Message", validators=[DataRequired()])
    banner_type = SelectField(
        "Banner Type",
        choices=[
            ("info", "Info (Blue)"),
            ("success", "Success (Green)"),
            ("warning", "Warning (Yellow)"),
            ("alert", "Alert (Red)"),
        ],
        validators=[DataRequired()],
    )
    is_dismissible = BooleanField("Allow users to dismiss")

    target_type = SelectField(
        "Target Audience",
        choices=[
            ("all", "All Users"),
            ("organization", "Specific Organization"),
            ("users", "Specific Users"),
        ],
        validators=[DataRequired()],
    )
    target_organization_id = SelectField("Target Organization", coerce=int, validators=[Optional()])
    target_user_ids = SelectMultipleField("Target Users", coerce=int, validators=[Optional()])

    start_date = DateTimeField("Start Date (optional)", format="%Y-%m-%d %H:%M", validators=[Optional()])
    end_date = DateTimeField("End Date (optional)", format="%Y-%m-%d %H:%M", validators=[Optional()])

    is_active = BooleanField("Active")

    submit = SubmitField("Save Changes")
