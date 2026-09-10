#!/usr/bin/env python3
"""
Netris VPC-to-GPU Discovery & Offline Native Deployer
Interrogates Netris Controller database for VPC-to-ServerCluster mappings,
discovers assigned HGX GPU hosts, installs native iPerf3 packages offline,
and launches multi-rail daemons across ports 5201-5208.

Author: Netris Solutions Architecture
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List

PKG_DIR = "/var/cache/apt/archives"
DEB_PATTERNS = ["iperf3*.deb", "libiperf0*.deb", "libsctp1*.deb"]
TOPOLOGY_FILE = os.path.expanduser("~/netris-gpu-fabric-sim/vpc_gpu_topology.json")

# ANSI Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


def run_cmd(cmd: List[str], check: bool = True) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nError: {res.stderr.strip()}")
    return res.stdout.strip()


def query_netris_db(query: str) -> List[Dict[str, str]]:
    """Runs an SQL query against the Netris Controller MariaDB container."""
    cmd = [
        "sudo", "k3s", "kubectl", "exec", "-n", "netris-controller",
        "netris-controller-mariadb-0", "--",
        "mariadb", "-u", "root", "-pchangeme", "-BNe", query
    ]
    raw = run_cmd(cmd)
    if not raw:
        return []
    lines = raw.split("\n")
    results = []
    for line in lines:
        if line.strip():
            results.append(line.strip().split("\t"))
    return results


def parse_cloudsim_aliases() -> Dict[str, str]:
    """Extracts hostname to management IP mapping from ~/.cloudsim_aliases."""
    alias_path = os.path.expanduser("~/.cloudsim_aliases")
    host_to_ip = {}
    if not os.path.exists(alias_path):
        print(f"{YELLOW}[WARN] {alias_path} not found. Attempting fallback...{RESET}")
        return host_to_ip

    pattern = re.compile(r"alias\s+([\w\-]+)='ssh.*?root@([\d\.]+)'")
    with open(alias_path, "r") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                host_to_ip[m.group(1)] = m.group(2)
    return host_to_ip


def discover_vpc_gpu_mappings() -> Dict[str, Any]:
    """Queries Netris DB to discover VPCs, Server Clusters, and assigned HGX servers."""
    print(f"\n{BOLD}{CYAN}=== [1/4] Interrogating Netris Controller Database ==={RESET}")
    sql = """
    USE netris;
    SELECT 
        vpc.id AS vpc_id, 
        vpc.name AS vpc_name, 
        sc.id AS cluster_id, 
        sc.name AS cluster_name, 
        s.switch_id, 
        s.description AS server_hostname
    FROM srv_cluster sc
    JOIN srv_cluster_service_rel r_vnet ON (r_vnet.cluster_id = sc.id AND r_vnet.type = 'vnet')
    JOIN vpc ON vpc.id = r_vnet.vpc_id
    JOIN srv_cluster_service_rel r_hw ON (r_hw.cluster_id = sc.id AND r_hw.type = 'hw')
    JOIN switch s ON s.switch_id = r_hw.cluster_svc_id
    GROUP BY vpc.id, sc.id, s.switch_id;
    """
    rows = query_netris_db(sql)
    aliases = parse_cloudsim_aliases()

    vpcs: Dict[str, Any] = {}

    for row in rows:
        if len(row) < 6:
            continue
        vpc_id, vpc_name, cluster_id, cluster_name, switch_id, hostname = row
        if vpc_name not in vpcs:
            vpcs[vpc_name] = {
                "vpc_id": int(vpc_id),
                "vpc_name": vpc_name,
                "cluster_id": int(cluster_id),
                "cluster_name": cluster_name,
                "servers": [],
            }

        mgmt_ip = aliases.get(hostname)
        vpcs[vpc_name]["servers"].append({
            "hostname": hostname,
            "switch_id": int(switch_id),
            "mgmt_ip": mgmt_ip,
            "backend_rails": {},  # Will be populated via SSH inspection
        })

    print(f"{GREEN}[OK] Discovered {len(vpcs)} active VPC(s) with Server Clusters:{RESET}")
    for vname, vdata in vpcs.items():
        print(f"  -> VPC: {BOLD}{vname}{RESET} (ID: {vdata['vpc_id']}), Cluster: {vdata['cluster_name']}, Assigned Hosts: {len(vdata['servers'])}")
        for s in vdata["servers"]:
            print(f"       * {s['hostname']} (Mgmt IP: {s['mgmt_ip']})")

    return vpcs


def inspect_backend_interfaces(mgmt_ip: str) -> Dict[int, str]:
    """Inspects an HGX server to discover high-speed East-West backend fabric IPs (ens5-ens12)."""
    ssh_cmd = [
        "ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5", f"root@{mgmt_ip}", "ip -br -4 a"
    ]
    raw = run_cmd(ssh_cmd)
    backend_rails = {}

    # Expected rail interface mapping on HGX CloudSim nodes:
    # ens5  -> Rail 0 (172.16.x.x)
    # ens7  -> Rail 1 (172.18.x.x)
    # ens9  -> Rail 2 (172.20.x.x)
    # ens11 -> Rail 3 (172.22.x.x)
    # ens6  -> Rail 4 (172.24.x.x)
    # ens8  -> Rail 5 (172.26.x.x)
    # ens10 -> Rail 6 (172.28.x.x)
    # ens12 -> Rail 7 (172.30.x.x)
    iface_to_rail = {
        "ens5": 0, "ens7": 1, "ens9": 2, "ens11": 3,
        "ens6": 4, "ens8": 5, "ens10": 6, "ens12": 7
    }

    for line in raw.split("\n"):
        parts = line.split()
        if len(parts) >= 3:
            iface = parts[0]
            if iface in iface_to_rail:
                ip_cidr = parts[2]
                ip = ip_cidr.split("/")[0]
                rail_id = iface_to_rail[iface]
                backend_rails[rail_id] = {"interface": iface, "ip": ip}

    return backend_rails


def stage_offline_packages() -> List[str]:
    """Ensures offline deb packages for iperf3 and dependencies exist in local packages folder."""
    print(f"\n{BOLD}{CYAN}=== [2/4] Verifying Offline Package Cache on Controller ==={RESET}")
    local_pkg_dir = os.path.expanduser("~/netris-gpu-fabric-sim/packages")
    os.makedirs(local_pkg_dir, exist_ok=True)

    # Copy cached deb files from /var/cache/apt/archives using sudo if needed
    copy_cmd = (
        f"sudo cp /var/cache/apt/archives/*iperf*.deb "
        f"/var/cache/apt/archives/*sctp*.deb '{local_pkg_dir}/' 2>/dev/null || true && "
        f"sudo chown -R $(id -u):$(id -g) '{local_pkg_dir}'"
    )
    subprocess.run(copy_cmd, shell=True, check=False)

    import glob
    pkg_files = glob.glob(os.path.join(local_pkg_dir, "*.deb"))

    if len(pkg_files) < 3:
        print(f"{YELLOW}[INFO] Downloading deb packages to cache...{RESET}")
        subprocess.run(["sudo", "apt-get", "install", "-y", "--download-only", "iperf3", "libiperf0", "libsctp1"], check=True)
        subprocess.run(copy_cmd, shell=True, check=False)
        pkg_files = glob.glob(os.path.join(local_pkg_dir, "*.deb"))

    print(f"{GREEN}[OK] Staged {len(pkg_files)} offline deb packages for bare-metal distribution:{RESET}")
    for p in pkg_files:
        print(f"  -> {os.path.basename(p)}")
    return pkg_files


def deploy_to_host(server: Dict[str, Any], deb_files: List[str]):
    """Installs native iperf3 on the HGX host and starts 8 rail daemons."""
    hostname = server["hostname"]
    mgmt_ip = server["mgmt_ip"]
    print(f"\n{BOLD}[Deploying]{RESET} Host: {BOLD}{hostname}{RESET} ({mgmt_ip})")

    # 1. SCP deb files to host
    scp_cmd = [
        "scp", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5"
    ] + deb_files + [f"root@{mgmt_ip}:/tmp/"]
    run_cmd(scp_cmd)
    print(f"  -> Copied offline .deb packages to /tmp/")

    # 2. Install packages & start daemons
    remote_script = """
    export DEBIAN_FRONTEND=noninteractive
    dpkg -i /tmp/iperf3*.deb /tmp/libiperf0*.deb /tmp/libsctp1*.deb >/dev/null 2>&1 || true
    rm -f /tmp/iperf3*.deb /tmp/libiperf0*.deb /tmp/libsctp1*.deb

    # Kill existing iperf3 instances
    killall -q iperf3 2>/dev/null || true
    sleep 0.5

    # Start 8 daemons on ports 5201 through 5208 (Rail 0 - 7)
    for port in $(seq 5201 5208); do
        iperf3 -s -p $port -D --logfile /var/log/iperf3-port-$port.log
    done
    """

    ssh_cmd = [
        "ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5", f"root@{mgmt_ip}", remote_script
    ]
    run_cmd(ssh_cmd)

    # 3. Verify daemons
    verify_cmd = [
        "ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5", f"root@{mgmt_ip}", "pgrep -c iperf3"
    ]
    daemon_count = run_cmd(verify_cmd)
    print(f"  -> {GREEN}Native iperf3 verified: {daemon_count} rail daemons active (Ports 5201-5208){RESET}")


def main():
    parser = argparse.ArgumentParser(description="Discover Netris VPC GPU hosts and deploy offline native iPerf3")
    parser.add_argument("--vpc", type=str, default=None, help="Filter discovery to specific VPC name")
    args = parser.parse_args()

    print(f"{BOLD}{CYAN}================================================================{RESET}")
    print(f"{BOLD}{CYAN}   NETRIS CONTROLLER: VPC-TO-GPU DISCOVERY & DEPLOYER TOOLKIT   {RESET}")
    print(f"{BOLD}{CYAN}================================================================{RESET}")

    vpcs = discover_vpc_gpu_mappings()
    if args.vpc:
        if args.vpc not in vpcs:
            print(f"{RED}[ERROR] VPC '{args.vpc}' not found in Netris database.{RESET}")
            sys.exit(1)
        vpcs = {args.vpc: vpcs[args.vpc]}

    deb_files = stage_offline_packages()

    print(f"\n{BOLD}{CYAN}=== [3/4] Inspecting High-Speed Backend Rails & Deploying ==={RESET}")
    for vname, vdata in vpcs.items():
        print(f"\nProcessing VPC: {BOLD}{vname}{RESET}")
        for server in vdata["servers"]:
            if not server["mgmt_ip"]:
                print(f"{YELLOW}[SKIP] No management IP found for {server['hostname']}{RESET}")
                continue
            # Discover backend RoCEv2 rail IPs
            rails = inspect_backend_interfaces(server["mgmt_ip"])
            server["backend_rails"] = rails
            print(f"  -> {server['hostname']}: Discovered {len(rails)} high-speed backend rails")

            # Deploy native packages
            deploy_to_host(server, deb_files)

    print(f"\n{BOLD}{CYAN}=== [4/4] Persisting Topology Manifest ==={RESET}")
    os.makedirs(os.path.dirname(TOPOLOGY_FILE), exist_ok=True)
    with open(TOPOLOGY_FILE, "w") as f:
        json.dump(vpcs, f, indent=2)
    print(f"{GREEN}[OK] Topology successfully saved to: {TOPOLOGY_FILE}{RESET}")
    print(f"\n{BOLD}{GREEN}Ready for AI Collective Traffic Simulation!{RESET}\n")


if __name__ == "__main__":
    main()
