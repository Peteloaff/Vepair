"""Backend Admin (post-Stage-12). Every state-changing endpoint here is audit-logged via
app.admin_audit.log_admin_action, in the same transaction as the change itself -- see
app/admin_auth.py and app/models.AdminAuditLog for the mechanism this router relies on.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.account_deletion import delete_user_and_storage
from app.admin_audit import log_admin_action
from app.admin_auth import get_current_admin
from app.config import get_settings
from app.database import get_db
from app.email import send_password_reset_email
from app.models import (
    CoachProfile,
    DailyCheckIn,
    PasswordResetToken,
    Recording,
    RefreshToken,
    User,
    UserProfile,
    VoiceSession,
)
from app.schemas_admin import (
    AdminReportsSummaryOut,
    AdminSetAdminIn,
    AdminSetCoachIn,
    AdminUserDetailOut,
    AdminUserListItemOut,
)
from app.schemas_auth import UserOut
from app.security import generate_opaque_token

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
settings = get_settings()

CANNOT_TARGET_SELF = HTTPException(
    status_code=400,
    detail={
        "code": "cannot_target_self",
        "message": "An admin cannot deactivate or delete their own account.",
    },
)

CANNOT_CHANGE_OWN_ADMIN_STATUS = HTTPException(
    status_code=400,
    detail={
        "code": "cannot_target_self",
        "message": "An admin cannot change their own admin status.",
    },
)


def _user_not_found() -> HTTPException:
    return HTTPException(
        status_code=404, detail={"code": "user_not_found", "message": "No such user."}
    )


def _get_target(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise _user_not_found()
    return user


def _account_type(db: Session, user_id: uuid.UUID) -> str:
    is_coach = db.scalar(select(CoachProfile.id).where(CoachProfile.user_id == user_id))
    return "coach" if is_coach is not None else "singer"


def _onboarding_complete(db: Session, user_id: uuid.UUID) -> bool:
    return db.scalar(select(UserProfile.id).where(UserProfile.user_id == user_id)) is not None


def _to_list_item(db: Session, user: User) -> AdminUserListItemOut:
    return AdminUserListItemOut(
        id=user.id,
        email=user.email,
        account_type=_account_type(db, user.id),
        created_at=user.created_at,
        is_active=user.is_active,
        is_admin=user.is_admin,
        onboarding_complete=_onboarding_complete(db, user.id),
    )


@router.get("/profile", response_model=UserOut)
def get_admin_profile(admin: User = Depends(get_current_admin)) -> User:
    """Lightweight "am I an admin" check for RequireAdmin.tsx, mirroring GET
    /api/v1/coach/profile's role in RequireCoach.tsx -- server-truth, never a client-trusted
    flag."""
    return admin


@router.get("/users", response_model=list[AdminUserListItemOut])
def search_users(
    query: str | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> list[AdminUserListItemOut]:
    stmt = select(User).order_by(User.created_at.desc()).limit(100)
    if query:
        stmt = stmt.where(User.email.ilike(f"%{query}%"))
    users = db.scalars(stmt).all()
    return [_to_list_item(db, u) for u in users]


@router.get("/users/{user_id}", response_model=AdminUserDetailOut)
def get_user_detail(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminUserDetailOut:
    user = _get_target(db, user_id)

    last_session_at = db.scalar(
        select(RefreshToken.created_at)
        .where(RefreshToken.user_id == user.id)
        .order_by(RefreshToken.created_at.desc())
        .limit(1)
    )
    last_checkin_date = db.scalar(
        select(DailyCheckIn.checkin_date)
        .where(DailyCheckIn.user_id == user.id)
        .order_by(DailyCheckIn.checkin_date.desc())
        .limit(1)
    )
    last_recording_at = db.scalar(
        select(Recording.created_at)
        .join(VoiceSession)
        .where(VoiceSession.user_id == user.id)
        .order_by(Recording.created_at.desc())
        .limit(1)
    )

    base = _to_list_item(db, user)
    return AdminUserDetailOut(
        **base.model_dump(),
        last_session_at=last_session_at,
        last_checkin_date=last_checkin_date,
        last_recording_at=last_recording_at,
    )


@router.post("/users/{user_id}/deactivate", response_model=AdminUserListItemOut)
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminUserListItemOut:
    if user_id == admin.id:
        raise CANNOT_TARGET_SELF
    user = _get_target(db, user_id)

    user.is_active = False
    active_tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    ).all()
    for t in active_tokens:
        t.revoked_at = datetime.now(UTC)

    log_admin_action(db, admin.id, "deactivate_user", user.id, {"email": user.email})
    db.commit()
    db.refresh(user)
    return _to_list_item(db, user)


@router.post("/users/{user_id}/reactivate", response_model=AdminUserListItemOut)
def reactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminUserListItemOut:
    user = _get_target(db, user_id)

    user.is_active = True
    log_admin_action(db, admin.id, "reactivate_user", user.id, {"email": user.email})
    db.commit()
    db.refresh(user)
    return _to_list_item(db, user)


@router.post("/users/{user_id}/delete", status_code=204)
def hard_delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> None:
    if user_id == admin.id:
        raise CANNOT_TARGET_SELF
    user = _get_target(db, user_id)

    if user.is_active:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "must_deactivate_first",
                "message": "The account must be deactivated before it can be permanently deleted.",
            },
        )

    log_admin_action(db, admin.id, "hard_delete_user", user.id, {"email": user.email})
    delete_user_and_storage(db, user)


@router.post("/users/{user_id}/set-admin", response_model=AdminUserListItemOut)
def set_admin(
    user_id: uuid.UUID,
    payload: AdminSetAdminIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminUserListItemOut:
    """No self-serve signup path ever sets is_admin -- but once at least one admin exists,
    granting or revoking it for *other* accounts through this UI is fine; a manual psql
    UPDATE is only required for the very first admin (see TECHNICAL_GUIDE.md). Blocking
    self-targeting isn't about the grant path being untrusted, it's to stop an admin from
    accidentally revoking their own access with no one left to undo it."""
    if user_id == admin.id:
        raise CANNOT_CHANGE_OWN_ADMIN_STATUS
    user = _get_target(db, user_id)

    user.is_admin = payload.is_admin
    log_admin_action(
        db,
        admin.id,
        "grant_admin" if payload.is_admin else "revoke_admin",
        user.id,
        {"email": user.email},
    )
    db.commit()
    db.refresh(user)
    return _to_list_item(db, user)


@router.post("/users/{user_id}/set-coach", response_model=AdminUserListItemOut)
def set_coach(
    user_id: uuid.UUID,
    payload: AdminSetCoachIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminUserListItemOut:
    """Lets a singer account also become a coach (or a coach-only account also be a singer --
    same mechanism, just starting from the other side) by attaching/detaching a CoachProfile
    on an *existing* account, something no self-serve flow does -- coach-signup only ever
    creates a coach account from scratch (see CoachSignupRequest's docstring). The frontend
    home page renders the full singer dashboard whenever a UserProfile exists, regardless of
    CoachProfile, so a dual-role account keeps both; only an account with a CoachProfile and
    no UserProfile at all gets the compact coach-only view.

    Removing coach status deletes the CoachProfile row, which cascades to every Exercise this
    coach authored (Exercise.created_by_coach_id is ON DELETE CASCADE) -- including ones
    already sitting in other singers' routines. That's a real, sharp consequence, not an
    oversight; the frontend confirms this explicitly before calling here with is_coach=False."""
    user = _get_target(db, user_id)
    existing = db.scalar(select(CoachProfile).where(CoachProfile.user_id == user.id))

    if payload.is_coach:
        if existing is None:
            if not payload.display_name:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "display_name_required",
                        "message": "A display name is required to make this account a coach.",
                    },
                )
            db.add(CoachProfile(user_id=user.id, display_name=payload.display_name))
        elif payload.display_name:
            existing.display_name = payload.display_name
        log_admin_action(db, admin.id, "grant_coach", user.id, {"email": user.email})
    else:
        if existing is not None:
            db.delete(existing)
        log_admin_action(db, admin.id, "revoke_coach", user.id, {"email": user.email})

    db.commit()
    return _to_list_item(db, user)


@router.post("/users/{user_id}/send-password-reset", status_code=202)
def send_password_reset(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> None:
    """Thin, admin-authorized wrapper around the same PasswordResetToken + email mechanism
    POST /api/v1/auth/password-reset/request already uses -- see that endpoint. No new password
    logic; the only real gap this closes is triggering it on someone else's behalf, audited."""
    user = _get_target(db, user_id)

    raw_token, token_hash = generate_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC)
            + timedelta(minutes=settings.password_reset_token_expire_minutes),
        )
    )
    log_admin_action(db, admin.id, "send_password_reset", user.id, {"email": user.email})
    db.commit()
    send_password_reset_email(user.email, raw_token)


