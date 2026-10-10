"""Badges earned: 2x2 cards, one Hoenn gym badge per real competition result.

Each badge's type matches the win (Psychic for the perfect CCC score, Fire for the
hackathon, Water for the submarine game, Electric for robotics). Content: profile.toml.
"""
from __future__ import annotations

from scripts.common import PALETTES, THEMES, esc, font_face, load_profile, sprite_uri, write_asset

W, CARD_W, CARD_H, GAP = 860, 424, 124, 12
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"


def _card(badge: dict, x: int, y: int, i: int) -> str:
    tx = x + 112
    lines = "".join(f'<text x="{tx}" y="{y + 82 + n * 18}" class="desc">{esc(line)}</text>'
                    for n, line in enumerate(badge["lines"]))
    return f'''<g>
<rect x="{x + .5}" y="{y + .5}" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="10" class="card"/>
<image href="{sprite_uri(badge["art"])}" x="{x + 18}" y="{y + 10}" width="76" height="76" class="badge" style="animation-delay:{i * 1.2:.1f}s"/>
<image href="{sprite_uri("type-" + badge["type"] + ".png")}" x="{x + 32}" y="{y + 93}" width="48" height="21" class="px"/>
<text x="{tx}" y="{y + 32}" class="place">{esc(badge["place"].upper())}</text>
<text x="{tx}" y="{y + 56}" class="title">{esc(badge["title"])}</text>
{lines}
</g>'''


def render(theme: str) -> str:
    p = PALETTES[theme]
    badges = load_profile()["badges"]
    rows = (len(badges) + 1) // 2
    h = rows * CARD_H + (rows - 1) * GAP
    font = font_face("Mono", "JetBrainsMono.ttf", "".join(b["place"].upper() for b in badges), weight=700)
    cards = "".join(_card(b, (i % 2) * (CARD_W + GAP), (i // 2) * (CARD_H + GAP), i) for i, b in enumerate(badges))
    label = "; ".join(f'{b["title"]}: {b["place"]}' for b in badges)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="Badges earned. {esc(label)}">
<style>{font}
.card{{fill:{p["cave"]};stroke:{p["body_d"]}}}
.place{{font:700 11px Mono,ui-monospace,monospace;letter-spacing:.08em;fill:{p["gold"]}}}
.title{{font:600 15.5px {SANS};fill:{p["txt"]}}}
.desc{{font:400 12.5px {SANS};fill:{p["dim"]}}}
.px{{image-rendering:pixelated}}
.badge{{animation:shine 5s ease-in-out infinite}}
@keyframes shine{{0%,84%,100%{{filter:brightness(1)}}92%{{filter:brightness(1.4) drop-shadow(0 0 6px #fff)}}}}
@media (prefers-reduced-motion:reduce){{.badge{{animation:none}}}}
</style>
{cards}
</svg>'''


def render_badges() -> None:
    for theme in THEMES:
        write_asset(f"badges-{theme}.svg", render(theme))
