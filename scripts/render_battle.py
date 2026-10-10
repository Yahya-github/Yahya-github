"""Battle scene: replays the last community turn from game/state.json on an 8s loop.

Showdown damp-cave background, Mega Sableye's animated back sprite vs a wild Caterpie.
Sequence: lunge -> Caterpie flickers -> HP drops in steps (green/yellow/red) -> faint and
respawn on a KO. The text box cycles through the turn's battle text.
"""
from __future__ import annotations

import json
import textwrap

from scripts.battle import MOVES
from scripts.common import ROOT, PALETTES, THEMES, esc, font_face, hp_color, sprite_uri, write_asset

W, H, ARENA_H = 860, 432, 300
BAR_W = 150
CYCLE = 8  # seconds
SABLEYE_PATH = ROOT / "game" / "sableye.json"
WRAP = 24  # characters per text-box line in the pixel font


def _sableye() -> dict:
    if SABLEYE_PATH.exists():
        return json.loads(SABLEYE_PATH.read_text())
    return {"level": 1, "xp": 0.0}


def _messages(state: dict) -> list[list[str]]:
    lines = state["last"]["lines"] or ["A wild CATERPIE appeared!"]
    msgs = [textwrap.wrap(line.upper(), WRAP)[:2] for line in lines]
    return msgs + [["WHAT WILL", "YAHYA DO?"]]


def _text_keyframes(n: int) -> str:
    out = []
    for i in range(n):
        a, b = i / n * 100, (i + 1) / n * 100
        frames = [f"0%{{opacity:{1 if i == 0 else 0}}}"]
        if i:
            frames.append(f"{a - .01:.2f}%{{opacity:0}}")
        frames.append(f"{a:.2f}%{{opacity:1}}")
        frames.append(f"{b - .01:.2f}%{{opacity:1}}")
        if i < n - 1:
            frames.append(f"{b:.2f}%{{opacity:0}}100%{{opacity:0}}")
        else:
            frames.append("100%{opacity:1}")
        out.append(f"@keyframes m{i}{{{''.join(frames)}}}")
    return "".join(out)


def _hp_box(x: int, y: int, name: str, level: int, type_icon: str | None, extra: str, w: int = 250) -> str:
    icon = (f'<image href="{sprite_uri(type_icon)}" x="{x + 18 + len(name) * 10 + 6}" y="{y + 11}" '
            f'width="32" height="14" class="px"/>') if type_icon else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{62 if not extra else 80}" rx="6" class="box"/>'
            f'<text x="{x + 14}" y="{y + 24}" class="px10">{esc(name)}</text>{icon}'
            f'<text x="{x + w - 14}" y="{y + 24}" class="px10" text-anchor="end">Lv{level}</text>'
            f'<rect x="{x + 14}" y="{y + 36}" width="26" height="14" rx="3" class="hplbl"/>'
            f'<text x="{x + 27}" y="{y + 46.5}" class="px8 gold" text-anchor="middle">HP</text>'
            f'<rect x="{x + 46}" y="{y + 37}" width="{BAR_W + 4}" height="12" rx="6" class="track"/>' + extra)


