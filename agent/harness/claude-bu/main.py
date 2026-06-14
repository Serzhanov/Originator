"""Claude computer use (browser) harness for Excalidraw tasks."""

from __future__ import annotations

from typing import Any

from playwright.sync_api import sync_playwright

from .browser import BrowserTool
from .loop import run_loop


def run(
    url: str,
    seed: dict[str, Any],
    prompt: str,
    model: str,
    headless: bool = True,
    max_steps: int = 100,
) -> dict[str, Any]:
    """Run the task and return state, screenshots, and transcript."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1400, "height": 850})
        page = context.new_page()
        page.goto(url)
        page.wait_for_function("() => typeof window.seed === 'function'", timeout=15000)

        screenshot_pre_seed = page.screenshot()

        page.evaluate("(seed) => window.seed(seed)", seed)

        screenshot_post_seed = page.screenshot()

        # Deselect everything before handing off to the agent
        page.keyboard.press("Escape")

        tool = BrowserTool(page)
        result = run_loop(tool, prompt, model, max_steps)

        # Commit any in-progress edits before capturing state
        page.keyboard.press("Escape")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        screenshot_post_attempt = page.screenshot()
        state = page.evaluate("() => window.getState()")

        browser.close()

    return {
        "state": state,
        "transcript_json": _serialize_messages(result["messages"]),
        "transcript_html": None,
        "screenshot_pre_seed": screenshot_pre_seed,
        "screenshot_post_seed": screenshot_post_seed,
        "screenshot_post_attempt": screenshot_post_attempt,
    }


def _serialize_messages(messages: list[dict]) -> list[dict]:
    """Serialize Anthropic SDK message objects to JSON-safe dicts, stripping binary image data."""
    out = []
    for msg in messages:
        content = msg["content"]
        if isinstance(content, str):
            out.append({"role": msg["role"], "content": content})
            continue
        safe = []
        for block in content:
            if hasattr(block, "type"):
                # Anthropic SDK content block object
                if block.type == "text":
                    safe.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    safe.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
            elif isinstance(block, dict):
                if block.get("type") == "tool_result":
                    # Keep text and image content (images are already base64-encoded)
                    kept = [c for c in block.get("content", []) if c.get("type") in ("text", "image")]
                    safe.append({**block, "content": kept})
                else:
                    safe.append(block)
        out.append({"role": msg["role"], "content": safe})
    return out
