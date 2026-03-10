"""Add super admin and system settings

Revision ID: g1a2b3c4d5e6
Revises: a8c4b3e7d2f6
Create Date: 2026-03-10 10:00:00.000000

"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "g1a2b3c4d5e6"
down_revision = "a8c4b3e7d2f6"
branch_labels = None
depends_on = None


def upgrade():
    # Add is_super_admin column to users table
    op.add_column("users", sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default="false"))

    # Create system_settings table
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("value_type", sa.String(length=20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name=op.f("fk_system_settings_updated_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_settings")),
    )
    op.create_index(op.f("ix_system_settings_key"), "system_settings", ["key"], unique=True)

    # Seed initial system settings
    op.execute(
        """
        INSERT INTO system_settings (key, value, value_type, category, description, updated_at)
        VALUES
        ('sso_enabled', 'false', 'boolean', 'authentication', 'Enable Single Sign-On (SSO) authentication system-wide', '%s'),
        ('sso_provider', 'oidc', 'string', 'authentication', 'Default SSO provider type: oidc, saml, or both', '%s'),
        ('sso_auto_provision', 'true', 'boolean', 'authentication', 'Automatically provision users on first SSO login (JIT)', '%s'),
        ('maintenance_mode', 'false', 'boolean', 'system', 'Put system in maintenance mode (read-only)', '%s'),
        ('registration_open', 'false', 'boolean', 'system', 'Allow new user self-registration', '%s'),
        ('session_timeout_seconds', '3600', 'integer', 'security', 'Session timeout in seconds (default 1 hour)', '%s')
    """
        % (
            datetime.utcnow(),
            datetime.utcnow(),
            datetime.utcnow(),
            datetime.utcnow(),
            datetime.utcnow(),
            datetime.utcnow(),
        )
    )


def downgrade():
    # Drop system_settings table
    op.drop_index(op.f("ix_system_settings_key"), table_name="system_settings")
    op.drop_table("system_settings")

    # Drop is_super_admin column from users
    op.drop_column("users", "is_super_admin")
