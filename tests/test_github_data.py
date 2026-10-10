from datetime import date, timedelta

import pytest

from scripts.github_data import compute_level, compute_streaks, language_shares


def days(start: date, counts: list[int]) -> list[tuple[date, int]]:
    return [(start + timedelta(days=i), c) for i, c in enumerate(counts)]


class TestComputeStreaks:
    def test_current_streak_runs_through_today(self):
        cal = days(date(2026, 10, 1), [0, 3, 1, 2])
        s = compute_streaks(cal, today=date(2026, 10, 4))
        assert (s.current, s.current_start, s.current_end) == (3, date(2026, 10, 2), date(2026, 10, 4))

    def test_empty_today_does_not_break_streak(self):
        # GitHub convention: today is still in progress.
        cal = days(date(2026, 10, 1), [1, 1, 1, 0])
        s = compute_streaks(cal, today=date(2026, 10, 4))
        assert s.current == 3
        assert s.current_end == date(2026, 10, 3)

    def test_gap_before_yesterday_resets_current(self):
        cal = days(date(2026, 10, 1), [5, 5, 0, 0])
        s = compute_streaks(cal, today=date(2026, 10, 4))
        assert s.current == 0

    def test_longest_is_tracked_separately(self):
        cal = days(date(2026, 9, 1), [1, 1, 1, 1, 0, 1, 1])
        s = compute_streaks(cal, today=date(2026, 9, 7))
        assert s.longest == 4
        assert (s.longest_start, s.longest_end) == (date(2026, 9, 1), date(2026, 9, 4))
        assert s.current == 2

    def test_future_days_are_ignored(self):
        cal = days(date(2026, 10, 1), [1, 1, 9])
        s = compute_streaks(cal, today=date(2026, 10, 2))
        assert s.current == 2

    def test_empty_calendar(self):
        s = compute_streaks([], today=date(2026, 10, 2))
        assert (s.current, s.longest) == (0, 0)


class TestLanguageShares:
    REPOS = [
        [("Python", 800, "#3572A5"), ("CSS", 500, "#563d7c")],
        [("Python", 200, "#3572A5"), ("C++", 300, "#f34b7d"), ("HTML", 50, "#e34c26")],
        [("Rust", 100, "#dea584")],
    ]

    def test_ignored_languages_are_removed_before_percentages(self):
        shares = language_shares(self.REPOS, ignore={"CSS", "HTML"}, top=5)
        assert [l.name for l in shares] == ["Python", "C++", "Rust"]
        assert shares[0].pct == pytest.approx(1000 / 1400 * 100)

    def test_top_limits_count(self):
        shares = language_shares(self.REPOS, ignore=set(), top=2)
        assert [l.name for l in shares] == ["Python", "CSS"]

    def test_no_repos(self):
        assert language_shares([], ignore=set(), top=5) == []


class TestComputeLevel:
    @pytest.mark.parametrize("contribs,level", [(0, 1), (1, 1), (100, 10), (1399, 37), (10**6, 100)])
    def test_level_curve(self, contribs, level):
        assert compute_level(contribs) == level
