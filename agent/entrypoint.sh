#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

cleanup() { kill $BACKEND_PID $VITE_PID 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Virtual display (needed by Playwright even in headless mode on Linux)
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
sleep 1

# Start backend
echo "[entrypoint] Starting backend..."
PORT=31464 app/node_modules/.bin/tsx app/backend/main.ts &
BACKEND_PID=$!
sleep 3

# Start frontend
echo "[entrypoint] Starting frontend..."
app/node_modules/.bin/vite --config app/vite.config.mts &
VITE_PID=$!

# Wait for frontend
echo "[entrypoint] Waiting for http://localhost:3001..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:3001 > /dev/null 2>&1; then
    echo "[entrypoint] Frontend ready"
    break
  fi
  sleep 1
done

echo "[entrypoint] Running task: ${TASK} (model=${MODEL:-claude-sonnet-4-6})"
PYTHONPATH=/workspace uv run python - <<'EOF'
import json, os, sys
sys.path.insert(0, "/workspace")
from agent.main import run

result = run(
    task=os.environ["TASK"],
    harness=os.environ.get("HARNESS", "claude-bu"),
    model=os.environ.get("MODEL", "claude-sonnet-4-6"),
)
print(json.dumps(result, indent=2))
sys.exit(0 if result["grade"] == 1 else 1)
EOF
