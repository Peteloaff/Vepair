"""activate pending coach organizations

Coach accounts used to wait for a manual admin activation. Every coach is now activated when
the account is created, so this activates the ones that were still waiting -- organizations
that have a coach and were never activated (coach_pro_period_start is still null). An
organization an admin deliberately revoked has a period start, so it is left alone.

Revision ID: c7d2a41e9b08
Revises: b3e1f7a29c54
Create Date: 2026-10-06 18:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = 'c7d2a41e9b08'
down_revision: str | None = 'b3e1f7a29c54'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE organizations
        SET is_coach_pro_active = true,
            coach_pro_period_start = now(),
            coach_pro_period_end = now() + interval '365 days'
        WHERE is_coach_pro_active = false
          AND coach_pro_period_start IS NULL
          AND id IN (SELECT organization_id FROM coach_profiles)
        """
    )


def downgrade() -> None:
    # Not reversible: there is no record of which organizations were activated by this
    # migration rather than by an admin.
    pass