def render(theme: str, state: dict) -> str:
    p = PALETTES[theme]
    last, foe_max = state["last"], state["foe_max"]
    before, after = last["hp_before"], last["hp_after"]
    attacked = last["trainer"] is not None
    ko = bool(last["ko"])
    msgs = _messages(state)
    sab = _sableye()

    glyphs = "".join("".join(m) for m in msgs) + "CATERPIESABLEYELv0123456789HP/" + "".join(
        f"{m.name}PP {m.pp}/{m.pp}" for m in MOVES.values())
    font = font_face("Pixel", "PressStart2P-Regular.ttf", glyphs)

    bw = lambda hp: BAR_W * hp / foe_max  # noqa: E731
    hp_anim = (f"@keyframes foehp{{0%,18%{{width:{bw(before):.1f}px;fill:{hp_color(before, foe_max)}}}"
               f"26%,{'86' if ko else '100'}%{{width:{bw(after):.1f}px;fill:{hp_color(after, foe_max)}}}"
               + (f"94%,100%{{width:{BAR_W}px;fill:{hp_color(foe_max, foe_max)}}}" if ko else "") + "}")
    foe_anim = ("@keyframes foe{0%,15%,25%,100%{opacity:1;transform:none}16%,18%,20%,22%{opacity:.15;transform:translateX(4px)}"
                "17%,19%,21%{opacity:1;transform:translateX(-4px)}"
                + ("30%{opacity:1;transform:none}40%,86%{opacity:0;transform:translateY(40px)}94%{opacity:1;transform:none}" if ko else "")
                + "}")
    msg_css = _text_keyframes(len(msgs)) + "".join(
        f".m{i}{{animation:m{i} {CYCLE}s steps(1,end) infinite}}" for i in range(len(msgs)))

    text_box = "".join(
        f'<g class="m{i}">' + "".join(f'<text x="22" y="{ARENA_H + 50 + j * 26}" class="px11">{esc(t)}</text>'
                                      for j, t in enumerate(m)) + "</g>" for i, m in enumerate(msgs))
    moves = []
    for i, move in enumerate(MOVES.values()):
        mx, my = 348 + (i % 2) * 256, ARENA_H + 8 + (i // 2) * 62
        moves.append(f'<rect x="{mx}" y="{my}" width="252" height="58" rx="4" class="move"/>'
                     f'<image href="{sprite_uri("type-" + move.type + ".png")}" x="{mx + 14}" y="{my + 19}" width="48" height="21" class="px"/>'
                     f'<text x="{mx + 74}" y="{my + 28}" class="px10">{move.name}</text>'
                     f'<text x="{mx + 74}" y="{my + 45}" class="px8 dim">PP {move.pp}/{move.pp}</text>')

    xp_w = (BAR_W + 4) * max(0.0, min(float(sab["xp"]), 1.0))
    player_extra = (f'<rect x="{594 + 48}" y="{208 + 39}" width="{BAR_W}" height="8" rx="4" fill="#3FD45A"/>'
                    f'<text x="{594 + 236}" y="{208 + 64}" class="px8" text-anchor="end">50/50</text>'
                    f'<rect x="{594 + 46}" y="{208 + 70}" width="{BAR_W + 4}" height="4" rx="2" class="track"/>'
                    f'<rect x="{594 + 46}" y="{208 + 70}" width="{xp_w:.1f}" height="4" rx="2" fill="#4AA8F0"/>')
    label = f"Battle: Mega Sableye vs wild Caterpie, Caterpie HP {state['foe_hp']}/{foe_max}. " + " ".join(
        " ".join(m) for m in msgs)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}">
<style>{font}
.px10{{font:10px Pixel,monospace;fill:{p["txt"]}}} .px8{{font:8px Pixel,monospace;fill:{p["txt"]}}}
.px11{{font:11px Pixel,monospace;fill:{p["txt"]}}} .gold{{fill:{p["gold"]}}} .dim{{fill:{p["dim"]}}}
.box{{fill:{p["box"]};fill-opacity:.94;stroke:{p["box_ink"]};stroke-width:3}}
.hplbl,.track{{fill:{p["box_ink"]}}}
.move{{fill:{p["cave2"]}}}
.px{{image-rendering:pixelated}}
{hp_anim}{foe_anim}{msg_css}
.foehp{{animation:foehp {CYCLE}s steps(1,end) infinite}}
.foe{{animation:foe {CYCLE}s linear infinite}}
.lunge{{animation:lunge {CYCLE}s ease-in-out infinite}}
@keyframes lunge{{0%,12%,18%,100%{{transform:none}}15%{{transform:translate(16px,-8px)}}}}
@media (prefers-reduced-motion:reduce){{.foehp,.foe,.lunge{{animation:none}}}}
</style>
<defs><clipPath id="arena"><rect width="{W}" height="{ARENA_H}" rx="10"/></clipPath></defs>
<rect width="{W}" height="{H}" rx="10" fill="{p["box_ink"]}"/>
<g clip-path="url(#arena)">
  <image href="{sprite_uri(p["bg"])}" width="{W}" height="{ARENA_H}" preserveAspectRatio="xMidYMid slice"/>
  <rect width="{W}" height="{ARENA_H}" fill="{p["tint"]}" opacity="{p["tint_alpha"]}" style="mix-blend-mode:multiply"/>
  <ellipse cx="640" cy="182" rx="92" ry="18" fill="{p["body_d"]}" opacity=".6"/>
  <ellipse cx="210" cy="296" rx="140" ry="28" fill="{p["body_d"]}" opacity=".6"/>
  <g class="foe"><image href="{sprite_uri(p["foe"])}" x="585" y="78" width="110" height="108" class="px"/></g>
  <g class="{"lunge" if attacked else ""}"><image href="{sprite_uri(p["back"])}" x="95" y="94" width="231" height="216" class="px"/></g>
  {_hp_box(16, 16, "CATERPIE", 5, "type-bug.png", "")}
  <rect x="{16 + 48}" y="{16 + 39}" width="{bw(state["foe_hp"]):.1f}" height="8" rx="4" class="foehp" fill="{hp_color(state["foe_hp"], foe_max)}"/>
  {_hp_box(594, 208, "SABLEYE", int(sab["level"]), None, player_extra)}
</g>
<rect x="4" y="{ARENA_H + 4}" width="338" height="{H - ARENA_H - 8}" rx="6" fill="{p["box"]}"/>
{text_box}
{"".join(moves)}
</svg>'''


def render_battle(state: dict) -> None:
    for theme in THEMES:
        write_asset(f"battle-{theme}.svg", render(theme, state))
