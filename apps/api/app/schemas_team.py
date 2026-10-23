import uuid
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


class TeamMemberUpdate(BaseModel):
    org_role: OrgRole | None = None
    is_active: bool | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
