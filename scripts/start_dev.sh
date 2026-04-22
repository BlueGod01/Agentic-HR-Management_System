#!/usr/bin/env bash
# ============================================================
# Start Development Servers (Backend + Frontend)
# Usage: bash scripts/start_dev.sh
# ============================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Must be run from repo root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".env" ]; then
  echo "❌ .env not found. Run: bash scripts/setup_dev.sh first"
  exit 1
fi

echo ""
echo -e "${BLUE}🚀 Starting Agentic AI HR System (Dev Mode)${NC}"
echo ""

# ── Backend ───────────────────────────────────────────────────────────────────
start_backend() {
  echo -e "${GREEN}[Backend]${NC} Starting FastAPI on http://localhost:8000"
  cd "$ROOT_DIR/backend"
  source venv/bin/activate
  cp "$ROOT_DIR/.env" .env 2>/dev/null || true
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

# ── Frontend ──────────────────────────────────────────────────────────────────
start_frontend() {
  echo -e "${GREEN}[Frontend]${NC} Starting Vite on http://localhost:5173"
  cd "$ROOT_DIR/frontend"
  npm run dev
}

# Export .env vars for backend
set -a
source "$ROOT_DIR/.env"
set +a

# Launch both in background, kill both on Ctrl+C
trap 'echo ""; echo "Shutting down..."; kill 0' EXIT INT TERM

start_backend &
BACKEND_PID=$!

sleep 2  # Give backend a moment to start
start_frontend &
FRONTEND_PID=$!

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Employee UI  →  http://localhost:5173       ║"
echo "║  API Docs     →  http://localhost:8000/docs  ║"
echo "║  Health       →  http://localhost:8000/health║"
echo "║  Press Ctrl+C to stop all servers            ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

wait
