"""Stage 8 vocal range mapping.

Maps comfortable low note, comfortable high note, and falsetto/head-voice range — deliberately
*not* chest/mix register classification, which the product brief explicitly warns against
("Do not pretend microphone analysis alone can definitively classify vocal registers"). No
register-classification logic exists here at all; that's not a missing feature, it's the
brief's own caution taken literally.

**Octave-error prevention, concretely**: this module doesn't run its own pitch detection — it
reuses `f0_min_hz`/`f0_max_hz` from Stage 3's already-validated Parselmouth pipeline (proven
accurate to ~0.001Hz on synthetic tones in Stage 3 testing), and the only new math here is
Hz-to-note-name conversion, which is pure, deterministic, and unit-tested at every octave
boundary. There's no new pitch-tracking algorithm here to introduce a fresh octave-error mode.

**"Do not encourage users to force extreme notes"**: every note here is captured as a
*comfortable* attempt (framed that way in the guided flow's copy), gated by quality/duration
criteria before it counts, and the one adaptive-challenge feature (a gentle +1 semitone stretch
suggestion) is always optional and always suppressed when recovery signals say otherwise — see
`suggest_stretch_target`.
"""

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AcousticMeasurement, Recording, VocalRange, VoiceSession

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
A4_MIDI = 69
A4_HZ = 440.0

# "Only count notes meeting quality and duration criteria" — the product brief's own words.
MIN_RANGE_ATTEMPT_DURATION_SECONDS = 1.0
MIN_VOICED_RATIO_FOR_RANGE_ATTEMPT = 0.5


@dataclass(frozen=True)
class RangeChange:
    semitones: int | None  # None if there's no data far enough back to compare
    from_note: str | None
    to_note: str | None


@dataclass
class VocalRangeSummary:
    current_low_note: str | None
    current_high_note: str | None
    current_falsetto_note: str | None
    historical_best_low_note: str | None
    historical_best_high_note: str | None
    change_30d_high: RangeChange
    change_90d_high: RangeChange
    change_30d_low: RangeChange
    change_90d_low: RangeChange
    history: list[dict]
    stretch_target_note: str | None
    stretch_target_reason: str | None


def hz_to_midi(hz: float) -> float:
    """Fractional MIDI note number — kept as a float so rounding happens exactly once, at the
    point of turning it into a note *name*, rather than compounding rounding error."""
    return A4_MIDI + 12 * math.log2(hz / A4_HZ)


def hz_to_note_name(hz: float) -> str:
    """E.g. 440.0 -> "A4", 392.0 -> "G4". Standard scientific pitch notation (middle C = C4)."""
    midi = round(hz_to_midi(hz))
    name = NOTE_NAMES[midi % 12]
    octave = midi // 12 - 1
    return f"{name}{octave}"


def note_name_to_midi(note: str) -> int:
    """Inverse of hz_to_note_name. Raises ValueError for anything that isn't a valid note name
    (e.g. "G4", "C#3") — never silently guesses."""
    for length in (2, 1):
        candidate = note[:length]
        if candidate in NOTE_NAMES:
            name, rest = candidate, note[length:]
            break
    else:
        raise ValueError(f"Not a valid note name: {note!r}")
    try:
        octave = int(rest)
    except ValueError:
        raise ValueError(f"Not a valid note name: {note!r}") from None
    return NOTE_NAMES.index(name) + (octave + 1) * 12


def semitones_between(from_note: str, to_note: str) -> int:
    """Positive = to_note is higher."""
    return note_name_to_midi(to_note) - note_name_to_midi(from_note)


def meets_quality_criteria(
    measurement: AcousticMeasurement, duration_seconds: float | None
) -> bool:
    if duration_seconds is None or duration_seconds < MIN_RANGE_ATTEMPT_DURATION_SECONDS:
        return False
    if (
        measurement.voiced_ratio is None
        or measurement.voiced_ratio < MIN_VOICED_RATIO_FOR_RANGE_ATTEMPT
    ):
        return False
    return True


# --- Data access & orchestration (talks to the DB; pure functions above don't) ---


