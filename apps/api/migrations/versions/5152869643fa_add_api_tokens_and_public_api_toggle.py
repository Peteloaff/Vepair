"""add api_tokens and public_api_enabled site setting

Revision ID: 5152869643fa
Revises: 111eef9cd430
Create Date: 2026-09-04 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '5152869643fa'
down_revision: str | None = '1a08d16d5e0c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'api_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_api_tokens_token_hash'), 'api_tokens', ['token_hash'], unique=True
    )
    op.add_column(
        'site_settings',
        sa.Column(
            'public_api_enabled', sa.Boolean(), server_default='false', nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column('site_settings', 'public_api_enabled')
    op.drop_index(op.f('ix_api_tokens_token_hash'), table_name='api_tokens')
    op.drop_table('api_tokens')
