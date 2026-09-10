#!/usr/bin/env python3
"""Netris Telemetry Recorder.

Connects to a live Netris Controller, captures complete topological metadata
(Sites, Hardware, Links, VPCs, VNets, Server Clusters, BGP Peers, IPAM Subnets),
and records successive telemetry frames (Active Assurance checks, heartbeats,
and Graphite streaming interface octets) over an adjustable time window.

The resulting recording is saved into a JSON package for infinite offline replay.
"""

import argparse
import datetime
import json
import logging
import os
import sys
import time

from config import config
from netris_client import NetrisClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("netris_recorder")


def parse_args():
    parser = argparse.ArgumentParser(description="Record live Netris telemetry for offline simulation replay.")
    parser.add_argument(
        "-d", "--duration",
        type=int,
        default=300,
        help="Recording duration in seconds (default: 300)"
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=15,
        help="Interval between telemetry frames in seconds (default: 15)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="sim_data/telemetry_recording.json",
        help="Output JSON file path (default: sim_data/telemetry_recording.json)"
    )
    return parser.parse_args()


def record(duration: int, interval: int, output_path: str):
    logger.info("Connecting to Netris Controller at %s...", config.netris_url)
    client = NetrisClient()

    if not client.login():
        logger.error("Failed to authenticate to Netris Controller. Please check netris.var credentials.")
        sys.exit(1)

    # 1. Capture Static & Topological Metadata
    logger.info("Capturing complete topological metadata snapshot...")
    t_start_meta = time.time()
    metadata = {
        "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "controller_url": config.netris_url,
        "sites": client.get_sites(),
        "hardware": client.get_hardware(),
        "ports": client.get_ports(),
        "links": client.get_links(),
        "vpcs": client.get_vpcs(),
        "vnets": client.get_vnets(),
        "server_clusters": client.get_server_clusters(),
        "ebgp": client.get_ebgp(),
        "ipam_subnets": client.get_ipam_subnets(),
        "tenants": client.get_tenants(),
    }
    logger.info(
        "Metadata captured in %.2fs: %d devices, %d links, %d clusters, %d subnets.",
        time.time() - t_start_meta,
        len(metadata["hardware"]),
        len(metadata["links"]),
        len(metadata["server_clusters"]),
        len(metadata["ipam_subnets"]),
    )

    # 2. Capture Timed Telemetry Frames
    frames = []
    start_time = time.time()
    frame_idx = 0
    total_expected_frames = max(1, duration // interval)

    logger.info(
        "Starting telemetry recording: %d seconds total, %d seconds per frame (~%d frames)...",
        duration, interval, total_expected_frames
    )

    while True:
        elapsed = time.time() - start_time
        if elapsed >= duration and len(frames) > 0:
            break

        f_start = time.time()
        logger.info(
            "Capturing frame %d (elapsed: %.1fs / %ds)...",
            frame_idx + 1, elapsed, duration
        )

        try:
            hw_health = client.get_hardware_health()
            heartbeats = client.get_agent_heartbeats()
            alarms = client.get_hardware_alarms()
            graphite_octets = client.get_graphite_metrics("collectd.*.interface-*.if_octets.*")

            frame = {
                "frame_index": frame_idx,
                "timestamp": time.time(),
                "elapsed_seconds": round(elapsed, 2),
                "hardware_health": hw_health,
                "agent_heartbeats": heartbeats,
                "hardware_alarms": alarms,
                "graphite_octets": graphite_octets,
            }
            frames.append(frame)
            logger.info(
                "Frame %d captured in %.2fs: %d health items, %d heartbeats, %d graphite series.",
                frame_idx + 1,
                time.time() - f_start,
                len(hw_health),
                len(heartbeats),
                len(graphite_octets),
            )
            frame_idx += 1

        except Exception as e:
            logger.warning("Error capturing frame %d: %s", frame_idx + 1, e)

        # Check remaining time before sleep
        elapsed = time.time() - start_time
        if elapsed >= duration:
            break

        sleep_time = min(interval, max(1.0, duration - elapsed))
        time.sleep(sleep_time)

    total_time = time.time() - start_time
    logger.info("Recording complete! Captured %d frames in %.1f seconds.", len(frames), total_time)

    # 3. Compile & Serialize Recording
    recording_data = {
        "version": "1.0",
        "type": "netris_telemetry_recording",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "duration_seconds": round(total_time, 2),
        "frame_count": len(frames),
        "frame_interval_seconds": interval,
        "metadata": metadata,
        "frames": frames,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    logger.info("Writing recording to %s...", output_path)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(recording_data, f, indent=2)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    logger.info("Successfully saved recording (%d frames, %.2f MB) to %s.", len(frames), file_size_mb, output_path)
    print("\n" + "=" * 72)
    print("           NETRIS TELEMETRY RECORDING SAVED SUCCESSFULLY           ")
    print("=" * 72)
    print(f"  📁 Output File:     {os.path.abspath(output_path)}")
    print(f"  ⏱  Duration:        {total_time:.1f}s ({len(frames)} frames captured)")
    print(f"  📦 File Size:       {file_size_mb:.2f} MB")
    print(f"  🏢 Managed Nodes:   {len(metadata['hardware'])} devices")
    print(f"  🔌 Mapped Links:    {len(metadata['links'])} ports")
    print(f"  📈 Octet Series:    {len(frames[0].get('graphite_octets', [])) if frames else 0} series per frame")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    args = parse_args()
    record(args.duration, args.interval, args.output)
