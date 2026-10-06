#!/usr/bin/env python3
"""
test_edge_cases.py
Automated edge-case test suite for Netris Terraform Generator.
Tests multiple fabric architectures against logical consistency rules,
OpenTofu validation, and plan generation.
"""

import os
import sys
import shutil
import subprocess
import csv
import io
import re
from typing import Dict, Any, List, Tuple
from tf_generator import TerraformGenerator

DEPLOYMENTS_DIR = os.path.join(os.path.dirname(__file__), "deployments")
CACHE_DIR = os.path.join(DEPLOYMENTS_DIR, "msp02")
TOFU_BIN = "/opt/homebrew/bin/tofu"


TEST_CASES: Dict[str, Dict[str, Any]] = {
    "case_1_single_plane_minimal": {
        "site_name": "TEST-SP-MIN",
        "planes_count": 1,
        "ew_spines_per_plane": 1,
        "ew_leaves_per_plane": 1,
        "switch_port_count": 32,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 2,
        "gpu_roce_ports": 8,
        "gpu_ns_ports": 1,
        "ns_spines": 1,
        "ns_leaves": 1,
        "softgate_count": 1,
        "enable_storage": False,
        "enable_oob": False,
    },
    "case_2_single_plane_standard": {
        "site_name": "TEST-SP-STD",
        "planes_count": 1,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 4,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 8,
        "gpu_roce_ports": 16,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 2,
        "enable_storage": True,
        "storage_leaves": 2,
        "storage_servers": 4,
        "enable_oob": True,
        "oob_switches": 2,
    },
    "case_3_dual_plane_32_port_switches": {
        "site_name": "TEST-DP-32P",
        "planes_count": 2,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 4,
        "switch_port_count": 32,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 8,
        "gpu_roce_ports": 16,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 2,
        "enable_storage": True,
        "storage_leaves": 2,
        "storage_servers": 2,
        "enable_oob": True,
        "oob_switches": 2,
    },
    "case_4_quad_plane_max_scale": {
        "site_name": "TEST-QP-MAX",
        "planes_count": 4,
        "ew_spines_per_plane": 4,
        "ew_leaves_per_plane": 8,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 16,
        "gpu_roce_ports": 16,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 4,
        "enable_storage": True,
        "storage_leaves": 4,
        "storage_servers": 8,
        "enable_oob": True,
        "oob_switches": 2,
    },
    "case_5_storage_disabled_oob_disabled": {
        "site_name": "TEST-NO-OPT",
        "planes_count": 2,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 4,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-pro",
        "gpu_count": 4,
        "gpu_roce_ports": 16,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 2,
        "enable_storage": False,
        "enable_oob": False,
    },
    "case_6_single_oob_single_storage_leaf": {
        "site_name": "TEST-1OOB-1STR",
        "planes_count": 2,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 2,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 4,
        "gpu_roce_ports": 16,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 1,
        "enable_storage": True,
        "storage_leaves": 1,
        "storage_servers": 2,
        "enable_oob": True,
        "oob_switches": 1,
    },
    "case_7_single_ns_leaf": {
        "site_name": "TEST-1NS-LF",
        "planes_count": 2,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 2,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 4,
        "gpu_roce_ports": 16,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 1,
        "softgate_count": 1,
        "enable_storage": False,
        "enable_oob": False,
    },
    "case_8_custom_cidrs_and_sonic": {
        "site_name": "TEST-SONIC",
        "planes_count": 2,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 4,
        "switch_port_count": 64,
        "nos": "sonic",
        "softgate_flavor": "sg-pro",
        "gpu_count": 4,
        "gpu_roce_ports": 16,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 2,
        "enable_storage": True,
        "storage_leaves": 2,
        "storage_servers": 4,
        "enable_oob": True,
        "oob_switches": 2,
        "ew_loopback_subnet": "10.200.0.0/24",
        "ew_p2p_allocation": "10.201.0.0/16",
        "ns_loopback_subnet": "10.200.1.0/24",
        "ns_mgmt_subnet": "10.200.2.0/24",
        "storage_subnet": "10.200.3.0/24",
        "oob_subnet": "10.200.4.0/24",
        "public_asn": 65000,
        "roh_asn": 65001,
        "switch_asn_base": 4200100000,
    },
    "case_9_quad_plane_8_roce_ports": {
        "site_name": "TEST-QP-8ROCE",
        "planes_count": 4,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 4,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 4,
        "gpu_roce_ports": 8,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 2,
        "enable_storage": False,
        "enable_oob": False,
    },
    "case_10_128_port_switches": {
        "site_name": "TEST-128P",
        "planes_count": 2,
        "ew_spines_per_plane": 4,
        "ew_leaves_per_plane": 4,
        "switch_port_count": 128,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 16,
        "gpu_roce_ports": 16,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 2,
        "enable_storage": True,
        "storage_leaves": 2,
        "storage_servers": 4,
        "enable_oob": True,
        "oob_switches": 2,
    },
    "case_11_three_oob_switches": {
        "site_name": "TEST-3OOB",
        "planes_count": 1,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 2,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 2,
        "gpu_roce_ports": 8,
        "gpu_ns_ports": 1,
        "ns_spines": 1,
        "ns_leaves": 1,
        "softgate_count": 1,
        "enable_storage": False,
        "enable_oob": True,
        "oob_switches": 3,
    },
    "case_12_three_softgates": {
        "site_name": "TEST-3SG",
        "planes_count": 2,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 2,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-pro",
        "gpu_count": 4,
        "gpu_roce_ports": 16,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 3,
        "enable_storage": False,
        "enable_oob": False,
    },
    "case_13_single_gpu_server": {
        "site_name": "TEST-1GPU",
        "planes_count": 4,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 2,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 1,
        "gpu_roce_ports": 16,
        "gpu_ns_ports": 1,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 2,
        "enable_storage": False,
        "enable_oob": False,
    },
    "case_14_minimal_storage_1leaf_1server": {
        "site_name": "TEST-1STR-1SRV",
        "planes_count": 1,
        "ew_spines_per_plane": 1,
        "ew_leaves_per_plane": 1,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 2,
        "gpu_roce_ports": 8,
        "gpu_ns_ports": 1,
        "ns_spines": 1,
        "ns_leaves": 1,
        "softgate_count": 1,
        "enable_storage": True,
        "storage_leaves": 1,
        "storage_servers": 1,
        "enable_oob": False,
    },
    "case_15_spectrum_x_reference_hgx": {
        "site_name": "TEST-SPEC-X",
        "planes_count": 2,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 4,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 8,
        "gpu_profile": {
            "preset_id": "hgx_spectrum_x",
            "name": "NVIDIA HGX H100 (Spectrum-X)",
            "roce_ports": 8,
            "ns_ports": 2,
            "oob_ports": 1,
            "total_ports": 11
        },
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 2,
        "enable_storage": True,
        "storage_leaves": 2,
        "storage_servers": 4,
        "storage_profile": {
            "preset_id": "storage_high_speed",
            "name": "High-IOPS NVMe-oF Storage Server",
            "roce_ports": 2,
            "ns_ports": 2,
            "oob_ports": 1,
            "total_ports": 5
        },
        "enable_oob": True,
        "oob_switches": 2,
    },
    "case_16_auto_optimized_ns_sizing": {
        "site_name": "TEST-AUTO-NS",
        "planes_count": 2,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 4,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 32,
        "gpu_profile": {
            "preset_id": "hgx_spectrum_x",
            "name": "NVIDIA HGX H100",
            "roce_ports": 8,
            "ns_ports": 2,
            "oob_ports": 1,
            "total_ports": 11
        },
        "auto_optimize_ns": True,
        "enable_storage": True,
        "storage_leaves": 2,
        "storage_servers": 8,
        "enable_oob": True,
        "oob_switches": 2,
    },
    "case_17_converged_storage_fabric": {
        "site_name": "TEST-CONV-STR",
        "planes_count": 2,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 4,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 8,
        "gpu_roce_ports": 16,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 2,
        "enable_storage": True,
        "storage_network_mode": "converged",
        "storage_servers": 4,
        "storage_ns_ports": 2,
        "enable_oob": True,
        "oob_switches": 2,
    },
    "case_18_custom_netris_inventory_profile": {
        "site_name": "TEST-CUST-PROF",
        "planes_count": 2,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 2,
        "switch_port_count": 64,
        "nos": "cumulus_nvue",
        "softgate_flavor": "sg-hs",
        "gpu_count": 4,
        "gpu_roce_ports": 8,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 2,
        "softgate_count": 2,
        "enable_storage": False,
        "enable_oob": True,
        "oob_switches": 2,
        "acl_default_policy": "deny",
        "vlan_range": "100-2000",
        "vlan_range_auto_assign": "200-1900",
        "roce_adaptive_routing": True,
        "congestion_control": True,
        "qos_and_roce": True,
        "aggregate_l3vpn_prefix": True,
        "unnumbered_bgp_underlay": True,
        "optimise_bgp_overlay": True,
        "refarch": "b300_spx_2_tier_dual_plane",
    },
    "case_19_large_128_gpu_4plane_fabric": {
        "site_name": "Test-128GPU-Fabric",
        "planes_count": 4,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 8,
        "switch_port_count": 64,
        "gpu_count": 128,
        "gpu_roce_ports": 8,
        "gpu_ns_ports": 2,
        "ns_spines": 2,
        "ns_leaves": 6,
        "softgate_count": 4,
        "enable_storage": True,
        "storage_servers": 4,
        "storage_network_mode": "standalone",
        "storage_leaves": 2,
        "enable_oob": True,
        "oob_switches": 2,
    }
}


