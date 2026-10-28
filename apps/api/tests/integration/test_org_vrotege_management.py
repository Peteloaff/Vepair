"""Organization admins managing *who coaches whom* (invite for a coach, end a connection, move a
Vrotégé to another coach) and removing a coach from the team -- all without ever seeing a
Vrotégé's voice data, and without bypassing the Vrotégé's own acceptance."""

import pytest

from app.models import AdminAuditLog, CoachAccess, ConsentRecord, User
from tests.integration.test_coach_assignments import _connect
from tests.integration.test_org_teams import (
    _add,
    _login_as_new_member,
    _org_id,
    _platform_admin,
    _team,
)

TEAM = "/api/v1/coach/team"


@pytest.fixture()
def invite_emails(monkeypatch):
    """Captures coach-invite emails sent by the org-admin endpoints."""
    sent: list[tuple] = []
    monkeypatch.setattr(
        "app.routers.coach_team.send_coach_invite_email",
        lambda to, coach_name, studio, message, has_account: sent.append(
            (to, coach_name, has_account)
        ),
    )
    return sent


@pytest.fixture()
def added_emails(monkeypatch):
    sent: list[tuple] = []
    monkeypatch.setattr(
        "app.routers.coach_team.send_team_added_email",
        lambda to, name, org, role: sent.append((to, name, org, role)),
    )
    monkeypatch.setattr(
        "app.routers.admin.send_team_added_email",
        lambda to, name, org, role: sent.append((to, name, org, role)),
    )
    return sent


def _vroteges(client, headers):
    resp = client.get(f"{TEAM}/vroteges", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _setup(client, signed_up_coach, signed_up_user, welcome_emails):
    """An org with an admin and a member; the Vrotégé is connected to the *member*."""
    admin, admin_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    member = _add(client, admin_headers, "member@example.com", "Member Coach").json()
    member_headers = _login_as_new_member(client, welcome_emails, "member@example.com")
    access_id = _connect(
        client, member_headers, singer["email"], singer_headers, ["recovery_trends"]
    )
    return admin_headers, member, member_headers, singer, singer_headers, access_id


# ---- seeing who is connected ----


def test_org_admin_sees_who_is_connected_to_which_coach_but_no_voice_data(
    client, signed_up_coach, signed_up_user, welcome_emails
) -> None:
    admin_headers, member, _mh, singer, _sh, access_id = _setup(
        client, signed_up_coach, signed_up_user, welcome_emails
    )
    body = _vroteges(client, admin_headers)
    assert [c["access_id"] for c in body["connections"]] == [access_id]
    conn = body["connections"][0]
    assert conn["singer_email"] == singer["email"]
    assert conn["coach_id"] == member["coach_id"]
    assert conn["coach_name"] == "Member Coach"
    # An identifier and a date, nothing about their voice.
    assert set(conn) == {
        "access_id",
        "singer_label",
        "singer_email",
        "coach_id",
        "coach_name",
        "connected_since",
    }
    # ...and the admin still can't open that Vrotégé.
    summary = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary", headers=admin_headers
    )
    assert summary.status_code == 403


def test_a_member_cannot_manage_vrotege_connections(
    client, signed_up_coach, signed_up_user, welcome_emails
) -> None:
    _ah, _m, member_headers, _s, _sh, access_id = _setup(
        client, signed_up_coach, signed_up_user, welcome_emails
    )
    assert client.get(f"{TEAM}/vroteges", headers=member_headers).status_code == 403
    assert client.delete(f"{TEAM}/vroteges/{access_id}", headers=member_headers).status_code == 403


# ---- inviting on behalf of a coach ----


