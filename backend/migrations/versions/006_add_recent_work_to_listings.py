"""add recent_work_json column to listings table

Revision ID: 006
Revises: 005
Create Date: 2026-03-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("recent_work_json", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("listings", "recent_work_json")
