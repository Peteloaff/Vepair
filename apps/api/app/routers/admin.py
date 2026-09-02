"""Backend Admin (post-Stage-12). Every state-changing endpoint here is audit-logged via
app.admin_audit.log_admin_action, in the same transaction as the change itself -- see
app/admin_auth.py and app/models.AdminAuditLog for the mechanism this router relies on.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.account_deletion import delete_user_and_storage
from app.admin_audit import log_admin_action
from app.admin_auth import get_current_admin, require_full_admin
from app.auth import create_access_token
from app.config import get_settings
from app.database import get_db
from app.email import send_password_reset_email
from app.models import (
    AuthCredential,
    CoachProfile,
    DailyCheckIn,
    LoginEvent,
    Organization,
    PasswordResetToken,
    Recording,
    RefreshToken,
    User,
    UserProfile,
    VoiceSession,
)
from app.organizations import invites_used_this_period
from app.schemas_admin import (
    AdminBulkResultOut,
    AdminBulkUserIdsIn,
    AdminCreateUserIn,
    AdminImpersonateOut,
    AdminOrganizationOut,
    AdminReportsSummaryOut,
    AdminSetAdminIn,
    AdminSetCoachIn,
    AdminSetCoachProIn,
    AdminSetPasswordIn,
    AdminSiteSettingsIn,
    AdminSiteSettingsOut,
    AdminUserDetailOut,
    AdminUserListItemOut,
)
from app.schemas_auth import UserOut
from app.security import generate_opaque_token, hash_password
from app.site_settings import get_site_settings

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
        admin_role=user.admin_role,
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


@router.post("/users", response_model=AdminUserListItemOut, status_code=201)
def create_user(
    payload: AdminCreateUserIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_full_admin),
) -> AdminUserListItemOut:
    """Admin-authorized account creation, mirroring POST /api/v1/auth/signup and
    /coach-signup but authorized by an admin instead of self-serve -- for support/testing
    accounts, and deliberately exempt from the site-wide signups_enabled lockdown (see
    /site-settings below), since locking down the *public* forms is the whole point of that
    toggle, not locking out the admin who set it. Full-admin-only: this can create a new
    account with is_admin=True, so it's gated the same as granting admin directly."""
    user = User(email=payload.email.lower(), is_admin=payload.is_admin)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": "email_taken", "message": "An account with this email already exists."},
        ) from None

    db.add(AuthCredential(user_id=user.id, password_hash=hash_password(payload.password)))
    if payload.account_type == "coach":
        organization = Organization(name=payload.studio_name)
        db.add(organization)
        db.flush()
        db.add(
            CoachProfile(
                user_id=user.id,
                display_name=payload.display_name,
                organization_id=organization.id,
            )
        )
    log_admin_action(
        db,
        admin.id,
        "create_user",
        user.id,
        {"email": user.email, "account_type": payload.account_type, "is_admin": payload.is_admin},
    )
    db.commit()
    db.refresh(user)
    return _to_list_item(db, user)


