"""KPI forms"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class KPICreateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    value_type_ids = SelectMultipleField("Value Types", coerce=int, validators=[DataRequired()])
    display_order = IntegerField("Display Order", default=0)
    submit = SubmitField("Create KPI")


class KPIEditForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    display_order = IntegerField("Display Order")
    # Active set of value types attached to this KPI. Validated by the route
    # (must be ≥ 1) rather than DataRequired so the form still validates when
    # the user is mid-edit and momentarily has nothing checked.
    value_type_ids = SelectMultipleField("Value Types", coerce=int)
    submit = SubmitField("Save Changes")
