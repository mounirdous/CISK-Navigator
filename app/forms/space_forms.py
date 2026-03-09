"""Space forms"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class SpaceCreateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    space_label = StringField("Space Label (e.g., Season, Site)", validators=[Optional(), Length(max=100)])
    display_order = IntegerField("Display Order", default=0)
    is_private = BooleanField("Private Space")
    submit = SubmitField("Create Space")


class SpaceEditForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    space_label = StringField("Space Label", validators=[Optional(), Length(max=100)])
    display_order = IntegerField("Display Order")
    is_private = BooleanField("Private Space")
    submit = SubmitField("Save Changes")
