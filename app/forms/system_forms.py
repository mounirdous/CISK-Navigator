"""System forms"""

from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class SystemCreateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    initiative_ids = SelectMultipleField("Link to Initiatives", coerce=int)
    submit = SubmitField("Create System")


class SystemEditForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    submit = SubmitField("Save Changes")
