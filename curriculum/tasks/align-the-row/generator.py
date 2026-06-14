"""Regenerate seed.json for align-the-row.

Five equal-sized boxes are scattered across the canvas at different heights and
uneven horizontal spacing. The agent must tidy them into a single neat
horizontal row: every box aligned along the same top edge AND spaced with equal
gaps between neighbours — without resizing them.

This probes *precision the agent cannot eyeball*. Dragging the boxes into a
"roughly" tidy row looks fine in a screenshot but almost never hits the tight
top-alignment and equal-gap tolerances; the reliable path is to select all five
and use Excalidraw's align ("align top") and distribute ("distribute
horizontally") controls, which only appear on a multi-selection. So the task
splits on whether the agent discovers and correctly uses those tools — a
tool-knowledge / precision failure surface, not a puzzle that a planner can
simply reason out.

The boxes start scattered (different tops, uneven gaps), so the seed grades 0.

Run:
    uv run python curriculum/tasks/align-the-row/generator.py
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_root))

from curriculum.seed_generator import (
    SeedBuilder, rectangle, RED, BLUE, GREEN, YELLOW, VIOLET,
)

BOX_W, BOX_H = 100, 70

# Scattered start: distinct tops (defeats tops_aligned) and uneven horizontal
# gaps (defeats evenly_spaced). Positions are (x, y, fill).
SCATTER = [
    (120, 140, RED),
    (640, 180, BLUE),
    (250, 500, GREEN),
    (520, 460, YELLOW),
    (390, 300, VIOLET),
]

b = SeedBuilder()
for x, y, fill in SCATTER:
    b.add(rectangle(x, y, BOX_W, BOX_H, background_color=fill, stroke_width=2))

b.save(Path(__file__).parent / "seed.json")
