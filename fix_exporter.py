from pathlib import Path

start_sh = Path("demo-portal/managed-tools/netris-prometheus-exporter/start.sh")
content = start_sh.read_text()
old_check = """    if [ ! -f "$SIM_DATA_FILE" ]; then
        echo -e "${RED}[-] Error: Recording file '${SIM_DATA_FILE}' does not exist!${NC}"
        echo -e "${YELLOW}[!] To generate a simulation recording, connect to Netris and run:${NC}"
        echo -e "    ${BOLD}./record.sh 60 15${NC} (or ./start.sh --record 60 15)"
        exit 1
    fi"""

new_check = """    if [ ! -f "$SIM_DATA_FILE" ]; then
        if [ -f "${SIM_DATA_FILE}.gz" ]; then
            echo "[*] Decompressing $SIM_DATA_FILE.gz..."
            gunzip -k "${SIM_DATA_FILE}.gz"
        else
            echo -e "${RED}[-] Error: Recording file '${SIM_DATA_FILE}' does not exist!${NC}"
            echo -e "${YELLOW}[!] To generate a simulation recording, connect to Netris and run:${NC}"
            echo -e "    ${BOLD}./record.sh 60 15${NC} (or ./start.sh --record 60 15)"
            exit 1
        fi
    fi"""
content = content.replace(old_check, new_check)
start_sh.write_text(content)
print("done")
