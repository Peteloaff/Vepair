"""SQLAlchemy models for all VepAIr entities.

Stage 0 shipped the full schema so later stages build on a reviewed foundation. See
ARCHITECTURE.md section 4 for the plain-English description of each entity.

Stage 1 adds AuthCredential / RefreshToken / PasswordResetToken for self-hosted email+password
auth. These are deliberately kept separate from `User` (which stays Supabase-Auth-shaped: just
id + email) so a future move to Supabase Auth only means dropping these three tables and
swapping `app/auth.py`'s token verification — nothing else in the schema changes.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Base, TimestampMixin):
    """Authentication identity. Shaped to match the Supabase Auth user (id + email) so a
    later migration doesn't need to change anything that references `users.id`."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)

    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False)


class AuthCredential(Base, TimestampMixin):
    """Self-hosted-auth-only: password hash for one user. Not part of the Supabase-shaped
    core schema — this table is dropped, not migrated, when VepAIr moves to Supabase Auth."""

    __tablename__ = "auth_credentials"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    password_hash: Mapped[str] = mapped_column(String(200))


class RefreshToken(Base, TimestampMixin):
    """Self-hosted-auth-only: a hashed, revocable refresh token backing one login session."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetToken(Base, TimestampMixin):
    """Self-hosted-auth-only: a hashed, single-use password reset token."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserProfile(Base, TimestampMixin):
    """Onboarding answers. No medical diagnosis fields — see MEDICAL_SAFETY.md."""

    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    voice_use: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_singer: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    musical_style: Mapped[str | None] = mapped_column(String(200), nullable=True)
    practice_frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    perceived_vocal_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    vocal_coaching_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    under_professional_care: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Stage 9: "repair" | "improvement" | None. Self-selected, never inferred as a diagnosis —
    # see MEDICAL_SAFETY.md. Drives which VocalPlan is active and how aggressively the exercise
    # routine (app/exercise_routine.py) and range stretch-target (app/vocal_range.py) behave.
    track: Mapped[str | None] = mapped_column(String(20), nullable=True)

    user: Mapped[User] = relationship(back_populates="profile")


class VoiceProfile(Base, TimestampMixin):
    """The evolving personalized model of one user's voice."""

    __tablename__ = "voice_profiles"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    current_baseline_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("baselines.id", ondelete="SET NULL"), nullable=True
    )
    confidence_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    range_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeviceMetadata(Base, TimestampMixin):
    """Recording device/microphone fingerprint, reused across sessions."""

    __tablename__ = "device_metadata"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    device_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    microphone_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    os_info: Mapped[str | None] = mapped_column(String(200), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(50), nullable=True)


class VoiceSession(Base, TimestampMixin):
    """One guided recording session (sustained vowels, hum, glide, sentence, optional song)."""

    __tablename__ = "voice_sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    device_metadata_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device_metadata.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    recordings: Mapped[list["Recording"]] = relationship(back_populates="voice_session")


class Recording(Base, TimestampMixin):
    """One raw audio asset within a session. Originals are never destructively overwritten."""

    __tablename__ = "recordings"

    id: Mapped[uuid.UUID] = _uuid_pk()
    voice_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voice_sessions.id", ondelete="CASCADE")
    )
    # sustained_ah|ee|oo, hum, glide, sentence, singing
    sample_type: Mapped[str] = mapped_column(String(50))
    file_path: Mapped[str] = mapped_column(String(500))
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channels: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    voice_session: Mapped[VoiceSession] = relationship(back_populates="recordings")
    measurement: Mapped["AcousticMeasurement | None"] = relationship(
        back_populates="recording", uselist=False
    )


class AcousticMeasurement(Base, TimestampMixin):
    """DSP output for one recording, computed by packages/audio-engine (Stage 3). See
    docs/acoustic-measurements.md for the definition/algorithm/units/limitations of every
    field. Every field is nullable: a metric is null when it genuinely can't be measured for
    that recording (e.g. jitter/shimmer/HNR are only valid for sustained phonation — see
    SUSTAINED_PHONATION_SAMPLE_TYPES), never a fabricated placeholder."""

    __tablename__ = "acoustic_measurements"

    id: Mapped[uuid.UUID] = _uuid_pk()
    recording_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recordings.id", ondelete="CASCADE"), unique=True
    )
    f0_mean_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    f0_median_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    f0_min_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    f0_max_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    pitch_stability_semitones: Mapped[float | None] = mapped_column(Float, nullable=True)
    jitter_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    shimmer_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    hnr_db: Mapped[float | None] = mapped_column(Float, nullable=True)
    rms_loudness: Mapped[float | None] = mapped_column(Float, nullable=True)
    spectral_centroid_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    spectral_rolloff_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    zero_crossing_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    voiced_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Stage 10 "Vocal Endurance": longest unbroken run of voiced frames, in seconds. A
    # byproduct of the same frame-level voicing decisions voiced_ratio already uses.
    longest_voiced_run_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    recording: Mapped[Recording] = relationship(back_populates="measurement")


