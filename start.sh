#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

# --- dependency checks ---
if [ ! -d "$DIR/backend/.venv" ]; then
  echo "ERROR: backend/.venv not found. Create it first:"
  echo "  cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [ ! -d "$DIR/frontend/node_modules" ]; then
  echo "ERROR: frontend/node_modules not found. Install dependencies first:"
  echo "  cd frontend && npm install"
  exit 1
fi

# --- cleanup on exit ---
cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
  wait 2>/dev/null
  echo "Done."
}
trap cleanup SIGINT SIGTERM EXIT

# --- start backend ---
echo "Starting backend (uvicorn) ..."
(
  cd "$DIR/backend"
  source .venv/bin/activate
  uvicorn app.main:app --reload --port 8000
) &
BACKEND_PID=$!

# --- start frontend ---
echo "Starting frontend (vite) ..."
(
  cd "$DIR/frontend"
  npm run dev
) &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both."

wait
