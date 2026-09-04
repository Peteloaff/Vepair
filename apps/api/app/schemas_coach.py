import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.exercise_library import CATEGORY_INTENSITY
from app.schemas_checkin import CheckInOut
from app.schemas_exercise import RoutineOut
from app.schemas_exercise_trend import ExerciseTrendOut
from app.schemas_recording import RecordingOut
from app.schemas_recovery_score import RecoveryScoreOut, ScoreHistoryPointOut
from app.schemas_training_consistency import TrainingConsistencyOut
from app.schemas_vocal_goals import VocalGoalOut
from app.schemas_vocal_range import VocalRangeSummaryOut
from app.vocal_range import note_name_to_midi

# Kept in sync with app.coach_auth's usage and PRIVACY.md's per-category sharing requirement —
# a whitelist, not free text, so a category can't be silently invented that no code enforces.
# DailyCheckIn free-text fields and any live-coach session transcript are a hardcoded omission
# from every coach-facing response, never a togglable category — see app/coach.py.
COACH_SHARE_CATEGORIES = {
    "recovery_trends",
    "vocal_range",
    "exercise_history",
    "recordings",
}


class CoachProfileOut(BaseModel):
    id: uuid.UUID
    display_name: str
    studio_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CoachInviteCreate(BaseModel):
    singer_email: EmailStr
    message: str | None = Field(default=None, max_length=1000)


class CoachInviteOut(BaseModel):
    """A coach's own view of an invite they sent."""

    id: uuid.UUID
    singer_email: str
    status: str
    message: str | None
    created_at: datetime
    responded_at: datetime | None


class SingerInviteOut(BaseModel):
    """A singer's view of an invite they received — coach identity, not the coach's user id."""

    id: uuid.UUID
    coach_display_name: str
    coach_studio_name: str | None
    message: str | None
    created_at: datetime


class InviteAcceptIn(BaseModel):
    granted_categories: list[str] = Field(min_length=1)


class CategoryToggleIn(BaseModel):
    category: str
    granted: bool


class CoachConnectionOut(BaseModel):
    """A singer's own 'manage access' list item — one active or past connection."""

    id: uuid.UUID
    coach_display_name: str
    coach_studio_name: str | None
    status: str
    granted_categories: list[str]
    granted_at: datetime
    revoked_at: datetime | None
    # Count of coach-sent CoachMessage rows with read_at still null on this connection --
    # powers the badge on the singer's "Coach Access" nav link. 0 for a connection with no
    # messages, never None.
    unread_message_count: int = 0


class CoachSingerSummaryOut(BaseModel):
    """Every field is None unless the singer granted that specific category — never a blanket
    all-or-nothing gate. Each populated field is built from the exact same response schema
    (RecoveryScoreOut, VocalRangeSummaryOut, etc.) the singer's own endpoints already return,
    via the exact same pure functions (app.recovery_score, app.vocal_range, ...) — see
    app/routers/coach.py. This is what "one shared Voice Intelligence engine" means in code,
    not just in ROADMAP.md prose."""

    singer_id: uuid.UUID
    # Never gated -- identifying who this dashboard is even about isn't a shareable "category"
    # of voice data, the same way the roster list (CoachSingerListItemOut) always includes it.
    singer_email: str
    granted_categories: list[str]
    recovery_score: RecoveryScoreOut | None
    vocal_range: VocalRangeSummaryOut | None
    # Gated on the same "vocal_range" category grant as vocal_range above -- a target range is
    # naturally part of "vocal range history" from a sharing-consent standpoint, not a category
    # of its own.
    vocal_goal: VocalGoalOut | None
    exercise_trends: list[ExerciseTrendOut] | None
    training_consistency: TrainingConsistencyOut | None
    todays_routine: RoutineOut | None
    # A coach's own reminder for themself -- not gated by singer consent, since it never reveals
    # anything about the singer's voice data, only the coach's own scheduling note.
    next_reassessment_date: date | None = None


class CoachReassessmentIn(BaseModel):
    next_reassessment_date: date | None = None


class CoachReassessmentOut(BaseModel):
    next_reassessment_date: date | None


class CoachSingerHistoryOut(BaseModel):
    """Long-range trend data for the coach Progress tab -- the date-ranged sibling of
    CoachSingerSummaryOut above, same "None unless granted" discipline. score_history and
    checkins are bounded by the caller's from_date/to_date; exercise_trends is all-time by
    design (see app.exercise_trends.compute_exercise_trends), so it isn't affected by the
    requested range."""

    granted_categories: list[str]
    score_history: list[ScoreHistoryPointOut] | None
    checkins: list[CheckInOut] | None
    training_consistency: TrainingConsistencyOut | None
    exercise_trends: list[ExerciseTrendOut] | None


class CoachSingerListItemOut(BaseModel):
    """A coach's own singer roster entry — enough to identify who's who and what's shared,
    without pulling their full dashboard (see CoachSingerSummaryOut for that)."""

    singer_user_id: uuid.UUID
    singer_email: str
    coach_access_id: uuid.UUID
    granted_categories: list[str]
    granted_at: datetime
    # Count of singer-sent CoachMessage rows with read_at still null on this connection --
    # powers the badge on the coach's roster. 0 for a connection with no messages, never None.
    unread_message_count: int = 0


