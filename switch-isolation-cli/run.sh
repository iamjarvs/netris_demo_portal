#!/usr/bin/env bash
# ==============================================================================
# Netris Switch & Fabric Isolation CLI Utility Launcher
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Ensure venv exists with all required dependencies
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet questionary rich paramiko asyncssh
fi

# Make sure all scripts are executable
chmod +x "$SCRIPT_DIR/isolation_tool.py" "$SCRIPT_DIR/run.sh" 2>/dev/null || true

# Execute the primary isolation tool
exec "$VENV_DIR/bin/python3" "$SCRIPT_DIR/isolation_tool.py" "$@"