def test_org_admin_invites_a_vrotege_for_a_coach_and_the_vrotege_still_accepts(
    client, signed_up_coach, signed_up_user, welcome_emails, invite_emails
) -> None:
    admin, admin_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    member = _add(client, admin_headers, "member@example.com", "Member Coach").json()

    resp = client.post(
        f"{TEAM}/vroteges/invite",
        headers=admin_headers,
        json={"coach_id": member["coach_id"], "singer_email": singer["email"]},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["coach_name"] == "Member Coach"
    assert invite_emails == [(singer["email"], "Member Coach", True)]

    pending = _vroteges(client, admin_headers)["pending_invites"]
    assert [p["singer_email"] for p in pending] == [singer["email"]]

    # Nothing is connected until the Vrotégé accepts.
    assert _vroteges(client, admin_headers)["connections"] == []
    invites = client.get("/api/v1/invites", headers=singer_headers).json()
    assert len(invites) == 1
    accepted = client.post(
        f"/api/v1/invites/{invites[0]['id']}/accept",
        headers=singer_headers,
        json={"granted_categories": ["recovery_trends"]},
    )
    assert accepted.status_code == 200
    after = _vroteges(client, admin_headers)
    assert [c["coach_name"] for c in after["connections"]] == ["Member Coach"]
    assert after["pending_invites"] == []


def test_org_invite_counts_against_the_shared_quota_and_rejects_duplicates(
    client, signed_up_coach, db_session, welcome_emails, invite_emails
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.models import CoachProfile, Organization

    coach, admin_headers = signed_up_coach
    org = (
        db_session.query(Organization)
        .join(CoachProfile, CoachProfile.organization_id == Organization.id)
        .filter(CoachProfile.user_id == coach["user"]["id"])
        .one()
    )
    org.coach_pro_period_start = datetime.now(UTC) - timedelta(days=1)
    db_session.commit()
    me = _team(client, admin_headers)["members"][0]

    before = _team(client, admin_headers)["invites_used_this_period"]
    payload = {"coach_id": me["coach_id"], "singer_email": "newperson@example.com"}
    assert (
        client.post(f"{TEAM}/vroteges/invite", headers=admin_headers, json=payload).status_code
        == 201
    )
    assert _team(client, admin_headers)["invites_used_this_period"] == before + 1

    again = client.post(f"{TEAM}/vroteges/invite", headers=admin_headers, json=payload)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "invite_already_pending"


def test_org_admin_cannot_invite_for_a_deactivated_coach(
    client, signed_up_coach, welcome_emails, invite_emails
) -> None:
    _coach, admin_headers = signed_up_coach
    member = _add(client, admin_headers, "member@example.com").json()
    client.patch(
        f"{TEAM}/members/{member['coach_id']}", headers=admin_headers, json={"is_active": False}
    )

    deactivated = client.post(
        f"{TEAM}/vroteges/invite",
        headers=admin_headers,
        json={"coach_id": member["coach_id"], "singer_email": "x@example.com"},
    )
    assert deactivated.status_code == 409
    assert deactivated.json()["error"]["code"] == "coach_deactivated"
    assert invite_emails == []


def test_org_admin_can_cancel_a_pending_invite(
    client, signed_up_coach, welcome_emails, invite_emails
) -> None:
    _coach, admin_headers = signed_up_coach
    me = _team(client, admin_headers)["members"][0]
    client.post(
        f"{TEAM}/vroteges/invite",
        headers=admin_headers,
        json={"coach_id": me["coach_id"], "singer_email": "later@example.com"},
    )
    invite_id = _vroteges(client, admin_headers)["pending_invites"][0]["invite_id"]
    assert (
        client.delete(f"{TEAM}/vroteges/invites/{invite_id}", headers=admin_headers).status_code
        == 204
    )
    assert _vroteges(client, admin_headers)["pending_invites"] == []
    assert (
        client.delete(f"{TEAM}/vroteges/invites/{invite_id}", headers=admin_headers).status_code
        == 404
    )


# ---- ending and moving connections ----


def test_org_admin_ends_a_connection_and_the_coach_loses_access(
    client, signed_up_coach, signed_up_user, welcome_emails, db_session
) -> None:
    admin_headers, _m, member_headers, singer, singer_headers, access_id = _setup(
        client, signed_up_coach, signed_up_user, welcome_emails
    )
    assert client.delete(f"{TEAM}/vroteges/{access_id}", headers=admin_headers).status_code == 204

    assert _vroteges(client, admin_headers)["connections"] == []
    # The coach's next request is refused, exactly as if the Vrotégé had revoked.
    blocked = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary", headers=member_headers
    )
    assert blocked.status_code == 403
    row = db_session.query(CoachAccess).filter_by(id=access_id).one()
    assert (row.status, row.revoked_by) == ("revoked", "org_admin")
    # The consent ledger records the withdrawal.
    withdrawn = (
        db_session.query(ConsentRecord)
        .filter_by(consent_type="coach_sharing", granted=False, category="recovery_trends")
        .count()
    )
    assert withdrawn >= 1
    # The Vrotégé's own account is untouched.
    assert client.get("/api/v1/auth/me", headers=singer_headers).status_code == 200
    # And the Vrotégé sees the connection as revoked.
    connections = client.get("/api/v1/coach-connections", headers=singer_headers).json()
    assert [c["status"] for c in connections] == ["revoked"]


def test_org_admin_moves_a_vrotege_to_another_coach_who_must_be_accepted(
    client, signed_up_coach, signed_up_user, welcome_emails, invite_emails
) -> None:
    admin_headers, _m, member_headers, singer, singer_headers, access_id = _setup(
        client, signed_up_coach, signed_up_user, welcome_emails
    )
    admin_coach = next(m for m in _team(client, admin_headers)["members"] if m["is_me"])

    moved = client.post(
        f"{TEAM}/vroteges/{access_id}/move",
        headers=admin_headers,
        json={"coach_id": admin_coach["coach_id"]},
    )
    assert moved.status_code == 201, moved.text
    # The old coach is cut off at once; the new one sees nothing until the Vrotégé accepts.
    assert (
        client.get(
            f"/api/v1/coach/singers/{singer['user']['id']}/summary", headers=member_headers
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/coach/singers/{singer['user']['id']}/summary", headers=admin_headers
        ).status_code
        == 403
    )
    assert _vroteges(client, admin_headers)["connections"] == []
    assert [p["coach_name"] for p in _vroteges(client, admin_headers)["pending_invites"]] == [
        admin_coach["display_name"]
    ]
    assert invite_emails[-1][0] == singer["email"]

    invites = client.get("/api/v1/invites", headers=singer_headers).json()
    accepted = client.post(
        f"/api/v1/invites/{invites[0]['id']}/accept",
        headers=singer_headers,
        json={"granted_categories": ["recovery_trends"]},
    )
    assert accepted.status_code == 200, accepted.text
    after = _vroteges(client, admin_headers)["connections"]
    assert [c["coach_name"] for c in after] == [admin_coach["display_name"]]


def test_moving_to_the_same_coach_is_refused(
    client, signed_up_coach, signed_up_user, welcome_emails, invite_emails
) -> None:
    admin_headers, member, _mh, _s, _sh, access_id = _setup(
        client, signed_up_coach, signed_up_user, welcome_emails
    )
    resp = client.post(
        f"{TEAM}/vroteges/{access_id}/move",
        headers=admin_headers,
        json={"coach_id": member["coach_id"]},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "same_coach"
    # Nothing changed.
    assert len(_vroteges(client, admin_headers)["connections"]) == 1


def test_an_admin_cannot_touch_another_organizations_connections(
    client, signed_up_coach, signed_up_user, welcome_emails, db_session
) -> None:
    _ah, _m, _mh, _s, _sh, access_id = _setup(
        client, signed_up_coach, signed_up_user, welcome_emails
    )
    from app.models import CoachProfile, Organization

    other = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": "other.clinic@example.com",
            "password": "correcthorse123",
            "display_name": "Other",
            "studio_name": "Other Clinic",
        },
    ).json()
    org = (
        db_session.query(Organization)
        .join(CoachProfile, CoachProfile.organization_id == Organization.id)
        .filter(CoachProfile.user_id == other["user"]["id"])
        .one()
    )
    org.is_coach_pro_active = True
    db_session.commit()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    assert client.delete(f"{TEAM}/vroteges/{access_id}", headers=other_headers).status_code == 404
    assert _vroteges(client, other_headers)["connections"] == []


