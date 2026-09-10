#!/usr/bin/env bash
# ==============================================================================
# Netris Telemetry Recording Runner
# Captures live topology & streaming telemetry from Netris for offline simulation.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
NC="\033[0m"

echo -e "${BOLD}${BLUE}"
echo "========================================================================"
echo "           NETRIS TELEMETRY RECORDER & SNAPSHOT TOOL                    "
echo "========================================================================"
echo -e "${NC}"

if [ ! -f "netris.var" ]; then
    echo -e "${RED}[-] Error: netris.var not found! Live credentials are required to record.${NC}"
    exit 1
fi

DURATION="${1:-300}"
INTERVAL="${2:-15}"
OUTPUT="sim_data/telemetry_recording.json"

echo -e "[*] Recording Duration: ${BOLD}${DURATION} seconds${NC}"
echo -e "[*] Frame Interval:     ${BOLD}${INTERVAL} seconds${NC}"
echo -e "[*] Output Destination: ${BOLD}${OUTPUT}${NC}"
echo ""

if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
else
    PYTHON_CMD="python3"
fi

$PYTHON_CMD record.py --duration "$DURATION" --interval "$INTERVAL" --output "$OUTPUT"
