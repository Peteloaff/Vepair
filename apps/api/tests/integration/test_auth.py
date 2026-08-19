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

    # Dev-mode "log" email backend logs the reset link (with the raw token as a query param)
    # instead of sending it — pull it back out to simulate the user clicking the emailed link.
    token = None
    for record in caplog.records:
        message = record.getMessage()
        if "reset-password?token=" in message:
            token = message.rsplit("reset-password?token=", 1)[-1].split()[0]
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


def test_delete_account_rejects_wrong_password(client, signed_up_user) -> None:
    user, headers = signed_up_user
    resp = client.request(
        "DELETE",
        "/api/v1/auth/me",
        headers=headers,
        json={"password": "definitely-wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_password"

    # The account must still exist and be usable.
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200


def test_delete_account_requires_auth(client) -> None:
    resp = client.request("DELETE", "/api/v1/auth/me", json={"password": "whatever123"})
    assert resp.status_code == 401


def test_delete_account_removes_it_and_revokes_access(client, signed_up_user) -> None:
    user, headers = signed_up_user
    resp = client.request(
        "DELETE",
        "/api/v1/auth/me",
        headers=headers,
        json={"password": user["password"]},
    )
    assert resp.status_code == 204

    # The old access token is stateless (JWT), but the account it points at is gone.
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 401
    assert me.json()["error"]["code"] == "user_not_found"

    # Logging in again must fail — the account no longer exists.
    login = client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": user["password"]}
    )
    assert login.status_code == 401

    # The refresh token is fully gone (cascaded), not just revoked.
    refresh = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": user["refresh_token"]}
    )
    assert refresh.status_code == 401

    # The email is free again for a fresh signup.
    resignup = client.post(
        "/api/v1/auth/signup", json={"email": user["email"], "password": "brand-new-pw-1"}
    )
    assert resignup.status_code == 201


def test_delete_account_wipes_recording_storage(client, signed_up_user, db_session) -> None:
    from app.storage import get_storage
    from tests.integration.test_recordings import clean_wav_bytes

    user, headers = signed_up_user
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    upload = client.post(
        f"/api/v1/voice-sessions/{session_id}/recordings",
        headers=headers,
        data={"sample_type": "sustained_ah"},
        files={"file": ("recording.wav", clean_wav_bytes(), "audio/wav")},
    )
    assert upload.status_code == 201

    from app.models import Recording

    recording = db_session.query(Recording).filter_by(id=upload.json()["id"]).one()
    file_path = recording.file_path
    storage = get_storage()
    assert storage.exists(file_path)

    resp = client.request(
        "DELETE",
        "/api/v1/auth/me",
        headers=headers,
        json={"password": user["password"]},
    )
    assert resp.status_code == 204
    assert not storage.exists(file_path)


def test_nda_status_defaults_to_required_and_unaccepted(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.get("/api/v1/auth/nda-status", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["required"] is True
    assert body["accepted_at"] is None


def test_accept_nda_persists_and_is_reflected_in_status(client, signed_up_user) -> None:
    _user, headers = signed_up_user

    accept = client.post("/api/v1/auth/accept-nda", headers=headers)
    assert accept.status_code == 200
    assert accept.json()["accepted_at"] is not None

    status = client.get("/api/v1/auth/nda-status", headers=headers)
    assert status.status_code == 200
    assert status.json()["accepted_at"] is not None

    # Accepting again (e.g. a stray double-click) is idempotent, not an error.
    accept_again = client.post("/api/v1/auth/accept-nda", headers=headers)
    assert accept_again.status_code == 200


def test_nda_status_requires_auth(client) -> None:
    assert client.get("/api/v1/auth/nda-status").status_code == 401
    assert client.post("/api/v1/auth/accept-nda").status_code == 401
