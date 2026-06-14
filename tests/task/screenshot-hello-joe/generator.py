"""Regenerate seed.json for screenshot-hello-joe.

The seed shows the text "Hello Joe" in red on a blank canvas.
The agent task is to take a screenshot and describe what it sees.

Run:
    python3 curriculum/tasks/screenshot-hello-joe/generator.py
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_root))

from curriculum.seed_generator import SeedBuilder, text, STROKE_RED

b = SeedBuilder()
b.add(text(300, 250, "Hello Joe", font_size=48, stroke_color=STROKE_RED))

b.save(Path(__file__).parent / "seed.json")
