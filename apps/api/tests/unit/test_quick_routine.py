import uuid

from app.exercise_library import SEED_EXERCISES
from app.exercise_routine import ExerciseInfo, RoutineSignals
from app.quick_routine import generate_quick_routine


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


class TestWarmUp:
    def test_pulls_breathing_humming_sovt_in_order(self) -> None:
        exercises = make_exercises()
        result = generate_quick_routine(exercises, "warm_up", healthy_signals())
        assert [item.category for item in result.items] == [
            "Breathing",
            "Gentle humming",
            "SOVT",
        ]

    def test_never_repeats_an_exercise(self) -> None:
        exercises = make_exercises()
        result = generate_quick_routine(exercises, "warm_up", healthy_signals())
        ids = [item.id for item in result.items]
        assert len(ids) == len(set(ids))

    def test_total_duration_is_sum_of_selected_items(self) -> None:
        exercises = make_exercises()
        result = generate_quick_routine(exercises, "warm_up", healthy_signals())
        assert result.total_duration_seconds == sum(i.duration_seconds for i in result.items)


class TestCoolDown:
    def test_pulls_only_vocal_cooldown(self) -> None:
        exercises = make_exercises()
        result = generate_quick_routine(exercises, "cool_down", healthy_signals())
        assert [item.category for item in result.items] == ["Vocal cooldown"]


class TestSafetyStillApplies:
    """The category filter is a no-op today (every warm-up category is already "low"
    intensity), but the safety pipeline itself -- the hard discomfort override -- must still
    run identically to the daily adaptive routine, not be silently skipped for a "quick" flow."""

    def test_high_discomfort_forces_low_cap_and_safety_message(self) -> None:
        exercises = make_exercises()
        signals = healthy_signals(throat_discomfort=8)
        result = generate_quick_routine(exercises, "warm_up", signals)
        assert result.intensity_cap == "low"
        assert result.safety_message is not None
        # Still returns a valid (shrunk, not empty) routine -- discomfort never means "nothing."
        assert len(result.items) == 3

    def test_healthy_day_reaches_high_cap(self) -> None:
        exercises = make_exercises()
        result = generate_quick_routine(exercises, "cool_down", healthy_signals())
        assert result.intensity_cap == "high"
        assert result.safety_message is None
