"""Fetch profile numbers from the GitHub GraphQL API and reduce them to display stats.

Network code lives in `fetch_stats`; everything it calls afterwards is pure and tested.
With a token that can see private repos (PROFILE_TOKEN), private contributions and
languages are included, which is why the hosted stat cards undercount.
"""
from __future__ import annotations

import json
import math
import os
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Sequence

API = "https://api.github.com/graphql"
MAX_LEVEL = 100


@dataclass(frozen=True)
class Streaks:
    current: int
    current_start: date | None
    current_end: date | None
    longest: int
    longest_start: date | None
    longest_end: date | None


@dataclass(frozen=True)
class Language:
    name: str
    pct: float
    color: str


@dataclass(frozen=True)
class Stats:
    login: str
    total_contributions: int
    since: date
    commits: int
    pull_requests: int
    issues: int
    reviews: int
    repos_contributed: int
    streaks: Streaks
    languages: tuple[Language, ...]
    level: int


def compute_streaks(calendar: Sequence[tuple[date, int]], today: date) -> Streaks:
    """Current and longest daily streaks. An empty `today` does not break the current streak."""
    active = [(d, c) for d, c in sorted(calendar) if d <= today]
    longest, l_start, l_end = 0, None, None
    run, run_start = 0, None
    for d, count in active:
        if count > 0:
            run_start = d if run == 0 else run_start
            run += 1
            if run > longest:
                longest, l_start, l_end = run, run_start, d
        else:
            run = 0

    current, c_start, c_end = 0, None, None
    by_day = dict(active)
    cursor = today if by_day.get(today, 0) > 0 else today - timedelta(days=1)
    while by_day.get(cursor, 0) > 0:
        current += 1
        c_end = c_end or cursor
        c_start = cursor
        cursor -= timedelta(days=1)
    return Streaks(current, c_start, c_end, longest, l_start, l_end)


def language_shares(
    repos: Iterable[Sequence[tuple[str, int, str]]], ignore: set[str], top: int
) -> list[Language]:
    """Byte share per language across repos, after dropping ignored (non-skill) languages."""
    sizes: dict[str, int] = defaultdict(int)
    colors: dict[str, str] = {}
    for repo in repos:
        for name, size, color in repo:
            if name in ignore:
                continue
            sizes[name] += size
            colors[name] = color or "#888888"
    total = sum(sizes.values())
    if total == 0:
        return []
    ranked = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:top]
    return [Language(name, size / total * 100, colors[name]) for name, size in ranked]


def compute_level(total_contributions: int) -> int:
    """Sableye's level: square root curve, so early contributions level fastest. Capped at 100."""
    return max(1, min(MAX_LEVEL, math.isqrt(max(total_contributions, 0))))


# ---------------------------------------------------------------- network

YEAR_QUERY = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      totalCommitContributions restrictedContributionsCount
      totalPullRequestContributions totalIssueContributions totalPullRequestReviewContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } }
    }
  }
}"""

PROFILE_QUERY = """
query($login:String!){
  user(login:$login){
    createdAt
    repositories(ownerAffiliations:OWNER,first:100){
      nodes{ name languages(first:10,orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name color } } } }
    }
  }
}"""


def graphql(query: str, variables: dict, token: str) -> dict:
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "sablenite-profile"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {payload['errors'][0].get('message')}")
    return payload["data"]


def _year_windows(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    windows, cursor = [], start
    while cursor < end:
        nxt = min(cursor.replace(year=cursor.year + 1), end)
        windows.append((cursor, nxt))
        cursor = nxt
    return windows


def fetch_stats(
    login: str, token: str, ignore: set[str], top: int, exclude_repos: frozenset[str] = frozenset()
) -> Stats:
    """Team projects are forks into this account, so forks count unless listed in `exclude_repos`."""
    profile = graphql(PROFILE_QUERY, {"login": login}, token)["user"]
    created = datetime.fromisoformat(profile["createdAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)

    calendar: list[tuple[date, int]] = []
    totals = defaultdict(int)
    for start, end in _year_windows(created, now):
        col = graphql(YEAR_QUERY, {"login": login, "from": start.isoformat(), "to": end.isoformat()}, token)
        col = col["user"]["contributionsCollection"]
        totals["contribs"] += col["contributionCalendar"]["totalContributions"]
        totals["commits"] += col["totalCommitContributions"] + col["restrictedContributionsCount"]
        totals["prs"] += col["totalPullRequestContributions"]
        totals["issues"] += col["totalIssueContributions"]
        totals["reviews"] += col["totalPullRequestReviewContributions"]
        totals["repos"] = max(totals["repos"], col["totalRepositoriesWithContributedCommits"])
        for week in col["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                calendar.append((date.fromisoformat(day["date"]), day["contributionCount"]))

    repos = [
        [(e["node"]["name"], e["size"], e["node"]["color"]) for e in node["languages"]["edges"]]
        for node in profile["repositories"]["nodes"]
        if node["name"] not in exclude_repos
    ]
    # Overlapping window edges can repeat a day; keep the max count per day.
    merged: dict[date, int] = {}
    for d, c in calendar:
        merged[d] = max(c, merged.get(d, 0))

    return Stats(
        login=login,
        total_contributions=totals["contribs"],
        since=created.date(),
        commits=totals["commits"],
        pull_requests=totals["prs"],
        issues=totals["issues"],
        reviews=totals["reviews"],
        repos_contributed=totals["repos"],
        streaks=compute_streaks(list(merged.items()), today=now.date()),
        languages=tuple(language_shares(repos, ignore=ignore, top=top)),
        level=compute_level(totals["contribs"]),
    )


def token_from_env() -> str:
    token = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("Set PROFILE_TOKEN (or GITHUB_TOKEN) to query the GitHub API.")
    return token
