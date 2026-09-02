import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.coach_notes import find_flagged_terms
from app.database import get_db
from app.email import send_new_message_email
from app.models import (
    CoachAccess,
    CoachAccessCategoryGrant,
    CoachInvite,
    CoachMessage,
    CoachNote,
    CoachProfile,
    ConsentRecord,
    User,
)
from app.notifications import has_notifications_consent
from app.schemas_coach import (
    COACH_SHARE_CATEGORIES,
    CategoryToggleIn,
    CoachConnectionOut,
    CoachMessageCreate,
    CoachMessageOut,
    CoachNoteOut,
    InviteAcceptIn,
    SingerInviteOut,
)

router = APIRouter(prefix="/api/v1", tags=["coach-access"])


def _pending_invite_for_singer(
    db: Session, invite_id: uuid.UUID, singer_user_id: uuid.UUID
) -> CoachInvite:
    invite = db.scalar(
        select(CoachInvite).where(
            CoachInvite.id == invite_id, CoachInvite.singer_user_id == singer_user_id
        )
    )
    if invite is None:
        raise HTTPException(
            status_code=404, detail={"code": "invite_not_found", "message": "Invite not found."}
        )
    if invite.status != "pending":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "invite_not_pending",
                "message": "This invite has already been responded to.",
            },
        )
    return invite


@router.get("/invites", response_model=list[SingerInviteOut])
def list_my_invites(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SingerInviteOut]:
    rows = db.execute(
        select(CoachInvite, CoachProfile)
        .join(CoachProfile, CoachProfile.id == CoachInvite.coach_id)
        .where(CoachInvite.singer_user_id == current_user.id, CoachInvite.status == "pending")
        .order_by(CoachInvite.created_at.desc())
    ).all()
    return [
        SingerInviteOut(
            id=invite.id,
            coach_display_name=coach.display_name,
            coach_studio_name=coach.studio_name,
            message=invite.message,
            created_at=invite.created_at,
        )
        for invite, coach in rows
    ]


@router.post("/invites/{invite_id}/accept", response_model=CoachConnectionOut)
def accept_invite(
    invite_id: uuid.UUID,
    payload: InviteAcceptIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoachConnectionOut:
    invite = _pending_invite_for_singer(db, invite_id, current_user.id)

    invalid = set(payload.granted_categories) - COACH_SHARE_CATEGORIES
    if invalid:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_category",
                "message": f"Unknown categories: {sorted(invalid)}",
            },
        )

    existing_active = db.scalar(
        select(CoachAccess).where(
            CoachAccess.singer_user_id == current_user.id, CoachAccess.status == "active"
        )
    )
    if existing_active is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "already_has_active_coach",
                "message": (
                    "You already have an active coach connection — revoke it before "
                    "accepting a new invite."
                ),
            },
        )

    now = datetime.now(UTC)
    invite.status = "accepted"
    invite.responded_at = now

    access = CoachAccess(
        coach_id=invite.coach_id,
        singer_user_id=current_user.id,
        invite_id=invite.id,
        granted_at=now,
    )
    db.add(access)
    db.flush()

    for category in payload.granted_categories:
        db.add(
            CoachAccessCategoryGrant(coach_access_id=access.id, category=category, granted=True)
        )
        # Audit trail (PRIVACY.md "auditable access") — CoachAccessCategoryGrant above is what
        # authorization checks actually query; this row is never read at request time.
        db.add(
            ConsentRecord(
                user_id=current_user.id,
                consent_type="coach_sharing",
                category=category,
                granted=True,
                granted_at=func.clock_timestamp(),
                clinician_id=invite.coach_id,
            )
        )

    db.commit()
    db.refresh(access)

    coach = db.get(CoachProfile, access.coach_id)
    return CoachConnectionOut(
        id=access.id,
        coach_display_name=coach.display_name,
        coach_studio_name=coach.studio_name,
        status=access.status,
        granted_categories=payload.granted_categories,
        granted_at=access.granted_at,
        revoked_at=access.revoked_at,
    )


