import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EquipmentItemOut(BaseModel):
    name: str
    description: str
    how_to_use: str


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
    equipment: list[EquipmentItemOut] | None = None

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


class QuickRoutineOut(BaseModel):
    """A standalone, on-demand Warm Up / Cool Down routine -- deliberately its own shape, not
    RoutineOut: no length_minutes (not user-timeboxed), no assigned_exercise_ids/
    exercise_tone_targets (coach assignment is an adaptive-routine-only concept), no
    rest_day_* fields (a quick routine is low-stakes enough that a rest-day banner would
    contradict "even a rough day still gets a safely shrunk version" -- see
    app/quick_routine.py)."""

    kind: str  # "warm_up" | "cool_down"
    intensity_cap: str
    total_duration_seconds: int
    safety_message: str | None
    reasons: list[str]
    items: list[ExerciseOut]


class AssignedExercisesOut(BaseModel):
    """What the signed-in singer's coach has assigned, for the home page card and the runner
    behind it. `items` are runnable today; `held_back` are assigned exercises today's own safety
    check is keeping off the list -- shown so the singer knows they exist, never launchable. All
    coach fields are null when there is no active assignment (`has_assignment` false)."""

    has_assignment: bool
    coach_display_name: str | None
    coach_studio_name: str | None
    note_to_singer: str | None
    assigned_at: datetime | None
    intensity_cap: str
    total_duration_seconds: int
    safety_message: str | None
    reasons: list[str]
    items: list[ExerciseOut]
    held_back: list[ExerciseOut]
    exercise_tone_targets: dict[uuid.UUID, str]


class ExerciseSessionCreate(BaseModel):
    routine_length_minutes: int | None = Field(default=None, ge=1, le=60)
    # "adaptive" (default) is the existing once-daily routine; "warm_up"/"cool_down" are the
    # standalone on-demand sessions -- see app/quick_routine.py; "assigned" is a coach's
    # assignment run on its own -- see app/assigned_exercises.py. Plain string, matching how
    # every other categorical field in this schema (intensity_cap, difficulty, etc.) is stored,
    # not a DB enum.
    session_type: str = "adaptive"


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
