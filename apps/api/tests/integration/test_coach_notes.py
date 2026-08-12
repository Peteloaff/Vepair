"""Stage 12 Phase II professional notes — driven through the real API endpoints."""


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


def test_note_with_blocklisted_term_returns_warning_but_still_saves(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["recovery_trends"])

    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes",
        headers=coach_headers,
        json={"body": "I'm concerned this might be vocal nodules — recommend seeing an ENT."},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["flagged_terms"] == ["nodule"]

    listed = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes", headers=coach_headers
    )
    assert len(listed.json()) == 1


def test_note_without_trigger_words_has_no_warning(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["recovery_trends"])

    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes",
        headers=coach_headers,
        json={"body": "Great breath support today, keep working on the glide exercises."},
    )
    assert resp.status_code == 201
    assert resp.json()["flagged_terms"] is None


def test_note_over_max_length_is_rejected_422(client, signed_up_coach, signed_up_user) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["recovery_trends"])

    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes",
        headers=coach_headers,
        json={"body": "x" * 2001},
    )
    assert resp.status_code == 422


def test_singer_can_read_notes_written_about_them(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )

    client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes",
        headers=coach_headers,
        json={"body": "Nice progress this week."},
    )

    resp = client.get(f"/api/v1/coach-connections/{access_id}/notes", headers=singer_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["body"] == "Nice progress this week."


def test_singer_can_still_read_notes_after_revoking_access(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )
    client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes",
        headers=coach_headers,
        json={"body": "A note before revoking."},
    )

    client.delete(f"/api/v1/coach-connections/{access_id}", headers=singer_headers)

    resp = client.get(f"/api/v1/coach-connections/{access_id}/notes", headers=singer_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_another_singer_cannot_read_someone_elses_notes(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer_a, singer_a_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer_a["email"], singer_a_headers, ["recovery_trends"]
    )

    signup_b = client.post(
        "/api/v1/auth/signup",
        json={"email": "singer-b-notes-test@example.com", "password": "correcthorse123"},
    )
    headers_b = {"Authorization": f"Bearer {signup_b.json()['access_token']}"}

    resp = client.get(f"/api/v1/coach-connections/{access_id}/notes", headers=headers_b)
    assert resp.status_code == 404


def test_coach_can_soft_delete_own_note(client, signed_up_coach, signed_up_user) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )

    created = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes",
        headers=coach_headers,
        json={"body": "A note to delete."},
    )
    note_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/coach/notes/{note_id}", headers=coach_headers)
    assert deleted.status_code == 204

    # Gone from both the coach's own list and the singer's read.
    coach_list = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes", headers=coach_headers
    )
    assert coach_list.json() == []
    singer_list = client.get(
        f"/api/v1/coach-connections/{access_id}/notes", headers=singer_headers
    )
    assert singer_list.json() == []


def test_notes_require_active_access_not_just_a_coach_account(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, _singer_headers = signed_up_user

    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes",
        headers=coach_headers,
        json={"body": "Should not be allowed."},
    )
    assert resp.status_code == 403