@router.post("/invites/{invite_id}/decline", status_code=204)
def decline_invite(
    invite_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    invite = _pending_invite_for_singer(db, invite_id, current_user.id)
    invite.status = "declined"
    invite.responded_at = datetime.now(UTC)
    db.commit()


@router.get("/coach-connections", response_model=list[CoachConnectionOut])
def list_my_coach_connections(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[CoachConnectionOut]:
    accesses = db.scalars(
        select(CoachAccess)
        .where(CoachAccess.singer_user_id == current_user.id)
        .order_by(CoachAccess.granted_at.desc())
    ).all()
    result = []
    for access in accesses:
        coach = db.get(CoachProfile, access.coach_id)
        grants = db.scalars(
            select(CoachAccessCategoryGrant).where(
                CoachAccessCategoryGrant.coach_access_id == access.id,
                CoachAccessCategoryGrant.granted.is_(True),
            )
        ).all()
        result.append(
            CoachConnectionOut(
                id=access.id,
                coach_display_name=coach.display_name,
                coach_studio_name=coach.studio_name,
                status=access.status,
                granted_categories=[g.category for g in grants],
                granted_at=access.granted_at,
                revoked_at=access.revoked_at,
                unread_message_count=_unread_message_count(db, access.id, from_sender="coach"),
            )
        )
    return result


def _unread_message_count(db: Session, coach_access_id: uuid.UUID, *, from_sender: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(CoachMessage)
        .where(
            CoachMessage.coach_access_id == coach_access_id,
            CoachMessage.sender == from_sender,
            CoachMessage.read_at.is_(None),
        )
    )


def _owned_access(
    db: Session, coach_access_id: uuid.UUID, singer_user_id: uuid.UUID
) -> CoachAccess:
    access = db.scalar(
        select(CoachAccess).where(
            CoachAccess.id == coach_access_id, CoachAccess.singer_user_id == singer_user_id
        )
    )
    if access is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "connection_not_found", "message": "Coach connection not found."},
        )
    return access


@router.patch("/coach-connections/{coach_access_id}/categories", response_model=CoachConnectionOut)
def toggle_category(
    coach_access_id: uuid.UUID,
    payload: CategoryToggleIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoachConnectionOut:
    """Separate and lighter-weight than full revoke — turning one category off never touches
    CoachAccess.status or any other category's grant. This is what makes consent genuinely
    per-category rather than all-or-nothing."""
    if payload.category not in COACH_SHARE_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_category",
                "message": f"Unknown category: {payload.category}",
            },
        )
    access = _owned_access(db, coach_access_id, current_user.id)

    grant = db.scalar(
        select(CoachAccessCategoryGrant).where(
            CoachAccessCategoryGrant.coach_access_id == access.id,
            CoachAccessCategoryGrant.category == payload.category,
        )
    )
    if grant is None:
        grant = CoachAccessCategoryGrant(coach_access_id=access.id, category=payload.category)
        db.add(grant)
    grant.granted = payload.granted

    db.add(
        ConsentRecord(
            user_id=current_user.id,
            consent_type="coach_sharing",
            category=payload.category,
            granted=payload.granted,
            granted_at=func.clock_timestamp(),
            clinician_id=access.coach_id,
        )
    )
    db.commit()

    coach = db.get(CoachProfile, access.coach_id)
    grants = db.scalars(
        select(CoachAccessCategoryGrant).where(
            CoachAccessCategoryGrant.coach_access_id == access.id,
            CoachAccessCategoryGrant.granted.is_(True),
        )
    ).all()
    return CoachConnectionOut(
        id=access.id,
        coach_display_name=coach.display_name,
        coach_studio_name=coach.studio_name,
        status=access.status,
        granted_categories=[g.category for g in grants],
        granted_at=access.granted_at,
        revoked_at=access.revoked_at,
        unread_message_count=_unread_message_count(db, access.id, from_sender="coach"),
    )


