"""add raw_response_json to linkup_market_value_cache

Revision ID: 003
Revises: 002
Create Date: 2026-03-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "linkup_market_value_cache",
        sa.Column("raw_response_json", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("linkup_market_value_cache", "raw_response_json")
