"""curriculum.py — grader interface: GraderInput, rubricgrader, rubrics."""

from __future__ import annotations

import functools
from typing import Any, Callable, TypedDict

Rubric = TypedDict("Rubric", {"pass": bool, "expected": Any, "actual": Any, "description": str, "message": str})


class Grade(TypedDict, total=False):
    result: int | float
    debug: str
    metadata: dict[str, Any]


class GraderInput(TypedDict):
    snapshots: dict[str, Any]
    transcript: str
    extra_fields: dict[str, Any]
    posted_answer: dict | None


def grade(value: int | float, debug: str, metadata: dict[str, Any] | None = None) -> Grade:
    result: Grade = {"result": value, "debug": debug}
    if metadata is not None:
        result["metadata"] = metadata
    return result


def score_rubrics(rubrics_dict: dict[str, Rubric]) -> int:
    return 1 if all(r["pass"] for r in rubrics_dict.values()) else 0


def pretty_print(rubrics_dict: dict[str, Rubric]) -> str:
    lines = []
    for key, r in rubrics_dict.items():
        symbol = "PASS" if r["pass"] else "FAIL"
        message = r.get("message", "")
        if message:
            lines.append(f"{symbol} {key}: {message}")
        else:
            description = r.get("description", "")
            desc_suffix = f" ({description})" if description else ""
            lines.append(f"{symbol} {key}: expected {r['expected']!r}, got {r['actual']!r}{desc_suffix}")
    return "\n".join(lines)


class RubricCollector:
    def __init__(self) -> None:
        self._rubrics: dict[str, Rubric] = {}

    def assertTrue(self, name: str, condition: bool, description: str = "", *,
                   success: str = "", failure: str = "") -> None:
        passed = condition is True
        self._rubrics[name] = {
            "pass": passed,
            "expected": True,
            "actual": condition,
            "description": description,
            "message": success if passed else failure,
        }

    def assertEquals(self, name: str, expected: Any, actual: Any, description: str = "", *,
                     success: str = "", failure: str = "") -> None:
        passed = expected == actual
        self._rubrics[name] = {
            "pass": passed,
            "expected": expected,
            "actual": actual,
            "description": description,
            "message": success if passed else failure,
        }

    def get_rubrics(self) -> dict[str, Rubric]:
        return self._rubrics.copy()

    def reset(self) -> None:
        self._rubrics.clear()


def rubricgrader(func: Callable[[GraderInput], Any]) -> Callable[[GraderInput], Grade]:
    @functools.wraps(func)
    def wrapper(input: GraderInput) -> Grade:
        rubrics.reset()
        func(input)
        collected = rubrics.get_rubrics()
        return grade(score_rubrics(collected), pretty_print(collected), metadata={"rubrics": collected})
    return wrapper


rubrics = RubricCollector()
