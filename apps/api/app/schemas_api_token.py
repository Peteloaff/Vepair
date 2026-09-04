import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# Reuses the same three data categories as CoachAssignment/CoachAccessCategoryGrant's
# `recovery_trends`/`vocal_range`/`exercise_history` (see app/schemas_coach.py's
# COACH_SHARE_CATEGORIES) -- deliberately excludes `recordings`. Raw audio is never reachable
# through the public API in v1; a coach's live, ownership-checked playback link is a
# fundamentally different exposure than handing a bearer token that could end up anywhere.
API_TOKEN_SCOPES = {
    "recovery_trends",
    "vocal_range",
    "exercise_history",
}


class ApiTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    scopes: list[str] = Field(min_length=1)

    @field_validator("scopes")
    @classmethod
    def _validate_scopes(cls, value: list[str]) -> list[str]:
        unknown = set(value) - API_TOKEN_SCOPES
        if unknown:
            raise ValueError(f"scopes must be a subset of {sorted(API_TOKEN_SCOPES)}")
        return value


class ApiTokenCreateOut(BaseModel):
    """Returned exactly once, at creation -- the raw `token` is never retrievable again, same
    convention as a GitHub personal access token."""

    id: uuid.UUID
    name: str
    scopes: list[str]
    token: str
    created_at: datetime


class ApiTokenOut(BaseModel):
    """The list/management view -- never includes the raw token or its hash."""

    id: uuid.UUID
    name: str
    scopes: list[str]
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None

    model_config = {"from_attributes": True}
