import uuid
from datetime import datetime

from pydantic import BaseModel


class ProfileIn(BaseModel):
    """Onboarding answers. Every field is optional — users may skip any question.
    No medical diagnosis fields; see MEDICAL_SAFETY.md."""

    voice_use: str | None = None
    is_singer: bool | None = None
    musical_style: str | None = None
    practice_frequency: str | None = None
    perceived_vocal_range: str | None = None
    goals: str | None = None
    vocal_coaching_history: str | None = None
    under_professional_care: bool | None = None


class ProfileOut(ProfileIn):
    id: uuid.UUID
    user_id: uuid.UUID
    # Stage 9: read-only here — set via PATCH /api/v1/profile/track, never through this
    # full-replace PUT, so an onboarding edit can never silently reset it.
    track: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
