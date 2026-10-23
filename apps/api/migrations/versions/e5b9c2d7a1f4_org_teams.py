"""Organization teams: allow several coaches per organization, with an org role

Drops the unique constraint that made an Organization hold exactly one coach, and adds
coach_profiles.org_role. Every existing coach is the sole coach of their own organization, so the
server_default of "admin" is exactly right for the backfill.

Revision ID: e5b9c2d7a1f4
Revises: d4a8e6b1f2c3
"""

import sqlalchemy as sa
from alembic import op

revision = "e5b9c2d7a1f4"
down_revision = "d4a8e6b1f2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "coach_profiles",
        sa.Column("org_role", sa.String(length=20), server_default="admin", nullable=False),
    )
    # Created unnamed in 059761a907fa, so Postgres named it itself.
    op.execute(
        "ALTER TABLE coach_profiles DROP CONSTRAINT IF EXISTS coach_profiles_organization_id_key"
    )
    op.create_index("ix_coach_profiles_organization_id", "coach_profiles", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_coach_profiles_organization_id", table_name="coach_profiles")
    # Only safe while every organization still has at most one coach.
    op.create_unique_constraint(
        "coach_profiles_organization_id_key", "coach_profiles", ["organization_id"]
    )
    op.drop_column("coach_profiles", "org_role")
