"""The coach-side team page: a clinic or studio's coaches managing their own organization.
Any coach in the organization can see the team; only an organization admin can change it.
See app/org_team.py for the rules."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coach_auth import get_current_coach, get_current_org_admin
from app.coach_connections import end_connection, new_invite
from app.database import get_db
from app.email import send_coach_invite_email, send_team_added_email, send_team_welcome_email
from app.models import CoachInvite, CoachProfile, User
from app.org_report import PERIODS, build_report
from app.org_team import (
    WELCOME_TOKEN_DAYS,
    add_member,
    build_team,
    build_vroteges,
    issue_welcome_token,
    org_access,
    org_coach,
    remove_member,
    rename_organization,
    team_member_not_found,
    update_member,
)
from app.schemas_team import (
    OrganizationRename,
    OrgInviteCreate,
    OrgMoveVrotege,
    OrgPendingInviteOut,
    OrgReportOut,
    OrgVrotegesOut,
    RemoveMemberOut,
    TeamMemberCreate,
    TeamMemberOut,
    TeamMemberUpdate,
    TeamOut,
)

router = APIRouter(prefix="/api/v1/coach/team", tags=["coach-team"])


def _member_out(db: Session, coach: CoachProfile, my_user_id: uuid.UUID) -> TeamMemberOut:
    team = build_team(db, coach.organization, my_user_id)
    return next(m for m in team.members if m.coach_id == coach.id)


@router.get("", response_model=TeamOut)
def get_team(
    coach: CoachProfile = Depends(get_current_coach), db: Session = Depends(get_db)
) -> TeamOut:
    return build_team(db, coach.organization, coach.user_id)


@router.patch("/organization", response_model=TeamOut)
def rename_my_organization(
    payload: OrganizationRename,
    admin: CoachProfile = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
) -> TeamOut:
    rename_organization(admin.organization, payload.name)
    db.commit()
    return build_team(db, admin.organization, admin.user_id)


@router.post("/members", response_model=TeamMemberOut, status_code=201)
def add_team_member(
    payload: TeamMemberCreate,
    admin: CoachProfile = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
) -> TeamMemberOut:
    organization = admin.organization
    new_coach, new_user, token = add_member(
        db, organization, payload.email, payload.display_name, payload.org_role
    )
    db.commit()
    if token is None:
        # Someone this organization removed earlier, added back: they keep their login.
        send_team_added_email(
            new_user.email, new_coach.display_name, organization.name, new_coach.org_role
        )
    else:
        send_team_welcome_email(
            new_user.email,
            new_coach.display_name,
            organization.name,
            admin.display_name,
            new_coach.org_role,
            token,
            WELCOME_TOKEN_DAYS,
        )
    return _member_out(db, new_coach, admin.user_id)


@router.patch("/members/{coach_id}", response_model=TeamMemberOut)
def update_team_member(
    coach_id: uuid.UUID,
    payload: TeamMemberUpdate,
    admin: CoachProfile = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
) -> TeamMemberOut:
    coach, _user = update_member(
        db,
        admin.organization,
        coach_id,
        acting_user_id=admin.user_id,
        org_role=payload.org_role,
        is_active=payload.is_active,
        display_name=payload.display_name,
    )
    db.commit()
    return _member_out(db, coach, admin.user_id)


@router.post("/members/{coach_id}/resend-welcome", status_code=202)
def resend_welcome(
    coach_id: uuid.UUID,
    admin: CoachProfile = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
) -> None:
    """A fresh set-your-password link, for a member who lost or never got the first one."""
    target = db.get(CoachProfile, coach_id)
    if (
        target is None
        or target.organization_id != admin.organization_id
        or target.removed_at is not None
    ):
        raise team_member_not_found()
    user = db.get(User, target.user_id)
    token = issue_welcome_token(db, user)
    db.commit()
    send_team_welcome_email(
        user.email,
        target.display_name,
        admin.organization.name,
        admin.display_name,
        target.org_role,
        token,
        WELCOME_TOKEN_DAYS,
    )


@router.delete("/members/{coach_id}", response_model=RemoveMemberOut)
def remove_team_member(
    coach_id: uuid.UUID,
    admin: CoachProfile = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
) -> RemoveMemberOut:
    """Takes a coach off the team: their login survives (it just stops being a coach), their
    notes and history are kept, their Vrotégés' connections end, and their pending invites are
    cancelled. Use PATCH is_active=false instead for a reversible pause."""
    _coach, _user, ended, cancelled = remove_member(
        db, admin.organization, coach_id, acting_user_id=admin.user_id
    )
    db.commit()
    return RemoveMemberOut(ended_connections=ended, cancelled_invites=cancelled)


# ---- Vrotégé connections, for organization admins ----
# An admin manages *who coaches whom* -- never what a Vrotégé shares. Every connection still
# needs the Vrotégé's own acceptance, and an admin never sees any of their voice data.


@router.get("/report", response_model=OrgReportOut)
def get_org_report(
    days: int = Query(default=30),
    admin: CoachProfile = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
) -> OrgReportOut:
    """Per-coach activity and practice for the organization, as counts only (see
    app/org_report.py for what is shown and when it is hidden)."""
    if days not in PERIODS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_period",
                "message": f"Choose a period of {', '.join(str(p) for p in PERIODS)} days.",
            },
        )
    return build_report(db, admin.organization, days)


@router.get("/vroteges", response_model=OrgVrotegesOut)
def list_org_vroteges(
    admin: CoachProfile = Depends(get_current_org_admin), db: Session = Depends(get_db)
) -> OrgVrotegesOut:
    return build_vroteges(db, admin.organization)


def _pending_out(invite, coach) -> OrgPendingInviteOut:
    return OrgPendingInviteOut(
        invite_id=invite.id,
        singer_email=invite.singer_email,
        coach_id=coach.id,
        coach_name=coach.display_name,
        sent_at=invite.created_at,
    )


@router.post("/vroteges/invite", response_model=OrgPendingInviteOut, status_code=201)
def invite_vrotege_for_coach(
    payload: OrgInviteCreate,
    admin: CoachProfile = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
) -> OrgPendingInviteOut:
    """Invites a Vrotégé on behalf of a coach on this team. The invite comes from that coach, uses
    the organization's shared invite allowance, and still needs the Vrotégé to accept."""
    coach = org_coach(db, admin.organization, payload.coach_id)
    invite, has_account = new_invite(db, coach, payload.singer_email, payload.message)
    db.commit()
    db.refresh(invite)
    send_coach_invite_email(
        invite.singer_email,
        coach.display_name,
        coach.studio_name,
        invite.message,
        has_account=has_account,
    )
    return _pending_out(invite, coach)


