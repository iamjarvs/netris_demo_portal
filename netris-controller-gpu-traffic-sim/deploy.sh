#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_HOST="ubuntu@adam-ctl.netris.io"
REMOTE_DIR="~/netris-gpu-fabric-sim"

echo "=========================================================="
echo " Netris Controller GPU Fabric Traffic Deployer & Launcher "
echo "=========================================================="

echo "[1/3] Syncing automation scripts to Netris Controller ($REMOTE_HOST)..."
ssh -o StrictHostKeyChecking=accept-new "$REMOTE_HOST" "mkdir -p $REMOTE_DIR"
scp -o StrictHostKeyChecking=accept-new "$DIR/discover_and_deploy.py" "$DIR/run_fabric_traffic.py" "$REMOTE_HOST:$REMOTE_DIR/"

echo "[2/3] Executing VPC-to-GPU Discovery and Native Offline Deployment..."
ssh -t -o StrictHostKeyChecking=accept-new "$REMOTE_HOST" "python3 $REMOTE_DIR/discover_and_deploy.py"

echo "[3/3] Launching AI Collective Traffic Generation..."
if [ "$#" -eq 0 ]; then
    # Default: Run Ring-AllReduce across all GPU servers
    ssh -t -o StrictHostKeyChecking=accept-new "$REMOTE_HOST" "python3 $REMOTE_DIR/run_fabric_traffic.py --pattern ring-allreduce --duration 5"
else
    # Forward user arguments
    ssh -t -o StrictHostKeyChecking=accept-new "$REMOTE_HOST" "python3 $REMOTE_DIR/run_fabric_traffic.py $*"
fi

echo ""
echo "=========================================================="
echo " Deployment & Execution Complete!"
echo " To run continuous mode on the Netris Controller directly:"
echo "   ssh ubuntu@adam-ctl.netris.io"
echo "   cd ~/netris-gpu-fabric-sim"
echo "   python3 run_fabric_traffic.py --continuous --interval 5"
echo "=========================================================="
