"""Stage 6 simulated-user test plan, driven through the real check-in/routine/session
endpoints (not the pure functions unit-tested in tests/unit/test_exercise_routine.py).

Confirms the product brief's explicit acceptance criteria: the recommendation engine behaves
correctly for a healthy baseline, a fatigued user, range reduction, high discomfort, poor
sleep, heavy rehearsal yesterday, and several rest days — and that dangerous combinations
(e.g. heavy load stacked with high fatigue) are prevented.
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.exercise_library import CATEGORY_INTENSITY
from app.models import ExerciseSession
from tests.integration.test_baseline import upload_tone
from tests.integration.test_recovery_score import TODAY, post_checkin


def get_routine(client, headers, length_minutes=10, for_date=TODAY):
    resp = client.get(
        "/api/v1/routine",
        headers=headers,
        params={"length_minutes": length_minutes, "date": for_date},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_library_is_seeded_and_excludes_no_categories(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.get("/api/v1/exercises", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) > 0
    categories = {e["category"] for e in body}
    assert categories == set(CATEGORY_INTENSITY)


def test_healthy_baseline_gets_full_intensity_routine(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers)

    body = get_routine(client, headers)
    assert body["intensity_cap"] == "high"
    assert body["safety_message"] is None
    assert len(body["items"]) > 0


def test_fatigued_user_gets_moderate_routine(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers, {"fatigue": 9, "rehearsal_or_performance_yesterday": False})

    body = get_routine(client, headers)
    assert body["intensity_cap"] in ("low", "moderate")
    for item in body["items"]:
        assert CATEGORY_INTENSITY[item["category"]] != "high"


def test_range_reduction_baseline_deviation_avoids_high_intensity(client, signed_up_user) -> None:
    """"Range reduction" from the test plan -- a today's-recording measurement that looks
    notably different from the user's established baseline -- must not receive a demanding
    routine that pushes further into range/pitch-glide territory."""
    _user, headers = signed_up_user
    for _ in range(6):
        upload_tone(client, headers, 220.0)
    post_checkin(client, headers)
    # An outlier recording today -> Stage 5's acoustic/consistency components read low.
    upload_tone(client, headers, 320.0)

    body = get_routine(client, headers)
    categories = {item["category"] for item in body["items"]}
    assert "Range exploration" not in categories
    assert "Pitch glides" not in categories


def test_high_discomfort_triggers_safety_guidance_never_push_through(
    client, signed_up_user
) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers, {"throat_discomfort": 9})

    body = get_routine(client, headers)
    assert body["intensity_cap"] == "low"
    assert body["safety_message"] is not None
    for item in body["items"]:
        assert CATEGORY_INTENSITY[item["category"]] == "low"


def test_poor_sleep_avoids_high_intensity(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers, {"sleep_hours": 2.5})

    body = get_routine(client, headers)
    assert body["intensity_cap"] != "high"


def test_heavy_rehearsal_yesterday_dangerous_combination_prevented(client, signed_up_user) -> None:
    """The explicit "dangerous combination" scenario: heavy load yesterday stacked with high
    fatigue must cap at low, not just moderate."""
    _user, headers = signed_up_user
    post_checkin(
        client,
        headers,
        {
            "rehearsal_or_performance_yesterday": True,
            "singing_load": "high",
            "fatigue": 8,
        },
    )

    body = get_routine(client, headers)
    assert body["intensity_cap"] == "low"
    for item in body["items"]:
        assert CATEGORY_INTENSITY[item["category"]] == "low"


def test_several_rest_days_eases_back_in(client, signed_up_user, db_session) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers)

    session_id = client.post(
        "/api/v1/exercise-sessions", headers=headers, json={"routine_length_minutes": 10}
    ).json()["id"]
    db_session.query(ExerciseSession).filter(ExerciseSession.id == session_id).update(
        {"completed_at": datetime.now(UTC) - timedelta(days=9)}
    )
    db_session.commit()

    body = get_routine(client, headers)
    assert body["intensity_cap"] != "high"


def test_full_session_lifecycle(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers)
    routine = get_routine(client, headers)

    session_resp = client.post(
        "/api/v1/exercise-sessions", headers=headers, json={"routine_length_minutes": 10}
    )
    assert session_resp.status_code == 201
    session_id = session_resp.json()["id"]

    for i, item in enumerate(routine["items"]):
        result_resp = client.post(
            f"/api/v1/exercise-sessions/{session_id}/results",
            headers=headers,
            data={
                "exercise_id": item["id"],
                "order_index": i,
                "completed": True,
                "self_reported_difficulty": 4,
            },
        )
        assert result_resp.status_code == 201, result_resp.text

    complete_resp = client.patch(
        f"/api/v1/exercise-sessions/{session_id}/complete", headers=headers
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["completed_at"] is not None

    get_resp = client.get(f"/api/v1/exercise-sessions/{session_id}", headers=headers)
    assert get_resp.status_code == 200
    assert len(get_resp.json()["results"]) == len(routine["items"])


def test_rejects_invalid_length_minutes(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.get(
        "/api/v1/routine", headers=headers, params={"length_minutes": 7, "date": TODAY}
    )
    assert resp.status_code == 422


def test_user_cannot_log_results_on_another_users_session(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    session_id = client.post(
        "/api/v1/exercise-sessions", headers=headers, json={"routine_length_minutes": 5}
    ).json()["id"]

    import uuid

    other_email = f"other_{uuid.uuid4().hex[:12]}@example.com"
    other_signup = client.post(
        "/api/v1/auth/signup", json={"email": other_email, "password": "correcthorse123"}
    )
    other_headers = {"Authorization": f"Bearer {other_signup.json()['access_token']}"}

    resp = client.get(f"/api/v1/exercise-sessions/{session_id}", headers=other_headers)
    assert resp.status_code == 404


@pytest.mark.parametrize("length_minutes", [5, 10, 15, 20])
def test_all_valid_routine_lengths_work(client, signed_up_user, length_minutes) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers)
    body = get_routine(client, headers, length_minutes=length_minutes)
    assert len(body["items"]) > 0
    assert body["total_duration_seconds"] <= length_minutes * 60


def test_severe_discomfort_recommends_rest_day_but_still_returns_a_routine(
    client, signed_up_user
) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers, {"throat_discomfort": 9})

    body = get_routine(client, headers)
    assert body["rest_day_recommended"] is True
    assert body["rest_day_reason"] is not None
    assert len(body["items"]) > 0  # a strong recommendation, never a block


def test_moderate_discomfort_does_not_recommend_rest_day(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers, {"throat_discomfort": 6})

    body = get_routine(client, headers)
    assert body["rest_day_recommended"] is False
    assert body["rest_day_reason"] is None


def test_three_consecutive_red_days_recommends_rest_day(client, signed_up_user) -> None:
    """Isolates the consecutive-red-days trigger from the direct severe-discomfort one:
    discomfort=7 already forces a red recovery status (DISCOMFORT_SAFETY_THRESHOLD in
    app/recovery_score.py) but is below the rest-day discomfort threshold of 9."""
    _user, headers = signed_up_user
    today = date.fromisoformat(TODAY)
    for days_ago in (2, 1, 0):
        day = (today - timedelta(days=days_ago)).isoformat()
        post_checkin(client, headers, {"checkin_date": day, "throat_discomfort": 7})
        # Triggers compute_and_store_recovery_score for that date so it's a real stored row —
        # fetch_score_history (which the rest-day check reads) never backfills.
        resp = client.get("/api/v1/recovery-score", headers=headers, params={"date": day})
        assert resp.status_code == 200
        assert resp.json()["status"] == "red"

    body = get_routine(client, headers)
    assert body["rest_day_recommended"] is True
    assert "red" in body["rest_day_reason"].lower()


def test_rest_check_endpoint_matches_routine(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers, {"throat_discomfort": 9})

    routine = get_routine(client, headers)
    rest_check = client.get(
        "/api/v1/routine/rest-check", headers=headers, params={"date": TODAY}
    )
    assert rest_check.status_code == 200
    assert rest_check.json()["rest_day_recommended"] == routine["rest_day_recommended"]
    assert rest_check.json()["rest_day_reason"] == routine["rest_day_reason"]