@router.get("/users/export")
def export_contact_list(
    email: str | None = Query(default=None),
    account_type: str | None = Query(default=None, pattern="^(singer|coach)$"),
    is_active: bool | None = Query(default=None),
    is_admin: bool | None = Query(default=None),
    onboarding_complete: bool | None = Query(default=None),
    created_after: date | None = Query(default=None),
    created_before: date | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_full_admin),
) -> Response:
    """Contact-list / outreach export -- full-admin-only, and the one action in this entire
    admin surface that hands raw PII out of the system as a downloadable file, so it gets
    hard-delete-level gating. Deliberately minimal fields: email address only -- this app
    keeps no other contact PII (see PRIVACY.md), so there's nothing else to export. Reuses
    query_report's exact filter set (same helper, same semantics) but uncapped rather than
    200-row-limited, since an actual outreach export needs to be complete, not a dashboard
    preview. Logs the filters used, never the resulting rows -- the audit trail records that
    an export happened and under what criteria, not a second copy of the exported emails.

    Registered here (before /users/{user_id} below) deliberately -- FastAPI matches routes in
    registration order, and "/users/export" would otherwise be captured by "/users/{user_id}"
    with "export" failing UUID validation (422) before ever reaching this handler."""
    stmt = _build_user_filter_stmt(
        email=email,
        account_type=account_type,
        is_active=is_active,
        is_admin=is_admin,
        onboarding_complete=onboarding_complete,
        created_after=created_after,
        created_before=created_before,
        limit=100_000,
    )
    emails = db.scalars(stmt.with_only_columns(User.email)).all()

    csv_lines = ["email"] + list(emails)
    csv_body = "\n".join(csv_lines) + "\n"

    log_admin_action(
        db,
        admin.id,
        "export_contact_list",
        None,
        {
            "filters": {
                "email": email,
                "account_type": account_type,
                "is_active": is_active,
                "is_admin": is_admin,
                "onboarding_complete": onboarding_complete,
                "created_after": created_after.isoformat() if created_after else None,
                "created_before": created_before.isoformat() if created_before else None,
            },
            "row_count": len(emails),
        },
    )
    db.commit()

    filename = f"vepair-contacts-{date.today().isoformat()}.csv"
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailOut)
def get_user_detail(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminUserDetailOut:
    user = _get_target(db, user_id)

    last_session_at = db.scalar(
        select(LoginEvent.occurred_at)
        .where(LoginEvent.user_id == user.id)
        .order_by(LoginEvent.occurred_at.desc())
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
    admin: User = Depends(require_full_admin),
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


@router.post("/users/{user_id}/impersonate", response_model=AdminImpersonateOut)
def impersonate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_full_admin),
) -> AdminImpersonateOut:
    """Issues a short-lived (same expiry as a normal access token -- see
    app/auth.py's create_access_token) read-only token that authenticates as the target user.
    Read-only is enforced centrally in app/auth.py's get_current_user, not here -- every
    non-GET request made with this token 403s regardless of which endpoint it hits. Full-admin
    only, and its own distinctly-named audit action (impersonate_start) rather than folded into
    a generic "admin logged in" -- see impersonate_end below for the matching close-out event."""
    if user_id == admin.id:
        raise CANNOT_TARGET_SELF
    user = _get_target(db, user_id)

    token = create_access_token(user.id, impersonated_by=admin.id)
    log_admin_action(db, admin.id, "impersonate_start", user.id, {"email": user.email})
    db.commit()
    return AdminImpersonateOut(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user_email=user.email,
    )


@router.post("/users/{user_id}/impersonate/end", status_code=204)
def end_impersonation(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_full_admin),
) -> None:
    """Called with the *admin's own* token (not the impersonation token) right as the frontend
    switches back from "Viewing as..." to the admin's own session -- an impersonation token
    could never call this itself, since it's a POST and impersonation is read-only. Best-effort
    close-out: the impersonation token expires on its own regardless of whether this is ever
    called (e.g. the browser tab just closes), so a missing impersonate_end is a known,
    acceptable gap, not a security hole -- the read-only enforcement and the short expiry are
    what actually bound the risk, this just keeps the audit trail's start/end pairing clean for
    the common case."""
    user = _get_target(db, user_id)
    log_admin_action(db, admin.id, "impersonate_end", user.id, {"email": user.email})
    db.commit()


