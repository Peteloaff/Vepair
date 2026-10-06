"""add equipment to exercises

Revision ID: b3e1f7a29c54
Revises: 904710cf99c0
Create Date: 2026-10-06 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b3e1f7a29c54'
down_revision: str | None = '904710cf99c0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('exercises', sa.Column('equipment', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('exercises', 'equipment')
