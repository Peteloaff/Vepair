"""GET /api/v1/assigned-exercises -- what a coach assigned, resolved for the singer's own
screens. Unlike the daily routine it always lists the assignment (so it can't "disappear" behind
a time budget), while still obeying today's safety cap."""

from tests.integration.test_coach_assignments import _connect, _low_intensity_exercise_id
from tests.integration.test_recovery_score import TODAY, post_checkin


def get_assigned(client, headers):
    resp = client.get("/api/v1/assigned-exercises", headers=headers, params={"date": TODAY})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _assign(client, coach_headers, singer, exercise_ids, **extra):
    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/assignments",
        headers=coach_headers,
        json={"exercise_ids": exercise_ids, **extra},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _exercise_id_in_category(client, headers, category) -> str:
    exercises = client.get("/api/v1/exercises", headers=headers).json()
    return next(e for e in exercises if e["category"] == category)["id"]


def test_no_assignment_returns_empty_shape(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers)

    body = get_assigned(client, headers)
    assert body["has_assignment"] is False
    assert body["items"] == []
    assert body["held_back"] == []
    assert body["coach_display_name"] is None


def test_lists_the_assignment_with_coach_note_and_tone_targets(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["exercise_history"])
    post_checkin(client, singer_headers)

    first = _low_intensity_exercise_id(client, singer_headers)
    second = _exercise_id_in_category(client, singer_headers, "Gentle humming")
    _assign(
        client,
        coach_headers,
        singer,
        [first, second],
        note_to_singer="Easy and steady today",
        exercise_tone_targets={second: "G3"},
    )

    body = get_assigned(client, singer_headers)
    assert body["has_assignment"] is True
    assert body["coach_display_name"]
    assert body["note_to_singer"] == "Easy and steady today"
    assert [i["id"] for i in body["items"]] == [first, second]  # the coach's order
    assert body["held_back"] == []
    assert body["exercise_tone_targets"] == {second: "G3"}
    assert body["total_duration_seconds"] == sum(i["duration_seconds"] for i in body["items"])


def test_today_safety_cap_holds_back_demanding_assigned_exercises(
    client, signed_up_coach, signed_up_user
) -> None:
    """A coach can assign a demanding exercise, but on a day with high reported throat
    discomfort it is listed as held back and is NOT in the runnable items."""
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["exercise_history"])

    gentle = _low_intensity_exercise_id(client, singer_headers)
    demanding = _exercise_id_in_category(client, singer_headers, "Range exploration")
    _assign(client, coach_headers, singer, [gentle, demanding])

    post_checkin(client, singer_headers, {"throat_discomfort": 9})

    body = get_assigned(client, singer_headers)
    assert [i["id"] for i in body["items"]] == [gentle]
    assert [i["id"] for i in body["held_back"]] == [demanding]
    assert body["intensity_cap"] == "low"
    assert body["safety_message"]


def test_revoked_access_hides_the_assignment(client, signed_up_coach, signed_up_user) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["exercise_history"]
    )
    post_checkin(client, singer_headers)
    _assign(client, coach_headers, singer, [_low_intensity_exercise_id(client, singer_headers)])
    client.delete(f"/api/v1/coach-connections/{access_id}", headers=singer_headers)

    assert get_assigned(client, singer_headers)["has_assignment"] is False


def test_an_assigned_session_type_is_accepted(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    created = client.post(
        "/api/v1/exercise-sessions", headers=headers, json={"session_type": "assigned"}
    )
    assert created.status_code == 201, created.text