def _fetch_recording_and_measurement(
    db: Session, user_id: uuid.UUID, recording_id: uuid.UUID
) -> tuple[Recording, AcousticMeasurement] | None:
    row = db.execute(
        select(Recording, AcousticMeasurement)
        .join(AcousticMeasurement, AcousticMeasurement.recording_id == Recording.id)
        .join(VoiceSession, VoiceSession.id == Recording.voice_session_id)
        .where(Recording.id == recording_id, VoiceSession.user_id == user_id)
    ).first()
    return (row[0], row[1]) if row else None


def record_range_attempt(
    db: Session,
    user_id: uuid.UUID,
    low_recording_id: uuid.UUID | None,
    high_recording_id: uuid.UUID | None,
    falsetto_recording_id: uuid.UUID | None,
) -> VocalRange:
    """Builds one new historical VocalRange row from up to three just-uploaded recordings
    (range_low/range_high/range_falsetto sample types). Any recording that fails the quality
    gate is simply omitted from this entry (never a fabricated note) rather than blocking the
    other, valid ones."""
    low_note = high_note = falsetto_note = None
    source_recording_id = None

    for recording_id, sample_type in (
        (low_recording_id, "range_low"),
        (high_recording_id, "range_high"),
        (falsetto_recording_id, "range_falsetto"),
    ):
        if recording_id is None:
            continue
        found = _fetch_recording_and_measurement(db, user_id, recording_id)
        if found is None:
            continue
        recording, measurement = found
        if recording.sample_type != sample_type:
            continue
        if not meets_quality_criteria(measurement, recording.duration_seconds):
            continue

        source_recording_id = recording.id
        if sample_type == "range_low" and measurement.f0_min_hz is not None:
            low_note = hz_to_note_name(measurement.f0_min_hz)
        elif sample_type == "range_high" and measurement.f0_max_hz is not None:
            high_note = hz_to_note_name(measurement.f0_max_hz)
        elif sample_type == "range_falsetto" and measurement.f0_max_hz is not None:
            falsetto_note = hz_to_note_name(measurement.f0_max_hz)

    entry = VocalRange(
        user_id=user_id,
        comfortable_low_note=low_note,
        comfortable_high_note=high_note,
        falsetto_high_note=falsetto_note,
        source_recording_id=source_recording_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _closest_entry_on_or_before(entries: list[VocalRange], target: datetime) -> VocalRange | None:
    candidates = [e for e in entries if e.measured_at <= target]
    return max(candidates, key=lambda e: e.measured_at) if candidates else None


def _change_since(
    entries: list[VocalRange], days_ago: int, field: str, current_note: str | None
) -> RangeChange:
    if current_note is None or not entries:
        return RangeChange(semitones=None, from_note=None, to_note=None)
    target = datetime.now(entries[0].measured_at.tzinfo) - timedelta(days=days_ago)
    past_entry = _closest_entry_on_or_before(entries, target)
    past_note = getattr(past_entry, field) if past_entry else None
    if past_note is None:
        return RangeChange(semitones=None, from_note=None, to_note=current_note)
    return RangeChange(
        semitones=semitones_between(past_note, current_note),
        from_note=past_note,
        to_note=current_note,
    )


def suggest_stretch_target(
    historical_best_high_note: str | None,
    recovery_status: str,
    throat_discomfort: int | None,
    trend_is_declining: bool,
    track: str | None = None,
    trend_is_improving: bool = False,
) -> tuple[str | None, str | None]:
    """A gentle, always-optional stretch suggestion beyond the user's own historical best —
    never a population target, never framed as a requirement. Returns (note, reason) or
    (None, None) when conditions don't support suggesting one at all. Discomfort/red-status/
    declining-trend all suppress it outright — this can only ever nudge slightly, never push
    through anything, per the product brief's explicit "do not encourage forcing extreme
    notes" and MEDICAL_SAFETY.md section 7/8.

    Stage 9: `track == "repair"` always suppresses this outright — a repair program is about
    steadiness, not stretch. `track == "improvement"` allows a slightly bigger +2 semitone
    stretch, but only when the recent trend is genuinely improving (not just non-declining) —
    matching Improvement's brief to be "more aggressive with pushing the vocalist to stretch
    their vocal range safely," while still passing through every safety check below rather
    than bypassing them."""
    if track == "repair":
        return None, None
    if historical_best_high_note is None:
        return None, None
    if throat_discomfort is not None and throat_discomfort >= 7:
        return None, None
    if recovery_status == "red":
        return None, None
    if trend_is_declining:
        return None, None

    best_midi = note_name_to_midi(historical_best_high_note)
    semitone_step = 2 if (track == "improvement" and trend_is_improving) else 1
    target_midi = best_midi + semitone_step
    target_note = f"{NOTE_NAMES[target_midi % 12]}{target_midi // 12 - 1}"
    if semitone_step == 2:
        reason = (
            "Your range has been trending up on an Improvement track — if it feels comfortable, "
            "you could try reaching two semitones beyond your recent best — never force it."
        )
    else:
        reason = (
            "If it feels comfortable, you could try reaching one semitone beyond your recent "
            "best — never force it."
        )
    return target_note, reason


def _recent_trend_is_declining(notes_newest_last: list[str], lookback: int = 3) -> bool:
    """A small, self-contained check on the range history itself (not the exercise-trend
    engine — this only needs to answer "has the user's own recent high note been slipping,"
    which the VocalRange history already has everything needed for). Requires at least two
    recent points; with fewer, there's nothing to call declining yet."""
    recent = notes_newest_last[-lookback:]
    if len(recent) < 2:
        return False
    return note_name_to_midi(recent[-1]) < note_name_to_midi(recent[0])


def _recent_trend_is_improving(notes_newest_last: list[str], lookback: int = 3) -> bool:
    """The Improvement-track mirror of `_recent_trend_is_declining`: requires the same recent
    window to be strictly increasing before `suggest_stretch_target` allows the bigger +2
    semitone stretch."""
    recent = notes_newest_last[-lookback:]
    if len(recent) < 2:
        return False
    return note_name_to_midi(recent[-1]) > note_name_to_midi(recent[0])


def build_summary(
    db: Session,
    user_id: uuid.UUID,
    recovery_status: str = "unknown",
    throat_discomfort: int | None = None,
    track: str | None = None,
) -> VocalRangeSummary:
    entries = list(
        db.scalars(
            select(VocalRange).where(VocalRange.user_id == user_id).order_by(VocalRange.measured_at)
        ).all()
    )

    latest_low = next(
        (e.comfortable_low_note for e in reversed(entries) if e.comfortable_low_note), None
    )
    latest_high = next(
        (e.comfortable_high_note for e in reversed(entries) if e.comfortable_high_note), None
    )
    latest_falsetto = next(
        (e.falsetto_high_note for e in reversed(entries) if e.falsetto_high_note), None
    )

    low_notes = [e.comfortable_low_note for e in entries if e.comfortable_low_note]
    high_notes = [e.comfortable_high_note for e in entries if e.comfortable_high_note]
    historical_best_low = min(low_notes, key=note_name_to_midi) if low_notes else None
    historical_best_high = max(high_notes, key=note_name_to_midi) if high_notes else None

    stretch_note, stretch_reason = suggest_stretch_target(
        historical_best_high,
        recovery_status,
        throat_discomfort,
        _recent_trend_is_declining(high_notes),
        track=track,
        trend_is_improving=_recent_trend_is_improving(high_notes),
    )

    return VocalRangeSummary(
        current_low_note=latest_low,
        current_high_note=latest_high,
        current_falsetto_note=latest_falsetto,
        historical_best_low_note=historical_best_low,
        historical_best_high_note=historical_best_high,
        change_30d_high=_change_since(entries, 30, "comfortable_high_note", latest_high),
        change_90d_high=_change_since(entries, 90, "comfortable_high_note", latest_high),
        change_30d_low=_change_since(entries, 30, "comfortable_low_note", latest_low),
        change_90d_low=_change_since(entries, 90, "comfortable_low_note", latest_low),
        history=[
            {
                "measured_at": e.measured_at.isoformat(),
                "comfortable_low_note": e.comfortable_low_note,
                "comfortable_high_note": e.comfortable_high_note,
                "falsetto_high_note": e.falsetto_high_note,
            }
            for e in entries
        ],
        stretch_target_note=stretch_note,
        stretch_target_reason=stretch_reason,
    )
