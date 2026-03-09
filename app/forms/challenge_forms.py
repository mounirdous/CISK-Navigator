"""Challenge forms"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class ChallengeCreateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    display_order = IntegerField("Display Order", default=0)
    submit = SubmitField("Create Challenge")


class ChallengeEditForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    display_order = IntegerField("Display Order")
    submit = SubmitField("Save Changes")
