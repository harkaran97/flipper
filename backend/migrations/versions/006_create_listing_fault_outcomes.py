"""create listing_fault_outcomes table

Revision ID: 006
Revises: 005
Create Date: 2026-03-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listing_fault_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=True),
        sa.Column("make", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("mileage", sa.Integer(), nullable=True),
        sa.Column("fuel_type", sa.String(50), nullable=True),
        sa.Column("predicted_fault_type", sa.String(100), nullable=False),
        sa.Column("predicted_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("predicted_severity", sa.String(50), nullable=True),
        sa.Column("ai_overall_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("confirmed", sa.Boolean(), nullable=True),
        sa.Column("actual_fault_type", sa.String(100), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_index("idx_fault_outcomes_make_model", "listing_fault_outcomes", ["make", "model", "year", "mileage"])
    op.create_index("idx_fault_outcomes_fault_type", "listing_fault_outcomes", ["predicted_fault_type"])
    op.create_index("idx_fault_outcomes_confirmed", "listing_fault_outcomes", ["confirmed"])


def downgrade() -> None:
    op.drop_index("idx_fault_outcomes_confirmed", table_name="listing_fault_outcomes")
    op.drop_index("idx_fault_outcomes_fault_type", table_name="listing_fault_outcomes")
    op.drop_index("idx_fault_outcomes_make_model", table_name="listing_fault_outcomes")
    op.drop_table("listing_fault_outcomes")