class DailyCheckIn(Base, TimestampMixin):
    """Subjective daily journal entry. All fields except date are skippable."""

    __tablename__ = "daily_check_ins"
    __table_args__ = (UniqueConstraint("user_id", "checkin_date", name="uq_checkin_user_date"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    checkin_date: Mapped[date] = mapped_column(Date)
    voice_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-10
    fatigue: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-10
    throat_discomfort: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-10
    speaking_load: Mapped[str | None] = mapped_column(String(50), nullable=True)
    singing_load: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rehearsal_or_performance_yesterday: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    hydration_estimate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    alcohol_exposure: Mapped[str | None] = mapped_column(String(50), nullable=True)
    smoke_vape_exposure: Mapped[str | None] = mapped_column(String(50), nullable=True)
    illness_symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    reflux_symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Exercise(Base, TimestampMixin):
    """Exercise library entry."""

    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100))
    purpose: Mapped[str] = mapped_column(Text)
    instructions: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[str] = mapped_column(String(50))
    audio_demo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contraindications: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_measurement: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expected_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ExerciseSession(Base, TimestampMixin):
    """One instance of a user doing a routine."""

    __tablename__ = "exercise_sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    routine_length_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    results: Mapped[list["ExerciseResult"]] = relationship(back_populates="exercise_session")


class ExerciseResult(Base, TimestampMixin):
    """Measured/self-reported outcome of one exercise within a session."""

    __tablename__ = "exercise_results"

    id: Mapped[uuid.UUID] = _uuid_pk()
    exercise_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exercise_sessions.id", ondelete="CASCADE")
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exercises.id", ondelete="RESTRICT")
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    measured_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    self_reported_difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)

    exercise_session: Mapped[ExerciseSession] = relationship(back_populates="results")


class Baseline(Base, TimestampMixin):
    """A computed personal baseline snapshot for one metric (Stage 4). One row per
    (user, metric) — updated in place as new usable sessions arrive, not a growing history
    table. `median_value`/`mad_value` are robust statistics (median, median absolute
    deviation) over the user's own historical measurements for that metric — see
    app/baseline.py and docs/baseline.md for the full methodology."""

    __tablename__ = "baselines"
    __table_args__ = (UniqueConstraint("user_id", "metric_name", name="uq_baseline_user_metric"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    metric_name: Mapped[str] = mapped_column(String(100))
    window_start: Mapped[date] = mapped_column(Date)
    window_end: Mapped[date] = mapped_column(Date)
    median_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    mad_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence_pct: Mapped[float | None] = mapped_column(Float, nullable=True)


class VocalRange(Base, TimestampMixin):
    """Comfortable low/high note history."""

    __tablename__ = "vocal_ranges"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    comfortable_low_note: Mapped[str | None] = mapped_column(String(10), nullable=True)
    comfortable_high_note: Mapped[str | None] = mapped_column(String(10), nullable=True)
    falsetto_high_note: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_recording_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recordings.id", ondelete="SET NULL"), nullable=True
    )


class VocalPlan(Base, TimestampMixin):
    """Stage 9: a 90-day repair/improvement plan. `baseline_snapshot` captures the real
    measurements the plan was generated from (the "specific to the range that it analyzed"
    part) — never regenerated after the fact, so a plan's targets stay traceable to what was
    actually true when it was created. Day-to-day exercise/range decisions still run through
    app/exercise_routine.py and app/vocal_range.py; this table only supplies the track and
    long-term targets they read. One row per plan; a user's history of past plans is kept
    (superseded, not deleted) rather than overwritten in place."""

    __tablename__ = "vocal_plans"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    track: Mapped[str] = mapped_column(String(20))  # "repair" | "improvement"
    start_date: Mapped[date] = mapped_column(Date)
    target_end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|completed|superseded
    baseline_snapshot: Mapped[dict] = mapped_column(JSON)
    target_milestones: Mapped[dict] = mapped_column(JSON)


class Recommendation(Base, TimestampMixin):
    """A generated suggestion with the inputs that produced it, kept explainable."""

    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    recommendation_type: Mapped[str] = mapped_column(String(100))
    inputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_text: Mapped[str] = mapped_column(Text)


class RecoveryScore(Base, TimestampMixin):
    """The daily 0-100 VepAIr Score with component breakdown and confidence."""

    __tablename__ = "recovery_scores"
    __table_args__ = (UniqueConstraint("user_id", "score_date", name="uq_score_user_date"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    score_date: Mapped[date] = mapped_column(Date)
    score_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    components: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ConsentRecord(Base, TimestampMixin):
    """Explicit, timestamped, purpose-specific consent grant. See PRIVACY.md section 3."""

    __tablename__ = "consent_records"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    # product_analytics | model_training | clinician_sharing
    consent_type: Mapped[str] = mapped_column(String(50))
    granted: Mapped[bool] = mapped_column(Boolean)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clinician_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
