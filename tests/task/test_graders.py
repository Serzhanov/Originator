"""Grader regression tests — no browser, API key, or gym needed.

For every task: the committed seed must grade 0 (task not yet done).
For each authored task: a programmatically solved state must grade 1, and a
couple of near-miss states (the anti-hack rubrics' reason for existing) must
still grade 0.

Solved states are built by mutating the seed JSON the same way a successful
agent run would mutate the canvas state.
"""

import copy
import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
TASKS = ROOT / "curriculum" / "tasks"
sys.path.insert(0, str(ROOT))

ALL_TASKS = sorted(p.name for p in TASKS.iterdir() if (p / "grader.py").exists())


def _load_grader(task: str):
    path = TASKS / task / "grader.py"
    name = f"grader_{task.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.grader


def _seed(task: str) -> dict:
    return json.loads((TASKS / task / "seed.json").read_text())


def _grade(task: str, data: dict) -> dict:
    grader = _load_grader(task)
    return grader({"snapshots": {"excalidraw": data}, "transcript": "",
                   "extra_fields": {}, "posted_answer": None})


def _els(data: dict) -> list[dict]:
    return data["elements"]


# ---------------------------------------------------------------------------
# Solved-state builders
# ---------------------------------------------------------------------------


def _solve_clock(data: dict) -> None:
    hands = [e for e in _els(data) if e["type"] == "arrow"]
    hour = min(hands, key=lambda e: math.hypot(*e["points"][-1]))
    length = math.hypot(*hour["points"][-1])
    t = math.radians(120)  # 120 deg clockwise from 12 = the 4 (4 o'clock)
    hour["points"] = [[0, 0], [length * math.sin(t), -length * math.cos(t)]]


STYLE_FIELDS = ["backgroundColor", "fillStyle", "strokeColor",
                "strokeWidth", "strokeStyle", "opacity"]


def _style_rects(data: dict) -> tuple[dict, dict]:
    rects = sorted((e for e in _els(data) if e["type"] == "rectangle"),
                   key=lambda e: e["x"])
    return rects[0], rects[1]


def _solve_style(data: dict) -> None:
    ref, target = _style_rects(data)
    for field in STYLE_FIELDS:
        target[field] = ref[field]


def _solve_venn(data: dict) -> None:
    """Arrange the three circles into an equilateral-triangle Venn (side 100),
    centered at (500, 400) — deep enough that the centroid is inside all three."""
    R = 90.0
    s = 100.0
    cr = s / math.sqrt(3)
    cx, cy = 500.0, 400.0
    centers = [(cx, cy - cr), (cx + s / 2, cy + cr / 2), (cx - s / 2, cy + cr / 2)]
    circles = [e for e in _els(data) if e["type"] == "ellipse"]
    for el, (px, py) in zip(circles, centers):
        el["x"], el["y"] = px - R, py - R


def _solve_align_row(data: dict) -> None:
    """Lay the five boxes in a row: same top (y=200) and equal 60px gaps."""
    rects = [e for e in _els(data) if e["type"] == "rectangle"]
    for i, el in enumerate(rects):
        el["x"], el["y"] = 100 + 160 * i, 200   # width 100 + gap 60 = 160 pitch


