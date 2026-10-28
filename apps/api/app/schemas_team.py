import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

OrgRole = Literal["admin", "member"]


class TeamMemberOut(BaseModel):
    coach_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    org_role: OrgRole
    is_active: bool
    # "invited" = created but has never logged in; "deactivated" = login switched off.
    status: Literal["active", "invited", "deactivated"]
    # Vrotégés currently connected to this coach -- a count only, never who they are.
    singer_count: int
    is_me: bool
    # The same login is also a Vrotégé (admin-attached existing account). Deactivating
    # the coach deactivates the whole login, so the UI says so.
    also_singer: bool = False


class TeamOut(BaseModel):
    organization_id: uuid.UUID
    organization_name: str | None
    # The viewer's own role; a platform admin managing the org from the admin console is "admin".
    my_role: OrgRole
    members: list[TeamMemberOut]
    invite_quota_included: int
    invites_used_this_period: int


class TeamMemberCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=200)
    org_role: OrgRole = "member"


class OrgVrotegeConnectionOut(BaseModel):
    """One active coach/Vrotégé connection, as an organization admin sees it: who is connected to
    which coach and since when -- an identifier only, never any of their voice data."""

    access_id: uuid.UUID
    singer_label: str  # username if they set one, else their email
    singer_email: str
    coach_id: uuid.UUID
    coach_name: str
    connected_since: datetime | None


class OrgPendingInviteOut(BaseModel):
    invite_id: uuid.UUID
    singer_email: str
    coach_id: uuid.UUID
    coach_name: str
    sent_at: datetime


class OrgVrotegesOut(BaseModel):
    connections: list[OrgVrotegeConnectionOut]
    pending_invites: list[OrgPendingInviteOut]


class OrgInviteCreate(BaseModel):
    coach_id: uuid.UUID
    singer_email: EmailStr
    message: str | None = Field(default=None, max_length=1000)


class OrgMoveVrotege(BaseModel):
    coach_id: uuid.UUID


class RemoveMemberOut(BaseModel):
    ended_connections: int
    cancelled_invites: int


class TeamExistingMemberCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=200)
    org_role: OrgRole = "member"


class OrganizationRename(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class TeamMemberUpdate(BaseModel):
    org_role: OrgRole | None = None
    is_active: bool | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=200)


class CoachReportRow(BaseModel):
    """One coach's activity for the report period. Everything here is a count.

    The first group is the coach's own work (nothing about any Vrotégé's voice). The practice
    figures describe Vrotégés, so they only cover those who share their exercise history with
    this coach, and are None (hidden) until at least `min_group_size` of them do -- with fewer,
    a count would effectively describe one identifiable person."""

    coach_id: uuid.UUID
    display_name: str
    org_role: OrgRole
    is_active: bool
    connected_vroteges: int
    invites_sent: int
    notes_written: int
    messages_sent: int
    assignments_sent: int
    # Vrotégés connected to this coach who share their exercise history (a count, no names).
    sharing_vroteges: int
    practice_sessions: int | None
    practicing_vroteges: int | None


class OrgReportTotals(BaseModel):
    connected_vroteges: int
    invites_sent: int
    notes_written: int
    messages_sent: int
    assignments_sent: int
    # Sums over the coaches whose practice figures are shown, never over hidden ones, so a
    # hidden coach can't be worked out by subtraction.
    practice_sessions: int
    practicing_vroteges: int


class OrgReportOut(BaseModel):
    period_days: int
    since: datetime
    min_group_size: int
    coaches: list[CoachReportRow]
    totals: OrgReportTotals
