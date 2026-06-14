"""
Grader: Screenshot Hello Joe

Verifies that the canvas still contains the original "Hello Joe" text in red
after the agent runs (i.e., the agent did not modify the canvas).

Rubrics:
- hello_joe_text_preserved: A text element with "Hello Joe" still exists
- hello_joe_is_red: The text element stroke color is still red (#e03131)
"""

import sys
import json
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_root))

from curriculum import GraderInput, rubricgrader, rubrics


@rubricgrader
def grader(input: GraderInput):
    elements = [
        el for el in input["snapshots"]["excalidraw"].get("elements", [])
        if not el.get("isDeleted", False)
    ]
    text_els = [el for el in elements if el.get("type") == "text" and el.get("text") == "Hello Joe"]

    rubrics.assertTrue(
        "hello_joe_text_preserved",
        len(text_els) >= 1,
        success='Text element "Hello Joe" is still present on the canvas',
        failure='Text element "Hello Joe" was removed or not found',
    )

    el = text_els[0] if text_els else None
    rubrics.assertTrue(
        "hello_joe_is_red",
        el is not None and el.get("strokeColor", "").lower() == "#e03131",
        success='Text "Hello Joe" stroke color is still red (#e03131)',
        failure=(
            "No text element to check color."
            if not el else
            f'Expected strokeColor #e03131, got {el.get("strokeColor")!r}'
        ),
    )


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "seed.json"
    with open(path) as f:
        data = json.load(f)
    result = grader({"snapshots": {"excalidraw": data}, "transcript": "", "extra_fields": {}, "posted_answer": None})
    print(f"result={result['result']}")
    for k, v in result["metadata"]["rubrics"].items():
        print(f"  {'PASS' if v['pass'] else 'FAIL'} {k}: {v.get('message') or v.get('description', '')}")
