"""add saved and marked_as_build columns to opportunities

Revision ID: 010
Revises: 009
Create Date: 2026-03-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("saved", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "opportunities",
        sa.Column("marked_as_build", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("opportunities", "marked_as_build")
    op.drop_column("opportunities", "saved")
