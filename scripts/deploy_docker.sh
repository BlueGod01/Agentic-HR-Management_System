#!/usr/bin/env bash
# ============================================================
# Production Docker Deploy
# Usage: bash scripts/deploy_docker.sh
# ============================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "🐳 Building and deploying via Docker Compose..."

if [ ! -f ".env" ]; then
  echo "❌ .env not found. Copy .env.example to .env and fill in keys."
  exit 1
fi

# Build fresh images
docker compose build --no-cache

# Start in detached mode
docker compose up -d

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  Deployment complete!                    ║"
echo "║  App:     http://localhost               ║"
echo "║  API:     http://localhost/api/v1        ║"
echo "║  Logs:    docker compose logs -f         ║"
echo "║  Stop:    docker compose down            ║"
echo "╚══════════════════════════════════════════╝"
