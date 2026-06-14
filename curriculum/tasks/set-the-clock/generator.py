"""Regenerate seed.json for set-the-clock.

A clock face with two hands (arrows), both pointing up at 12. The agent must
rotate the hands so the clock reads 4:00 — hour hand to the 4 (lower-right, a
non-cardinal 120 deg bearing), minute hand left at the 12 (pointing up).

This probes turning a linear element to a precise bearing while keeping it
anchored at a pivot — a UI mechanic almost nothing else exercises. The natural
trap: Excalidraw's rotate handle pivots a hand about its own middle, which
detaches its base from the clock center; the agent must drag the tip endpoint
instead (or re-anchor afterwards). The grader recovers each hand's endpoints
from points + angle, so it's robust whether the agent dragged the tip or
redrew the hand.

Both hands start at 12, so the seed (reading 12:00) grades 0.

Run:
    uv run python curriculum/tasks/set-the-clock/generator.py
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_root))

from curriculum.seed_generator import SeedBuilder, ellipse, arrow, WHITE, STROKE_BLACK, STROKE_BLUE

CX, CY = 400, 350        # clock center — keeps it central after scrollToContent
FACE_R = 200
HOUR_LEN = 130
MIN_LEN = 185

b = SeedBuilder()
# Clock face.
b.add(ellipse(CX - FACE_R, CY - FACE_R, FACE_R * 2, FACE_R * 2, background_color=WHITE, stroke_color=STROKE_BLACK, stroke_width=4))
# Hands: rooted at center, pointing straight up (12 o'clock). Negative y = up.
b.add(arrow(CX, CY, [[0, 0], [0, -HOUR_LEN]], stroke_color=STROKE_BLACK, stroke_width=4))   # hour (shorter)
b.add(arrow(CX, CY, [[0, 0], [0, -MIN_LEN]], stroke_color=STROKE_BLUE, stroke_width=2))     # minute (longer)

b.save(Path(__file__).parent / "seed.json")
