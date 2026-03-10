"""Add SSO fields and organization SSO config

Revision ID: h2b3c4d5e6f7
Revises: g1a2b3c4d5e6
Create Date: 2026-03-10 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "h2b3c4d5e6f7"
down_revision = "g1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    # Add SSO fields to users table
    op.add_column("users", sa.Column("sso_provider", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("sso_subject_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("sso_email", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("last_sso_login", sa.DateTime(), nullable=True))

    # Create index on sso_subject_id for fast lookups
    op.create_index(op.f("ix_users_sso_subject_id"), "users", ["sso_subject_id"], unique=False)

    # Make password_hash nullable for SSO-only users
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)

    # Create organization_sso_configs table
    op.create_table(
        "organization_sso_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
        # OIDC Configuration
        sa.Column("client_id", sa.String(length=255), nullable=True),
        sa.Column("client_secret", sa.Text(), nullable=True),
        sa.Column("discovery_url", sa.String(length=500), nullable=True),
        sa.Column("authorization_endpoint", sa.String(length=500), nullable=True),
        sa.Column("token_endpoint", sa.String(length=500), nullable=True),
        sa.Column("userinfo_endpoint", sa.String(length=500), nullable=True),
        sa.Column("jwks_uri", sa.String(length=500), nullable=True),
        # SAML Configuration
        sa.Column("idp_entity_id", sa.String(length=500), nullable=True),
        sa.Column("sso_url", sa.String(length=500), nullable=True),
        sa.Column("x509_cert", sa.Text(), nullable=True),
        # User Provisioning Settings
        sa.Column("email_domains", sa.JSON(), nullable=True),
        sa.Column("auto_provision_users", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("default_permissions", sa.JSON(), nullable=True),
        # Metadata
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_sso_configs_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=op.f("fk_organization_sso_configs_updated_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_sso_configs")),
    )

    # Create indexes
    op.create_index(
        op.f("ix_organization_sso_configs_organization_id"),
        "organization_sso_configs",
        ["organization_id"],
        unique=False,
    )


def downgrade():
    # Drop organization_sso_configs table
    op.drop_index(op.f("ix_organization_sso_configs_organization_id"), table_name="organization_sso_configs")
    op.drop_table("organization_sso_configs")

    # Revert users table changes
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)

    op.drop_index(op.f("ix_users_sso_subject_id"), table_name="users")
    op.drop_column("users", "last_sso_login")
    op.drop_column("users", "sso_email")
    op.drop_column("users", "sso_subject_id")
    op.drop_column("users", "sso_provider")
