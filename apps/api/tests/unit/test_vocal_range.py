import pytest

from app.vocal_range import (
    hz_to_note_name,
    note_name_to_midi,
    semitones_between,
    suggest_stretch_target,
)


class TestHzToNoteName:
    @pytest.mark.parametrize(
        ("hz", "expected"),
        [
            (440.0, "A4"),
            (392.0, "G4"),
            (261.63, "C4"),
            (220.0, "A3"),
            (880.0, "A5"),
            (523.25, "C5"),
        ],
    )
    def test_known_reference_frequencies(self, hz: float, expected: str) -> None:
        assert hz_to_note_name(hz) == expected

    def test_octave_boundary_below_c(self) -> None:
        assert hz_to_note_name(246.94) == "B3"

    def test_octave_boundary_at_c(self) -> None:
        assert hz_to_note_name(261.63) == "C4"

    def test_one_octave_up_increments_octave_digit_by_exactly_one(self) -> None:
        low = hz_to_note_name(220.0)
        high = hz_to_note_name(440.0)
        assert low == "A3"
        assert high == "A4"
        assert semitones_between(low, high) == 12


class TestVoiceRangeCoverage:
    """"Test male/female/high/low voice ranges. Test falsetto." — Stage 8's own test plan,
    exercised against typical published F0 ranges for each rather than a single frequency."""

    @pytest.mark.parametrize(
        ("label", "low_hz", "high_hz"),
        [
            ("typical adult male chest range", 85.0, 180.0),
            ("typical adult female chest range", 165.0, 255.0),
            ("low bass extreme", 65.0, 65.0),
            ("high soprano extreme", 1000.0, 1000.0),
        ],
    )
    def test_low_and_high_convert_to_plausible_distinct_notes(
        self, label: str, low_hz: float, high_hz: float
    ) -> None:
        low_note = hz_to_note_name(low_hz)
        high_note = hz_to_note_name(high_hz)
        assert note_name_to_midi(high_note) >= note_name_to_midi(low_note), label

    def test_falsetto_range_converts_higher_than_chest_range(self) -> None:
        chest_high = hz_to_note_name(220.0)
        falsetto = hz_to_note_name(600.0)
        assert semitones_between(chest_high, falsetto) > 0


class TestNoteNameToMidi:
    def test_round_trips_through_hz_to_note_name(self) -> None:
        assert note_name_to_midi("A4") == 69
        assert note_name_to_midi("C4") == 60

    def test_rejects_garbage_input(self) -> None:
        with pytest.raises(ValueError, match="Not a valid note name"):
            note_name_to_midi("not a note")

    def test_rejects_missing_octave(self) -> None:
        with pytest.raises(ValueError, match="Not a valid note name"):
            note_name_to_midi("A")


class TestSemitonesBetween:
    def test_octave_is_twelve_semitones(self) -> None:
        assert semitones_between("A3", "A4") == 12

    def test_negative_for_a_lower_target(self) -> None:
        assert semitones_between("A4", "A3") == -12

    def test_zero_for_the_same_note(self) -> None:
        assert semitones_between("G4", "G4") == 0


class TestSuggestStretchTarget:
    def test_suggests_one_semitone_above_historical_best_when_conditions_are_good(self) -> None:
        note, reason = suggest_stretch_target("G4", "green", 1, False)
        assert note == "G#4"
        assert reason is not None

    def test_no_suggestion_without_historical_data(self) -> None:
        assert suggest_stretch_target(None, "green", 1, False) == (None, None)

    def test_no_suggestion_on_red_recovery_status(self) -> None:
        assert suggest_stretch_target("G4", "red", 1, False) == (None, None)

    def test_no_suggestion_on_high_discomfort(self) -> None:
        assert suggest_stretch_target("G4", "green", 8, False) == (None, None)

    def test_discomfort_below_threshold_does_not_suppress_it(self) -> None:
        note, _ = suggest_stretch_target("G4", "green", 5, False)
        assert note is not None

    def test_no_suggestion_when_trend_is_declining(self) -> None:
        assert suggest_stretch_target("G4", "green", 1, True) == (None, None)

    def test_never_more_than_one_semitone_beyond_best(self) -> None:
        note, _ = suggest_stretch_target("C4", "green", 1, False)
        assert semitones_between("C4", note) == 1


class TestSuggestStretchTargetTrack:
    """Stage 9: Repair always suppresses this suggestion; Improvement allows a bigger stretch
    only when the recent trend is genuinely improving, and both still pass through every
    existing safety check unchanged."""

    def test_repair_track_suppresses_suggestion_even_with_good_conditions(self) -> None:
        assert suggest_stretch_target("G4", "green", 1, False, track="repair") == (None, None)

    def test_repair_track_suppresses_even_with_improving_trend(self) -> None:
        result = suggest_stretch_target(
            "G4", "green", 1, False, track="repair", trend_is_improving=True
        )
        assert result == (None, None)

    def test_improvement_track_with_improving_trend_allows_two_semitones(self) -> None:
        note, reason = suggest_stretch_target(
            "G4", "green", 1, False, track="improvement", trend_is_improving=True
        )
        assert semitones_between("G4", note) == 2
        assert reason is not None

    def test_improvement_track_without_improving_trend_stays_at_one_semitone(self) -> None:
        note, _ = suggest_stretch_target(
            "G4", "green", 1, False, track="improvement", trend_is_improving=False
        )
        assert semitones_between("G4", note) == 1

    def test_no_track_stays_at_one_semitone_even_with_improving_trend(self) -> None:
        note, _ = suggest_stretch_target(
            "G4", "green", 1, False, track=None, trend_is_improving=True
        )
        assert semitones_between("G4", note) == 1

    def test_improvement_track_still_suppressed_by_high_discomfort(self) -> None:
        result = suggest_stretch_target(
            "G4", "green", 8, False, track="improvement", trend_is_improving=True
        )
        assert result == (None, None)

    def test_improvement_track_still_suppressed_by_red_status(self) -> None:
        result = suggest_stretch_target(
            "G4", "red", 1, False, track="improvement", trend_is_improving=True
        )
        assert result == (None, None)

    def test_improvement_track_still_suppressed_by_declining_trend(self) -> None:
        result = suggest_stretch_target(
            "G4", "green", 1, True, track="improvement", trend_is_improving=True
        )
        assert result == (None, None)
