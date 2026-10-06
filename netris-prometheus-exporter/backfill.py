#!/usr/bin/env python3
"""Netris Prometheus TSDB Historical Backfill Engine.

Pre-populates the Prometheus TSDB with historical telemetry (default: 90 minutes)
synthesized from recorded simulation data (sim_data/telemetry_recording.json).

Instead of waiting 90 minutes for streaming scrapes to populate graphs, this tool
generates OpenMetrics time-series blocks using promtool directly into the Prometheus
storage directory. When the stack is launched, Grafana immediately displays complete,
rich historical graphs ready for executive customer demonstrations.
"""

from __future__ import annotations

import argparse
import datetime
import logging
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict

from config import config
from enricher import NetrisEnricher
from exporter import NetrisCollector
from sim_client import SimulatedNetrisClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("netris_backfill")


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill Prometheus TSDB with historical Netris simulation telemetry.")
    parser.add_argument(
        "-m", "--minutes",
        type=int,
        default=90,
        help="Historical duration in minutes to backfill (default: 90)"
    )
    parser.add_argument(
        "-s", "--step",
        type=int,
        default=60,
        help="Step interval between historical samples in seconds (default: 60)"
    )
    parser.add_argument(
        "-d", "--sim-data",
        type=str,
        default="sim_data/telemetry_recording.json",
        help="Path to telemetry recording file (default: sim_data/telemetry_recording.json)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default="prometheus/data",
        help="Path to Prometheus TSDB data directory (default: prometheus/data)"
    )
    return parser.parse_args()


