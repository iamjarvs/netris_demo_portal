#!/usr/bin/env python3
"""
Netris GPU AI Fabric Traffic Orchestrator & Continuous Runner
Executes distributed AI collective communication patterns (NCCL/RCCL)
across actual bare-metal HGX GPU hosts in a Netris-managed backend fabric.

Author: Netris Solutions Architecture
"""

import argparse
import concurrent.futures
import json
import os
import random
import signal
import subprocess
import sys
import time
from typing import Any, Dict, List

TOPOLOGY_FILE = os.path.expanduser("~/netris-gpu-fabric-sim/vpc_gpu_topology.json")
LOG_FILE = os.path.expanduser("~/netris-gpu-fabric-sim/traffic_runner.log")
PID_FILE = os.path.expanduser("~/netris-gpu-fabric-sim/traffic_runner.pid")

# ANSI Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


def daemonize(log_file: str, pid_file: str):
    """Forks process into the background, detaching from TTY and session."""
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            print(f"{RED}[ERROR] Traffic runner is already active in background (PID: {old_pid}).{RESET}")
            print(f"  To check status : python3 run_fabric_traffic.py --status")
            print(f"  To view logs     : tail -f {log_file}")
            print(f"  To stop it       : python3 run_fabric_traffic.py --stop")
            sys.exit(1)
        except (OSError, ValueError):
            pass

    pid = os.fork()
    if pid > 0:
        # Parent writes PID and exits
        os.makedirs(os.path.dirname(pid_file), exist_ok=True)
        with open(pid_file, "w") as f:
            f.write(str(pid) + "\n")
        print(f"\n{BOLD}{GREEN}[OK] Netris GPU AI Fabric Runner started in background (PID: {pid}){RESET}")
        print(f"Log file : {BOLD}{CYAN}{log_file}{RESET}")
        print(f"PID file : {CYAN}{pid_file}{RESET}")
        print(f"\n{YELLOW}You can now safely disconnect this SSH session.{RESET}")
        print(f"Management commands:")
        print(f"  Live logs : {BOLD}tail -n 25 -f {log_file}{RESET}")
        print(f"  Status    : {BOLD}python3 run_fabric_traffic.py --status{RESET}")
        print(f"  Stop      : {BOLD}python3 run_fabric_traffic.py --stop{RESET}\n")
        sys.exit(0)

    # In child process: create new session and ignore SIGHUP
    os.setsid()
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    os.umask(0)

    sys.stdout.flush()
    sys.stderr.flush()

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    log_fd = open(log_file, "a", buffering=1, encoding="utf-8")
    sys.stdout = log_fd
    sys.stderr = log_fd


def stop_daemon(pid_file: str):
    """Terminates running background traffic runner process."""
    if not os.path.exists(pid_file):
        print(f"{YELLOW}[INFO] No active background runner found (PID file missing).{RESET}")
        return
    with open(pid_file, "r") as f:
        try:
            pid = int(f.read().strip())
        except ValueError:
            pid = None
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"{GREEN}[OK] Sent SIGTERM to background traffic runner (PID: {pid}){RESET}")
        except ProcessLookupError:
            print(f"{YELLOW}[INFO] Process {pid} was not running.{RESET}")
    if os.path.exists(pid_file):
        os.remove(pid_file)


def check_status(pid_file: str, log_file: str):
    """Reports status of background runner."""
    if not os.path.exists(pid_file):
        print(f"{YELLOW}Traffic runner status: STOPPED (No active background process){RESET}")
        return
    with open(pid_file, "r") as f:
        try:
            pid = int(f.read().strip())
        except ValueError:
            pid = None
    if pid:
        try:
            os.kill(pid, 0)
            print(f"{GREEN}Traffic runner status: RUNNING in background (PID: {pid}){RESET}")
            print(f"Log file: {log_file}")
            print(f"Run 'tail -n 25 -f {log_file}' to view live output.")
            return
        except ProcessLookupError:
            print(f"{RED}Traffic runner status: DEAD (stale PID {pid}){RESET}")
            os.remove(pid_file)
            return
    print(f"{YELLOW}Traffic runner status: STOPPED{RESET}")


