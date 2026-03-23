"""sync alembic_version table with existing migrations 001-007

Revision ID: 008
Revises: 007
Create Date: 2026-03-23



"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VERSIONS = ["001", "002", "003", "004", "005", "006", "007"]


def upgrade() -> None:
    conn = op.get_bind()
    for version in VERSIONS:
        conn.execute(
            sa.text(
                "INSERT INTO alembic_version (version_num) VALUES (:v) "
                "ON CONFLICT (version_num) DO NOTHING"
            ),
            {"v": version},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM alembic_version WHERE version_num = ANY(:versions)"
        ),
        {"versions": VERSIONS},
    )
