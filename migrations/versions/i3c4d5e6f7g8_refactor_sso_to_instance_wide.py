"""Refactor SSO to instance-wide configuration

Revision ID: i3c4d5e6f7g8
Revises: h2b3c4d5e6f7
Create Date: 2026-03-10 08:45:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "i3c4d5e6f7g8"
down_revision = "h2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    # Create instance-wide SSO configuration table
    op.create_table(
        "sso_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("client_id", sa.String(length=255), nullable=True),
        sa.Column("client_secret", sa.Text(), nullable=True),
        sa.Column("discovery_url", sa.String(length=500), nullable=True),
        sa.Column("authorization_endpoint", sa.String(length=500), nullable=True),
        sa.Column("token_endpoint", sa.String(length=500), nullable=True),
        sa.Column("userinfo_endpoint", sa.String(length=500), nullable=True),
        sa.Column("jwks_uri", sa.String(length=500), nullable=True),
        sa.Column("auto_provision_users", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("default_permissions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Drop the old organization-specific SSO config table
    op.drop_table("organization_sso_configs")


def downgrade():
    # Recreate organization_sso_configs table
    op.create_table(
        "organization_sso_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=True),
        sa.Column("client_secret", sa.Text(), nullable=True),
        sa.Column("discovery_url", sa.String(length=500), nullable=True),
        sa.Column("authorization_endpoint", sa.String(length=500), nullable=True),
        sa.Column("token_endpoint", sa.String(length=500), nullable=True),
        sa.Column("userinfo_endpoint", sa.String(length=500), nullable=True),
        sa.Column("jwks_uri", sa.String(length=500), nullable=True),
        sa.Column("email_domains", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("auto_provision_users", sa.Boolean(), nullable=False),
        sa.Column("default_permissions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organization_sso_configs_organization_id", "organization_sso_configs", ["organization_id"], unique=False
    )

    # Drop instance-wide SSO config table
    op.drop_table("sso_config")
