"""coach_profiles.removed_at: remove a coach from an organization's team without deleting history

Revision ID: f6c3a8d1b2e7
Revises: e5b9c2d7a1f4
"""

import sqlalchemy as sa
from alembic import op

revision = "f6c3a8d1b2e7"
down_revision = "e5b9c2d7a1f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "coach_profiles", sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("coach_profiles", "removed_at")
