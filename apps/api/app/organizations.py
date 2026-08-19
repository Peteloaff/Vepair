"""SaaS billing, coach side (post-Stage-12 Part 2). Helpers for app.models.Organization --
the entity that owns coach_pro billing state and the invite quota. See that model's docstring
for the full design rationale.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CoachInvite, CoachProfile, Organization


def invites_used_this_period(db: Session, organization: Organization) -> int:
    """Live count, not a maintained counter -- avoids the drift risk of keeping a running total
    in sync with every CoachInvite accept/decline/revoke transition. Counts invites sent by any
    coach in this organization (today, always exactly one) since coach_pro_period_start, that
    aren't declined or revoked -- a declined/revoked invite frees its unit back up rather than
    permanently consuming it (see ROADMAP.md's "Coach organizations & invite quota" section).
    Returns 0 for an organization with no active period (nothing to count against yet)."""
    if organization.coach_pro_period_start is None:
        return 0

    return (
        db.scalar(
            select(func.count())
            .select_from(CoachInvite)
            .join(CoachProfile, CoachProfile.id == CoachInvite.coach_id)
            .where(
                CoachProfile.organization_id == organization.id,
                CoachInvite.status.not_in(("declined", "revoked")),
                CoachInvite.created_at >= organization.coach_pro_period_start,
            )
        )
        or 0
    )
