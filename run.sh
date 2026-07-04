#!/usr/bin/env bash
# Starts the backend (port 8000) and frontend (port 5173) together.
# Stop both with Ctrl+C.
set -e
cd "$(dirname "$0")"

# Make sure a modern Node (Homebrew's) is used, not an old system one.
export PATH="/opt/homebrew/bin:$PATH"

echo "starting backend on http://localhost:8000 ..."
( cd backend && uv run uvicorn app.main:app --port 8000 ) &
BACKEND_PID=$!
trap "echo; echo 'stopping...'; kill $BACKEND_PID 2>/dev/null" EXIT

echo "starting frontend on http://localhost:5173 ..."
cd frontend && npm run dev
