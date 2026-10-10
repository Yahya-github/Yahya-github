"""Rendered SVGs must survive GitHub's <img> sandbox: well-formed, self-contained, small."""
import random
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

import pytest

from scripts.battle import TurnResult, initial_state, play_turn
from scripts.github_data import Language, Stats, Streaks
from scripts import render_badges, render_battle, render_cards, render_terminal

MAX_BYTES = 200_000
STATS = Stats(
    login="octocat", total_contributions=1412, since=date(2024, 9, 6), commits=1386, pull_requests=16,
    issues=1, reviews=0, repos_contributed=7,
    streaks=Streaks(102, date(2026, 6, 30), date(2026, 10, 9), 102, date(2026, 6, 30), date(2026, 10, 9)),
    languages=(Language("Python", 43.4, "#3572A5"), Language("C++", 11.8, "#f34b7d")), level=37,
)


def ko_state() -> dict:
    rules = lambda m, hp, mx, rng: TurnResult(damage=hp, lines=(f"SABLEYE used {m.name}!",))  # noqa: E731
    s, _ = play_turn({**initial_state(), "foe_hp": 30}, "battle|foul-play", "ash",
                     datetime(2026, 10, 9, tzinfo=timezone.utc), random.Random(0), rules=rules)
    return s


RENDERS = {
    "terminal": lambda t: render_terminal.render(t, STATS, today=date(2026, 10, 9)),
    "stats": lambda t: render_cards.render(t, STATS),
    "badges": lambda t: render_badges.render(t),
    "battle-idle": lambda t: render_battle.render(t, initial_state()),
    "battle-ko": lambda t: render_battle.render(t, ko_state()),
}


@pytest.fixture(scope="module", params=[(n, t) for n in RENDERS for t in ("dark", "light")], ids=lambda p: f"{p[0]}-{p[1]}")
def svg(request):
    name, theme = request.param
    return RENDERS[name](theme)


def test_is_well_formed_svg(svg):
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert root.get("role") == "img" and root.get("aria-label")


def test_has_no_external_references(svg):
    # GitHub's image proxy blocks every external fetch from inside an SVG.
    refs = re.findall(r'(?:href|src)="([^"]+)"|url\((?!#)([^)]+)\)', svg)
    for href, url in refs:
        ref = href or url
        assert ref.startswith("data:"), f"external reference: {ref[:60]}"


def test_has_no_script(svg):
    assert "<script" not in svg.lower()


def test_stays_small(svg):
    assert len(svg.encode()) < MAX_BYTES


def test_respects_reduced_motion(svg):
    assert "prefers-reduced-motion" in svg


def test_ko_battle_animates_faint_and_respawn():
    out = render_battle.render("dark", ko_state())
    assert "translateY(40px)" in out           # faint slide
    assert "FAINTED" in out
    assert "width:0.0px" in out                 # HP bar empties before respawning
