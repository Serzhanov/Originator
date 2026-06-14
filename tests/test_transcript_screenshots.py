"""Tests for agent run artifacts and transcript screenshot data.

Existing tests (test_screenshot_results_have_image_data) validate that
screenshot tool calls have base64 image data in their tool_results, by
reading the latest recorded exec for known tasks.

Integration test (TestScreenshotHelloJoe) actually launches the agent
against a live gym, runs the screenshot-hello-joe task, and asserts:
  - all expected artifact files are written
  - transcript.json contains base64 images in tool_results
  - the agent's text description mentions "Hello Joe" and describes it as red
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_TEST_TASKS_DIR = Path(__file__).resolve().parent / "task"

sys.path.insert(0, str(_ROOT))


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _tool_result_image_ids(messages: list[dict]) -> set[str]:
    """Return tool_use_ids whose tool_result contains at least one image with base64 data."""
    ids = set()
    for msg in messages:
        if msg.get("role") != "user":
            continue
        for block in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
            if block.get("type") != "tool_result":
                continue
            for c in block.get("content", []):
                if (
                    c.get("type") == "image"
                    and c.get("source", {}).get("type") == "base64"
                    and c.get("source", {}).get("data")
                ):
                    ids.add(block["tool_use_id"])
                    break
    return ids


def _assistant_text(messages: list[dict]) -> str:
    """Concatenate all assistant text blocks into a single lowercase string."""
    parts = []
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "text":
                parts.append(block["text"])
    return " ".join(parts).lower()


# ---------------------------------------------------------------------------
# Integration: screenshot-hello-joe
# ---------------------------------------------------------------------------

_TASK = str(_TEST_TASKS_DIR / "screenshot-hello-joe")
_MODEL = "claude-sonnet-4-6"
_ARTIFACT_FILES = [
    "prompt.txt",
    "seed.json",
    "output.json",
    "grade.json",
    "transcript.json",
    "transcript.html",
]


@pytest.fixture(scope="module")
def hello_joe_run():
    """Run the agent once for the whole module; skip if gym is unreachable."""
    gym_url = os.environ.get("GYM_URL", "http://localhost:3001")
    try:
        urllib.request.urlopen(gym_url, timeout=3)
    except (urllib.error.URLError, OSError):
        pytest.skip(f"Gym not reachable at {gym_url} — start it with ./dev.sh")

    from agent.main import run
    return run(task=_TASK, model=_MODEL)


def test_all_artifacts_created(hello_joe_run):
    run_dir = Path(hello_joe_run["run_dir"])
    missing = [f for f in _ARTIFACT_FILES if not (run_dir / f).exists()]
    assert not missing, f"Missing artifact files in {run_dir}: {missing}"


def test_transcript_has_images(hello_joe_run):
    run_dir = Path(hello_joe_run["run_dir"])
    messages = json.loads((run_dir / "transcript.json").read_text(encoding="utf-8"))
    image_ids = _tool_result_image_ids(messages)
    assert image_ids, "No base64 images found in transcript tool_results"


def test_transcript_describes_red_hello_joe(hello_joe_run):
    run_dir = Path(hello_joe_run["run_dir"])
    messages = json.loads((run_dir / "transcript.json").read_text(encoding="utf-8"))
    text = _assistant_text(messages)
    assert "hello joe" in text, (
        "Transcript does not mention 'Hello Joe' — agent may not have described the canvas"
    )
    assert "red" in text, (
        "Transcript does not describe 'Hello Joe' as red — agent may not have noticed the color"
    )
