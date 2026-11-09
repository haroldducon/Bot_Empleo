"""Add optional profile avatar blob.

Revision ID: f4a82c6d91b0
Revises: e19a6846c2d1
Create Date: 2026-10-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4a82c6d91b0"
down_revision: Union[str, Sequence[str], None] = "e19a6846c2d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column("avatar_data", sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("profiles", "avatar_data")
