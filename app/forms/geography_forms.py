"""Geography forms for region/country/site management"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class GeographyRegionForm(FlaskForm):
    """Form for creating/editing geography regions"""

    name = StringField("Region Name", validators=[DataRequired(), Length(max=100)])
    code = StringField(
        "Short Code",
        validators=[Optional(), Length(max=20)],
        description="e.g., EMEA, AMER, APAC",
    )
    display_order = IntegerField("Display Order", default=0)
    submit = SubmitField("Save Region")


class GeographyCountryForm(FlaskForm):
    """Form for creating/editing geography countries"""

    region_id = SelectField("Region", coerce=int, validators=[DataRequired()])
    name = StringField("Country Name", validators=[DataRequired(), Length(max=100)])
    code = StringField(
        "Short Code",
        validators=[Optional(), Length(max=10)],
        description="e.g., FR, DE, ES",
    )
    iso_code = StringField(
        "ISO Code",
        validators=[Optional(), Length(max=3)],
        description="ISO 3166-1 alpha-2/3 code",
    )
    display_order = IntegerField("Display Order", default=0)
    submit = SubmitField("Save Country")


class GeographySiteForm(FlaskForm):
    """Form for creating/editing geography sites"""

    country_id = SelectField("Country", coerce=int, validators=[DataRequired()])
    name = StringField("Site Name", validators=[DataRequired(), Length(max=200)])
    code = StringField(
        "Short Code",
        validators=[Optional(), Length(max=20)],
        description="e.g., PAR-HQ, LYN-OFF",
    )
    address = TextAreaField("Address", validators=[Optional()])
    latitude = DecimalField(
        "Latitude",
        validators=[Optional(), NumberRange(min=-90, max=90)],
        places=8,
        description="Decimal degrees (-90 to 90)",
    )
    longitude = DecimalField(
        "Longitude",
        validators=[Optional(), NumberRange(min=-180, max=180)],
        places=8,
        description="Decimal degrees (-180 to 180)",
    )
    is_active = BooleanField("Active", default=True)
    display_order = IntegerField("Display Order", default=0)
    submit = SubmitField("Save Site")
