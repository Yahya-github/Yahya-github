"""Shared helpers: paths, Sableye palettes, embedded assets and fonts for SVG output.

GitHub renders README SVGs through <img>, which blocks every external request.
So every sprite and font is inlined as a data: URI, and fonts are subset to the
characters actually drawn to keep files small.
"""
from __future__ import annotations

import base64
import io
import tomllib
from functools import lru_cache
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPRITES = ROOT / "sprites"
ASSETS = ROOT / "assets"
THEMES = ("dark", "light")

# Dark = Mega Sableye, light = Shiny Mega Sableye (colours sampled from the official art).
PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "cave": "#0D0A14", "cave2": "#2A2238", "body_d": "#3E3354", "body": "#54486C",
        "body_l": "#9084A8", "gem": "#D83C60", "gem_d": "#903048", "gem_l": "#F0909C",
        "gold": "#C09C48", "txt": "#EDE6F5", "dim": "#9084A8", "tint": "#341E4E",
        "tint_alpha": "0.6", "box": "#0D0A14", "box_ink": "#3E3354",
        "sprite": "ani.gif", "back": "ani-back.gif", "foe": "caterpie.gif", "bg": "bg-dampcave.png",
    },
    "light": {
        "cave": "#FBF7EC", "cave2": "#EFE4C8", "body_d": "#C0A860", "body": "#A8903C",
        "body_l": "#786018", "gem": "#48B460", "gem_d": "#248430", "gem_l": "#248430",
        "gold": "#604800", "txt": "#2A2410", "dim": "#786018", "tint": "#F0E2B4",
        "tint_alpha": "0.4", "box": "#FBF7EC", "box_ink": "#C0A860",
        "sprite": "ani-shiny.gif", "back": "ani-back-shiny.gif", "foe": "caterpie-shiny.gif", "bg": "bg-icecave.png",
    },
}

# Real in-game HP bar colours.
HP_COLORS = {"green": "#3FD45A", "yellow": "#F2C230", "red": "#E8483C"}
MIME = {".png": "image/png", ".gif": "image/gif", ".svg": "image/svg+xml"}


@lru_cache(maxsize=None)
def load_profile() -> dict:
    with open(ROOT / "profile.toml", "rb") as fh:
        return tomllib.load(fh)


@lru_cache(maxsize=None)
def sprite_uri(name: str) -> str:
    path = SPRITES / name
    if not path.is_file():
        raise FileNotFoundError(f"Missing sprite: {path}")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{MIME[path.suffix]};base64,{data}"


def font_face(family: str, ttf: str, text: str, weight: int | None = None) -> str:
    """Return an @font-face rule with the font subset to `text`, embedded as woff2."""
    from fontTools import subset
    from fontTools.ttLib import TTFont

    font = TTFont(SPRITES / "fonts" / ttf)
    if weight is not None and "fvar" in font:
        from fontTools.varLib import instancer
        font = instancer.instantiateVariableFont(font, {"wght": weight})
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = []
    options.name_IDs = []
    options.hinting = False
    subsetter = subset.Subsetter(options)
    subsetter.populate(text="".join(sorted(set(text + " "))))
    subsetter.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,{data}) format('woff2');}}"


def esc(text: str) -> str:
    return escape(text, quote=True)


def hp_color(hp: int, max_hp: int) -> str:
    ratio = hp / max_hp if max_hp else 0
    if ratio > 0.5:
        return HP_COLORS["green"]
    if ratio > 0.2:
        return HP_COLORS["yellow"]
    return HP_COLORS["red"]


def write_asset(name: str, svg: str) -> Path:
    ASSETS.mkdir(exist_ok=True)
    path = ASSETS / name
    path.write_text(svg, encoding="utf-8")
    return path