def load_topology() -> Dict[str, Any]:
    if not os.path.exists(TOPOLOGY_FILE):
        print(f"{RED}[ERROR] Topology file not found: {TOPOLOGY_FILE}{RESET}")
        print(f"{YELLOW}Please run 'python3 discover_and_deploy.py' first.{RESET}")
        sys.exit(1)
    with open(TOPOLOGY_FILE, "r") as f:
        return json.load(f)


def parse_bandwidth_to_bps(val_str: str) -> float:
    """Parses '500M', '1G', '100K', '2.5G' into bits per second."""
    import re
    s = val_str.strip().upper()
    multiplier = 1.0
    if s.endswith("K") or s.endswith("KBPS") or s.endswith("KBIT"):
        multiplier = 1e3
        s = re.sub(r"[A-Z]+", "", s)
    elif s.endswith("M") or s.endswith("MBPS") or s.endswith("MBIT"):
        multiplier = 1e6
        s = re.sub(r"[A-Z]+", "", s)
    elif s.endswith("G") or s.endswith("GBPS") or s.endswith("GBIT"):
        multiplier = 1e9
        s = re.sub(r"[A-Z]+", "", s)
    return float(s) * multiplier


def format_bps(bps: float) -> str:
    """Formats numeric bps into iperf3-friendly bandwidth string."""
    if bps >= 1e9:
        return f"{bps / 1e9:.2f}G"
    elif bps >= 1e6:
        return f"{bps / 1e6:.2f}M"
    elif bps >= 1e3:
        return f"{bps / 1e3:.2f}K"
    return f"{int(bps)}"


def execute_remote_iperf(
    src_mgmt_ip: str,
    src_hostname: str,
    dst_backend_ip: str,
    dst_hostname: str,
    port: int,
    rail_id: int,
    duration: int,
    streams: int,
    tos: int = 96,
    bitrate_per_stream: str = None,
    bytes_limit: str = None,
) -> Dict[str, Any]:
    """
    Triggers an iperf3 client flow on src_mgmt_ip targeting dst_backend_ip:port.
    Parses JSON output directly from stdout.
    """
    cmd_parts = [f"iperf3 -c {dst_backend_ip} -p {port}"]
    if bytes_limit:
        cmd_parts.append(f"-n {bytes_limit}")
    else:
        cmd_parts.append(f"-t {duration}")

    cmd_parts.append(f"-P {streams}")
    cmd_parts.append(f"--tos {tos}")

    if bitrate_per_stream:
        cmd_parts.append(f"-b {bitrate_per_stream}")

    cmd_parts.append("-J")
    iperf_cmd = " ".join(cmd_parts)

    ssh_cmd = [
        "ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5", f"root@{src_mgmt_ip}", iperf_cmd
    ]

    start_t = time.time()
    res = subprocess.run(ssh_cmd, capture_output=True, text=True)
    elapsed = time.time() - start_t

    flow_res = {
        "src": src_hostname,
        "dst": dst_hostname,
        "dst_ip": dst_backend_ip,
        "port": port,
        "rail_id": rail_id,
        "duration": duration,
        "streams": streams,
        "elapsed_sec": round(elapsed, 2),
        "success": False,
        "throughput_gbps": 0.0,
        "bytes_sent": 0,
        "retransmits": 0,
        "error": None,
    }

    if res.returncode != 0:
        flow_res["error"] = res.stderr.strip() or res.stdout.strip()
        return flow_res

    try:
        data = json.loads(res.stdout)
        end_data = data.get("end", {})
        sender = end_data.get("sum_sent", {})
        bps = sender.get("bits_per_second", 0.0)
        bytes_sent = sender.get("bytes", 0)
        retransmits = sender.get("retransmits", 0)

        flow_res.update({
            "success": True,
            "throughput_gbps": round(bps / 1e9, 2),
            "bytes_sent": bytes_sent,
            "retransmits": retransmits,
        })
    except Exception as e:
        flow_res["error"] = f"JSON parse error: {e}"

    return flow_res


