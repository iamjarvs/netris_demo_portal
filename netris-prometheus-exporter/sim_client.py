"""Simulated Netris Client for Offline Replay.

Provides a drop-in replacement for NetrisClient that operates 100% offline
using a recorded telemetry file (sim_data/telemetry_recording.json).
Replays recorded telemetry frames in an infinite ring buffer with realistic
micro-jitter, advancing per Prometheus scrape without requiring network reachability
or credentials for the Netris Controller.
"""

from __future__ import annotations

import copy
import gzip
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
            if os.path.exists(target_path + ".gz"):
                target_path = target_path + ".gz"
            elif target_path.endswith(".gz") and os.path.exists(target_path[:-3]):
                target_path = target_path[:-3]
            else:
                raise FileNotFoundError(
                    f"Simulation data file '{self.data_file}' does not exist! "
                    f"Please run './record.sh' to capture live telemetry, or ensure the file is present."
                )

        logger.info("Loading offline simulation recording from '%s'...", target_path)
        open_fn = gzip.open if target_path.endswith(".gz") else open
        with open_fn(target_path, "rt", encoding="utf-8") as f:
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

    # --- Dynamic Telemetry Endpoints (Returns looping frames) ---

    def get_hardware_health(self) -> list[dict]:
        frame = self._get_current_frame()
        raw_health = frame.get("hardware_health") or []

        # Add subtle organic jitter to load average and memory so graphs show natural variance
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
        """Replay recorded Graphite octet time-series with fresh timestamps & organic jitter."""
        frame = self._get_current_frame()
        raw_series = frame.get("graphite_octets") or []

        now_ts = int(time.time())
        simulated_series = []

        # Add subtle organic jitter (±1.5%) so live graphs show natural network variance
        for item in raw_series:
            series_copy = copy.deepcopy(item)
            pts = series_copy.get("datapoints") or []
            new_pts = []
            for val, _ in pts:
                if val is not None:
                    jitter = 1.0 + random.uniform(-0.02, 0.02)
                    new_val = max(0.0, round(float(val) * jitter, 3))
                    new_pts.append([new_val, now_ts])
                else:
                    new_pts.append([None, now_ts])
            series_copy["datapoints"] = new_pts
            simulated_series.append(series_copy)

        # Increment scrape cycle and advance frame when done
        self.advance_frame()
        return simulated_series
