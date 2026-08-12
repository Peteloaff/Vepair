import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas_baseline import AnomalyOut

SAMPLE_TYPES = (
    "sustained_ah",
    "sustained_ee",
    "sustained_oo",
    "hum",
    "glide",
    "sentence",
    "singing",
    # Stage 8 vocal range mapping: deliberately sustained extremes, not "typical" phonation --
    # kept out of vepair_audio_engine.measurements.SUSTAINED_PHONATION_SAMPLE_TYPES (so they
    # never feed Stage 4's personal baseline, which represents normal day-to-day variation, not
    # deliberately-tested extremes) but still get full f0_min_hz/f0_max_hz measurement, which
    # is computed for every sample type regardless. See app/vocal_range.py.
    "range_low",
    "range_high",
    "range_falsetto",
)


class DeviceMetadataIn(BaseModel):
    device_type: str | None = None
    microphone_name: str | None = None
    os_info: str | None = None
    app_version: str | None = None


class DeviceMetadataOut(DeviceMetadataIn):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class VoiceSessionOut(BaseModel):
    id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None
    notes: str | None
    device_metadata_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class AcousticMeasurementOut(BaseModel):
    """Stage 3 DSP output. See docs/acoustic-measurements.md for what each field means, how
    it's computed, and its limitations — every field is null when it genuinely can't be
    measured for that recording, never a fabricated number."""

    f0_mean_hz: float | None
    f0_median_hz: float | None
    f0_min_hz: float | None
    f0_max_hz: float | None
    pitch_stability_semitones: float | None
    jitter_percent: float | None
    shimmer_percent: float | None
    hnr_db: float | None
    rms_loudness: float | None
    spectral_centroid_hz: float | None
    spectral_rolloff_hz: float | None
    zero_crossing_rate: float | None
    voiced_ratio: float | None

    model_config = {"from_attributes": True}


class RecordingOut(BaseModel):
    id: uuid.UUID
    voice_session_id: uuid.UUID
    sample_type: str
    duration_seconds: float | None
    sample_rate: int | None
    channels: int | None
    quality_flags: dict | None
    measurement: AcousticMeasurementOut | None = None
    created_at: datetime
    # Populated only in the response to the upload that triggered it — a one-time "was this
    # notably different from your recent baseline" signal, not stored/re-served on GET.
    anomalies: list[AnomalyOut] = []

    model_config = {"from_attributes": True}


class VoiceSessionWithRecordingsOut(VoiceSessionOut):
    recordings: list[RecordingOut] = []
