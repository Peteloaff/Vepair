from datetime import date

import pytest

from app.recovery_score import (
    NEUTRAL_COMPONENT_SCORE,
    compute_recovery_score,
    confidence_label_from_coverage,
    score_hydration,
    score_recent_vocal_load,
    score_sleep,
    score_subjective_fatigue,
    status_from_score,
)

TODAY = date(2026, 8, 11)


class TestScoreSubjectiveFatigue:
    def test_lowest_fatigue_scores_100(self) -> None:
        assert score_subjective_fatigue(1) == 100.0

    def test_highest_fatigue_scores_0(self) -> None:
        assert score_subjective_fatigue(10) == 0.0

    def test_none_is_excluded_not_zero(self) -> None:
        assert score_subjective_fatigue(None) is None


class TestScoreSleep:
    def test_eight_hours_is_peak(self) -> None:
        assert score_sleep(8.0) == 100.0

    def test_falls_off_symmetrically(self) -> None:
        assert score_sleep(6.0) == pytest.approx(score_sleep(10.0))

    def test_floors_at_zero_for_extreme_values(self) -> None:
        assert score_sleep(0.0) == 0.0

    def test_none_is_excluded(self) -> None:
        assert score_sleep(None) is None


class TestScoreRecentVocalLoad:
    def test_none_load_scores_100(self) -> None:
        assert score_recent_vocal_load("none", "none", False) == 100.0

    def test_high_load_scores_low(self) -> None:
        assert score_recent_vocal_load("high", "none", False) == 20.0

    def test_more_demanding_of_two_loads_dominates(self) -> None:
        assert score_recent_vocal_load("low", "high", False) == 20.0

    def test_rehearsal_yesterday_lowers_score(self) -> None:
        with_rehearsal = score_recent_vocal_load("low", "low", True)
        without_rehearsal = score_recent_vocal_load("low", "low", False)
        assert with_rehearsal < without_rehearsal

    def test_rehearsal_penalty_never_goes_negative(self) -> None:
        assert score_recent_vocal_load("high", "high", True) == 5.0

    def test_both_loads_missing_is_excluded(self) -> None:
        assert score_recent_vocal_load(None, None, False) is None


class TestScoreHydration:
    def test_high_hydration_scores_100(self) -> None:
        assert score_hydration("high") == 100.0

    def test_none_hydration_scores_low(self) -> None:
        assert score_hydration("none") == 20.0

    def test_missing_value_is_excluded(self) -> None:
        assert score_hydration(None) is None


class TestConfidenceLabelFromCoverage:
    @pytest.mark.parametrize(
        ("available", "expected"),
        [
            (0, "insufficient"),
            (1, "low"),
            (2, "low"),
            (3, "moderate"),
            (4, "moderate"),
            (5, "high"),
            (6, "high"),
        ],
    )
    def test_thresholds(self, available: int, expected: str) -> None:
        assert confidence_label_from_coverage(available, 6) == expected


class TestStatusFromScore:
    def test_high_score_is_green(self) -> None:
        status, label, safety = status_from_score(85, throat_discomfort=1)
        assert status == "green"
        assert safety is None

    def test_mid_score_is_yellow(self) -> None:
        status, _, _ = status_from_score(55, throat_discomfort=None)
        assert status == "yellow"

    def test_low_score_is_red(self) -> None:
        status, _, _ = status_from_score(20, throat_discomfort=None)
        assert status == "red"

    def test_none_score_is_unknown(self) -> None:
        status, _, safety = status_from_score(None, throat_discomfort=None)
        assert status == "unknown"
        assert safety is None

    def test_high_discomfort_forces_red_even_with_perfect_score(self) -> None:
        """A hard safety override, not something a good score can outvote."""
        status, _, safety = status_from_score(100, throat_discomfort=9)
        assert status == "red"
        assert safety is not None

    def test_discomfort_below_threshold_does_not_override(self) -> None:
        status, _, safety = status_from_score(85, throat_discomfort=6)
        assert status == "green"
        assert safety is None