@router.post("/users/{user_id}/set-admin", response_model=AdminUserListItemOut)
def set_admin(
    user_id: uuid.UUID,
    payload: AdminSetAdminIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_full_admin),
) -> AdminUserListItemOut:
    """No self-serve signup path ever sets is_admin -- but once at least one admin exists,
    granting or revoking it for *other* accounts through this UI is fine; a manual psql
    UPDATE is only required for the very first admin (see TECHNICAL_GUIDE.md). Blocking
    self-targeting isn't about the grant path being untrusted, it's to stop an admin from
    accidentally revoking their own access with no one left to undo it. Full-admin-only, same
    reasoning as create_user: this can mint another full admin. Setting the tier (full/support)
    is folded into this same endpoint rather than a separate one -- granting admin without a
    tier defaults to "full", matching what is_admin=True has always meant."""
    if user_id == admin.id:
        raise CANNOT_CHANGE_OWN_ADMIN_STATUS
    user = _get_target(db, user_id)

    user.is_admin = payload.is_admin
    user.admin_role = (payload.admin_role or "full") if payload.is_admin else None
    log_admin_action(
        db,
        admin.id,
        "grant_admin" if payload.is_admin else "revoke_admin",
        user.id,
        {"email": user.email, "admin_role": user.admin_role},
    )
    db.commit()
    db.refresh(user)
    return _to_list_item(db, user)


@router.post("/users/{user_id}/set-coach", response_model=AdminUserListItemOut)
def set_coach(
    user_id: uuid.UUID,
    payload: AdminSetCoachIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_full_admin),
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
            organization = Organization()
            db.add(organization)
            db.flush()
            db.add(
                CoachProfile(
                    user_id=user.id,
                    display_name=payload.display_name,
                    organization_id=organization.id,
                )
            )
        elif payload.display_name:
            existing.display_name = payload.display_name
        log_admin_action(db, admin.id, "grant_coach", user.id, {"email": user.email})
    else:
        if existing is not None:
            db.delete(existing)
        log_admin_action(db, admin.id, "revoke_coach", user.id, {"email": user.email})

    db.commit()
    return _to_list_item(db, user)


def _organization_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "organization_not_found", "message": "No such organization."},
    )


def _organization_to_out(db: Session, organization: Organization) -> AdminOrganizationOut:
    coach = db.scalar(
        select(CoachProfile).where(CoachProfile.organization_id == organization.id)
    )
    coach_user = db.get(User, coach.user_id) if coach else None
    return AdminOrganizationOut(
        id=organization.id,
        name=organization.name,
        coach_email=coach_user.email if coach_user else "",
        coach_display_name=coach.display_name if coach else "",
        is_coach_pro_active=organization.is_coach_pro_active,
        coach_pro_period_start=organization.coach_pro_period_start,
        coach_pro_period_end=organization.coach_pro_period_end,
        invite_quota_included=organization.invite_quota_included,
        invites_used_this_period=invites_used_this_period(db, organization),
    )


