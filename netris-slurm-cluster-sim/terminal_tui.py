#!/usr/bin/env python3
"""
terminal_tui.py - Terminal Console Dashboard for Slurm + Netris Integration
Provides a clean ANSI/text-based dashboard directly in SSH/console sessions.
"""

import os
import sys
import time
from typing import Any, Dict
from slurm_orchestrator import SlurmOrchestrator

# ANSI escape codes for terminal formatting
CLEAR_SCREEN = "\033[2J\033[H"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

COLOR_GREEN = "\033[38;5;48m"
COLOR_YELLOW = "\033[38;5;220m"
COLOR_PURPLE = "\033[38;5;141m"
COLOR_BLUE = "\033[38;5;75m"
COLOR_CYAN = "\033[38;5;87m"
COLOR_RED = "\033[38;5;203m"
COLOR_GRAY = "\033[38;5;242m"
BG_DARK = "\033[48;5;234m"


def format_progress_bar(pct: float, width: int = 15) -> str:
    """Renders an ANSI progress bar."""
    filled = int(round(width * (pct / 100.0)))
    empty = width - filled
    return f"{COLOR_PURPLE}{'█' * filled}{COLOR_GRAY}{'░' * empty}{RESET} {pct:.0f}%"


def render_tui(orchestrator: SlurmOrchestrator):
    """Renders a single frame of the terminal dashboard."""
    snapshot = orchestrator.get_cluster_snapshot()
    summary = snapshot["summary"]
    nodes = snapshot["nodes"]
    jobs = snapshot["jobs"]
    events = snapshot["events"]

    lines = []
    lines.append(f"{BOLD}{COLOR_CYAN}╔════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
    lines.append(f"{BOLD}{COLOR_CYAN}║     NETRIS + SLURM AI FABRIC ORCHESTRATION CONSOLE                                 ║{RESET}")
    lines.append(f"{BOLD}{COLOR_CYAN}║     Controller: adam-ctl.netris.io | VPC: Demo (ID: 20) | Template: RoCEv2 (ID: 6) ║{RESET}")
    lines.append(f"{BOLD}{COLOR_CYAN}╚════════════════════════════════════════════════════════════════════════════════════╝{RESET}")

    # Metrics Summary Line
    autopilot_tag = f"{COLOR_GREEN}[AUTOPILOT ON]{RESET}" if summary['autopilot'] else f"{COLOR_GRAY}[AUTOPILOT OFF]{RESET}"
    lines.append(
        f" {BOLD}Pool:{RESET} {summary['total_nodes']} Nodes ({summary['total_gpus']} GPUs) │ "
        f"{COLOR_GREEN}{summary['idle_nodes']} Idle{RESET} │ "
        f"{COLOR_PURPLE}{summary['allocated_nodes']} Allocated{RESET} │ "
        f"{COLOR_CYAN}{summary['active_jobs']} Netris Clusters{RESET} │ "
        f"{COLOR_YELLOW}{summary['total_bandwidth_gbps']:.1f} Gb/s RoCEv2{RESET} │ {autopilot_tag}"
    )
    lines.append(f"{COLOR_GRAY}{'─' * 84}{RESET}")

    # Node Matrix Grid (4 per row)
    lines.append(f"{BOLD}► HGX GPU NODE PARTITION (8 RoCEv2 Rails / Node):{RESET}")
    row_nodes = []
    for i, node in enumerate(nodes):
        state = node["state"]
        name = node["name"]
        job_id = node["job_id"] or "IDLE"
        if state == "IDLE":
            badge = f"{COLOR_GREEN}● IDLE{RESET}"
            rails = f"{COLOR_GRAY}........{RESET}"
        elif state == "PROVISIONING":
            badge = f"{COLOR_YELLOW}▲ PROV{RESET}"
            rails = f"{COLOR_YELLOW}········{RESET}"
        elif state == "ALLOCATED":
            badge = f"{COLOR_PURPLE}■ {job_id}{RESET}"
            rails = f"{COLOR_PURPLE}════════{RESET}"
        else:
            badge = f"{COLOR_RED}▼ TEAR{RESET}"
            rails = f"{COLOR_RED}········{RESET}"

        box = f"[{name[-8:]} {badge} {rails}]"
        row_nodes.append(box)

        if len(row_nodes) == 3 or i == len(nodes) - 1:
            lines.append("  " + "  ".join(row_nodes))
            row_nodes = []

    lines.append(f"{COLOR_GRAY}{'─' * 84}{RESET}")

    # Active Jobs Table
    lines.append(f"{BOLD}► ACTIVE SLURM JOBS & DYNAMIC NETRIS SERVER CLUSTERS:{RESET}")
    if not jobs:
        lines.append(f"  {DIM}(No jobs executing. Waiting for scheduler or autopilot...){RESET}")
    else:
        lines.append(f"  {BOLD}{'JOB ID':<10} {'MODEL / WORKLOAD':<24} {'NODES':<8} {'CLUSTER':<16} {'STATUS / PROGRESS':<26} {'THROUGHPUT':<12}{RESET}")
        for j in jobs:
            jid = j["id"]
            model = (j["name"][:22] + "..") if len(j["name"]) > 22 else j["name"]
            n_str = f"{j['nodes_count']} ({j['nodes_count']*8}G)"
            cid_str = f"#{j['cluster_id']} ({j['cluster_name']})" if j['cluster_id'] else "Prov Netris..."
            bw_str = f"{j.get('throughput_gbps', 0.0):.1f} Gb/s"

            state = j.get("state", "PENDING")
            if state == "PROVISIONING":
                pelapsed = int(j.get("provision_elapsed", 0))
                prog = f"{COLOR_YELLOW}PROV {pelapsed}s / 120s{RESET}"
            elif state == "TEARDOWN":
                telapsed = int(j.get("teardown_elapsed", 0))
                prog = f"{COLOR_RED}TEAR {telapsed}s / 120s{RESET}"
            else:
                rem = max(0, int(j.get("duration", 0) - j.get("elapsed", 0)))
                bar = format_progress_bar(j.get("progress", 0.0), width=6)
                prog = f"{bar} {rem//60}m{rem%60:02d}s"

            lines.append(f"  {COLOR_CYAN}{jid:<10}{RESET} {model:<24} {n_str:<8} {COLOR_PURPLE}{cid_str:<16}{RESET} {prog:<35} {COLOR_YELLOW}{bw_str:<12}{RESET}")

    lines.append(f"{COLOR_GRAY}{'─' * 84}{RESET}")

    # Live Event Feed (Last 5 events)
    lines.append(f"{BOLD}► RECENT ORCHESTRATION & NETRIS CONTROLLER EVENTS:{RESET}")
    recent_events = events[-5:] if events else []
    if not recent_events:
        lines.append(f"  {DIM}(No events logged yet){RESET}")
    else:
        for e in recent_events:
            src = e["source"]
            tag_color = COLOR_BLUE
            if "NETRIS" in src:
                tag_color = COLOR_PURPLE
            elif "FABRIC" in src:
                tag_color = COLOR_GREEN

            lines.append(f"  {DIM}{e['timestamp']}{RESET} {tag_color}[{src:<10}]{RESET} {e['message']}")

    lines.append(f"{COLOR_GRAY}{'─' * 84}{RESET}")
    lines.append(f"{DIM}Press Ctrl+C to exit console. (Web UI running in parallel){RESET}")

    # Output frame to terminal
    sys.stdout.write(CLEAR_SCREEN + "\n".join(lines) + "\n")
    sys.stdout.flush()


def run_terminal_loop(orchestrator: SlurmOrchestrator):
    """Runs the terminal TUI update loop."""
    try:
        while orchestrator.running:
            render_tui(orchestrator)
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
