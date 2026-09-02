import array
import io
import math
import uuid
import wave

import pytest
from sqlalchemy import select

from app.models import Recording

SAMPLE_RATE = 16000


def make_wav(samples: list[float], sample_rate: int = SAMPLE_RATE, channels: int = 1) -> bytes:
    clamped = [max(-1.0, min(1.0, s)) for s in samples]
    ints = array.array("h", [int(s * 32767) for s in clamped])
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(ints.tobytes())
    return buf.getvalue()


def sine_tone(freq_hz: float, duration_s: float, amplitude: float = 0.5) -> list[float]:
    n = int(SAMPLE_RATE * duration_s)
    return [amplitude * math.sin(2 * math.pi * freq_hz * i / SAMPLE_RATE) for i in range(n)]


def clean_wav_bytes(duration_s: float = 2.0) -> bytes:
    return make_wav(sine_tone(220, duration_s, amplitude=0.5))


def upload_file(client, headers, session_id, sample_type="sustained_ah", wav_bytes=None):
    return client.post(
        f"/api/v1/voice-sessions/{session_id}/recordings",
        headers=headers,
        data={"sample_type": sample_type},
        files={"file": ("recording.wav", wav_bytes or clean_wav_bytes(), "audio/wav")},
    )


def test_create_voice_session_without_device_metadata(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.post("/api/v1/voice-sessions", headers=headers, json={})
    assert resp.status_code == 201
    body = resp.json()
    assert body["device_metadata_id"] is None
    assert body["completed_at"] is None


def test_create_voice_session_with_device_metadata(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.post(
        "/api/v1/voice-sessions",
        headers=headers,
        json={"device_type": "mobile", "microphone_name": "iPhone mic", "os_info": "iOS 18"},
    )
    assert resp.status_code == 201
    assert resp.json()["device_metadata_id"] is not None


def test_device_metadata_is_reused_across_sessions(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    device = {"device_type": "desktop", "microphone_name": "Blue Yeti", "os_info": "Windows 11"}

    first = client.post("/api/v1/voice-sessions", headers=headers, json=device)
    second = client.post("/api/v1/voice-sessions", headers=headers, json=device)

    assert first.json()["device_metadata_id"] == second.json()["device_metadata_id"]


def test_list_voice_sessions(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    client.post("/api/v1/voice-sessions", headers=headers, json={})
    client.post("/api/v1/voice-sessions", headers=headers, json={})

    resp = client.get("/api/v1/voice-sessions", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_complete_voice_session(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    resp = client.patch(f"/api/v1/voice-sessions/{session_id}/complete", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is not None


def test_upload_clean_recording(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    resp = upload_file(client, headers, session_id)
    assert resp.status_code == 201
    body = resp.json()
    assert body["sample_type"] == "sustained_ah"
    assert body["sample_rate"] == SAMPLE_RATE
    assert 1.9 < body["duration_seconds"] < 2.1
    flags = body["quality_flags"]
    assert flags["clipping"] is False
    assert flags["too_quiet"] is False
    assert flags["too_short"] is False


def test_upload_tone_baseline_sample_gets_full_measurement(client, signed_up_user) -> None:
    """The Tone Match "find your average pitch" recorder (Goal Tones, app/vocal_goals.py) --
    an ordinary sustained sample, so it reuses the exact same upload/measurement pipeline as
    sustained_ah, just under a different sample_type."""
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    resp = upload_file(client, headers, session_id, sample_type="tone_baseline")
    assert resp.status_code == 201
    body = resp.json()
    assert body["sample_type"] == "tone_baseline"
    assert body["measurement"]["f0_mean_hz"] is not None


def test_upload_rejects_invalid_sample_type(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    resp = upload_file(client, headers, session_id, sample_type="not_a_real_type")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_sample_type"


def test_upload_rejects_non_wav_bytes(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    resp = client.post(
        f"/api/v1/voice-sessions/{session_id}/recordings",
        headers=headers,
        data={"sample_type": "hum"},
        files={"file": ("recording.wav", b"not a real wav file", "audio/wav")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_audio"


def test_upload_flags_clipped_audio(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    clipped = make_wav(sine_tone(220, 2.0, amplitude=3.0))
    resp = upload_file(client, headers, session_id, wav_bytes=clipped)
    assert resp.json()["quality_flags"]["clipping"] is True


def test_upload_flags_silent_audio(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    silent = make_wav([0.0] * SAMPLE_RATE * 2)
    resp = upload_file(client, headers, session_id, wav_bytes=silent)
    assert resp.json()["quality_flags"]["too_quiet"] is True


def test_upload_flags_short_audio(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    short = make_wav(sine_tone(220, 0.1, amplitude=0.5))
    resp = upload_file(client, headers, session_id, wav_bytes=short)
    assert resp.json()["quality_flags"]["too_short"] is True


def test_get_session_includes_uploaded_recordings(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    upload_file(client, headers, session_id, sample_type="sustained_ah")
    upload_file(client, headers, session_id, sample_type="hum")

    resp = client.get(f"/api/v1/voice-sessions/{session_id}", headers=headers)
    assert resp.status_code == 200
    recordings = resp.json()["recordings"]
    assert {r["sample_type"] for r in recordings} == {"sustained_ah", "hum"}


def test_recording_audio_is_byte_identical_after_round_trip(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    original = clean_wav_bytes()

    recording_id = upload_file(client, headers, session_id, wav_bytes=original).json()["id"]

    resp = client.get(f"/api/v1/recordings/{recording_id}/audio", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    assert resp.content == original


def test_recordings_require_authentication(client) -> None:
    assert client.get("/api/v1/voice-sessions").status_code == 401
    assert client.post("/api/v1/voice-sessions", json={}).status_code == 401


def test_user_cannot_access_another_users_session(client, signed_up_user) -> None:
    _user_a, headers_a = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers_a, json={}).json()["id"]

    signup_b = client.post(
        "/api/v1/auth/signup",
        json={"email": "recordings-user-b@example.com", "password": "correcthorse123"},
    )
    headers_b = {"Authorization": f"Bearer {signup_b.json()['access_token']}"}

    assert client.get(f"/api/v1/voice-sessions/{session_id}", headers=headers_b).status_code == 404
    assert upload_file(client, headers_b, session_id).status_code == 404


def test_user_cannot_play_back_another_users_recording(client, signed_up_user) -> None:
    _user_a, headers_a = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers_a, json={}).json()["id"]
    recording_id = upload_file(client, headers_a, session_id).json()["id"]

    signup_b = client.post(
        "/api/v1/auth/signup",
        json={"email": "recordings-user-b2@example.com", "password": "correcthorse123"},
    )
    headers_b = {"Authorization": f"Bearer {signup_b.json()['access_token']}"}

    resp = client.get(f"/api/v1/recordings/{recording_id}/audio", headers=headers_b)
    assert resp.status_code == 404


# --- Stage 3: acoustic analysis wiring ---


def test_upload_populates_acoustic_measurement(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    resp = upload_file(client, headers, session_id, sample_type="sustained_ah")
    assert resp.status_code == 201
    measurement = resp.json()["measurement"]
    assert measurement is not None
    assert measurement["f0_mean_hz"] == pytest.approx(220.0, abs=1.0)
    assert measurement["jitter_percent"] < 0.01
    assert measurement["hnr_db"] > 60


def test_upload_withholds_periodicity_measures_for_sentence(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    resp = upload_file(client, headers, session_id, sample_type="sentence")
    measurement = resp.json()["measurement"]
    assert measurement["jitter_percent"] is None
    assert measurement["shimmer_percent"] is None
    assert measurement["hnr_db"] is None
    assert measurement["f0_mean_hz"] is not None  # F0 remains valid for running speech


def test_upload_too_short_recording_has_no_measurement_but_still_succeeds(
    client, signed_up_user
) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    short_wav = make_wav(sine_tone(220, 0.1, amplitude=0.5))
    resp = upload_file(client, headers, session_id, wav_bytes=short_wav)

    assert resp.status_code == 201  # the recording itself is never blocked
    body = resp.json()
    assert body["measurement"] is None
    assert body["quality_flags"]["too_short"] is True


def test_upload_response_includes_recording_quality_score(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    resp = upload_file(client, headers, session_id)
    score = resp.json()["quality_flags"]["quality_score"]
    assert score["score"] == 100
    assert score["label"] == "excellent"
    assert set(score["components"].keys()) == {
        "clipping",
        "loudness",
        "duration",
        "background_noise",
    }


def test_session_detail_includes_nested_measurements(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    upload_file(client, headers, session_id, sample_type="hum")

    resp = client.get(f"/api/v1/voice-sessions/{session_id}", headers=headers)
    recordings = resp.json()["recordings"]
    assert len(recordings) == 1
    assert recordings[0]["measurement"]["f0_mean_hz"] == pytest.approx(220.0, abs=1.0)


# --- Data minimization: per-recording deletion + audio_available (A2/A3) ---


def test_uploaded_recording_reports_audio_available(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]

    resp = upload_file(client, headers, session_id)
    assert resp.json()["audio_available"] is True
    assert resp.json()["audio_purged_at"] is None
    # The raw storage key is never exposed to the client.
    assert "file_path" not in resp.json()


def test_list_voice_sessions_includes_nested_recordings(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    upload_file(client, headers, session_id, sample_type="hum")

    resp = client.get("/api/v1/voice-sessions", headers=headers)
    assert resp.status_code == 200
    session = next(s for s in resp.json() if s["id"] == session_id)
    assert len(session["recordings"]) == 1
    assert session["recordings"][0]["sample_type"] == "hum"


def test_user_can_delete_own_recording(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    recording_id = upload_file(client, headers, session_id).json()["id"]

    resp = client.delete(f"/api/v1/recordings/{recording_id}", headers=headers)
    assert resp.status_code == 204

    # Gone from the audio endpoint and from the session's recording list.
    audio = client.get(f"/api/v1/recordings/{recording_id}/audio", headers=headers)
    assert audio.status_code == 404

    session_detail = client.get(f"/api/v1/voice-sessions/{session_id}", headers=headers)
    assert session_detail.json()["recordings"] == []


def test_deleting_nonexistent_recording_404s(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.delete(f"/api/v1/recordings/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


def test_user_cannot_delete_another_users_recording(client, signed_up_user) -> None:
    _user_a, headers_a = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers_a, json={}).json()["id"]
    recording_id = upload_file(client, headers_a, session_id).json()["id"]

    signup_b = client.post(
        "/api/v1/auth/signup",
        json={"email": "recordings-delete-user-b@example.com", "password": "correcthorse123"},
    )
    headers_b = {"Authorization": f"Bearer {signup_b.json()['access_token']}"}

    resp = client.delete(f"/api/v1/recordings/{recording_id}", headers=headers_b)
    assert resp.status_code == 404

    # Still there for its actual owner.
    still_there = client.get(f"/api/v1/recordings/{recording_id}/audio", headers=headers_a)
    assert still_there.status_code == 200


def test_purged_recording_audio_endpoint_returns_audio_purged(
    client, db_session, signed_up_user
) -> None:
    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    recording_id = upload_file(client, headers, session_id).json()["id"]

    # Simulate the retention job having already purged this recording's audio.
    recording = db_session.scalar(select(Recording).where(Recording.id == recording_id))
    recording.file_path = None
    db_session.commit()

    resp = client.get(f"/api/v1/recordings/{recording_id}/audio", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "audio_purged"

    # Still listed, still has its measurement, just no playable audio.
    listed = client.get("/api/v1/voice-sessions", headers=headers)
    voice_session = next(s for s in listed.json() if s["id"] == session_id)
    assert voice_session["recordings"][0]["audio_available"] is False
    assert voice_session["recordings"][0]["measurement"] is not None
