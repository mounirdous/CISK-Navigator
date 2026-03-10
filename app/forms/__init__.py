"""
WTForms for the application
"""

from .auth_forms import ChangePasswordForm, LoginForm, ProfileEditForm
from .challenge_forms import ChallengeCreateForm, ChallengeEditForm
from .contribution_forms import ContributionForm
from .governance_body_forms import GovernanceBodyCreateForm, GovernanceBodyEditForm
from .initiative_forms import InitiativeCreateForm, InitiativeEditForm
from .kpi_forms import KPICreateForm, KPIEditForm
from .organization_clone_forms import OrganizationCloneForm
from .organization_forms import OrganizationCreateForm, OrganizationEditForm
from .space_forms import SpaceCreateForm, SpaceEditForm
from .sso_forms import OrganizationSSOConfigForm
from .system_forms import SystemCreateForm, SystemEditForm
from .user_forms import UserCreateForm, UserEditForm
from .value_type_forms import ValueTypeCreateForm, ValueTypeEditForm
from .yaml_forms import YAMLUploadForm

__all__ = [
    "LoginForm",
    "ChangePasswordForm",
    "ProfileEditForm",
    "UserCreateForm",
    "UserEditForm",
    "OrganizationCreateForm",
    "OrganizationEditForm",
    "SpaceCreateForm",
    "SpaceEditForm",
    "ChallengeCreateForm",
    "ChallengeEditForm",
    "InitiativeCreateForm",
    "InitiativeEditForm",
    "SystemCreateForm",
    "SystemEditForm",
    "KPICreateForm",
    "KPIEditForm",
    "ValueTypeCreateForm",
    "ValueTypeEditForm",
    "GovernanceBodyCreateForm",
    "GovernanceBodyEditForm",
    "ContributionForm",
    "YAMLUploadForm",
    "OrganizationCloneForm",
    "OrganizationSSOConfigForm",
]