def backfill(minutes: int = 90, step: int = 60, sim_data_path: str = "sim_data/telemetry_recording.json", output_dir: str = "prometheus/data"):
    if not os.path.exists(sim_data_path):
        if os.path.exists(sim_data_path + ".gz"):
            sim_data_path = sim_data_path + ".gz"
        else:
            logger.error("Simulation data file '%s' not found! Please run './record.sh' first.", sim_data_path)
            sys.exit(1)

    # Parse prometheus.yml to discover target labels (job, instance, etc.)
    target_labels: dict[str, str] = {
        "job": "netris",
        "instance": f"netris-exporter:{config.exporter_port}",
        "environment": "production",
        "controller": "adam-ctl.netris.io",
    }
    prom_cfg_path = os.path.join(os.path.dirname(output_dir) if output_dir != "prometheus/data" else "prometheus", "prometheus.yml")
    if os.path.exists(prom_cfg_path):
        try:
            import yaml
            with open(prom_cfg_path, "r", encoding="utf-8") as pf:
                pcfg = yaml.safe_load(pf)
            for sc in pcfg.get("scrape_configs", []):
                if sc.get("job_name") == "netris":
                    target_labels["job"] = sc.get("job_name", "netris")
                    for stc in sc.get("static_configs", []):
                        if stc.get("targets"):
                            target_labels["instance"] = stc["targets"][0]
                        for lk, lv in stc.get("labels", {}).items():
                            target_labels[lk] = str(lv)
                    break
            logger.info("Discovered Prometheus target labels for backfill: %s", target_labels)
        except Exception as e:
            logger.warning("Could not parse %s via PyYAML: %s. Using configured defaults.", prom_cfg_path, e)

    t_start_total = time.time()
    # End backfill 60 seconds before current time so initial live scrape continues seamlessly without overlap
    now = int(time.time()) - 60
    num_steps = (minutes * 60) // step
    t0 = now - (num_steps * step)

    t0_dt = datetime.datetime.fromtimestamp(t0, tz=datetime.timezone.utc).strftime('%H:%M:%S UTC')
    now_dt = datetime.datetime.fromtimestamp(now, tz=datetime.timezone.utc).strftime('%H:%M:%S UTC')

    print("\n" + "=" * 76)
    print("      NETRIS PROMETHEUS TSDB HISTORICAL PRE-POPULATION (BACKFILL)      ")
    print("=" * 76)
    print(f"  ⏱  Backfill Window:    {minutes} minutes ({t0_dt} → {now_dt})")
    print(f"  🔄 Resolution Step:    {step} seconds ({num_steps} sample points per series)")
    print(f"  📁 Source Snapshot:    {sim_data_path}")
    print(f"  💾 TSDB Destination:   {output_dir}")
    print("=" * 76 + "\n")

    # 1. Initialize Simulator & Collector
    logger.info("Initializing simulated Netris client and topology enricher...")
    client = SimulatedNetrisClient(data_file=sim_data_path)
    client.login()
    enricher = NetrisEnricher(client)
    enricher.refresh()
    collector = NetrisCollector(client, enricher)

    # Bypass redundant metadata refreshes inside backfill loop for maximum speed
    enricher.refresh = lambda *a, **kw: None

    # 2. Synthesize Historical OpenMetrics Dataset
    logger.info("Generating %d historical frames of enriched telemetry...", num_steps)
    families_help: dict[str, str] = {}
    families_type: dict[str, str] = {}
    # family_name -> { sorted_labels_str: [(timestamp, value), ...] }
    series_data: dict[str, dict[str, list[tuple[int, float]]]] = defaultdict(lambda: defaultdict(list))

    t_gen_start = time.time()
    for i in range(num_steps):
        t = t0 + (i * step)
        for family in collector.collect():
            fname = family.name
            if fname not in families_help:
                families_help[fname] = family.documentation or fname
                families_type[fname] = family.type or "gauge"

            for sample in family.samples:
                # sample: (name, labels_dict, value, timestamp, exemplar)
                labels = dict(sample[1])
                # Merge target labels so TSDB series fingerprint matches live scrapes exactly
                labels.update(target_labels)
                val = sample[2]
                lbl_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                series_data[fname][lbl_str].append((t, val))

    t_gen_duration = time.time() - t_gen_start
    total_series = sum(len(smap) for smap in series_data.values())
    total_samples = sum(len(pts) for smap in series_data.values() for pts in smap.values())
    logger.info(
        "Synthesized %d series (%d samples) in %.2fs.",
        total_series, total_samples, t_gen_duration
    )

    # 3. Write Grouped OpenMetrics File
    temp_prom_path = os.path.join(os.path.dirname(sim_data_path) or ".", ".backfill_temp.prom")
    logger.info("Serializing OpenMetrics stream to temporary file '%s'...", temp_prom_path)
    t_write_start = time.time()

    with open(temp_prom_path, "w", encoding="utf-8") as f:
        for fname, series_map in series_data.items():
            doc = families_help.get(fname) or fname
            ftype = families_type.get(fname) or "gauge"
            f.write(f"# HELP {fname} {doc}\n")
            f.write(f"# TYPE {fname} {ftype}\n")
            for lbl_str, points in series_map.items():
                prefix = f"{fname}{{{lbl_str}}}" if lbl_str else fname
                for t, val in points:
                    f.write(f"{prefix} {val} {t}.000\n")
        f.write("# EOF\n")

    logger.info("OpenMetrics file written in %.2fs (%.1f MB).", time.time() - t_write_start, os.path.getsize(temp_prom_path) / (1024 * 1024))

    # 4. Clean TSDB Destination Directory
    os.makedirs(output_dir, exist_ok=True)
    logger.info("Preparing TSDB directory '%s' (clearing stale blocks)...", output_dir)
    for entry in os.listdir(output_dir):
        full_p = os.path.join(output_dir, entry)
        try:
            if os.path.isdir(full_p):
                shutil.rmtree(full_p)
            else:
                os.remove(full_p)
        except Exception as e:
            logger.warning("Could not remove stale item '%s': %s", full_p, e)

    # 5. Build TSDB Blocks using promtool via Docker
    logger.info("Compiling OpenMetrics samples into Prometheus TSDB blocks using promtool...")
    abs_root = os.path.abspath(".")
    rel_prom = os.path.relpath(temp_prom_path, abs_root)
    rel_out = os.path.relpath(output_dir, abs_root)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{abs_root}:/work",
        "-w", "/work",
        "--entrypoint", "/bin/promtool",
        "prom/prometheus:v2.50.1",
        "tsdb", "create-blocks-from", "openmetrics",
        rel_prom, f"/work/{rel_out}"
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if res.stdout:
            print(res.stdout)
    except subprocess.CalledProcessError as e:
        logger.error("promtool failed to generate TSDB blocks: %s\n%s", e, e.stderr)
        sys.exit(1)
    finally:
        if os.path.exists(temp_prom_path):
            os.remove(temp_prom_path)

    # Ensure permissions for container user nobody
    try:
        subprocess.run(["chmod", "-R", "777", output_dir], check=False)
    except Exception:
        pass

    total_duration = time.time() - t_start_total
    logger.info("TSDB backfill completed successfully in %.2fs!", total_duration)

    print("\n" + "=" * 76)
    print("      PROMETHEUS PRE-POPULATION COMPLETE: DEMO-READY STATE REACHED      ")
    print("=" * 76)
    print(f"  ✅ Status:             READY (Complete 90-minute historical telemetry)")
    print(f"  📊 Total Series:       {total_series:,}")
    print(f"  📈 Samples Ingested:   {total_samples:,}")
    print(f"  ⚡ Generation Time:    {total_duration:.2f} seconds")
    print(f"  🏢 Managed Switches:   {len(client.get_hardware())} devices populated")
    print(f"  🔌 Ports & Cabling:    {len(client.get_links())} links active")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    args = parse_args()
    backfill(args.minutes, args.step, args.sim_data, args.output_dir)
