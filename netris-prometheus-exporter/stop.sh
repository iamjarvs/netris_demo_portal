#!/usr/bin/env bash
# ==============================================================================
# Netris Observability Stack Shutdown Script
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[*] Stopping Netris Observability Stack..."

if command -v docker > /dev/null 2>&1 && docker info > /dev/null 2>&1; then
    docker compose down
fi

if [ -f ".exporter.pid" ]; then
    PID=$(cat .exporter.pid)
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "[*] Terminating local exporter PID $PID..."
        kill "$PID" 2>/dev/null || true
    fi
    rm -f .exporter.pid
fi

echo "[+] Stack stopped."
