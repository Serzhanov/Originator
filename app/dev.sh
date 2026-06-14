#!/usr/bin/env bash
# Dev server: Fastify backend on :31464, Vite HMR on :3001
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

cleanup() { kill $BACKEND_PID $VITE_PID 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Kill anything already on these ports
lsof -ti:31464 -ti:3001 | xargs kill -9 2>/dev/null || true

PORT=31464 node_modules/.bin/tsx watch backend/main.ts &
BACKEND_PID=$!

sleep 2

node_modules/.bin/vite --config vite.config.mts &
VITE_PID=$!

echo ""
echo "[dev] Backend: http://localhost:31464"
echo "[dev] Frontend: http://localhost:3001"
echo "[dev] Press Ctrl+C to stop"

wait
