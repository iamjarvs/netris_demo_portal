#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")"

PORT="${PORT:-8750}"
echo "[*] Stopping Netris Demo Tool on port ${PORT}..."

# Gracefully terminate any listener on the designated port
PID=$(lsof -ti:${PORT} 2>/dev/null || true)
if [ -n "$PID" ]; then
  kill -TERM $PID 2>/dev/null || true
  sleep 1
  kill -9 $PID 2>/dev/null || true
  echo "[✓] Stopped process PID ${PID}."
else
  echo "[*] No active process discovered on port ${PORT}."
fi
