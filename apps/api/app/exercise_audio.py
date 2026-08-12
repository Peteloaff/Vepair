"""Stage 8: "listen to your exercises." Analyzes an exercise attempt's audio using the same
Parselmouth/librosa pipeline Stage 3 already built and validated — not a new or different
"AI," the same real DSP measurement, just applied to a new kind of recording.

**Deliberately never written to storage.** Unlike `Recording` (Stage 2), which persists audio
for playback, exercise audio has no playback use case — only the derived numbers matter for
trend tracking. Analysis happens entirely in the request handler's memory and the bytes are
discarded when the request completes; see PRIVACY.md's "minimal collection" principle.

**Never feeds the personal baseline.** Exercise attempts are a different context from Stage 2's
guided recording sessions (different vocal demands, different exercise-specific targets), so
mixing them into Stage 4's baseline would blur what "your normal voice" means. Exercise trend
tracking (`app/exercise_trends.py`) is its own, separate history — not folded into `Baseline`.
"""

import logging

from vepair_audio_engine.measurements import (
    InsufficientAudioError,
    InvalidAudioError,
    analyze_wav_bytes,
)

from app.exercise_library import CATEGORY_ANALYSIS_SAMPLE_TYPE

logger = logging.getLogger("vepair.exercise_audio")


def analyze_exercise_attempt(audio_bytes: bytes, category: str) -> dict | None:
    """Best-effort, same principle as Stage 3's recording analysis: a clip too short or
    otherwise unanalyzable simply yields no measurement, never a blocked exercise log. Returns
    None outright for categories with no vocal signal (Breathing) without even attempting
    analysis."""
    sample_type = CATEGORY_ANALYSIS_SAMPLE_TYPE.get(category)
    if sample_type is None:
        return None
    try:
        measurements = analyze_wav_bytes(audio_bytes, sample_type)
    except (InvalidAudioError, InsufficientAudioError) as exc:
        logger.info("Skipping exercise audio analysis for category %s: %s", category, exc)
        return None
    return measurements.as_dict()
