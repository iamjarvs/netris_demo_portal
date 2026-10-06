#!/usr/bin/env bash
# =============================================================================
# Fabric Terraform Builder — One-Click Startup Script
# =============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-5050}"

echo "========================================================"
echo " Starting Netris Fabric Terraform Builder UI"
echo " Location: $DIR"
echo "========================================================"

# Check if frontend is built
if [ ! -d "$DIR/frontend/dist" ]; then
    echo "[1/3] Building frontend assets..."
    cd "$DIR/frontend"
    npm install
    npm run build
    cd "$DIR"
else
    echo "[1/3] Frontend production build found in frontend/dist."
fi

# Launch backend
echo "[2/3] Launching Flask server on http://localhost:$PORT ..."
cd "$DIR/backend"

# Open browser after 1.5s in background
(sleep 1.5 && open "http://localhost:$PORT" 2>/dev/null || true) &

# Run server
exec python3 app.py
