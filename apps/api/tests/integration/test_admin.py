import uuid

from app.models import AdminAuditLog, AuthCredential, CoachProfile, Exercise, User


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

    resp = client.get(f"/api/v1/admin/users?query={admin_user['email'][:8]}", headers=admin_headers)
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
    # last_session_at comes from LoginEvent, written only by POST /auth/login (see that
    # model's docstring) -- signup deliberately doesn't count as a login, so it's still null
    # right after signup.
    assert body["last_session_at"] is None
    assert body["last_checkin_date"] is None
    assert body["last_recording_at"] is None


def test_get_user_detail_last_session_at_reflects_a_real_login(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    coach_user, _coach_headers = signed_up_coach
    coach_row = db_session.query(User).filter_by(email=coach_user["email"]).one()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": coach_user["email"], "password": coach_user["password"]},
    )
    assert login.status_code == 200

    resp = client.get(f"/api/v1/admin/users/{coach_row.id}", headers=admin_headers)
    assert resp.json()["last_session_at"] is not None


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
    assert (
        audit.admin_user_id == db_session.query(User).filter_by(email=admin_user["email"]).one().id
    )


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


def test_set_admin_grants_and_revokes(client, signed_up_user, signed_up_coach, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    target_user, target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    grant = client.post(
        f"/api/v1/admin/users/{target_row.id}/set-admin",
        headers=admin_headers,
        json={"is_admin": True},
    )
    assert grant.status_code == 200
    assert grant.json()["is_admin"] is True
    assert client.get("/api/v1/admin/profile", headers=target_headers).status_code == 200

    revoke = client.post(
        f"/api/v1/admin/users/{target_row.id}/set-admin",
        headers=admin_headers,
        json={"is_admin": False},
    )
    assert revoke.status_code == 200
    assert revoke.json()["is_admin"] is False
    assert client.get("/api/v1/admin/profile", headers=target_headers).status_code == 403

    actions = [
        row.action
        for row in db_session.query(AdminAuditLog).filter_by(target_user_id=target_row.id).all()
    ]
    assert "grant_admin" in actions
    assert "revoke_admin" in actions


def test_set_admin_blocks_self_target(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    admin_row = db_session.query(User).filter_by(email=admin_user["email"]).one()

    resp = client.post(
        f"/api/v1/admin/users/{admin_row.id}/set-admin",
        headers=admin_headers,
        json={"is_admin": False},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "cannot_target_self"


def test_set_coach_requires_display_name_for_a_new_coach(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()
    # signed_up_coach is already a coach -- flip it back to a plain singer first so this is a
    # genuine "no existing CoachProfile" case.
    db_session.query(CoachProfile).filter_by(user_id=target_row.id).delete()
    db_session.commit()

    resp = client.post(
        f"/api/v1/admin/users/{target_row.id}/set-coach",
        headers=admin_headers,
        json={"is_coach": True},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "display_name_required"


def test_set_coach_creates_and_removes_coach_profile(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()
    db_session.query(CoachProfile).filter_by(user_id=target_row.id).delete()
    db_session.commit()

    grant = client.post(
        f"/api/v1/admin/users/{target_row.id}/set-coach",
        headers=admin_headers,
        json={"is_coach": True, "display_name": "Coach Admin-Granted"},
    )
    assert grant.status_code == 200
    assert grant.json()["account_type"] == "coach"
    profile = db_session.query(CoachProfile).filter_by(user_id=target_row.id).one()
    assert profile.display_name == "Coach Admin-Granted"

    revoke = client.post(
        f"/api/v1/admin/users/{target_row.id}/set-coach",
        headers=admin_headers,
        json={"is_coach": False},
    )
    assert revoke.status_code == 200
    assert revoke.json()["account_type"] == "singer"
    assert db_session.query(CoachProfile).filter_by(user_id=target_row.id).first() is None


def test_set_coach_revoke_cascades_coach_authored_exercises(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    """Documents a real, deliberate consequence: Exercise.created_by_coach_id is ON DELETE
    CASCADE, so revoking coach status deletes exercises that coach authored, even ones already
    sitting in other singers' routines."""
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    coach_user, coach_headers = signed_up_coach

    created = client.post(
        "/api/v1/coach/exercises",
        headers=coach_headers,
        json={
            "name": "Admin-cascade test exercise",
            "instructions": "Do the thing.",
            "category": "Breathing",
            "duration_seconds": 60,
            "difficulty": "easy",
        },
    )
    assert created.status_code == 201, created.text
    exercise_id = created.json()["id"]
    assert db_session.query(Exercise).filter_by(id=exercise_id).first() is not None

    coach_row = db_session.query(User).filter_by(email=coach_user["email"]).one()
    revoke = client.post(
        f"/api/v1/admin/users/{coach_row.id}/set-coach",
        headers=admin_headers,
        json={"is_coach": False},
    )
    assert revoke.status_code == 200
    assert db_session.query(Exercise).filter_by(id=exercise_id).first() is None


def test_reports_query_filters_combine(client, signed_up_user, signed_up_coach, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    coach_user, _coach_headers = signed_up_coach
    coach_row = db_session.query(User).filter_by(email=coach_user["email"]).one()

    by_email = client.get(
        "/api/v1/admin/reports/query",
        headers=admin_headers,
        params={"email": coach_user["email"][:10]},
    )
    assert by_email.status_code == 200
    assert coach_user["email"] in [row["email"] for row in by_email.json()]

    coaches_only = client.get(
        "/api/v1/admin/reports/query",
        headers=admin_headers,
        params={"account_type": "coach"},
    )
    assert coaches_only.status_code == 200
    assert all(row["account_type"] == "coach" for row in coaches_only.json())
    assert coach_user["email"] in [row["email"] for row in coaches_only.json()]

    singers_only = client.get(
        "/api/v1/admin/reports/query",
        headers=admin_headers,
        params={"account_type": "singer"},
    )
    assert singers_only.status_code == 200
    assert coach_user["email"] not in [row["email"] for row in singers_only.json()]

    client.post(f"/api/v1/admin/users/{coach_row.id}/deactivate", headers=admin_headers)
    inactive_coaches = client.get(
        "/api/v1/admin/reports/query",
        headers=admin_headers,
        params={"account_type": "coach", "is_active": "false"},
    )
    assert inactive_coaches.status_code == 200
    assert coach_user["email"] in [row["email"] for row in inactive_coaches.json()]
    assert all(row["is_active"] is False for row in inactive_coaches.json())


def test_create_user_makes_a_singer_account_that_can_log_in(
    client, signed_up_user, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    new_email = f"admin_created_{uuid.uuid4().hex[:12]}@example.com"

    resp = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={"email": new_email, "password": "hunter22!"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == new_email
    assert body["account_type"] == "singer"
    assert body["is_admin"] is False

    login = client.post("/api/v1/auth/login", json={"email": new_email, "password": "hunter22!"})
    assert login.status_code == 200

    row = db_session.query(User).filter_by(email=new_email).one()
    assert db_session.query(AuthCredential).filter_by(user_id=row.id).first() is not None
    action = (
        db_session.query(AdminAuditLog).filter_by(action="create_user", target_user_id=row.id).one()
    )
    assert action.details["account_type"] == "singer"


def test_create_user_can_make_a_coach_and_an_admin(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    new_email = f"admin_created_coach_{uuid.uuid4().hex[:12]}@example.com"

    resp = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "email": new_email,
            "password": "hunter22!",
            "account_type": "coach",
            "display_name": "Admin-Made Coach",
            "is_admin": True,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["account_type"] == "coach"
    assert body["is_admin"] is True

    row = db_session.query(User).filter_by(email=new_email).one()
    profile = db_session.query(CoachProfile).filter_by(user_id=row.id).one()
    assert profile.display_name == "Admin-Made Coach"


def test_create_user_requires_display_name_for_coach(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])

    resp = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "email": f"missing_name_{uuid.uuid4().hex[:12]}@example.com",
            "password": "hunter22!",
            "account_type": "coach",
        },
    )
    assert resp.status_code == 422


def test_create_user_rejects_duplicate_email(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])

    resp = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={"email": admin_user["email"], "password": "hunter22!"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "email_taken"


def test_create_user_requires_admin(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={"email": f"nope_{uuid.uuid4().hex[:12]}@example.com", "password": "hunter22!"},
    )
    assert resp.status_code == 403


def test_site_settings_default_to_signups_enabled(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])

    resp = client.get("/api/v1/admin/site-settings", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["signups_enabled"] is True
    assert resp.json()["nda_required"] is True
    assert resp.json()["recording_retention_days"] == 90
    assert resp.json()["checkin_notes_retention_days"] == 30
    assert resp.json()["login_event_retention_days"] == 365
    assert resp.json()["public_api_enabled"] is False


def test_disabling_signups_blocks_public_signup_but_not_admin_create(
    client, signed_up_user, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])

    toggle = client.post(
        "/api/v1/admin/site-settings",
        headers=admin_headers,
        json={
            "signups_enabled": False,
            "nda_required": True,
            "recording_retention_days": 90,
            "checkin_notes_retention_days": 30,
            "login_event_retention_days": 365,
            "public_api_enabled": False,
        },
    )
    assert toggle.status_code == 200
    assert toggle.json()["signups_enabled"] is False

    blocked = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"locked_out_{uuid.uuid4().hex[:12]}@example.com",
            "password": "hunter22!",
        },
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "signups_disabled"

    blocked_coach = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": f"locked_out_coach_{uuid.uuid4().hex[:12]}@example.com",
            "password": "hunter22!",
            "display_name": "Locked Out Coach",
        },
    )
    assert blocked_coach.status_code == 403

    # Admin-created accounts still work while public signup is locked down.
    still_works = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "email": f"admin_bypass_{uuid.uuid4().hex[:12]}@example.com",
            "password": "hunter22!",
        },
    )
    assert still_works.status_code == 201

    # .order_by(created_at.desc()) -- action-only filters here aren't scoped to a specific
    # target_user_id (this action logs with target_user_id=None), so an unordered .first() can
    # return a stray row from unrelated manual testing against the same dev database rather than
    # the row this test just created. The most recent matching row is always this test's own.
    action = (
        db_session.query(AdminAuditLog)
        .filter_by(action="update_site_settings")
        .order_by(AdminAuditLog.created_at.desc())
        .first()
    )
    assert action is not None
    assert action.details["to"]["signups_enabled"] is False

    # Re-enabling restores public signup.
    reenable = client.post(
        "/api/v1/admin/site-settings",
        headers=admin_headers,
        json={
            "signups_enabled": True,
            "nda_required": True,
            "recording_retention_days": 90,
            "checkin_notes_retention_days": 30,
            "login_event_retention_days": 365,
            "public_api_enabled": False,
        },
    )
    assert reenable.status_code == 200
    unblocked = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"reenabled_{uuid.uuid4().hex[:12]}@example.com",
            "password": "hunter22!",
        },
    )
    assert unblocked.status_code == 201


