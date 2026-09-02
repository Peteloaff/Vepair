"""Self-serve data export -- GET /api/v1/profile/export."""


def test_export_requires_authentication(client) -> None:
    assert client.get("/api/v1/profile/export").status_code == 401


def test_export_includes_account_and_checkins(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    client.post(
        "/api/v1/checkins",
        headers=headers,
        json={"checkin_date": "2026-01-01", "voice_quality": 8},
    )

    resp = client.get("/api/v1/profile/export", headers=headers)
    assert resp.status_code == 200
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.headers["content-disposition"].endswith('.json"')

    body = resp.json()
    assert body["account"]["email"] == _user["email"]
    assert len(body["checkins"]) == 1
    assert body["checkins"][0]["voice_quality"] == 8


def test_export_never_includes_password_hash(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.get("/api/v1/profile/export", headers=headers)
    body_text = resp.text
    assert "password_hash" not in body_text


def test_export_includes_recordings_without_raw_audio(client, signed_up_user) -> None:
    from tests.integration.test_recordings import clean_wav_bytes

    _user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    client.post(
        f"/api/v1/voice-sessions/{session_id}/recordings",
        headers=headers,
        data={"sample_type": "sustained_ah"},
        files={"file": ("recording.wav", clean_wav_bytes(), "audio/wav")},
    )

    resp = client.get("/api/v1/profile/export", headers=headers)
    body = resp.json()
    session = next(s for s in body["voice_sessions"] if s["id"] == session_id)
    assert len(session["recordings"]) == 1
    recording = session["recordings"][0]
    assert "file_path" not in recording
    assert recording["audio_download_url"] == f"/api/v1/recordings/{recording['id']}/audio"
    assert recording["measurement"] is not None


def test_coach_export_includes_authored_notes_and_messages(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user

    invite_id = client.post(
        "/api/v1/coach/invites",
        headers=coach_headers,
        json={"singer_email": singer["email"]},
    ).json()["id"]
    client.post(
        f"/api/v1/invites/{invite_id}/accept",
        headers=singer_headers,
        json={"granted_categories": ["recovery_trends"]},
    )
    client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes",
        headers=coach_headers,
        json={"body": "Great session today."},
    )
    client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages",
        headers=coach_headers,
        json={"body": "Hello!"},
    )

    resp = client.get("/api/v1/profile/export", headers=coach_headers)
    body = resp.json()
    assert len(body["coach_activity"]["notes_authored"]) == 1
    assert len(body["coach_activity"]["messages_sent"]) == 1


def test_singer_export_includes_coach_connection_notes_and_messages(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user

    invite_id = client.post(
        "/api/v1/coach/invites",
        headers=coach_headers,
        json={"singer_email": singer["email"]},
    ).json()["id"]
    client.post(
        f"/api/v1/invites/{invite_id}/accept",
        headers=singer_headers,
        json={"granted_categories": ["recovery_trends"]},
    )
    client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes",
        headers=coach_headers,
        json={"body": "A note about the singer."},
    )

    resp = client.get("/api/v1/profile/export", headers=singer_headers)
    body = resp.json()
    assert len(body["coach_connections"]) == 1
    assert len(body["coach_connections"][0]["notes_from_coach"]) == 1