def check_logical_invariants(files: Dict[str, str], cfg: Dict[str, Any]) -> List[str]:
    """Inspects generated CSVs and HCL for logical bugs."""
    errors = []
    
    # 1. Parse switches to know their portcount
    switch_portcounts = {}
    switch_ips = {}
    if "csv/switches.csv" in files:
        reader = csv.DictReader(io.StringIO(files["csv/switches.csv"]))
        for row in reader:
            s_name = row["name"]
            p_count = int(row["portcount"])
            switch_portcounts[s_name] = p_count
            lb = row["loopback"]
            mgmt = row["mgmtip"]
            if lb in switch_ips:
                errors.append(f"Duplicate switch loopback IP {lb} on {s_name} and {switch_ips[lb]}")
            switch_ips[lb] = s_name
            if mgmt in switch_ips:
                errors.append(f"Duplicate switch mgmt IP {mgmt} on {s_name} and {switch_ips[mgmt]}")
            switch_ips[mgmt] = s_name

    # 2. Check softgate IPs
    if "csv/softgates.csv" in files:
        reader = csv.DictReader(io.StringIO(files["csv/softgates.csv"]))
        for row in reader:
            sg_name = row["name"]
            mainip = row["mainip"]
            mgmtip = row["mgmtip"]
            if mainip in switch_ips:
                errors.append(f"Duplicate IP {mainip} between softgate {sg_name} and switch/softgate {switch_ips[mainip]}")
            switch_ips[mainip] = sg_name
            if mgmtip in switch_ips:
                errors.append(f"Duplicate IP {mgmtip} between softgate {sg_name} and switch/softgate {switch_ips[mgmtip]}")
            switch_ips[mgmtip] = sg_name

    # 3. Check link port collisions and out-of-bounds ports
    # Port map: device -> set of used ports
    used_ports: Dict[str, Dict[str, str]] = {}

    def record_port(device: str, port: str, link_desc: str):
        if device not in used_ports:
            used_ports[device] = {}
        if port in used_ports[device]:
            errors.append(f"PORT COLLISION: {device} port {port} used in multiple links! First in: {used_ports[device][port]}, now in: {link_desc}")
        else:
            used_ports[device][port] = link_desc

        # Check port range if device is a switch
        if device in switch_portcounts:
            max_p = switch_portcounts[device]
            match = re.match(r"swp(\d+)", port)
            if match:
                p_num = int(match.group(1))
                if p_num < 1 or p_num > max_p:
                    errors.append(f"PORT OUT OF RANGE: {device} (capacity {max_p}) has link assigned to {port} ({p_num} > {max_p}) in {link_desc}")

    # Inspect all link CSVs
    link_csv_names = [
        "csv/links_ew_switch.csv",
        "csv/links_ew_gpu.csv",
        "csv/links_ns_switch.csv",
        "csv/links_ns_gpu.csv",
        "csv/links_softgate.csv",
        "csv/links_storage.csv",
        "csv/links_oob_switch.csv"
    ]

    for csv_file in link_csv_names:
        if csv_file not in files:
            continue
        content = files[csv_file].strip()
        if not content:
            continue
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            if "deviceA" in row and "deviceB" in row:
                dA, pA, dB, pB = row["deviceA"], row["deviceA_port"], row["deviceB"], row["deviceB_port"]
                link_desc = f"{pA}@{dA}--{pB}@{dB} in {csv_file}"
                record_port(dA, pA, link_desc)
                record_port(dB, pB, link_desc)
            elif "leaf" in row and "gpu" in row:
                leaf, l_port, gpu, g_port = row["leaf"], row["leaf_port"], row["gpu"], row["gpu_port"]
                link_desc = f"{l_port}@{leaf}--{g_port}@{gpu} in {csv_file}"
                record_port(leaf, l_port, link_desc)
                record_port(gpu, g_port, link_desc)
            elif "leaf" in row and "server" in row:
                leaf, l_port, srv, s_port = row["leaf"], row["leaf_port"], row["server"], row["server_port"]
                link_desc = f"{l_port}@{leaf}--{s_port}@{srv} in {csv_file}"
                record_port(leaf, l_port, link_desc)
                record_port(srv, s_port, link_desc)

    return errors