def execute_flow_batch(
    flows: List[Dict[str, Any]],
    title: str,
    max_aggregate_bw: str = None,
    per_flow_bw: str = None,
    bytes_limit: str = None,
    variance_pct: float = 20.0,
) -> List[Dict[str, Any]]:
    print(f"\n{BOLD}{CYAN}=== Running: {title} ({len(flows)} concurrent flows) ==={RESET}")

    # Determine per-stream rate cap if any bandwidth limiter is specified
    stream_bitrate_str = None
    if max_aggregate_bw:
        base_target_bps = parse_bandwidth_to_bps(max_aggregate_bw)
        if variance_pct > 0:
            # Equal-weight random variability within ±variance_pct
            var_factor = random.uniform(1.0 - (variance_pct / 100.0), 1.0 + (variance_pct / 100.0))
            effective_target_bps = base_target_bps * var_factor
            diff_pct = (var_factor - 1.0) * 100.0
            var_info = f" [±{variance_pct:.0f}% Variation -> Iteration Target: {format_bps(effective_target_bps)} ({'+' if diff_pct >= 0 else ''}{diff_pct:.1f}%)]"
        else:
            effective_target_bps = base_target_bps
            var_info = ""

        # Total streams = len(flows) * streams_per_flow
        streams_per_flow = flows[0]["streams"] if flows else 1
        total_streams = len(flows) * streams_per_flow
        bps_per_stream = effective_target_bps / max(total_streams, 1)
        stream_bitrate_str = format_bps(bps_per_stream)
        print(f"Applying Aggregate Ceiling: {BOLD}{max_aggregate_bw}{RESET}{var_info} across {len(flows)} flows ({total_streams} streams -> {stream_bitrate_str}/stream)")
    elif per_flow_bw:
        flow_target_bps = parse_bandwidth_to_bps(per_flow_bw)
        if variance_pct > 0:
            var_factor = random.uniform(1.0 - (variance_pct / 100.0), 1.0 + (variance_pct / 100.0))
            flow_target_bps *= var_factor
            diff_pct = (var_factor - 1.0) * 100.0
            var_info = f" [±{variance_pct:.0f}% Var: {format_bps(flow_target_bps)} ({'+' if diff_pct >= 0 else ''}{diff_pct:.1f}%)]"
        else:
            var_info = ""
        streams_per_flow = flows[0]["streams"] if flows else 1
        bps_per_stream = flow_target_bps / max(streams_per_flow, 1)
        stream_bitrate_str = format_bps(bps_per_stream)
        print(f"Applying Per-Flow Cap: {BOLD}{per_flow_bw}{RESET}{var_info} ({stream_bitrate_str}/stream)")

    if bytes_limit:
        print(f"Applying Per-Flow Data Cap: {BOLD}{bytes_limit}{RESET}")

    print(f"Injecting traffic across Netris backend leaf-spine fabric...")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(flows) + 2) as executor:
        futures = {
            executor.submit(
                execute_remote_iperf,
                f["src_mgmt"],
                f["src_name"],
                f["dst_ip"],
                f["dst_name"],
                f["port"],
                f["rail_id"],
                f["duration"],
                f["streams"],
                f["tos"],
                stream_bitrate_str,
                bytes_limit,
            ): f
            for f in flows
        }

        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    return results


