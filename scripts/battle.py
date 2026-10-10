"""Issue-driven battle: visitors open an issue titled `battle|<move>`, an Action plays the turn.

Flow (see .github/workflows/battle.yml):
    ISSUE_TITLE/ISSUE_AUTHOR env -> play_turn() -> game/state.json, assets/battle-*.svg,
    README leaderboard section, and a comment body in game/comment.md.

Only the four whitelisted moves are accepted. The issue title is never executed or
interpolated into a shell; it is only matched against MOVES.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from scripts.common import ROOT

STATE_PATH = ROOT / "game" / "state.json"
COMMENT_PATH = ROOT / "game" / "comment.md"
README_PATH = ROOT / "README.md"
START, END = "<!--BATTLE:START-->", "<!--BATTLE:END-->"
COOLDOWN = timedelta(seconds=60)
LOG_SIZE = 10
FOE_MAX_HP = 100
TITLE_RE = re.compile(r"^battle\|([a-z-]+)$")

# Damage tuning: base Attack stats (Caterpie 30, Mega Sableye 85), Gen 6+ crit odds.
CATERPIE_ATK, SABLEYE_ATK = 30, 85
CRIT_CHANCE = 1 / 24
ITEM_CHANCE = 1 / 4
DAMAGE_SCALE = 0.5  # Knock Off lands ~3 hits to KO a 100 HP Caterpie, Foul Play ~7


@dataclass(frozen=True)
class Move:
    id: str
    name: str
    type: str      # matches sprites/type-<type>.png
    power: int     # 0 for status moves
    pp: int


# Mega Sableye's competitive set (Smogon Sablenite sets), Gen 6 PP values.
MOVES: dict[str, Move] = {
    "foul-play": Move("foul-play", "FOUL PLAY", "dark", 95, 15),
    "knock-off": Move("knock-off", "KNOCK OFF", "dark", 65, 20),
    "will-o-wisp": Move("will-o-wisp", "WILL-O-WISP", "fire", 0, 15),
    "recover": Move("recover", "RECOVER", "normal", 0, 10),
}


@dataclass(frozen=True)
class TurnResult:
    damage: int                 # HP removed from Caterpie (engine clamps to [0, foe_hp])
    lines: tuple[str, ...]      # battle text, e.g. ("SABLEYE used FOUL PLAY!", "It's super effective!")


class RateLimited(Exception):
    pass


Rules = Callable[[Move, int, int, random.Random], TurnResult]


def apply_move(move: Move, foe_hp: int, foe_max: int, rng: random.Random) -> TurnResult:
    """How much damage each move deals to the wild Caterpie (max 100 HP), following the games.

    - Foul Play uses the *target's* Attack: Caterpie's base 30 vs Sableye's 85, so it's weak.
    - Knock Off: 1.5x when the target holds an item (1 in 4 wild Caterpie carry Silver Powder).
    - Will-O-Wisp: no direct damage, the burn chips 1/16 of max HP.
    - Recover: Sableye is already at full HP, so nothing happens.
    Damaging moves roll 85-100% damage and crit 1 in 24 for 1.5x.
    The engine clamps damage, handles knockouts, the leaderboard and respawning.
    """
    lines = [f"SABLEYE used {move.name}!"]
    if move.id == "recover":
        return TurnResult(0, (*lines, "But SABLEYE's HP is already full!"))
    if move.id == "will-o-wisp":
        return TurnResult(foe_max // 16, (*lines, "CATERPIE was burned!", "CATERPIE is hurt by its burn!"))

    attack_ratio = CATERPIE_ATK / SABLEYE_ATK if move.id == "foul-play" else 1.0
    crit = rng.random() < CRIT_CHANCE
    held_item = move.id == "knock-off" and rng.random() < ITEM_CHANCE
    damage = move.power * DAMAGE_SCALE * attack_ratio * rng.uniform(0.85, 1.0)
    damage *= (1.5 if crit else 1.0) * (1.5 if held_item else 1.0)
    if move.id == "foul-play":
        lines.append("CATERPIE's own Attack was used against it!")
    if held_item:
        lines.append("SABLEYE knocked off CATERPIE's SILVER POWDER!")
    if crit:
        lines.append("A critical hit!")
    return TurnResult(max(1, round(damage)), tuple(lines))


def initial_state() -> dict:
    return {
        "foe_hp": FOE_MAX_HP, "foe_max": FOE_MAX_HP, "turn": 0, "kos": 0,
        "log": [], "leaderboard": {}, "last_move_at": {},
        "last": {"trainer": None, "move": None, "hp_before": FOE_MAX_HP, "hp_after": FOE_MAX_HP,
                 "ko": False, "lines": ["A wild CATERPIE appeared!"]},
    }


def parse_title(title: str) -> Move:
    match = TITLE_RE.match(title.strip().lower())
    if not match or match.group(1) not in MOVES:
        raise ValueError(f"Unknown move. Use one of: {', '.join(MOVES)}")
    return MOVES[match.group(1)]


def play_turn(
    state: dict, title: str, trainer: str, now: datetime, rng: random.Random, rules: Rules = apply_move
) -> tuple[dict, str]:
    """Return (new_state, comment). Never mutates `state`."""
    move = parse_title(title)
    last = state["last_move_at"].get(trainer)
    if last and now - datetime.fromisoformat(last) < COOLDOWN:
        raise RateLimited(f"@{trainer}, Sableye needs a minute to recover. Try again shortly.")

    hp_before = state["foe_hp"]
    result = rules(move, hp_before, state["foe_max"], rng)
    damage = max(0, min(hp_before, int(result.damage)))
    hp_after = hp_before - damage
    ko = hp_after == 0
    lines = list(result.lines) + (["The wild CATERPIE fainted!", f"@{trainer} gets the KO!"] if ko else [])

    prev = state["leaderboard"].get(trainer, {"kos": 0, "damage": 0})
    entry = {"turn": state["turn"] + 1, "trainer": trainer, "move": move.id, "damage": damage,
             "at": now.isoformat()}
    new_state = {
        **state,
        "turn": state["turn"] + 1,
        "kos": state.get("kos", 0) + int(ko),
        "foe_hp": state["foe_max"] if ko else hp_after,
        "log": [*state["log"], entry][-LOG_SIZE:],
        "leaderboard": {**state["leaderboard"],
                        trainer: {"kos": prev["kos"] + int(ko), "damage": prev["damage"] + damage}},
        "last_move_at": {**state["last_move_at"], trainer: now.isoformat()},
        "last": {"trainer": trainer, "move": move.id, "hp_before": hp_before, "hp_after": hp_after,
                 "ko": ko, "lines": lines},
    }
    comment = "\n".join([f"**@{trainer}** used **{move.name}**!", "", *[f"> {line}" for line in lines], "",
                         f"Caterpie HP: {new_state['foe_hp']}/{state['foe_max']}. "
                         "[Back to the battle](https://github.com/Yahya-github)"])
    return new_state, comment


def update_readme(readme: str, state: dict) -> str:
    if START not in readme or END not in readme:
        raise ValueError("README is missing the BATTLE markers.")
    recent = list(reversed(state["log"][-5:]))
    board = sorted(state["leaderboard"].items(), key=lambda kv: (-kv[1]["kos"], -kv[1]["damage"]))[:5]
    rows = ["", "<table><tr><td valign=\"top\">", "", "**Last moves**", "",
            "| Trainer | Move | Damage |", "|:--|:--|--:|"]
    rows += [f"| [@{e['trainer']}](https://github.com/{e['trainer']}) | {MOVES[e['move']].name.title()} "
             f"| {e['damage']} |" for e in recent] or ["| No moves yet | Be the first! | |"]
    rows += ["", "</td><td valign=\"top\">", "", "**Top trainers**", "", "| Trainer | KOs | Damage |",
             "|:--|--:|--:|"]
    rows += [f"| [@{name}](https://github.com/{name}) | {s['kos']} | {s['damage']} |" for name, s in board] \
        or ["| Nobody yet | | |"]
    rows += ["", "</td></tr></table>", ""]
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    return head + START + "\n".join(rows) + END + tail


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else initial_state()


def main() -> int:
    from scripts.render_battle import render_battle  # local import keeps tests light

    title, trainer = os.environ.get("ISSUE_TITLE", ""), os.environ.get("ISSUE_AUTHOR", "")
    if not trainer:
        print("ISSUE_AUTHOR is required", file=sys.stderr)
        return 2
    try:
        state, comment = play_turn(load_state(), title, trainer, datetime.now(timezone.utc), random.Random())
    except (ValueError, RateLimited) as err:
        COMMENT_PATH.write_text(str(err))
        return 1
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")
    README_PATH.write_text(update_readme(README_PATH.read_text(), state))
    render_battle(state)
    COMMENT_PATH.write_text(comment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
