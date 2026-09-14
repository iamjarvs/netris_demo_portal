#!/usr/bin/env bash
# ==============================================================================
# Netris Observability Stack Launcher
# Starts Netris Prometheus Exporter, Prometheus, and Grafana locally.
# Supports both Live Netris streaming and 100% Offline Simulation replay.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m"

# Print banner
print_banner() {
    echo -e "${BOLD}${BLUE}"
    echo "========================================================================"
    echo "         NETRIS PROMETHEUS & GRAFANA OBSERVABILITY STACK                "
    echo "========================================================================"
    echo -e "${NC}"
}

usage() {
    print_banner
    echo -e "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --sim, --simulation       Run in offline Simulation Mode (no controller needed)"
    echo "  -l, --live                    Run in Live Mode (connects to Netris Controller)"
    echo "  -b, --backfill [MIN]          Pre-populate Prometheus TSDB with MIN minutes of history (default: 90)"
    echo "      --no-backfill             Skip historical backfill in simulation mode"
    echo "  -r, --record [SEC] [INT]      Record live telemetry (default: 300s duration, 15s interval)"
    echo "  -h, --help                    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --sim                      # Launch offline simulation with 90m historical backfill (ready for demo!)"
    echo "  $0 --sim --backfill 120       # Launch offline simulation with 120m of pre-populated history"
    echo "  $0 --live                     # Launch live capture from Netris controller"
    echo "  $0 --record 60 15             # Capture 60 seconds of telemetry into simulation file"
    echo ""
    exit 0
}

# Parse Command-Line Arguments
MODE=""
DO_BACKFILL="true"
BACKFILL_MINUTES=90

while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--sim|--simulation)
            MODE="sim"
            shift
            ;;
        -l|--live)
            MODE="live"
            shift
            ;;
        -b|--backfill)
            DO_BACKFILL="true"
            if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                BACKFILL_MINUTES="$2"
                shift 2
            else
                BACKFILL_MINUTES=90
                shift
            fi
            ;;
        --no-backfill)
            DO_BACKFILL="false"
            shift
            ;;
        -r|--record)
            DURATION="${2:-300}"
            INTERVAL="${3:-15}"
            ./record.sh "$DURATION" "$INTERVAL"
            exit 0
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}[-] Unknown option: $1${NC}"
            usage
            ;;
    esac
done

print_banner

# Ensure config.env exists
if [ ! -f "config.env" ]; then
    if [ -f "config.env.example" ]; then
        echo -e "${YELLOW}[!] config.env not found. Creating from config.env.example...${NC}"
        cp config.env.example config.env
    else
        echo -e "${RED}[-] Error: config.env not found!${NC}"
        exit 1
    fi
fi

# Load config.env first
set -a
# shellcheck disable=SC1091
source config.env
set +a

# Determine mode if not explicitly passed as a flag
if [ -z "$MODE" ]; then
    if [ "${SIMULATION_MODE:-false}" = "true" ] || [ "${SIMULATION_MODE:-false}" = "1" ]; then
        MODE="sim"
    else
        MODE="live"
    fi
fi

# Determine python interpreter
if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
elif [ -f "../demo-portal/.venv/bin/python" ]; then
    PYTHON_CMD="../demo-portal/.venv/bin/python"
else
    PYTHON_CMD="python3"
fi

