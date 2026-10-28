"""Organization teams: several coaches under one clinic or studio, with an admin/member role.
Covers the coach-side Team endpoints, the platform-admin equivalents, and -- the part that
matters most -- that sharing an organization never shares a coach's Vrotégés."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models import AdminAuditLog, CoachProfile, Organization, User
from tests.integration.test_admin import _make_admin
from tests.integration.test_coach_assignments import _connect


def _add(client, headers, email, name="New Coach", role="member"):
    return client.post(
        "/api/v1/coach/team/members",
        headers=headers,
        json={"email": email, "display_name": name, "org_role": role},
    )


def _login_as_new_member(client, welcome_emails, email, password="brandnewpass123"):
    token = next(e["token"] for e in welcome_emails if e["to"] == email)
    confirm = client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": password}
    )
    assert confirm.status_code == 204, confirm.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _team(client, headers):
    resp = client.get("/api/v1/coach/team", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_org_admin_adds_a_coach_who_sets_their_own_password(
    client, signed_up_coach, welcome_emails
) -> None:
    _coach, admin_headers = signed_up_coach
    created = _add(client, admin_headers, "second.coach@example.com", "Second Coach")
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "invited"
    assert created.json()["org_role"] == "member"
    assert [e["to"] for e in welcome_emails] == ["second.coach@example.com"]

    member_headers = _login_as_new_member(client, welcome_emails, "second.coach@example.com")

    # Logged in once -> no longer "invited"; and they're a real coach in the same organization.
    team = _team(client, member_headers)
    assert team["my_role"] == "member"
    assert {m["email"]: m["status"] for m in team["members"]}["second.coach@example.com"] == (
        "active"
    )
    profile = client.get("/api/v1/coach/profile", headers=member_headers).json()
    assert profile["org_role"] == "member"
    assert profile["studio_name"] == "Test Studio"


def test_a_member_cannot_manage_the_team(client, signed_up_coach, welcome_emails) -> None:
    _coach, admin_headers = signed_up_coach
    _add(client, admin_headers, "member@example.com")
    member_headers = _login_as_new_member(client, welcome_emails, "member@example.com")

    assert _add(client, member_headers, "another@example.com").status_code == 403
    admin_coach_id = _team(client, admin_headers)["members"][0]["coach_id"]
    patch = client.patch(
        f"/api/v1/coach/team/members/{admin_coach_id}",
        headers=member_headers,
        json={"org_role": "member"},
    )
    assert patch.status_code == 403
    assert patch.json()["error"]["code"] == "org_admin_required"
    # ...but they can still see who is on the team.
    assert len(_team(client, member_headers)["members"]) == 2


def test_adding_an_email_that_already_has_an_account_is_refused(
    client, signed_up_coach, signed_up_user, welcome_emails
) -> None:
    _coach, admin_headers = signed_up_coach
    singer, _ = signed_up_user
    resp = _add(client, admin_headers, singer["email"])
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "email_taken"
    assert welcome_emails == []


def test_an_org_always_keeps_one_active_admin(client, signed_up_coach, welcome_emails) -> None:
    _coach, admin_headers = signed_up_coach
    me = _team(client, admin_headers)["members"][0]

    demote = client.patch(
        f"/api/v1/coach/team/members/{me['coach_id']}",
        headers=admin_headers,
        json={"org_role": "member"},
    )
    assert demote.status_code == 409
    assert demote.json()["error"]["code"] == "last_admin"

    # With a second admin in place, the first can step down.
    _add(client, admin_headers, "co.admin@example.com", role="admin")
    assert (
        client.patch(
            f"/api/v1/coach/team/members/{me['coach_id']}",
            headers=admin_headers,
            json={"org_role": "member"},
        ).status_code
        == 200
    )


def test_an_admin_cannot_deactivate_themselves(client, signed_up_coach, welcome_emails) -> None:
    _coach, admin_headers = signed_up_coach
    _add(client, admin_headers, "co.admin@example.com", role="admin")
    me = next(m for m in _team(client, admin_headers)["members"] if m["is_me"])

    resp = client.patch(
        f"/api/v1/coach/team/members/{me['coach_id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "cannot_deactivate_self"


def test_deactivating_a_member_blocks_their_login_and_can_be_undone(
    client, signed_up_coach, welcome_emails
) -> None:
    _coach, admin_headers = signed_up_coach
    created = _add(client, admin_headers, "temp@example.com").json()
    member_headers = _login_as_new_member(client, welcome_emails, "temp@example.com")
    url = f"/api/v1/coach/team/members/{created['coach_id']}"

    off = client.patch(url, headers=admin_headers, json={"is_active": False})
    assert off.status_code == 200
    assert off.json()["status"] == "deactivated"
    assert client.get("/api/v1/coach/team", headers=member_headers).status_code == 401

    on = client.patch(url, headers=admin_headers, json={"is_active": True})
    assert on.json()["status"] == "active"
    assert client.get("/api/v1/coach/team", headers=member_headers).status_code == 200


def test_an_admin_cannot_touch_another_organizations_member(
    client, signed_up_coach, db_session, welcome_emails
) -> None:
    _coach, admin_headers = signed_up_coach
    other = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": "other.clinic@example.com",
            "password": "correcthorse123",
            "display_name": "Other",
            "studio_name": "Other Clinic",
        },
    ).json()
    other_coach = db_session.query(CoachProfile).filter_by(display_name="Other").one()
    # (An unactivated org can't act anyway; the point is the 404 for a foreign coach id.)
    del other
    resp = client.patch(
        f"/api/v1/coach/team/members/{other_coach.id}",
        headers=admin_headers,
        json={"org_role": "admin"},
    )
    assert resp.status_code == 404


def test_coaches_in_one_org_never_see_each_others_singers(
    client, signed_up_coach, signed_up_user, welcome_emails
) -> None:
    """The privacy promise: a singer consents to one coach, not to the clinic."""
    admin, admin_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _add(client, admin_headers, "member@example.com")
    member_headers = _login_as_new_member(client, welcome_emails, "member@example.com")

    # The singer connects to the *member*. The org admin must not see them.
    _connect(client, member_headers, singer["email"], singer_headers, ["recovery_trends"])
    assert len(client.get("/api/v1/coach/singers", headers=member_headers).json()) == 1
    assert client.get("/api/v1/coach/singers", headers=admin_headers).json() == []
    summary = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary", headers=admin_headers
    )
    assert summary.status_code == 403

    # The team page only ever shows a count.
    members = {m["email"]: m for m in _team(client, admin_headers)["members"]}
    assert members["member@example.com"]["singer_count"] == 1
    assert "singers" not in members["member@example.com"]


def test_invite_quota_is_shared_across_the_team(
    client, signed_up_coach, db_session, welcome_emails
) -> None:
    coach, admin_headers = signed_up_coach
    # Backdate the period: invites are stamped with the DB's transaction-start now(), which in a
    # rolled-back test transaction is earlier than the fixture's Python-clock period start.
    org = (
        db_session.query(Organization)
        .join(CoachProfile, CoachProfile.organization_id == Organization.id)
        .filter(CoachProfile.user_id == coach["user"]["id"])
        .one()
    )
    org.coach_pro_period_start = datetime.now(UTC) - timedelta(days=1)
    db_session.commit()
    _add(client, admin_headers, "member@example.com")
    member_headers = _login_as_new_member(client, welcome_emails, "member@example.com")

    before = _team(client, admin_headers)["invites_used_this_period"]
    sent = client.post(
        "/api/v1/coach/invites", headers=member_headers, json={"singer_email": "x@example.com"}
    )
    assert sent.status_code == 201, sent.text
    after = _team(client, admin_headers)
    assert after["invites_used_this_period"] == before + 1
    assert after["invite_quota_included"] == 50


def test_resend_welcome_issues_a_fresh_link(client, signed_up_coach, welcome_emails) -> None:
    _coach, admin_headers = signed_up_coach
    created = _add(client, admin_headers, "member@example.com").json()
    resp = client.post(
        f"/api/v1/coach/team/members/{created['coach_id']}/resend-welcome", headers=admin_headers
    )
    assert resp.status_code == 202
    assert len(welcome_emails) == 2
    assert welcome_emails[0]["token"] != welcome_emails[1]["token"]


# ---- platform admin console ----


def _platform_admin(client, signed_up_user, db_session):
    user, headers = signed_up_user
    _make_admin(db_session, headers, user["email"])
    return headers


def _org_id(client, admin_headers, query):
    orgs = client.get(
        "/api/v1/admin/organizations", headers=admin_headers, params={"query": query}
    ).json()
    return orgs


def test_organization_list_shows_one_row_per_org_with_a_member_count(
    client, signed_up_coach, signed_up_user, db_session, welcome_emails
) -> None:
    coach, coach_headers = signed_up_coach
    _add(client, coach_headers, "member@example.com", "Member Person")
    admin_headers = _platform_admin(client, signed_up_user, db_session)

    # Both coaches' names/emails match this search, but it is still one organization.
    orgs = _org_id(client, admin_headers, coach["email"])
    assert len(orgs) == 1
    assert orgs[0]["member_count"] == 2
    by_member = _org_id(client, admin_headers, "member@example.com")
    assert [o["id"] for o in by_member] == [orgs[0]["id"]]


def test_platform_admin_can_manage_an_orgs_team_and_it_is_audited(
    client, signed_up_coach, signed_up_user, db_session, welcome_emails
) -> None:
    coach, _ = signed_up_coach
    admin_headers = _platform_admin(client, signed_up_user, db_session)
    org_id = _org_id(client, admin_headers, coach["email"])[0]["id"]

    team = client.get(f"/api/v1/admin/organizations/{org_id}/team", headers=admin_headers)
    assert team.status_code == 200
    assert len(team.json()["members"]) == 1

    added = client.post(
        f"/api/v1/admin/organizations/{org_id}/team/members",
        headers=admin_headers,
        json={
            "email": "added.by.support@example.com",
            "display_name": "Added",
            "org_role": "admin",
        },
    )
    assert added.status_code == 201, added.text
    members = {m["email"]: m for m in added.json()["members"]}
    assert members["added.by.support@example.com"]["org_role"] == "admin"
    assert [e["to"] for e in welcome_emails] == ["added.by.support@example.com"]

    coach_id = members["added.by.support@example.com"]["coach_id"]
    patched = client.patch(
        f"/api/v1/admin/organizations/{org_id}/team/members/{coach_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert patched.status_code == 200
    actions = {row.action for row in db_session.query(AdminAuditLog).all()}
    assert {"add_org_member", "update_org_member"} <= actions


def test_removing_coach_status_is_refused_while_the_org_has_other_coaches(
    client, signed_up_coach, signed_up_user, db_session, welcome_emails
) -> None:
    coach, coach_headers = signed_up_coach
    _add(client, coach_headers, "member@example.com")
    admin_headers = _platform_admin(client, signed_up_user, db_session)
    coach_user = db_session.query(User).filter_by(email=coach["email"]).one()

    resp = client.post(
        f"/api/v1/admin/users/{coach_user.id}/set-coach",
        headers=admin_headers,
        json={"is_coach": False},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "org_has_team"


# ---- renaming an organization ----


def test_org_admin_can_rename_their_organization(client, signed_up_coach, welcome_emails) -> None:
    _coach, admin_headers = signed_up_coach
    resp = client.patch(
        "/api/v1/coach/team/organization", headers=admin_headers, json={"name": "  Harbor Clinic "}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["organization_name"] == "Harbor Clinic"
    # Reflected everywhere the studio name is shown.
    assert client.get("/api/v1/coach/profile", headers=admin_headers).json()["studio_name"] == (
        "Harbor Clinic"
    )


def test_a_member_cannot_rename_the_organization(client, signed_up_coach, welcome_emails) -> None:
    _coach, admin_headers = signed_up_coach
    _add(client, admin_headers, "member@example.com")
    member_headers = _login_as_new_member(client, welcome_emails, "member@example.com")
    resp = client.patch(
        "/api/v1/coach/team/organization", headers=member_headers, json={"name": "Mine now"}
    )
    assert resp.status_code == 403


def test_a_blank_organization_name_is_rejected(client, signed_up_coach) -> None:
    _coach, admin_headers = signed_up_coach
    resp = client.patch("/api/v1/coach/team/organization", headers=admin_headers, json={"name": ""})
    assert resp.status_code == 422


def test_platform_admin_can_rename_an_organization_and_it_is_audited(
    client, signed_up_coach, signed_up_user, db_session
) -> None:
    coach, _ = signed_up_coach
    admin_headers = _platform_admin(client, signed_up_user, db_session)
    org_id = _org_id(client, admin_headers, coach["email"])[0]["id"]

    resp = client.patch(
        f"/api/v1/admin/organizations/{org_id}", headers=admin_headers, json={"name": "Renamed"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Renamed"
    entries = [
        e
        for e in db_session.query(AdminAuditLog).filter_by(action="rename_organization")
        if e.details["organization_id"] == org_id
    ]
    assert [e.details["to"] for e in entries] == ["Renamed"]


# ---- adding an existing account to a team ----


@pytest.fixture()
def added_emails(monkeypatch):
    sent: list[tuple] = []
    monkeypatch.setattr(
        "app.routers.admin.send_team_added_email",
        lambda to, name, org, role: sent.append((to, name, org, role)),
    )
    return sent


def _existing_url(org_id):
    return f"/api/v1/admin/organizations/{org_id}/team/members/existing"


def test_platform_admin_can_add_an_existing_vrotege_as_a_coach(
    client, signed_up_coach, signed_up_user, db_session, added_emails
) -> None:
    coach, _ = signed_up_coach
    admin_headers = _platform_admin(client, signed_up_user, db_session)
    org_id = _org_id(client, admin_headers, coach["email"])[0]["id"]

    # A separate, ordinary Vrotégé account.
    singer_email = "existing.singer@example.com"
    signup = client.post(
        "/api/v1/auth/signup", json={"email": singer_email, "password": "correcthorse123"}
    )
    assert signup.status_code == 201
    singer_headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}

    resp = client.post(
        _existing_url(org_id),
        headers=admin_headers,
        json={"email": singer_email, "display_name": "Sam Singer", "org_role": "member"},
    )
    assert resp.status_code == 201, resp.text
    member = next(m for m in resp.json()["members"] if m["email"] == singer_email)
    assert member["org_role"] == "member"
    assert member["also_singer"] is False  # no UserProfile yet in this test account
    assert added_emails == [(singer_email, "Sam Singer", "Test Studio", "member")]

    # Same login, now also a coach in that organization -- no new password involved.
    team = client.get("/api/v1/coach/team", headers=singer_headers)
    assert team.status_code == 200, team.text
    assert team.json()["my_role"] == "member"
    assert {m["email"] for m in team.json()["members"]} >= {coach["email"], singer_email}
    logged = [
        e
        for e in db_session.query(AdminAuditLog).filter_by(action="add_existing_org_member")
        if e.details["email"] == singer_email
    ]
    assert len(logged) == 1


def test_an_existing_account_with_a_vrotege_profile_is_flagged_also_singer(
    client, signed_up_coach, signed_up_user, db_session, added_emails
) -> None:
    from app.models import UserProfile

    coach, _ = signed_up_coach
    singer, _ = signed_up_user
    singer_row = db_session.query(User).filter_by(email=singer["email"]).one()
    db_session.add(UserProfile(user_id=singer_row.id))
    db_session.commit()

    # A platform admin account is needed too; make the coach's own user one.
    admin_user = db_session.query(User).filter_by(email=coach["email"]).one()
    admin_user.is_admin = True
    db_session.commit()
    admin_headers = {"Authorization": f"Bearer {coach['access_token']}"}
    org_id = _org_id(client, admin_headers, coach["email"])[0]["id"]

    resp = client.post(
        _existing_url(org_id),
        headers=admin_headers,
        json={"email": singer["email"], "display_name": "Dual Role"},
    )
    assert resp.status_code == 201, resp.text
    member = next(m for m in resp.json()["members"] if m["email"] == singer["email"])
    assert member["also_singer"] is True


def test_existing_account_attach_refuses_coaches_unknown_and_deactivated(
    client, signed_up_coach, signed_up_user, db_session, added_emails
) -> None:
    coach, _ = signed_up_coach
    admin_headers = _platform_admin(client, signed_up_user, db_session)
    org_id = _org_id(client, admin_headers, coach["email"])[0]["id"]

    def attempt(email):
        return client.post(
            _existing_url(org_id),
            headers=admin_headers,
            json={"email": email, "display_name": "X"},
        )

    already = attempt(coach["email"])
    assert already.status_code == 409
    assert already.json()["error"]["code"] == "already_a_coach"

    unknown = attempt("nobody.here@example.com")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "account_not_found"

    gone = client.post(
        "/api/v1/auth/signup", json={"email": "gone@example.com", "password": "correcthorse123"}
    )
    assert gone.status_code == 201
    db_session.query(User).filter_by(email="gone@example.com").one().is_active = False
    db_session.commit()
    deactivated = attempt("gone@example.com")
    assert deactivated.status_code == 409
    assert deactivated.json()["error"]["code"] == "account_deactivated"
    assert added_emails == []


def test_org_admins_cannot_attach_existing_accounts_themselves(
    client, signed_up_coach, signed_up_user
) -> None:
    """Only a platform admin can; an org admin adding someone else's existing account is the
    thing the privacy rules rule out."""
    coach, admin_headers = signed_up_coach
    singer, _ = signed_up_user
    team = _team(client, admin_headers)
    resp = client.post(
        f"/api/v1/admin/organizations/{team['organization_id']}/team/members/existing",
        headers=admin_headers,
        json={"email": singer["email"], "display_name": "X"},
    )
    assert resp.status_code == 403
