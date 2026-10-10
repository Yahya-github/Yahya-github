"""Daily build: fetch live stats, then regenerate every generated asset in assets/.

    PROFILE_TOKEN=... python -m scripts.build

Run by .github/workflows/profile.yml on a schedule. Safe to run locally with `gh auth token`.
"""
from __future__ import annotations

import json
import sys

from scripts.battle import load_state
from scripts.common import load_profile
from scripts.github_data import fetch_stats, token_from_env
from scripts.render_badges import render_badges
from scripts.render_battle import SABLEYE_PATH, render_battle
from scripts.render_cards import render_cards
from scripts.render_terminal import render_terminal


def main() -> int:
    profile = load_profile()
    langs = profile["languages"]
    stats = fetch_stats(
        profile["login"], token_from_env(), set(langs["ignore"]), langs["top"], frozenset(langs["exclude_repos"])
    )
    lvl = stats.level
    xp = 1.0 if lvl >= 100 else (stats.total_contributions - lvl ** 2) / ((lvl + 1) ** 2 - lvl ** 2)
    SABLEYE_PATH.parent.mkdir(exist_ok=True)
    SABLEYE_PATH.write_text(json.dumps({"level": lvl, "xp": round(xp, 3)}) + "\n")

    render_terminal(stats)
    render_cards(stats)
    render_badges()
    render_battle(load_state())
    print(f"Built assets for {stats.login}: {stats.total_contributions} contributions, "
          f"{stats.streaks.current}-day streak, level {lvl}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