# Mode-specific preparation
if [ "$MODE" = "sim" ]; then
    export SIMULATION_MODE="true"
    SIM_DATA_FILE="${SIM_DATA_FILE:-sim_data/telemetry_recording.json}"

    echo -e "${BOLD}${CYAN}[⚡ MODE] SIMULATION (100% Offline Replay)${NC}"
    echo -e "[*] Simulation Data File:     ${BOLD}${SIM_DATA_FILE}${NC}"
    echo -e "[*] Netris Controller:        ${BOLD}Bypassed (No network connection required)${NC}"

    if [ ! -f "$SIM_DATA_FILE" ]; then
        echo -e "${RED}[-] Error: Recording file '${SIM_DATA_FILE}' does not exist!${NC}"
        echo -e "${YELLOW}[!] To generate a simulation recording, connect to Netris and run:${NC}"
        echo -e "    ${BOLD}./record.sh 60 15${NC} (or ./start.sh --record 60 15)"
        exit 1
    fi

    # Historical Backfill (Pre-populates Prometheus TSDB blocks)
    if [ "$DO_BACKFILL" = "true" ]; then
        echo -e "[*] Pre-populating Prometheus TSDB with ${BOLD}${BACKFILL_MINUTES} minutes${NC} of historical telemetry..."
        $PYTHON_CMD backfill.py --minutes "$BACKFILL_MINUTES" --step 60 --sim-data "$SIM_DATA_FILE" --output-dir "prometheus/data"
    fi

    # Optionally load netris.var for custom port overrides if present
    if [ -f "netris.var" ]; then
        set -a
        # shellcheck disable=SC1091
        source netris.var
        set +a
    fi
else
    export SIMULATION_MODE="false"
    echo -e "${BOLD}${GREEN}[⚡ MODE] LIVE STREAMING (Active Controller)${NC}"

    # Check Configuration & Variable Files
    if [ ! -f "netris.var" ]; then
        if [ -f ".var" ]; then
            cp .var netris.var
        elif [ -f "netris.var.example" ]; then
            echo -e "${YELLOW}[!] netris.var not found. Creating from netris.var.example...${NC}"
            cp netris.var.example netris.var
        else
            echo -e "${RED}[-] Error: netris.var not found! Please create it with your Netris credentials.${NC}"
            exit 1
        fi
    fi

    set -a
    # shellcheck disable=SC1091
    source netris.var
    set +a

    echo -e "[*] Target Netris Controller: ${BOLD}${NETRIS_URL}${NC}"
    echo -e "[*] Netris User:              ${BOLD}${NETRIS_USERNAME}${NC}"

    # Check Netris Controller Reachability
    echo -n "[*] Checking Netris Controller reachability... "
    if curl -k -s --connect-timeout 5 "${NETRIS_URL}/api/v2/sites" > /dev/null 2>&1 || curl -k -s --connect-timeout 5 "${NETRIS_URL}" > /dev/null 2>&1; then
        echo -e "${GREEN}CONNECTED${NC}"
    else
        echo -e "${YELLOW}WARNING (Controller did not respond immediately, continuing anyway)${NC}"
    fi
fi

EXPORTER_PORT="${EXPORTER_PORT:-9101}"
PROMETHEUS_PORT="${PROMETHEUS_PORT:-9090}"
GRAFANA_PORT="${GRAFANA_PORT:-3000}"

echo -e "[*] Exporter Metrics Port:    ${BOLD}${EXPORTER_PORT}${NC}"
echo -e "[*] Prometheus Port:          ${BOLD}${PROMETHEUS_PORT}${NC}"
echo -e "[*] Grafana UI Port:          ${BOLD}${GRAFANA_PORT}${NC}"
echo ""

# Launch Stack
DOCKER_ENV_ARGS=("--env-file" "config.env")
if [ -f "netris.var" ]; then
    DOCKER_ENV_ARGS+=("--env-file" "netris.var")
fi

if command -v docker > /dev/null 2>&1 && docker info > /dev/null 2>&1; then
    echo -e "[*] Launching containers via Docker Compose (SIMULATION_MODE=${SIMULATION_MODE})..."
    docker compose "${DOCKER_ENV_ARGS[@]}" up -d --build
else
    echo -e "${YELLOW}[!] Docker not found or not running. Falling back to local Python environment...${NC}"
    if [ ! -d ".venv" ]; then
        echo "[*] Creating virtual environment..."
        python3 -m venv .venv
        .venv/bin/pip install -r requirements.txt
    fi
    echo "[*] Launching Netris Exporter locally in background..."
    if [ -f ".exporter.pid" ]; then
        kill "$(cat .exporter.pid)" >/dev/null 2>&1 || true
    fi
    nohup env SIMULATION_MODE="${SIMULATION_MODE}" .venv/bin/python exporter.py > exporter.log 2>&1 &
    echo $! > .exporter.pid
    echo -e "${GREEN}[+] Exporter running locally with PID $(cat .exporter.pid)${NC}"
