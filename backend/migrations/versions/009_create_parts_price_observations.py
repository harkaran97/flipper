"""create parts_price_observations table

Revision ID: 009
Revises: 008
Create Date: 2026-03-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parts_price_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("part_name", sa.String(200), nullable=False),
        sa.Column("part_name_normalised", sa.String(200), nullable=False),
        sa.Column("make", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("supplier", sa.String(100), nullable=False),
        sa.Column("condition", sa.String(30), nullable=False),
        sa.Column("base_price_pence", sa.Integer(), nullable=False),
        sa.Column("delivery_pence", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("total_cost_pence", sa.Integer(), nullable=False),
        sa.Column("search_method", sa.String(30), nullable=False),
        sa.Column("ebay_item_url", sa.String(500), nullable=True),
        sa.Column("observed_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # Primary lookup: part + vehicle
    op.create_index(
        "idx_ppo_part_vehicle",
        "parts_price_observations",
        ["part_name_normalised", "make", "model", "year"],
    )

    # Condition-split queries: new vs used
    op.create_index(
        "idx_ppo_condition",
        "parts_price_observations",
        ["part_name_normalised", "make", "model", "year", "condition"],
    )

    # Date range queries: "prices in last 30 days"
    op.create_index(
        "idx_ppo_date",
        "parts_price_observations",
        ["observed_date"],
    )


def downgrade() -> None:
    op.drop_index("idx_ppo_date", table_name="parts_price_observations")
    op.drop_index("idx_ppo_condition", table_name="parts_price_observations")
    op.drop_index("idx_ppo_part_vehicle", table_name="parts_price_observations")
    op.drop_table("parts_price_observations")
