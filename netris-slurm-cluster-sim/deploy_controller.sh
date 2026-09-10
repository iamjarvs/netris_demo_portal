#!/usr/bin/env bash
# ==============================================================================
# deploy_controller.sh - Sync & Deploy Slurm Integration to Netris Controller
# ==============================================================================

set -euo pipefail

CONTROLLER_HOST="ubuntu@adam-ctl.netris.io"
REMOTE_DIR="~/netris-slurm-sim"

echo "=== [1/3] Preparing files for deployment ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== [2/3] Syncing files to Netris Controller (${CONTROLLER_HOST}:${REMOTE_DIR}) ==="
ssh -o StrictHostKeyChecking=no "${CONTROLLER_HOST}" "mkdir -p ${REMOTE_DIR}"
rsync -avz --exclude='.git*' "${SCRIPT_DIR}/" "${CONTROLLER_HOST}:${REMOTE_DIR}/"

echo "=== [3/3] Setting permissions on Controller ==="
ssh -o StrictHostKeyChecking=no "${CONTROLLER_HOST}" "chmod +x ${REMOTE_DIR}/*.py ${REMOTE_DIR}/*.sh"

echo ""
echo "================================================================="
echo " Deployment Complete!"
echo " To run on controller directly:"
echo "   ssh ${CONTROLLER_HOST}"
echo "   cd ${REMOTE_DIR}"
echo "   python3 run_simulation.py --terminal"
echo ""
echo " To forward Web UI port 8088 to your local machine:"
echo "   ssh -L 8088:localhost:8088 ${CONTROLLER_HOST}"
echo "================================================================="
