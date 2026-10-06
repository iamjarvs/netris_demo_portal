#!/usr/bin/env bash
# ==============================================================================
# Open Remote Netris Terraform Files in VS Code
# Target: ubuntu@adam-ctl.netris.io:~/netris-init/netris-spectrum-x-init
# ==============================================================================
set -e

HOST="${1:-ubuntu@adam-ctl.netris.io}"
REMOTE_PATH="${2:-/home/ubuntu/netris-init/netris-spectrum-x-init}"
CODE_BIN="$(command -v code || echo "/opt/homebrew/bin/code")"

echo "================================================================="
echo "      Netris Remote Terraform Explorer (VS Code Remote-SSH)      "
echo "================================================================="
echo " Target Host:       $HOST"
echo " Remote Path:       $REMOTE_PATH"
echo " Netris Controller: https://adam-ctl.netris.io"
echo " Netris Web User:   netris (or admin)"
echo " Netris Password:   913QGAi6oQTSGgZm20eU"
echo " SSH Username:      ubuntu (SSH Key)"
echo "================================================================="
echo "Executing: $CODE_BIN --remote ssh-remote+$HOST $REMOTE_PATH"
echo "================================================================="

# Launch in background
nohup "$CODE_BIN" --remote "ssh-remote+$HOST" "$REMOTE_PATH" >/dev/null 2>&1 &

echo "[SUCCESS] VS Code launched in background."
