#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=========================================================="
echo "   Netris GPU AI Fabric Traffic Simulator Launcher        "
echo "=========================================================="

# Check Docker
if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] Docker is not running. Please start Docker Desktop or the Docker daemon."
    exit 1
fi

echo "[1/3] Building and starting pretend GPU nodes..."
docker compose up -d --build

echo "[2/3] Waiting for multi-rail iPerf3 daemons to initialize..."
sleep 2

echo "[3/3] Executing AI Collective Simulation..."
if [ "$#" -eq 0 ]; then
    # Default: Run Ring-AllReduce simulation
    python3 "$DIR/simulate.py" --pattern ring-allreduce --duration 5
else
    python3 "$DIR/simulate.py" "$@"
fi

echo ""
echo "=========================================================="
echo " Simulation Complete!"
echo " Available patterns to test:"
echo "   ./run.sh --pattern ring-allreduce --duration 5"
echo "   ./run.sh --pattern all-to-all    --duration 5"
echo "   ./run.sh --pattern incast        --duration 5"
echo "   ./run.sh --pattern multi-rail    --duration 5"
echo "   ./run.sh --pattern all           --duration 3"
echo " To stop containers: docker compose down"
echo "=========================================================="
