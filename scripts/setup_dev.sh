#!/usr/bin/env bash
# ============================================================
# Agentic AI HR System - Local Development Setup
# Usage: bash scripts/setup_dev.sh
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info() { echo -e "${BLUE}[→]${NC} $1"; }

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    Agentic AI HR System - Dev Setup      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Check requirements ────────────────────────────────────────────────────────
info "Checking prerequisites..."
command -v python3 &>/dev/null || err "Python 3 is required"
command -v node    &>/dev/null || err "Node.js is required"
command -v npm     &>/dev/null || err "npm is required"
log "Prerequisites OK"

# ── .env setup ────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  warn ".env not found — copying from .env.example"
  cp .env.example .env
  warn "⚠️  Please edit .env and add your GOOGLE_API_KEY before running the app!"
else
  log ".env already exists"
fi

# ── Backend setup ─────────────────────────────────────────────────────────────
info "Setting up Python backend..."
cd backend

if [ ! -d "venv" ]; then
  python3 -m venv venv
  log "Virtual environment created"
fi

source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
log "Python dependencies installed"

cd ..

# ── Frontend setup ────────────────────────────────────────────────────────────
info "Setting up React frontend..."
cd frontend
npm install --silent
log "Node dependencies installed"
cd ..

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║             Setup Complete! 🎉               ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Edit .env → add GOOGLE_API_KEY              ║${NC}"
echo -e "${GREEN}║  Then run:  bash scripts/start_dev.sh        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