def run_tofu_test(case_name: str, target_dir: str) -> Tuple[bool, str]:
    """Runs tofu init, tofu validate, and tofu plan in target_dir."""
    # 1. Init
    init_cmd = [TOFU_BIN, "init", "-no-color", "-backend=false", "-get=false"]
    p_init = subprocess.run(init_cmd, cwd=target_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p_init.returncode != 0:
        return False, f"tofu init failed:\n{p_init.stderr}\n{p_init.stdout}"

    # 2. Validate
    val_cmd = [TOFU_BIN, "validate", "-no-color"]
    p_val = subprocess.run(val_cmd, cwd=target_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p_val.returncode != 0:
        return False, f"tofu validate failed:\n{p_val.stderr}\n{p_val.stdout}"

    # 3. Plan
    plan_cmd = [TOFU_BIN, "plan", "-no-color", "-refresh=false"]
    p_plan = subprocess.run(plan_cmd, cwd=target_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p_plan.returncode != 0:
        return False, f"tofu plan failed:\n{p_plan.stderr}\n{p_plan.stdout}"

    # Extract summary line from plan
    summary = "Success"
    for line in p_plan.stdout.splitlines():
        if "Plan:" in line:
            summary = line.strip()
            break

    return True, summary


def main():
    print("=" * 80)
    print("NETRIS TERRAFORM GENERATOR — EDGE CASE TEST SUITE")
    print(f"Total Test Cases: {len(TEST_CASES)}")
    print("=" * 80)

    test_base_dir = os.path.join(DEPLOYMENTS_DIR, "test_matrix")
    if os.path.exists(test_base_dir):
        shutil.rmtree(test_base_dir)
    os.makedirs(test_base_dir, exist_ok=True)

    results = []

    for case_name, cfg in TEST_CASES.items():
        print(f"\n--- Testing [{case_name}] ---")
        case_dir = os.path.join(test_base_dir, case_name)
        os.makedirs(case_dir, exist_ok=True)
        os.makedirs(os.path.join(case_dir, "csv"), exist_ok=True)

        # 1. Generate files
        try:
            gen = TerraformGenerator(cfg)
            files = gen.generate_all_files()
            for path, content in files.items():
                full_path = os.path.join(case_dir, path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)
        except Exception as e:
            print(f"  FAILED in Python generator: {e}")
            results.append((case_name, False, f"Generator error: {e}", []))
            continue

        # 2. Check Logical Invariants
        invariants_errors = check_logical_invariants(files, cfg)
        if invariants_errors:
            print(f"  FAILED logical invariants ({len(invariants_errors)} errors):")
            for err in invariants_errors[:5]:
                print(f"    - {err}")
            if len(invariants_errors) > 5:
                print(f"    ... and {len(invariants_errors) - 5} more.")

        # 3. Setup .terraform from cache to make init instant
        dot_tf = os.path.join(case_dir, ".terraform")
        lock_file = os.path.join(case_dir, ".terraform.lock.hcl")
        if os.path.exists(os.path.join(CACHE_DIR, ".terraform")):
            shutil.copytree(os.path.join(CACHE_DIR, ".terraform"), dot_tf)
        if os.path.exists(os.path.join(CACHE_DIR, ".terraform.lock.hcl")):
            shutil.copy(os.path.join(CACHE_DIR, ".terraform.lock.hcl"), lock_file)

        # 4. Run OpenTofu test
        tofu_ok, tofu_msg = run_tofu_test(case_name, case_dir)
        if tofu_ok:
            print(f"  OpenTofu: {tofu_msg}")
        else:
            print(f"  OpenTofu FAILED:\n    {tofu_msg}")

        overall_ok = (len(invariants_errors) == 0) and tofu_ok
        results.append((case_name, overall_ok, tofu_msg, invariants_errors))

    # Summary table
    print("\n" + "=" * 80)
    print("POSITIVE TEST SUITE SUMMARY RESULTS")
    print("=" * 80)
    passed_count = sum(1 for r in results if r[1])
    for case_name, ok, msg, errs in results:
        status = "PASS" if ok else "FAIL"
        err_info = f"({len(errs)} logical errors)" if errs else f"({msg})"
        print(f"[{status:4s}] {case_name:<38} {err_info}")

    print(f"\nPositive Cases Passed: {passed_count}/{len(TEST_CASES)}")

    # Negative Tests (verifying safe error handling for impossible designs)
    print("\n" + "=" * 80)
    print("NEGATIVE BOUNDARY TESTS (Oversubscription & Subnet Exhaustion)")
    print("=" * 80)
    
    # Negative Test 1: Port Oversubscription
    neg1_cfg = {
        "site_name": "NEG-OVERSUB",
        "planes_count": 1,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 1,
        "switch_port_count": 32,
        "gpu_count": 4,
        "gpu_roce_ports": 32,
        "gpu_ns_ports": 1,
        "ns_spines": 1,
        "ns_leaves": 1,
        "softgate_count": 1,
    }
    try:
        TerraformGenerator(neg1_cfg).generate_all_files()
        print("[FAIL] negative_port_oversubscription: Expected ValueError but generation succeeded.")
        neg1_ok = False
    except ValueError as ve:
        if "oversubscription" in str(ve).lower() or "exceed" in str(ve).lower() or "capacity" in str(ve).lower():
            print(f"[PASS] negative_port_oversubscription: Cleanly caught -> {ve}")
            neg1_ok = True
        else:
            print(f"[FAIL] negative_port_oversubscription: Unexpected error: {ve}")
            neg1_ok = False

    # Negative Test 2: Subnet Exhaustion
    neg2_cfg = {
        "site_name": "NEG-EXHAUST",
        "planes_count": 2,
        "ew_spines_per_plane": 2,
        "ew_leaves_per_plane": 4, # 12 switches
        "ew_loopback_subnet": "192.168.1.0/29", # only 6 usable host IPs!
        "switch_port_count": 64,
        "gpu_count": 2,
        "gpu_roce_ports": 8,
        "gpu_ns_ports": 1,
        "ns_spines": 1,
        "ns_leaves": 1,
        "softgate_count": 1,
    }
    try:
        TerraformGenerator(neg2_cfg).generate_all_files()
        print("[FAIL] negative_subnet_exhaustion: Expected ValueError but generation succeeded.")
        neg2_ok = False
    except ValueError as ve:
        if "usable host ips" in str(ve).lower():
            print(f"[PASS] negative_subnet_exhaustion: Cleanly caught -> {ve}")
            neg2_ok = True
        else:
            print(f"[FAIL] negative_subnet_exhaustion: Unexpected error: {ve}")
            neg2_ok = False

    total_tests = len(TEST_CASES) + 2
    total_passed = passed_count + (1 if neg1_ok else 0) + (1 if neg2_ok else 0)
    print(f"\nFinal Edge Case Test Score: {total_passed}/{total_tests} Passed.")
    if total_passed < total_tests:
        sys.exit(1)


if __name__ == "__main__":
    main()

