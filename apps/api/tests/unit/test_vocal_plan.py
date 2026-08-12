from datetime import date

from app.vocal_plan import (
    PLAN_DURATION_DAYS,
    READINESS_LOOKBACK_DAYS,
    assess_graduation_readiness,
    build_target_milestones,
    plan_end_date,
)


def steady_statuses(n: int = READINESS_LOOKBACK_DAYS, red: int = 0) -> list[str]:
    return ["red"] * red + ["green"] * (n - red)


class TestAssessGraduationReadiness:
    def test_ready_when_every_criterion_passes(self) -> None:
        result = assess_graduation_readiness(steady_statuses(), "established", ["stable"])
        assert result.ready is True
        assert len(result.reasons) == 3

    def test_not_ready_with_too_few_days_of_data(self) -> None:
        result = assess_graduation_readiness(steady_statuses(n=5), "established", ["stable"])
        assert result.ready is False
        assert any("at least" in r for r in result.reasons)

    def test_not_ready_with_too_many_red_days(self) -> None:
        result = assess_graduation_readiness(steady_statuses(red=10), "established", ["stable"])
        assert result.ready is False

    def test_not_ready_with_low_baseline_confidence(self) -> None:
        result = assess_graduation_readiness(steady_statuses(), "new", ["stable"])
        assert result.ready is False

    def test_not_ready_with_a_missing_baseline_confidence(self) -> None:
        result = assess_graduation_readiness(steady_statuses(), None, ["stable"])
        assert result.ready is False

    def test_not_ready_with_a_declining_exercise_trend(self) -> None:
        result = assess_graduation_readiness(
            steady_statuses(), "established", ["stable", "declining"]
        )
        assert result.ready is False

    def test_reasons_always_cover_all_three_criteria_regardless_of_outcome(self) -> None:
        """A "not ready" answer must never be a mystery — every criterion's reason is always
        present, not just the one that failed."""
        result = assess_graduation_readiness(steady_statuses(n=3), None, ["declining"])
        assert result.ready is False
        assert len(result.reasons) == 3

    def test_no_declining_trends_is_fine_with_an_empty_trend_list(self) -> None:
        result = assess_graduation_readiness(steady_statuses(), "developing", [])
        assert result.ready is True


class TestBuildTargetMilestones:
    def test_repair_targets_stability(self) -> None:
        milestones = build_target_milestones("repair", {})
        assert milestones["goal"] == "stability"
        assert milestones["target_stable_days"] > 0

    def test_improvement_targets_range_extension_from_current_high_note(self) -> None:
        milestones = build_target_milestones(
            "improvement", {"comfortable_high_note": "G4"}
        )
        assert milestones["goal"] == "range_extension"
        assert milestones["from_note"] == "G4"
        assert milestones["target_semitones"] > 0

    def test_unknown_track_raises(self) -> None:
        try:
            build_target_milestones("bogus", {})
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for an unknown track")


class TestPlanEndDate:
    def test_end_date_is_start_plus_duration(self) -> None:
        start = date(2026, 1, 1)
        assert (plan_end_date(start) - start).days == PLAN_DURATION_DAYS
