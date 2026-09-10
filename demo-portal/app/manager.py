from __future__ import annotations

import collections
import logging
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

import httpx

from app.models import ToolInfo

logger = logging.getLogger("tool_manager")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# In-memory store for active subprocesses and logs
_PROCESS_REGISTRY: Dict[str, subprocess.Popen] = {}
_LOG_BUFFERS: Dict[str, collections.deque] = collections.defaultdict(lambda: collections.deque(maxlen=1000))
_START_TIMES: Dict[str, float] = {}

# Tool Definitions
TOOLS_METADATA: Dict[str, Dict[str, Any]] = {
    "netris-slurm-cluster-sim": {
        "id": "netris-slurm-cluster-sim",
        "name": "Slurm Dynamic Cluster Orchestrator",
        "category": "Workload Orchestration",
        "description": "Simulates Slurm HPC job scheduling, dynamically provisioning and dismantling Netris Server Clusters & RoCEv2 V-Nets.",
        "tool_type": "subprocess",
        "port": 8088,
        "popout_url": "http://localhost:8088",
        "health_endpoint": "http://localhost:8088/api/cluster",
        "default_args": ["python3", "run_simulation.py", "--sim-mode", "--port", "8088"],
        "cwd": REPO_ROOT / "netris-slurm-cluster-sim",
        "summary_command": "python3 run_simulation.py --sim-mode --port 8088",
    },
    "provider-portal": {
        "id": "provider-portal",
        "name": "HeliosGrid Provider Portal",
        "category": "Cloud Control Plane",
        "description": "Full-stack multi-tenant AI Cloud self-service portal (FastAPI + React 18) for ordering GPU clusters and managing Netris VPCs.",
        "tool_type": "subprocess",
        "port": 8000,
        "popout_url": "http://localhost:8000",
        "health_endpoint": "http://localhost:8000/ops/api/settings",
        "default_args": ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        "cwd": REPO_ROOT / "provider-portal",
        "summary_command": "uvicorn app.main:app --port 8000",
    },
    "chatsim": {
        "id": "chatsim",
        "name": "Meridian ChatSim Console",
        "category": "Tenant Workload",
        "description": "In-cluster AI chat assistant prop running on compute nodes, reflecting real tenant branding, Netris VPC, and active GPU rails.",
        "tool_type": "subprocess",
        "port": 8765,
        "popout_url": "http://localhost:8765",
        "health_endpoint": "http://localhost:8765/api/context",
        "default_args": ["python3", "server.py"],
        "cwd": REPO_ROOT / "chatsim",
        "summary_command": "python3 server.py",
    },
    "netris-prometheus-exporter": {
        "id": "netris-prometheus-exporter",
        "name": "Prometheus & Grafana Observability",
        "category": "Telemetry & Monitoring",
        "description": "Prometheus exporter with semantic port/VPC enrichment, 90-min instant historical TSDB backfill, and pre-built Grafana dashboards.",
        "tool_type": "docker",
        "port": 3000,
        "popout_url": "http://localhost:3000",
        "health_endpoint": "http://localhost:3000/api/health",
        "start_script": ["./start.sh", "--sim"],
        "stop_script": ["./stop.sh"],
        "cwd": REPO_ROOT / "netris-prometheus-exporter",
        "summary_command": "./start.sh --sim",
    },
    "netbox-netris": {
        "id": "netbox-netris",
        "name": "NetBox ↔ Netris IPAM Sync",
        "category": "IPAM & DCIM",
        "description": "Bi-directional synchronization between NetBox (planning source of truth) and Netris Controller, mirroring live assignments.",
        "tool_type": "docker",
        "port": 8000,
        "popout_url": "http://localhost:8000",
        "health_endpoint": "http://localhost:8090/health",
        "start_script": ["docker", "compose", "up", "-d"],
        "stop_script": ["docker", "compose", "down"],
        "cwd": REPO_ROOT / "netbox-netris",
        "summary_command": "./start-netbox-integration.sh",
    },
    "gpu-ai-fabric-traffic-sim": {
        "id": "gpu-ai-fabric-traffic-sim",
        "name": "GPU AI Fabric Traffic Simulator",
        "category": "Traffic Simulation",
        "description": "Containerized multi-rail RoCEv2 iPerf3 collective traffic generator (Ring-AllReduce, MoE All-to-All, Incast) across mock GPU nodes.",
        "tool_type": "docker",
        "port": None,
        "popout_url": None,
        "health_endpoint": None,
        "start_script": ["docker", "compose", "up", "-d"],
        "stop_script": ["docker", "compose", "down"],
        "cwd": REPO_ROOT / "gpu-ai-fabric-traffic-sim",
        "summary_command": "docker compose up -d",
    },
    "netris-controller-gpu-traffic-sim": {
        "id": "netris-controller-gpu-traffic-sim",
        "name": "Controller GPU Fabric Runner",
        "category": "Hardware Traffic Sim",
        "description": "Netris Controller automation discovering VPC GPU hosts, deploying offline iPerf3 binaries, and running bare-metal traffic.",
        "tool_type": "remote",
        "port": None,
        "popout_url": None,
        "health_endpoint": None,
        "start_script": ["./deploy.sh"],
        "stop_script": [],
        "cwd": REPO_ROOT / "netris-controller-gpu-traffic-sim",
        "summary_command": "./deploy.sh",
    }
}


