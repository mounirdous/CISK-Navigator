"""Organization Clone forms"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length


class OrganizationCloneForm(FlaskForm):
    """Form for cloning an organization"""
    new_name = StringField(
        'New Organization Name',
        validators=[
            DataRequired(),
            Length(min=3, max=200, message='Organization name must be between 3 and 200 characters')
        ]
    )

    new_description = TextAreaField(
        'Description',
        validators=[Length(max=1000, message='Description cannot exceed 1000 characters')]
    )

    submit = SubmitField('Clone Organization')