@router.get("/organizations", response_model=list[AdminOrganizationOut])
def search_organizations(
    query: str | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> list[AdminOrganizationOut]:
    """Search by org name or coach email/display name -- mirrors search_users's shape. One coach
    per organization today (see Organization's docstring), so the join is always 1:1."""
    stmt = (
        select(Organization)
        .join(CoachProfile, CoachProfile.organization_id == Organization.id)
        .join(User, User.id == CoachProfile.user_id)
        .order_by(Organization.created_at.desc())
        .limit(100)
    )
    if query:
        stmt = stmt.where(
            (Organization.name.ilike(f"%{query}%"))
            | (User.email.ilike(f"%{query}%"))
            | (CoachProfile.display_name.ilike(f"%{query}%"))
        )
    orgs = db.scalars(stmt).all()
    return [_organization_to_out(db, o) for o in orgs]


@router.get("/organizations/{organization_id}", response_model=AdminOrganizationOut)
def get_organization_detail(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminOrganizationOut:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise _organization_not_found()
    return _organization_to_out(db, organization)


@router.post("/organizations/{organization_id}/set-coach-pro", response_model=AdminOrganizationOut)
def set_coach_pro(
    organization_id: uuid.UUID,
    payload: AdminSetCoachProIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_full_admin),
) -> AdminOrganizationOut:
    """The manual entitlement-activation action every coach account needs, since coach billing
    goes entirely through QuickBooks (see ROADMAP.md's "QuickBooks Online monthly invoicing
    sync") -- no payment processor reports back into VepAIr automatically, so an admin flips
    this once payment is confirmed outside the app. Same audit-logged shape as
    set_admin/set_coach above. Activating sets a fresh coach_pro_period_start/end (also resets
    the invite quota window, since invites_used_this_period only counts from period_start
    forward); deactivating clears the period end but leaves period_start alone, so past usage
    stays attributable to the period it happened in."""
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise _organization_not_found()

    organization.is_coach_pro_active = payload.is_coach_pro_active
    if payload.is_coach_pro_active:
        organization.coach_pro_period_start = datetime.now(UTC)
        # 30-day months, not calendar months -- no dateutil dependency yet for exact month
        # arithmetic. Fine for v1 (the period only gates invite-quota windowing and the
        # QuickBooks sync's period boundaries, both tolerant of a few days' slack); revisit if
        # exact calendar-month billing periods turn out to matter.
        organization.coach_pro_period_end = datetime.now(UTC) + timedelta(
            days=30 * payload.period_months
        )
    else:
        organization.coach_pro_period_end = datetime.now(UTC)

    log_admin_action(
        db,
        admin.id,
        "set_coach_pro" if payload.is_coach_pro_active else "revoke_coach_pro",
        None,
        {"organization_id": str(organization.id), "organization_name": organization.name},
    )
    db.commit()
    db.refresh(organization)
    return _organization_to_out(db, organization)


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


@router.post("/users/{user_id}/set-password", status_code=204)
def set_password(
    user_id: uuid.UUID,
    payload: AdminSetPasswordIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_full_admin),
) -> None:
    """Sets a user's password directly, for when an admin needs the account usable right away
    rather than waiting on the user to receive and act on a reset email (see
    send_password_reset above, which stays available for the normal case, including for a
    support admin). Same effect as a self-serve password reset otherwise: revokes every active
    session so a stale token from before the change can't keep working. The new password itself
    is never logged -- only the fact that it was changed, and by whom. Full-admin-only: a
    support admin can trigger a reset email, but never sets a password an admin themself now
    knows."""
    user = _get_target(db, user_id)
    credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == user.id))
    if credential is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "no_credential", "message": "This account has no password set."},
        )

    credential.password_hash = hash_password(payload.new_password)
    active_tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    ).all()
    for t in active_tokens:
        t.revoked_at = datetime.now(UTC)

    log_admin_action(db, admin.id, "set_password", user.id, {"email": user.email})
    db.commit()


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


@router.get("/site-settings", response_model=AdminSiteSettingsOut)
def get_site_settings_endpoint(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminSiteSettingsOut:
    settings_row = get_site_settings(db)
    return AdminSiteSettingsOut(
        signups_enabled=settings_row.signups_enabled,
        nda_required=settings_row.nda_required,
        recording_retention_days=settings_row.recording_retention_days,
        checkin_notes_retention_days=settings_row.checkin_notes_retention_days,
        login_event_retention_days=settings_row.login_event_retention_days,
    )


@router.post("/site-settings", response_model=AdminSiteSettingsOut)
def set_site_settings(
    payload: AdminSiteSettingsIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_full_admin),
) -> AdminSiteSettingsOut:
    """Five independent settings sharing one row: signups_enabled is the kill switch for
    the public signup/coach-signup forms (see app/routers/auth.py) -- for locking down new
    accounts during load testing without touching the database by hand, and doesn't affect
    admin-created accounts (POST /users above) or logins for existing accounts. nda_required
    controls whether NdaGate.tsx blocks the authenticated app behind the beta NDA click-through
    -- turn it off once the beta phase ends, no redeploy required. recording_retention_days,
    checkin_notes_retention_days, and login_event_retention_days feed
    app/data_retention.py's daily purge job -- see that module's docstring. All values are sent
    on every call (full replace, not a partial patch), same as the rest of this admin surface."""
    settings_row = get_site_settings(db)
    previous = {
        "signups_enabled": settings_row.signups_enabled,
        "nda_required": settings_row.nda_required,
        "recording_retention_days": settings_row.recording_retention_days,
        "checkin_notes_retention_days": settings_row.checkin_notes_retention_days,
        "login_event_retention_days": settings_row.login_event_retention_days,
    }
    settings_row.signups_enabled = payload.signups_enabled
    settings_row.nda_required = payload.nda_required
    settings_row.recording_retention_days = payload.recording_retention_days
    settings_row.checkin_notes_retention_days = payload.checkin_notes_retention_days
    settings_row.login_event_retention_days = payload.login_event_retention_days
    log_admin_action(
        db,
        admin.id,
        "update_site_settings",
        None,
        {
            "from": previous,
            "to": payload.model_dump(),
        },
    )
    db.commit()
    db.refresh(settings_row)
    return AdminSiteSettingsOut(
        signups_enabled=settings_row.signups_enabled,
        nda_required=settings_row.nda_required,
        recording_retention_days=settings_row.recording_retention_days,
        checkin_notes_retention_days=settings_row.checkin_notes_retention_days,
        login_event_retention_days=settings_row.login_event_retention_days,
    )


