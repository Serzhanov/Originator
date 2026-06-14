"""
Grader: Match the Style

Verifies the plain RIGHT rectangle was restyled to exactly match the styled
LEFT reference across six independent style fields — fill color, fill pattern
(fillStyle), stroke color, stroke width, stroke style, and opacity — while the
reference itself and both geometries stay untouched.

The two rectangles deliberately differ in size, so the geometry rubric defeats
the "duplicate the reference over the target" shortcut: the style has to be
transferred onto the existing shape.

Rubrics:
- two_rectangles_preserved: Still exactly 2 rectangles
- geometry_unchanged: Both rectangles keep their seed position and size
- reference_untouched: The left reference keeps every seed style field
- target_style_matches: The right rectangle's six style fields match the
  reference (task goal; opacity within +/-5 to absorb slider granularity)

The right rectangle starts plain, so the seed grades 0.
"""

import sys
import json
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_root))

from curriculum.sdk import ExcalidrawProject
from curriculum import GraderInput, rubricgrader, rubrics

# Mirror generator.py
REF_GEOM = (250, 300, 160, 120)
TGT_GEOM = (650, 300, 220, 140)
TARGET_STYLE = {
    "backgroundColor": "#ff6b6b",
    "fillStyle": "hachure",
    "strokeColor": "#1971c2",
    "strokeWidth": 4,
    "strokeStyle": "dashed",
    "opacity": 60,
}
POS_TOL = 10        # px — shapes must not move
SIZE_TOL = 5        # px — shapes must not be resized
OPACITY_TOL = 5     # the opacity slider snaps in steps of 10


def _style_of(rect) -> dict:
    return {
        "backgroundColor": rect.background_color.lower(),
        "fillStyle": rect.fill_style,
        "strokeColor": rect.stroke_color.lower(),
        "strokeWidth": rect.stroke_width,
        "strokeStyle": rect.stroke_style,
        "opacity": rect.opacity,
    }


def _style_mismatches(rect) -> list[str]:
    """Fields where *rect*'s style differs from TARGET_STYLE."""
    actual = _style_of(rect)
    out = []
    for field, expected in TARGET_STYLE.items():
        got = actual[field]
        ok = abs(got - expected) <= OPACITY_TOL if field == "opacity" else got == expected
        if not ok:
            out.append(f"{field}: {got!r} (expected {expected!r})")
    return out


def _geom_ok(rect, geom) -> bool:
    x, y, w, h = geom
    return (abs(rect.x - x) <= POS_TOL and abs(rect.y - y) <= POS_TOL
            and abs(rect.width - w) <= SIZE_TOL and abs(rect.height - h) <= SIZE_TOL)


@rubricgrader
def grader(input: GraderInput):
    project = ExcalidrawProject(input["snapshots"]["excalidraw"])
    rects = project.get_rectangles()

    rubrics.assertTrue("two_rectangles_preserved", len(rects) == 2,
        success="Both rectangles preserved",
        failure=f"Expected exactly 2 rectangles, got {len(rects)}."
    )

    # Left = reference, right = target; geometry pins which is which.
    if len(rects) == 2:
        ref, target = sorted(rects, key=lambda r: r.center_x)
    else:
        ref = target = None

    rubrics.assertTrue("geometry_unchanged",
        ref is not None and _geom_ok(ref, REF_GEOM) and _geom_ok(target, TGT_GEOM),
        success="Neither rectangle was moved or resized",
        failure=(
            "Cannot check geometry — need exactly 2 rectangles."
            if ref is None else
            "A rectangle was moved or resized — only the right one's STYLE should change."
        )
    )

    ref_mismatches = _style_mismatches(ref) if ref else []
    rubrics.assertTrue("reference_untouched", ref is not None and not ref_mismatches,
        success="The left reference rectangle is untouched",
        failure=(
            "No reference rectangle to check."
            if ref is None else
            "The left reference was modified: " + "; ".join(ref_mismatches)
        )
    )

    tgt_mismatches = _style_mismatches(target) if target else []
    rubrics.assertTrue("target_style_matches", target is not None and not tgt_mismatches,
        success="The right rectangle's style exactly matches the reference",
        failure=(
            "No target rectangle to check."
            if target is None else
            "Style fields still differ from the reference — " + "; ".join(tgt_mismatches)
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
