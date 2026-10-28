"""Organization reporting for admins: per-coach activity and practice as counts only. The
Vrotégé-derived figures cover only Vrotégés who share their exercise history with that coach, and
stay hidden until a coach has at least MIN_GROUP_SIZE of them."""

import uuid
from datetime import UTC, datetime, timedelta

from app.models import ExerciseSession
from app.org_report import MIN_GROUP_SIZE
from tests.integration.test_coach_assignments import _connect
from tests.integration.test_org_teams import _add, _login_as_new_member

REPORT = "/api/v1/coach/team/report"


def _new_singer(client):
    email = f"rep_{uuid.uuid4().hex[:12]}@example.com"
    resp = client.post("/api/v1/auth/signup", json={"email": email, "password": "correcthorse123"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return email, body["user"]["id"], {"Authorization": f"Bearer {body['access_token']}"}


def _practice(db_session, user_id, *, days_ago, completed=True):
    when = datetime.now(UTC) - timedelta(days=days_ago)
    db_session.add(
        ExerciseSession(
            user_id=user_id,
            routine_length_minutes=10,
            started_at=when,
            completed_at=when if completed else None,
        )
    )
    db_session.flush()


def _report(client, headers, days=30):
    resp = client.get(REPORT, headers=headers, params={"days": days})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(report, name):
    return next(c for c in report["coaches"] if c["display_name"] == name)


def _connect_singers(client, coach_headers, count, categories):
    ids = []
    for _ in range(count):
        email, user_id, headers = _new_singer(client)
        _connect(client, coach_headers, email, headers, categories)
        ids.append(user_id)
    return ids


def test_report_counts_a_coachs_own_work_and_one_sharing_vrotege(
    client, db_session, signed_up_coach, signed_up_user
) -> None:
    coach, headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, headers, singer["email"], singer_headers, ["exercise_history"])
    singer_id = singer["user"]["id"]
    _practice(db_session, uuid.UUID(singer_id), days_ago=1)

    client.post(
        f"/api/v1/coach/singers/{singer_id}/notes", headers=headers, json={"body": "Nice work."}
    )

    report = _report(client, headers)
    name = client.get("/api/v1/coach/profile", headers=headers).json()["display_name"]
    row = _row(report, name)
    assert report["min_group_size"] == MIN_GROUP_SIZE
    assert row["connected_vroteges"] == 1
    assert row["invites_sent"] == 1
    assert row["notes_written"] == 1
    assert row["sharing_vroteges"] == 1
    # There is no minimum group size: one sharing Vrotégé's practice is counted.
    assert row["practice_sessions"] == 1
    assert row["practicing_vroteges"] == 1
    assert report["totals"]["practice_sessions"] == 1


def test_report_sums_practice_across_sharing_vroteges_within_the_window(
    client, db_session, signed_up_coach
) -> None:
    _coach, headers = signed_up_coach
    singer_ids = _connect_singers(client, headers, 3, ["exercise_history"])
    _practice(db_session, uuid.UUID(singer_ids[0]), days_ago=1)
    _practice(db_session, uuid.UUID(singer_ids[0]), days_ago=2)
    _practice(db_session, uuid.UUID(singer_ids[1]), days_ago=3)
    _practice(db_session, uuid.UUID(singer_ids[1]), days_ago=3, completed=False)  # not finished
    _practice(db_session, uuid.UUID(singer_ids[2]), days_ago=60)  # outside the 30-day window

    report = _report(client, headers, 30)
    row = report["coaches"][0]
    assert row["sharing_vroteges"] == 3
    assert row["practice_sessions"] == 3
    assert row["practicing_vroteges"] == 2
    assert report["totals"]["practice_sessions"] == 3
    assert report["totals"]["practicing_vroteges"] == 2

    # A longer window picks up the older session.
    longer = _report(client, headers, 90)["coaches"][0]
    assert longer["practice_sessions"] == 4
    assert longer["practicing_vroteges"] == 3


def test_vroteges_who_do_not_share_exercise_history_are_not_counted(
    client, db_session, signed_up_coach
) -> None:
    _coach, headers = signed_up_coach
    shared = _connect_singers(client, headers, 2, ["exercise_history"])
    private = _connect_singers(client, headers, 1, ["recovery_trends"])
    for user_id in shared + private:
        _practice(db_session, uuid.UUID(user_id), days_ago=1)

    row = _report(client, headers)["coaches"][0]
    assert row["connected_vroteges"] == 3
    # Three are connected but only two share exercise history, so only theirs are counted.
    assert row["sharing_vroteges"] == 2
    assert row["practice_sessions"] == 2
    assert row["practicing_vroteges"] == 2


def test_a_coach_nobody_shares_with_is_hidden_and_left_out_of_the_totals(
    client, db_session, signed_up_coach, welcome_emails
) -> None:
    _coach, admin_headers = signed_up_coach
    _add(client, admin_headers, "member@example.com", "Member Coach")
    member_headers = _login_as_new_member(client, welcome_emails, "member@example.com")

    sharing = _connect_singers(client, admin_headers, 2, ["exercise_history"])
    private = _connect_singers(client, member_headers, 1, ["recovery_trends"])
    for user_id in sharing:
        _practice(db_session, uuid.UUID(user_id), days_ago=1)
    for _ in range(5):
        _practice(db_session, uuid.UUID(private[0]), days_ago=1)  # never shared

    report = _report(client, admin_headers)
    member = _row(report, "Member Coach")
    assert member["connected_vroteges"] == 1
    assert member["sharing_vroteges"] == 0
    assert member["practice_sessions"] is None
    assert member["practicing_vroteges"] is None
    # The total covers only the coach whose practice is shown, and never the unshared sessions.
    assert report["totals"]["practice_sessions"] == 2


def test_report_is_admin_only_and_validates_the_period(
    client, signed_up_coach, signed_up_user, welcome_emails
) -> None:
    _coach, admin_headers = signed_up_coach
    _add(client, admin_headers, "member@example.com")
    member_headers = _login_as_new_member(client, welcome_emails, "member@example.com")

    denied = client.get(REPORT, headers=member_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "org_admin_required"
    assert client.get(REPORT, headers=signed_up_user[1]).status_code == 403
    assert client.get(REPORT).status_code in (401, 403)

    bad = client.get(REPORT, headers=admin_headers, params={"days": 5})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "invalid_period"


def test_report_never_names_a_vrotege(client, db_session, signed_up_coach) -> None:
    _coach, headers = signed_up_coach
    ids = _connect_singers(client, headers, MIN_GROUP_SIZE, ["exercise_history"])
    _practice(db_session, uuid.UUID(ids[0]), days_ago=1)
    raw = client.get(REPORT, headers=headers).text
    assert "rep_" not in raw
    for user_id in ids:
        assert user_id not in raw
