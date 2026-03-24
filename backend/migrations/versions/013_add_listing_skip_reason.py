"""add skip_reason column to listings

Revision ID: 013
Revises: 010
Create Date: 2026-03-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column("skip_reason", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("listings", "skip_reason")
