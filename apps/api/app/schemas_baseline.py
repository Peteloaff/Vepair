from datetime import date

from pydantic import BaseModel


class BaselineOut(BaseModel):
    metric_name: str
    median_value: float | None
    mad_value: float | None
    sample_count: int
    confidence_pct: float | None
    confidence_label: str | None
    window_start: date | None
    window_end: date | None

    model_config = {"from_attributes": True}


class AnomalyOut(BaseModel):
    metric_name: str
    current_value: float
    baseline_median: float
    modified_z_score: float
    message: str


class BaselineSummaryOut(BaseModel):
    voice_baselines: list[BaselineOut]
    voice_confidence_pct: float
    voice_confidence_label: str
    usable_session_count: int
    fatigue_baseline: BaselineOut | None
