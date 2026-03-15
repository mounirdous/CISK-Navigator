"""Rename mobile_beta_tester to beta_tester

Revision ID: 2683fafe7d5a
Revises: 551babdaeb39
Create Date: 2026-03-15 22:41:10.870961

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "2683fafe7d5a"
down_revision = "551babdaeb39"
branch_labels = None
depends_on = None


def upgrade():
    # Rename column from mobile_beta_tester to beta_tester
    op.alter_column("users", "mobile_beta_tester", new_column_name="beta_tester")


def downgrade():
    # Rename back from beta_tester to mobile_beta_tester
    op.alter_column("users", "beta_tester", new_column_name="mobile_beta_tester")
