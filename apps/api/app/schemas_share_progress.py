from datetime import date

from pydantic import BaseModel


class TodaySnapshotOut(BaseModel):
    for_date: date
    score_value: int | None
    score_delta: int | None
    measurement_confidence_label: str | None
    low_measurement_confidence: bool
    comfortable_low_note: str | None
    comfortable_high_note: str | None
    range_span_semitones: int | None
    pitch_stability_pct: float | None
    vocal_endurance_seconds: float | None
    reported_fatigue: int | None
    vocal_load: str | None
    training_completed_pct: float | None


class RangeProgressOut(BaseModel):
    start_low_note: str | None
    start_high_note: str | None
    now_low_note: str | None
    now_high_note: str | None
    high_note_semitone_delta: int | None
    start_basis: str


class NumericProgressOut(BaseModel):
    start_value: float
    now_value: float
    delta: float
    start_basis: str


class ProgressSnapshotOut(BaseModel):
    for_date: date
    insufficient_data: bool
    valid_session_count: int
    comfortable_range: RangeProgressOut | None
    pitch_stability_pct: NumericProgressOut | None
    vocal_endurance_seconds: NumericProgressOut | None
    reported_fatigue: NumericProgressOut | None
    days_tracked: int
    sessions_completed: int
    training_compliance_pct: float | None
