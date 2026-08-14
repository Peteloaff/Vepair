from app.models import AdminAuditLog, User


def _make_admin(db_session, headers, user_email) -> None:
    """Flips is_admin on the account behind `headers` -- mirrors the real one-time manual
    `UPDATE users SET is_admin = true` bootstrap (see TECHNICAL_GUIDE.md), just done directly
    against the test's db_session instead of psql."""
    user = db_session.query(User).filter_by(email=user_email).one()
    user.is_admin = True
    db_session.commit()


def test_non_admin_is_rejected_from_every_admin_endpoint(client, signed_up_user) -> None:
    user, headers = signed_up_user
    assert client.get("/api/v1/admin/profile", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/reports/summary", headers=headers).status_code == 403


def test_unauthenticated_is_rejected(client) -> None:
    assert client.get("/api/v1/admin/profile").status_code == 401
    assert client.get("/api/v1/admin/users").status_code == 401


def test_admin_profile_check_succeeds_for_real_admin(client, signed_up_user, db_session) -> None:
    user, headers = signed_up_user
    _make_admin(db_session, headers, user["email"])
    resp = client.get("/api/v1/admin/profile", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == user["email"]


def test_search_users_by_email_substring(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])

    resp = client.get(
        f"/api/v1/admin/users?query={admin_user['email'][:8]}", headers=admin_headers
    )
    assert resp.status_code == 200
    emails = [row["email"] for row in resp.json()]
    assert admin_user["email"] in emails


def test_get_user_detail_includes_activity_proxies(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    coach_user, _coach_headers = signed_up_coach

    coach_row = db_session.query(User).filter_by(email=coach_user["email"]).one()
    resp = client.get(f"/api/v1/admin/users/{coach_row.id}", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["account_type"] == "coach"
    assert body["last_session_at"] is not None
    assert body["last_checkin_date"] is None
    assert body["last_recording_at"] is None


def test_get_user_detail_404_for_unknown_id(client, signed_up_user, db_session) -> None:
    import uuid

    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])

    resp = client.get(f"/api/v1/admin/users/{uuid.uuid4()}", headers=admin_headers)
    assert resp.status_code == 404


def test_deactivate_locks_out_the_account_and_revokes_sessions(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    target_user, target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    resp = client.post(f"/api/v1/admin/users/{target_row.id}/deactivate", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # The deactivated account's own existing access token is now rejected.
    me = client.get("/api/v1/auth/me", headers=target_headers)
    assert me.status_code == 401
    assert me.json()["error"]["code"] == "account_deactivated"

    # Its refresh token is revoked too.
    refresh = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": target_user["refresh_token"]}
    )
    assert refresh.status_code == 401

    # Login is rejected outright while deactivated.
    login = client.post(
        "/api/v1/auth/login",
        json={"email": target_user["email"], "password": target_user["password"]},
    )
    assert login.status_code == 401
    assert login.json()["error"]["code"] == "account_deactivated"

    audit = (
        db_session.query(AdminAuditLog)
        .filter_by(target_user_id=target_row.id, action="deactivate_user")
        .one()
    )
    assert audit.admin_user_id == db_session.query(User).filter_by(
        email=admin_user["email"]
    ).one().id


def test_reactivate_restores_access(client, signed_up_user, signed_up_coach, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    client.post(f"/api/v1/admin/users/{target_row.id}/deactivate", headers=admin_headers)
    resp = client.post(f"/api/v1/admin/users/{target_row.id}/reactivate", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    login = client.post(
        "/api/v1/auth/login",
        json={"email": target_user["email"], "password": target_user["password"]},
    )
    assert login.status_code == 200


def test_admin_cannot_deactivate_or_delete_self(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    admin_row = db_session.query(User).filter_by(email=admin_user["email"]).one()

    deactivate = client.post(
        f"/api/v1/admin/users/{admin_row.id}/deactivate", headers=admin_headers
    )
    assert deactivate.status_code == 400
    assert deactivate.json()["error"]["code"] == "cannot_target_self"

    delete = client.post(f"/api/v1/admin/users/{admin_row.id}/delete", headers=admin_headers)
    assert delete.status_code == 400
    assert delete.json()["error"]["code"] == "cannot_target_self"


def test_hard_delete_requires_deactivation_first(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    resp = client.post(f"/api/v1/admin/users/{target_row.id}/delete", headers=admin_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "must_deactivate_first"


def test_hard_delete_removes_account_after_deactivation(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()
    target_id = target_row.id

    client.post(f"/api/v1/admin/users/{target_id}/deactivate", headers=admin_headers)
    resp = client.post(f"/api/v1/admin/users/{target_id}/delete", headers=admin_headers)
    assert resp.status_code == 204

    assert db_session.get(User, target_id) is None

    audit = (
        db_session.query(AdminAuditLog)
        .filter_by(target_user_id=None, action="hard_delete_user")
        .all()
    )
    # target_user_id is SET NULL once the target row is gone, but the audit row survives with
    # the captured email in `details`.
    assert any(row.details and row.details.get("email") == target_user["email"] for row in audit)

    resignup = client.post(
        "/api/v1/auth/signup", json={"email": target_user["email"], "password": "brand-new-pw-1"}
    )
    assert resignup.status_code == 201


def test_send_password_reset_triggers_real_reset_flow(
    client, signed_up_user, signed_up_coach, db_session, caplog
) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="vepair.email")
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    resp = client.post(
        f"/api/v1/admin/users/{target_row.id}/send-password-reset", headers=admin_headers
    )
    assert resp.status_code == 202

    token = None
    for record in caplog.records:
        message = record.getMessage()
        if "reset-password?token=" in message:
            token = message.rsplit("reset-password?token=", 1)[-1].split()[0]
    assert token, "reset token was not logged by the dev email backend"

    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "admin-triggered-pw-1"},
    )
    assert confirm.status_code == 204

    login = client.post(
        "/api/v1/auth/login",
        json={"email": target_user["email"], "password": "admin-triggered-pw-1"},
    )
    assert login.status_code == 200

    audit = (
        db_session.query(AdminAuditLog)
        .filter_by(target_user_id=target_row.id, action="send_password_reset")
        .one()
    )
    assert audit.details["email"] == target_user["email"]


def test_reports_summary_reflects_signups_and_active_state(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    resp = client.get("/api/v1/admin/reports/summary", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_users"] >= 2
    assert body["coach_count"] >= 1
    assert body["active_count"] >= 2

    client.post(f"/api/v1/admin/users/{target_row.id}/deactivate", headers=admin_headers)
    after = client.get("/api/v1/admin/reports/summary", headers=admin_headers).json()
    assert after["deactivated_count"] >= 1
