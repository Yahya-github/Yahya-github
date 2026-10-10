"""Network and CLI paths, with the GitHub API and file locations stubbed out."""
from datetime import date

import pytest

from scripts import battle, github_data


def fake_graphql(query, variables, token):
    if "createdAt" in query:
        return {"user": {"createdAt": "2025-10-01T00:00:00Z", "repositories": {"nodes": [
            {"name": "facturo", "languages": {"edges": [{"size": 900, "node": {"name": "Python", "color": "#3572A5"}},
                                                         {"size": 300, "node": {"name": "CSS", "color": "#563d7c"}}]}},
            {"name": "showdex", "languages": {"edges": [{"size": 9999, "node": {"name": "TypeScript", "color": "#3178c6"}}]}},
        ]}}}
    return {"user": {"contributionsCollection": {
        "totalCommitContributions": 10, "restrictedContributionsCount": 5, "totalPullRequestContributions": 2,
        "totalIssueContributions": 1, "totalPullRequestReviewContributions": 0,
        "totalRepositoriesWithContributedCommits": 3,
        "contributionCalendar": {"totalContributions": 18, "weeks": [{"contributionDays": [
            {"date": "2026-01-01", "contributionCount": 4}, {"date": "2026-01-02", "contributionCount": 0}]}]},
    }}}


def test_fetch_stats_sums_years_and_skips_excluded_forks(monkeypatch):
    monkeypatch.setattr(github_data, "graphql", fake_graphql)
    s = github_data.fetch_stats("octocat", "token", ignore={"CSS"}, top=4, exclude_repos=frozenset({"showdex"}))
    assert s.since == date(2025, 10, 1)
    assert s.commits % 15 == 0 and s.commits >= 15           # public + private, per yearly window
    assert [l.name for l in s.languages] == ["Python"]        # CSS ignored, showdex excluded
    assert s.streaks.longest == 1


def test_token_from_env_requires_a_token(monkeypatch):
    for var in ("PROFILE_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(SystemExit):
        github_data.token_from_env()
    monkeypatch.setenv("GITHUB_TOKEN", "abc")
    assert github_data.token_from_env() == "abc"


@pytest.fixture
def game_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(battle, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(battle, "COMMENT_PATH", tmp_path / "comment.md")
    monkeypatch.setattr(battle, "README_PATH", tmp_path / "README.md")
    return tmp_path


def test_cli_rejects_unknown_move_with_a_comment(game_dir, monkeypatch):
    monkeypatch.setenv("ISSUE_TITLE", "battle|hyper-beam")
    monkeypatch.setenv("ISSUE_AUTHOR", "ash")
    assert battle.main() == 1
    assert "Unknown move" in (game_dir / "comment.md").read_text()
    assert not (game_dir / "state.json").exists()


def test_cli_requires_author(game_dir, monkeypatch):
    monkeypatch.setenv("ISSUE_TITLE", "battle|recover")
    monkeypatch.delenv("ISSUE_AUTHOR", raising=False)
    assert battle.main() == 2


def test_load_state_defaults_when_missing(game_dir):
    assert battle.load_state() == battle.initial_state()
