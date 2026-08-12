"""Consent grants (PRIVACY.md section 3) — driven through the real API endpoints."""


def test_unset_consent_returns_null_not_false(client, signed_up_user) -> None:
    """A user who has never been asked must be distinguishable from one who said no."""
    _user, headers = signed_up_user
    resp = client.get("/api/v1/consent/notifications", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["consent_type"] == "notifications"
    assert body["granted"] is None
    assert body["granted_at"] is None


def test_set_consent_true_then_read_it_back(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    put_resp = client.put(
        "/api/v1/consent/notifications", headers=headers, json={"granted": True}
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["granted"] is True
    assert put_resp.json()["granted_at"] is not None

    get_resp = client.get("/api/v1/consent/notifications", headers=headers)
    assert get_resp.json()["granted"] is True


def test_changing_the_answer_returns_the_latest_choice(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    client.put("/api/v1/consent/notifications", headers=headers, json={"granted": True})
    client.put("/api/v1/consent/notifications", headers=headers, json={"granted": False})

    resp = client.get("/api/v1/consent/notifications", headers=headers)
    assert resp.json()["granted"] is False


def test_rejects_an_unknown_consent_type(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.get("/api/v1/consent/bogus", headers=headers)
    assert resp.status_code == 422

    put_resp = client.put(
        "/api/v1/consent/bogus", headers=headers, json={"granted": True}
    )
    assert put_resp.status_code == 422


def test_consent_types_are_independent(client, signed_up_user) -> None:
    """Saying yes to notifications must never imply yes to anything else."""
    _user, headers = signed_up_user
    client.put("/api/v1/consent/notifications", headers=headers, json={"granted": True})

    other = client.get("/api/v1/consent/product_analytics", headers=headers)
    assert other.json()["granted"] is None


def test_consent_requires_authentication(client) -> None:
    resp = client.get("/api/v1/consent/notifications")
    assert resp.status_code == 401

    put_resp = client.put("/api/v1/consent/notifications", json={"granted": True})
    assert put_resp.status_code == 401


def test_consent_is_scoped_to_the_requesting_user(client, signed_up_user) -> None:
    """One user's consent choice must never leak into another user's read."""
    _user, headers = signed_up_user
    client.put("/api/v1/consent/notifications", headers=headers, json={"granted": True})

    signup2 = client.post(
        "/api/v1/auth/signup",
        json={"email": "consent-other-user@example.com", "password": "TestPass123!"},
    )
    other_headers = {"Authorization": f"Bearer {signup2.json()['access_token']}"}

    resp = client.get("/api/v1/consent/notifications", headers=other_headers)
    assert resp.json()["granted"] is None
