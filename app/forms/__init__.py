"""
WTForms for the application
"""
from .auth_forms import LoginForm, ChangePasswordForm
from .user_forms import UserCreateForm, UserEditForm
from .organization_forms import OrganizationCreateForm, OrganizationEditForm
from .space_forms import SpaceCreateForm, SpaceEditForm
from .challenge_forms import ChallengeCreateForm, ChallengeEditForm
from .initiative_forms import InitiativeCreateForm, InitiativeEditForm
from .system_forms import SystemCreateForm, SystemEditForm
from .kpi_forms import KPICreateForm, KPIEditForm
from .value_type_forms import ValueTypeCreateForm, ValueTypeEditForm
from .contribution_forms import ContributionForm

__all__ = [
    'LoginForm', 'ChangePasswordForm',
    'UserCreateForm', 'UserEditForm',
    'OrganizationCreateForm', 'OrganizationEditForm',
    'SpaceCreateForm', 'SpaceEditForm',
    'ChallengeCreateForm', 'ChallengeEditForm',
    'InitiativeCreateForm', 'InitiativeEditForm',
    'SystemCreateForm', 'SystemEditForm',
    'KPICreateForm', 'KPIEditForm',
    'ValueTypeCreateForm', 'ValueTypeEditForm',
    'ContributionForm',
]
