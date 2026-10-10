import random
from datetime import datetime, timedelta, timezone

import pytest

from scripts.battle import (
    MOVES,
    RateLimited,
    TurnResult,
    initial_state,
    parse_title,
    play_turn,
    update_readme,
)

NOW = datetime(2026, 10, 9, 21, 0, tzinfo=timezone.utc)


def fixed(damage: int, *lines: str):
    """Stand-in for the user's apply_move: always deals `damage`."""
    return lambda move, foe_hp, foe_max, rng: TurnResult(damage=damage, lines=lines or (f"{move.name}!",))


class TestParseTitle:
    @pytest.mark.parametrize("title,move", [
        ("battle|foul-play", "foul-play"),
        ("battle|KNOCK-OFF", "knock-off"),
        ("  battle|recover  ", "recover"),
    ])
    def test_valid(self, title, move):
        assert parse_title(title).id == move

    @pytest.mark.parametrize("title", ["battle|hyper-beam", "foul-play", "battle|", "battle|foul-play; rm -rf /", ""])
    def test_rejects_anything_not_whitelisted(self, title):
        with pytest.raises(ValueError):
            parse_title(title)


class TestPlayTurn:
    def test_damage_reduces_hp_and_records_trainer(self):
        state, comment = play_turn(initial_state(), "battle|foul-play", "ash", NOW, random.Random(1), rules=fixed(30))
        assert state["foe_hp"] == 70
        assert state["leaderboard"]["ash"] == {"kos": 0, "damage": 30}
        assert state["log"][-1]["move"] == "foul-play"
        assert state["last"]["hp_before"] == 100 and state["last"]["hp_after"] == 70
        assert "ash" in comment

    def test_does_not_mutate_input_state(self):
        before = initial_state()
        snapshot = repr(before)
        play_turn(before, "battle|foul-play", "ash", NOW, random.Random(1), rules=fixed(30))
        assert repr(before) == snapshot

    def test_knockout_credits_trainer_and_spawns_new_caterpie(self):
        s = {**initial_state(), "foe_hp": 10}
        state, comment = play_turn(s, "battle|knock-off", "misty", NOW, random.Random(1), rules=fixed(25))
        assert state["last"]["ko"] is True
        assert state["last"]["hp_after"] == 0
        assert state["foe_hp"] == state["foe_max"]
        assert state["leaderboard"]["misty"]["kos"] == 1
        assert state["leaderboard"]["misty"]["damage"] == 10  # only the HP that was left
        assert "fainted" in comment.lower()

    def test_damage_is_clamped_to_valid_range(self):
        state, _ = play_turn(initial_state(), "battle|recover", "ash", NOW, random.Random(1), rules=fixed(-50))
        assert state["foe_hp"] == 100

    def test_rate_limit_one_move_per_trainer_per_minute(self):
        s, _ = play_turn(initial_state(), "battle|foul-play", "ash", NOW, random.Random(1), rules=fixed(5))
        with pytest.raises(RateLimited):
            play_turn(s, "battle|foul-play", "ash", NOW + timedelta(seconds=30), random.Random(1), rules=fixed(5))
        play_turn(s, "battle|foul-play", "ash", NOW + timedelta(seconds=61), random.Random(1), rules=fixed(5))

    def test_log_keeps_last_ten_turns(self):
        s = initial_state()
        for i in range(15):
            s, _ = play_turn(s, "battle|recover", f"t{i}", NOW, random.Random(1), rules=fixed(0))
        assert len(s["log"]) == 10
        assert s["turn"] == 15


def test_every_move_has_a_type_icon_and_pp():
    for move in MOVES.values():
        assert move.type in {"dark", "fire", "normal"}
        assert move.pp > 0


def test_update_readme_replaces_only_marked_section():
    readme = "intro\n<!--BATTLE:START-->\nold\n<!--BATTLE:END-->\noutro\n"
    s, _ = play_turn(initial_state(), "battle|foul-play", "ash", NOW, random.Random(1), rules=fixed(30))
    out = update_readme(readme, s)
    assert out.startswith("intro\n<!--BATTLE:START-->") and out.endswith("<!--BATTLE:END-->\noutro\n")
    assert "old" not in out
    assert "@ash" in out


def test_update_readme_requires_markers():
    with pytest.raises(ValueError):
        update_readme("no markers here", initial_state())


class FakeRng:
    """Deterministic rng: `rolls` feeds random(), uniform() returns its upper bound * `spread`."""

    def __init__(self, rolls=(0.99,), spread=1.0):
        self.rolls, self.spread, self.i = list(rolls), spread, 0

    def random(self):
        value = self.rolls[min(self.i, len(self.rolls) - 1)]
        self.i += 1
        return value

    def uniform(self, a, b):
        return b * self.spread


class TestApplyMove:
    """The real damage rules (scripts.battle.apply_move)."""

    def run(self, move_id, rng=None, hp=100):
        from scripts.battle import apply_move
        return apply_move(MOVES[move_id], hp, 100, rng or FakeRng())

    def test_every_move_announces_itself(self):
        for move_id, move in MOVES.items():
            assert self.run(move_id).lines[0] == f"SABLEYE used {move.name}!"

    def test_foul_play_is_weak_because_it_uses_caterpies_attack(self):
        assert 0 < self.run("foul-play").damage < self.run("knock-off").damage

    def test_knock_off_hits_harder_when_caterpie_holds_an_item(self):
        no_item = self.run("knock-off", FakeRng(rolls=(0.99, 0.99))).damage
        item = self.run("knock-off", FakeRng(rolls=(0.99, 0.0)))
        assert item.damage > no_item
        assert any("SILVER POWDER" in line for line in item.lines)

    def test_critical_hit_multiplies_damage(self):
        normal = self.run("knock-off", FakeRng(rolls=(0.99, 0.99))).damage
        crit = self.run("knock-off", FakeRng(rolls=(0.0, 0.99)))
        assert crit.damage > normal
        assert "A critical hit!" in crit.lines

    def test_will_o_wisp_burns_for_a_sixteenth(self):
        result = self.run("will-o-wisp")
        assert result.damage == 100 // 16
        assert any("burn" in line.lower() for line in result.lines)

    def test_recover_deals_no_damage(self):
        result = self.run("recover")
        assert result.damage == 0
        assert any("full" in line.lower() for line in result.lines)

    def test_damage_roll_lowers_damage(self):
        assert self.run("foul-play", FakeRng(spread=0.85)).damage <= self.run("foul-play").damage


def test_update_readme_cache_busts_battle_images():
    readme = ('<source srcset="assets/battle-dark.svg"><img src="assets/battle-light.svg?v=3">\n'
              '<!--BATTLE:START--><!--BATTLE:END-->\n<img src="assets/stats-dark.svg">')
    s, _ = play_turn(initial_state(), "battle|foul-play", "ash", NOW, random.Random(1), rules=fixed(30))
    out = update_readme(readme, s)
    assert 'srcset="assets/battle-dark.svg?v=1"' in out
    assert 'src="assets/battle-light.svg?v=1"' in out
    assert 'src="assets/stats-dark.svg"' in out  # other images untouched


def test_exempt_trainer_skips_cooldown():
    s, _ = play_turn(initial_state(), "battle|foul-play", "owner", NOW, random.Random(1), rules=fixed(5))
    play_turn(s, "battle|foul-play", "owner", NOW + timedelta(seconds=5), random.Random(1), rules=fixed(5),
              exempt=frozenset({"owner"}))
