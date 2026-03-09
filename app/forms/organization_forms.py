"""Organization forms"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class OrganizationCreateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Create Organization")


class OrganizationEditForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description")
    is_active = BooleanField("Active")
    submit = SubmitField("Save Changes")
