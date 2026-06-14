"""
Grader: Align the Row

Verifies the five boxes were tidied into one neat horizontal row: equal size
preserved, all tops aligned, and equal gaps between neighbours (no overlaps).

The boxes are equal-sized, so "equal gaps" is read directly from the
edge-to-edge spacing of horizontally-sorted boxes. Tolerances are tight enough
that a hand-dragged "roughly tidy" row fails — the reliable way to satisfy them
is Excalidraw's align-top + distribute-horizontally tools.

Rubrics:
- five_boxes: Exactly 5 rectangles, each still the seed size (anti-hack:
  forbids deleting/duplicating or resizing boxes to fudge spacing).
- tops_aligned: All five share the same top edge within TOP_TOL.
- in_a_row_no_overlap: Sorted left-to-right, consecutive boxes have a positive
  gap (the boxes form a row and do not overlap).
- evenly_spaced: The consecutive gaps are all equal within GAP_TOL (an evenly
  distributed row, not just a non-overlapping one).

The seed boxes are scattered (different tops, uneven gaps), so it grades 0.
"""

import sys
import json
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_root))

from curriculum.sdk import ExcalidrawProject
from curriculum import GraderInput, rubricgrader, rubrics

N = 5
BOX_W, BOX_H = 100.0, 70.0
SIZE_TOL = 6.0     # px — a box must keep ~its seed size
TOP_TOL = 7.0      # px — spread of the boxes' top edges
GAP_TOL = 10.0     # px — spread between the largest and smallest gap


@rubricgrader
def grader(input: GraderInput):
    project = ExcalidrawProject(input["snapshots"]["excalidraw"])
    boxes = project.get_rectangles()
    n = len(boxes)

    sizes_ok = n == N and all(
        abs(b.width - BOX_W) <= SIZE_TOL and abs(b.height - BOX_H) <= SIZE_TOL
        for b in boxes
    )
    rubrics.assertTrue("five_boxes", sizes_ok,
        success="All five boxes present at their original size",
        failure=(
            f"Expected exactly {N} rectangles, got {n}."
            if n != N else
            "A box was resized — keep every box its original size, only move them."
        )
    )

    if n != N:
        for name in ("tops_aligned", "in_a_row_no_overlap", "evenly_spaced"):
            rubrics.assertTrue(name, False, failure=f"Need exactly {N} boxes.")
        return

    tops = [b.y for b in boxes]
    top_spread = max(tops) - min(tops)
    rubrics.assertTrue("tops_aligned", top_spread <= TOP_TOL,
        success="All boxes' tops are aligned",
        failure=(
            f"Box tops are not aligned — they span {top_spread:.0f}px "
            f"(must be within {TOP_TOL:.0f}px). Align the boxes along their top edge."
        )
    )

    ordered = sorted(boxes, key=lambda b: b.x)
    gaps = [ordered[i + 1].x - (ordered[i].x + ordered[i].width) for i in range(N - 1)]
    positive = all(g > 0 for g in gaps)
    rubrics.assertTrue("in_a_row_no_overlap", positive,
        success="Boxes form a row with no overlaps",
        failure=(
            f"Boxes overlap or sit on top of each other (gaps: {[round(g) for g in gaps]}). "
            "Lay them out side by side in a row."
        )
    )

    gap_spread = max(gaps) - min(gaps) if gaps else 0.0
    rubrics.assertTrue("evenly_spaced", positive and gap_spread <= GAP_TOL,
        success="Boxes are evenly spaced",
        failure=(
            "Cannot check spacing — boxes overlap."
            if not positive else
            f"Gaps between boxes are uneven — they range {min(gaps):.0f}..{max(gaps):.0f}px "
            f"(spread {gap_spread:.0f}px, must be within {GAP_TOL:.0f}px). "
            "Distribute the boxes so the gaps are equal."
        )
    )


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "seed.json"
    with open(path) as f:
        data = json.load(f)
    result = grader({"snapshots": {"excalidraw": data}, "transcript": "", "extra_fields": {}, "posted_answer": None})
    print(f"result={result['result']}")
    for k, v in result["metadata"]["rubrics"].items():
        print(f"  {'PASS' if v['pass'] else 'FAIL'} {k}: {v.get('message') or v.get('description', '')}")
