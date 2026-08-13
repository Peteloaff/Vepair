"""Stage 12 Phase II recording comparison — category-gated, driven through the real API
endpoints. Reuses the WAV-generation helpers already established in test_recordings.py."""

from tests.integration.test_recordings import clean_wav_bytes, upload_file


def _connect(client, coach_headers, singer_email, singer_headers, categories) -> str:
    created = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer_email}
    )
    invite_id = created.json()["id"]
    accepted = client.post(
        f"/api/v1/invites/{invite_id}/accept",
        headers=singer_headers,
        json={"granted_categories": categories},
    )
    assert accepted.status_code == 200, accepted.text
    return accepted.json()["id"]


def _upload_a_recording(client, singer_headers) -> str:
    session = client.post("/api/v1/voice-sessions", headers=singer_headers, json={})
    session_id = session.json()["id"]
    upload = upload_file(client, singer_headers, session_id, wav_bytes=clean_wav_bytes())
    assert upload.status_code == 201, upload.text
    return upload.json()["id"]


def test_coach_with_recordings_category_can_list_and_play_singers_recording(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    recording_id = _upload_a_recording(client, singer_headers)
    _connect(client, coach_headers, singer["email"], singer_headers, ["recordings"])

    listing = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/recordings", headers=coach_headers
    )
    assert listing.status_code == 200, listing.text
    sessions = listing.json()
    assert len(sessions) == 1
    assert sessions[0]["recordings"][0]["id"] == recording_id

    audio = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/recordings/{recording_id}/audio",
        headers=coach_headers,
    )
    assert audio.status_code == 200
    assert audio.headers["content-type"] == "audio/wav"
    assert audio.content == clean_wav_bytes()


def test_coach_without_recordings_category_gets_403(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _upload_a_recording(client, singer_headers)
    _connect(client, coach_headers, singer["email"], singer_headers, ["recovery_trends"])

    listing = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/recordings", headers=coach_headers
    )
    assert listing.status_code == 403
    assert listing.json()["error"]["code"] == "category_not_shared"


def test_coach_cannot_play_a_recording_belonging_to_a_different_singer(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer_a, singer_a_headers = signed_up_user
    recording_id = _upload_a_recording(client, singer_a_headers)
    _connect(client, coach_headers, singer_a["email"], singer_a_headers, ["recordings"])

    signup_b = client.post(
        "/api/v1/auth/signup",
        json={"email": "singer-b-recordings-test@example.com", "password": "correcthorse123"},
    )
    singer_b_headers = {"Authorization": f"Bearer {signup_b.json()['access_token']}"}
    singer_b_id = signup_b.json()["user"]["id"]
    _connect(
        client,
        coach_headers,
        "singer-b-recordings-test@example.com",
        singer_b_headers,
        ["recordings"],
    )

    # The coach is authorized for singer B, but this recording belongs to singer A.
    resp = client.get(
        f"/api/v1/coach/singers/{singer_b_id}/recordings/{recording_id}/audio",
        headers=coach_headers,
    )
    assert resp.status_code == 404


def test_voice_session_notes_field_never_appears_in_coach_recordings_response(
    client, signed_up_coach, signed_up_user
) -> None:
    """VoiceSession.notes is user free-text, same category of field as DailyCheckIn's — a
    hardcoded omission from the coach-facing schema, not a togglable category."""
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _upload_a_recording(client, singer_headers)
    _connect(client, coach_headers, singer["email"], singer_headers, ["recordings"])

    resp = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/recordings", headers=coach_headers
    )
    assert resp.status_code == 200
    assert "notes" not in resp.json()[0]
