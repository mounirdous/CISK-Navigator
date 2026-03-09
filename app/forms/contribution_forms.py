"""Contribution forms"""

from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class ContributionForm(FlaskForm):
    contributor_name = StringField("Contributor Name", validators=[DataRequired(), Length(max=200)])
    numeric_value = DecimalField("Numeric Value", validators=[Optional()])
    qualitative_level = SelectField(
        "Qualitative Level",
        choices=[("", "Select..."), ("1", "Level 1"), ("2", "Level 2"), ("3", "Level 3")],
        coerce=lambda x: int(x) if x else None,
        validators=[Optional()],
    )
    comment = TextAreaField("Comment")
    submit = SubmitField("Save Contribution")
