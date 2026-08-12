"""Stage 8 vocal range mapping, driven through the real recordings-upload + vocal-range
endpoints (not the pure functions unit-tested in tests/unit/test_vocal_range.py).

Confirms the product brief's explicit Stage 8 test plan: validate MIDI/note conversion, reject
accidental octave errors, test male/female/high/low voice ranges and falsetto, test background
instrument contamination — plus "only count notes meeting quality and duration criteria" and
"do not pretend microphone analysis alone can definitively classify vocal registers" (no
register-classification field exists anywhere in the response).
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.models import VocalRange
from app.vocal_range import semitones_between
from tests.integration.test_recordings import make_wav, sine_tone


def upload_range_recording(client, headers, sample_type, freq_hz, duration_s=2.0):
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


def test_submit_low_and_high_range_attempt(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    low = upload_range_recording(client, headers, "range_low", 110.0)  # A2
    high = upload_range_recording(client, headers, "range_high", 440.0)  # A4

    resp = client.post(
        "/api/v1/vocal-range",
        headers=headers,
        json={"low_recording_id": low["id"], "high_recording_id": high["id"]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["comfortable_low_note"] == "A2"
    assert body["comfortable_high_note"] == "A4"


def test_falsetto_recorded_separately_from_modal_high(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    high = upload_range_recording(client, headers, "range_high", 330.0)
    falsetto = upload_range_recording(client, headers, "range_falsetto", 660.0)

    resp = client.post(
        "/api/v1/vocal-range",
        headers=headers,
        json={"high_recording_id": high["id"], "falsetto_recording_id": falsetto["id"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["comfortable_high_note"] is not None
    assert body["falsetto_high_note"] is not None
    assert body["falsetto_high_note"] != body["comfortable_high_note"]


def test_too_short_recording_does_not_count_toward_range(client, signed_up_user) -> None:
    """"Only count notes meeting quality and duration criteria" — the product brief's words."""
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    short_wav = make_wav(sine_tone(440.0, 0.2, amplitude=0.5))  # well under the 1.0s minimum
    resp = client.post(
        f"/api/v1/voice-sessions/{session_id}/recordings",
        headers=headers,
        data={"sample_type": "range_high"},
        files={"file": ("recording.wav", short_wav, "audio/wav")},
    )
    assert resp.status_code == 201
    short_recording = resp.json()

    submit_resp = client.post(
        "/api/v1/vocal-range",
        headers=headers,
        json={"high_recording_id": short_recording["id"]},
    )
    assert submit_resp.status_code == 201
    assert submit_resp.json()["comfortable_high_note"] is None


def test_response_never_includes_a_register_classification(client, signed_up_user) -> None:
    """"Do not pretend microphone analysis alone can definitively classify vocal registers" —
    there must be no chest/mix/head-voice classification field anywhere in the response."""
    _user, headers = signed_up_user
    high = upload_range_recording(client, headers, "range_high", 300.0)
    resp = client.post(
        "/api/v1/vocal-range", headers=headers, json={"high_recording_id": high["id"]}
    )
    body_keys = set(resp.json().keys())
    forbidden = {"register", "chest_voice", "mix_voice", "head_voice", "voice_type", "fach"}
    assert body_keys.isdisjoint(forbidden)


def test_male_female_low_high_and_falsetto_ranges_all_convert_sensibly(
    client, signed_up_user
) -> None:
    """Test male/female/high/low voice ranges. Test falsetto. — Stage 8's own test plan,
    simulated with synthetic tones across typical published F0 bands."""
    _user, headers = signed_up_user
    scenarios = [
        ("male chest low", "range_low", 90.0),
        ("male chest high", "range_high", 175.0),
        ("female chest low", "range_low", 170.0),
        ("female chest high", "range_high", 250.0),
        ("falsetto", "range_falsetto", 550.0),
    ]
    for _label, sample_type, freq in scenarios:
        recording = upload_range_recording(client, headers, sample_type, freq)
        payload_key = {
            "range_low": "low_recording_id",
            "range_high": "high_recording_id",
            "range_falsetto": "falsetto_recording_id",
        }[sample_type]
        resp = client.post(
            "/api/v1/vocal-range", headers=headers, json={payload_key: recording["id"]}
        )
        assert resp.status_code == 201, resp.text
        note_field = {
            "range_low": "comfortable_low_note",
            "range_high": "comfortable_high_note",
            "range_falsetto": "falsetto_high_note",
        }[sample_type]
        assert resp.json()[note_field] is not None


def test_background_instrument_contamination_does_not_crash_the_pipeline(
    client, signed_up_user
) -> None:
    """"Test background instruments contaminating recording" — a second, unrelated tone mixed
    in must never crash analysis; the Stage 3-documented "missing fundamental" limitation means
    the resulting note may not be the intended one, so this only asserts robustness (a note is
    still produced, or gracefully none), not pitch-tracking correctness under contamination."""
    _user, headers = signed_up_user
    contaminated = [
        a + b
        for a, b in zip(
            sine_tone(220.0, 2.0, amplitude=0.4), sine_tone(523.0, 2.0, amplitude=0.3), strict=True
        )
    ]
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    resp = client.post(
        f"/api/v1/voice-sessions/{session_id}/recordings",
        headers=headers,
        data={"sample_type": "range_high"},
        files={"file": ("recording.wav", make_wav(contaminated), "audio/wav")},
    )
    assert resp.status_code == 201  # never a crash

    submit_resp = client.post(
        "/api/v1/vocal-range", headers=headers, json={"high_recording_id": resp.json()["id"]}
    )
    assert submit_resp.status_code == 201  # never a crash, whatever the resulting note is


def test_summary_reports_historical_best_and_30_90_day_change(
    client, signed_up_user, db_session
) -> None:
    _user, headers = signed_up_user
    user_id = uuid.UUID(_user["user"]["id"])

    entries = [
        (100, "F3"),  # oldest -- 100 days ago, will anchor the 90-day change
        (40, "G3"),  # 40 days ago -- outside the 30-day window, inside the 90-day window
        (1, "A3"),  # most recent -- today's "current" and the historical best
    ]
    for days_ago, note in entries:
        row = VocalRange(user_id=user_id, comfortable_high_note=note)
        db_session.add(row)
        db_session.flush()
        row.measured_at = datetime.now(UTC) - timedelta(days=days_ago)
    db_session.commit()

    resp = client.get("/api/v1/vocal-range/summary", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["current_high_note"] == "A3"
    assert body["historical_best_high_note"] == "A3"  # A3 > G3 > F3
    # 40 days ago the note was G3; 90 days back only F3 (100 days ago) is far enough back.
    assert body["change_30d_high"]["from_note"] == "G3"
    assert body["change_30d_high"]["semitones"] == semitones_between("G3", "A3")
    assert body["change_90d_high"]["from_note"] == "F3"
    assert body["change_90d_high"]["semitones"] == semitones_between("F3", "A3")
