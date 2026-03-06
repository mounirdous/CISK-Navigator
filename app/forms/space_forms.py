"""Space forms"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class SpaceCreateForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    space_label = StringField('Space Label (e.g., Season, Site)', validators=[Optional(), Length(max=100)])
    display_order = IntegerField('Display Order', default=0)
    submit = SubmitField('Create Space')

class SpaceEditForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    space_label = StringField('Space Label', validators=[Optional(), Length(max=100)])
    display_order = IntegerField('Display Order')
    submit = SubmitField('Save Changes')
