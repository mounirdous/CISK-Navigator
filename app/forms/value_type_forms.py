"""Value Type forms"""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class ValueTypeCreateForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    kind = SelectField('Kind', choices=[
        ('numeric', 'Numeric'),
        ('risk', 'Risk (!, !!, !!!)'),
        ('positive_impact', 'Impact (★)'),
        ('negative_impact', 'Negative Impact (▼)')
    ], validators=[DataRequired()])
    numeric_format = SelectField('Numeric Format', choices=[
        ('integer', 'Integer'),
        ('decimal', 'Decimal')
    ], validators=[Optional()])
    decimal_places = IntegerField('Decimal Places', default=2)
    unit_label = StringField('Unit Label (e.g., €, tCO2e)', validators=[Optional(), Length(max=50)])
    default_aggregation_formula = SelectField('Default Aggregation Formula', choices=[
        ('sum', 'Sum'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('avg', 'Average'),
        ('median', 'Median'),
        ('count', 'Count')
    ], validators=[DataRequired()])
    display_order = IntegerField('Display Order', default=0)
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Create Value Type')

class ValueTypeEditForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    decimal_places = IntegerField('Decimal Places', validators=[Optional()])
    unit_label = StringField('Unit Label (e.g., €, tCO2e)', validators=[Optional(), Length(max=50)])
    is_active = BooleanField('Active')
    display_order = IntegerField('Display Order')
    submit = SubmitField('Save Changes')
