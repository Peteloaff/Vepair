import uuid

import pytest

from app.exercise_library import CATEGORY_INTENSITY, SEED_EXERCISES
from app.exercise_routine import (
    INTENSITY_ORDER,
    ExerciseInfo,
    RoutineSignals,
    generate_routine,
)


def make_exercises() -> list[ExerciseInfo]:
    return [
        ExerciseInfo(
            id=uuid.uuid4(),
            name=e.name,
            category=e.category,
            purpose=e.purpose,
            instructions=e.instructions,
            duration_seconds=e.duration_seconds,
            difficulty=e.difficulty,
            contraindications=e.contraindications,
            target_measurement=e.target_measurement,
            expected_result=e.expected_result,
        )
        for e in SEED_EXERCISES
    ]


def healthy_signals(**overrides) -> RoutineSignals:
    base = {
        "recovery_status": "green",
        "throat_discomfort": 1,
        "fatigue": 2,
        "sleep_hours": 8.0,
        "rehearsal_or_performance_yesterday": False,
        "baseline_deviation": False,
        "days_since_last_exercise": 1,
        "goal_text": None,
    }
    base.update(overrides)
    return RoutineSignals(**base)


class TestHealthyBaseline:
    def test_full_intensity_available(self) -> None:
        exercises = make_exercises()
        result = generate_routine(exercises, 10, healthy_signals())
        assert result.intensity_cap == "high"
        assert result.safety_message is None

    def test_fills_close_to_target_duration(self) -> None:
        exercises = make_exercises()
        result = generate_routine(exercises, 10, healthy_signals())
        assert 480 <= result.total_duration_seconds <= 600  # within a minute of target

    def test_starts_with_breathing_and_ends_with_cooldown(self) -> None:
        exercises = make_exercises()
        for length in (5, 10, 15, 20):
            result = generate_routine(exercises, length, healthy_signals())
            assert result.items[0].category == "Breathing"
            assert result.items[-1].category == "Vocal cooldown"

    def test_never_repeats_an_exercise(self) -> None:
        exercises = make_exercises()
        result = generate_routine(exercises, 20, healthy_signals())
        ids = [item.id for item in result.items]
        assert len(ids) == len(set(ids))


