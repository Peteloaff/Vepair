"""add_organizations_and_saas_billing_tables

Revision ID: 059761a907fa
Revises: 2c9e63f37bd8
Create Date: 2026-08-19 13:55:51.911508

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '059761a907fa'
down_revision: str | None = '2c9e63f37bd8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('organizations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=True),
    sa.Column('is_coach_pro_active', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('coach_pro_period_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('coach_pro_period_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('invite_quota_included', sa.Integer(), server_default='50', nullable=False),
    sa.Column('quickbooks_customer_id', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('organization_invoice_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
    sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
    sa.Column('quickbooks_invoice_id', sa.String(length=100), nullable=True),
    sa.Column('invite_overage_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_subscriptions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('tier', sa.String(length=20), server_default='free', nullable=False),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('stripe_customer_id', sa.String(length=100), nullable=True),
    sa.Column('stripe_subscription_id', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )

    # organization_id starts nullable so existing coach_profiles rows (if any) can be backfilled
    # with a real Organization row each -- one coach = one org, formalizing the old studio_name
    # label into the new entity. Tightened to NOT NULL only after the backfill below.
    op.add_column('coach_profiles', sa.Column('organization_id', sa.UUID(), nullable=True))

    # One Organization per existing CoachProfile, carrying over the old studio_name as the new
    # org's name. `mapping` pre-generates each org's id once (a plain SELECT CTE is materialized
    # once and reused by both the INSERT and the UPDATE below, so the same id lands in both
    # places) -- the standard Postgres idiom for backfilling a new 1:1 parent per existing row.
    op.execute(
        """
        WITH mapping AS (
            SELECT id AS coach_profile_id, studio_name, gen_random_uuid() AS org_id
            FROM coach_profiles
        ),
        inserted AS (
            INSERT INTO organizations (id, name, is_coach_pro_active, invite_quota_included, created_at, updated_at)
            SELECT org_id, studio_name, false, 50, now(), now()
            FROM mapping
        )
        UPDATE coach_profiles cp
        SET organization_id = mapping.org_id
        FROM mapping
        WHERE cp.id = mapping.coach_profile_id
        """
    )

    op.alter_column('coach_profiles', 'organization_id', nullable=False)
    op.create_unique_constraint(None, 'coach_profiles', ['organization_id'])
    op.create_foreign_key(None, 'coach_profiles', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.drop_column('coach_profiles', 'studio_name')


def downgrade() -> None:
    op.add_column('coach_profiles', sa.Column('studio_name', sa.VARCHAR(length=200), autoincrement=False, nullable=True))
    op.execute(
        """
        UPDATE coach_profiles cp
        SET studio_name = o.name
        FROM organizations o
        WHERE cp.organization_id = o.id
        """
    )
    op.drop_constraint(None, 'coach_profiles', type_='foreignkey')
    op.drop_constraint(None, 'coach_profiles', type_='unique')
    op.drop_column('coach_profiles', 'organization_id')
    op.drop_table('user_subscriptions')
    op.drop_table('organization_invoice_logs')
    op.drop_table('organizations')
