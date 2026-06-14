"""Regenerate seed.json for match-the-style.

Two rectangles: a heavily styled reference on the LEFT (red hachure fill, blue
dashed extra-bold stroke, 60% opacity) and a plain one on the RIGHT
(transparent, black solid stroke, full opacity). The agent must restyle the
right rectangle so its appearance exactly matches the reference, without
moving or resizing either shape.

This probes multi-property style transfer through the left style panel (or the
copy-style / paste-style shortcuts): five independent style controls — fill
color, fill pattern, stroke color, stroke width + style, and the opacity
slider. The classic failure is a partial transfer: the fill color gets copied,
but fillStyle / strokeStyle / opacity are missed.

The rectangles deliberately differ in SIZE, so "duplicate the reference onto
the target's spot" fails the geometry rubric — the style must be transferred,
not the shape.

The right rectangle starts plain, so the seed grades 0.

Run:
    uv run python curriculum/tasks/match-the-style/generator.py
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_root))

from curriculum.seed_generator import (
    SeedBuilder, rectangle, RED, TRANSPARENT, STROKE_BLUE, STROKE_BLACK,
)

# Reference (left) — every style field differs from the plain target.
REF_X, REF_Y, REF_W, REF_H = 250, 300, 160, 120
TGT_X, TGT_Y, TGT_W, TGT_H = 650, 300, 220, 140  # different size: blocks duplicate-and-replace
REF_OPACITY = 60

b = SeedBuilder()

ref = rectangle(
    REF_X, REF_Y, REF_W, REF_H,
    background_color=RED,
    stroke_color=STROKE_BLUE,
    fill_style="hachure",
    stroke_width=4,
    stroke_style="dashed",
)
ref["opacity"] = REF_OPACITY
b.add(ref)

b.add(rectangle(
    TGT_X, TGT_Y, TGT_W, TGT_H,
    background_color=TRANSPARENT,
    stroke_color=STROKE_BLACK,
    fill_style="solid",
    stroke_width=2,
    stroke_style="solid",
))

b.save(Path(__file__).parent / "seed.json")
