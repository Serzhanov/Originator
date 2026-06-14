"""Regenerate seed.json for yellow-circle-in-blue-box.

The seed shows a blue rectangle on the left and a yellow circle to the right,
outside the rectangle. The agent task is to move the circle inside the box.

Run:
    python3 curriculum/tasks/yellow-circle-in-blue-box/generator.py
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_root))

from curriculum.seed_generator import SeedBuilder, rectangle, ellipse, BLUE, YELLOW, STROKE_RED, STROKE_BLUE

b = SeedBuilder()
b.add(rectangle(100, 150, 500, 400, background_color=BLUE, stroke_color=STROKE_RED))
b.add(ellipse(750, 200, 300, 300, background_color=YELLOW, stroke_color=STROKE_BLUE))

b.save(Path(__file__).parent / "seed.json")
