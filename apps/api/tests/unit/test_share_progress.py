from app.share_progress import _higher_load


class TestHigherLoad:
    def test_high_beats_low(self) -> None:
        assert _higher_load("low", "high") == "high"

    def test_moderate_beats_none(self) -> None:
        assert _higher_load("none", "moderate") == "moderate"

    def test_equal_loads_return_that_load(self) -> None:
        assert _higher_load("moderate", "moderate") == "moderate"

    def test_missing_speaking_load_falls_back_to_singing(self) -> None:
        assert _higher_load(None, "high") == "high"

    def test_both_missing_returns_none(self) -> None:
        assert _higher_load(None, None) is None

    def test_unrecognized_value_is_ignored(self) -> None:
        assert _higher_load("bogus", "low") == "low"
