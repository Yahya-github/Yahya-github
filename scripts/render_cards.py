"""Live stats row: trainer stats, streak ring and language bars in one 860px card set.

Replaces the hosted stat/streak/language cards (rate limited, public repos only) with
numbers from our own GraphQL query, so private contributions and team forks count.
"""
from __future__ import annotations

import math

from scripts.common import PALETTES, THEMES, esc, font_face, sprite_uri, write_asset
from scripts.github_data import Stats

W, H = 860, 214
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
PANELS = ((0, 290), (302, 256), (570, 290))  # (x, width)
RING_R = 50


def _fmt_date(d) -> str:
    return d.strftime("%b %-d, %Y") if d else "-"


def _stats_panel(s: Stats) -> str:
    x, w = PANELS[0]
    nxt = (s.level + 1) ** 2
    xp = 1.0 if s.level >= 100 else (s.total_contributions - s.level ** 2) / (nxt - s.level ** 2)
    rows = [("Contributions", f"{s.total_contributions:,}"), ("Commits", f"{s.commits:,}"),
            ("Pull requests", f"{s.pull_requests:,}"), ("Longest streak", f"{s.streaks.longest} days")]
    out = [f'<text x="{x + 22}" y="36" class="h">Trainer stats</text>']
    for i, (label, value) in enumerate(rows):
        y = 68 + i * 26
        out.append(f'<text x="{x + 22}" y="{y}" class="lbl">{label}</text>'
                   f'<text x="{x + w - 22}" y="{y}" class="val" text-anchor="end">{value}</text>')
    y = 68 + len(rows) * 26
    out.append(f'<text x="{x + 22}" y="{y}" class="lbl">Level</text>'
               f'<text x="{x + w - 22}" y="{y}" class="val" text-anchor="end">Lv {s.level}</text>'
               f'<rect x="{x + 22}" y="{y + 10}" width="{w - 44}" height="5" rx="2.5" class="track"/>'
               f'<rect x="{x + 22}" y="{y + 10}" width="{(w - 44) * max(0.0, min(xp, 1.0)):.1f}" height="5" rx="2.5" class="xp grow"/>')
    return "".join(out)


def _streak_panel(s: Stats) -> str:
    x, w = PANELS[1]
    cx, cy = x + w / 2, 96
    circ = 2 * math.pi * RING_R
    st = s.streaks
    dates = f"{_fmt_date(st.current_start)} - {_fmt_date(st.current_end)}" if st.current else "Start one today"
    return (f'<circle cx="{cx}" cy="{cy}" r="{RING_R}" class="ringbg"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{RING_R}" class="ring" stroke-dasharray="{circ:.1f}" '
            f'style="--c:{circ:.1f}px" transform="rotate(-90 {cx} {cy})"/>'
            f'<rect x="{cx - 30}" y="{cy - RING_R - 12}" width="60" height="24" class="gap"/>'
            f'<image href="{sprite_uri("type-fire.png")}" x="{cx - 24}" y="{cy - RING_R - 10.5}" width="48" height="21" class="px"/>'
            f'<text x="{cx}" y="{cy + 11}" class="big" text-anchor="middle">{st.current}</text>'
            f'<text x="{cx}" y="{cy + RING_R + 30}" class="h" text-anchor="middle">Current streak</text>'
            f'<text x="{cx}" y="{cy + RING_R + 48}" class="sm" text-anchor="middle">{esc(dates)}</text>')


def _lang_panel(s: Stats) -> str:
    x, w = PANELS[2]
    out = [f'<text x="{x + 22}" y="36" class="h">Move types</text>']
    for i, lang in enumerate(s.languages):
        y = 66 + i * 36
        out.append(f'<text x="{x + 22}" y="{y}" class="lbl">{esc(lang.name)}</text>'
                   f'<text x="{x + w - 22}" y="{y}" class="val" text-anchor="end">{lang.pct:.1f}%</text>'
                   f'<rect x="{x + 22}" y="{y + 9}" width="{w - 44}" height="7" rx="3.5" class="track"/>'
                   f'<rect x="{x + 22}" y="{y + 9}" width="{(w - 44) * lang.pct / 100:.1f}" height="7" rx="3.5" '
                   f'fill="{lang.color}" class="grow" style="animation-delay:{0.2 + i * 0.15:.2f}s"/>')
    return "".join(out)


def render(theme: str, s: Stats) -> str:
    p = PALETTES[theme]
    font = font_face("Mono", "JetBrainsMono.ttf", "0123456789,.%Lv days", weight=700)
    panels = "".join(f'<rect x="{x + .5}" y=".5" width="{w - 1}" height="{H - 1}" rx="10" class="panel"/>'
                     for x, w in PANELS)
    label = (f"{s.total_contributions:,} contributions, {s.commits:,} commits, {s.pull_requests} pull requests, "
             f"{s.streaks.current}-day current streak, level {s.level}. Languages: "
             + ", ".join(f"{l.name} {l.pct:.0f}%" for l in s.languages))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}">
<style>{font}
.panel{{fill:{p["cave"]};stroke:{p["body_d"]}}} .gap{{fill:{p["cave"]}}}
.h{{font:600 15px {SANS};fill:{p["gem_l"]}}}
.lbl{{font:400 13.5px {SANS};fill:{p["txt"]}}}
.val{{font:700 13.5px Mono,ui-monospace,monospace;fill:{p["txt"]}}}
.sm{{font:400 12px {SANS};fill:{p["dim"]}}}
.big{{font:700 34px Mono,ui-monospace,monospace;fill:{p["txt"]}}}
.track{{fill:{p["body_d"]}}} .xp{{fill:{p["gold"]}}}
.ringbg{{fill:none;stroke:{p["body_d"]};stroke-width:7}}
.ring{{fill:none;stroke:{p["gem"]};stroke-width:7;stroke-linecap:round;animation:draw 1.4s ease-out both}}
@keyframes draw{{from{{stroke-dashoffset:var(--c)}}to{{stroke-dashoffset:0}}}}
.grow{{transform-box:fill-box;transform-origin:left;animation:grow .9s ease-out both}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
.px{{image-rendering:pixelated}}
@media (prefers-reduced-motion:reduce){{.ring,.grow{{animation:none}}}}
</style>
{panels}{_stats_panel(s)}{_streak_panel(s)}{_lang_panel(s)}
</svg>'''


def render_cards(stats: Stats) -> None:
    for theme in THEMES:
        write_asset(f"stats-{theme}.svg", render(theme, stats))
