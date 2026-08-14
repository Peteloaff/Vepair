import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ExerciseOut(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    purpose: str
    instructions: str
    duration_seconds: int
    difficulty: str
    audio_demo_url: str | None
    contraindications: str | None
    target_measurement: str | None
    expected_result: str

    model_config = {"from_attributes": True}


class RoutineOut(BaseModel):
    length_minutes: int
    intensity_cap: str
    total_duration_seconds: int
    safety_message: str | None
    reasons: list[str]
    items: list[ExerciseOut]
    # Stage 12 Phase II: which items (if any) came from an active coach assignment rather
    # than the adaptive selector — lets the frontend badge them. Empty when there's no
    # assignment, or none of it fit today's safety limits (reasons explains why).
    assigned_exercise_ids: list[uuid.UUID] = []
    # A strong recommendation, never a block -- items above is still a valid routine even when
    # this is True. See app/exercise_routine.py's REST_DAY_* thresholds.
    rest_day_recommended: bool = False
    rest_day_reason: str | None = None
    # Stage 12 Phase II: coach-set per-exercise target notes, for whichever assigned exercises
    # made it into items today. Purely informational -- never affects selection or safety.
    exercise_tone_targets: dict[uuid.UUID, str] = {}


class RestCheckOut(BaseModel):
    """Lightweight companion to RoutineOut for surfaces (like the home page) that want the
    rest-day recommendation without building a full routine."""

    rest_day_recommended: bool
    rest_day_reason: str | None


class ExerciseSessionCreate(BaseModel):
    routine_length_minutes: int = Field(ge=1, le=60)


class ExerciseResultOut(BaseModel):
    id: uuid.UUID
    exercise_id: uuid.UUID
    order_index: int
    completed: bool
    self_reported_difficulty: int | None
    measured_result: dict | None

    model_config = {"from_attributes": True}


class ExerciseSessionOut(BaseModel):
    id: uuid.UUID
    routine_length_minutes: int | None
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ExerciseSessionWithResultsOut(ExerciseSessionOut):
    results: list[ExerciseResultOut] = []
