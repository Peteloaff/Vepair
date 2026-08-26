import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

VALID_GRADES = {"spot_on", "close", "off", "no_pitch"}


class ToneGameAttemptIn(BaseModel):
    order_index: int = Field(ge=0, le=4)
    target_note: str
    target_hz: float = Field(gt=0)
    detected_hz: float | None = None
    semitones_off: float | None = None
    grade: str
    hold_fraction: float = Field(ge=0, le=1)
    reaction_ms: int | None = Field(default=None, ge=0)
    score: int = Field(ge=0, le=100)

    @field_validator("grade")
    @classmethod
    def _grade_is_whitelisted(cls, v: str) -> str:
        if v not in VALID_GRADES:
            raise ValueError(f"grade must be one of {sorted(VALID_GRADES)}")
        return v


class ToneGameSessionCreate(BaseModel):
    attempts: list[ToneGameAttemptIn] = Field(min_length=5, max_length=5)


class ToneGameAttemptOut(BaseModel):
    order_index: int
    target_note: str
    target_hz: float
    detected_hz: float | None
    semitones_off: float | None
    grade: str
    hold_fraction: float
    reaction_ms: int | None
    score: int

    model_config = {"from_attributes": True}


class ToneGameSessionOut(BaseModel):
    id: uuid.UUID
    played_at: datetime
    total_score: int
    attempts: list[ToneGameAttemptOut] = []

    model_config = {"from_attributes": True}
