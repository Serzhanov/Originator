"""CLI for excalidraw calibration tools.

Commands:
    calibration run --task <name> [--attempts N] [--model M] [--docker] [--gym-url URL]
    calibration run-graders --task <name>
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
load_dotenv(_ROOT / ".env")

_TASKS_DIR = _ROOT / "curriculum" / "tasks"
_CALIBRATION_DIR = _ROOT / "calibration"
_DOCKER_IMAGE = "excalidraw-agent"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}


def _save_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _resolve_task(name: str) -> Path:
    task_dir = _TASKS_DIR / name
    if task_dir.is_dir():
        return task_dir
    raise ValueError(f"Unknown task {name!r}. Tasks live in curriculum/tasks/.")


def _load_grader_fn(task_dir: Path):
    grader_path = task_dir / "grader.py"
    if not grader_path.exists():
        raise FileNotFoundError(f"grader.py not found in {task_dir}")
    spec = importlib.util.spec_from_file_location("_grader", grader_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.grader


def _run_grader(grader_fn, json_path: Path) -> dict:
    data = json.loads(json_path.read_text())
    return grader_fn({
        "snapshots": {"excalidraw": data},
        "transcript": "",
        "extra_fields": {},
        "posted_answer": None,
    })


def _print_result(label: str, result: dict, expected: int, passed: bool) -> None:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label}: result={result['result']} (expected {expected})")
    for name, rubric in result.get("metadata", {}).get("rubrics", {}).items():
        mark = "+" if rubric.get("pass") else "-"
        desc = rubric.get("message") or rubric.get("description", "")
        suffix = f": {desc}" if desc else ""
        print(f"         {mark} {name}{suffix}")


# ---------------------------------------------------------------------------
# run-graders
# ---------------------------------------------------------------------------

def cmd_run_graders(args) -> None:
    task_dir = _resolve_task(args.task)
    print(f"\n=== {task_dir.name} ===")
    grader_fn = _load_grader_fn(task_dir)
    all_passed = True

    # seed.json should fail (initial state, task not yet done)
    seed_path = task_dir / "seed.json"
    if seed_path.exists():
        result = _run_grader(grader_fn, seed_path)
        passed = result["result"] == 0
        _print_result("seed.json", result, expected=0, passed=passed)
        all_passed = all_passed and passed

    # Re-grade all recorded agent runs
    execs_dir = task_dir / ".execs"
    if execs_dir.exists():
        for model_dir in sorted(execs_dir.iterdir()):
            if not model_dir.is_dir() or model_dir.name == "manual":
                continue
            for run_dir in sorted(d for d in model_dir.iterdir() if d.is_dir()):
                output_path = run_dir / "output.json"
                if not output_path.exists():
                    continue
                result = _run_grader(grader_fn, output_path)
                (run_dir / "grade.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
                label = f".execs/{model_dir.name}/{run_dir.name}/output.json"
                _print_result(label, result, expected=result["result"], passed=True)

    sys.exit(0 if all_passed else 1)


# ---------------------------------------------------------------------------
# run-calibration
# ---------------------------------------------------------------------------

def _run_attempt(args, task_name: str, attempt: int) -> dict:
    print(f"\n[ex] Attempt {attempt}/{args.attempts}  task={task_name!r}  model={args.model}")

    task_dir = _resolve_task(task_name)
    runs_dir = task_dir / ".execs" / args.model
    existing = {p.resolve() for p in runs_dir.iterdir()} if runs_dir.exists() else set()

    if args.docker:
        cmd = [
            "docker", "run", "--rm",
            "-e", f"TASK={task_name}",
            "-e", "HARNESS=claude-bu",
            "-e", f"MODEL={args.model}",
            "-e", f"GYM_URL={args.gym_url}",
            "-v", f"{_ROOT / 'tasks'}:/workspace/tasks",
        ]
        if "OPENROUTER_API_KEY" in os.environ:
            cmd += ["-e", f"OPENROUTER_API_KEY={os.environ['OPENROUTER_API_KEY']}"]
        cmd.append(_DOCKER_IMAGE)
        subprocess.run(cmd, cwd=_ROOT)
    else:
        env = {**os.environ, "GYM_URL": args.gym_url, "PYTHONPATH": str(_ROOT)}
        script = (
            "import sys;"
            f"sys.path.insert(0,{str(_ROOT)!r});"
            "from agent.main import run;"
            f"r=run(task={task_name!r},harness='claude-bu',model={args.model!r});"
            "sys.exit(0 if r['grade']==1 else 1)"
        )
        subprocess.run(["uv", "run", "python", "-c", script], cwd=_ROOT, env=env)

    runs_dir.mkdir(parents=True, exist_ok=True)
    new_dirs = [d for d in runs_dir.iterdir() if d.resolve() not in existing and d.is_dir()]
    if not new_dirs:
        print(f"[ex] WARNING: no run directory found for attempt {attempt}")
        return {"graded": False, "score": None, "failed_rubrics": []}

    run_dir = max(new_dirs, key=lambda d: d.stat().st_mtime)
    grade_path = run_dir / "grade.json"
    if not grade_path.exists():
        print(f"[ex] WARNING: no grade.json in {run_dir.name}")
        return {"graded": False, "score": None, "failed_rubrics": []}

    grade = json.loads(grade_path.read_text())
    score = grade["result"]
    rubrics = grade.get("metadata", {}).get("rubrics", {})
    failed = [
        {"name": k, "message": v.get("message") or v.get("description", "")}
        for k, v in rubrics.items()
        if not v.get("pass", True)
    ]
    message = "; ".join(
        f"{r['name']}: {r['message']}" if r.get("message") else r["name"]
        for r in failed
    ) if failed else None

    print(f"[ex] score={score}" + (f"  failed: {message}" if message else "  all pass"))

    try:
        rel = str(run_dir.relative_to(_ROOT))
    except ValueError:
        rel = str(run_dir)
    return {"graded": True, "score": score, "message": message, "run_dir": rel}


def _check_gym_reachable(url: str) -> None:
    try:
        urllib.request.urlopen(url, timeout=3)
    except (urllib.error.URLError, OSError):
        print(f"ERROR: Cannot reach the Excalidraw app at {url}")
        print("       Start it first with:  ./app/dev.sh")
        print("       Or pass a different URL with:  --gym-url <url>")
        sys.exit(1)


def cmd_run_calibration(args) -> None:
    task_name = args.task

    if not args.docker:
        _check_gym_reachable(args.gym_url)

    if args.docker and not args.no_build:
        print(f"[ex] Building {_DOCKER_IMAGE}...")
        subprocess.run(["docker", "build", "-t", _DOCKER_IMAGE, "."], cwd=_ROOT, check=True)

    results = [_run_attempt(args, task_name, i) for i in range(1, args.attempts + 1)]

    graded = [r for r in results if r.get("graded")]
    if not graded:
        print("[ex] WARNING: no graded attempts — calibration not written")
        return

    cal_path = _CALIBRATION_DIR / f"{args.model}.yaml"
    data = _load_yaml(cal_path)
    existing = data.get(task_name) or []
    if not isinstance(existing, list):
        existing = []  # migrate from old aggregate format

    for r in graded:
        entry: dict = {"path": r["run_dir"], "score": r["score"]}
        if r.get("message"):
            entry["message"] = r["message"]
        existing.append(entry)

    data[task_name] = existing
    _save_yaml(cal_path, data)

    total_score = sum(r["score"] for r in graded)
    n = len(graded)
    print(f"\n[ex] Calibration complete: {total_score}/{n}")
    print(f"[ex] Written to calibration/{args.model}.yaml")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Excalidraw calibration tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    cal = subparsers.add_parser("run", help="Run agent calibration on a task")
    cal.add_argument("--task", required=True, metavar="TASK", help="Task name (must exist in curriculum/tasks/)")
    cal.add_argument("--attempts", type=int, default=1, metavar="N", help="Number of attempts (default: 1)")
    cal.add_argument("--model", default="claude-sonnet-4-6", help="Model (default: claude-sonnet-4-6)")
    cal.add_argument("--gym-url", default="http://localhost:3001", metavar="URL")
    cal.add_argument("--docker", action="store_true", help="Run inside Docker")
    cal.add_argument("--no-build", action="store_true", help="Skip docker build step")

    grade = subparsers.add_parser("run-graders", help="Run graders on recorded agent execs")
    grade.add_argument("--task", required=True, metavar="TASK")

    args = parser.parse_args()
    {"run": cmd_run_calibration, "run-graders": cmd_run_graders}[args.command](args)


if __name__ == "__main__":
    main()
