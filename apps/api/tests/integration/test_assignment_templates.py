"""Coach assignment templates -- a coach's saved, reusable exercise set (private to that coach,
never tied to a singer). Covers the CRUD lifecycle and the ownership boundary between coaches."""

from datetime import UTC, datetime, timedelta


def _exercise_id(client, headers) -> str:
    exercises = client.get("/api/v1/exercises", headers=headers).json()
    return next(e for e in exercises if e["category"] == "Breathing")["id"]


def _second_coach(client, db_session) -> tuple[dict, dict]:
    import uuid

    from app.models import CoachProfile, Organization

    email = f"coach_{uuid.uuid4().hex[:12]}@example.com"
    resp = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": email,
            "password": "correcthorse123",
            "display_name": "Second Coach",
            "studio_name": "Second Studio",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    coach = db_session.query(CoachProfile).filter_by(user_id=body["user"]["id"]).one()
    org = db_session.query(Organization).filter_by(id=coach.organization_id).one()
    org.is_coach_pro_active = True
    org.coach_pro_period_start = datetime.now(UTC)
    org.coach_pro_period_end = datetime.now(UTC) + timedelta(days=365)
    db_session.commit()

    return body, headers


def test_create_and_list_template(client, signed_up_coach) -> None:
    _coach, coach_headers = signed_up_coach
    exercise_id = _exercise_id(client, coach_headers)

    created = client.post(
        "/api/v1/coach/assignment-templates",
        headers=coach_headers,
        json={
            "name": "Warmup routine",
            "exercise_ids": [exercise_id],
            "note_to_singer": "Start here every session",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "Warmup routine"
    assert created.json()["exercise_ids"] == [exercise_id]

    listed = client.get("/api/v1/coach/assignment-templates", headers=coach_headers)
    assert listed.status_code == 200
    assert [t["id"] for t in listed.json()] == [created.json()["id"]]


def test_create_template_rejects_unknown_exercise_ids(client, signed_up_coach) -> None:
    _coach, coach_headers = signed_up_coach

    resp = client.post(
        "/api/v1/coach/assignment-templates",
        headers=coach_headers,
        json={"name": "Bad template", "exercise_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    assert resp.status_code == 422


def test_create_template_validates_tone_target_subset(client, signed_up_coach) -> None:
    _coach, coach_headers = signed_up_coach
    exercises = client.get("/api/v1/exercises", headers=coach_headers).json()
    included_id = _exercise_id(client, coach_headers)
    other_id = next(e["id"] for e in exercises if e["id"] != included_id)

    resp = client.post(
        "/api/v1/coach/assignment-templates",
        headers=coach_headers,
        json={
            "name": "Bad targets",
            "exercise_ids": [included_id],
            "exercise_tone_targets": {other_id: "G4"},
        },
    )
    assert resp.status_code == 422


def test_rename_template(client, signed_up_coach) -> None:
    _coach, coach_headers = signed_up_coach
    exercise_id = _exercise_id(client, coach_headers)
    created = client.post(
        "/api/v1/coach/assignment-templates",
        headers=coach_headers,
        json={"name": "Original name", "exercise_ids": [exercise_id]},
    )

    renamed = client.patch(
        f"/api/v1/coach/assignment-templates/{created.json()['id']}",
        headers=coach_headers,
        json={"name": "New name"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "New name"


def test_delete_template(client, signed_up_coach) -> None:
    _coach, coach_headers = signed_up_coach
    exercise_id = _exercise_id(client, coach_headers)
    created = client.post(
        "/api/v1/coach/assignment-templates",
        headers=coach_headers,
        json={"name": "Delete me", "exercise_ids": [exercise_id]},
    )

    deleted = client.delete(
        f"/api/v1/coach/assignment-templates/{created.json()['id']}", headers=coach_headers
    )
    assert deleted.status_code == 204

    listed = client.get("/api/v1/coach/assignment-templates", headers=coach_headers)
    assert listed.json() == []


def test_template_is_private_to_the_owning_coach(client, signed_up_coach, db_session) -> None:
    """A second coach can neither see nor modify the first coach's template -- templates are
    scoped per-coach, same as CoachAssignment and coach-created Exercise rows (not shared within
    an Organization/studio)."""
    _coach, coach_headers = signed_up_coach
    exercise_id = _exercise_id(client, coach_headers)
    created = client.post(
        "/api/v1/coach/assignment-templates",
        headers=coach_headers,
        json={"name": "Private template", "exercise_ids": [exercise_id]},
    )
    template_id = created.json()["id"]

    _other_coach, other_headers = _second_coach(client, db_session)

    listed = client.get("/api/v1/coach/assignment-templates", headers=other_headers)
    assert listed.json() == []

    renamed = client.patch(
        f"/api/v1/coach/assignment-templates/{template_id}",
        headers=other_headers,
        json={"name": "Hijacked"},
    )
    assert renamed.status_code == 404

    deleted = client.delete(
        f"/api/v1/coach/assignment-templates/{template_id}", headers=other_headers
    )
    assert deleted.status_code == 404


def test_template_endpoints_require_a_coach_account(client, signed_up_user) -> None:
    _singer, singer_headers = signed_up_user

    resp = client.get("/api/v1/coach/assignment-templates", headers=singer_headers)
    assert resp.status_code == 403
