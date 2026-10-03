"""Track completed extraction once per contract version.

Revision ID: 002
Revises: 001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_extractions",
        sa.Column(
            "contract_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="started"),
        sa.Column("ai_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["contract_version_id"],
            ["contract_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("contract_version_id"),
    )


def downgrade() -> None:
    op.drop_table("contract_extractions")