fi

# Wait for Telemetry Capture to Begin
echo -n "[*] Waiting for exporter to initialize telemetry stream"
MAX_RETRIES=20
COUNT=0
CAPTURED=0

while [ $COUNT -lt $MAX_RETRIES ]; do
    if curl -s "http://localhost:${EXPORTER_PORT}/metrics" 2>/dev/null | grep -q "netris_up 1"; then
        CAPTURED=1
        break
    fi
    echo -n "."
    sleep 1
    COUNT=$((COUNT + 1))
done
echo ""

if [ $CAPTURED -eq 1 ]; then
    SAMPLE_COUNT=$(curl -s "http://localhost:${EXPORTER_PORT}/metrics" | grep -c "^netris_" || echo "0")
    if [ "$MODE" = "sim" ]; then
        echo -e "${GREEN}[+] SUCCESS: Simulation replay active! (${SAMPLE_COUNT} Netris metric series streaming in loop)${NC}"
    else
        echo -e "${GREEN}[+] SUCCESS: Live data capture active! (${SAMPLE_COUNT} Netris metric series streaming)${NC}"
    fi
else
    echo -e "${YELLOW}[!] Telemetry stream starting up (check logs if initial scrape takes longer).${NC}"
fi

# Summary & Links
echo ""
echo -e "${BOLD}${GREEN}========================================================================${NC}"
if [ "$MODE" = "sim" ]; then
    echo -e "${BOLD}${CYAN}         NETRIS OBSERVABILITY STACK IS LIVE (SIMULATION MODE)           ${NC}"
else
    echo -e "${BOLD}${GREEN}         NETRIS OBSERVABILITY STACK IS LIVE (LIVE STREAMING)            ${NC}"
fi
echo -e "${BOLD}${GREEN}========================================================================${NC}"
echo ""
echo -e "  📊  ${BOLD}Grafana Dashboard:${NC}  http://localhost:${GRAFANA_PORT}"
echo -e "      ${BOLD}Login Credentials:${NC}  User: ${BOLD}${GRAFANA_ADMIN_USER:-admin}${NC} / Pass: ${BOLD}${GRAFANA_ADMIN_PASSWORD:-admin}${NC}"
echo -e "      ${BOLD}Home Dashboard:${NC}     Netris Fabric Observability"
echo ""
echo -e "  🔥  ${BOLD}Prometheus Server:${NC}  http://localhost:${PROMETHEUS_PORT}"
echo -e "  📈  ${BOLD}Raw Metrics Feed:${NC}   http://localhost:${EXPORTER_PORT}/metrics"
echo ""
if [ "$MODE" = "sim" ]; then
    echo -e "  🔁  ${BOLD}Simulation Data:${NC}   ${SCRIPT_DIR}/${SIM_DATA_FILE}"
    if [ "$DO_BACKFILL" = "true" ]; then
        echo -e "  ⏱   ${BOLD}Historical Pre-fill:${NC} ${BACKFILL_MINUTES} minutes pre-populated into TSDB (Demo-Ready)"
    fi
    echo -e "  💡  ${BOLD}Replay Details:${NC}    Infinite circular loop with micro-jitter"
else
    echo -e "  🔑  ${BOLD}Netris Creds:${NC}       ${SCRIPT_DIR}/netris.var"
fi
echo -e "  ⚙️   ${BOLD}Adjust Configs:${NC}     ${SCRIPT_DIR}/config.env"
echo -e "  🛑  ${BOLD}Stop Stack:${NC}         ./stop.sh (or 'docker compose down')"
echo -e "${BOLD}${GREEN}========================================================================${NC}"
echo ""
