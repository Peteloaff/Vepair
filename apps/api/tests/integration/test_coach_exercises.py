"""Coach-authored custom exercises: title + description, immediately active and eligible for
the general adaptive routine pool (not just that coach's own singers) — gated into the same
intensity-cap safety check as every seed exercise by requiring an existing, whitelisted
category rather than free text."""


def create_exercise(client, headers, **overrides):
    payload = {
        "name": "Custom lip trill variant",
        "instructions": "Trill on a descending scale while gently tapping the sternum.",
        "category": "Lip trill",
        "duration_seconds": 60,
        "difficulty": "moderate",
        **overrides,
    }
    return client.post("/api/v1/coach/exercises", headers=headers, json=payload)


def test_coach_can_create_a_custom_exercise(client, signed_up_coach) -> None:
    _coach, headers = signed_up_coach
    resp = create_exercise(client, headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Custom lip trill variant"
    assert body["category"] == "Lip trill"
    assert body["difficulty"] == "moderate"


def test_purpose_defaults_when_omitted(client, signed_up_coach) -> None:
    _coach, headers = signed_up_coach
    resp = create_exercise(client, headers)
    assert resp.status_code == 201
    assert resp.json()["purpose"]  # non-empty, auto-generated


def test_custom_exercise_is_immediately_selectable_by_singers(
    client, signed_up_coach
) -> None:
    """Confirms it's a normal, immediately-active Exercise row -- it shows up on the general
    library list every user (including non-connected singers) already calls."""
    _coach, coach_headers = signed_up_coach
    created = create_exercise(client, coach_headers).json()

    import uuid

    singer_email = f"singer_{uuid.uuid4().hex[:12]}@example.com"
    signup = client.post(
        "/api/v1/auth/signup", json={"email": singer_email, "password": "correcthorse123"}
    )
    singer_headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}

    resp = client.get("/api/v1/exercises", headers=singer_headers)
    assert resp.status_code == 200
    ids = {e["id"] for e in resp.json()}
    assert created["id"] in ids


def test_non_coach_cannot_create_exercises(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = create_exercise(client, headers)
    assert resp.status_code == 403


def test_rejects_invalid_category(client, signed_up_coach) -> None:
    _coach, headers = signed_up_coach
    resp = create_exercise(client, headers, category="Not a real category")
    assert resp.status_code == 422


def test_rejects_invalid_difficulty(client, signed_up_coach) -> None:
    _coach, headers = signed_up_coach
    resp = create_exercise(client, headers, difficulty="extreme")
    assert resp.status_code == 422


def test_rejects_empty_title_or_description(client, signed_up_coach) -> None:
    _coach, headers = signed_up_coach
    assert create_exercise(client, headers, name="").status_code == 422
    assert create_exercise(client, headers, instructions="").status_code == 422


def test_coach_can_list_their_own_created_exercises(client, signed_up_coach) -> None:
    _coach, headers = signed_up_coach
    create_exercise(client, headers, name="First")
    create_exercise(client, headers, name="Second")

    resp = client.get("/api/v1/coach/exercises", headers=headers)
    assert resp.status_code == 200
    names = {e["name"] for e in resp.json()}
    assert names == {"First", "Second"}


def test_coach_exercise_list_excludes_seed_exercises(client, signed_up_coach) -> None:
    _coach, headers = signed_up_coach
    resp = client.get("/api/v1/coach/exercises", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_coach_a_does_not_see_coach_bs_created_exercises(
    client, signed_up_coach
) -> None:
    _coach_a, headers_a = signed_up_coach

    import uuid

    email_b = f"coach_{uuid.uuid4().hex[:12]}@example.com"
    signup_b = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": email_b,
            "password": "correcthorse123",
            "display_name": "Coach B",
            "studio_name": None,
        },
    )
    headers_b = {"Authorization": f"Bearer {signup_b.json()['access_token']}"}

    create_exercise(client, headers_a, name="Coach A's exercise")
    create_exercise(client, headers_b, name="Coach B's exercise")

    resp = client.get("/api/v1/coach/exercises", headers=headers_a)
    names = {e["name"] for e in resp.json()}
    assert names == {"Coach A's exercise"}
