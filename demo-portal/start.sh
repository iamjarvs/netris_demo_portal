#!/usr/bin/env bash
# ==============================================================================
# Demo Command Center Launcher (Port 8800)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-8800}"
HOST="${HOST:-0.0.0.0}"

BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
CORAL="\033[0;31m"
NC="\033[0m"

echo -e "${BOLD}${CORAL}"
echo "========================================================================"
echo "                     DEMO COMMAND CENTER                                "
echo "========================================================================"
echo -e "${NC}"

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo -e "[*] Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

PYTHON_BIN=".venv/bin/python"
PIP_BIN=".venv/bin/pip"
UVICORN_BIN=".venv/bin/uvicorn"

# Install requirements if uvicorn is missing
if [ ! -f "$UVICORN_BIN" ]; then
    echo -e "[*] Installing dependencies from requirements.txt..."
    "$PIP_BIN" install --upgrade pip
    "$PIP_BIN" install -r requirements.txt
fi

echo -e "[*] Starting Demo Command Center on ${BOLD}${GREEN}http://localhost:${PORT}${NC}..."
echo -e "[*] Press Ctrl+C to stop the portal.\n"

exec "$UVICORN_BIN" app.main:app --host "$HOST" --port "$PORT" --reload
