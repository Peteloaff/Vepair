"""Standalone, on-demand Warm Up / Cool Down routines, driven through the real endpoints --
GET /api/v1/quick-routine and the session-creation/completion flow with session_type set."""

from tests.integration.test_recovery_score import TODAY, post_checkin


def get_quick_routine(client, headers, kind, for_date=TODAY):
    resp = client.get(
        "/api/v1/quick-routine", headers=headers, params={"kind": kind, "date": for_date}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_warm_up_pulls_breathing_humming_sovt(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers)

    body = get_quick_routine(client, headers, "warm_up")
    assert [item["category"] for item in body["items"]] == [
        "Breathing",
        "Gentle humming",
        "SOVT",
    ]
    assert body["kind"] == "warm_up"
    assert body["total_duration_seconds"] == sum(
        i["duration_seconds"] for i in body["items"]
    )


def test_cool_down_pulls_only_vocal_cooldown(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers)

    body = get_quick_routine(client, headers, "cool_down")
    assert [item["category"] for item in body["items"]] == ["Vocal cooldown"]
    assert body["kind"] == "cool_down"


def test_quick_routine_has_no_adaptive_only_fields(client, signed_up_user) -> None:
    """QuickRoutineOut is deliberately its own shape -- no length_minutes, assigned exercise
    ids, tone targets, or rest-day fields, unlike RoutineOut."""
    _user, headers = signed_up_user
    post_checkin(client, headers)

    body = get_quick_routine(client, headers, "warm_up")
    for field in (
        "length_minutes",
        "assigned_exercise_ids",
        "rest_day_recommended",
        "rest_day_reason",
        "exercise_tone_targets",
    ):
        assert field not in body


def test_high_discomfort_still_shrinks_a_quick_routine(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers, {"throat_discomfort": 8})

    body = get_quick_routine(client, headers, "warm_up")
    assert body["intensity_cap"] == "low"
    assert body["safety_message"] is not None
    assert len(body["items"]) == 3  # still a valid routine, not empty


def test_invalid_kind_is_rejected(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.get(
        "/api/v1/quick-routine", headers=headers, params={"kind": "not_a_kind", "date": TODAY}
    )
    assert resp.status_code == 422


def test_quick_routine_requires_auth(client) -> None:
    resp = client.get("/api/v1/quick-routine", params={"kind": "warm_up", "date": TODAY})
    assert resp.status_code == 401


class TestSessionTracking:
    def test_session_defaults_to_adaptive_type(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        resp = client.post(
            "/api/v1/exercise-sessions", headers=headers, json={"routine_length_minutes": 10}
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["routine_length_minutes"] == 10

    def test_warm_up_session_can_be_created_and_completed(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        created = client.post(
            "/api/v1/exercise-sessions", headers=headers, json={"session_type": "warm_up"}
        )
        assert created.status_code == 201, created.text
        assert created.json()["routine_length_minutes"] is None

        session_id = created.json()["id"]
        completed = client.patch(
            f"/api/v1/exercise-sessions/{session_id}/complete", headers=headers
        )
        assert completed.status_code == 200
        assert completed.json()["completed_at"] is not None

    def test_completed_warm_up_session_counts_toward_training_consistency(
        self, client, signed_up_user
    ) -> None:
        """No special-casing needed -- build_training_consistency only checks completed_at,
        not session_type, so a warm-up counts as real practice the same as any other session."""
        _user, headers = signed_up_user
        created = client.post(
            "/api/v1/exercise-sessions", headers=headers, json={"session_type": "warm_up"}
        )
        session_id = created.json()["id"]
        client.patch(f"/api/v1/exercise-sessions/{session_id}/complete", headers=headers)

        resp = client.get(
            "/api/v1/training-consistency",
            headers=headers,
            params={"from_date": TODAY, "to_date": TODAY, "as_of": TODAY},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["current_streak_days"] >= 1