# ---- removing a coach from the team ----


def test_removing_a_coach_ends_their_connections_keeps_history_and_keeps_their_login(
    client, signed_up_coach, signed_up_user, welcome_emails, invite_emails
) -> None:
    admin_headers, member, member_headers, singer, singer_headers, access_id = _setup(
        client, signed_up_coach, signed_up_user, welcome_emails
    )
    # History the Vrotégé must keep: a note the coach wrote before being removed.
    note = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/notes",
        headers=member_headers,
        json={"body": "Lovely steady tone this week."},
    )
    assert note.status_code == 201, note.text
    # A pending invite from the same coach, which should be cancelled.
    client.post(
        "/api/v1/coach/invites",
        headers=member_headers,
        json={"singer_email": "waiting@example.com"},
    )

    resp = client.delete(f"{TEAM}/members/{member['coach_id']}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ended_connections": 1, "cancelled_invites": 1}

    # Off the team lists, and no longer a coach...
    assert [m["email"] for m in _team(client, admin_headers)["members"]] == [
        next(m["email"] for m in _team(client, admin_headers)["members"] if m["is_me"])
    ]
    assert client.get(f"{TEAM}", headers=member_headers).status_code == 403
    assert client.get("/api/v1/coach/profile", headers=member_headers).status_code == 403
    # ...but their login still works, as an ordinary account.
    assert client.get("/api/v1/auth/me", headers=member_headers).status_code == 200
    # The Vrotégé's connection ended, yet the note written about them is still theirs to read.
    notes = client.get(f"/api/v1/coach-connections/{access_id}/notes", headers=singer_headers)
    assert notes.status_code == 200
    assert [n["body"] for n in notes.json()] == ["Lovely steady tone this week."]
    assert _vroteges(client, admin_headers) == {"connections": [], "pending_invites": []}


