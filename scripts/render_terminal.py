"""Hero: a neofetch terminal whose logo is a window into Sableye's cave.

Lines type in with a stepped cover that slides off each line, the Showdown sprite idles
inside the cave, and the caret blinks. Live lines (langs, streak) come from Stats.
"""
from __future__ import annotations

from datetime import date

from scripts.common import PALETTES, THEMES, esc, font_face, load_profile, sprite_uri, write_asset
from scripts.github_data import Stats

W = 860
TEXT_X, KEY_W, TOP, STEP = 276, 78, 78, 24
COVER_W = W - TEXT_X - 16
CHAR_W = 8.1  # JetBrains Mono advance at 13.5px


def terminal_lines(stats: Stats) -> list[tuple[str, str]]:
    t = load_profile()["terminal"]
    langs = " · ".join(l.name for l in stats.languages) or "Python"
    streak = f"{stats.streaks.current}-day streak · {stats.total_contributions:,} contributions"
    return [
        ("role", t["role"]),
        ("type", "@types"),
        ("now", t["now"]),
        ("ability", t["ability"]),
        ("langs", langs),
        ("streak", streak),
        ("speaks", t["speaks"]),
        ("status", t["status"]),
    ]


def _row(key: str, value: str, y: int, host: str) -> str:
    if key == "@prompt":
        return f'<text x="{TEXT_X}" y="{y}"><tspan class="p">{esc(host)}</tspan> ~ $ {esc(value)}</text>'
    if value == "@types":
        x = TEXT_X + KEY_W
        return (f'<text x="{TEXT_X}" y="{y}" class="k">type</text>'
                f'<image href="{sprite_uri("type-dark.png")}" x="{x}" y="{y - 15}" width="48" height="21" class="px"/>'
                f'<image href="{sprite_uri("type-ghost.png")}" x="{x + 54}" y="{y - 15}" width="48" height="21" class="px"/>')
    return (f'<text x="{TEXT_X}" y="{y}"><tspan class="k">{esc(key)}</tspan>'
            f'<tspan x="{TEXT_X + KEY_W}">{esc(value)}</tspan></text>')


def render(theme: str, stats: Stats, today: date | None = None) -> str:
    p = PALETTES[theme]
    host = load_profile()["terminal"]["host"]
    lines = terminal_lines(stats)
    updated = (today or date.today()).isoformat()
    all_rows = [("@prompt", "neofetch --pokemon"), *lines]
    glyphs = host + "~$" + "".join(k + v for k, v in all_rows) + "auto-updated" + updated + ":/cave"
    font = font_face("Mono", "JetBrainsMono.ttf", glyphs, weight=500)

    rows, covers = [], []
    for i, (key, value) in enumerate(all_rows):
        y = TOP + i * STEP
        rows.append(_row(key, value, y, host))
        covers.append(f'<rect class="cover" x="{TEXT_X - 2}" y="{y - 17}" width="{COVER_W}" height="{STEP}" '
                      f'style="animation-delay:{0.2 + i * 0.32:.2f}s"/>')

    block_colors = [p[k] for k in ("cave2", "body_d", "body", "body_l", "gem_d", "gem", "gem_l", "gold")]
    by = TOP + len(all_rows) * STEP - 8
    blocks = "".join(f'<rect x="{TEXT_X + i * 24}" y="{by}" width="24" height="14" fill="{c}"/>'
                     for i, c in enumerate(block_colors))
    py = by + 38
    H = py + 22
    label = ", ".join(f"{k}: {v}" for k, v in lines if v != "@types")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(host)} terminal. type: Dark/Ghost, {esc(label)}">
<style>{font}
text{{font-family:Mono,ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13.5px;fill:{p["txt"]}}}
.k{{fill:{p["gem_l"]}}} .p{{fill:{p["gold"]}}} .dim{{fill:{p["dim"]};font-size:11px}}
.px{{image-rendering:pixelated}}
.cover{{fill:{p["cave"]};animation:reveal .55s steps(30,end) both}}
@keyframes reveal{{from{{transform:translateX(0)}}to{{transform:translateX({COVER_W}px)}}}}
.caret{{fill:{p["gem"]};animation:blink 1s steps(1) infinite}}
@keyframes blink{{50%{{opacity:0}}}}
.bob{{animation:bob 3s ease-in-out infinite}}
@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-5px)}}}}
@media (prefers-reduced-motion:reduce){{.cover{{display:none}}.bob,.caret{{animation:none}}}}
</style>
<defs>
<clipPath id="portal"><rect x="20" y="54" width="230" height="{H - 74}" rx="8"/></clipPath>
<radialGradient id="vig" cx="50%" cy="68%" r="65%"><stop offset="55%" stop-color="{p["cave"]}" stop-opacity="0"/><stop offset="100%" stop-color="{p["cave"]}" stop-opacity=".95"/></radialGradient>
</defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{p["cave"]}" stroke="{p["body_d"]}"/>
<path d="M1 36V11A10 10 0 0 1 11 1H{W - 11}A10 10 0 0 1 {W - 1} 11V36z" fill="{p["cave2"]}"/>
<line x1="0" y1="36" x2="{W}" y2="36" stroke="{p["body_d"]}"/>
<circle cx="20" cy="18" r="5.5" fill="{p["gem"]}"/><circle cx="38" cy="18" r="5.5" fill="{p["body_l"]}" opacity=".6"/><circle cx="56" cy="18" r="5.5" fill="{p["body_l"]}" opacity=".6"/>
<text x="76" y="22" class="dim">{esc(host)}:~/cave</text>
<g clip-path="url(#portal)">
  <image href="{sprite_uri(p["bg"])}" x="-130" y="10" width="500" height="332" preserveAspectRatio="xMidYMid slice"/>
  <rect x="20" y="54" width="230" height="{H - 74}" fill="{p["tint"]}" opacity="{p["tint_alpha"]}" style="mix-blend-mode:multiply"/>
  <rect x="20" y="54" width="230" height="{H - 74}" fill="url(#vig)"/>
  <g class="bob"><image href="{sprite_uri(p["sprite"])}" x="49" y="{H - 214}" width="172" height="170" class="px"/></g>
</g>
<rect x="20.5" y="54.5" width="229" height="{H - 75}" rx="8" fill="none" stroke="{p["body_d"]}"/>
{"".join(rows)}
{blocks}
<text x="{TEXT_X}" y="{py}"><tspan class="p">{esc(host)}</tspan> ~ $</text>
<rect class="caret" x="{TEXT_X + CHAR_W * (len(host) + 5)}" y="{py - 13}" width="8" height="16"/>
{"".join(covers)}
<text x="{W - 16}" y="{H - 12}" text-anchor="end" class="dim">auto-updated {updated}</text>
</svg>'''


def render_terminal(stats: Stats) -> None:
    for theme in THEMES:
        write_asset(f"terminal-{theme}.svg", render(theme, stats))