@router.get("/reports/summary", response_model=AdminReportsSummaryOut)
def reports_summary(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminReportsSummaryOut:
    now = datetime.now(UTC)

    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    coach_count = db.scalar(select(func.count()).select_from(CoachProfile)) or 0
    singer_count = total_users - coach_count
    active_count = db.scalar(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    ) or 0
    deactivated_count = total_users - active_count
    onboarded_count = db.scalar(select(func.count()).select_from(UserProfile)) or 0
    onboarding_completion_rate = (onboarded_count / total_users) if total_users else 0.0

    signups_7d = db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.created_at >= now - timedelta(days=7))
    ) or 0
    signups_90d = db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.created_at >= now - timedelta(days=90))
    ) or 0

    def _active_user_count(since: datetime) -> int:
        checkin_users = select(DailyCheckIn.user_id).where(DailyCheckIn.created_at >= since)
        recording_users = (
            select(VoiceSession.user_id)
            .join(Recording)
            .where(Recording.created_at >= since)
        )
        combined = checkin_users.union(recording_users).subquery()
        return db.scalar(select(func.count()).select_from(combined)) or 0

    dau = _active_user_count(now - timedelta(days=1))
    wau = _active_user_count(now - timedelta(days=7))

    return AdminReportsSummaryOut(
        total_users=total_users,
        singer_count=singer_count,
        coach_count=coach_count,
        active_count=active_count,
        deactivated_count=deactivated_count,
        onboarding_completion_rate=round(onboarding_completion_rate, 4),
        signups_last_7_days=signups_7d,
        signups_last_90_days=signups_90d,
        dau=dau,
        wau=wau,
    )


