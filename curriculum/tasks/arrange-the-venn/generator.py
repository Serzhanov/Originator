"""Regenerate seed.json for arrange-the-venn.

Three equal-radius circles (ellipses) — red, green, blue outlines — sit far
apart in a horizontal row, none overlapping any other. The agent must drag
them together into a proper three-set Venn diagram: every pair overlaps AND
all three share a common central region (the iconic Venn core), without
resizing any circle.

This probes arranging elements into a multi-way *partial-overlap* relationship
to a precise depth — a distinct mechanic from containment, binding, z-order,
rotation, or style transfer. The natural trap is a "loose" Venn: nudging the
circles until they merely kiss in a row looks overlapping in a screenshot but
leaves no region common to all three, so it fails the shared-center rubric.
The grader uses exact circle geometry (center distance vs. radii), so it is
independent of how the agent moved the circles.

In the seed the circles are far apart (no pair overlaps), so it grades 0.

Run:
    uv run python curriculum/tasks/arrange-the-venn/generator.py
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_root))

from curriculum.seed_generator import (
    SeedBuilder,
    ellipse,
    STROKE_RED,
    STROKE_GREEN,
    STROKE_BLUE,
)

R = 90                      # circle radius — mirrored in grader
DIAM = R * 2
ROW_Y = 350                 # shared center y for all three (row)
CENTERS_X = [200, 560, 920]  # far apart: adjacent gap 360 >> 2R, so no overlap
STROKES = [STROKE_RED, STROKE_GREEN, STROKE_BLUE]

b = SeedBuilder()
for cx, stroke in zip(CENTERS_X, STROKES):
    b.add(ellipse(
        cx - R, ROW_Y - R, DIAM, DIAM,
        background_color="transparent",
        stroke_color=stroke,
        stroke_width=3,
    ))

b.save(Path(__file__).parent / "seed.json")