def _build_user_filter_stmt(
    *,
    email: str | None,
    account_type: str | None,
    is_active: bool | None,
    is_admin: bool | None,
    onboarding_complete: bool | None,
    created_after: date | None,
    created_before: date | None,
    limit: int,
):
    """Shared filter-building for query_report and export_contact_list -- every filter is
    optional and they combine with AND."""
    stmt = select(User).order_by(User.created_at.desc()).limit(limit)

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
    return stmt


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
    stmt = _build_user_filter_stmt(
        email=email,
        account_type=account_type,
        is_active=is_active,
        is_admin=is_admin,
        onboarding_complete=onboarding_complete,
        created_after=created_after,
        created_before=created_before,
        limit=200,
    )
    users = db.scalars(stmt).all()
    return [_to_list_item(db, u) for u in users]


@router.post("/users/bulk-deactivate", response_model=AdminBulkResultOut)
def bulk_deactivate_users(
    payload: AdminBulkUserIdsIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminBulkResultOut:
    """Bulk scope is deliberately narrow -- deactivate and reactivate only (this endpoint and
    bulk_reactivate_users below), both already fully reversible single-account actions. Bulk
    hard-delete and bulk admin-grant stay single-account and high-friction on purpose; a
    misclick on a multi-select shouldn't be able to do either. Available to a support admin,
    same as the single-account deactivate endpoint. One log_admin_action row per affected user
    -- not one row for the whole batch -- so the audit trail's shape never depends on how many
    accounts were selected at once. Silently skips the caller's own id and any id that doesn't
    resolve to a real user, reporting both back rather than 404ing the whole batch."""
    updated: list[uuid.UUID] = []
    not_found: list[uuid.UUID] = []
    for user_id in payload.user_ids:
        if user_id == admin.id:
            continue
        user = db.get(User, user_id)
        if user is None:
            not_found.append(user_id)
            continue
        user.is_active = False
        active_tokens = db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
            )
        ).all()
        for t in active_tokens:
            t.revoked_at = datetime.now(UTC)
        log_admin_action(db, admin.id, "deactivate_user", user.id, {"email": user.email})
        updated.append(user.id)
    db.commit()
    return AdminBulkResultOut(updated=updated, not_found=not_found)


@router.post("/users/bulk-reactivate", response_model=AdminBulkResultOut)
def bulk_reactivate_users(
    payload: AdminBulkUserIdsIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminBulkResultOut:
    updated: list[uuid.UUID] = []
    not_found: list[uuid.UUID] = []
    for user_id in payload.user_ids:
        user = db.get(User, user_id)
        if user is None:
            not_found.append(user_id)
            continue
        user.is_active = True
        log_admin_action(db, admin.id, "reactivate_user", user.id, {"email": user.email})
        updated.append(user.id)
    db.commit()
    return AdminBulkResultOut(updated=updated, not_found=not_found)


