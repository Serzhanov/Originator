"""Claude agent loop."""

from __future__ import annotations

from typing import Any

import os

import anthropic

from .browser import BrowserTool

BROWSER_TOOL: dict[str, Any] = {
    "name": "browser",
    "description": "Controls Chrome via DevTools Protocol. For web automation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate", "screenshot", "left_click", "right_click", "middle_click",
                    "double_click", "triple_click", "left_click_drag", "left_mouse_down",
                    "left_mouse_up", "scroll", "scroll_to", "type", "press_key", "key",
                    "hold_key", "read_page", "get_page_text", "wait", "form_input", "zoom",
                    "create_tab", "close_tab", "switch_tab", "list_tabs",
                ],
            },
            "url": {"type": "string"},
            "text": {"type": "string"},
            "ref": {"type": "string"},
            "coordinate": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
            "start_coordinate": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
            "scroll_direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
            "scroll_amount": {"type": "number"},
            "duration": {"type": "number"},
            "value": {"type": "string"},
            "selector": {"type": "string"},
            "filter": {"type": "string"},
            "region": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
            "repeat": {"type": "integer", "default": 1},
            "tabId": {"type": "string"},
        },
        "required": ["action"],
    },
}


def _fmt_tool(tc: Any) -> str:
    action = tc.input.get("action", "?")
    extras = []
    for key in ("url", "text", "coordinate", "selector", "ref"):
        val = tc.input.get(key)
        if val is not None:
            s = str(val)
            extras.append(f"{key}={s[:60]!r}" if len(s) > 60 else f"{key}={s!r}")
    return f"{action}({', '.join(extras)})" if extras else action


# Static tools list with a cache breakpoint at the end. The breakpoint caches
# the tools + system prefix so it's a hit on every step after the first.
_TOOLS_CACHED = [{**BROWSER_TOOL, "cache_control": {"type": "ephemeral"}}]


def _mark_latest_user_message_for_caching(messages: list[dict]) -> None:
    # Roll one breakpoint forward each step: clear any prior cache_control on
    # user messages, then place a fresh one on the last block of the last user
    # message. Two effects: (1) the prefix [prompt + all prior turns] is a cache
    # hit on the next call, (2) we never accumulate more than 2 breakpoints
    # (one on tools, one on the latest user message) — well under OpenRouter's
    # 4-per-request limit.
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    block.pop("cache_control", None)

    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, list) and content:
            last_block = content[-1]
            if isinstance(last_block, dict):
                last_block["cache_control"] = {"type": "ephemeral"}
        return


def run_loop(
    browser: BrowserTool,
    prompt: str,
    model: str,
    max_steps: int = 100,
) -> dict[str, Any]:
    client = anthropic.Anthropic(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api",
    )
    # Initial user message in block form so we can attach cache_control to it.
    messages: list[dict] = [
        {"role": "user", "content": [{"type": "text", "text": prompt}]}
    ]

    for step in range(1, max_steps + 1):
        print(f"  step {step}", flush=True)
        or_model = f"anthropic/{model}" if "/" not in model else model
        _mark_latest_user_message_for_caching(messages)
        response = client.messages.create(
            model=or_model,
            max_tokens=4096,
            messages=messages,
            tools=_TOOLS_CACHED,
        )

        usage = getattr(response, "usage", None)
        if usage is not None:
            cr = getattr(usage, "cache_read_input_tokens", 0) or 0
            cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
            it = getattr(usage, "input_tokens", 0) or 0
            ot = getattr(usage, "output_tokens", 0) or 0
            print(
                f"    usage: input={it} output={ot} cache_read={cr} cache_write={cw}",
                flush=True,
            )

        assistant_content = list(response.content)
        tool_calls = [b for b in response.content if b.type == "tool_use"]

        for block in assistant_content:
            if hasattr(block, "type") and block.type == "text" and block.text.strip():
                preview = block.text.strip().replace("\n", " ")[:120]
                print(f"    > {preview}", flush=True)

        messages.append({"role": "assistant", "content": assistant_content})

        if not tool_calls:
            print(f"  done (stop_reason={response.stop_reason})", flush=True)
            break

        tool_results = []
        for tc in tool_calls:
            print(f"    tool: {_fmt_tool(tc)}", flush=True)
            result = browser.execute(**tc.input)
            content = []
            for c in result.get("content", []):
                if c["type"] == "text":
                    content.append({"type": "text", "text": c["text"]})
                elif c["type"] == "image":
                    content.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": c["mimeType"], "data": c["data"]},
                    })
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "is_error": result.get("is_error", False),
                "content": content,
            })

        messages.append({"role": "user", "content": tool_results})

    return {"messages": messages}
