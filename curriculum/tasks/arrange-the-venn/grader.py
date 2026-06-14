"""
Grader: Arrange the Venn

Verifies the three circles were moved into a proper three-set Venn diagram:
every pair overlaps, and all three share a common central region — without
resizing any circle and without collapsing them onto the same spot.

All geometry is computed from exact circle math (center distance vs. radii),
not bounding-box overlap, so the result is independent of how the agent moved
the circles.

Let c_i be circle i's center and r_i its radius, and let G be the centroid of
the three centers.

Rubrics:
- three_circles_preserved: Exactly 3 ellipses, one each of the red/green/blue
  outlines from the seed (not deleted or recolored).
- radii_unchanged: Every circle's radius is still ~R (anti-hack: forbids
  blowing one circle up so it simply swallows the other two).
- centers_distinct: Every pair of centers is at least MIN_SEP apart (anti-hack:
  forbids stacking all three concentrically to trivially "share" a region).
- all_pairs_overlap: Every pair genuinely overlaps — dist(c_i, c_j) is comfortably
  less than r_i + r_j (a tangent kiss does not count).
- shared_center: The centroid G lies inside all three circles by a margin
  (dist(G, c_i) <= r_i - CORE_MARGIN), which guarantees a non-trivial region
  common to red AND green AND blue — the Venn core. This is the rubric a
  "loose" row-of-overlaps fails.

In the seed the circles are far apart, so no pair overlaps and it grades 0.
"""

import sys
import json
import math
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_root))

from curriculum.sdk import ExcalidrawProject
from curriculum import GraderInput, rubricgrader, rubrics

# Geometry constants — R mirrors generator.R.
R = 90.0
RADIUS_TOL = 18.0       # px — circle radius must stay within R +/- this
MIN_SEP = 55.0          # px — centers must be at least this far apart
OVERLAP_MARGIN = 12.0   # px — real overlap: dist <= r_i + r_j - margin
CORE_MARGIN = 22.0      # px — centroid must sit inside each circle by this margin

EXPECTED_STROKES = ["#e03131", "#2f9e44", "#1971c2"]  # STROKE_RED/GREEN/BLUE


def _radius(c):
    return (c.width + c.height) / 4.0   # mean of the two semi-axes


def _center_dist(a, b):
    return math.hypot(a.center_x - b.center_x, a.center_y - b.center_y)


@rubricgrader
def grader(input: GraderInput):
    project = ExcalidrawProject(input["snapshots"]["excalidraw"])
    circles = project.get_ellipses()
    n = len(circles)

    # --- preservation: exactly the three seeded circles, colors intact ---
    strokes = sorted(c.stroke_color.lower() for c in circles)
    colors_ok = n == 3 and strokes == sorted(EXPECTED_STROKES)
    rubrics.assertTrue("three_circles_preserved", colors_ok,
        success="All three circles (red, green, blue) preserved",
        failure=(
            f"Expected exactly 3 circles, got {n}."
            if n != 3 else
            f"Circle outline colors changed — expected red/green/blue "
            f"{sorted(EXPECTED_STROKES)}, got {strokes}."
        )
    )

    radii = [_radius(c) for c in circles]
    radii_ok = n == 3 and all(abs(r - R) <= RADIUS_TOL for r in radii)
    rubrics.assertTrue("radii_unchanged", radii_ok,
        success="Circles kept their original size",
        failure=(
            "Cannot check sizes — need exactly 3 circles."
            if n != 3 else
            f"A circle was resized — radii {[round(r) for r in radii]} px must each "
            f"stay within {R:.0f}+/-{RADIUS_TOL:.0f}px. Move the circles, do not resize them."
        )
    )

    # Remaining geometry rubrics need exactly 3 circles.
    if n != 3:
        for name in ("centers_distinct", "all_pairs_overlap", "shared_center"):
            rubrics.assertTrue(name, False, failure="Need exactly 3 circles.")
        return

    pairs = [(0, 1), (0, 2), (1, 2)]

    # --- centers distinct (not concentric) ---
    seps = [_center_dist(circles[i], circles[j]) for i, j in pairs]
    distinct_ok = all(s >= MIN_SEP for s in seps)
    rubrics.assertTrue("centers_distinct", distinct_ok,
        success="The three circles are clearly distinct",
        failure=(
            f"Circles are too close to the same spot — every pair of centers must be "
            f">= {MIN_SEP:.0f}px apart (pairwise center distances: {[round(s) for s in seps]})."
        )
    )

    # --- every pair overlaps (real overlap, not a tangent kiss) ---
    overlap_flags = [
        seps[k] <= radii[i] + radii[j] - OVERLAP_MARGIN
        for k, (i, j) in enumerate(pairs)
    ]
    rubrics.assertTrue("all_pairs_overlap", all(overlap_flags),
        success="Every pair of circles overlaps",
        failure=(
            f"{overlap_flags.count(False)} pair(s) of circles do not overlap (or only "
            f"touch). Pairwise center distances {[round(s) for s in seps]} must each be "
            f"clearly less than the sum of the two radii (~{round(2 * R)}px)."
        )
    )

    # --- shared central region: centroid inside all three by a margin ---
    gx = sum(c.center_x for c in circles) / 3.0
    gy = sum(c.center_y for c in circles) / 3.0
    core_dists = [math.hypot(gx - c.center_x, gy - c.center_y) for c in circles]
    shared_ok = all(d <= radii[i] - CORE_MARGIN for i, d in enumerate(core_dists))
    rubrics.assertTrue("shared_center", shared_ok,
        success="All three circles share a common central region",
        failure=(
            "There is no region common to all three circles — the overlap is too "
            "shallow. The very middle of the three centers must fall inside red AND "
            "green AND blue at once (push the circles together more deeply)."
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
