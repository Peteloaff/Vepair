"""Stage 11 training consistency, driven through the real endpoint — not the pure
`compute_streaks` unit-tested in tests/unit/test_training_consistency.py."""

import uuid
from datetime import UTC, date, datetime, timedelta

from app.models import ExerciseSession


def get_consistency(client, headers, from_date, to_date, as_of):
    resp = client.get(
        "/api/v1/training-consistency",
        headers=headers,
        params={"from_date": from_date, "to_date": to_date, "as_of": as_of},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def add_completed_session(db_session, user_id, on_date: date) -> None:
    session = ExerciseSession(user_id=user_id, routine_length_minutes=10)
    db_session.add(session)
    db_session.flush()
    session.completed_at = datetime(on_date.year, on_date.month, on_date.day, 12, tzinfo=UTC)
    db_session.commit()


def test_no_sessions_ever(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    today = date.today()
    from_date = (today - timedelta(days=6)).isoformat()
    body = get_consistency(client, headers, from_date, today.isoformat(), today.isoformat())
    assert body["current_streak_days"] == 0
    assert body["longest_streak_days"] == 0
    assert body["total_sessions_in_range"] == 0
    assert all(d["sessions_completed"] == 0 for d in body["days"])
    assert len(body["days"]) == 7


def test_reflects_real_completed_sessions_and_streak(client, db_session, signed_up_user) -> None:
    user, headers = signed_up_user
    user_id = uuid.UUID(user["user"]["id"])
    today = date.today()

    for i in range(3):
        add_completed_session(db_session, user_id, today - timedelta(days=i))

    from_date = (today - timedelta(days=10)).isoformat()
    body = get_consistency(client, headers, from_date, today.isoformat(), today.isoformat())
    assert body["current_streak_days"] == 3
    assert body["longest_streak_days"] == 3
    assert body["total_sessions_in_range"] == 3
    today_entry = next(d for d in body["days"] if d["for_date"] == today.isoformat())
    assert today_entry["sessions_completed"] == 1


def test_streak_survives_outside_the_requested_display_range(
    client, db_session, signed_up_user
) -> None:
    """A streak that started before the requested window must still report its real length —
    never clipped to whatever range the chart happens to be showing."""
    user, headers = signed_up_user
    user_id = uuid.UUID(user["user"]["id"])
    today = date.today()

    for i in range(10):
        add_completed_session(db_session, user_id, today - timedelta(days=i))

    # Only ask for the last 3 days of the display grid.
    from_date = (today - timedelta(days=2)).isoformat()
    body = get_consistency(client, headers, from_date, today.isoformat(), today.isoformat())
    assert body["current_streak_days"] == 10
    assert body["longest_streak_days"] == 10
    assert len(body["days"]) == 3


def test_multiple_sessions_same_day_count_toward_total_but_streak_stays_one_day(
    client, db_session, signed_up_user
) -> None:
    user, headers = signed_up_user
    user_id = uuid.UUID(user["user"]["id"])
    today = date.today()

    add_completed_session(db_session, user_id, today)
    add_completed_session(db_session, user_id, today)

    body = get_consistency(client, headers, today.isoformat(), today.isoformat(), today.isoformat())
    assert body["current_streak_days"] == 1
    assert body["total_sessions_in_range"] == 2
    assert body["days"][0]["sessions_completed"] == 2


def test_incomplete_sessions_never_count(client, db_session, signed_up_user) -> None:
    user, headers = signed_up_user
    user_id = uuid.UUID(user["user"]["id"])
    today = date.today()
    db_session.add(ExerciseSession(user_id=user_id, routine_length_minutes=10))  # never completed
    db_session.commit()

    body = get_consistency(client, headers, today.isoformat(), today.isoformat(), today.isoformat())
    assert body["current_streak_days"] == 0
    assert body["total_sessions_in_range"] == 0
