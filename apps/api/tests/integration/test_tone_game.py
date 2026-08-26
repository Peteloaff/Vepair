"""Tone Match Challenge (5-tone scored game). Grading happens client-side (see
apps/web/src/lib/toneGame.ts); this router's only job is persisting the 5 already-graded
attempts and returning them back, self-scoped per user."""

from datetime import UTC, datetime, timedelta

from app.models import ToneGameSession


def _attempt(order_index, score=80, grade="close"):
    return {
        "order_index": order_index,
        "target_note": "C4",
        "target_hz": 261.63,
        "detected_hz": 262.0,
        "semitones_off": 0.3,
        "grade": grade,
        "hold_fraction": 0.6,
        "reaction_ms": 400,
        "score": score,
    }


def _full_session_payload(scores=(80, 90, 70, 60, 100)):
    return {"attempts": [_attempt(i, score=s) for i, s in enumerate(scores)]}


def test_create_session_persists_and_sums_score(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.post(
        "/api/v1/tone-game/sessions", headers=headers, json=_full_session_payload()
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["total_score"] == 80 + 90 + 70 + 60 + 100
    assert len(body["attempts"]) == 5
    assert [a["order_index"] for a in body["attempts"]] == [0, 1, 2, 3, 4]


def test_list_sessions_returns_own_only_newest_first(client, db_session, signed_up_user) -> None:
    _user, headers = signed_up_user
    import uuid

    other_email = f"test_{uuid.uuid4().hex[:12]}@example.com"
    signup = client.post(
        "/api/v1/auth/signup", json={"email": other_email, "password": "correcthorse123"}
    )
    assert signup.status_code == 201, signup.text
    other_headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}

    low = _full_session_payload((10, 10, 10, 10, 10))
    high = _full_session_payload((20, 20, 20, 20, 20))
    others = _full_session_payload((99, 99, 99, 99, 99))
    client.post("/api/v1/tone-game/sessions", headers=headers, json=low)
    client.post("/api/v1/tone-game/sessions", headers=headers, json=high)
    client.post("/api/v1/tone-game/sessions", headers=other_headers, json=others)

    # Both of this user's sessions land in the same DB transaction inside this test, so
    # Postgres's now() (transaction-scoped, not statement-scoped) would give them identical
    # played_at values -- force distinct ones directly so ordering is actually exercised.
    own_sessions = list(db_session.query(ToneGameSession).filter_by(user_id=_user["user"]["id"]))
    own_sessions.sort(key=lambda s: s.total_score)
    base = datetime.now(UTC)
    for i, session in enumerate(own_sessions):
        session.played_at = base + timedelta(seconds=i)
    db_session.commit()

    resp = client.get("/api/v1/tone-game/sessions", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 2
    assert [s["total_score"] for s in body] == [100, 50]


def test_create_session_requires_auth(client) -> None:
    resp = client.post("/api/v1/tone-game/sessions", json=_full_session_payload())
    assert resp.status_code == 401


def test_list_sessions_requires_auth(client) -> None:
    resp = client.get("/api/v1/tone-game/sessions")
    assert resp.status_code == 401


def test_create_session_rejects_wrong_attempt_count(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    payload = {"attempts": [_attempt(0), _attempt(1)]}
    resp = client.post("/api/v1/tone-game/sessions", headers=headers, json=payload)
    assert resp.status_code == 422


def test_create_session_rejects_invalid_grade(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    payload = _full_session_payload()
    payload["attempts"][0]["grade"] = "amazing"
    resp = client.post("/api/v1/tone-game/sessions", headers=headers, json=payload)
    assert resp.status_code == 422