class CoachAssignmentCreate(BaseModel):
    exercise_ids: list[uuid.UUID] = Field(min_length=1)
    note_to_singer: str | None = Field(default=None, max_length=1000)
    # Optional per-exercise target note, e.g. {"<exercise_id>": "G4"} -- every key must also be
    # in exercise_ids (not a way to sneak in a target for an exercise that isn't even part of
    # this assignment) and every value a real note name.
    exercise_tone_targets: dict[uuid.UUID, str] | None = None

    @model_validator(mode="after")
    def _validate_tone_targets(self) -> "CoachAssignmentCreate":
        if self.exercise_tone_targets is None:
            return self
        unknown = set(self.exercise_tone_targets) - set(self.exercise_ids)
        if unknown:
            raise ValueError(
                f"exercise_tone_targets keys must be a subset of exercise_ids: "
                f"{sorted(str(i) for i in unknown)} are not in exercise_ids"
            )
        for exercise_id, note in self.exercise_tone_targets.items():
            try:
                note_name_to_midi(note)
            except ValueError:
                raise ValueError(
                    f"Not a valid note name for exercise {exercise_id}: {note!r}"
                ) from None
        return self


class CoachAssignmentOut(BaseModel):
    id: uuid.UUID
    exercise_ids: list[uuid.UUID]
    note_to_singer: str | None
    status: str
    created_at: datetime
    exercise_tone_targets: dict[uuid.UUID, str] | None

    model_config = {"from_attributes": True}


class AssignmentTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    exercise_ids: list[uuid.UUID] = Field(min_length=1)
    note_to_singer: str | None = Field(default=None, max_length=1000)
    exercise_tone_targets: dict[uuid.UUID, str] | None = None

    # Same validation as CoachAssignmentCreate -- kept as a separate copy rather than a shared
    # mixin since the two models' fields (whether to require exercise_ids as a name-carrying
    # template vs. an immediate per-singer assignment) are conceptually distinct even though the
    # tone-target shape happens to match today.
    @model_validator(mode="after")
    def _validate_tone_targets(self) -> "AssignmentTemplateCreate":
        if self.exercise_tone_targets is None:
            return self
        unknown = set(self.exercise_tone_targets) - set(self.exercise_ids)
        if unknown:
            raise ValueError(
                f"exercise_tone_targets keys must be a subset of exercise_ids: "
                f"{sorted(str(i) for i in unknown)} are not in exercise_ids"
            )
        for exercise_id, note in self.exercise_tone_targets.items():
            try:
                note_name_to_midi(note)
            except ValueError:
                raise ValueError(
                    f"Not a valid note name for exercise {exercise_id}: {note!r}"
                ) from None
        return self


class AssignmentTemplateUpdate(BaseModel):
    """Rename only, in v1 -- changing the exercise set is done by deleting and re-saving from
    the Assign page's current selection, rather than a partial-update endpoint that would need
    to re-run the same tone-target/exercise-id validation as creation for every field."""

    name: str = Field(min_length=1, max_length=200)


class AssignmentTemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    exercise_ids: list[uuid.UUID]
    note_to_singer: str | None
    exercise_tone_targets: dict[uuid.UUID, str] | None
    created_at: datetime

    model_config = {"from_attributes": True}


VALID_DIFFICULTIES = {"easy", "moderate", "hard"}


class CoachExerciseCreate(BaseModel):
    """A coach-authored addition to the exercise library (title + description, per the
    request). `category` must be one of the existing, safety-reviewed categories
    (CATEGORY_INTENSITY in app/exercise_library.py) rather than free text -- that's not just a
    content-quality nicety, it's the mechanism the adaptive routine generator's intensity-cap
    safety gate actually keys on (see app/exercise_routine.py); a category outside that fixed
    set would make the exercise un-selectable rather than unsafe, but validating here gives a
    clear error instead of a silent no-op."""

    name: str = Field(min_length=1, max_length=200)
    instructions: str = Field(min_length=1)
    purpose: str | None = Field(default=None, max_length=2000)
    category: str
    duration_seconds: int = Field(gt=0, le=1800)
    difficulty: str

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        if value not in CATEGORY_INTENSITY:
            raise ValueError(f"category must be one of {sorted(CATEGORY_INTENSITY)}")
        return value

    @field_validator("difficulty")
    @classmethod
    def _validate_difficulty(cls, value: str) -> str:
        if value not in VALID_DIFFICULTIES:
            raise ValueError(f"difficulty must be one of {sorted(VALID_DIFFICULTIES)}")
        return value


class CoachNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CoachNoteOut(BaseModel):
    """Not a clinical record — see MEDICAL_SAFETY.md. `flagged_terms` is non-empty when
    app.coach_notes's blocklist matched; the note is saved regardless (see
    app/routers/coach.py's create_note)."""

    id: uuid.UUID
    body: str
    flagged_terms: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CoachMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CoachMessageOut(BaseModel):
    """Two-way chat, deliberately separate from CoachNoteOut — see app/models.py's
    CoachMessage. `flagged_terms` is non-empty when app.coach_notes's blocklist matched; the
    message is saved regardless, same non-blocking posture as notes (MEDICAL_SAFETY.md §12).
    Not a clinical record — see the disclaimer shown alongside every thread in the app."""

    id: uuid.UUID
    sender: str
    body: str
    flagged_terms: list[str] | None
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CoachVoiceSessionOut(BaseModel):
    """Same shape as VoiceSessionWithRecordingsOut minus `notes` — VoiceSession.notes is
    user free-text, the same category of field DailyCheckIn's illness_symptoms/reflux_symptoms/
    notes are hardcoded out of every coach-facing response for. Built explicitly in
    app/routers/coach.py rather than via VoiceSessionWithRecordingsOut.model_validate(...), so
    `notes` can never leak through by accident even if a future field gets added to that
    schema without this one being updated to match."""

    id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None
    device_metadata_id: uuid.UUID | None
    recordings: list[RecordingOut] = []
