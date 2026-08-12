"""Stage 5 simulated-user test plan, driven through the real check-in/upload/recovery-score
endpoints (not the pure functions unit-tested in tests/unit/test_recovery_score.py).

Confirms the product brief's explicit acceptance criteria:
  - good data raises appropriate components
  - poor sleep alone doesn't falsely indicate vocal injury
  - bad microphone recordings don't tank recovery score
  - high discomfort triggers appropriate safety guidance
  - score explanation mathematically matches score
  - same input always produces same score
"""

from datetime import date

from app.recovery_score import NEUTRAL_COMPONENT_SCORE
from tests.integration.test_baseline import upload_tone
from tests.integration.test_recordings import make_wav, sine_tone

TODAY = date.today().isoformat()

GOOD_CHECKIN = {
    "checkin_date": TODAY,
    "fatigue": 2,
    "throat_discomfort": 1,
    "sleep_hours": 8.0,
    "speaking_load": "low",
    "singing_load": "none",
    "hydration_estimate": "high",
    "rehearsal_or_performance_yesterday": False,
}


def post_checkin(client, headers, overrides=None):
    payload = {**GOOD_CHECKIN, **(overrides or {})}
    resp = client.post("/api/v1/checkins", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def get_score(client, headers, for_date=TODAY):
    resp = client.get("/api/v1/recovery-score", headers=headers, params={"date": for_date})
    assert resp.status_code == 200, resp.text
    return resp.json()


def component(score_body, key):
    return next(c for c in score_body["components"] if c["key"] == key)


def test_good_data_raises_appropriate_components(client, signed_up_user) -> None:
    _user, headers = signed_up_user

    for _ in range(6):
        upload_tone(client, headers, 220.0)
    post_checkin(client, headers)

    body = get_score(client, headers)
    assert body["score_value"] is not None
    assert body["score_value"] >= 80
    assert body["status"] == "green"

    for key in (
        "consistency_vs_baseline",
        "acoustic_stability",
        "subjective_fatigue",
        "sleep",
        "recent_vocal_load",
        "hydration",
    ):
        c = component(body, key)
        assert c["included"] is True
        assert c["score"] >= 75, f"{key} unexpectedly low: {c['score']}"

    assert len(body["factors"]) > 0
    assert all(f["direction"] == "positive" for f in body["factors"])


def test_poor_sleep_alone_does_not_falsely_indicate_injury(client, signed_up_user) -> None:
    _user, headers = signed_up_user

    post_checkin(client, headers, {"fatigue": None, "throat_discomfort": None,
                                    "speaking_load": None, "singing_load": None,
                                    "hydration_estimate": None, "sleep_hours": 2.0})

    body = get_score(client, headers)
    assert body["status"] != "red"


def test_bad_microphone_recording_does_not_tank_score(client, signed_up_user) -> None:
    """A too-short recording (no AcousticMeasurement) must leave the acoustic components
    exactly as excluded as if no recording existed at all — never scored as bad data."""
    _user, headers_with_bad_mic = signed_up_user
    post_checkin(client, headers_with_bad_mic)

    session_id = client.post(
        "/api/v1/voice-sessions", headers=headers_with_bad_mic, json={}
    ).json()["id"]
    short_wav = make_wav(sine_tone(220.0, 0.1, amplitude=0.5))
    resp = client.post(
        f"/api/v1/voice-sessions/{session_id}/recordings",
        headers=headers_with_bad_mic,
        data={"sample_type": "sustained_ah"},
        files={"file": ("recording.wav", short_wav, "audio/wav")},
    )
    assert resp.status_code == 201
    assert resp.json()["measurement"] is None

    with_bad_mic = get_score(client, headers_with_bad_mic)

    # A second, independent user with the identical check-in but no recording at all.
    import uuid

    email = f"norecording_{uuid.uuid4().hex[:12]}@example.com"
    signup = client.post(
        "/api/v1/auth/signup", json={"email": email, "password": "correcthorse123"}
    )
    headers_no_recording = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    post_checkin(client, headers_no_recording)
    without_recording = get_score(client, headers_no_recording)

    assert with_bad_mic["score_value"] == without_recording["score_value"]
    assert component(with_bad_mic, "consistency_vs_baseline")["included"] is False
    assert component(with_bad_mic, "acoustic_stability")["included"] is False


def test_high_discomfort_triggers_safety_guidance(client, signed_up_user) -> None:
    _user, headers = signed_up_user

    for _ in range(6):
        upload_tone(client, headers, 220.0)
    post_checkin(client, headers, {"throat_discomfort": 9})

    body = get_score(client, headers)
    assert body["status"] == "red"
    assert body["safety_message"] is not None
    assert "professional" in body["safety_message"].lower()


def test_score_explanation_mathematically_matches_score(client, signed_up_user) -> None:
    _user, headers = signed_up_user

    for _ in range(6):
        upload_tone(client, headers, 220.0)
    post_checkin(client, headers, {"sleep_hours": 4.0})

    body = get_score(client, headers)
    recomputed = sum(
        c["weight"] * (c["score"] if c["included"] else NEUTRAL_COMPONENT_SCORE)
        for c in body["components"]
    )
    assert body["score_value"] == round(recomputed)


def test_same_input_always_produces_same_score(client, signed_up_user) -> None:
    _user, headers = signed_up_user

    for _ in range(6):
        upload_tone(client, headers, 220.0)
    post_checkin(client, headers)

    first = get_score(client, headers)
    second = get_score(client, headers)
    assert first == second


def test_no_data_returns_null_score_not_a_fabricated_number(client, signed_up_user) -> None:
    _user, headers = signed_up_user

    body = get_score(client, headers)
    assert body["score_value"] is None
    assert body["confidence_label"] == "insufficient"
    assert body["status"] == "unknown"
