"""Stage 12 Phase II invite lifecycle — coach invites a singer, singer accepts/declines. Driven
through the real API endpoints, per this codebase's established testing convention."""


def test_coach_can_invite_an_existing_singer_by_email(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, _singer_headers = signed_up_user

    resp = client.post(
        "/api/v1/coach/invites",
        headers=coach_headers,
        json={"singer_email": singer["email"], "message": "Let's work together!"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["singer_email"] == singer["email"]
    assert body["status"] == "pending"
    assert body["message"] == "Let's work together!"


def test_inviting_a_nonexistent_email_returns_404(client, signed_up_coach) -> None:
    _coach, coach_headers = signed_up_coach
    resp = client.post(
        "/api/v1/coach/invites",
        headers=coach_headers,
        json={"singer_email": "nobody-has-this-account@example.com"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "singer_not_found"


def test_duplicate_pending_invite_is_not_created_twice(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, _singer_headers = signed_up_user

    client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer["email"]}
    )
    second = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer["email"]}
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "invite_already_pending"


def test_non_coach_user_gets_403_calling_coach_invite_endpoints(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.post(
        "/api/v1/coach/invites", headers=headers, json={"singer_email": "someone@example.com"}
    )
    assert resp.status_code == 403


def test_singer_sees_pending_invite_with_coach_display_name_and_message(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user

    client.post(
        "/api/v1/coach/invites",
        headers=coach_headers,
        json={"singer_email": singer["email"], "message": "Hi there"},
    )

    resp = client.get("/api/v1/invites", headers=singer_headers)
    assert resp.status_code == 200
    invites = resp.json()
    assert len(invites) == 1
    assert invites[0]["coach_display_name"] == "Test Coach"
    assert invites[0]["coach_studio_name"] == "Test Studio"
    assert invites[0]["message"] == "Hi there"


def test_coach_can_cancel_a_pending_invite(client, signed_up_coach, signed_up_user) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user

    created = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer["email"]}
    )
    invite_id = created.json()["id"]

    cancelled = client.delete(f"/api/v1/coach/invites/{invite_id}", headers=coach_headers)
    assert cancelled.status_code == 204

    # A cancelled invite is no longer pending, so the singer no longer sees it.
    resp = client.get("/api/v1/invites", headers=singer_headers)
    assert resp.json() == []


def test_declining_an_invite_creates_no_coach_access_row(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user

    created = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer["email"]}
    )
    invite_id = created.json()["id"]

    declined = client.post(f"/api/v1/invites/{invite_id}/decline", headers=singer_headers)
    assert declined.status_code == 204

    connections = client.get("/api/v1/coach-connections", headers=singer_headers)
    assert connections.json() == []


def test_accepting_requires_at_least_one_category(client, signed_up_coach, signed_up_user) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user

    created = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer["email"]}
    )
    invite_id = created.json()["id"]

    resp = client.post(
        f"/api/v1/invites/{invite_id}/accept",
        headers=singer_headers,
        json={"granted_categories": []},
    )
    assert resp.status_code == 422


