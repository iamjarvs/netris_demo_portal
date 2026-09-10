#!/usr/bin/env python3
"""
run_simulation.py - Unified Entrypoint for Slurm + Netris AI Fabric Simulation
Launches the Netris API client, Slurm Orchestrator, and Visual Dashboard.
"""

import argparse
import logging
import signal
import sys
import threading
import time
from netris_api import NetrisAPIClient
from slurm_orchestrator import SlurmOrchestrator
from web_dashboard import run_web_server
from terminal_tui import run_terminal_loop

logger = logging.getLogger("main")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Netris + Slurm GPU AI Fabric Orchestration Simulator"
    )
    parser.add_argument(
        "--controller-url",
        default="https://adam-ctl.netris.io",
        help="Netris Controller URL (default: https://adam-ctl.netris.io)",
    )
    parser.add_argument(
        "--username",
        default="netris",
        help="Netris API username (default: netris)",
    )
    parser.add_argument(
        "--password",
        default="913QGAi6oQTSGgZm20eU",
        help="Netris API password",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8088,
        help="HTTP Web Dashboard port (default: 8088)",
    )
    parser.add_argument(
        "--pool-size",
        type=int,
        default=12,
        help="Number of HGX GPU servers to manage in Slurm partition (default: 12)",
    )
    parser.add_argument(
        "--node-prefix",
        default="hgx-pod00-su0-h",
        help="Hostname prefix for selecting GPU servers (default: hgx-pod00-su0-h)",
    )
    parser.add_argument(
        "--no-autopilot",
        action="store_true",
        help="Disable automatic job scheduling on startup (manual submission only)",
    )
    parser.add_argument(
        "--terminal-only",
        action="store_true",
        help="Run only the terminal console TUI without starting the web server",
    )
    parser.add_argument(
        "--terminal",
        action="store_true",
        help="Display the terminal console TUI while running the web server",
    )
    parser.add_argument(
        "--prov-time",
        type=int,
        default=120,
        help="Netris Server Cluster & VPC provisioning time in seconds (default: 120s / 2 mins)",
    )
    parser.add_argument(
        "--teardown-time",
        type=int,
        default=120,
        help="Netris Server Cluster deprovisioning time in seconds (default: 120s / 2 mins)",
    )
    parser.add_argument(
        "--min-duration",
        type=int,
        default=420,
        help="Minimum job training duration in seconds (default: 420s / 7 mins)",
    )
    parser.add_argument(
        "--autopilot-interval",
        type=int,
        default=60,
        help="Seconds between autopilot job scheduling attempts (default: 60s)",
    )
    parser.add_argument(
        "--sim-mode",
        "--sim",
        "--replay",
        dest="sim_mode",
        action="store_true",
        help="Run in offline simulated replay mode (loops RoCEv2 telemetry nonstop without live Netris Controller)",
    )
    parser.add_argument(
        "--speedup",
        type=float,
        default=1.0,
        help="Simulation clock speedup multiplier (default: 1.0 = real-time)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Configure logging
    log_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    if args.terminal or args.terminal_only:
        # In terminal TUI mode, write logs to file to keep console clean
        logging.basicConfig(filename="slurm_sim.log", level=getattr(logging, args.log_level), format=log_format)
    else:
        logging.basicConfig(level=getattr(logging, args.log_level), format=log_format)

    mode_label = "OFFLINE SIMULATION REPLAY (Looping)" if args.sim_mode else f"LIVE CONTROLLER ({args.controller_url})"
    print("\n" + "=" * 70)
    print("  NETRIS + SLURM GPU AI FABRIC ORCHESTRATOR")
    print(f"  Operational Mode:  {mode_label}")
    print(f"  Managed Pool Size: {args.pool_size} HGX Nodes ({args.pool_size * 8} GPUs)")
    print(f"  Timing Profile:    ~{args.prov_time}s Prov | Min {args.min_duration}s ({args.min_duration//60}m) Run | ~{args.teardown_time}s Teardown")
    print(f"  Autopilot Mode:    {'OFF' if args.no_autopilot else f'ON (Interval: {args.autopilot_interval}s)'}")
    if args.speedup != 1.0:
        print(f"  Simulation Clock:  {args.speedup}x Speedup")
    print("=" * 70 + "\n")

    # 1. Initialize Netris API Client (with auto-fallback to sim mode if offline)
    if args.sim_mode:
        client = NetrisAPIClient(sim_mode=True)
        client.authenticate()
    else:
        client = NetrisAPIClient(
            base_url=args.controller_url,
            username=args.username,
            password=args.password,
        )
        try:
            client.authenticate()
        except Exception as e:
            print(f"\n[WARNING] Could not connect to live Netris Controller ({args.controller_url}): {e}")
            print("[AUTO-FALLBACK] Seamlessly switching to Offline Simulation & Telemetry Replay Mode (--sim-mode).\n")
            client = NetrisAPIClient(sim_mode=True)
            client.authenticate()

    # 2. Initialize Slurm Orchestrator
    orchestrator = SlurmOrchestrator(
        netris_client=client,
        pool_size=args.pool_size,
        node_prefix=args.node_prefix,
        autopilot=not args.no_autopilot,
        prov_time=args.prov_time,
        teardown_time=args.teardown_time,
        min_job_duration=args.min_duration,
        autopilot_interval=args.autopilot_interval,
        speedup=args.speedup,
    )

    # Clean shutdown handler
    def handle_exit(signum, frame):
        print("\n[SHUTDOWN] Received signal. Deprovisioning active Netris clusters...")
        orchestrator.stop()
        orchestrator.teardown_all()
        print("[SHUTDOWN] Clean exit complete.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Start orchestrator loop
    orchestrator.start()

    # 3. Launch UI
    if args.terminal_only:
        print("Launching Terminal TUI...")
        run_terminal_loop(orchestrator)
    elif args.terminal:
        # Run Web Server in background thread and TUI in foreground
        web_thread = threading.Thread(
            target=run_web_server,
            args=(orchestrator, "0.0.0.0", args.port),
            daemon=True,
        )
        web_thread.start()
        run_terminal_loop(orchestrator)
    else:
        # Run Web Server in foreground
        run_web_server(orchestrator, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
