#!/usr/bin/env python3
"""
GPU AI Fabric Traffic Simulator
Simulates distributed GPU cluster collective communication patterns (NCCL/RCCL)
using containerized multi-rail iPerf3 endpoints over simulated RoCEv2 fabric.

Author: Netris Solutions Architecture
"""

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Tuple

DEFAULT_CONTAINERS = [
    {"name": "pretend-gpu-01", "ip": "172.28.0.11", "role": "worker"},
    {"name": "pretend-gpu-02", "ip": "172.28.0.12", "role": "worker"},
    {"name": "pretend-gpu-03", "ip": "172.28.0.13", "role": "worker"},
    {"name": "pretend-gpu-04", "ip": "172.28.0.14", "role": "storage_target"},
]

BASE_PORT = 5201
NUM_RAILS = 8

# ANSI Terminal Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


def check_docker_containers():
    """Verify that the pretend GPU nodes are running and reachable."""
    try:
        res = subprocess.run(
            ["docker", "ps", "--filter", "name=pretend-gpu", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        running = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
        expected = [c["name"] for c in DEFAULT_CONTAINERS]
        missing = [name for name in expected if name not in running]
        if missing:
            print(f"{RED}[ERROR] Missing running pretend GPU containers: {missing}{RESET}")
            print(f"{YELLOW}Hint: Run 'docker compose up -d' first.{RESET}")
            sys.exit(1)
        return True
    except subprocess.CalledProcessError as e:
        print(f"{RED}[ERROR] Failed to query Docker: {e}{RESET}")
        sys.exit(1)


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


def run_iperf_flow(
    src_node: str,
    dst_ip: str,
    dst_name: str,
    port: int,
    rail_id: int,
    duration: int,
    streams: int,
    protocol: str = "tcp",
    tos: int = 96,  # TOS 96 = DSCP 24 (CS3/AF31) often used for RoCEv2 Lossless Priority 3
    bitrate_per_stream: str = None,
    bytes_limit: str = None,
) -> Dict[str, Any]:
    """
    Executes an iperf3 client command from within src_node targeting dst_ip:port.
    Returns parsed metrics dictionary.
    """
    cmd = [
        "docker", "exec", src_node,
        "iperf3",
        "-c", dst_ip,
        "-p", str(port),
    ]

    if bytes_limit:
        cmd.extend(["-n", str(bytes_limit)])
    else:
        cmd.extend(["-t", str(duration)])

    cmd.extend(["-P", str(streams)])

    if protocol == "udp":
        cmd.extend(["-u", "-b", bitrate_per_stream or "10G"])
    else:
        # Set Type of Service (TOS) to emulate RoCEv2 DSCP tagging
        cmd.extend(["--tos", str(tos)])
        if bitrate_per_stream:
            cmd.extend(["-b", bitrate_per_stream])

    cmd.append("-J")

    start_t = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_t

    flow_result = {
        "src": src_node,
        "dst": dst_name,
        "dst_ip": dst_ip,
        "port": port,
        "rail_id": rail_id,
        "protocol": protocol,
        "duration": duration,
        "streams": streams,
        "elapsed_sec": round(elapsed, 2),
        "success": False,
        "throughput_bps": 0.0,
        "throughput_gbps": 0.0,
        "bytes_sent": 0,
        "retransmits": 0,
        "mean_rtt_ms": 0.0,
        "error": None,
    }

    if res.returncode != 0:
        flow_result["error"] = res.stderr.strip() or res.stdout.strip()
        return flow_result

    try:
        data = json.loads(res.stdout)
        end_data = data.get("end", {})

        if protocol == "tcp":
            sender = end_data.get("sum_sent", {})
            receiver = end_data.get("sum_received", {})

            bytes_sent = sender.get("bytes", 0)
            bps = sender.get("bits_per_second", 0.0)
            retransmits = sender.get("retransmits", 0)

            # RTT summary if available
            streams_data = end_data.get("streams", [])
            rtts = []
            for s in streams_data:
                sender_s = s.get("sender", {})
                if "mean_rtt" in sender_s:
                    rtts.append(sender_s["mean_rtt"] / 1000.0)  # convert usec to ms
            mean_rtt = sum(rtts) / len(rtts) if rtts else 0.0

            flow_result.update({
                "success": True,
                "bytes_sent": bytes_sent,
                "throughput_bps": bps,
                "throughput_gbps": round(bps / 1e9, 2),
                "retransmits": retransmits,
                "mean_rtt_ms": round(mean_rtt, 3),
            })
        else:
            # UDP
            sum_data = end_data.get("sum", {})
            bytes_sent = sum_data.get("bytes", 0)
            bps = sum_data.get("bits_per_second", 0.0)
            lost_pkts = sum_data.get("lost_packets", 0)
            jitter_ms = sum_data.get("jitter_ms", 0.0)
            flow_result.update({
                "success": True,
                "bytes_sent": bytes_sent,
                "throughput_bps": bps,
                "throughput_gbps": round(bps / 1e9, 2),
                "retransmits": lost_pkts,
                "jitter_ms": round(jitter_ms, 3),
            })

    except Exception as e:
        flow_result["error"] = f"JSON parse error: {e}"

    return flow_result


def execute_flow_batch(
    flows: List[Dict[str, Any]],
    title: str,
    max_aggregate_bw: str = None,
    per_flow_bw: str = None,
    bytes_limit: str = None,
) -> List[Dict[str, Any]]:
    """Runs a batch of iperf3 flows concurrently across nodes using ThreadPoolExecutor."""
    print(f"\n{BOLD}{CYAN}=== Executing: {title} ({len(flows)} concurrent flows) ==={RESET}")

    stream_bitrate_str = None
    if max_aggregate_bw:
        total_target_bps = parse_bandwidth_to_bps(max_aggregate_bw)
        streams_per_flow = flows[0]["streams"] if flows else 1
        total_streams = len(flows) * streams_per_flow
        bps_per_stream = total_target_bps / max(total_streams, 1)
        stream_bitrate_str = format_bps(bps_per_stream)
        print(f"Applying Aggregate Ceiling: {BOLD}{max_aggregate_bw}{RESET} across {len(flows)} flows ({total_streams} streams -> {stream_bitrate_str}/stream)")
    elif per_flow_bw:
        flow_target_bps = parse_bandwidth_to_bps(per_flow_bw)
        streams_per_flow = flows[0]["streams"] if flows else 1
        bps_per_stream = flow_target_bps / max(streams_per_flow, 1)
        stream_bitrate_str = format_bps(bps_per_stream)
        print(f"Applying Per-Flow Cap: {BOLD}{per_flow_bw}{RESET} ({stream_bitrate_str}/stream)")

    if bytes_limit:
        print(f"Applying Per-Flow Data Cap: {BOLD}{bytes_limit}{RESET}")

    print(f"Injecting synchronized traffic across simulated GPU backend fabric...\n")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(flows) + 2) as executor:
        future_to_flow = {
            executor.submit(
                run_iperf_flow,
                flow["src"],
                flow["dst_ip"],
                flow["dst_name"],
                flow["port"],
                flow["rail_id"],
                flow["duration"],
                flow["streams"],
                flow["protocol"],
                flow["tos"],
                stream_bitrate_str,
                bytes_limit,
            ): flow
            for flow in flows
        }

        for future in concurrent.futures.as_completed(future_to_flow):
            res = future.result()
            results.append(res)

    return results


def print_results_table(results: List[Dict[str, Any]], title: str):
    """Prints a clean, scannable ASCII table summarizing the collective benchmark."""
    print(f"\n{BOLD}{GREEN}------------------------------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}{MAGENTA} COLLECTIVE BENCHMARK RESULTS: {title}{RESET}")
    print(f"{BOLD}{GREEN}------------------------------------------------------------------------------------------------{RESET}")
    print(f"{'Source Node':<16} {'Destination':<16} {'Rail/Port':<11} {'Streams':<8} {'Throughput':<14} {'Retrans/Loss':<13} {'Status'}")
    print(f"{'-'*16} {'-'*16} {'-'*11} {'-'*8} {'-'*14} {'-'*13} {'-'*8}")

    total_throughput_gbps = 0.0
    total_bytes = 0
    total_retransmits = 0

    # Sort results by src and rail
    sorted_res = sorted(results, key=lambda x: (x["src"], x["rail_id"]))

    for r in sorted_res:
        src = r["src"]
        dst = f"{r['dst']} ({r['dst_ip']})"
        rail_port = f"R{r['rail_id']} (:{r['port']})"
        streams = f"{r['streams']} QPs"

        if r["success"]:
            tp_str = f"{r['throughput_gbps']:>6.2f} Gbps"
            retrans_str = f"{r['retransmits']:>5} pkts"
            status_str = f"{GREEN}PASS{RESET}"
            total_throughput_gbps += r["throughput_gbps"]
            total_bytes += r["bytes_sent"]
            total_retransmits += r["retransmits"]
        else:
            tp_str = "    0.00 Gbps"
            retrans_str = "      N/A"
            status_str = f"{RED}FAIL{RESET}"

        print(f"{src:<16} {dst:<16} {rail_port:<11} {streams:<8} {tp_str:<14} {retrans_str:<13} {status_str}")

    print(f"{'-'*16} {'-'*16} {'-'*11} {'-'*8} {'-'*14} {'-'*13} {'-'*8}")
    total_gb = total_bytes / (1024 ** 3)
    print(f"{BOLD}Fabric Aggregated Throughput : {CYAN}{total_throughput_gbps:.2f} Gbps{RESET}")
    print(f"{BOLD}Total Data Transferred       : {CYAN}{total_gb:.2f} GB{RESET}")
    print(f"{BOLD}Total Fabric Retransmissions : {YELLOW if total_retransmits > 0 else GREEN}{total_retransmits} packets{RESET}")
    print(f"{BOLD}{GREEN}------------------------------------------------------------------------------------------------{RESET}\n")


def simulate_ring_allreduce(duration: int, streams: int, tos: int, protocol: str, max_bw: str = None, per_flow_bw: str = None, bytes_limit: str = None) -> List[Dict[str, Any]]:
    """
    Ring-AllReduce Collective:
    Node 1 -> Node 2 -> Node 3 -> Node 4 -> Node 1.
    All nodes transmit simultaneously across multiple rails.
    Models distributed model parameter reduction (e.g. Megatron-LM / PyTorch FSDP).
    """
    nodes = DEFAULT_CONTAINERS
    num_nodes = len(nodes)
    flows = []

    for i in range(num_nodes):
        src = nodes[i]
        dst = nodes[(i + 1) % num_nodes]
        # Distribute flows across rail ports (e.g., 2 parallel rail ports per link)
        for rail in range(2):
            port = BASE_PORT + rail
            flows.append({
                "src": src["name"],
                "dst_name": dst["name"],
                "dst_ip": dst["ip"],
                "port": port,
                "rail_id": rail,
                "duration": duration,
                "streams": streams,
                "protocol": protocol,
                "tos": tos,
            })

    results = execute_flow_batch(flows, "Ring-AllReduce Collective (Ring Topology)", max_aggregate_bw=max_bw, per_flow_bw=per_flow_bw, bytes_limit=bytes_limit)
    print_results_table(results, "Ring-AllReduce (Neighbor-to-Neighbor Synchronous Ring)")
    print(f"{BOLD}[AI Architectural Insight]{RESET} Ring-AllReduce produces synchronized, non-interfering circular flows.")
    print(f"In a healthy RoCEv2 fabric, each ring segment achieves deterministic line-rate with 0 retransmissions.")
    return results


def simulate_all_to_all(duration: int, streams: int, tos: int, protocol: str, max_bw: str = None, per_flow_bw: str = None, bytes_limit: str = None) -> List[Dict[str, Any]]:
    """
    All-to-All / Mixture of Experts (MoE) Collective:
    Every GPU node communicates concurrently with every other GPU node.
    Stresses fabric bisection bandwidth and buffer pools with multi-flow cross-traffic.
    """
    nodes = DEFAULT_CONTAINERS
    flows = []

    for src_idx, src in enumerate(nodes):
        # Target all other nodes
        rail_counter = 0
        for dst_idx, dst in enumerate(nodes):
            if src_idx == dst_idx:
                continue
            # Assign dedicated port to prevent iperf daemon collision on target
            port = BASE_PORT + (src_idx % NUM_RAILS)
            flows.append({
                "src": src["name"],
                "dst_name": dst["name"],
                "dst_ip": dst["ip"],
                "port": port,
                "rail_id": rail_counter,
                "duration": duration,
                "streams": streams,
                "protocol": protocol,
                "tos": tos,
            })
            rail_counter += 1

    results = execute_flow_batch(flows, "All-to-All / MoE Token Dispatch Collective", max_aggregate_bw=max_bw, per_flow_bw=per_flow_bw, bytes_limit=bytes_limit)
    print_results_table(results, "All-to-All Collective (Full-Mesh Bisection Stress)")
    print(f"{BOLD}[AI Architectural Insight]{RESET} All-to-All collective drives maximum entropy and simultaneous mesh flows.")
    print(f"This reveals potential leaf switch buffer contention and tests ECMP hash distribution across spine links.")
    return results


def simulate_incast(duration: int, streams: int, tos: int, protocol: str, target_name: str = "pretend-gpu-04", max_bw: str = None, per_flow_bw: str = None, bytes_limit: str = None) -> List[Dict[str, Any]]:
    """
    Many-to-One Incast Collective:
    Simulates multiple worker GPU nodes blasting into a single storage target or master parameter node.
    Models AI checkpoint write bursts (e.g. VAST Data / Weka) or AllGather stages.
    """
    target = next((c for c in DEFAULT_CONTAINERS if c["name"] == target_name), DEFAULT_CONTAINERS[-1])
    workers = [c for c in DEFAULT_CONTAINERS if c["name"] != target["name"]]

    flows = []
    for w_idx, worker in enumerate(workers):
        # Each worker hits 2 distinct rail ports on the target
        for r in range(2):
            port = BASE_PORT + (w_idx * 2) + r
            flows.append({
                "src": worker["name"],
                "dst_name": target["name"],
                "dst_ip": target["ip"],
                "port": port,
                "rail_id": r,
                "duration": duration,
                "streams": streams,
                "protocol": protocol,
                "tos": tos,
            })

    results = execute_flow_batch(flows, f"Many-to-One Incast / Storage Checkpoint Burst -> {target['name']}", max_aggregate_bw=max_bw, per_flow_bw=per_flow_bw, bytes_limit=bytes_limit)
    print_results_table(results, f"Incast Stress Test (Targets: {target['name']})")
    print(f"{BOLD}[AI Architectural Insight]{RESET} Incast creates severe port oversubscription at the destination.")
    print(f"In RoCEv2 networks, this triggers PFC (Priority Flow Control) pause frames and ECN (Explicit Congestion Notification) marking.")
    return results


def simulate_multi_rail(duration: int, streams: int, tos: int, protocol: str, max_bw: str = None, per_flow_bw: str = None, bytes_limit: str = None) -> List[Dict[str, Any]]:
    """
    Multi-Rail Rail-Optimized Interconnect:
    Simulates 8 distinct GPU rails between two HGX/MI300X nodes (pretend-gpu-01 -> pretend-gpu-02).
    Rail 0 -> Port 5201, Rail 1 -> Port 5202, ... Rail 7 -> Port 5208.
    """
    src = DEFAULT_CONTAINERS[0]
    dst = DEFAULT_CONTAINERS[1]
    flows = []

    for rail in range(NUM_RAILS):
        port = BASE_PORT + rail
        flows.append({
            "src": src["name"],
            "dst_name": dst["name"],
            "dst_ip": dst["ip"],
            "port": port,
            "rail_id": rail,
            "duration": duration,
            "streams": streams,
            "protocol": protocol,
            "tos": tos,
        })

    results = execute_flow_batch(flows, f"8-Rail Dedicated GPU Interconnect ({src['name']} -> {dst['name']})", max_aggregate_bw=max_bw, per_flow_bw=per_flow_bw, bytes_limit=bytes_limit)
    print_results_table(results, "Multi-Rail Rail-Optimized Burst (8x Parallel Rails)")
    print(f"{BOLD}[AI Architectural Insight]{RESET} Multi-Rail architectures map each GPU directly to a dedicated rail/NIC.")
    print(f"Eliminates inter-GPU contention and maximizes per-GPU PCIe-to-NIC saturation.")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Simulate GPU AI Fabric Traffic Patterns (Ring-AllReduce, All-to-All, Incast, Multi-Rail) using iPerf3"
    )
    parser.add_argument(
        "--pattern",
        choices=["ring-allreduce", "all-to-all", "incast", "multi-rail", "all"],
        default="ring-allreduce",
        help="AI Collective communication pattern to simulate",
    )
    parser.add_argument(
        "--duration", "-t",
        type=int,
        default=5,
        help="Duration of the simulation in seconds (default: 5s)",
    )
    parser.add_argument(
        "--streams", "-P",
        type=int,
        default=4,
        help="Number of parallel Queue Pairs (iPerf3 streams) per rail (default: 4)",
    )
    parser.add_argument(
        "--protocol",
        choices=["tcp", "udp"],
        default="tcp",
        help="L4 Transport protocol (default: tcp)",
    )
    parser.add_argument(
        "--tos",
        type=int,
        default=96,
        help="IP Type-of-Service / DSCP marking (default: 96 = DSCP 24 / RoCEv2 Priority 3)",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="pretend-gpu-04",
        help="Target node for incast simulation (default: pretend-gpu-04)",
    )
    parser.add_argument(
        "--max-bandwidth", "-B",
        type=str,
        default=None,
        help="Overall aggregate bandwidth limit (e.g. '500M', '1G', '2G')",
    )
    parser.add_argument(
        "--bitrate", "-b",
        type=str,
        default=None,
        help="Per-flow bandwidth limit (e.g. '50M', '100M')",
    )
    parser.add_argument(
        "--bytes-limit", "-n",
        type=str,
        default=None,
        help="Per-flow byte volume limit (e.g. '100M', '500M')",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=None,
        help="Optional path to output raw metrics in JSON",
    )

    args = parser.parse_args()

    print(f"{BOLD}{CYAN}================================================================{RESET}")
    print(f"{BOLD}{CYAN}         GPU AI FABRIC TRAFFIC SIMULATOR (iPerf3 / RoCEv2)      {RESET}")
    print(f"{BOLD}{CYAN}================================================================{RESET}")
    print(f"Simulating distributed GPU clusters on Netris-ready Ethernet topologies")
    print(f"Nodes: {[c['name'] for c in DEFAULT_CONTAINERS]}")
    print(f"QoS DSCP Marking: TOS {args.tos} (RoCEv2 Lossless Traffic Class)")
    print(f"Duration: {args.duration}s | Streams per rail: {args.streams} QPs | Transport: {args.protocol.upper()}")
    if args.max_bandwidth:
        print(f"Traffic Ceiling : {BOLD}{args.max_bandwidth}{RESET} (Aggregate Cluster Bandwidth)")
    elif args.bitrate:
        print(f"Traffic Ceiling : {BOLD}{args.bitrate}{RESET} (Per-Flow Bandwidth)")

    check_docker_containers()

    all_results = {}

    if args.pattern == "ring-allreduce" or args.pattern == "all":
        all_results["ring-allreduce"] = simulate_ring_allreduce(
            args.duration, args.streams, args.tos, args.protocol,
            max_bw=args.max_bandwidth, per_flow_bw=args.bitrate, bytes_limit=args.bytes_limit
        )

    if args.pattern == "all-to-all" or args.pattern == "all":
        all_results["all-to-all"] = simulate_all_to_all(
            args.duration, args.streams, args.tos, args.protocol,
            max_bw=args.max_bandwidth, per_flow_bw=args.bitrate, bytes_limit=args.bytes_limit
        )

    if args.pattern == "incast" or args.pattern == "all":
        all_results["incast"] = simulate_incast(
            args.duration, args.streams, args.tos, args.protocol, args.target,
            max_bw=args.max_bandwidth, per_flow_bw=args.bitrate, bytes_limit=args.bytes_limit
        )

    if args.pattern == "multi-rail" or args.pattern == "all":
        all_results["multi-rail"] = simulate_multi_rail(
            args.duration, args.streams, args.tos, args.protocol,
            max_bw=args.max_bandwidth, per_flow_bw=args.bitrate, bytes_limit=args.bytes_limit
        )

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\n{GREEN}[OK] Raw metrics written to {args.json_out}{RESET}")


if __name__ == "__main__":
    main()
