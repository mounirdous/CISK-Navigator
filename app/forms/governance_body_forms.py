"""
Governance Body forms
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp


class GovernanceBodyCreateForm(FlaskForm):
    """Form for creating a new governance body"""

    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    abbreviation = StringField("Abbreviation", validators=[DataRequired(), Length(max=20)])
    description = TextAreaField("Description", validators=[Optional()])
    color = StringField(
        "Color",
        validators=[DataRequired(), Regexp(r"^#[0-9A-Fa-f]{6}$", message="Must be a valid hex color (#RRGGBB)")],
    )
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Create Governance Body")


class GovernanceBodyEditForm(FlaskForm):
    """Form for editing an existing governance body"""

    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    abbreviation = StringField("Abbreviation", validators=[DataRequired(), Length(max=20)])
    description = TextAreaField("Description", validators=[Optional()])
    color = StringField(
        "Color",
        validators=[DataRequired(), Regexp(r"^#[0-9A-Fa-f]{6}$", message="Must be a valid hex color (#RRGGBB)")],
    )
    is_active = BooleanField("Active")
    submit = SubmitField("Save Changes")
