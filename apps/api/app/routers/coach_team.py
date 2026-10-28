"""The coach-side team page: a clinic or studio's coaches managing their own organization.
Any coach in the organization can see the team; only an organization admin can change it.
See app/org_team.py for the rules."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.coach_auth import get_current_coach, get_current_org_admin
from app.database import get_db
from app.email import send_team_welcome_email
from app.models import CoachProfile, User
from app.org_team import (
    WELCOME_TOKEN_DAYS,
    add_member,
    build_team,
    issue_welcome_token,
    rename_organization,
    team_member_not_found,
    update_member,
)
from app.schemas_team import (
    OrganizationRename,
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
    if target is None or target.organization_id != admin.organization_id:
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
