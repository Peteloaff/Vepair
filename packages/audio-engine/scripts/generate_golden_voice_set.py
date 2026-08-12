#!/usr/bin/env python
"""Regenerates the Golden Voice Set WAV files under data/fixtures/golden-voice-set/.

These are checked into the repo (small, deterministic, synthetic — no reason to regenerate
on every run), so this script only needs to be re-run if a generator in fixtures.py changes.
Run from anywhere with the audio-engine package installed:

    python packages/audio-engine/scripts/generate_golden_voice_set.py
"""

import sys
from pathlib import Path

import soundfile as sf

from vepair_audio_engine.fixtures import GOLDEN_VOICE_SET

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = REPO_ROOT / "data" / "fixtures" / "golden-voice-set"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, generator in GOLDEN_VOICE_SET.items():
        samples, sample_rate = generator()
        path = OUTPUT_DIR / f"{name}.wav"
        sf.write(path, samples, sample_rate, subtype="PCM_16")
        print(f"wrote {path.relative_to(REPO_ROOT)} ({len(samples) / sample_rate:.1f}s)")


if __name__ == "__main__":
    sys.exit(main())
