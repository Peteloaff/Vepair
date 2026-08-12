"""Stage 12 Phase II training assignment — end-to-end through the real API. Unit-level safety
guarantees live in tests/unit/test_exercise_routine.py's TestCoachAssignment; these tests cover
the assignment CRUD lifecycle and its integration into a real routine request."""

from datetime import date

TODAY = date.today().isoformat()


def _connect(client, coach_headers, singer_email, singer_headers, categories) -> str:
    created = client.post(
        "/api/v1/coach/invites", headers=coach_headers, json={"singer_email": singer_email}
    )
    invite_id = created.json()["id"]
    accepted = client.post(
        f"/api/v1/invites/{invite_id}/accept",
        headers=singer_headers,
        json={"granted_categories": categories},
    )
    assert accepted.status_code == 200, accepted.text
    return accepted.json()["id"]


def _low_intensity_exercise_id(client, headers) -> str:
    exercises = client.get("/api/v1/exercises", headers=headers).json()
    low = next(e for e in exercises if e["category"] == "Breathing")
    return low["id"]


def test_routine_reflects_a_coach_assignment_end_to_end(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["exercise_history"])

    exercise_id = _low_intensity_exercise_id(client, singer_headers)
    assign = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/assignments",
        headers=coach_headers,
        json={"exercise_ids": [exercise_id], "note_to_singer": "Focus on breath support today"},
    )
    assert assign.status_code == 201, assign.text
    assert assign.json()["status"] == "active"

    routine = client.get(
        "/api/v1/routine",
        headers=singer_headers,
        params={"length_minutes": 20, "date": TODAY},
    )
    assert routine.status_code == 200
    assert exercise_id in routine.json()["assigned_exercise_ids"]
    assert any(item["id"] == exercise_id for item in routine.json()["items"])
    assert any("assigned specific exercises" in r for r in routine.json()["reasons"])


def test_revoked_access_stops_the_assignment_from_influencing_the_routine(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["exercise_history"]
    )

    exercise_id = _low_intensity_exercise_id(client, singer_headers)
    client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/assignments",
        headers=coach_headers,
        json={"exercise_ids": [exercise_id]},
    )

    client.delete(f"/api/v1/coach-connections/{access_id}", headers=singer_headers)

    routine = client.get(
        "/api/v1/routine",
        headers=singer_headers,
        params={"length_minutes": 20, "date": TODAY},
    )
    assert routine.status_code == 200
    assert routine.json()["assigned_exercise_ids"] == []


def test_new_assignment_supersedes_not_deletes_the_previous_one(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["exercise_history"])

    exercise_id = _low_intensity_exercise_id(client, singer_headers)
    first = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/assignments",
        headers=coach_headers,
        json={"exercise_ids": [exercise_id]},
    )
    second = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/assignments",
        headers=coach_headers,
        json={"exercise_ids": [exercise_id]},
    )
    assert second.status_code == 201

    history = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/assignments", headers=coach_headers
    )
    by_id = {a["id"]: a for a in history.json()}
    assert by_id[first.json()["id"]]["status"] == "superseded"
    assert by_id[second.json()["id"]]["status"] == "active"


def test_assignment_rejects_unknown_exercise_ids(client, signed_up_coach, signed_up_user) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["exercise_history"])

    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/assignments",
        headers=coach_headers,
        json={"exercise_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    assert resp.status_code == 422


def test_assignment_requires_active_access_not_just_a_coach_account(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    exercise_id = _low_intensity_exercise_id(client, singer_headers)

    resp = client.post(
        f"/api/v1/coach/singers/{singer['user']['id']}/assignments",
        headers=coach_headers,
        json={"exercise_ids": [exercise_id]},
    )
    assert resp.status_code == 403
