import uuid
from datetime import date, datetime

from pydantic import BaseModel


class TrackIn(BaseModel):
    """Self-selected, never inferred — see MEDICAL_SAFETY.md."""

    track: str


class VocalPlanOut(BaseModel):
    id: uuid.UUID
    track: str
    start_date: date
    target_end_date: date
    status: str
    baseline_snapshot: dict
    target_milestones: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReadinessOut(BaseModel):
    ready: bool
    reasons: list[str]


class VocalPlanViewOut(BaseModel):
    plan: VocalPlanOut | None
    readiness: ReadinessOut | None
    just_graduated: bool


class TrackSetOut(BaseModel):
    track: str
    plan: VocalPlanOut | None
    plan_pending_reason: str | None