class TestHighDiscomfort:
    def test_forces_low_intensity_and_safety_message(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(throat_discomfort=8)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "low"
        assert result.safety_message is not None

    def test_never_recommends_high_intensity_exercise(self) -> None:
        """The hard requirement: reported discomfort must never lead to a "push through it"
        routine — verified by checking every selected exercise's own intensity tier."""
        exercises = make_exercises()
        signals = healthy_signals(throat_discomfort=9)
        result = generate_routine(exercises, 20, signals)
        for item in result.items:
            assert CATEGORY_INTENSITY[item.category] in ("low",)

    def test_discomfort_below_threshold_does_not_trigger_override(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(throat_discomfort=6)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "high"
        assert result.safety_message is None


class TestFatiguedUser:
    def test_high_fatigue_caps_at_moderate(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(fatigue=9)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "moderate"

    def test_low_fatigue_does_not_cap(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(fatigue=2)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "high"


class TestDangerousCombinations:
    def test_heavy_rehearsal_plus_high_fatigue_caps_at_low(self) -> None:
        """A specific "dangerous combination" the Stage 6 test plan calls out: heavy rehearsal
        yesterday stacked with high reported fatigue must not produce a demanding routine, even
        though fatigue alone would only cap at moderate."""
        exercises = make_exercises()
        signals = healthy_signals(rehearsal_or_performance_yesterday=True, fatigue=8)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "low"

    def test_rehearsal_alone_without_fatigue_does_not_cap(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(rehearsal_or_performance_yesterday=True, fatigue=2)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "high"

    def test_red_status_never_yields_a_high_intensity_exercise(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(recovery_status="red")
        result = generate_routine(exercises, 20, signals)
        for item in result.items:
            assert INTENSITY_ORDER[CATEGORY_INTENSITY[item.category]] <= INTENSITY_ORDER["low"]


class TestPoorSleep:
    def test_poor_sleep_caps_at_moderate(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(sleep_hours=3.0)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "moderate"

    def test_good_sleep_does_not_cap(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(sleep_hours=8.0)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "high"


class TestRangeReduction:
    def test_baseline_deviation_caps_at_moderate(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(baseline_deviation=True)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "moderate"
        for item in result.items:
            assert CATEGORY_INTENSITY[item.category] != "high"


class TestSeveralRestDays:
    def test_long_gap_since_last_exercise_eases_back_in(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(days_since_last_exercise=10)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "moderate"

    def test_recent_exercise_does_not_cap(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(days_since_last_exercise=1)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "high"

    def test_never_having_exercised_before_does_not_cap(self) -> None:
        """None means "no history," not "a long gap" — must not be misread as a rest-day cap."""
        exercises = make_exercises()
        signals = healthy_signals(days_since_last_exercise=None)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "high"


class TestGoalAdaptation:
    def test_range_goal_prioritizes_range_exercises_when_safe(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(goal_text="I want to expand my vocal range")
        result = generate_routine(exercises, 5, signals)
        categories = {item.category for item in result.items}
        assert "Range exploration" in categories

    def test_goal_never_overrides_a_safety_cap(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(goal_text="I want to expand my vocal range", throat_discomfort=9)
        result = generate_routine(exercises, 10, signals)
        assert result.intensity_cap == "low"
        categories = {item.category for item in result.items}
        assert "Range exploration" not in categories
        assert "Pitch glides" not in categories


@pytest.mark.parametrize("length", [5, 10, 15, 20])
def test_all_valid_lengths_produce_a_nonempty_routine(length: int) -> None:
    exercises = make_exercises()
    result = generate_routine(exercises, length, healthy_signals())
    assert len(result.items) > 0
    assert result.total_duration_seconds <= length * 60


class TestAdaptiveChallenge:
    """"As you get better the AI needs to challenge your voice to get better as well" — always
    subordinate to every existing safety rule above; see the "never overrides" tests."""

    def test_positive_trend_on_an_uncapped_day_reaches_more_demanding_categories(self) -> None:
        exercises = make_exercises()
        normal = generate_routine(exercises, 10, healthy_signals(trending_positive=False))
        challenge = generate_routine(exercises, 10, healthy_signals(trending_positive=True))

        normal_categories = {item.category for item in normal.items}
        challenge_categories = {item.category for item in challenge.items}
        assert "Range exploration" not in normal_categories
        assert "Range exploration" in challenge_categories or "Pitch glides" in challenge_categories

    def test_reasons_disclose_challenge_mode_when_active(self) -> None:
        exercises = make_exercises()
        result = generate_routine(exercises, 10, healthy_signals(trending_positive=True))
        assert any("more demanding" in reason for reason in result.reasons)

    def test_no_challenge_note_when_trend_is_not_positive(self) -> None:
        exercises = make_exercises()
        result = generate_routine(exercises, 10, healthy_signals(trending_positive=False))
        assert not any("more demanding" in reason for reason in result.reasons)

    def test_positive_trend_never_overrides_a_high_discomfort_cap(self) -> None:
        """The core safety property: challenge_mode can only ever apply on an already-uncapped
        day. A positive trend must never unlock high-intensity exercises when discomfort alone
        would otherwise cap the routine at low."""
        exercises = make_exercises()
        result = generate_routine(
            exercises, 10, healthy_signals(throat_discomfort=9, trending_positive=True)
        )
        assert result.intensity_cap == "low"
        categories = {item.category for item in result.items}
        assert "Range exploration" not in categories
        assert "Pitch glides" not in categories

    def test_positive_trend_never_overrides_a_red_recovery_status(self) -> None:
        exercises = make_exercises()
        result = generate_routine(
            exercises, 10, healthy_signals(recovery_status="red", trending_positive=True)
        )
        assert result.intensity_cap == "low"

    def test_positive_trend_never_overrides_several_rest_days(self) -> None:
        exercises = make_exercises()
        result = generate_routine(
            exercises,
            10,
            healthy_signals(days_since_last_exercise=10, trending_positive=True),
        )
        assert result.intensity_cap == "moderate"


class TestTrackChallengeMode:
    """Stage 9: track choice adjusts how readily challenge mode engages, but never how it
    behaves once engaged, and never any hard safety rule above it."""

    def test_repair_track_never_enters_challenge_mode_even_with_positive_trend(self) -> None:
        exercises = make_exercises()
        result = generate_routine(
            exercises, 10, healthy_signals(track="repair", trending_positive=True)
        )
        assert not any("more demanding" in reason for reason in result.reasons)
        categories = {item.category for item in result.items}
        assert "Range exploration" not in categories

    def test_improvement_track_enters_challenge_mode_without_a_positive_trend(self) -> None:
        exercises = make_exercises()
        result = generate_routine(
            exercises, 10, healthy_signals(track="improvement", trending_positive=False)
        )
        assert any("Improvement track" in reason for reason in result.reasons)
        categories = {item.category for item in result.items}
        assert "Range exploration" in categories or "Pitch glides" in categories

    def test_no_track_keeps_original_trend_gated_behavior(self) -> None:
        exercises = make_exercises()
        result = generate_routine(
            exercises, 10, healthy_signals(track=None, trending_positive=False)
        )
        assert not any("more demanding" in reason for reason in result.reasons)

    def test_improvement_track_never_overrides_a_high_discomfort_cap(self) -> None:
        exercises = make_exercises()
        result = generate_routine(
            exercises, 10, healthy_signals(track="improvement", throat_discomfort=9)
        )
        assert result.intensity_cap == "low"
        categories = {item.category for item in result.items}
        assert "Range exploration" not in categories
        assert "Pitch glides" not in categories

    def test_improvement_track_never_overrides_a_red_recovery_status(self) -> None:
        exercises = make_exercises()
        result = generate_routine(
            exercises, 10, healthy_signals(track="improvement", recovery_status="red")
        )
        assert result.intensity_cap == "low"
