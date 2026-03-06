"""Initiative forms"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length

class InitiativeCreateForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    challenge_ids = SelectMultipleField('Link to Challenges', coerce=int)
    submit = SubmitField('Create Initiative')

class InitiativeEditForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    submit = SubmitField('Save Changes')
