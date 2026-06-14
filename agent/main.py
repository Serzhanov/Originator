"""Excalidraw agent runner.

Usage:
    from agent.main import run
    result = run(task="yellow-circle-in-blue-box", model="claude-sonnet-4-6")
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).resolve().parent.parent
_TASKS_DIR = _ROOT / "curriculum" / "tasks"


def run(task: str, harness: str = "claude-bu", model: str = "claude-sonnet-4-6") -> dict:
    harness_mod = importlib.import_module(f"agent.harness.{harness}.main")

    task_dir = _resolve_task(task)
    url, seed, prompt, grader = _load_task(task_dir)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final_dir = task_dir / ".execs" / model / timestamp
    tmp_dir = final_dir.parent / f".tmp_{timestamp}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    result = harness_mod.run(url=url, seed=seed, prompt=prompt, model=model)

    grade_result = grader({
        "snapshots": {"excalidraw": result["state"]},
        "transcript": "",
        "extra_fields": {},
        "posted_answer": None,
    })

    # Write all artifacts, then atomically rename into place
    (tmp_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    (tmp_dir / "seed.json").write_text(json.dumps(seed, indent=2), encoding="utf-8")
    (tmp_dir / "output.json").write_text(json.dumps(result["state"], indent=2), encoding="utf-8")
    (tmp_dir / "grade.json").write_text(json.dumps(grade_result, indent=2), encoding="utf-8")
    if result.get("transcript_json") is not None:
        (tmp_dir / "transcript.json").write_text(json.dumps(result["transcript_json"], indent=2), encoding="utf-8")
        screenshots = {
            k: result[k] for k in ("screenshot_pre_seed", "screenshot_post_seed", "screenshot_post_attempt")
            if result.get(k) is not None
        }
        html = result.get("transcript_html") or _build_transcript_html(result["transcript_json"], screenshots or None)
        (tmp_dir / "transcript.html").write_text(html, encoding="utf-8")
    for key, filename in (
        ("screenshot_pre_seed", "screenshot_pre_seed.png"),
        ("screenshot_post_seed", "screenshot_post_seed.png"),
        ("screenshot_post_attempt", "screenshot_post_attempt.png"),
    ):
        if result.get(key) is not None:
            (tmp_dir / filename).write_bytes(result[key])

    tmp_dir.rename(final_dir)
    run_dir = final_dir

    return {
        "run_dir": str(run_dir),
        "grade": grade_result["result"],
        "rubrics": {k: v["pass"] for k, v in grade_result.get("metadata", {}).get("rubrics", {}).items()},
    }


def _resolve_task(task: str) -> Path:
    p = Path(task)
    if p.is_absolute() and p.is_dir():
        return p
    task_dir = _TASKS_DIR / task
    if task_dir.is_dir():
        return task_dir
    raise ValueError(f"Unknown task {task!r}. Tasks live in curriculum/tasks/.")


def _load_task(task_dir: Path):
    with open(task_dir / "task.yaml") as f:
        raw = yaml.safe_load(f)
    prompt: str = raw["prompt"]["data"].strip()
    if raw.get("hints", {}).get("data", "").strip():
        prompt = prompt + "\n" + raw["hints"]["data"].strip()

    with open(task_dir / "seed.json") as f:
        seed = json.load(f)

    url = os.environ.get("GYM_URL", "http://localhost:3001")

    sys.path.insert(0, str(_ROOT))
    spec = importlib.util.spec_from_file_location("_grader", task_dir / "grader.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    return url, seed, prompt, mod.grader


def _build_transcript_html(messages: list[dict], screenshots: dict[str, bytes] | None = None) -> str:
    import base64
    import html as _html

    def _esc(s: str) -> str:
        return _html.escape(str(s))

    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        role_class = "user" if role == "user" else "assistant"

        if isinstance(content, str):
            parts.append(f'<div class="msg {role_class}"><span class="role">{_esc(role)}</span>'
                         f'<pre>{_esc(content)}</pre></div>')
            continue

        blocks: list[str] = []
        for block in content:
            btype = block.get("type", "")
            if btype == "text":
                blocks.append(f'<pre class="text">{_esc(block.get("text", ""))}</pre>')
            elif btype == "tool_use":
                inp = json.dumps(block.get("input", {}), indent=2, ensure_ascii=False)
                blocks.append(
                    f'<div class="tool-use">'
                    f'<span class="tool-name">tool_use: {_esc(block.get("name", ""))}</span>'
                    f'<pre>{_esc(inp)}</pre></div>'
                )
            elif btype == "tool_result":
                result_parts: list[str] = []
                for c in block.get("content", []):
                    if c.get("type") == "text":
                        result_parts.append(f'<pre>{_esc(c.get("text", ""))}</pre>')
                    elif c.get("type") == "image":
                        src = c.get("source", {})
                        if src.get("type") == "base64":
                            mime = src.get("media_type", "image/png")
                            result_parts.append(
                                f'<img src="data:{mime};base64,{src["data"]}"'
                                f' class="tool-screenshot">'
                            )
                blocks.append(f'<div class="tool-result"><span class="tool-name">tool_result</span>'
                               f'{"".join(result_parts)}</div>')
            else:
                blocks.append(f'<pre>{_esc(json.dumps(block, ensure_ascii=False))}</pre>')

        parts.append(f'<div class="msg {role_class}"><span class="role">{_esc(role)}</span>'
                     f'{"".join(blocks)}</div>')

    screenshot_labels = {
        "screenshot_post_seed": "Post-seed (agent start)",
        "screenshot_post_attempt": "Post-attempt (agent end)",
    }
    screenshot_html = ""
    if screenshots:
        imgs = []
        for key, label in screenshot_labels.items():
            if key in screenshots:
                b64 = base64.b64encode(screenshots[key]).decode()
                imgs.append(
                    f'<div class="screenshot">'
                    f'<span class="screenshot-label">{label}</span>'
                    f'<img src="data:image/png;base64,{b64}" alt="{label}">'
                    f'</div>'
                )
        if imgs:
            screenshot_html = '<div class="screenshots">' + "".join(imgs) + '</div>'

    body = "\n".join(parts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Transcript</title>
<style>
  body {{ font-family: monospace; font-size: 13px; background: #1e1e1e; color: #ccc; margin: 0; padding: 16px; }}
  .msg {{ border-left: 3px solid #555; margin: 8px 0; padding: 6px 10px; background: #252525; }}
  .msg.user {{ border-color: #4a9eff; }}
  .msg.assistant {{ border-color: #a8cc8c; }}
  .role {{ font-weight: bold; font-size: 11px; text-transform: uppercase; color: #888; display: block; margin-bottom: 4px; }}
  pre {{ margin: 0; white-space: pre-wrap; word-break: break-word; }}
  .tool-use {{ background: #2a2a3a; border-left: 2px solid #9b8dc4; margin: 4px 0; padding: 4px 8px; }}
  .tool-result {{ background: #2a3a2a; border-left: 2px solid #6aaf6a; margin: 4px 0; padding: 4px 8px; }}
  .tool-name {{ font-size: 11px; color: #aaa; display: block; margin-bottom: 2px; }}
  .tool-screenshot {{ max-width: 420px; display: block; margin: 4px 0; border: 1px solid #444; }}
  .screenshots {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }}
  .screenshot {{ display: flex; flex-direction: column; gap: 4px; }}
  .screenshot-label {{ font-size: 11px; color: #aaa; text-transform: uppercase; }}
  .screenshot img {{ max-width: 420px; border: 1px solid #444; }}
</style>
</head>
<body>{screenshot_html}{body}</body>
</html>"""