def print_results_table(results: List[Dict[str, Any]], title: str, iteration: int = 1):
    print(f"\n{BOLD}{GREEN}------------------------------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}{MAGENTA} COLLECTIVE BENCHMARK [Iter {iteration}]: {title}{RESET}")
    print(f"{BOLD}{GREEN}------------------------------------------------------------------------------------------------{RESET}")
    print(f"{'Source Host':<20} {'Destination Host':<20} {'Rail / Target IP':<24} {'Throughput':<14} {'Retrans':<10} {'Status'}")
    print(f"{'-'*20} {'-'*20} {'-'*24} {'-'*14} {'-'*10} {'-'*8}")

    total_throughput = 0.0
    total_bytes = 0
    total_retransmits = 0

    sorted_res = sorted(results, key=lambda x: (x["src"], x["rail_id"]))

    for r in sorted_res:
        src = r["src"]
        dst = r["dst"]
        rail_ip = f"Rail {r['rail_id']} ({r['dst_ip']}:{r['port']})"

        if r["success"]:
            tp_str = f"{r['throughput_gbps']:>6.2f} Gbps"
            retrans_str = f"{r['retransmits']:>5} pkts"
            status_str = f"{GREEN}PASS{RESET}"
            total_throughput += r["throughput_gbps"]
            total_bytes += r["bytes_sent"]
            total_retransmits += r["retransmits"]
        else:
            tp_str = "    0.00 Gbps"
            retrans_str = "      N/A"
            status_str = f"{RED}FAIL{RESET}"

        print(f"{src:<20} {dst:<20} {rail_ip:<24} {tp_str:<14} {retrans_str:<10} {status_str}")

    print(f"{'-'*20} {'-'*20} {'-'*24} {'-'*14} {'-'*10} {'-'*8}")
    total_gb = total_bytes / (1024 ** 3)
    print(f"{BOLD}Aggregate Fabric Bandwidth   : {CYAN}{total_throughput:.2f} Gbps{RESET}")
    print(f"{BOLD}Total Data Transferred       : {CYAN}{total_gb:.2f} GB{RESET}")
    print(f"{BOLD}Total RoCEv2 Retransmissions : {YELLOW if total_retransmits > 0 else GREEN}{total_retransmits} packets{RESET}")
    print(f"{BOLD}{GREEN}------------------------------------------------------------------------------------------------{RESET}\n")


def build_ring_allreduce_flows(servers: List[Dict[str, Any]], duration: int, streams: int, tos: int) -> List[Dict[str, Any]]:
    flows = []
    n = len(servers)
    for i in range(n):
        src = servers[i]
        dst = servers[(i + 1) % n]
        # Transmit across 2 parallel rails (Rail 0 port 5201, Rail 1 port 5202)
        for rail in range(2):
            rail_str = str(rail)
            dst_ip = dst["backend_rails"].get(rail_str, {}).get("ip")
            if not dst_ip:
                continue
            flows.append({
                "src_mgmt": src["mgmt_ip"],
                "src_name": src["hostname"],
                "dst_name": dst["hostname"],
                "dst_ip": dst_ip,
                "port": 5201 + rail,
                "rail_id": rail,
                "duration": duration,
                "streams": streams,
                "tos": tos,
            })
    return flows


def build_all_to_all_flows(servers: List[Dict[str, Any]], duration: int, streams: int, tos: int) -> List[Dict[str, Any]]:
    flows = []
    for src_idx, src in enumerate(servers):
        rail_counter = 0
        for dst_idx, dst in enumerate(servers):
            if src_idx == dst_idx:
                continue
            rail_id = src_idx % 8
            dst_ip = dst["backend_rails"].get(str(rail_id), {}).get("ip")
            if not dst_ip:
                # fallback to rail 0
                dst_ip = dst["backend_rails"].get("0", {}).get("ip")
            flows.append({
                "src_mgmt": src["mgmt_ip"],
                "src_name": src["hostname"],
                "dst_name": dst["hostname"],
                "dst_ip": dst_ip,
                "port": 5201 + (src_idx % 8),
                "rail_id": rail_id,
                "duration": duration,
                "streams": streams,
                "tos": tos,
            })
    return flows


def build_incast_flows(servers: List[Dict[str, Any]], duration: int, streams: int, tos: int, target_idx: int = 0) -> List[Dict[str, Any]]:
    target = servers[target_idx]
    workers = [s for idx, s in enumerate(servers) if idx != target_idx]
    flows = []
    for w_idx, worker in enumerate(workers):
        rail_id = w_idx % 8
        dst_ip = target["backend_rails"].get(str(rail_id), {}).get("ip") or target["backend_rails"].get("0", {}).get("ip")
        flows.append({
            "src_mgmt": worker["mgmt_ip"],
            "src_name": worker["hostname"],
            "dst_name": target["hostname"],
            "dst_ip": dst_ip,
            "port": 5201 + rail_id,
            "rail_id": rail_id,
            "duration": duration,
            "streams": streams,
            "tos": tos,
        })
    return flows


