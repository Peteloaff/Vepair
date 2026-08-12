import logging
import uuid


def _unique_email() -> str:
    return f"test_{uuid.uuid4().hex[:12]}@example.com"


def test_signup_creates_account_and_returns_tokens(client) -> None:
    email = _unique_email()
    resp = client.post(
        "/api/v1/auth/signup", json={"email": email, "password": "correcthorse123"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == email
    assert body["access_token"]
    assert body["refresh_token"]


def test_signup_rejects_duplicate_email(client) -> None:
    email = _unique_email()
    payload = {"email": email, "password": "correcthorse123"}
    first = client.post("/api/v1/auth/signup", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/signup", json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "email_taken"


def test_signup_rejects_short_password(client) -> None:
    resp = client.post(
        "/api/v1/auth/signup", json={"email": _unique_email(), "password": "short"}
    )
    assert resp.status_code == 422


def test_signup_rejects_invalid_email(client) -> None:
    resp = client.post(
        "/api/v1/auth/signup", json={"email": "not-an-email", "password": "correcthorse123"}
    )
    assert resp.status_code == 422


def test_login_with_correct_credentials(client, signed_up_user) -> None:
    user, _headers = signed_up_user
    resp = client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": user["password"]}
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == user["email"]


def test_login_with_wrong_password_is_rejected(client, signed_up_user) -> None:
    user, _headers = signed_up_user
    resp = client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"


def test_login_with_unknown_email_is_rejected_generically(client) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody-here@example.com", "password": "whatever123"},
    )
    assert resp.status_code == 401
    # Same error code as wrong-password, so responses don't reveal whether an email exists.
    assert resp.json()["error"]["code"] == "invalid_credentials"


def test_me_requires_a_valid_token(client) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user_with_valid_token(client, signed_up_user) -> None:
    user, headers = signed_up_user
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == user["email"]


def test_refresh_issues_new_tokens_and_rotates_old_one(client, signed_up_user) -> None:
    user, _headers = signed_up_user
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": user["refresh_token"]})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != user["refresh_token"]

    # The old refresh token must no longer work (rotation).
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": user["refresh_token"]})
    assert reuse.status_code == 401


def test_logout_revokes_the_refresh_token(client, signed_up_user) -> None:
    user, _headers = signed_up_user
    logout_resp = client.post(
        "/api/v1/auth/logout", json={"refresh_token": user["refresh_token"]}
    )
    assert logout_resp.status_code == 204

    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": user["refresh_token"]})
    assert reuse.status_code == 401


def test_password_reset_flow(client, signed_up_user, caplog) -> None:
    caplog.set_level(logging.INFO, logger="vepair.email")
    user, _headers = signed_up_user

    request_resp = client.post(
        "/api/v1/auth/password-reset/request", json={"email": user["email"]}
    )
    assert request_resp.status_code == 202

    # Dev-mode "email" backend logs the raw token — pull it back out to simulate the user
    # clicking the emailed link.
    token = None
    for record in caplog.records:
        if "Password reset requested" in record.getMessage():
            token = record.getMessage().rsplit("token: ", 1)[-1]
    assert token, "reset token was not logged by the dev email backend"

    confirm_resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "brand-new-password-1"},
    )
    assert confirm_resp.status_code == 204

    # Old password no longer works, new one does.
    old_login = client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": user["password"]}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": "brand-new-password-1"},
    )
    assert new_login.status_code == 200

    # Password reset also revokes existing sessions.
    stale_refresh = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": user["refresh_token"]}
    )
    assert stale_refresh.status_code == 401


def test_password_reset_request_for_unknown_email_still_returns_202(client) -> None:
    resp = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"}
    )
    assert resp.status_code == 202


def test_password_reset_confirm_rejects_invalid_token(client) -> None:
    resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "not-a-real-token", "new_password": "brand-new-password-1"},
    )
    assert resp.status_code == 400
