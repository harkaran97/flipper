"""add display fields to listings and seller evidence to detected_faults

Revision ID: 015
Revises: 014
Create Date: 2026-10-09

Idempotent: ADD COLUMN IF NOT EXISTS only (CLAUDE.md migration rules).
Does not touch the opportunities table.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS image_urls JSON")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS location_town VARCHAR(100)")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS listed_at TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS distance_miles DOUBLE PRECISION")
    op.execute("ALTER TABLE detected_faults ADD COLUMN IF NOT EXISTS evidence TEXT")
    op.execute("ALTER TABLE detected_faults ADD COLUMN IF NOT EXISTS explanation TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE detected_faults DROP COLUMN IF EXISTS explanation")
    op.execute("ALTER TABLE detected_faults DROP COLUMN IF EXISTS evidence")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS distance_miles")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS listed_at")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS location_town")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS image_urls")
