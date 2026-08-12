"""Stage 11 VepAIr Score history, driven through the real endpoint — confirms it's strictly
read-only over whatever's already stored, never backfilling or recomputing a past day."""

import uuid
from datetime import date, timedelta

from sqlalchemy import select

from app.models import RecoveryScore
from tests.integration.test_recovery_score import TODAY, post_checkin


def get_history(client, headers, from_date, to_date):
    resp = client.get(
        "/api/v1/recovery-score/history",
        headers=headers,
        params={"from_date": from_date, "to_date": to_date},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_no_scores_ever_returns_an_empty_list(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    body = get_history(client, headers, "2026-01-01", TODAY)
    assert body == []


def test_returns_only_days_that_actually_have_a_stored_score(
    client, db_session, signed_up_user
) -> None:
    user, headers = signed_up_user
    user_id = uuid.UUID(user["user"]["id"])
    today = date.today()

    db_session.add(
        RecoveryScore(
            user_id=user_id,
            score_date=today - timedelta(days=5),
            score_value=70,
            confidence_label="moderate",
            components={"status": "green"},
        )
    )
    db_session.add(
        RecoveryScore(
            user_id=user_id,
            score_date=today - timedelta(days=2),
            score_value=40,
            confidence_label="low",
            components={"status": "yellow"},
        )
    )
    db_session.commit()

    body = get_history(
        client, headers, (today - timedelta(days=10)).isoformat(), today.isoformat()
    )
    assert len(body) == 2
    assert body[0]["score_value"] == 70
    assert body[0]["status"] == "green"
    assert body[1]["score_value"] == 40
    assert body[1]["status"] == "yellow"
    # Ordered oldest-first, and the gap days in between simply aren't in the list.
    assert body[0]["score_date"] < body[1]["score_date"]


def test_never_recomputes_or_overwrites_an_existing_stored_day(
    client, db_session, signed_up_user
) -> None:
    """The core regression this endpoint must never introduce: viewing history must not change
    what a past day's score was. Checks the stored row directly rather than through
    GET /recovery-score, since *that* endpoint always recomputes-and-overwrites by design
    (Stage 5) — the thing under test here is specifically that /recovery-score/history does
    not."""
    user, headers = signed_up_user
    user_id = uuid.UUID(user["user"]["id"])
    yesterday = date.today() - timedelta(days=1)

    db_session.add(
        RecoveryScore(
            user_id=user_id,
            score_date=yesterday,
            score_value=88,
            confidence_label="high",
            components={"status": "green"},
        )
    )
    db_session.commit()

    # Give today wildly different data, then request history spanning both days.
    post_checkin(client, headers, {"fatigue": 9, "throat_discomfort": 8})
    get_history(client, headers, yesterday.isoformat(), TODAY)

    stored = db_session.scalar(
        select(RecoveryScore).where(
            RecoveryScore.user_id == user_id, RecoveryScore.score_date == yesterday
        )
    )
    assert stored.score_value == 88
    assert stored.components["status"] == "green"


def test_out_of_range_days_are_excluded(client, db_session, signed_up_user) -> None:
    user, headers = signed_up_user
    user_id = uuid.UUID(user["user"]["id"])
    today = date.today()
    db_session.add(
        RecoveryScore(
            user_id=user_id,
            score_date=today - timedelta(days=100),
            score_value=55,
            confidence_label="low",
            components={"status": "yellow"},
        )
    )
    db_session.commit()

    body = get_history(
        client, headers, (today - timedelta(days=10)).isoformat(), today.isoformat()
    )
    assert body == []
