"""
Forms for action items and memos
"""

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class ActionItemCreateForm(FlaskForm):
    """Form for creating action items or memos"""

    type = SelectField(
        "Type",
        choices=[("memo", "Memo"), ("action", "Action")],
        default="action",
        validators=[DataRequired()],
    )

    title = StringField("Title", validators=[DataRequired(), Length(min=1, max=200)])

    description = TextAreaField("Description", validators=[Optional()])

    # Action-specific fields
    status = SelectField(
        "Status",
        choices=[("draft", "Draft"), ("active", "Active"), ("completed", "Completed"), ("cancelled", "Cancelled")],
        default="active",
        validators=[Optional()],
    )

    priority = SelectField(
        "Priority",
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")],
        default="medium",
        validators=[Optional()],
    )

    due_date = DateField("Due Date", format="%Y-%m-%d", validators=[Optional()])

    owner_user_id = SelectField(
        "Assign To",
        coerce=int,
        validators=[DataRequired()],
    )

    visibility = SelectField(
        "Visibility",
        choices=[("private", "Private (only me)"), ("shared", "Shared (team)")],
        default="shared",
        validators=[DataRequired()],
    )


class ActionItemEditForm(FlaskForm):
    """Form for editing action items or memos"""

    title = StringField("Title", validators=[DataRequired(), Length(min=1, max=200)])

    description = TextAreaField("Description", validators=[Optional()])

    # Action-specific fields
    status = SelectField(
        "Status",
        choices=[("draft", "Draft"), ("active", "Active"), ("completed", "Completed"), ("cancelled", "Cancelled")],
        validators=[Optional()],
    )

    priority = SelectField(
        "Priority",
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")],
        validators=[Optional()],
    )

    due_date = DateField("Due Date", format="%Y-%m-%d", validators=[Optional()])

    owner_user_id = SelectField(
        "Assign To",
        coerce=int,
        validators=[DataRequired()],
    )

    visibility = SelectField(
        "Visibility",
        choices=[("private", "Private (only me)"), ("shared", "Shared (team)")],
        validators=[DataRequired()],
    )


class ActionItemFilterForm(FlaskForm):
    """Form for filtering action items"""

    type_filter = SelectField(
        "Type",
        choices=[("all", "All"), ("memo", "Memos"), ("action", "Actions")],
        default="all",
    )

    status_filter = SelectField(
        "Status",
        choices=[
            ("all", "All"),
            ("draft", "Draft"),
            ("active", "Active"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="all",
    )

    visibility_filter = SelectField(
        "View",
        choices=[("all", "All Items"), ("my_items", "My Items"), ("team_items", "Team Items")],
        default="all",
    )