class TestComputeRecoveryScore:
    def test_all_good_components_yields_high_score_and_green(self) -> None:
        scores = {
            "consistency_vs_baseline": 95.0,
            "acoustic_stability": 90.0,
            "subjective_fatigue": 100.0,
            "sleep": 100.0,
            "recent_vocal_load": 100.0,
            "hydration": 100.0,
        }
        result = compute_recovery_score(scores, throat_discomfort=0, score_date=TODAY)
        assert result.score_value is not None
        assert result.score_value >= 90
        assert result.status == "green"
        assert result.confidence_label == "high"

    def test_poor_sleep_alone_does_not_falsely_indicate_injury(self) -> None:
        """Regression test: a single bad self-report component must not swing the whole score
        to "red" — see the NEUTRAL_COMPONENT_SCORE blending in compute_recovery_score."""
        result = compute_recovery_score(
            {"sleep": score_sleep(2.0)}, throat_discomfort=None, score_date=TODAY
        )
        assert result.status != "red"

    def test_no_recording_today_does_not_tank_score(self) -> None:
        """Missing acoustic components (e.g. no recording today, or one too short to analyze)
        must regress toward neutral, never toward zero."""
        scores = {
            "subjective_fatigue": 80.0,
            "sleep": 80.0,
            "recent_vocal_load": 80.0,
            "hydration": 80.0,
        }
        result = compute_recovery_score(scores, throat_discomfort=1, score_date=TODAY)
        # Two components (0.40 combined weight) default to neutral (50); with everything else
        # at 80, the floor on the blended score is well above a "tanked" value.
        assert result.score_value is not None
        assert result.score_value >= 60

    def test_no_data_at_all_returns_none_not_a_fabricated_number(self) -> None:
        result = compute_recovery_score({}, throat_discomfort=None, score_date=TODAY)
        assert result.score_value is None
        assert result.confidence_label == "insufficient"
        assert result.status == "unknown"

    def test_high_discomfort_overrides_otherwise_perfect_score(self) -> None:
        scores = {
            "consistency_vs_baseline": 100.0,
            "acoustic_stability": 100.0,
            "subjective_fatigue": 100.0,
            "sleep": 100.0,
            "recent_vocal_load": 100.0,
            "hydration": 100.0,
        }
        result = compute_recovery_score(scores, throat_discomfort=8, score_date=TODAY)
        assert result.status == "red"
        assert result.safety_message is not None

    def test_same_input_always_produces_same_score(self) -> None:
        scores = {
            "consistency_vs_baseline": 62.0,
            "sleep": 71.0,
            "hydration": 40.0,
        }
        first = compute_recovery_score(scores, throat_discomfort=3, score_date=TODAY)
        second = compute_recovery_score(scores, throat_discomfort=3, score_date=TODAY)
        assert first.score_value == second.score_value
        assert first.confidence_label == second.confidence_label
        assert first.status == second.status
        assert first.factors == second.factors

    def test_explanation_mathematically_matches_score(self) -> None:
        """Recomputes the weighted total from exactly what the response exposes (each
        component's score/weight/included flag) and confirms it reproduces score_value —
        proving the explanation isn't a separate, potentially-divergent narrative path."""
        scores = {
            "consistency_vs_baseline": 88.0,
            "acoustic_stability": 40.0,
            "subjective_fatigue": 70.0,
            "sleep": 55.0,
        }
        result = compute_recovery_score(scores, throat_discomfort=2, score_date=TODAY)
        recomputed = sum(
            c.weight * (c.score if c.score is not None else NEUTRAL_COMPONENT_SCORE)
            for c in result.components
        )
        assert result.score_value == round(recomputed)

    def test_positive_and_negative_factors_reflect_component_scores(self) -> None:
        scores = {
            "sleep": 95.0,  # clearly positive
            "hydration": 10.0,  # clearly negative
            "recent_vocal_load": 55.0,  # neutral, should not appear
        }
        result = compute_recovery_score(scores, throat_discomfort=1, score_date=TODAY)
        directions = {f["direction"] for f in result.factors}
        texts = " ".join(f["text"] for f in result.factors)
        assert "positive" in directions
        assert "negative" in directions
        assert "sleep" not in texts.lower() or "good night's sleep" in texts.lower()
        assert len(result.factors) == 2

    def test_result_score_date_matches_caller_supplied_date(self) -> None:
        result = compute_recovery_score({}, throat_discomfort=None, score_date=TODAY)
        assert result.score_date == TODAY
