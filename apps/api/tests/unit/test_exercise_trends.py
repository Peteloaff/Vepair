from app.exercise_trends import classify_trend, overall_trend_is_positive


class TestClassifyTrendLowerIsBetter:
    def test_improving_when_recent_is_meaningfully_lower(self) -> None:
        trend = classify_trend([1.0, 1.1, 0.9, 0.3, 0.2, 0.25], "jitter_percent")
        assert trend.direction == "improving"

    def test_declining_when_recent_is_meaningfully_higher(self) -> None:
        trend = classify_trend([0.2, 0.25, 0.3, 0.9, 1.0, 1.1], "jitter_percent")
        assert trend.direction == "declining"

    def test_stable_when_difference_is_within_noise_tolerance(self) -> None:
        trend = classify_trend([1.0, 1.01, 0.99, 1.0, 1.02, 0.98], "jitter_percent")
        assert trend.direction == "stable"


class TestClassifyTrendHigherIsBetter:
    def test_improving_when_recent_is_meaningfully_higher(self) -> None:
        trend = classify_trend([60, 61, 59, 70, 71, 72], "hnr_db")
        assert trend.direction == "improving"

    def test_declining_when_recent_is_meaningfully_lower(self) -> None:
        trend = classify_trend([70, 71, 72, 60, 61, 59], "hnr_db")
        assert trend.direction == "declining"


class TestClassifyTrendEdgeCases:
    def test_insufficient_data_below_minimum_attempts(self) -> None:
        trend = classify_trend([1.0, 1.1, 1.2], "jitter_percent")
        assert trend.direction == "insufficient_data"
        assert trend.recent_median is None

    def test_unknown_metric_never_guesses_a_direction(self) -> None:
        trend = classify_trend([1.0, 2.0, 3.0, 100.0, 200.0, 300.0], "spectral_centroid_hz")
        assert trend.direction == "stable"

    def test_attempt_count_reflects_all_values_seen(self) -> None:
        trend = classify_trend([1.0, 1.0, 1.0, 1.0, 1.0], "jitter_percent")
        assert trend.attempt_count == 5

    def test_exactly_at_minimum_attempts_is_classified_not_insufficient(self) -> None:
        trend = classify_trend([1.0, 1.0, 1.0, 0.1], "jitter_percent")
        assert trend.direction != "insufficient_data"


class TestOverallTrendIsPositive:
    def test_true_when_more_improving_than_declining(self) -> None:
        trends = [
            classify_trend([1.0, 1.1, 0.9, 0.3, 0.2, 0.25], "jitter_percent"),  # improving
            classify_trend([60, 61, 59, 70, 71, 72], "hnr_db"),  # improving
            classify_trend([0.2, 0.25, 0.3, 0.9, 1.0, 1.1], "jitter_percent"),  # declining
        ]
        assert overall_trend_is_positive(trends) is True

    def test_false_when_tied(self) -> None:
        trends = [
            classify_trend([1.0, 1.1, 0.9, 0.3, 0.2, 0.25], "jitter_percent"),  # improving
            classify_trend([0.2, 0.25, 0.3, 0.9, 1.0, 1.1], "jitter_percent"),  # declining
        ]
        assert overall_trend_is_positive(trends) is False

    def test_false_when_no_data_at_all(self) -> None:
        assert overall_trend_is_positive([]) is False

    def test_false_when_everything_is_insufficient_or_stable(self) -> None:
        trends = [
            classify_trend([1.0, 1.1, 1.2], "jitter_percent"),  # insufficient
            classify_trend([1.0, 1.01, 0.99, 1.0], "jitter_percent"),  # stable
        ]
        assert overall_trend_is_positive(trends) is False