@router.delete("/coach-connections/{coach_access_id}", status_code=204)
def revoke_coach_connection(
    coach_access_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Immediate for future access — the coach's very next request 403s, since
    require_coach_access checks CoachAccess.status == "active" on every call. Forward-only for
    the past: data already rendered in the coach's browser can't be remotely un-shown, and
    CoachAssignment/CoachNote rows are never deleted here (see app/coach_assignment.py and
    app/routers/coach.py's notes endpoints) — only future access is cut off."""
    access = _owned_access(db, coach_access_id, current_user.id)
    if access.status == "active":
        access.status = "revoked"
        access.revoked_at = datetime.now(UTC)
        access.revoked_by = "singer"

        grants = db.scalars(
            select(CoachAccessCategoryGrant).where(
                CoachAccessCategoryGrant.coach_access_id == access.id,
                CoachAccessCategoryGrant.granted.is_(True),
            )
        ).all()
        for grant in grants:
            db.add(
                ConsentRecord(
                    user_id=current_user.id,
                    consent_type="coach_sharing",
                    category=grant.category,
                    granted=False,
                    granted_at=func.clock_timestamp(),
                    clinician_id=access.coach_id,
                )
            )
        db.commit()


@router.get("/coach-connections/{coach_access_id}/notes", response_model=list[CoachNoteOut])
def list_notes_about_me(
    coach_access_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CoachNote]:
    """Deliberately not gated on CoachAccess.status — a singer's own read access to notes
    written about them is their own record now, and survives a revoke, unlike the coach's
    future write/read access (see revoke_coach_connection)."""
    access = _owned_access(db, coach_access_id, current_user.id)
    return list(
        db.scalars(
            select(CoachNote)
            .where(CoachNote.coach_access_id == access.id, CoachNote.deleted_at.is_(None))
            .order_by(CoachNote.created_at.desc())
        ).all()
    )


@router.post(
    "/coach-connections/{coach_access_id}/messages",
    response_model=CoachMessageOut,
    status_code=201,
)
def send_message_to_coach(
    coach_access_id: uuid.UUID,
    payload: CoachMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoachMessage:
    """Unlike list_notes_about_me/list_messages_from_coach below, sending requires an active
    connection -- a revoked connection can't be messaged, mirroring require_coach_access()'s
    same rule on the coach's own send endpoint. Saved regardless of a flagged_terms match, same
    non-blocking posture as every other coach-note/message check in this app."""
    access = _owned_access(db, coach_access_id, current_user.id)
    if access.status != "active":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "connection_not_active",
                "message": "This coach connection is no longer active.",
            },
        )
    message = CoachMessage(
        coach_access_id=access.id,
        sender="singer",
        body=payload.body,
        flagged_terms=find_flagged_terms(payload.body) or None,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    coach_profile = db.get(CoachProfile, access.coach_id)
    if coach_profile is not None:
        coach_user = db.get(User, coach_profile.user_id)
        if coach_user is not None and has_notifications_consent(db, coach_user.id):
            send_new_message_email(coach_user.email, current_user.email)

    return message


@router.get(
    "/coach-connections/{coach_access_id}/messages", response_model=list[CoachMessageOut]
)
def list_messages_from_coach(
    coach_access_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CoachMessage]:
    """Deliberately not gated on CoachAccess.status -- same reasoning as list_notes_about_me:
    a singer's own message history is their own record and survives a revoke. Viewing the
    thread marks every coach-sent message read, clearing this connection's unread badge."""
    access = _owned_access(db, coach_access_id, current_user.id)
    messages = list(
        db.scalars(
            select(CoachMessage)
            .where(CoachMessage.coach_access_id == access.id)
            .order_by(CoachMessage.created_at.asc())
        ).all()
    )
    now = datetime.now(UTC)
    changed = False
    for message in messages:
        if message.sender == "coach" and message.read_at is None:
            message.read_at = now
            changed = True
    if changed:
        db.commit()
    return messages
