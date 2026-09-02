"""Two-way coach<->Vrotégé messaging — driven through the real API endpoints, mirroring
test_coach_notes.py's structure for the parts that overlap (blocklist flagging, access checks)."""


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


def test_coach_can_send_and_singer_can_read(client, signed_up_coach, signed_up_user) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )

    sent = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages",
        headers=coach_headers,
        json={"body": "How did today's warmup feel?"},
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["sender"] == "coach"
    assert sent.json()["flagged_terms"] is None
    assert sent.json()["read_at"] is None

    thread = client.get(f"/api/v1/coach-connections/{access_id}/messages", headers=singer_headers)
    assert thread.status_code == 200
    assert len(thread.json()) == 1
    assert thread.json()[0]["body"] == "How did today's warmup feel?"


def test_singer_can_send_and_coach_can_read(client, signed_up_coach, signed_up_user) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )

    sent = client.post(
        f"/api/v1/coach-connections/{access_id}/messages",
        headers=singer_headers,
        json={"body": "It felt great, thanks!"},
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["sender"] == "singer"

    thread = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages", headers=coach_headers
    )
    assert thread.status_code == 200
    assert len(thread.json()) == 1
    assert thread.json()[0]["body"] == "It felt great, thanks!"


def test_message_with_blocklisted_term_flags_but_still_saves(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["recovery_trends"])

    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages",
        headers=coach_headers,
        json={"body": "This could be a vocal nodule — please see an ENT."},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["flagged_terms"] == ["nodule"]


def test_message_over_max_length_is_rejected_422(client, signed_up_coach, signed_up_user) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["recovery_trends"])

    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages",
        headers=coach_headers,
        json={"body": "x" * 2001},
    )
    assert resp.status_code == 422


def test_messaging_not_gated_by_any_sharing_category(
    client, signed_up_coach, signed_up_user
) -> None:
    """Unlike get_singer_summary's fields, messaging works even with zero categories shared --
    same as notes: it's a channel the singer controls directly, not a passive data category."""
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["recovery_trends"])

    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages",
        headers=coach_headers,
        json={"body": "No categories shared, should still work."},
    )
    assert resp.status_code == 201, resp.text


def test_messages_require_active_access_not_just_a_coach_account(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, _singer_headers = signed_up_user

    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages",
        headers=coach_headers,
        json={"body": "Should not be allowed."},
    )
    assert resp.status_code == 403


def test_singer_send_rejected_after_revoke_but_read_history_still_works(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )

    client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages",
        headers=coach_headers,
        json={"body": "A message before revoking."},
    )
    client.delete(f"/api/v1/coach-connections/{access_id}", headers=singer_headers)

    # Reading the existing thread still works -- it's the singer's own record now.
    thread = client.get(f"/api/v1/coach-connections/{access_id}/messages", headers=singer_headers)
    assert thread.status_code == 200
    assert len(thread.json()) == 1

    # But sending a new one is rejected -- the connection is no longer active.
    resp = client.post(
        f"/api/v1/coach-connections/{access_id}/messages",
        headers=singer_headers,
        json={"body": "Should not be allowed after revoke."},
    )
    assert resp.status_code == 409


def test_coach_send_rejected_after_revoke(client, signed_up_coach, signed_up_user) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )
    client.delete(f"/api/v1/coach-connections/{access_id}", headers=singer_headers)

    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages",
        headers=coach_headers,
        json={"body": "Should not be allowed after revoke."},
    )
    assert resp.status_code == 403


def test_another_singer_cannot_read_or_send_on_someone_elses_connection(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer_a, singer_a_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer_a["email"], singer_a_headers, ["recovery_trends"]
    )

    signup_b = client.post(
        "/api/v1/auth/signup",
        json={"email": "singer-b-messages-test@example.com", "password": "correcthorse123"},
    )
    headers_b = {"Authorization": f"Bearer {signup_b.json()['access_token']}"}

    read_resp = client.get(f"/api/v1/coach-connections/{access_id}/messages", headers=headers_b)
    assert read_resp.status_code == 404

    send_resp = client.post(
        f"/api/v1/coach-connections/{access_id}/messages",
        headers=headers_b,
        json={"body": "Should not be allowed."},
    )
    assert send_resp.status_code == 404


def test_unread_count_increments_and_clears_on_read_for_coach_roster(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )

    client.post(
        f"/api/v1/coach-connections/{access_id}/messages",
        headers=singer_headers,
        json={"body": "First message from singer."},
    )
    client.post(
        f"/api/v1/coach-connections/{access_id}/messages",
        headers=singer_headers,
        json={"body": "Second message from singer."},
    )

    roster = client.get("/api/v1/coach/singers", headers=coach_headers)
    row = next(r for r in roster.json() if r["coach_access_id"] == access_id)
    assert row["unread_message_count"] == 2

    # Reading the thread as the coach clears it.
    client.get(f"/api/v1/coach/singers/{singer['user']['id']}/messages", headers=coach_headers)

    roster_after = client.get("/api/v1/coach/singers", headers=coach_headers)
    row_after = next(r for r in roster_after.json() if r["coach_access_id"] == access_id)
    assert row_after["unread_message_count"] == 0


def test_unread_count_increments_and_clears_on_read_for_singer_connections(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )

    client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages",
        headers=coach_headers,
        json={"body": "Hello from your coach."},
    )

    connections = client.get("/api/v1/coach-connections", headers=singer_headers)
    row = next(c for c in connections.json() if c["id"] == access_id)
    assert row["unread_message_count"] == 1

    client.get(f"/api/v1/coach-connections/{access_id}/messages", headers=singer_headers)

    connections_after = client.get("/api/v1/coach-connections", headers=singer_headers)
    row_after = next(c for c in connections_after.json() if c["id"] == access_id)
    assert row_after["unread_message_count"] == 0


def test_sending_does_not_mark_own_message_read_by_recipient(
    client, signed_up_coach, signed_up_user
) -> None:
    """Sending a message never touches read_at -- only the *recipient* viewing the thread does.
    A coach sending twice in a row shouldn't accidentally self-clear their own unread badge."""
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )

    client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages",
        headers=coach_headers,
        json={"body": "First."},
    )
    second = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/messages",
        headers=coach_headers,
        json={"body": "Second."},
    )
    assert second.json()["read_at"] is None

    connections = client.get("/api/v1/coach-connections", headers=singer_headers)
    row = next(c for c in connections.json() if c["id"] == access_id)
    assert row["unread_message_count"] == 2
