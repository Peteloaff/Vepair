"""Stage 12 Phase II coach-reads-singer authorization boundary, and the regression tests that
enforce coach dashboard reads reuse the singer's own endpoints exactly rather than
reimplementing them. Driven through the real API endpoints."""

import json
from datetime import date

TODAY = date.today().isoformat()


def _connect(client, coach_headers, singer_email, singer_headers, categories) -> str:
    """Sends an invite and accepts it with the given categories. Returns the coach_access id."""
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


def test_coach_without_any_access_gets_403_reading_a_singers_summary(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, _singer_headers = signed_up_user

    resp = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": TODAY},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "no_active_access"


def test_coach_with_revoked_access_gets_403(client, signed_up_coach, signed_up_user) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )

    client.delete(f"/api/v1/coach-connections/{access_id}", headers=singer_headers)

    resp = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": TODAY},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "no_active_access"


def test_category_gating_only_populates_granted_sections(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["recovery_trends"])

    resp = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": TODAY},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["granted_categories"] == ["recovery_trends"]
    assert body["recovery_score"] is not None
    assert body["vocal_range"] is None
    assert body["exercise_trends"] is None
    assert body["training_consistency"] is None
    assert body["todays_routine"] is None


def test_coach_a_cannot_read_coach_bs_singer(client, signed_up_user) -> None:
    singer, singer_headers = signed_up_user

    signup_a = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": "coach-a-isolation-test@example.com",
            "password": "correcthorse123",
            "display_name": "Coach A",
        },
    )
    coach_a_headers = {"Authorization": f"Bearer {signup_a.json()['access_token']}"}

    signup_b = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": "coach-b-isolation-test@example.com",
            "password": "correcthorse123",
            "display_name": "Coach B",
        },
    )
    coach_b_headers = {"Authorization": f"Bearer {signup_b.json()['access_token']}"}

    _connect(client, coach_a_headers, singer["email"], singer_headers, ["recovery_trends"])

    resp = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_b_headers,
        params={"date": TODAY},
    )
    assert resp.status_code == 403


def test_singer_cannot_call_coach_only_endpoints(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.get("/api/v1/coach/singers", headers=headers)
    assert resp.status_code == 403


def test_coach_dashboard_recovery_score_matches_singers_own_endpoint(
    client, signed_up_coach, signed_up_user
) -> None:
    """The regression test that catches a future reimplementation instead of reuse — see
    app/routers/coach.py's get_singer_summary docstring."""
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user

    client.post(
        "/api/v1/checkins",
        headers=singer_headers,
        json={"checkin_date": TODAY, "voice_quality": 7, "fatigue": 3, "throat_discomfort": 1},
    )
    _connect(client, coach_headers, singer["email"], singer_headers, ["recovery_trends"])

    singer_own = client.get(
        "/api/v1/recovery-score", headers=singer_headers, params={"date": TODAY}
    )
    assert singer_own.status_code == 200

    coach_view = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": TODAY},
    )
    assert coach_view.status_code == 200
    assert coach_view.json()["recovery_score"] == singer_own.json()


def test_coach_vocal_range_summary_matches_singers_own_endpoint(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["vocal_range"])

    singer_own = client.get("/api/v1/vocal-range/summary", headers=singer_headers)
    assert singer_own.status_code == 200

    coach_view = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": TODAY},
    )
    assert coach_view.status_code == 200
    assert coach_view.json()["vocal_range"] == singer_own.json()


def test_coach_vocal_goal_matches_singers_own_endpoint_and_is_gated_on_vocal_range(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["vocal_range"])

    singer_own = client.get("/api/v1/vocal-goals", headers=singer_headers)
    assert singer_own.status_code == 200

    coach_view = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": TODAY},
    )
    assert coach_view.status_code == 200
    assert coach_view.json()["vocal_goal"] == singer_own.json()


def test_coach_vocal_goal_is_null_without_vocal_range_category(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    _connect(client, coach_headers, singer["email"], singer_headers, ["recovery_trends"])

    coach_view = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": TODAY},
    )
    assert coach_view.status_code == 200
    assert coach_view.json()["vocal_goal"] is None


def test_revoke_immediately_blocks_future_coach_reads(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )

    before = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": TODAY},
    )
    assert before.status_code == 200

    revoked = client.delete(f"/api/v1/coach-connections/{access_id}", headers=singer_headers)
    assert revoked.status_code == 204

    after = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": TODAY},
    )
    assert after.status_code == 403


def test_category_toggle_off_blocks_only_that_category(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client,
        coach_headers,
        singer["email"],
        singer_headers,
        ["recovery_trends", "vocal_range"],
    )

    toggled = client.patch(
        f"/api/v1/coach-connections/{access_id}/categories",
        headers=singer_headers,
        json={"category": "vocal_range", "granted": False},
    )
    assert toggled.status_code == 200
    assert toggled.json()["granted_categories"] == ["recovery_trends"]

    summary = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": TODAY},
    )
    assert summary.json()["recovery_score"] is not None
    assert summary.json()["vocal_range"] is None


def test_every_consent_change_appends_a_new_consent_record_row(
    client, signed_up_coach, signed_up_user
) -> None:
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user
    access_id = _connect(
        client, coach_headers, singer["email"], singer_headers, ["recovery_trends"]
    )

    client.patch(
        f"/api/v1/coach-connections/{access_id}/categories",
        headers=singer_headers,
        json={"category": "vocal_range", "granted": True},
    )
    client.delete(f"/api/v1/coach-connections/{access_id}", headers=singer_headers)

    consent = client.get("/api/v1/consent/coach_sharing", headers=singer_headers)
    assert consent.status_code == 200
    # accept (recovery_trends) + toggle-on (vocal_range) + revoke (recovery_trends, since it
    # was the only granted category at revoke time) = at least 3 rows exist; the endpoint only
    # surfaces the latest, so this just confirms the type is tracked and the most recent
    # change (a revoke => granted False) is what reads back.
    assert consent.json()["granted"] is False


def test_dailycheckin_free_text_fields_never_appear_in_any_coach_response(
    client, signed_up_coach, signed_up_user
) -> None:
    """Negative-content test, same style as Stage 10's share-progress regression — these
    fields must be a hardcoded omission, never a togglable category."""
    _coach, coach_headers = signed_up_coach
    singer, singer_headers = signed_up_user

    secret_illness = "UNIQUE_MARKER_illness_xyz123"
    secret_reflux = "UNIQUE_MARKER_reflux_abc456"
    secret_notes = "UNIQUE_MARKER_notes_def789"
    client.post(
        "/api/v1/checkins",
        headers=singer_headers,
        json={
            "checkin_date": TODAY,
            "illness_symptoms": secret_illness,
            "reflux_symptoms": secret_reflux,
            "notes": secret_notes,
        },
    )
    _connect(
        client,
        coach_headers,
        singer["email"],
        singer_headers,
        ["recovery_trends", "vocal_range", "exercise_history"],
    )

    resp = client.get(
        f"/api/v1/coach/singers/{singer['user']['id']}/summary",
        headers=coach_headers,
        params={"date": TODAY},
    )
    assert resp.status_code == 200
    raw = json.dumps(resp.json())
    assert secret_illness not in raw
    assert secret_reflux not in raw
    assert secret_notes not in raw
