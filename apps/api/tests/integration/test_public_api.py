"""The read-only public API (`/api/public/v1/*`) and the personal access tokens that gate it.
Covers token CRUD, the public_api_enabled kill switch, scope enforcement, and rate limiting."""

from datetime import date

from app.models import User


def _make_admin(db_session, user_email) -> None:
    user = db_session.query(User).filter_by(email=user_email).one()
    user.is_admin = True
    db_session.commit()


def _enable_public_api(client, admin_headers, *, enabled: bool = True) -> None:
    resp = client.post(
        "/api/v1/admin/site-settings",
        headers=admin_headers,
        json={
            "signups_enabled": True,
            "nda_required": True,
            "recording_retention_days": 90,
            "checkin_notes_retention_days": 30,
            "login_event_retention_days": 365,
            "public_api_enabled": enabled,
        },
    )
    assert resp.status_code == 200, resp.text


def _admin_headers(client, signed_up_user, db_session):
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    return admin_headers


def test_create_token_returns_raw_value_once(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    created = client.post(
        "/api/v1/api-tokens",
        headers=headers,
        json={"name": "My integration", "scopes": ["recovery_trends"]},
    )
    assert created.status_code == 201, created.text
    assert "token" in created.json()
    assert len(created.json()["token"]) > 20

    listed = client.get("/api/v1/api-tokens", headers=headers)
    assert listed.status_code == 200
    assert "token" not in listed.json()[0]
    assert listed.json()[0]["name"] == "My integration"


def test_create_token_rejects_unknown_scope(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.post(
        "/api/v1/api-tokens",
        headers=headers,
        json={"name": "Bad scope", "scopes": ["recordings"]},
    )
    assert resp.status_code == 422


def test_revoked_token_no_longer_lists_as_active_and_stops_working(
    client, signed_up_user, db_session
) -> None:
    _user, headers = signed_up_user
    admin_headers = _admin_headers(client, signed_up_user, db_session)
    _enable_public_api(client, admin_headers)

    created = client.post(
        "/api/v1/api-tokens",
        headers=headers,
        json={"name": "Temp", "scopes": ["recovery_trends"]},
    )
    token_id = created.json()["id"]
    raw_token = created.json()["token"]

    revoked = client.delete(f"/api/v1/api-tokens/{token_id}", headers=headers)
    assert revoked.status_code == 204

    listed = client.get("/api/v1/api-tokens", headers=headers)
    assert listed.json()[0]["revoked_at"] is not None

    blocked = client.get(
        "/api/public/v1/recovery-score",
        headers={"Authorization": f"Bearer {raw_token}"},
        params={"date": date.today().isoformat()},
    )
    assert blocked.status_code == 401


def test_public_api_disabled_by_default(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    created = client.post(
        "/api/v1/api-tokens",
        headers=headers,
        json={"name": "Disabled by default", "scopes": ["recovery_trends"]},
    )
    raw_token = created.json()["token"]

    resp = client.get(
        "/api/public/v1/recovery-score",
        headers={"Authorization": f"Bearer {raw_token}"},
        params={"date": date.today().isoformat()},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "public_api_disabled"


def test_valid_token_with_right_scope_reaches_the_endpoint(
    client, signed_up_user, db_session
) -> None:
    _user, headers = signed_up_user
    admin_headers = _admin_headers(client, signed_up_user, db_session)
    _enable_public_api(client, admin_headers)

    created = client.post(
        "/api/v1/api-tokens",
        headers=headers,
        json={"name": "Works", "scopes": ["recovery_trends"]},
    )
    raw_token = created.json()["token"]

    resp = client.get(
        "/api/public/v1/recovery-score",
        headers={"Authorization": f"Bearer {raw_token}"},
        params={"date": date.today().isoformat()},
    )
    assert resp.status_code == 200
    assert "score_date" in resp.json()


def test_token_without_the_right_scope_is_rejected(client, signed_up_user, db_session) -> None:
    _user, headers = signed_up_user
    admin_headers = _admin_headers(client, signed_up_user, db_session)
    _enable_public_api(client, admin_headers)

    created = client.post(
        "/api/v1/api-tokens",
        headers=headers,
        json={"name": "Wrong scope", "scopes": ["vocal_range"]},
    )
    raw_token = created.json()["token"]

    resp = client.get(
        "/api/public/v1/recovery-score",
        headers={"Authorization": f"Bearer {raw_token}"},
        params={"date": date.today().isoformat()},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "scope_not_granted"


def test_garbage_bearer_token_is_rejected(client, signed_up_user, db_session) -> None:
    admin_headers = _admin_headers(client, signed_up_user, db_session)
    _enable_public_api(client, admin_headers)

    resp = client.get(
        "/api/public/v1/recovery-score",
        headers={"Authorization": "Bearer not-a-real-token"},
        params={"date": date.today().isoformat()},
    )
    assert resp.status_code == 401


def test_vocal_range_and_exercise_trends_endpoints_respect_their_own_scopes(
    client, signed_up_user, db_session
) -> None:
    _user, headers = signed_up_user
    admin_headers = _admin_headers(client, signed_up_user, db_session)
    _enable_public_api(client, admin_headers)

    created = client.post(
        "/api/v1/api-tokens",
        headers=headers,
        json={"name": "Full access", "scopes": ["vocal_range", "exercise_history"]},
    )
    raw_token = created.json()["token"]
    auth = {"Authorization": f"Bearer {raw_token}"}

    vocal_range = client.get("/api/public/v1/vocal-range", headers=auth)
    assert vocal_range.status_code == 200

    trends = client.get("/api/public/v1/exercise-trends", headers=auth)
    assert trends.status_code == 200
    assert isinstance(trends.json(), list)

    recovery = client.get(
        "/api/public/v1/recovery-score",
        headers=auth,
        params={"date": date.today().isoformat()},
    )
    assert recovery.status_code == 403


def test_rate_limit_blocks_after_the_per_minute_cap(
    client, signed_up_user, db_session, monkeypatch
) -> None:
    import app.api_token_auth as api_token_auth

    monkeypatch.setattr(api_token_auth, "RATE_LIMIT_PER_MINUTE", 3)

    _user, headers = signed_up_user
    admin_headers = _admin_headers(client, signed_up_user, db_session)
    _enable_public_api(client, admin_headers)

    created = client.post(
        "/api/v1/api-tokens",
        headers=headers,
        json={"name": "Rate limited", "scopes": ["vocal_range"]},
    )
    raw_token = created.json()["token"]
    auth = {"Authorization": f"Bearer {raw_token}"}

    for _ in range(3):
        resp = client.get("/api/public/v1/vocal-range", headers=auth)
        assert resp.status_code == 200

    limited = client.get("/api/public/v1/vocal-range", headers=auth)
    assert limited.status_code == 429
