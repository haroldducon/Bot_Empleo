"""Add optional publication timestamp to jobs.

Revision ID: e19a6846c2d1
Revises: aa801e6e9c71
Create Date: 2026-10-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e19a6846c2d1"
down_revision: Union[str, Sequence[str], None] = "aa801e6e9c71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_published_at", "jobs", ["published_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_published_at", table_name="jobs")
    op.drop_column("jobs", "published_at")
