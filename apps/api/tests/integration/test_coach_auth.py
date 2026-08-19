"""Stage 12 Phase II coach identity and the get_current_coach boundary — proven in isolation
before anything else in the coach pilot builds on it. require_coach_access's behavior (which
needs a real CoachAccess row to exercise meaningfully) is tested in test_coach_access.py,
alongside the endpoints that actually depend on it.

Post-Stage-12 Part 2 (SaaS billing): get_current_coach also gates on the coach's Organization
having an active coach_pro subscription -- no free coach tier, so a fresh signup's org starts
inactive (see app.models.Organization's docstring). Tests below that need a *working* coach
account use the signed_up_coach fixture, which activates coach_pro automatically (see
tests/conftest.py) -- tests here that sign up directly are specifically about proving that
boundary itself."""


def test_coach_signup_creates_an_account_blocked_until_coach_pro_is_active(client) -> None:
    resp = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": "coach-signup-test@example.com",
            "password": "correcthorse123",
            "display_name": "Jane Coach",
            "studio_name": "Jane's Studio",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["email"] == "coach-signup-test@example.com"
    assert "access_token" in body

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    profile = client.get("/api/v1/coach/profile", headers=headers)
    assert profile.status_code == 403
    assert profile.json()["error"]["code"] == "coach_pro_required"


def test_coach_profile_works_once_coach_pro_is_active(client, signed_up_coach) -> None:
    """signed_up_coach activates coach_pro as part of the fixture -- see tests/conftest.py."""
    coach, headers = signed_up_coach
    profile = client.get("/api/v1/coach/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["display_name"] == "Test Coach"
    assert profile.json()["studio_name"] == "Test Studio"


def test_coach_signup_studio_name_is_optional(client) -> None:
    resp = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": "coach-no-studio@example.com",
            "password": "correcthorse123",
            "display_name": "Solo Coach",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["user"]["email"] == "coach-no-studio@example.com"


def test_coach_signup_rejects_duplicate_email(client, signed_up_user) -> None:
    user, _headers = signed_up_user
    resp = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": user["email"],
            "password": "correcthorse123",
            "display_name": "Duplicate Coach",
        },
    )
    assert resp.status_code == 409


def test_regular_signed_up_user_is_not_a_coach(client, signed_up_user) -> None:
    """A singer account signed up through the regular /auth/signup must never pass as a coach
    — coach-ness only ever comes from coach-signup, never inferred."""
    _user, headers = signed_up_user
    resp = client.get("/api/v1/coach/profile", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "not_a_coach"


def test_coach_profile_requires_authentication(client) -> None:
    resp = client.get("/api/v1/coach/profile")
    assert resp.status_code == 401


def test_coach_can_log_in_through_the_regular_login_endpoint(client, signed_up_coach) -> None:
    """Coach accounts use the exact same auth system as singers — same JWT, same /auth/login —
    only the signup path differs."""
    coach, _headers = signed_up_coach
    resp = client.post(
        "/api/v1/auth/login", json={"email": coach["email"], "password": coach["password"]}
    )
    assert resp.status_code == 200