def build_multi_rail_flows(servers: List[Dict[str, Any]], duration: int, streams: int, tos: int) -> List[Dict[str, Any]]:
    src = servers[0]
    dst = servers[1]
    flows = []
    for rail in range(8):
        dst_ip = dst["backend_rails"].get(str(rail), {}).get("ip")
        if not dst_ip:
            continue
        flows.append({
            "src_mgmt": src["mgmt_ip"],
            "src_name": src["hostname"],
            "dst_name": dst["hostname"],
            "dst_ip": dst_ip,
            "port": 5201 + rail,
            "rail_id": rail,
            "duration": duration,
            "streams": streams,
            "tos": tos,
        })
    return flows


def main():
    parser = argparse.ArgumentParser(description="Netris GPU AI Fabric Continuous Traffic Runner")
    parser.add_argument("--vpc", type=str, default=None, help="Target VPC name (default: first active VPC)")
    parser.add_argument("--pattern", choices=["ring-allreduce", "all-to-all", "incast", "multi-rail", "all"], default="ring-allreduce")
    parser.add_argument("--duration", "-t", type=int, default=5, help="Test duration in seconds per step (default: 5)")
    parser.add_argument("--streams", "-P", type=int, default=4, help="Number of parallel Queue Pairs / streams (default: 4)")
    parser.add_argument("--tos", type=int, default=96, help="TOS / DSCP marking for RoCEv2 (default: 96 = DSCP 24)")
    parser.add_argument("--continuous", action="store_true", help="Run traffic simulation continuously in a loop")
    parser.add_argument("--interval", type=int, default=5, help="Rest interval in seconds between continuous loops (default: 5)")
    parser.add_argument("--iterations", type=int, default=0, help="Number of iterations (0 = infinite if --continuous)")
    parser.add_argument("--max-bandwidth", "-B", type=str, default=None, help="Overall cluster aggregate bandwidth ceiling (e.g. '500M', '1G', '2G')")
    parser.add_argument("--variance", "-V", type=float, default=20.0, help="Equal-weight random variation percentage across runs (default: 20%)")
    parser.add_argument("--bitrate", "-b", type=str, default=None, help="Per-flow bandwidth limit (e.g. '50M', '100M')")
    parser.add_argument("--bytes-limit", "-n", type=str, default=None, help="Per-flow byte volume limit (e.g. '100M', '500M')")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run traffic simulation as a detached background daemon")
    parser.add_argument("--status", action="store_true", help="Check status of running background daemon")
    parser.add_argument("--stop", action="store_true", help="Stop running background daemon")
    parser.add_argument("--json-out", type=str, default=None, help="File to write benchmark metrics")

    args = parser.parse_args()

    # Handle service commands
    if args.stop:
        stop_daemon(PID_FILE)
        sys.exit(0)

    if args.status:
        check_status(PID_FILE, LOG_FILE)
        sys.exit(0)

    # Detach to background if requested
    if args.daemon:
        daemonize(LOG_FILE, PID_FILE)

    vpcs = load_topology()
    target_vpc = args.vpc or list(vpcs.keys())[0]
    if target_vpc not in vpcs:
        print(f"{RED}[ERROR] VPC '{target_vpc}' not in topology file.{RESET}")
        sys.exit(1)

    servers = vpcs[target_vpc]["servers"]
    print(f"{BOLD}{CYAN}================================================================{RESET}")
    print(f"{BOLD}{CYAN}    NETRIS GPU AI FABRIC TRAFFIC ORCHESTRATOR (LIVE FABRIC)     {RESET}")
    print(f"{BOLD}{CYAN}================================================================{RESET}")
    print(f"Target VPC     : {BOLD}{target_vpc}{RESET} (VPC ID: {vpcs[target_vpc]['vpc_id']})")
    print(f"Server Cluster : {BOLD}{vpcs[target_vpc]['cluster_name']}{RESET}")
    print(f"GPU Hosts ({len(servers)}) : {[s['hostname'] for s in servers]}")
    print(f"Pattern        : {BOLD}{args.pattern.upper()}{RESET} | Duration: {args.duration}s | Streams: {args.streams} QPs")
    if args.max_bandwidth:
        print(f"Traffic Limit  : {BOLD}{args.max_bandwidth}{RESET} (±{args.variance:.0f}% random run-to-run variation)")
    elif args.bitrate:
        print(f"Traffic Limit  : {BOLD}{args.bitrate}{RESET} (±{args.variance:.0f}% per-flow variation)")
    print(f"Mode           : {'CONTINUOUS LOOP' if args.continuous else 'SINGLE RUN'}")
    if args.daemon:
        print(f"Process Type   : BACKGROUND DAEMON (PID: {os.getpid()})")

    iteration = 0
    history = []

    try:
        while True:
            iteration += 1
            print(f"\n{BOLD}{YELLOW}>>> Starting Iteration #{iteration} <<<{RESET}")

            if args.pattern in ["ring-allreduce", "all"]:
                flows = build_ring_allreduce_flows(servers, args.duration, args.streams, args.tos)
                res = execute_flow_batch(
                    flows, "Ring-AllReduce (Neighbor-to-Neighbor Ring)",
                    max_aggregate_bw=args.max_bandwidth,
                    per_flow_bw=args.bitrate,
                    bytes_limit=args.bytes_limit,
                    variance_pct=args.variance,
                )
                print_results_table(res, "Ring-AllReduce Collective", iteration)
                history.extend(res)

            if args.pattern in ["all-to-all", "all"]:
                flows = build_all_to_all_flows(servers, args.duration, args.streams, args.tos)
                res = execute_flow_batch(
                    flows, "All-to-All / MoE Token Dispatch (Full Mesh)",
                    max_aggregate_bw=args.max_bandwidth,
                    per_flow_bw=args.bitrate,
                    bytes_limit=args.bytes_limit,
                    variance_pct=args.variance,
                )
                print_results_table(res, "All-to-All Collective", iteration)
                history.extend(res)

            if args.pattern in ["incast", "all"]:
                flows = build_incast_flows(servers, args.duration, args.streams, args.tos)
                res = execute_flow_batch(
                    flows, f"Many-to-One Incast Burst -> {servers[0]['hostname']}",
                    max_aggregate_bw=args.max_bandwidth,
                    per_flow_bw=args.bitrate,
                    bytes_limit=args.bytes_limit,
                    variance_pct=args.variance,
                )
                print_results_table(res, "Incast Stress Test", iteration)
                history.extend(res)

            if args.pattern in ["multi-rail", "all"]:
                flows = build_multi_rail_flows(servers, args.duration, args.streams, args.tos)
                res = execute_flow_batch(
                    flows, f"8-Rail Dedicated GPU Interconnect ({servers[0]['hostname']} -> {servers[1]['hostname']})",
                    max_aggregate_bw=args.max_bandwidth,
                    per_flow_bw=args.bitrate,
                    bytes_limit=args.bytes_limit,
                    variance_pct=args.variance,
                )
                print_results_table(res, "Multi-Rail Rail-Optimized Burst", iteration)
                history.extend(res)

            if not args.continuous or (args.iterations > 0 and iteration >= args.iterations):
                break

            print(f"{CYAN}Iteration #{iteration} complete. Sleeping {args.interval}s (simulating compute epoch)...{RESET}")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}[INFO] Continuous simulation stopped by user.{RESET}")

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(history, f, indent=2)
        print(f"{GREEN}[OK] Benchmark history saved to: {args.json_out}{RESET}")


if __name__ == "__main__":
    main()
