"""
Grader: Set the Clock

Verifies the two clock hands were rotated so the clock reads 4:00:
hour hand -> 4 (lower-right, 120 deg), minute hand -> 12 (pointing up / North).

Each hand's true endpoints are recovered from its geometry (points rotated by
the element `angle` about the bounding-box center, exactly as Excalidraw
renders them). The endpoint nearer the clock center is the hand's base; the
bearing is measured base -> tip, clockwise from 12. This is robust whether the
agent dragged the tip, rotated the element, or redrew the hand (in either
point order).

Rubrics:
- face_preserved: The clock face (ellipse) is still present
- two_hands: Exactly 2 hands (arrows) present
- hands_anchored_at_center: Each hand's base end stays on the clock center
  (forbids detaching a hand or redrawing it elsewhere on the canvas)
- hour_points_to_4: Hour hand bearing ~ 120 deg / the 4 (task goal)
- minute_points_to_12: Minute hand bearing ~ 0 deg / North (task goal)

Both hands start at 12, so the seed reads 12:00 and grades 0.
"""

import sys
import json
import math
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_root))

from curriculum.sdk import ExcalidrawProject
from curriculum import GraderInput, rubricgrader, rubrics

TWO_PI = 2 * math.pi
TOL = 0.15                  # radians (~8.6 deg)
HOUR_TARGET = 2 * math.pi / 3  # 120 deg = the 4 (4 o'clock)
MIN_TARGET = 0.0            # North = 12 o'clock
CENTER = (400.0, 350.0)     # clock pivot — mirrors generator (CX, CY)
ANCHOR_TOL = 30.0           # px — a hand's base must stay on the pivot


def _endpoints(hand):
    """Absolute coords of a hand's two end points, honoring the element
    `angle` (Excalidraw rotates a linear element about its bbox center).

    The rotation below is byte-for-byte Excalidraw's own `rotate(x, y, cx, cy,
    angle)` transform, so the recovered bearing always equals what is drawn on
    screen — the result is independent of the angle sign convention, and is the
    same whether the agent dragged the tip or used the rotate handle."""
    pts = hand.points
    if len(pts) < 2:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx = hand.x + (min(xs) + max(xs)) / 2
    cy = hand.y + (min(ys) + max(ys)) / 2
    a = hand.angle
    out = []
    for px, py in (pts[0], pts[-1]):
        ax, ay = hand.x + px, hand.y + py
        rx = cx + (ax - cx) * math.cos(a) - (ay - cy) * math.sin(a)
        ry = cy + (ax - cx) * math.sin(a) + (ay - cy) * math.cos(a)
        out.append((rx, ry))
    return out


def _anchor_tip(hand):
    """(base, tip) of a hand — the end point nearer the clock center is the base."""
    ends = _endpoints(hand)
    if ends is None:
        return None, None
    p0, p1 = ends
    d0 = math.hypot(p0[0] - CENTER[0], p0[1] - CENTER[1])
    d1 = math.hypot(p1[0] - CENTER[0], p1[1] - CENTER[1])
    return (p0, p1) if d0 <= d1 else (p1, p0)


def _anchored(hand):
    anchor, _ = _anchor_tip(hand)
    return anchor is not None and math.hypot(anchor[0] - CENTER[0], anchor[1] - CENTER[1]) <= ANCHOR_TOL


def _bearing(hand):
    """Clockwise bearing from 12 o'clock (up) of a hand, base -> tip."""
    anchor, tip = _anchor_tip(hand)
    if anchor is None:
        return None
    dx = tip[0] - anchor[0]
    dy = tip[1] - anchor[1]
    # up = (0,-1); east component = dx, north component = -dy
    return math.atan2(dx, -dy) % TWO_PI


def _length(hand):
    pts = hand.points
    if len(pts) < 2:
        return 0.0
    return math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])


def _close(bearing, target):
    if bearing is None:
        return False
    diff = abs((bearing - target + math.pi) % TWO_PI - math.pi)
    return diff <= TOL


def _deg(b):
    return None if b is None else round(math.degrees(b))


@rubricgrader
def grader(input: GraderInput):
    project = ExcalidrawProject(input["snapshots"]["excalidraw"])

    faces = project.get_ellipses()
    hands = project.get_arrows()

    rubrics.assertTrue("face_preserved", len(faces) >= 1,
        success="Clock face preserved",
        failure="The clock face (ellipse) is missing."
    )
    rubrics.assertTrue("two_hands", len(hands) == 2,
        success="Both clock hands present",
        failure=f"Expected 2 hands, got {len(hands)}."
    )

    # Identify hands by length: the longer one is the minute hand.
    if len(hands) == 2:
        hour, minute = sorted(hands, key=_length)  # shorter first
    else:
        hour = minute = None

    rubrics.assertTrue("hands_anchored_at_center",
        hour is not None and minute is not None and _anchored(hour) and _anchored(minute),
        success="Both hands stay anchored at the clock center",
        failure=(
            "Cannot check anchoring — need exactly 2 hands."
            if hour is None or minute is None else
            f"A hand's base end drifted more than {ANCHOR_TOL:.0f}px off the clock center "
            "— hands must stay attached to the pivot. (Note: the rotate handle pivots a "
            "hand about its own middle, which detaches its base.)"
        )
    )

    hb = _bearing(hour) if hour else None
    mb = _bearing(minute) if minute else None

    rubrics.assertTrue("hour_points_to_4", _close(hb, HOUR_TARGET),
        success="Hour hand points to the 4",
        failure=(
            "No hour hand to check."
            if hour is None else
            f"Hour hand points at {_deg(hb)} deg from 12; expected ~120 deg (to the 4)."
        )
    )
    rubrics.assertTrue("minute_points_to_12", _close(mb, MIN_TARGET),
        success="Minute hand points to the 12 (North)",
        failure=(
            "No minute hand to check."
            if minute is None else
            f"Minute hand points at {_deg(mb)} deg from 12; expected ~0 deg (to the 12)."
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
