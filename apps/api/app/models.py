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
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
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
    """Exercise library entry. `created_by_coach_id` is null for the hand-curated
    SEED_EXERCISES (see app/exercise_library.py); non-null means a coach authored it via
    POST /api/v1/coach/exercises. A coach-created row is a normal, immediately-active Exercise
    row like any other -- it's eligible for the general adaptive routine pool (not just that
    coach's own singers) the moment it's created, gated by the same `category`-driven
    intensity-cap safety check as every seed exercise (see CATEGORY_INTENSITY in
    exercise_library.py, which is exactly why `category` must be one of that fixed set rather
    than free text)."""

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
    created_by_coach_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="CASCADE"), nullable=True
    )


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


class VocalGoal(Base, TimestampMixin):
    """A singer's target low/avg/high note. Current-state, not history (one row per user,
    upserted in place) -- same pattern as UserProfile, unlike VocalRange's append-only log,
    because a "goal" is a single thing you're aiming for right now, not a measurement series.
    `source` records whether these are the AI's own suggestion (derived fresh from VocalRange
    history -- see app/vocal_goals.py -- whenever no row exists yet or the row itself was never
    manually edited) or a value the singer explicitly set, which then overrides the AI
    suggestion until cleared."""

    __tablename__ = "vocal_goals"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    target_low_note: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_avg_note: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_high_note: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source: Mapped[str] = mapped_column(String(10))  # "ai" | "manual"


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
    # product_analytics | model_training | coach_sharing | notifications
    # Kept in sync with app.schemas_consent.VALID_CONSENT_TYPES, the actual enforced whitelist.
    # Was "clinician_sharing" until Stage 12 Phase II — renamed since "clinician" is clinical
    # language on a permanently non-clinical feature (see the coach-tables migration).
    consent_type: Mapped[str] = mapped_column(String(50))
    # Only set when consent_type == "coach_sharing" — one row per category per grant/revoke
    # event, so the audit ledger stays per-category-granular too. See CoachAccessCategoryGrant,
    # the table authorization checks actually query; this column is audit-only.
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    granted: Mapped[bool] = mapped_column(Boolean)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Was an unconstrained, unused UUID column pre-Stage 12. Now a real FK, nullable since it
    # only applies to coach_sharing consent rows.
    clinician_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="SET NULL"), nullable=True
    )


class CoachProfile(Base, TimestampMixin):
    """Stage 12 Phase II. Presence of this row is what makes a User a coach — same optional
    1:1-extension shape as UserProfile, not a role flag. Created only via
    POST /api/v1/auth/coach-signup (app/routers/auth.py), never as a self-serve upgrade on an
    existing account — a coach account is a coach account from creation, so the same user can
    never also be a singer. See ROADMAP.md Stage 12 / the Phase II plan for why."""

    __tablename__ = "coach_profiles"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    display_name: Mapped[str] = mapped_column(String(200))
    studio_name: Mapped[str | None] = mapped_column(String(200), nullable=True)


class CoachInvite(Base, TimestampMixin):
    """One row per invite a coach sends. Targets an existing VepAIr account resolved by email
    at creation time — inviting a non-account email 404s rather than creating a dangling
    invite (Phase II doesn't build a parallel pending-account system). `status="revoked"` here
    means the coach or singer cancelled before any response — distinct from post-acceptance
    access revocation, which lives on CoachAccess.status, not here."""

    __tablename__ = "coach_invites"

    id: Mapped[uuid.UUID] = _uuid_pk()
    coach_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="CASCADE")
    )
    singer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    # pending|accepted|declined|revoked
    status: Mapped[str] = mapped_column(String(20), default="pending")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CoachAccess(Base, TimestampMixin):
    """The authorization-check table every coach-reads-singer endpoint actually queries —
    upserted in place, not append-only. ConsentRecord (consent_type="coach_sharing") is the
    separate append-only audit trail of the events that changed this row; a timestamped ledger
    is the wrong thing to query at request time for "is this currently allowed."

    One active coach per singer at a time (founder decision, Phase II plan section 1) is
    enforced at the database level, not just in the accept-invite endpoint, so it holds even
    under a race between two simultaneous accepts."""

    __tablename__ = "coach_access"
    __table_args__ = (
        UniqueConstraint("coach_id", "singer_user_id", name="uq_coach_access_pair"),
        Index(
            "uq_one_active_coach_per_singer",
            "singer_user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    coach_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="CASCADE")
    )
    singer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    invite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_invites.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|revoked
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "singer"|"coach"


class CoachAccessCategoryGrant(Base, TimestampMixin):
    """Per-category authorization state — the "per-category consent" non-negotiable
    (PRIVACY.md section 3) made queryable. One row per (coach_access, category); category is a
    fixed whitelist (recovery_trends | vocal_range | exercise_history | recordings). Toggling
    one category off (PATCH /api/v1/coach-connections/{id}/categories) never affects the
    others, and never touches CoachAccess.status itself — that's what makes this genuinely
    per-category rather than all-or-nothing."""

    __tablename__ = "coach_access_category_grants"
    __table_args__ = (
        UniqueConstraint("coach_access_id", "category", name="uq_grant_access_category"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    coach_access_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_access.id", ondelete="CASCADE")
    )
    category: Mapped[str] = mapped_column(String(50))
    granted: Mapped[bool] = mapped_column(Boolean, default=False)


class CoachAssignment(Base, TimestampMixin):
    """A coach's exercise assignment for a singer. History kept (superseded, not deleted) —
    same pattern as VocalPlan. Only ever consumed by app/exercise_routine.py while
    coach_access_id's linked CoachAccess is still active — see app/coach_assignment.py. Never
    bypasses app/exercise_routine.py's intensity-cap safety filter; see that module for the
    integration point."""

    __tablename__ = "coach_assignments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    coach_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="CASCADE")
    )
    singer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    coach_access_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_access.id", ondelete="CASCADE")
    )
    exercise_ids: Mapped[list] = mapped_column(JSON)  # ordered list of Exercise UUID strings
    note_to_singer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|superseded
    # Optional per-exercise target note, e.g. {"<exercise_id>": "G4"} -- keys are always a
    # subset of exercise_ids (validated at creation, see schemas_coach.py), values always a
    # valid note name (validated via app.vocal_range.note_name_to_midi). Parallel to
    # exercise_ids rather than folded into it so the ordered-list shape above never changes.
    exercise_tone_targets: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class CoachNote(Base, TimestampMixin):
    """Coach-authored, singer-readable by design — never a clinical chart (MEDICAL_SAFETY.md).
    Immutable once created; mistakes are soft-deleted (deleted_at), not hard-deleted, so the
    audit trail survives. `flagged_terms` is set when app/coach_notes.py's blocklist check
    matches a MEDICAL_SAFETY.md section 1 prohibited-pattern term — the note still saves; this
    is friction for review, not a hard block, since legitimate escalation language ("see an
    ENT") must never be prevented."""

    __tablename__ = "coach_notes"

    id: Mapped[uuid.UUID] = _uuid_pk()
    coach_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_profiles.id", ondelete="CASCADE")
    )
    singer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    coach_access_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_access.id", ondelete="CASCADE")
    )
    body: Mapped[str] = mapped_column(Text)  # max length enforced at the Pydantic schema layer
    flagged_terms: Mapped[list | None] = mapped_column(JSON, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