SOLVERS = {
    "set-the-clock": _solve_clock,
    "match-the-style": _solve_style,
    "arrange-the-venn": _solve_venn,
    "align-the-row": _solve_align_row,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("task", ALL_TASKS)
def test_seed_grades_zero(task):
    result = _grade(task, _seed(task))
    assert result["result"] == 0, f"seed must grade 0\n{result['debug']}"


@pytest.mark.parametrize("task", sorted(SOLVERS))
def test_solved_state_grades_one(task):
    data = copy.deepcopy(_seed(task))
    SOLVERS[task](data)
    result = _grade(task, data)
    assert result["result"] == 1, f"solved state must grade 1\n{result['debug']}"


def test_clock_rotate_handle_detaches_hand_and_fails():
    # Rotating via the rotate handle pivots about the element's middle,
    # pulling the base off the clock center: bearing is right, anchor is not.
    data = _seed("set-the-clock")
    hands = [e for e in _els(data) if e["type"] == "arrow"]
    hour = min(hands, key=lambda e: math.hypot(*e["points"][-1]))
    hour["angle"] = math.pi / 2
    result = _grade("set-the-clock", data)
    assert result["result"] == 0
    assert not result["metadata"]["rubrics"]["hands_anchored_at_center"]["pass"]


def test_style_partial_transfer_fails():
    # Fill color copied, low-salience fields (fillStyle, strokeStyle, opacity) missed.
    data = _seed("match-the-style")
    ref, target = _style_rects(data)
    for field in ["backgroundColor", "strokeColor", "strokeWidth"]:
        target[field] = ref[field]
    result = _grade("match-the-style", data)
    assert result["result"] == 0
    assert not result["metadata"]["rubrics"]["target_style_matches"]["pass"]


def _venn_place(data: dict, centers: list[tuple[float, float]]) -> None:
    R = 90.0
    circles = [e for e in _els(data) if e["type"] == "ellipse"]
    for el, (cx, cy) in zip(circles, centers):
        el["x"], el["y"] = cx - R, cy - R


def test_venn_loose_overlap_has_no_shared_center():
    # Three circles overlapping pairwise in a near-flat row, but too spread to
    # share a central region — the "loose Venn" failure mode.
    data = _seed("arrange-the-venn")
    _venn_place(data, [(420, 400), (580, 400), (500, 410)])
    result = _grade("arrange-the-venn", data)
    assert result["result"] == 0
    assert result["metadata"]["rubrics"]["all_pairs_overlap"]["pass"]
    assert not result["metadata"]["rubrics"]["shared_center"]["pass"]


def test_venn_concentric_stack_fails():
    # Piling all three on the same spot trivially "shares" a region — forbidden.
    data = _seed("arrange-the-venn")
    _venn_place(data, [(500, 400), (508, 402), (495, 405)])
    result = _grade("arrange-the-venn", data)
    assert result["result"] == 0
    assert not result["metadata"]["rubrics"]["centers_distinct"]["pass"]


def test_venn_giant_circle_hack_fails():
    # Blowing one circle up to swallow the others is caught by radii_unchanged.
    data = _seed("arrange-the-venn")
    circles = [e for e in _els(data) if e["type"] == "ellipse"]
    circles[0]["width"] = circles[0]["height"] = 600
    circles[0]["x"], circles[0]["y"] = 200, 100
    circles[1]["x"], circles[1]["y"] = 560 - 90, 350 - 90
    circles[2]["x"], circles[2]["y"] = 620 - 90, 350 - 90
    result = _grade("arrange-the-venn", data)
    assert result["result"] == 0
    assert not result["metadata"]["rubrics"]["radii_unchanged"]["pass"]


def _row_boxes(data: dict) -> list[dict]:
    return [e for e in _els(data) if e["type"] == "rectangle"]


def _place_row(data: dict, coords: list[tuple[float, float]]) -> None:
    for el, (x, y) in zip(_row_boxes(data), coords):
        el["x"], el["y"] = x, y


def test_row_tops_misaligned_fails():
    # Evenly spaced but one box's top is off — the precision the task demands.
    data = _seed("align-the-row")
    _place_row(data, [(100 + 160 * i, 200) for i in range(5)])
    _row_boxes(data)[2]["y"] += 30
    result = _grade("align-the-row", data)
    assert result["result"] == 0
    assert not result["metadata"]["rubrics"]["tops_aligned"]["pass"]


def test_row_uneven_gaps_fails():
    # Tops aligned but the last gap is larger — a hand-eyeballed row.
    data = _seed("align-the-row")
    _place_row(data, [(100, 200), (260, 200), (420, 200), (580, 200), (800, 200)])
    result = _grade("align-the-row", data)
    assert result["result"] == 0
    assert not result["metadata"]["rubrics"]["evenly_spaced"]["pass"]


def test_row_stacked_overlap_fails():
    # Piling the boxes on one spot is not a row.
    data = _seed("align-the-row")
    _place_row(data, [(300, 200)] * 5)
    result = _grade("align-the-row", data)
    assert result["result"] == 0
    assert not result["metadata"]["rubrics"]["in_a_row_no_overlap"]["pass"]


def test_style_duplicate_reference_hack_fails():
    # Copy of reference placed at target's position: style matches, geometry doesn't.
    data = _seed("match-the-style")
    ref, target = _style_rects(data)
    clone = copy.deepcopy(ref)
    clone["id"] = "cloned-reference"
    clone["x"], clone["y"] = target["x"], target["y"]
    _els(data).remove(target)
    _els(data).append(clone)
    result = _grade("match-the-style", data)
    assert result["result"] == 0
    assert not result["metadata"]["rubrics"]["geometry_unchanged"]["pass"]


def test_align_row_hand_dragged_uneven_gaps_fails():
    # Aligned tops but unequal gaps (the dominant agent failure) must fail the
    # evenly_spaced rubric.
    data = _seed("align-the-row")
    rects = sorted((e for e in _els(data) if e["type"] == "rectangle"), key=lambda e: e["x"])
    x = 100
    gaps = [40, 60, 40, 80]  # deliberately uneven
    for i, el in enumerate(rects):
        el["x"], el["y"] = x, 200
        x += el["width"] + (gaps[i] if i < len(gaps) else 50)
    result = _grade("align-the-row", data)
    assert result["result"] == 0
    assert not result["metadata"]["rubrics"]["evenly_spaced"]["pass"]
