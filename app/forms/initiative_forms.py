"""Initiative forms"""

from flask_wtf import FlaskForm
from wtforms import SelectField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class InitiativeCreateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    group_label = SelectField(
        "Group Label",
        choices=[("", "-- No Group --"), ("A", "Group A"), ("B", "Group B"), ("C", "Group C"), ("D", "Group D")],
        validators=[Optional()],
    )
    challenge_ids = SelectMultipleField("Link to Challenges", coerce=int)
    submit = SubmitField("Create Initiative")


class InitiativeEditForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    group_label = SelectField(
        "Group Label",
        choices=[("", "-- No Group --"), ("A", "Group A"), ("B", "Group B"), ("C", "Group C"), ("D", "Group D")],
        validators=[Optional()],
    )
    submit = SubmitField("Save Changes")
