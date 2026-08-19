"""Stage 12 Phase II. The one new piece of infrastructure everything else in the coach pilot
depends on: a way for an authenticated request to prove (a) the caller is a coach, and (b) that
coach currently has authorized access to a specific singer, optionally scoped to one data
category.

Nothing elsewhere in this codebase reads another user's data — every existing router trusts
`current_user.id` for all reads/writes. `require_coach_access` is the first (and only) place
that changes, and it does so through a single, explicit, testable seam rather than ad hoc
ownership checks scattered across coach endpoints.
"""

import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import CoachAccess, CoachAccessCategoryGrant, CoachProfile, User

NOT_A_COACH = HTTPException(
    status_code=403,
    detail={"code": "not_a_coach", "message": "This account is not a coach account."},
)

COACH_PRO_REQUIRED = HTTPException(
    status_code=403,
    detail={
        "code": "coach_pro_required",
        "message": "This account's Coach Pro subscription is not active.",
    },
)


def get_current_coach(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CoachProfile:
    """SaaS billing (post-Stage-12 Part 2): this is the single enforcement seam for coach_pro --
    every coach endpoint depends on this (directly, or transitively through
    require_coach_access below), so gating here blocks the entire coach surface at once rather
    than requiring each router to check Organization.is_coach_pro_active itself. No free coach
    tier: a freshly signed-up coach's Organization starts with is_coach_pro_active=False (see
    that model's docstring) and stays blocked until an admin activates it via
    POST /api/v1/admin/organizations/{id}/set-coach-pro."""
    coach = db.scalar(select(CoachProfile).where(CoachProfile.user_id == current_user.id))
    if coach is None:
        raise NOT_A_COACH
    if not coach.organization.is_coach_pro_active:
        raise COACH_PRO_REQUIRED
    return coach


def require_coach_access(category: str | None = None) -> Callable[..., CoachAccess]:
    """Dependency factory. The returned dependency resolves the active CoachAccess row for
    (the requesting coach, the `singer_user_id` path parameter on the route it's used on),
    403ing if there is none, it's revoked, or (when `category` is given) that specific category
    isn't currently granted. Every coach-reads-or-acts-on-a-singer endpoint takes this as a
    dependency rather than querying CoachAccess itself."""

    def _dependency(
        singer_user_id: uuid.UUID,
        coach: CoachProfile = Depends(get_current_coach),
        db: Session = Depends(get_db),
    ) -> CoachAccess:
        access = db.scalar(
            select(CoachAccess).where(
                CoachAccess.coach_id == coach.id,
                CoachAccess.singer_user_id == singer_user_id,
                CoachAccess.status == "active",
            )
        )
        if access is None:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "no_active_access",
                    "message": "No active access to this singer.",
                },
            )
        if category is not None:
            grant = db.scalar(
                select(CoachAccessCategoryGrant).where(
                    CoachAccessCategoryGrant.coach_access_id == access.id,
                    CoachAccessCategoryGrant.category == category,
                    CoachAccessCategoryGrant.granted.is_(True),
                )
            )
            if grant is None:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "category_not_shared",
                        "message": f"This singer has not shared '{category}' with you.",
                    },
                )
        return access

    return _dependency
