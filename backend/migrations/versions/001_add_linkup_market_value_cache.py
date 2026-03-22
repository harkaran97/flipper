"""add linkup_market_value_cache table

Revision ID: 001
Revises:
Create Date: 2026-03-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "linkup_market_value_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cache_key", sa.String(300), nullable=False, unique=True),
        sa.Column("median_sold_price_gbp", sa.Float(), nullable=False),
        sa.Column("price_range_low_gbp", sa.Float(), nullable=False),
        sa.Column("price_range_high_gbp", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ttl_days", sa.Integer(), nullable=False, server_default="30"),
    )


def downgrade() -> None:
    op.drop_table("linkup_market_value_cache")