def test_removal_guards_self_and_last_admin(
    client, signed_up_coach, welcome_emails, signed_up_user, db_session
) -> None:
    coach, admin_headers = signed_up_coach
    me = _team(client, admin_headers)["members"][0]

    own = client.delete(f"{TEAM}/members/{me['coach_id']}", headers=admin_headers)
    assert own.status_code == 409
    assert own.json()["error"]["code"] == "cannot_remove_self"

    # A platform admin can't strip an organization of its only admin either.
    platform_headers = _platform_admin(client, signed_up_user, db_session)
    org_id = _org_id(client, platform_headers, coach["email"])[0]["id"]
    last = client.delete(
        f"/api/v1/admin/organizations/{org_id}/team/members/{me['coach_id']}",
        headers=platform_headers,
    )
    assert last.status_code == 409
    assert last.json()["error"]["code"] == "last_admin"


def test_a_removed_coach_can_be_added_back_and_keeps_their_password(
    client, signed_up_coach, welcome_emails, added_emails
) -> None:
    _coach, admin_headers = signed_up_coach
    member = _add(client, admin_headers, "member@example.com", "Member Coach").json()
    member_headers = _login_as_new_member(client, welcome_emails, "member@example.com")
    client.delete(f"{TEAM}/members/{member['coach_id']}", headers=admin_headers)
    assert client.get(TEAM, headers=member_headers).status_code == 403
    sent_before = len(welcome_emails)

    back = _add(client, admin_headers, "member@example.com", "Member Coach (back)", role="admin")
    assert back.status_code == 201, back.text
    assert back.json()["org_role"] == "admin"
    assert back.json()["display_name"] == "Member Coach (back)"
    # No new set-your-password link: they already have a login and use it.
    assert len(welcome_emails) == sent_before
    assert added_emails == [("member@example.com", "Member Coach (back)", "Test Studio", "admin")]
    assert client.get(TEAM, headers=member_headers).status_code == 200
    assert len(_team(client, admin_headers)["members"]) == 2


def test_platform_admin_removal_is_audited_and_excluded_from_counts(
    client, signed_up_coach, signed_up_user, welcome_emails, db_session
) -> None:
    coach, admin_headers = signed_up_coach
    member = _add(client, admin_headers, "member@example.com").json()
    platform_headers = _platform_admin(client, signed_up_user, db_session)
    org_id = _org_id(client, platform_headers, coach["email"])[0]["id"]
    assert _org_id(client, platform_headers, coach["email"])[0]["member_count"] == 2

    resp = client.delete(
        f"/api/v1/admin/organizations/{org_id}/team/members/{member['coach_id']}",
        headers=platform_headers,
    )
    assert resp.status_code == 200, resp.text
    assert _org_id(client, platform_headers, coach["email"])[0]["member_count"] == 1
    entry = [
        e
        for e in db_session.query(AdminAuditLog).filter_by(action="remove_org_member")
        if e.details["organization_id"] == org_id
    ]
    assert len(entry) == 1 and entry[0].details["email"] == "member@example.com"
    # The removed coach's account still exists.
    assert db_session.query(User).filter_by(email="member@example.com").one().is_active is True
