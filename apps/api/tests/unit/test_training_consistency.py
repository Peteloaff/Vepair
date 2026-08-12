from datetime import date, timedelta

from app.training_consistency import compute_streaks

TODAY = date(2026, 8, 12)


def days_ago(n: int) -> date:
    return TODAY - timedelta(days=n)


class TestComputeStreaks:
    def test_no_sessions_ever(self) -> None:
        assert compute_streaks(set(), TODAY) == (0, 0)

    def test_single_session_today(self) -> None:
        assert compute_streaks({TODAY}, TODAY) == (1, 1)

    def test_consecutive_run_ending_today(self) -> None:
        dates = {days_ago(i) for i in range(5)}  # today, yesterday, ..., 4 days ago
        assert compute_streaks(dates, TODAY) == (5, 5)

    def test_consecutive_run_ending_yesterday_still_counts_as_current(self) -> None:
        """Today hasn't happened yet — a streak isn't broken until the day is actually over."""
        dates = {days_ago(i) for i in range(1, 4)}  # yesterday, 2, 3 days ago
        current, longest = compute_streaks(dates, TODAY)
        assert current == 3
        assert longest == 3

    def test_streak_broken_two_days_ago_reports_zero_current(self) -> None:
        dates = {days_ago(i) for i in range(2, 6)}  # 2-5 days ago, nothing yesterday/today
        current, _longest = compute_streaks(dates, TODAY)
        assert current == 0

    def test_longest_streak_reflects_a_gap_in_the_middle(self) -> None:
        """A 3-day run in the past plus today's fresh streak — longest picks the bigger one,
        current only ever reflects the run touching `as_of`."""
        dates = {days_ago(20), days_ago(19), days_ago(18)} | {TODAY, days_ago(1)}
        current, longest = compute_streaks(dates, TODAY)
        assert current == 2
        assert longest == 3

    def test_scattered_non_consecutive_days(self) -> None:
        dates = {days_ago(1), days_ago(5), days_ago(10)}
        current, longest = compute_streaks(dates, TODAY)
        assert current == 1  # yesterday only
        assert longest == 1

    def test_current_never_exceeds_longest(self) -> None:
        dates = {days_ago(i) for i in range(0, 10)}
        current, longest = compute_streaks(dates, TODAY)
        assert current == longest == 10
