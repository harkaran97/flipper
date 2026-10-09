"""add sold_comp_urls column to market_values

Revision ID: 014
Revises: 013
Create Date: 2026-03-30
"""
from typing import Sequence, Union

from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE market_values ADD COLUMN IF NOT EXISTS sold_comp_urls JSON")


def downgrade() -> None:
    op.drop_column("market_values", "sold_comp_urls")
