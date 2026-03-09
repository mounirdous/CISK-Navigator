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
    submit = SubmitField("Save Changes")
