import statistics
from datetime import date

import pytest

from app.baseline import (
    ESTABLISHED_SESSION_COUNT,
    MIN_SAMPLES_FOR_ANOMALY_DETECTION,
    compute_baseline_stats,
    confidence_from_session_count,
    detect_anomaly,
    median_absolute_deviation,
)


def dated(values: list[float]) -> list[tuple[float, date]]:
    return [(v, date(2026, 1, i + 1)) for i, v in enumerate(values)]


# --- median_absolute_deviation ---


def test_mad_of_identical_values_is_zero() -> None:
    assert median_absolute_deviation([5.0, 5.0, 5.0], center=5.0) == 0.0


def test_mad_matches_hand_computed_example() -> None:
    # values: 1, 2, 3, 4, 100 -- median is 3, deviations are 2,1,0,1,97 -- median of those is 1
    values = [1.0, 2.0, 3.0, 4.0, 100.0]
    median = statistics.median(values)
    assert median_absolute_deviation(values, median) == 1.0


# --- compute_baseline_stats ---


def test_compute_baseline_stats_empty_input() -> None:
    stats = compute_baseline_stats("f0_mean_hz", [])
    assert stats.sample_count == 0
    assert stats.median_value is None
    assert stats.mad_value is None
    assert stats.window_start is None


def test_compute_baseline_stats_normal_input() -> None:
    stats = compute_baseline_stats("f0_mean_hz", dated([218.0, 219.0, 220.0, 221.0, 222.0]))
    assert stats.sample_count == 5
    assert stats.median_value == 220.0
    assert stats.window_start == date(2026, 1, 1)
    assert stats.window_end == date(2026, 1, 5)


def test_baseline_median_resists_a_single_wild_outlier() -> None:
    """The core Stage 4 robustness requirement: one bad data point must not meaningfully
    move the baseline. Median barely moves; for comparison, mean would be dragged hard
    toward the outlier (proving why median/MAD were chosen over mean/stddev)."""
    clean = [219.0, 220.0, 220.5, 219.5, 220.0, 219.8, 220.2]
    with_outlier = [*clean, 400.0]  # one wildly bad recording

    clean_stats = compute_baseline_stats("f0_mean_hz", dated(clean))
    outlier_stats = compute_baseline_stats("f0_mean_hz", dated(with_outlier))

    # Median barely shifts.
    assert abs(outlier_stats.median_value - clean_stats.median_value) < 1.0
    # Mean, by contrast, would shift dramatically -- demonstrating why median was chosen.
    mean_shift = abs(statistics.mean(with_outlier) - statistics.mean(clean))
    assert mean_shift > 20.0


# --- confidence_from_session_count ---


@pytest.mark.parametrize(
    ("count", "expected_label"),
    [
        (0, "insufficient"),
        (1, "insufficient"),
        (2, "insufficient"),
        (3, "building"),
        (6, "building"),
        (7, "developing"),
        (13, "developing"),
        (14, "established"),
        (30, "established"),
    ],
)
def test_confidence_label_thresholds(count: int, expected_label: str) -> None:
    _pct, label = confidence_from_session_count(count)
    assert label == expected_label


def test_confidence_increases_monotonically_with_session_count() -> None:
    pcts = [confidence_from_session_count(n)[0] for n in range(0, ESTABLISHED_SESSION_COUNT + 5)]
    assert pcts == sorted(pcts)


def test_confidence_caps_at_100_percent() -> None:
    pct, label = confidence_from_session_count(ESTABLISHED_SESSION_COUNT)
    assert pct == 100.0
    assert label == "established"
    # Well past the threshold, still capped, never above 100.
    pct_over, _ = confidence_from_session_count(1000)
    assert pct_over == 100.0


# --- detect_anomaly ---


def test_insufficient_samples_returns_none_not_false() -> None:
    """Below MIN_SAMPLES_FOR_ANOMALY_DETECTION, the answer is "can't tell yet", which must be
    represented as None -- not silently treated as "not an anomaly"."""
    few_samples = dated([220.0, 221.0])
    assert len(few_samples) < MIN_SAMPLES_FOR_ANOMALY_DETECTION
    stats = compute_baseline_stats("f0_mean_hz", few_samples)
    assert detect_anomaly("f0_mean_hz", 300.0, stats) is None


def test_value_close_to_baseline_is_not_flagged() -> None:
    stats = compute_baseline_stats(
        "f0_mean_hz", dated([218.5, 219.8, 220.2, 219.1, 220.9, 221.3])
    )
    result = detect_anomaly("f0_mean_hz", 220.0, stats)
    assert result is not None
    assert result.is_anomaly is False


def test_large_deviation_is_flagged() -> None:
    stats = compute_baseline_stats(
        "f0_mean_hz", dated([218.5, 219.8, 220.2, 219.1, 220.9, 221.3])
    )
    result = detect_anomaly("f0_mean_hz", 260.0, stats)
    assert result is not None
    assert result.is_anomaly is True
    assert result.modified_z_score > 3.5


def test_zero_mad_baseline_flags_any_deviation() -> None:
    """Documented edge case: if a user's historical values have literally zero spread (every
    prior session landed on the exact same value), MAD is 0 and any measurable difference is
    technically "infinite" in z-score terms. Flagged as an anomaly by design, not a bug --
    real acoustic measurements essentially never have exactly zero MAD (natural biological
    variation), so this mostly matters for degenerate/synthetic input."""
    stats = compute_baseline_stats("f0_mean_hz", dated([220.0] * 6))
    assert stats.mad_value == 0.0

    same_value = detect_anomaly("f0_mean_hz", 220.0, stats)
    assert same_value.is_anomaly is False

    different_value = detect_anomaly("f0_mean_hz", 220.5, stats)
    assert different_value.is_anomaly is True
    assert different_value.modified_z_score == float("inf")
