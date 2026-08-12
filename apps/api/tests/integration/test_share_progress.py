"""Stage 10 Share My Progress, driven through the real endpoints — not the pure functions
unit-tested in tests/unit/test_share_progress.py.

Confirms the founder's own accuracy requirements: only real data is ever shown, missing
metrics are omitted (never fabricated), negative progress is reported honestly, and the
share-progress numbers match the same-date values from the real /recovery-score and
/vocal-range/summary endpoints they're derived from.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

from app.baseline import MIN_SAMPLES_FOR_ANOMALY_DETECTION
from app.models import DailyCheckIn, RecoveryScore, VocalRange
from tests.integration.test_recordings import make_wav, sine_tone
from tests.integration.test_recovery_score import TODAY, post_checkin
from tests.integration.test_vocal_range import upload_range_recording


def get_today(client, headers, for_date=TODAY):
    resp = client.get(
        "/api/v1/share-progress/today", headers=headers, params={"date": for_date}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def get_progress(client, headers, for_date=TODAY):
    resp = client.get(
        "/api/v1/share-progress/progress", headers=headers, params={"date": for_date}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def upload_sustained(client, headers, freq_hz=220.0, duration_s=2.0):
    session_id = client.post("/api/v1/voice-sessions", headers=headers, json={}).json()["id"]
    wav_bytes = make_wav(sine_tone(freq_hz, duration_s, amplitude=0.5))
    resp = client.post(
        f"/api/v1/voice-sessions/{session_id}/recordings",
        headers=headers,
        data={"sample_type": "sustained_ah"},
        files={"file": ("recording.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestTodaySnapshot:
    def test_fresh_user_has_every_optional_field_omitted(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        body = get_today(client, headers)
        assert body["score_value"] is None
        assert body["score_delta"] is None
        assert body["comfortable_low_note"] is None
        assert body["comfortable_high_note"] is None
        assert body["range_span_semitones"] is None
        assert body["pitch_stability_pct"] is None
        assert body["vocal_endurance_seconds"] is None
        assert body["reported_fatigue"] is None
        assert body["vocal_load"] is None
        assert body["training_completed_pct"] is None

    def test_low_measurement_confidence_flagged_with_no_data(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        body = get_today(client, headers)
        assert body["low_measurement_confidence"] is True

    def test_reflects_real_checkin_fatigue_and_more_demanding_load(
        self, client, signed_up_user
    ) -> None:
        _user, headers = signed_up_user
        post_checkin(
            client, headers, {"fatigue": 4, "speaking_load": "low", "singing_load": "high"}
        )
        body = get_today(client, headers)
        assert body["reported_fatigue"] == 4
        assert body["vocal_load"] == "high"

    def test_reflects_real_vocal_range_and_span(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        low = upload_range_recording(client, headers, "range_low", 220.0)  # A3
        high = upload_range_recording(client, headers, "range_high", 440.0)  # A4
        client.post(
            "/api/v1/vocal-range",
            headers=headers,
            json={"low_recording_id": low["id"], "high_recording_id": high["id"]},
        )
        body = get_today(client, headers)
        assert body["comfortable_low_note"] == "A3"
        assert body["comfortable_high_note"] == "A4"
        assert body["range_span_semitones"] == 12

    def test_vocal_endurance_from_todays_sustained_recording(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        upload_sustained(client, headers, duration_s=2.0)
        body = get_today(client, headers)
        assert body["vocal_endurance_seconds"] is not None
        assert body["vocal_endurance_seconds"] > 1.0

    def test_training_completed_pct_from_todays_session(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        post_checkin(client, headers)
        routine = client.get(
            "/api/v1/routine", headers=headers, params={"length_minutes": 5, "date": TODAY}
        ).json()
        session_id = client.post(
            "/api/v1/exercise-sessions", headers=headers, json={"routine_length_minutes": 5}
        ).json()["id"]
        for i, item in enumerate(routine["items"]):
            client.post(
                f"/api/v1/exercise-sessions/{session_id}/results",
                headers=headers,
                data={"exercise_id": item["id"], "order_index": i, "completed": i % 2 == 0},
            )
        body = get_today(client, headers)
        assert body["training_completed_pct"] is not None
        assert 0 < body["training_completed_pct"] < 100

    def test_score_delta_present_only_when_yesterday_has_a_stored_score(
        self, client, db_session, signed_up_user
    ) -> None:
        user, headers = signed_up_user
        user_id = uuid.UUID(user["user"]["id"])

        no_yesterday_body = get_today(client, headers)
        assert no_yesterday_body["score_delta"] is None

        yesterday = date.today() - timedelta(days=1)
        db_session.add(
            RecoveryScore(
                user_id=user_id,
                score_date=yesterday,
                score_value=50,
                components={"status": "green"},
            )
        )
        db_session.commit()
        post_checkin(client, headers)  # gives today's score real data to compute against
        body = get_today(client, headers)
        assert body["score_value"] is not None
        assert body["score_delta"] == body["score_value"] - 50


class TestProgressSnapshot:
    def test_insufficient_data_when_nothing_recorded_yet(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        body = get_progress(client, headers)
        assert body["insufficient_data"] is True
        assert body["valid_session_count"] == 0
        assert body["comfortable_range"] is None
        assert body["pitch_stability_pct"] is None
        assert body["vocal_endurance_seconds"] is None
        assert body["reported_fatigue"] is None

    def test_range_start_vs_now_reflects_real_history(
        self, client, db_session, signed_up_user
    ) -> None:
        user, headers = signed_up_user
        user_id = uuid.UUID(user["user"]["id"])
        old = VocalRange(user_id=user_id, comfortable_high_note="G4")
        db_session.add(old)
        db_session.flush()
        old.measured_at = datetime.now(UTC) - timedelta(days=30)
        db_session.add(VocalRange(user_id=user_id, comfortable_high_note="A4"))
        db_session.commit()

        body = get_progress(client, headers)
        rng = body["comfortable_range"]
        assert rng["start_high_note"] == "G4"
        assert rng["now_high_note"] == "A4"
        assert rng["high_note_semitone_delta"] == 2
        assert rng["start_basis"] == "first_valid_session"

    def test_fatigue_honestly_reports_a_decline(
        self, client, db_session, signed_up_user
    ) -> None:
        """"Negative progress must be displayed honestly" — a rise in fatigue must show as a
        positive delta on fatigue (worse), never hidden or reframed."""
        user, headers = signed_up_user
        user_id = uuid.UUID(user["user"]["id"])
        db_session.add_all(
            [
                DailyCheckIn(
                    user_id=user_id, checkin_date=date.today() - timedelta(days=10), fatigue=2
                ),
                DailyCheckIn(user_id=user_id, checkin_date=date.today(), fatigue=8),
            ]
        )
        db_session.commit()

        body = get_progress(client, headers)
        fatigue = body["reported_fatigue"]
        assert fatigue["start_value"] == 2
        assert fatigue["now_value"] == 8
        assert fatigue["delta"] == 6

    def test_pitch_stability_omitted_without_enough_recordings_for_a_baseline(
        self, client, signed_up_user
    ) -> None:
        _user, headers = signed_up_user
        upload_sustained(client, headers)
        upload_sustained(client, headers)
        body = get_progress(client, headers)
        assert body["pitch_stability_pct"] is None

    def test_pitch_stability_present_once_a_baseline_is_established(
        self, client, signed_up_user
    ) -> None:
        _user, headers = signed_up_user
        for _ in range(MIN_SAMPLES_FOR_ANOMALY_DETECTION + 2):
            upload_sustained(client, headers)
        body = get_progress(client, headers)
        assert body["pitch_stability_pct"] is not None
        assert 0 <= body["pitch_stability_pct"]["start_value"] <= 100

    def test_vocal_endurance_omitted_with_only_one_recording(
        self, client, signed_up_user
    ) -> None:
        _user, headers = signed_up_user
        upload_sustained(client, headers, duration_s=1.5)
        body = get_progress(client, headers)
        assert body["vocal_endurance_seconds"] is None

    def test_vocal_endurance_start_vs_now_with_two_recordings(
        self, client, signed_up_user
    ) -> None:
        _user, headers = signed_up_user
        upload_sustained(client, headers, duration_s=1.0)
        upload_sustained(client, headers, duration_s=2.0)
        body = get_progress(client, headers)
        endurance = body["vocal_endurance_seconds"]
        assert endurance is not None
        assert endurance["now_value"] >= endurance["start_value"]

    def test_days_tracked_sessions_completed_and_compliance(
        self, client, signed_up_user
    ) -> None:
        _user, headers = signed_up_user
        post_checkin(client, headers)
        session_id = client.post(
            "/api/v1/exercise-sessions", headers=headers, json={"routine_length_minutes": 5}
        ).json()["id"]
        client.patch(f"/api/v1/exercise-sessions/{session_id}/complete", headers=headers)

        body = get_progress(client, headers)
        assert body["days_tracked"] == 1
        assert body["sessions_completed"] == 1
        assert body["training_compliance_pct"] == 100.0


class TestPrivacy:
    """The exported images must never contain email, account ID, location, or raw journal
    text — see PRIVACY.md."""

    FORBIDDEN_KEYS = {"email", "user_id", "id", "location", "notes", "password"}

    def test_today_response_excludes_private_fields(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        post_checkin(client, headers)
        body = get_today(client, headers)
        assert set(body.keys()).isdisjoint(self.FORBIDDEN_KEYS)

    def test_progress_response_excludes_private_fields(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        post_checkin(client, headers)
        body = get_progress(client, headers)
        assert set(body.keys()).isdisjoint(self.FORBIDDEN_KEYS)


class TestDataValidation:
    """"Every displayed value... must match [the] source calculation beyond documented
    rounding" — the founder's own explicit requirement."""

    def test_today_score_matches_recovery_score_endpoint(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        post_checkin(client, headers)
        score_body = client.get(
            "/api/v1/recovery-score", headers=headers, params={"date": TODAY}
        ).json()
        share_body = get_today(client, headers)
        assert share_body["score_value"] == score_body["score_value"]
        assert share_body["measurement_confidence_label"] == score_body["confidence_label"]

    def test_range_matches_vocal_range_summary_endpoint(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        high = upload_range_recording(client, headers, "range_high", 440.0)
        client.post(
            "/api/v1/vocal-range", headers=headers, json={"high_recording_id": high["id"]}
        )
        range_body = client.get("/api/v1/vocal-range/summary", headers=headers).json()
        share_body = get_today(client, headers)
        assert share_body["comfortable_high_note"] == range_body["current_high_note"]
