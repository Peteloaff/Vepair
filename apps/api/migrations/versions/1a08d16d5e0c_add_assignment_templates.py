"""add assignment_templates

Revision ID: 1a08d16d5e0c
Revises: f72c4e7d5f35
Create Date: 2026-09-04 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '1a08d16d5e0c'
down_revision: str | None = '111eef9cd430'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'assignment_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('coach_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('exercise_ids', sa.JSON(), nullable=False),
        sa.Column('note_to_singer', sa.Text(), nullable=True),
        sa.Column('exercise_tone_targets', sa.JSON(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['coach_id'], ['coach_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('assignment_templates')