@router.get("/reports/query", response_model=list[AdminUserListItemOut])
def query_report(
    email: str | None = Query(default=None),
    account_type: str | None = Query(default=None, pattern="^(singer|coach)$"),
    is_active: bool | None = Query(default=None),
    is_admin: bool | None = Query(default=None),
    onboarding_complete: bool | None = Query(default=None),
    created_after: date | None = Query(default=None),
    created_before: date | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> list[AdminUserListItemOut]:
    """A filter-built report over the same fields the rest of /admin already exposes per
    account -- every filter is optional and they combine with AND. Capped at 200 rows, same
    reasoning as search_users's 100-row cap: this is an operator tool for a founder-scale
    user base, not a paginated export."""
    stmt = select(User).order_by(User.created_at.desc()).limit(200)

    if email:
        stmt = stmt.where(User.email.ilike(f"%{email}%"))
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    if is_admin is not None:
        stmt = stmt.where(User.is_admin.is_(is_admin))
    if created_after is not None:
        stmt = stmt.where(User.created_at >= created_after)
    if created_before is not None:
        stmt = stmt.where(User.created_at < created_before + timedelta(days=1))
    if account_type == "coach":
        stmt = stmt.where(User.id.in_(select(CoachProfile.user_id)))
    elif account_type == "singer":
        stmt = stmt.where(User.id.not_in(select(CoachProfile.user_id)))
    if onboarding_complete is True:
        stmt = stmt.where(User.id.in_(select(UserProfile.user_id)))
    elif onboarding_complete is False:
        stmt = stmt.where(User.id.not_in(select(UserProfile.user_id)))

    users = db.scalars(stmt).all()
    return [_to_list_item(db, u) for u in users]
