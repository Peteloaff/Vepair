"""Organization teams: several coaches under one clinic or studio.

An organization's coaches each have an org_role -- "admin" (can add coaches, change roles,
deactivate/reactivate) or "member". The organization owns Coach Pro status and the invite
quota, so every coach in it shares both.

A coach's Vrotégés stay that coach's own: a singer consents to one specific coach
(CoachAccess), not to the organization, so neither role can open another coach's singers. The
team view only ever shows a connected-singer *count* per coach.

Functions here don't commit -- callers add their own audit logging first and commit once.
Welcome emails are sent by the caller after the commit, so a failed commit never sends one."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.coach_invites import attach_pending_invites
from app.models import (
    AuthCredential,
    CoachAccess,
    CoachProfile,
    LoginEvent,
    Organization,
    PasswordResetToken,
    User,
)
from app.organizations import invites_used_this_period
from app.schemas_team import OrgRole, TeamMemberOut, TeamOut
from app.security import generate_opaque_token, hash_password

# A new member's set-your-password link outlives the usual one-hour reset link: it arrives in
# an inbox the person may not check for a while.
WELCOME_TOKEN_DAYS = 7


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def team_member_not_found() -> HTTPException:
    return _error(404, "team_member_not_found", "No such member in this organization.")


def _member_status(user: User, has_logged_in: bool) -> str:
    if not user.is_active:
        return "deactivated"
    return "active" if has_logged_in else "invited"


def build_team(db: Session, organization: Organization, my_user_id: uuid.UUID | None) -> TeamOut:
    rows = db.execute(
        select(CoachProfile, User)
        .join(User, User.id == CoachProfile.user_id)
        .where(CoachProfile.organization_id == organization.id)
        .order_by(CoachProfile.created_at, CoachProfile.id)
    ).all()
    coach_ids = [c.id for c, _ in rows]
    user_ids = [u.id for _, u in rows]

    singer_counts = dict(
        db.execute(
            select(CoachAccess.coach_id, func.count())
            .where(CoachAccess.coach_id.in_(coach_ids), CoachAccess.status == "active")
            .group_by(CoachAccess.coach_id)
        ).all()
    )
    logged_in = set(
        db.scalars(select(LoginEvent.user_id).where(LoginEvent.user_id.in_(user_ids)).distinct())
    )

    members = [
        TeamMemberOut(
            coach_id=coach.id,
            user_id=user.id,
            email=user.email,
            display_name=coach.display_name,
            org_role=coach.org_role,
            is_active=user.is_active,
            status=_member_status(user, user.id in logged_in),
            singer_count=singer_counts.get(coach.id, 0),
            is_me=user.id == my_user_id,
        )
        for coach, user in rows
    ]
    my_role: OrgRole = next((m.org_role for m in members if m.is_me), "admin")
    return TeamOut(
        organization_id=organization.id,
        organization_name=organization.name,
        my_role=my_role,
        members=members,
        invite_quota_included=organization.invite_quota_included,
        invites_used_this_period=invites_used_this_period(db, organization),
    )


def issue_welcome_token(db: Session, user: User) -> str:
    """Creates a single-use set-your-password token and returns the raw value for the email.
    Uses the ordinary password-reset machinery (/reset-password), just with a longer life."""
    raw_token, token_hash = generate_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=WELCOME_TOKEN_DAYS),
        )
    )
    return raw_token


def add_member(
    db: Session, organization: Organization, email: str, display_name: str, org_role: OrgRole
) -> tuple[CoachProfile, User, str]:
    """Creates a brand-new account and attaches it to the organization. Returns the coach, the
    user and the raw welcome token. An email that already has an account is refused -- turning
    an existing person (and their data) into a team member is an admin-console job (set-coach),
    not something another organization's admin should be able to do to them."""
    user = User(email=email.lower())
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _error(
            409,
            "email_taken",
            "That email already has a VepAIr account. Ask them to use a different email, or "
            "contact support to add an existing account to your team.",
        ) from None

    # Nobody knows this password: the person sets their own through the emailed link.
    db.add(AuthCredential(user_id=user.id, password_hash=hash_password(secrets.token_urlsafe(32))))
    attach_pending_invites(db, user)
    coach = CoachProfile(
        user_id=user.id,
        display_name=display_name.strip(),
        organization_id=organization.id,
        org_role=org_role,
    )
    db.add(coach)
    db.flush()
    return coach, user, issue_welcome_token(db, user)


def _get_member(db: Session, organization: Organization, coach_id: uuid.UUID) -> CoachProfile:
    coach = db.scalar(
        select(CoachProfile).where(
            CoachProfile.id == coach_id, CoachProfile.organization_id == organization.id
        )
    )
    if coach is None:
        raise team_member_not_found()
    return coach


def _active_admin_count(db: Session, organization: Organization) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(CoachProfile)
            .join(User, User.id == CoachProfile.user_id)
            .where(
                CoachProfile.organization_id == organization.id,
                CoachProfile.org_role == "admin",
                User.is_active.is_(True),
            )
        )
        or 0
    )


def update_member(
    db: Session,
    organization: Organization,
    coach_id: uuid.UUID,
    *,
    acting_user_id: uuid.UUID | None,
    org_role: OrgRole | None = None,
    is_active: bool | None = None,
    display_name: str | None = None,
) -> tuple[CoachProfile, User]:
    coach = _get_member(db, organization, coach_id)
    user = db.get(User, coach.user_id)

    is_active_admin = coach.org_role == "admin" and user.is_active
    loses_admin = (org_role == "member" and coach.org_role == "admin") or is_active is False
    if is_active_admin and loses_admin and _active_admin_count(db, organization) <= 1:
        raise _error(
            409,
            "last_admin",
            "An organization needs at least one active admin. Make someone else an admin first.",
        )
    if is_active is False and acting_user_id is not None and user.id == acting_user_id:
        raise _error(409, "cannot_deactivate_self", "You can't deactivate your own account.")

    if org_role is not None:
        coach.org_role = org_role
    if is_active is not None:
        user.is_active = is_active
    if display_name is not None:
        coach.display_name = display_name.strip()
    return coach, user
