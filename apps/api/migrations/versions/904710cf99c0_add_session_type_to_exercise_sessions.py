"""add session_type to exercise_sessions

Revision ID: 904710cf99c0
Revises: 5152869643fa
Create Date: 2026-09-28 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '904710cf99c0'
down_revision: str | None = '5152869643fa'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'exercise_sessions',
        sa.Column(
            'session_type', sa.String(length=20), server_default='adaptive', nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column('exercise_sessions', 'session_type')
