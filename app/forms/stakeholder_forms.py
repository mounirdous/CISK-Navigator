"""Forms for stakeholder mapping."""

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


class StakeholderForm(FlaskForm):
    """Form for creating/editing stakeholders."""

    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    role = StringField("Role/Title", validators=[Optional(), Length(max=200)])
    department = StringField("Department", validators=[Optional(), Length(max=200)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=255)])
    influence_level = IntegerField(
        "Influence Level",
        validators=[DataRequired(), NumberRange(min=1, max=100)],
        default=50,
        description="1 (Low) to 100 (High)",
    )
    interest_level = IntegerField(
        "Interest Level",
        validators=[DataRequired(), NumberRange(min=1, max=100)],
        default=50,
        description="1 (Low) to 100 (High)",
    )
    support_level = SelectField(
        "Support Level",
        choices=[
            ("champion", "Champion - Strong advocate"),
            ("supporter", "Supporter - Positive"),
            ("neutral", "Neutral - Indifferent"),
            ("skeptic", "Skeptic - Doubtful"),
            ("blocker", "Blocker - Opposes"),
        ],
        validators=[DataRequired()],
        default="neutral",
    )
    visibility = SelectField(
        "Visibility",
        choices=[
            ("shared", "Shared - Visible to all organization members"),
            ("private", "Private - Only visible to me"),
        ],
        validators=[DataRequired()],
        default="shared",
    )
    notes = TextAreaField("Notes", validators=[Optional()])


class StakeholderRelationshipForm(FlaskForm):
    """Form for creating/editing relationships between stakeholders."""

    from_stakeholder_id = SelectField("From Stakeholder", coerce=int, validators=[DataRequired()])
    to_stakeholder_id = SelectField("To Stakeholder", coerce=int, validators=[DataRequired()])
    relationship_type = SelectField(
        "Relationship Type",
        choices=[
            ("reports_to", "Reports To"),
            ("influences", "Influences"),
            ("collaborates", "Collaborates With"),
            ("sponsors", "Sponsors"),
            ("blocks", "Blocks"),
        ],
        validators=[DataRequired()],
    )
    strength = IntegerField(
        "Strength",
        validators=[DataRequired(), NumberRange(min=1, max=100)],
        default=50,
        description="1 (Weak) to 100 (Strong)",
    )
    notes = TextAreaField("Notes", validators=[Optional()])


class StakeholderEntityLinkForm(FlaskForm):
    """Form for linking stakeholders to CISK entities."""

    stakeholder_id = SelectField("Stakeholder", coerce=int, validators=[DataRequired()])
    entity_type = SelectField(
        "Entity Type",
        choices=[
            ("space", "Space"),
            ("challenge", "Challenge"),
            ("initiative", "Initiative"),
            ("system", "System"),
            ("kpi", "KPI"),
        ],
        validators=[DataRequired()],
    )
    entity_id = IntegerField("Entity ID", validators=[DataRequired()])
    interest_level = IntegerField(
        "Interest Level",
        validators=[DataRequired(), NumberRange(min=1, max=100)],
        default=50,
        description="How interested is the stakeholder?",
    )
    impact_level = IntegerField(
        "Impact Level",
        validators=[DataRequired(), NumberRange(min=1, max=100)],
        default=50,
        description="How much does this impact the stakeholder?",
    )
    notes = TextAreaField("Notes", validators=[Optional()])


class StakeholderFilterForm(FlaskForm):
    """Form for filtering stakeholders in the network view."""

    department = SelectField("Department", choices=[("", "All Departments")], validators=[Optional()])
    support_level = SelectField(
        "Support Level",
        choices=[
            ("", "All Levels"),
            ("champion", "Champion"),
            ("supporter", "Supporter"),
            ("neutral", "Neutral"),
            ("skeptic", "Skeptic"),
            ("blocker", "Blocker"),
        ],
        validators=[Optional()],
    )
    min_influence = IntegerField("Min Influence", validators=[Optional(), NumberRange(min=1, max=100)], default=1)
    max_influence = IntegerField("Max Influence", validators=[Optional(), NumberRange(min=1, max=100)], default=100)


class StakeholderMapForm(FlaskForm):
    """Form for creating/editing stakeholder maps."""

    name = StringField(
        "Map Name",
        validators=[DataRequired(), Length(max=200)],
        description="E.g., 'Executive Team', 'IT Department', 'Project Sponsors'",
    )
    description = TextAreaField(
        "Description", validators=[Optional()], description="Optional description of this map's purpose"
    )
    visibility = SelectField(
        "Visibility",
        choices=[
            ("shared", "Shared - Visible to all organization members"),
            ("private", "Private - Only visible to me"),
        ],
        validators=[DataRequired()],
        default="shared",
    )