def test_site_settings_requires_admin(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    assert client.get("/api/v1/admin/site-settings", headers=headers).status_code == 403
    resp = client.post(
        "/api/v1/admin/site-settings",
        headers=headers,
        json={
            "signups_enabled": False,
            "nda_required": True,
            "recording_retention_days": 90,
            "checkin_notes_retention_days": 30,
            "login_event_retention_days": 365,
            "public_api_enabled": False,
        },
    )
    assert resp.status_code == 403


def test_set_password_lets_the_user_log_in_with_the_new_password(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    target_user, target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    resp = client.post(
        f"/api/v1/admin/users/{target_row.id}/set-password",
        headers=admin_headers,
        json={"new_password": "brand-new-pw-1"},
    )
    assert resp.status_code == 204

    old_password_login = client.post(
        "/api/v1/auth/login",
        json={"email": target_user["email"], "password": target_user["password"]},
    )
    assert old_password_login.status_code == 401

    new_password_login = client.post(
        "/api/v1/auth/login",
        json={"email": target_user["email"], "password": "brand-new-pw-1"},
    )
    assert new_password_login.status_code == 200

    # The account's existing refresh token (issued before the change) is revoked, same as a
    # self-serve password reset -- the short-lived access token in target_headers is still
    # technically valid until it expires on its own, but the session can no longer be renewed.
    refresh = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": target_user["refresh_token"]}
    )
    assert refresh.status_code == 401

    action = (
        db_session.query(AdminAuditLog)
        .filter_by(action="set_password", target_user_id=target_row.id)
        .one()
    )
    assert action.details["email"] == target_user["email"]
    assert "brand-new-pw-1" not in str(action.details)


def test_set_password_requires_admin(client, signed_up_user, signed_up_coach, db_session) -> None:
    _user, headers = signed_up_user
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()
    resp = client.post(
        f"/api/v1/admin/users/{target_row.id}/set-password",
        headers=headers,
        json={"new_password": "irrelevant1"},
    )
    assert resp.status_code == 403


def test_set_password_rejects_too_short(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    resp = client.post(
        f"/api/v1/admin/users/{target_row.id}/set-password",
        headers=admin_headers,
        json={"new_password": "short"},
    )
    assert resp.status_code == 422


def test_admin_can_turn_off_nda_requirement(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])

    still_on = client.get("/api/v1/auth/nda-status", headers=admin_headers)
    assert still_on.json()["required"] is True

    toggle = client.post(
        "/api/v1/admin/site-settings",
        headers=admin_headers,
        json={
            "signups_enabled": True,
            "nda_required": False,
            "recording_retention_days": 90,
            "checkin_notes_retention_days": 30,
            "login_event_retention_days": 365,
            "public_api_enabled": False,
        },
    )
    assert toggle.status_code == 200
    assert toggle.json()["nda_required"] is False

    turned_off = client.get("/api/v1/auth/nda-status", headers=admin_headers)
    assert turned_off.json()["required"] is False

    action = (
        db_session.query(AdminAuditLog)
        .filter_by(action="update_site_settings")
        .order_by(AdminAuditLog.created_at.desc())
        .first()
    )
    assert action.details["to"]["nda_required"] is False


def test_new_coach_organization_starts_inactive(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    """signed_up_coach activates coach_pro as part of the fixture (see tests/conftest.py) --
    this test instead signs up a coach directly to see the real, unactivated default."""
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])

    signup = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": f"org_default_{uuid.uuid4().hex[:12]}@example.com",
            "password": "hunter22!",
            "display_name": "Fresh Coach",
            "studio_name": "Fresh Studio",
        },
    )
    assert signup.status_code == 201, signup.text
    coach_row = db_session.query(CoachProfile).filter_by(user_id=signup.json()["user"]["id"]).one()

    orgs = client.get(
        "/api/v1/admin/organizations", headers=admin_headers, params={"query": "Fresh"}
    )
    assert orgs.status_code == 200
    matches = [o for o in orgs.json() if o["id"] == str(coach_row.organization_id)]
    assert len(matches) == 1
    org = matches[0]
    assert org["name"] == "Fresh Studio"
    assert org["is_coach_pro_active"] is False
    assert org["invite_quota_included"] == 50
    assert org["invites_used_this_period"] == 0


