import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class CheckInCreate(BaseModel):
    """Every field except the date is optional — users may skip any question.

    checkin_date is required and must be supplied by the client (the user's local calendar
    date). The server intentionally never defaults this from its own clock: "today" depends
    on the user's timezone, not the server's, and defaulting to server-UTC "today" produces
    an off-by-one-day check-in for any user west of UTC in the evening.
    """

    checkin_date: date
    voice_quality: int | None = Field(default=None, ge=1, le=10)
    fatigue: int | None = Field(default=None, ge=1, le=10)
    throat_discomfort: int | None = Field(default=None, ge=0, le=10)
    speaking_load: str | None = None
    singing_load: str | None = None
    rehearsal_or_performance_yesterday: bool | None = None
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    hydration_estimate: str | None = None
    alcohol_exposure: str | None = None
    smoke_vape_exposure: str | None = None
    illness_symptoms: str | None = None
    reflux_symptoms: str | None = None
    notes: str | None = None


class CheckInUpdate(BaseModel):
    """Partial update — omit any field to leave it unchanged."""

    voice_quality: int | None = Field(default=None, ge=1, le=10)
    fatigue: int | None = Field(default=None, ge=1, le=10)
    throat_discomfort: int | None = Field(default=None, ge=0, le=10)
    speaking_load: str | None = None
    singing_load: str | None = None
    rehearsal_or_performance_yesterday: bool | None = None
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    hydration_estimate: str | None = None
    alcohol_exposure: str | None = None
    smoke_vape_exposure: str | None = None
    illness_symptoms: str | None = None
    reflux_symptoms: str | None = None
    notes: str | None = None


class CheckInOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    checkin_date: date
    voice_quality: int | None
    fatigue: int | None
    throat_discomfort: int | None
    speaking_load: str | None
    singing_load: str | None
    rehearsal_or_performance_yesterday: bool | None
    sleep_hours: float | None
    hydration_estimate: str | None
    alcohol_exposure: str | None
    smoke_vape_exposure: str | None
    illness_symptoms: str | None
    reflux_symptoms: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
