import uuid
from datetime import datetime

from pydantic import BaseModel


class VocalRangeAttemptIn(BaseModel):
    low_recording_id: uuid.UUID | None = None
    high_recording_id: uuid.UUID | None = None
    falsetto_recording_id: uuid.UUID | None = None


class VocalRangeEntryOut(BaseModel):
    id: uuid.UUID
    measured_at: datetime
    comfortable_low_note: str | None
    comfortable_high_note: str | None
    falsetto_high_note: str | None

    model_config = {"from_attributes": True}


class RangeChangeOut(BaseModel):
    semitones: int | None
    from_note: str | None
    to_note: str | None


class VocalRangeSummaryOut(BaseModel):
    current_low_note: str | None
    current_high_note: str | None
    current_falsetto_note: str | None
    historical_best_low_note: str | None
    historical_best_high_note: str | None
    change_30d_high: RangeChangeOut
    change_90d_high: RangeChangeOut
    change_30d_low: RangeChangeOut
    change_90d_low: RangeChangeOut
    history: list[dict]
    stretch_target_note: str | None
    stretch_target_reason: str | None
