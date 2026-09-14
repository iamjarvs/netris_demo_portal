"""Simulated Netris Client for Offline Replay.

Provides a drop-in replacement for NetrisClient that operates 100% offline
using a recorded telemetry file (sim_data/telemetry_recording.json).
Replays recorded telemetry frames in an infinite ring buffer with realistic
micro-jitter, advancing per Prometheus scrape without requiring network reachability
or credentials for the Netris Controller.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import random
import re
import threading
import time
from typing import Any

logger = logging.getLogger("sim_client")


class SimulatedNetrisClient:
    def __init__(self, data_file: str = "sim_data/telemetry_recording.json"):
        self.data_file = data_file
        self.base_url = "sim://offline-recorder"
        self.username = "simulated"
        self._authenticated = True
        self._lock = threading.Lock()

        self.metadata: dict[str, Any] = {}
        self.frames: list[dict[str, Any]] = []
        self.current_frame_idx = 0
        self._scrape_counter = 0

        self._load_recording()

    def _load_recording(self) -> None:
        target_path = self.data_file
        if not os.path.exists(target_path):
            gz_candidate = target_path + ".gz" if not target_path.endswith(".gz") else target_path
            if os.path.exists(gz_candidate):
                target_path = gz_candidate
            else:
                raise FileNotFoundError(
                    f"Simulation data file '{self.data_file}' does not exist! "
                    f"Please run './record.sh' to capture live telemetry, or ensure the file is present."
                )

        logger.info("Loading offline simulation recording from '%s'...", target_path)
        if target_path.endswith(".gz"):
            import gzip
            with gzip.open(target_path, "rt", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        self.metadata = data.get("metadata") or {}
        self.frames = data.get("frames") or []

        if not self.frames:
            raise ValueError(f"Recording file '{self.data_file}' contains 0 telemetry frames!")

        logger.info(
            "SimulatedNetrisClient initialized successfully: %d devices, %d links, %d frames (loop interval: %ds).",
            len(self.metadata.get("hardware", [])),
            len(self.metadata.get("links", [])),
            len(self.frames),
            data.get("duration_seconds", 0),
        )

    def login(self) -> bool:
        """Simulated authentication always succeeds."""
        logger.info("SimulatedNetrisClient: offline authentication active.")
        return True

    def advance_frame(self) -> None:
        """Advance to the next recorded frame in the circular buffer."""
        with self._lock:
            self.current_frame_idx = (self.current_frame_idx + 1) % len(self.frames)
            logger.debug("SimulatedNetrisClient: advanced to frame %d/%d", self.current_frame_idx + 1, len(self.frames))

    def _get_current_frame(self) -> dict[str, Any]:
        with self._lock:
            return self.frames[self.current_frame_idx]

    # --- Metadata Endpoints (Returns recorded static snapshot) ---

    def get_sites(self) -> list[dict]:
        return self.metadata.get("sites") or []

    def get_hardware(self) -> list[dict]:
        return self.metadata.get("hardware") or []

    def get_ports(self) -> list[dict]:
        return self.metadata.get("ports") or []

    def get_links(self) -> list[dict]:
        return self.metadata.get("links") or []

    def get_vpcs(self) -> list[dict]:
        return self.metadata.get("vpcs") or []

    def get_vnets(self) -> list[dict]:
        return self.metadata.get("vnets") or []

    def get_server_clusters(self) -> list[dict]:
        return self.metadata.get("server_clusters") or []

    def get_ebgp(self) -> list[dict]:
        return self.metadata.get("ebgp") or []

    def get_ipam_subnets(self) -> list[dict]:
        return self.metadata.get("ipam_subnets") or []

    def get_tenants(self) -> list[dict]:
        return self.metadata.get("tenants") or []

    def get_vpn_mesh(self) -> list[dict]:
        """Return simulated Site Mesh VPN links with SLA metrics."""
        frame = self._get_current_frame()
        if "vpn_mesh" in frame:
            return frame["vpn_mesh"]
        if "vpn" in self.metadata:
            return self.metadata["vpn"]
        sites = self.get_sites()
        site_a = sites[0].get("name", "Datacenter-A") if sites else "Datacenter-A"
        site_b = sites[1].get("name", "Cloud-Region-1") if len(sites) > 1 else "Cloud-Region-1"
        return [
            {
                "id": 1,
                "name": "mesh-sg0-to-sg1",
                "local_endpoint": "ns-softgate-0",
                "remote_endpoint": "ns-softgate-1",
                "local_site": site_a,
                "remote_site": site_b,
                "status": "ok",
                "bgp_state": "Established",
                "bgp_uptime": "12d 06h",
                "loss": 0.0,
                "rtt": round(1.24 + random.uniform(-0.05, 0.08), 3),
                "score": round(0.985 + random.uniform(-0.005, 0.005), 4),
            },
            {
                "id": 2,
                "name": "mesh-sg2-to-sg3",
                "local_endpoint": "ns-softgate-2",
                "remote_endpoint": "ns-softgate-3",
                "local_site": site_a,
                "remote_site": site_b,
                "status": "ok",
                "bgp_state": "Established",
                "bgp_uptime": "12d 06h",
                "loss": 0.0,
                "rtt": round(1.48 + random.uniform(-0.06, 0.09), 3),
                "score": round(0.978 + random.uniform(-0.004, 0.006), 4),
            },
        ]

    def get_l4lb_stats(self) -> list[dict]:
        """Return simulated L4 Load Balancer instances and VIP health states."""
        return [
            {
                "id": 1,
                "name": "k8s-ingress-vip",
                "ip": "10.254.0.10",
                "site_name": "Datacenter-A",
                "status": "ok",
                "response": "HTTP 200 OK (5 healthy backends)",
            },
            {
                "id": 2,
                "name": "ai-api-gateway-vip",
                "ip": "10.254.0.20",
                "site_name": "Datacenter-A",
                "status": "ok",
                "response": "HTTP 200 OK (8 healthy backends)",
            },
        ]

    # --- Dynamic Telemetry Endpoints (Returns looping frames) ---

    def get_hardware_health(self) -> list[dict]:
        frame = self._get_current_frame()
        raw_health = frame.get("hardware_health") or []

        # Add subtle organic jitter to load average, memory, and sensors
        cloned_health = copy.deepcopy(raw_health)
        for dev in cloned_health:
            for chk in dev.get("checks", []):
                cname = chk.get("check_name")
                msg = chk.get("message") or ""
                if cname == "check_load":
                    load_match = re.search(r"Load average\s+([\d\.]+),\s*([\d\.]+),\s*([\d\.]+)", msg)
                    if load_match:
                        l1 = max(0.05, round(float(load_match.group(1)) * (1.0 + random.uniform(-0.08, 0.08)), 2))
                        l5 = max(0.05, round(float(load_match.group(2)) * (1.0 + random.uniform(-0.04, 0.04)), 2))
                        l15 = max(0.05, round(float(load_match.group(3)) * (1.0 + random.uniform(-0.02, 0.02)), 2))
                        chk["message"] = f"Load average {l1}, {l5}, {l15}"
                elif cname == "check_memory":
                    mem_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*Used", msg)
                    if mem_match:
                        m_val = min(98.0, max(10.0, round(float(mem_match.group(1)) + random.uniform(-1.2, 1.2), 1)))
                        chk["message"] = f"{m_val} % Used"
        return cloned_health

    def get_agent_heartbeats(self) -> list[dict]:
        frame = self._get_current_frame()
        return frame.get("agent_heartbeats") or []

    def get_hardware_alarms(self) -> list[dict]:
        frame = self._get_current_frame()
        return frame.get("hardware_alarms") or []

    def get_graphite_metrics(
        self,
        targets: list[str] | str,
        time_from: str = "-3min",
        time_until: str = "now"
    ) -> list[dict]:
        """Replay recorded Graphite time-series with fresh timestamps & organic jitter,
        and dynamically synthesize companion metrics (PPS, errors, optics, compute) from recorded data.
        """
        if isinstance(targets, str):
            targets = [targets]

        frame = self._get_current_frame()
        raw_series = frame.get("graphite_octets") or []
        now_ts = int(time.time())
        simulated_series = []

        # 1. Base octet series (throughput)
        target_str = " ".join(targets)
        wants_octets = "if_octets" in target_str or not targets
        wants_packets = "if_packets" in target_str
        wants_errors = "if_errors" in target_str
        wants_optics = "if_optic" in target_str
        wants_compute = any(k in target_str for k in ("cpu-", "memory", "conntrack", "if_maccount"))

        devices_seen = set()

        for item in raw_series:
            t_name = item.get("target", "")
            pts = item.get("datapoints") or []
            val = 0.0
            for p in reversed(pts):
                if p[0] is not None:
                    val = float(p[0])
                    break

            jitter = 1.0 + random.uniform(-0.02, 0.02)
            cur_val = max(0.0, round(val * jitter, 3))

            # Match device and port
            m = re.match(r"^collectd\.([^.]+)\.interface-([^.]+)\.if_octets\.(rx|tx)$", t_name)
            if m:
                dev, port, direction = m.groups()
                devices_seen.add(dev)

                if wants_octets:
                    simulated_series.append({
                        "target": t_name,
                        "datapoints": [[cur_val, now_ts]]
                    })

                if wants_packets:
                    # Realistic average packet size ~ 1000 bytes
                    pps = max(0.0, round(cur_val / 1024.0, 2)) if cur_val > 0 else 0.0
                    simulated_series.append({
                        "target": f"collectd.{dev}.interface-{port}.if_packets.{direction}",
                        "datapoints": [[pps, now_ts]]
                    })

                if wants_errors:
                    err_val = 0.0
                    simulated_series.append({
                        "target": f"collectd.{dev}.interface-{port}.if_errors.{direction}",
                        "datapoints": [[err_val, now_ts]]
                    })

                if wants_optics and direction == "rx" and port.startswith("swp"):
                    # Synthesize lane optical levels (-3.5 to -5.5 dBm)
                    for lane in range(4):
                        optic_dbm = round(-4.2 + random.uniform(-0.8, 0.8), 2)
                        simulated_series.append({
                            "target": f"collectd.{dev}.interface-{port}.if_optic.rx{lane}",
                            "datapoints": [[optic_dbm, now_ts]]
                        })

                if wants_compute and direction == "rx":
                    mac_count = random.randint(12, 140) if cur_val > 0 else 2
                    simulated_series.append({
                        "target": f"collectd.{dev}.interface-{port}.if_maccount.count",
                        "datapoints": [[mac_count, now_ts]]
                    })

        # 2. Synthesize system compute metrics for managed devices
        if wants_compute:
            target_devs = set([d for d in devices_seen if "softgate" in d.lower()] + list(devices_seen)[:20])
            for dev in target_devs:
                # CPU per core
                for core in range(4):
                    user_pct = round(random.uniform(4.0, 12.0), 1)
                    sys_pct = round(random.uniform(2.0, 6.0), 1)
                    wait_pct = round(random.uniform(0.1, 0.8), 1)
                    idle_pct = round(100.0 - (user_pct + sys_pct + wait_pct), 1)
                    simulated_series.append({
                        "target": f"collectd.{dev}.cpu-{core}.cpu-user",
                        "datapoints": [[user_pct, now_ts]]
                    })
                    simulated_series.append({
                        "target": f"collectd.{dev}.cpu-{core}.cpu-system",
                        "datapoints": [[sys_pct, now_ts]]
                    })
                    simulated_series.append({
                        "target": f"collectd.{dev}.cpu-{core}.cpu-idle",
                        "datapoints": [[idle_pct, now_ts]]
                    })
                    simulated_series.append({
                        "target": f"collectd.{dev}.cpu-{core}.cpu-wait",
                        "datapoints": [[wait_pct, now_ts]]
                    })

                # Memory
                mem_total = 16.0 * 1024 * 1024 * 1024  # 16 GB
                mem_used = mem_total * random.uniform(0.38, 0.52)
                mem_free = mem_total - mem_used
                simulated_series.append({
                    "target": f"collectd.{dev}.memory.memory-used",
                    "datapoints": [[mem_used, now_ts]]
                })
                simulated_series.append({
                    "target": f"collectd.{dev}.memory.memory-free",
                    "datapoints": [[mem_free, now_ts]]
                })

                # Conntrack (for SoftGates)
                if "softgate" in dev.lower():
                    conns = random.randint(12500, 28000)
                    simulated_series.append({
                        "target": f"collectd.{dev}.conntrack.conntrack",
                        "datapoints": [[conns, now_ts]]
                    })
                    simulated_series.append({
                        "target": f"collectd.{dev}.conntrack.conntrack-max",
                        "datapoints": [[500000, now_ts]]
                    })
                    simulated_series.append({
                        "target": f"collectd.{dev}.conntrack.percent-used",
                        "datapoints": [[round((conns / 500000.0) * 100.0, 2), now_ts]]
                    })

        # Increment scrape cycle and advance frame when done
        self.advance_frame()
        return simulated_series

