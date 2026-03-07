"""YAML Import forms"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField, BooleanField
from wtforms.validators import DataRequired


class YAMLUploadForm(FlaskForm):
    """Form for uploading YAML structure files"""
    yaml_file = FileField(
        'YAML File',
        validators=[
            FileRequired(),
            FileAllowed(['yaml', 'yml'], 'Only YAML files are allowed!')
        ]
    )

    confirm_delete = BooleanField(
        'I understand that ALL existing data for this organization will be DELETED and replaced with the uploaded structure',
        validators=[DataRequired(message='You must confirm that you understand all data will be deleted')]
    )

    submit = SubmitField('Upload and Replace All Data')
