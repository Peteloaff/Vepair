"""coach invites addressed by email

Lets a coach invite someone who has no account yet: the invite stores the email, and
singer_user_id becomes nullable until that person signs up.

Revision ID: d4a8e6b1f2c3
Revises: c7d2a41e9b08
Create Date: 2026-10-06 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'd4a8e6b1f2c3'
down_revision: str | None = 'c7d2a41e9b08'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('coach_invites', sa.Column('singer_email', sa.String(length=320), nullable=True))
    op.execute(
        "UPDATE coach_invites SET singer_email = lower(users.email) "
        "FROM users WHERE users.id = coach_invites.singer_user_id"
    )
    op.alter_column('coach_invites', 'singer_email', nullable=False)
    op.alter_column('coach_invites', 'singer_user_id', nullable=True)
    op.create_index('ix_coach_invites_singer_email', 'coach_invites', ['singer_email'])


def downgrade() -> None:
    op.execute("DELETE FROM coach_invites WHERE singer_user_id IS NULL")
    op.drop_index('ix_coach_invites_singer_email', table_name='coach_invites')
    op.alter_column('coach_invites', 'singer_user_id', nullable=False)
    op.drop_column('coach_invites', 'singer_email')