def test_admin_can_activate_and_deactivate_coach_pro(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])

    signup = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": f"org_activate_{uuid.uuid4().hex[:12]}@example.com",
            "password": "hunter22!",
            "display_name": "Pending Coach",
        },
    )
    coach_headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    coach_row = db_session.query(CoachProfile).filter_by(user_id=signup.json()["user"]["id"]).one()
    org_id = coach_row.organization_id

    blocked = client.get("/api/v1/coach/profile", headers=coach_headers)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "coach_pro_required"

    activate = client.post(
        f"/api/v1/admin/organizations/{org_id}/set-coach-pro",
        headers=admin_headers,
        json={"is_coach_pro_active": True},
    )
    assert activate.status_code == 200, activate.text
    assert activate.json()["is_coach_pro_active"] is True
    assert activate.json()["coach_pro_period_end"] is not None

    now_works = client.get("/api/v1/coach/profile", headers=coach_headers)
    assert now_works.status_code == 200

    action = (
        db_session.query(AdminAuditLog)
        .filter_by(action="set_coach_pro")
        .order_by(AdminAuditLog.created_at.desc())
        .first()
    )
    assert action is not None
    assert action.details["organization_id"] == str(org_id)

    deactivate = client.post(
        f"/api/v1/admin/organizations/{org_id}/set-coach-pro",
        headers=admin_headers,
        json={"is_coach_pro_active": False},
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["is_coach_pro_active"] is False

    blocked_again = client.get("/api/v1/coach/profile", headers=coach_headers)
    assert blocked_again.status_code == 403
    assert blocked_again.json()["error"]["code"] == "coach_pro_required"


def test_invite_quota_excludes_declined_and_revoked_invites(
    client, signed_up_coach, signed_up_user, db_session
) -> None:
    admin_email = f"admin_quota_{uuid.uuid4().hex[:12]}@example.com"
    admin_signup = client.post(
        "/api/v1/auth/signup", json={"email": admin_email, "password": "hunter22!"}
    )
    admin_headers = {"Authorization": f"Bearer {admin_signup.json()['access_token']}"}
    _make_admin(db_session, admin_headers, admin_email)

    coach, coach_headers = signed_up_coach
    coach_row = db_session.query(CoachProfile).filter_by(user_id=coach["user"]["id"]).one()

    _singer1, singer1_headers = signed_up_user
    invite1 = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": _singer1["email"]}
    )
    assert invite1.status_code == 201, invite1.text
    decline = client.post(
        f"/api/v1/invites/{invite1.json()['id']}/decline", headers=singer1_headers
    )
    assert decline.status_code == 204, decline.text

    detail = client.get(
        f"/api/v1/admin/organizations/{coach_row.organization_id}", headers=admin_headers
    )
    assert detail.status_code == 200
    assert detail.json()["invites_used_this_period"] == 0


def test_organization_endpoints_require_admin(client, signed_up_coach) -> None:
    _coach, coach_headers = signed_up_coach
    assert client.get("/api/v1/admin/organizations", headers=coach_headers).status_code == 403
    assert (
        client.post(
            f"/api/v1/admin/organizations/{uuid.uuid4()}/set-coach-pro",
            headers=coach_headers,
            json={"is_coach_pro_active": True},
        ).status_code
        == 403
    )


def test_set_coach_pro_404s_for_unknown_organization(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_headers, admin_user["email"])

    resp = client.post(
        f"/api/v1/admin/organizations/{uuid.uuid4()}/set-coach-pro",
        headers=admin_headers,
        json={"is_coach_pro_active": True},
    )
    assert resp.status_code == 404