@router.post("/vroteges/{access_id}/move", response_model=OrgPendingInviteOut, status_code=201)
def move_vrotege_to_coach(
    access_id: uuid.UUID,
    payload: OrgMoveVrotege,
    admin: CoachProfile = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
) -> OrgPendingInviteOut:
    """Ends a Vrotégé's connection to one coach and invites them to another coach on the team. The
    old coach loses access immediately; the new coach sees nothing until the Vrotégé accepts and
    chooses what to share."""
    access = org_access(db, admin.organization, access_id)
    target = org_coach(db, admin.organization, payload.coach_id)
    if target.id == access.coach_id:
        raise HTTPException(
            status_code=409,
            detail={"code": "same_coach", "message": "They are already with that coach."},
        )
    singer = db.get(User, access.singer_user_id)
    invite, _has_account = new_invite(db, target, singer.email, None)
    end_connection(db, access, "org_admin")
    db.commit()
    db.refresh(invite)
    send_coach_invite_email(
        singer.email, target.display_name, target.studio_name, None, has_account=True
    )
    return _pending_out(invite, target)


@router.delete("/vroteges/invites/{invite_id}", status_code=204)
def cancel_org_invite(
    invite_id: uuid.UUID,
    admin: CoachProfile = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
) -> None:
    invite = db.scalar(
        select(CoachInvite)
        .join(CoachProfile, CoachProfile.id == CoachInvite.coach_id)
        .where(
            CoachInvite.id == invite_id,
            CoachInvite.status == "pending",
            CoachProfile.organization_id == admin.organization_id,
        )
    )
    if invite is None:
        raise HTTPException(
            status_code=404, detail={"code": "invite_not_found", "message": "Invite not found."}
        )
    invite.status = "revoked"
    db.commit()


@router.delete("/vroteges/{access_id}", status_code=204)
def end_org_connection(
    access_id: uuid.UUID,
    admin: CoachProfile = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
) -> None:
    """Ends a Vrotégé's connection to one of this team's coaches. Same effect as the coach
    removing them from their own roster: immediate, forward-only, and the Vrotégé's own account
    and data are untouched."""
    access = org_access(db, admin.organization, access_id)
    end_connection(db, access, "org_admin")
    db.commit()