def is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Test whether a TCP port is currently open and listening."""
    if not port:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def _append_log(tool_id: str, line: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    _LOG_BUFFERS[tool_id].append(f"[{timestamp}] {line.rstrip()}")


def _stream_output(tool_id: str, proc: subprocess.Popen) -> None:
    """Thread function to stream stdout/stderr of a subprocess into memory."""
    for line in iter(proc.stdout.readline, b""):
        if not line:
            break
        try:
            decoded = line.decode("utf-8", errors="replace")
            _append_log(tool_id, decoded)
        except Exception:
            pass
    proc.stdout.close()


def get_all_tools() -> List[ToolInfo]:
    """Return status and metadata for all registered tools."""
    results = []
    for tool_id, meta in TOOLS_METADATA.items():
        is_running = False
        pid = None
        uptime = None

        if meta["tool_type"] == "subprocess":
            proc = _PROCESS_REGISTRY.get(tool_id)
            if proc and proc.poll() is None:
                is_running = True
                pid = proc.pid
                start_t = _START_TIMES.get(tool_id)
                if start_t:
                    secs = int(time.time() - start_t)
                    uptime = f"{secs // 60}m {secs % 60}s"
            elif meta.get("port") and is_port_open(meta["port"]):
                # Port is active even if not spawned by this manager session
                is_running = True
        elif meta["tool_type"] == "docker":
            # Check docker compose ps
            cwd = meta.get("cwd")
            if cwd and (cwd / "docker-compose.yml").exists():
                try:
                    res = subprocess.run(
                        ["docker", "compose", "ps", "-q"],
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        timeout=2.0
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        is_running = True
                except Exception:
                    pass

            if not is_running and meta.get("port") and is_port_open(meta["port"]):
                is_running = True

        status = "running" if is_running else "stopped"

        results.append(ToolInfo(
            id=meta["id"],
            name=meta["name"],
            category=meta["category"],
            description=meta["description"],
            tool_type=meta["tool_type"],
            port=meta.get("port"),
            popout_url=meta.get("popout_url"),
            health_endpoint=meta.get("health_endpoint"),
            status=status,
            is_running=is_running,
            pid=pid,
            uptime=uptime,
            summary_command=meta["summary_command"],
        ))
    return results


def start_tool(tool_id: str, custom_args: Optional[List[str]] = None) -> tuple[bool, str]:
    """Start a tool via subprocess or Docker Compose."""
    meta = TOOLS_METADATA.get(tool_id)
    if not meta:
        return False, f"Tool '{tool_id}' not found."

    cwd = meta["cwd"]
    if not cwd.exists():
        return False, f"Directory '{cwd}' does not exist."

    _append_log(tool_id, f"Initiating start sequence for {meta['name']}...")

    if meta["tool_type"] == "subprocess":
        # Check if already running
        existing = _PROCESS_REGISTRY.get(tool_id)
        if existing and existing.poll() is None:
            return True, f"Tool '{tool_id}' is already running (PID {existing.pid})."

        cmd = custom_args or meta["default_args"]
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
            )
            _PROCESS_REGISTRY[tool_id] = proc
            _START_TIMES[tool_id] = time.time()

            t = threading.Thread(target=_stream_output, args=(tool_id, proc), daemon=True)
            t.start()

            _append_log(tool_id, f"Started subprocess with PID {proc.pid}: {' '.join(cmd)}")
            return True, f"Started {meta['name']} successfully (PID {proc.pid})."
        except Exception as e:
            _append_log(tool_id, f"Failed to launch subprocess: {e}")
            return False, f"Failed to launch: {e}"

    elif meta["tool_type"] == "docker":
        cmd = custom_args or meta.get("start_script", ["docker", "compose", "up", "-d"])
        try:
            res = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60.0
            )
            for line in res.stdout.splitlines():
                _append_log(tool_id, line)
            if res.stderr:
                for line in res.stderr.splitlines():
                    _append_log(tool_id, line)

            if res.returncode == 0:
                _append_log(tool_id, "Docker start command exited successfully.")
                return True, f"Started {meta['name']} via Docker Compose."
            else:
                return False, f"Docker exited with code {res.returncode}: {res.stderr}"
        except Exception as e:
            _append_log(tool_id, f"Docker error: {e}")
            return False, f"Docker error: {e}"

    elif meta["tool_type"] == "remote":
        cmd = custom_args or meta.get("start_script")
        try:
            res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=10.0)
            _append_log(tool_id, res.stdout or "Command completed.")
            return True, "Triggered controller script."
        except Exception as e:
            return False, str(e)

    return False, "Unknown tool type."


def stop_tool(tool_id: str) -> tuple[bool, str]:
    """Stop a running tool."""
    meta = TOOLS_METADATA.get(tool_id)
    if not meta:
        return False, f"Tool '{tool_id}' not found."

    cwd = meta["cwd"]
    _append_log(tool_id, f"Stopping {meta['name']}...")

    if meta["tool_type"] == "subprocess":
        proc = _PROCESS_REGISTRY.get(tool_id)
        if proc:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                _append_log(tool_id, "Process terminated.")
            except Exception as e:
                _append_log(tool_id, f"Error terminating process: {e}")
            del _PROCESS_REGISTRY[tool_id]
            if tool_id in _START_TIMES:
                del _START_TIMES[tool_id]

        # In case there are leftover processes on that specific port, kill if necessary
        port = meta.get("port")
        if port and is_port_open(port):
            try:
                subprocess.run(f"lsof -ti tcp:{port} | xargs kill -9", shell=True, timeout=3.0)
                _append_log(tool_id, f"Cleared orphaned process on port {port}.")
            except Exception:
                pass

        return True, f"Stopped {meta['name']}."

    elif meta["tool_type"] == "docker":
        cmd = meta.get("stop_script", ["docker", "compose", "down"])
        try:
            res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=45.0)
            _append_log(tool_id, res.stdout or "Docker down complete.")
            return True, f"Stopped {meta['name']}."
        except Exception as e:
            _append_log(tool_id, f"Error stopping docker: {e}")
            return False, str(e)

    return True, "Stopped."


def restart_tool(tool_id: str) -> tuple[bool, str]:
    """Restart a tool."""
    stop_tool(tool_id)
    time.sleep(1.0)
    return start_tool(tool_id)


def get_logs(tool_id: str, limit: int = 100) -> List[str]:
    """Get the latest log lines for a tool."""
    buf = _LOG_BUFFERS[tool_id]
    lines = list(buf)
    return lines[-limit:]
