"""Stage 8: "it needs to listen to your exercises and keep track if you are getting better."
End-to-end trend detection, driven through the real exercise-session/result/trend endpoints
(not the pure functions unit-tested in tests/unit/test_exercise_trends.py and
tests/unit/test_exercise_routine.py).
"""

from tests.integration.test_recordings import make_wav, sine_tone
from tests.integration.test_recovery_score import post_checkin


def log_sovt_attempt(client, headers, session_id, order_index, freq_hz):
    routine = client.get(
        "/api/v1/routine", headers=headers, params={"length_minutes": 10, "date": "2026-08-11"}
    ).json()
    sovt_item = next(i for i in routine["items"] if i["category"] == "SOVT")
    wav_bytes = make_wav(sine_tone(freq_hz, 2.0, amplitude=0.5))
    resp = client.post(
        f"/api/v1/exercise-sessions/{session_id}/results",
        headers=headers,
        data={"exercise_id": sovt_item["id"], "order_index": order_index, "completed": True},
        files={"audio": ("attempt.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 201, resp.text
    return sovt_item


def test_repeated_attempts_of_the_same_exercise_produce_a_trend(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers)
    session_id = client.post(
        "/api/v1/exercise-sessions", headers=headers, json={"routine_length_minutes": 10}
    ).json()["id"]

    # SOVT's target_measurement is hnr_db (higher = better). All attempts are clean synthetic
    # tones, so HNR stays high throughout -- what matters here is that a trend gets classified
    # at all once there's enough history, not any particular direction.
    exercise = None
    for i in range(5):
        exercise = log_sovt_attempt(client, headers, session_id, i, 220.0)

    trends_resp = client.get("/api/v1/exercise-trends", headers=headers)
    assert trends_resp.status_code == 200
    trends = trends_resp.json()
    matching = [t for t in trends if t["exercise_id"] == exercise["id"]]
    assert len(matching) == 1
    assert matching[0]["direction"] in ("improving", "declining", "stable")
    assert matching[0]["attempt_count"] == 5


def test_fewer_than_minimum_attempts_reports_no_classified_trend(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers)
    session_id = client.post(
        "/api/v1/exercise-sessions", headers=headers, json={"routine_length_minutes": 10}
    ).json()["id"]

    exercise = log_sovt_attempt(client, headers, session_id, 0, 220.0)

    trends = client.get("/api/v1/exercise-trends", headers=headers).json()
    # Below MIN_ATTEMPTS_FOR_TREND, the exercise simply doesn't appear as a classified trend
    # entry rather than being reported with a guessed direction.
    matching = [t for t in trends if t["exercise_id"] == exercise["id"]]
    assert matching == [] or matching[0]["direction"] == "insufficient_data"


def test_exercise_without_target_measurement_never_appears_in_trends(
    client, signed_up_user
) -> None:
    _user, headers = signed_up_user
    post_checkin(client, headers)
    session_id = client.post(
        "/api/v1/exercise-sessions", headers=headers, json={"routine_length_minutes": 10}
    ).json()["id"]

    routine = client.get(
        "/api/v1/routine", headers=headers, params={"length_minutes": 10, "date": "2026-08-11"}
    ).json()
    breathing_item = next(i for i in routine["items"] if i["category"] == "Breathing")
    for i in range(5):
        resp = client.post(
            f"/api/v1/exercise-sessions/{session_id}/results",
            headers=headers,
            data={"exercise_id": breathing_item["id"], "order_index": i, "completed": True},
        )
        assert resp.status_code == 201

    trends = client.get("/api/v1/exercise-trends", headers=headers).json()
    assert all(t["exercise_id"] != breathing_item["id"] for t in trends)
