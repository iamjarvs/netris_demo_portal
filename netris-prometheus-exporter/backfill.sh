#!/usr/bin/env bash
# ==============================================================================
# Netris Prometheus TSDB Backfill Launcher
# Pre-populates Prometheus TSDB with historical telemetry (default: 90 minutes)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MINUTES="${1:-90}"
STEP="${2:-60}"

if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
else
    PYTHON_CMD="python3"
fi

$PYTHON_CMD backfill.py --minutes "$MINUTES" --step "$STEP"
