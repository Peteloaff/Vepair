"""Stage 4 simulated-user test plan: stable, improving, declining, single-anomaly,
bad-microphone, and missing-days scenarios, driven through the real upload + baseline
endpoints (not the pure statistics unit-tested in tests/unit/test_baseline.py).

Confirms the product brief's explicit acceptance criteria:
  - bad recordings do not corrupt baseline
  - single anomalies do not permanently shift baseline
  - progressive changes are detectable
  - baseline confidence increases appropriately
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.models import Recording
from tests.integration.test_recordings import make_wav, sine_tone

MIN_SAMPLES_FOR_ANOMALY_DETECTION = 5


def upload_tone(client, headers, freq_hz, duration_s=2.0, sample_type="sustained_ah"):
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    wav_bytes = make_wav(sine_tone(freq_hz, duration_s, amplitude=0.5))
    resp = client.post(
        f"/api/v1/voice-sessions/{session_id}/recordings",
        headers=headers,
        data={"sample_type": sample_type},
        files={"file": ("recording.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def get_baseline(client, headers):
    resp = client.get("/api/v1/baseline", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def f0_baseline(summary):
    for b in summary["voice_baselines"]:
        if b["metric_name"] == "f0_mean_hz":
            return b
    return None


def test_stable_user_no_anomalies_and_confidence_increases(client, signed_up_user) -> None:
    _user, headers = signed_up_user

    for _ in range(8):
        body = upload_tone(client, headers, 220.0)
        assert body["anomalies"] == []

    summary = get_baseline(client, headers)
    assert summary["usable_session_count"] == 8
    assert summary["voice_confidence_pct"] > 0
    baseline = f0_baseline(summary)
    assert baseline["median_value"] == pytest.approx(220.0, abs=1.0)


def test_confidence_increases_monotonically_as_sessions_accumulate(
    client, signed_up_user
) -> None:
    _user, headers = signed_up_user

    seen_pct = []
    for _ in range(6):
        upload_tone(client, headers, 220.0)
        seen_pct.append(get_baseline(client, headers)["voice_confidence_pct"])

    assert seen_pct == sorted(seen_pct)
    assert seen_pct[-1] > seen_pct[0]


def _pitch_anomaly_metrics(body):
    """Pure synthetic sine tones have near-zero jitter/shimmer noise, so those metrics can
    trip the documented zero-MAD "any deviation is an anomaly" fallback path on essentially
    meaningless floating-point differences (see test_zero_mad_baseline_flags_any_deviation
    in tests/unit/test_baseline.py) — that's a synthetic-signal artifact, not what this test
    is checking. We only care whether the deliberately-varied pitch metrics get flagged.
    """
    pitch_metrics = {"f0_mean_hz", "f0_min_hz", "f0_max_hz", "pitch_stability_semitones"}
    return {a["metric_name"] for a in body["anomalies"]} & pitch_metrics


def test_slow_improvement_is_not_flagged_as_anomaly(client, signed_up_user) -> None:
    """A gradual upward drift (e.g. pitch range opening up over weeks) is a real trend,
    not a one-off anomaly — it should never trip the anomaly detector."""
    _user, headers = signed_up_user

    freqs = [220.0 + i * 0.8 for i in range(12)]  # 220.0 -> 228.8 in small steps
    for f in freqs:
        body = upload_tone(client, headers, f)
        assert _pitch_anomaly_metrics(body) == set(), f"unexpected pitch anomaly at f0={f}"


def test_slow_decline_is_not_flagged_as_anomaly(client, signed_up_user) -> None:
    _user, headers = signed_up_user

    freqs = [220.0 - i * 0.8 for i in range(12)]  # 220.0 -> 211.2 in small steps
    for f in freqs:
        body = upload_tone(client, headers, f)
        assert _pitch_anomaly_metrics(body) == set(), f"unexpected pitch anomaly at f0={f}"


def test_one_day_anomaly_does_not_permanently_shift_baseline(client, signed_up_user) -> None:
    _user, headers = signed_up_user

    for _ in range(8):
        upload_tone(client, headers, 220.0)

    baseline_before = f0_baseline(get_baseline(client, headers))
    median_before = baseline_before["median_value"]

    anomalous = upload_tone(client, headers, 320.0)
    anomaly_metrics = {a["metric_name"] for a in anomalous["anomalies"]}
    assert "f0_mean_hz" in anomaly_metrics

    baseline_after_anomaly = f0_baseline(get_baseline(client, headers))
    assert abs(baseline_after_anomaly["median_value"] - median_before) < 5.0

    next_normal = upload_tone(client, headers, 220.0)
    assert next_normal["anomalies"] == []

    baseline_final = f0_baseline(get_baseline(client, headers))
    assert baseline_final["median_value"] == pytest.approx(220.0, abs=2.0)


def test_bad_microphone_data_does_not_corrupt_baseline(client, signed_up_user) -> None:
    """A too-short/unanalyzable recording gets no AcousticMeasurement row (see
    test_upload_too_short_recording_has_no_measurement_but_still_succeeds), so it must not
    count toward usable sessions or move the baseline at all."""
    _user, headers = signed_up_user

    for _ in range(6):
        upload_tone(client, headers, 220.0)

    summary_before = get_baseline(client, headers)

    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    short_wav = make_wav(sine_tone(220.0, 0.1, amplitude=0.5))
    resp = client.post(
        f"/api/v1/voice-sessions/{session_id}/recordings",
        headers=headers,
        data={"sample_type": "sustained_ah"},
        files={"file": ("recording.wav", short_wav, "audio/wav")},
    )
    assert resp.status_code == 201
    assert resp.json()["measurement"] is None
    assert resp.json()["anomalies"] == []

    summary_after = get_baseline(client, headers)
    assert summary_after["usable_session_count"] == summary_before["usable_session_count"]
    assert f0_baseline(summary_after) == f0_baseline(summary_before)


def test_missing_days_between_sessions_still_accumulate_into_baseline(
    client, signed_up_user, db_session
) -> None:
    """Real usage won't be one-a-day: baseline computation must not assume or require
    consecutive-day sessions, only that enough usable sessions exist."""
    _user, headers = signed_up_user

    recording_ids = []
    for _ in range(6):
        body = upload_tone(client, headers, 220.0)
        recording_ids.append(body["id"])

    # Backdate the recordings to simulate large gaps (e.g. over two months of once-a-week
    # sessions) rather than all landing "today".
    for i, rec_id in enumerate(recording_ids):
        recording = db_session.get(Recording, rec_id)
        recording.created_at = datetime.now(UTC) - timedelta(days=(len(recording_ids) - i) * 9)
    db_session.commit()

    # The stored Baseline row is a snapshot updated on each upload, not recomputed on GET, so
    # one more upload is needed to fold the backdated window into it — this mirrors how a real
    # user's baseline only updates when they actually record again after a gap.
    upload_tone(client, headers, 220.0)

    summary = get_baseline(client, headers)
    assert summary["usable_session_count"] == 7
    baseline = f0_baseline(summary)
    assert baseline["sample_count"] == 7
    assert baseline["median_value"] == pytest.approx(220.0, abs=1.0)
    assert baseline["window_start"] < baseline["window_end"]
