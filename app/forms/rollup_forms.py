"""Rollup Rule forms"""
from flask_wtf import FlaskForm
from wtforms import SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired


class RollupRuleForm(FlaskForm):
    """Form for configuring a single rollup rule"""
    rollup_enabled = BooleanField('Enable Roll-up')
    formula_override = SelectField('Formula Override', choices=[
        ('default', 'Use Value Type Default'),
        ('sum', 'Sum'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('avg', 'Average')
    ], validators=[DataRequired()])
    submit = SubmitField('Save Rules')