def test_accepting_creates_coach_access_category_grants_and_consent_records(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user

    created = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer["email"]}
    )
    invite_id = created.json()["id"]

    resp = client.post(
        f"/api/v1/invites/{invite_id}/accept",
        headers=singer_headers,
        json={"granted_categories": ["recovery_trends", "vocal_range"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert sorted(body["granted_categories"]) == ["recovery_trends", "vocal_range"]
    assert body["coach_display_name"] == "Test Coach"

    connections = client.get("/api/v1/coach-connections", headers=singer_headers)
    assert len(connections.json()) == 1
    assert connections.json()[0]["status"] == "active"

    consent = client.get("/api/v1/consent/coach_sharing", headers=singer_headers)
    # coach_sharing is category-specific, not a single flag — the generic consent endpoint
    # reads the most recent row for the type regardless of category, so this just confirms
    # a coach_sharing row now exists at all (granted=True from whichever category was last
    # inserted). Per-category state is authoritative via CoachAccessCategoryGrant instead.
    assert consent.status_code == 200
    assert consent.json()["granted"] is True


def test_singer_cannot_accept_an_invite_addressed_to_someone_else(
    client, signed_up_coach, signed_up_user
) -> None:
    """Cross-user boundary: an invite is only ever acceptable by the singer it was sent to."""
    _coach, coach_headers = signed_up_coach
    singer_a, _headers_a = signed_up_user

    created = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer_a["email"]}
    )
    invite_id = created.json()["id"]

    signup_b = client.post(
        "/api/v1/auth/signup",
        json={"email": "singer-b-boundary-test@example.com", "password": "correcthorse123"},
    )
    headers_b = {"Authorization": f"Bearer {signup_b.json()['access_token']}"}

    resp = client.post(
        f"/api/v1/invites/{invite_id}/accept",
        headers=headers_b,
        json={"granted_categories": ["recovery_trends"]},
    )
    assert resp.status_code == 404


def test_cannot_accept_a_second_invite_while_one_coach_is_already_active(
    client, signed_up_user
) -> None:
    """One active coach at a time (founder decision) — enforced at the API layer, backed by a
    DB-level partial unique index."""
    singer, singer_headers = signed_up_user

    signup_coach_a = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": "coach-a-onecoach-test@example.com",
            "password": "correcthorse123",
            "display_name": "Coach A",
        },
    )
    coach_a_headers = {"Authorization": f"Bearer {signup_coach_a.json()['access_token']}"}

    signup_coach_b = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": "coach-b-onecoach-test@example.com",
            "password": "correcthorse123",
            "display_name": "Coach B",
        },
    )
    coach_b_headers = {"Authorization": f"Bearer {signup_coach_b.json()['access_token']}"}

    invite_a = client.post(
        "/api/v1/coach/invites", headers=coach_a_headers, json={"singer_email": singer["email"]}
    )
    client.post(
        f"/api/v1/invites/{invite_a.json()['id']}/accept",
        headers=singer_headers,
        json={"granted_categories": ["recovery_trends"]},
    )

    invite_b = client.post(
        "/api/v1/coach/invites", headers=coach_b_headers, json={"singer_email": singer["email"]}
    )
    resp = client.post(
        f"/api/v1/invites/{invite_b.json()['id']}/accept",
        headers=singer_headers,
        json={"granted_categories": ["recovery_trends"]},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "already_has_active_coach"


def test_singer_list_includes_identifying_info_not_bare_ids(
    client, signed_up_coach, signed_up_user
) -> None:
    """The roster a coach actually sees must be usable — email and granted categories, not
    just an opaque UUID a coach has no way to act on."""
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    created = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer["email"]}
    )
    client.post(
        f"/api/v1/invites/{created.json()['id']}/accept",
        headers=singer_headers,
        json={"granted_categories": ["recovery_trends", "vocal_range"]},
    )

    resp = client.get("/api/v1/coach/singers", headers=coach_headers)
    assert resp.status_code == 200
    singers = resp.json()
    assert len(singers) == 1
    assert singers[0]["singer_user_id"] == singer["user"]["id"]
    assert singers[0]["singer_email"] == singer["email"]
    assert sorted(singers[0]["granted_categories"]) == ["recovery_trends", "vocal_range"]


def test_coach_can_remove_a_singer_from_their_roster(
    client, signed_up_coach, signed_up_user
) -> None:
    """Coach-initiated disconnect — the mirror of the singer's own DELETE
    /api/v1/coach-connections/{id}, just from the other side."""
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    created = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer["email"]}
    )
    client.post(
        f"/api/v1/invites/{created.json()['id']}/accept",
        headers=singer_headers,
        json={"granted_categories": ["recovery_trends"]},
    )

    resp = client.delete(
        f"/api/v1/coach/singers/{singer['user']['id']}", headers=coach_headers
    )
    assert resp.status_code == 204

    # Immediate for the coach's own future access.
    roster = client.get("/api/v1/coach/singers", headers=coach_headers)
    assert roster.json() == []

    # The singer's own account and data are completely untouched.
    me = client.get("/api/v1/auth/me", headers=singer_headers)
    assert me.status_code == 200
    assert me.json()["email"] == singer["email"]


def test_removed_singer_can_still_see_the_coachs_notes_about_them(
    client, signed_up_coach, signed_up_user
) -> None:
    """Forward-only revoke, same as the singer-initiated path: a coach can't retroactively
    take back a note the singer already has permanent read access to."""
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    created = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer["email"]}
    )
    accepted = client.post(
        f"/api/v1/invites/{created.json()['id']}/accept",
        headers=singer_headers,
        json={"granted_categories": ["recovery_trends"]},
    )
    connection_id = accepted.json()["id"]

    client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes",
        headers=coach_headers,
        json={"body": "Great breath support in today's session."},
    )

    client.delete(f"/api/v1/coach/singers/{singer['user']['id']}", headers=coach_headers)

    notes = client.get(
        f"/api/v1/coach-connections/{connection_id}/notes", headers=singer_headers
    )
    assert notes.status_code == 200
    assert len(notes.json()) == 1
    assert notes.json()[0]["body"] == "Great breath support in today's session."


def test_coach_cannot_remove_a_singer_with_no_active_access(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, _singer_headers = signed_up_user

    resp = client.delete(
        f"/api/v1/coach/singers/{singer['user']['id']}", headers=coach_headers
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "no_active_access"


def test_removing_a_singer_blocks_the_coachs_own_further_reads(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    created = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer["email"]}
    )
    client.post(
        f"/api/v1/invites/{created.json()['id']}/accept",
        headers=singer_headers,
        json={"granted_categories": ["recovery_trends"]},
    )

    client.delete(f"/api/v1/coach/singers/{singer['user']['id']}", headers=coach_headers)

    resp = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": "2026-08-13"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "no_active_access"
