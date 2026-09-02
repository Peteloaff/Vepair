"""Admin tooling gaps (Part B): role tiers, bulk operations, impersonation, login events, and
the contact-list export -- driven through the real API, mirroring test_admin.py's fixtures."""

import uuid

from app.models import AdminAuditLog, LoginEvent, User


def _make_admin(db_session, user_email: str, *, admin_role: str | None = None) -> None:
    """Same as test_admin.py's _make_admin, plus an optional tier -- admin_role=None reads as
    "full" (see User.admin_role's docstring), so passing nothing here is a full admin."""
    user = db_session.query(User).filter_by(email=user_email).one()
    user.is_admin = True
    user.admin_role = admin_role
    db_session.commit()


# --- B1: admin role tiers ---


def test_support_admin_can_search_and_deactivate(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"], admin_role="support")
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    search = client.get("/api/v1/admin/users", headers=admin_headers)
    assert search.status_code == 200

    deactivate = client.post(
        f"/api/v1/admin/users/{target_row.id}/deactivate", headers=admin_headers
    )
    assert deactivate.status_code == 200

    reset = client.post(
        f"/api/v1/admin/users/{target_row.id}/send-password-reset", headers=admin_headers
    )
    assert reset.status_code == 202


def test_support_admin_is_rejected_from_full_admin_only_endpoints(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"], admin_role="support")
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    # hard-delete requires deactivation first, but a support admin should 403 before even
    # getting to that check.
    assert (
        client.post(f"/api/v1/admin/users/{target_row.id}/delete", headers=admin_headers).json()[
            "error"
        ]["code"]
        == "full_admin_required"
    )
    assert (
        client.post(
            f"/api/v1/admin/users/{target_row.id}/set-admin",
            headers=admin_headers,
            json={"is_admin": True},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/admin/users/{target_row.id}/set-coach",
            headers=admin_headers,
            json={"is_coach": True, "display_name": "Coach"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/admin/users/{target_row.id}/set-password",
            headers=admin_headers,
            json={"new_password": "correcthorse123"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/admin/users",
            headers=admin_headers,
            json={"email": "support-created@example.com", "password": "correcthorse123"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/admin/site-settings",
            headers=admin_headers,
            json={
                "signups_enabled": True,
                "nda_required": True,
                "recording_retention_days": 90,
                "checkin_notes_retention_days": 30,
                "login_event_retention_days": 365,
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/admin/users/{target_row.id}/impersonate", headers=admin_headers
        ).status_code
        == 403
    )
    assert client.get("/api/v1/admin/users/export", headers=admin_headers).status_code == 403


def test_full_admin_can_grant_support_tier_and_it_sticks(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])  # full
    target_user, target_headers = signed_up_coach

    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()
    resp = client.post(
        f"/api/v1/admin/users/{target_row.id}/set-admin",
        headers=admin_headers,
        json={"is_admin": True, "admin_role": "support"},
    )
    assert resp.status_code == 200
    assert resp.json()["admin_role"] == "support"

    # The newly-support admin is immediately rejected from a full-only action.
    resp2 = client.post(
        "/api/v1/admin/users",
        headers=target_headers,
        json={"email": "nested-created@example.com", "password": "correcthorse123"},
    )
    assert resp2.status_code == 403


def test_revoking_admin_clears_the_tier(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    client.post(
        f"/api/v1/admin/users/{target_row.id}/set-admin",
        headers=admin_headers,
        json={"is_admin": True, "admin_role": "support"},
    )
    revoke = client.post(
        f"/api/v1/admin/users/{target_row.id}/set-admin",
        headers=admin_headers,
        json={"is_admin": False},
    )
    assert revoke.status_code == 200
    assert revoke.json()["admin_role"] is None


# --- B2: bulk operations ---


def test_bulk_deactivate_and_reactivate(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])

    targets = []
    for i in range(3):
        signup = client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"bulk-target-{i}-{uuid.uuid4().hex[:6]}@example.com",
                "password": "correcthorse123",
            },
        )
        targets.append(signup.json()["user"]["id"])

    deactivate = client.post(
        "/api/v1/admin/users/bulk-deactivate",
        headers=admin_headers,
        json={"user_ids": targets},
    )
    assert deactivate.status_code == 200
    body = deactivate.json()
    assert set(body["updated"]) == set(targets)
    assert body["not_found"] == []

    for target_id in targets:
        row = db_session.get(User, uuid.UUID(target_id))
        assert row.is_active is False

    reactivate = client.post(
        "/api/v1/admin/users/bulk-reactivate",
        headers=admin_headers,
        json={"user_ids": targets},
    )
    assert reactivate.status_code == 200
    for target_id in targets:
        db_session.refresh(db_session.get(User, uuid.UUID(target_id)))
        assert db_session.get(User, uuid.UUID(target_id)).is_active is True


def test_bulk_deactivate_skips_self_and_reports_missing_ids(
    client, signed_up_user, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    admin_row = db_session.query(User).filter_by(email=admin_user["email"]).one()
    missing_id = uuid.uuid4()

    resp = client.post(
        "/api/v1/admin/users/bulk-deactivate",
        headers=admin_headers,
        json={"user_ids": [str(admin_row.id), str(missing_id)]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert str(admin_row.id) not in body["updated"]
    assert str(missing_id) in body["not_found"]

    # The admin never actually got deactivated.
    db_session.refresh(admin_row)
    assert admin_row.is_active is True


def test_bulk_deactivate_writes_one_audit_row_per_user(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])

    targets = []
    for i in range(2):
        signup = client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"bulk-audit-{i}-{uuid.uuid4().hex[:6]}@example.com",
                "password": "correcthorse123",
            },
        )
        targets.append(signup.json()["user"]["id"])

    client.post(
        "/api/v1/admin/users/bulk-deactivate", headers=admin_headers, json={"user_ids": targets}
    )
    rows = (
        db_session.query(AdminAuditLog)
        .filter(
            AdminAuditLog.action == "deactivate_user",
            AdminAuditLog.target_user_id.in_([uuid.UUID(t) for t in targets]),
        )
        .all()
    )
    assert len(rows) == 2


# --- B3: impersonation ---


def _login(client, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_impersonate_issues_a_token_that_reads_as_the_target(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    target_user, target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    resp = client.post(f"/api/v1/admin/users/{target_row.id}/impersonate", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user_email"] == target_user["email"]
    assert "refresh_token" not in body

    impersonation_headers = {"Authorization": f"Bearer {body['access_token']}"}
    me = client.get("/api/v1/auth/me", headers=impersonation_headers)
    assert me.status_code == 200
    assert me.json()["email"] == target_user["email"]


def test_impersonation_token_is_rejected_on_write_requests(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    token = client.post(
        f"/api/v1/admin/users/{target_row.id}/impersonate", headers=admin_headers
    ).json()["access_token"]
    impersonation_headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/v1/checkins",
        headers=impersonation_headers,
        json={"checkin_date": "2026-01-01", "voice_quality": 5},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "impersonation_read_only"


def test_impersonate_start_and_end_are_audited(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    client.post(f"/api/v1/admin/users/{target_row.id}/impersonate", headers=admin_headers)
    end = client.post(f"/api/v1/admin/users/{target_row.id}/impersonate/end", headers=admin_headers)
    assert end.status_code == 204

    actions = {
        row.action
        for row in db_session.query(AdminAuditLog).filter_by(target_user_id=target_row.id).all()
    }
    assert "impersonate_start" in actions
    assert "impersonate_end" in actions


def test_cannot_impersonate_self(client, signed_up_user, db_session) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    admin_row = db_session.query(User).filter_by(email=admin_user["email"]).one()

    resp = client.post(f"/api/v1/admin/users/{admin_row.id}/impersonate", headers=admin_headers)
    assert resp.status_code == 400


# --- B4: login events ---


def test_login_writes_a_login_event(client, signed_up_user, db_session) -> None:
    user, _headers = signed_up_user
    before = db_session.query(LoginEvent).filter_by(user_id=uuid.UUID(user["user"]["id"])).count()

    _login(client, user["email"], user["password"])

    after = db_session.query(LoginEvent).filter_by(user_id=uuid.UUID(user["user"]["id"])).count()
    assert after == before + 1


def test_signup_does_not_write_a_login_event(client, db_session) -> None:
    email = f"no-login-event-{uuid.uuid4().hex[:8]}@example.com"
    signup = client.post(
        "/api/v1/auth/signup", json={"email": email, "password": "correcthorse123"}
    )
    user_id = uuid.UUID(signup.json()["user"]["id"])
    assert db_session.query(LoginEvent).filter_by(user_id=user_id).count() == 0


def test_admin_user_detail_reflects_real_last_login(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    target_user, _target_headers = signed_up_coach
    target_row = db_session.query(User).filter_by(email=target_user["email"]).one()

    before = client.get(f"/api/v1/admin/users/{target_row.id}", headers=admin_headers)
    first_seen = before.json()["last_session_at"]

    _login(client, target_user["email"], target_user["password"])

    after = client.get(f"/api/v1/admin/users/{target_row.id}", headers=admin_headers)
    assert after.json()["last_session_at"] is not None
    assert after.json()["last_session_at"] != first_seen


# --- B5: contact-list export ---


def test_export_contact_list_returns_csv_of_emails_only(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    target_user, _target_headers = signed_up_coach

    resp = client.get(
        f"/api/v1/admin/users/export?email={target_user['email'][:10]}", headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    lines = resp.text.strip().splitlines()
    assert lines[0] == "email"
    assert target_user["email"] in lines


def test_export_contact_list_is_audited_with_filters_not_content(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, admin_headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    target_user, _target_headers = signed_up_coach

    client.get(
        f"/api/v1/admin/users/export?email={target_user['email'][:10]}", headers=admin_headers
    )

    row = (
        db_session.query(AdminAuditLog)
        .filter_by(action="export_contact_list")
        .order_by(AdminAuditLog.created_at.desc())
        .first()
    )
    assert row is not None
    assert row.details["filters"]["email"] == target_user["email"][:10]
    assert "emails" not in row.details
    assert row.details["row_count"] >= 1
