"""Stage 9 track selection and 90-day plan, driven through the real API endpoints — not the
pure functions unit-tested in tests/unit/test_vocal_plan.py."""

import uuid
from datetime import date, timedelta

from app.models import Baseline, RecoveryScore
from tests.integration.test_vocal_range import upload_range_recording


def complete_onboarding(client, headers) -> None:
    resp = client.put("/api/v1/profile", headers=headers, json={})
    assert resp.status_code == 200, resp.text


def give_user_assessment_data(client, headers) -> dict:
    """The minimum real data build_assessment_snapshot needs: one analyzed recording plus a
    vocal-range entry."""
    high = upload_range_recording(client, headers, "range_high", 220.0)  # A3
    resp = client.post(
        "/api/v1/vocal-range", headers=headers, json={"high_recording_id": high["id"]}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestSetTrack:
    def test_rejects_an_unknown_track(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        resp = client.patch("/api/v1/profile/track", headers=headers, json={"track": "bogus"})
        assert resp.status_code == 422

    def test_works_immediately_after_signup_with_no_profile_yet(
        self, client, signed_up_user
    ) -> None:
        """Track selection must work the moment a new user lands on onboarding — the very
        first thing they're asked, never gated behind saving the rest of the profile form
        first. Found live: a brand-new signup had no UserProfile row yet."""
        _user, headers = signed_up_user
        resp = client.patch("/api/v1/profile/track", headers=headers, json={"track": "repair"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["track"] == "repair"

        profile = client.get("/api/v1/profile", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["track"] == "repair"

    def test_setting_track_without_assessment_data_yet_leaves_plan_pending(
        self, client, signed_up_user
    ) -> None:
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        resp = client.patch("/api/v1/profile/track", headers=headers, json={"track": "repair"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["track"] == "repair"
        assert body["plan"] is None
        assert body["plan_pending_reason"] is not None

    def test_track_is_reflected_on_the_profile(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        client.patch("/api/v1/profile/track", headers=headers, json={"track": "improvement"})
        resp = client.get("/api/v1/profile", headers=headers)
        assert resp.json()["track"] == "improvement"


class TestPlanCreation:
    def test_setting_track_after_assessment_data_exists_creates_a_plan_immediately(
        self, client, signed_up_user
    ) -> None:
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        give_user_assessment_data(client, headers)

        resp = client.patch("/api/v1/profile/track", headers=headers, json={"track": "repair"})
        assert resp.status_code == 200
        plan = resp.json()["plan"]
        assert plan is not None
        assert plan["track"] == "repair"
        assert plan["status"] == "active"
        assert plan["target_milestones"]["goal"] == "stability"

    def test_submitting_a_vocal_range_entry_after_choosing_a_track_creates_the_pending_plan(
        self, client, signed_up_user
    ) -> None:
        """"once the AI hears you after you choose it can choose the appropriate 90 day
        exercises" — a track can be chosen before any data exists; the plan appears as soon as
        real data does, without any extra action from the user."""
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        set_resp = client.patch(
            "/api/v1/profile/track", headers=headers, json={"track": "improvement"}
        )
        assert set_resp.json()["plan"] is None

        give_user_assessment_data(client, headers)

        plan_resp = client.get("/api/v1/vocal-plan", headers=headers)
        assert plan_resp.status_code == 200
        plan = plan_resp.json()["plan"]
        assert plan is not None
        assert plan["track"] == "improvement"

    def test_improvement_plan_targets_range_extension_from_measured_high_note(
        self, client, signed_up_user
    ) -> None:
        """"specific to the range that it analyzed" — the plan target is derived from the
        user's own just-measured data, not a generic goal."""
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        range_entry = give_user_assessment_data(client, headers)
        resp = client.patch(
            "/api/v1/profile/track", headers=headers, json={"track": "improvement"}
        )
        milestones = resp.json()["plan"]["target_milestones"]
        assert milestones["goal"] == "range_extension"
        assert milestones["from_note"] == range_entry["comfortable_high_note"]

    def test_manually_switching_track_replaces_a_mismatched_active_plan(
        self, client, signed_up_user
    ) -> None:
        """A deliberate track switch through the selector is a strong enough signal to
        replace the old plan immediately — unlike an unrelated vocal-range submission, which
        must never restart the 90-day clock on an already-active plan."""
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        give_user_assessment_data(client, headers)

        repair_resp = client.patch(
            "/api/v1/profile/track", headers=headers, json={"track": "repair"}
        )
        repair_plan_id = repair_resp.json()["plan"]["id"]

        improvement_resp = client.patch(
            "/api/v1/profile/track", headers=headers, json={"track": "improvement"}
        )
        improvement_plan = improvement_resp.json()["plan"]
        assert improvement_plan is not None
        assert improvement_plan["track"] == "improvement"
        assert improvement_plan["id"] != repair_plan_id

        plan_resp = client.get("/api/v1/vocal-plan", headers=headers)
        assert plan_resp.json()["plan"]["track"] == "improvement"

    def test_reselecting_the_same_track_keeps_the_existing_plan(
        self, client, signed_up_user
    ) -> None:
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        give_user_assessment_data(client, headers)

        first = client.patch("/api/v1/profile/track", headers=headers, json={"track": "repair"})
        second = client.patch("/api/v1/profile/track", headers=headers, json={"track": "repair"})
        assert first.json()["plan"]["id"] == second.json()["plan"]["id"]

    def test_plan_end_date_is_ninety_days_after_start(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        give_user_assessment_data(client, headers)
        resp = client.patch("/api/v1/profile/track", headers=headers, json={"track": "repair"})
        plan = resp.json()["plan"]
        start = date.fromisoformat(plan["start_date"])
        end = date.fromisoformat(plan["target_end_date"])
        assert (end - start).days == 90


class TestGetPlan:
    def test_no_track_selected_returns_an_empty_view(self, client, signed_up_user) -> None:
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        resp = client.get("/api/v1/vocal-plan", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"plan": None, "readiness": None, "just_graduated": False}

    def test_improvement_plan_never_reports_graduation_readiness(
        self, client, signed_up_user
    ) -> None:
        """Graduation only ever applies to a Repair-track plan — Improvement has nowhere
        further to graduate to."""
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        give_user_assessment_data(client, headers)
        client.patch("/api/v1/profile/track", headers=headers, json={"track": "improvement"})

        resp = client.get("/api/v1/vocal-plan", headers=headers)
        body = resp.json()
        assert body["readiness"] is None
        assert body["just_graduated"] is False


class TestGraduation:
    def _seed_ready_recovery_history(self, db_session, user_id: uuid.UUID, today: date) -> None:
        for i in range(14):
            db_session.add(
                RecoveryScore(
                    user_id=user_id,
                    score_date=today - timedelta(days=i),
                    score_value=80,
                    components={"status": "green"},
                )
            )
        db_session.add(
            Baseline(
                user_id=user_id,
                metric_name="f0_mean_hz",
                window_start=today - timedelta(days=30),
                window_end=today,
                median_value=150.0,
                mad_value=5.0,
                sample_count=10,
                confidence_label="established",
                confidence_pct=90.0,
            )
        )
        db_session.commit()

    def test_repair_track_auto_graduates_to_improvement_when_criteria_are_met(
        self, client, db_session, signed_up_user
    ) -> None:
        """"once it feels like you have repaired your voice it will then move you to
        improvement... it will start you after hearing your voice with a recommended 90-day
        plan" — the founder's exact spec for auto-graduation."""
        user, headers = signed_up_user
        user_id = uuid.UUID(user["user"]["id"])
        complete_onboarding(client, headers)
        give_user_assessment_data(client, headers)
        client.patch("/api/v1/profile/track", headers=headers, json={"track": "repair"})

        self._seed_ready_recovery_history(db_session, user_id, date.today())

        resp = client.get("/api/v1/vocal-plan", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["just_graduated"] is True
        assert body["readiness"]["ready"] is True
        assert body["plan"]["track"] == "improvement"

        profile_resp = client.get("/api/v1/profile", headers=headers)
        assert profile_resp.json()["track"] == "improvement"

    def test_repair_track_stays_on_repair_when_not_yet_ready(
        self, client, db_session, signed_up_user
    ) -> None:
        _user, headers = signed_up_user
        complete_onboarding(client, headers)
        give_user_assessment_data(client, headers)
        client.patch("/api/v1/profile/track", headers=headers, json={"track": "repair"})

        resp = client.get("/api/v1/vocal-plan", headers=headers)
        body = resp.json()
        assert body["just_graduated"] is False
        assert body["readiness"]["ready"] is False
        assert body["plan"]["track"] == "repair"
