"""add feedback requests for bug reports and enhancement requests

Revision ID: d1e2f3g4h5i6
Revises: c0d1e2f3g4h5
Create Date: 2026-04-05
"""
import sqlalchemy as sa
from alembic import op

revision = "d1e2f3g4h5i6"
down_revision = "c0d1e2f3g4h5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "feedback_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False, server_default="bug"),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new"),
        sa.Column("page_url", sa.String(length=500), nullable=True),
        sa.Column("screenshot_data", sa.LargeBinary(), nullable=True),
        sa.Column("screenshot_mime", sa.String(length=50), nullable=True),
        sa.Column("submitted_by_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feedback_requests_type"), "feedback_requests", ["type"])
    op.create_index(op.f("ix_feedback_requests_status"), "feedback_requests", ["status"])
    op.create_index(op.f("ix_feedback_requests_submitted_by_id"), "feedback_requests", ["submitted_by_id"])


def downgrade():
    op.drop_index(op.f("ix_feedback_requests_submitted_by_id"), table_name="feedback_requests")
    op.drop_index(op.f("ix_feedback_requests_status"), table_name="feedback_requests")
    op.drop_index(op.f("ix_feedback_requests_type"), table_name="feedback_requests")
    op.drop_table("feedback_requests")
