"""add mileage, body_type, colour columns to vehicles table

Revision ID: 005
Revises: 004
Create Date: 2026-03-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("mileage", sa.Integer(), nullable=True))
    op.add_column("vehicles", sa.Column("body_type", sa.String(100), nullable=True))
    op.add_column("vehicles", sa.Column("colour", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("vehicles", "colour")
    op.drop_column("vehicles", "body_type")
    op.drop_column("vehicles", "mileage")
