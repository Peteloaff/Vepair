"""rename user_subscriptions stripe columns to square

Revision ID: f72c4e7d5f35
Revises: 111eef9cd430
Create Date: 2026-09-04 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = 'f72c4e7d5f35'
down_revision: str | None = '111eef9cd430'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # UserSubscription (Stage 5) is laid down but not yet enforced anywhere -- no rows exist,
    # so this is a plain rename, not a data migration. Square replaces Stripe as the payment
    # provider for tighter QuickBooks integration (founder decision) -- see ROADMAP.md.
    op.alter_column(
        'user_subscriptions', 'stripe_customer_id', new_column_name='square_customer_id'
    )
    op.alter_column(
        'user_subscriptions', 'stripe_subscription_id', new_column_name='square_subscription_id'
    )


def downgrade() -> None:
    op.alter_column(
        'user_subscriptions', 'square_customer_id', new_column_name='stripe_customer_id'
    )
    op.alter_column(
        'user_subscriptions', 'square_subscription_id', new_column_name='stripe_subscription_id'
    )
