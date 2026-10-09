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
import yaml

from app.models import ToolInfo

logger = logging.getLogger("tool_manager")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

VENV_PYTHON = REPO_ROOT / "demo-portal" / ".venv" / "bin" / "python3"
PYTHON_EXE = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"

# In-memory store for active subprocesses and logs
_PROCESS_REGISTRY: Dict[str, subprocess.Popen] = {}
_LOG_BUFFERS: Dict[str, collections.deque] = collections.defaultdict(lambda: collections.deque(maxlen=1000))
_START_TIMES: Dict[str, float] = {}

# Tool Definitions
TOOLS_METADATA: Dict[str, Dict[str, Any]] = {
    "netris-slurm-cluster-sim": {
        "id": "netris-slurm-cluster-sim",
        "name": "Slurm Dynamic Cluster Orchestrator",
        "category": "Other",
        "description": "Simulates Slurm HPC job scheduling, dynamically provisioning and dismantling Netris Server Clusters & RoCEv2 V-Nets.",
        "tool_type": "subprocess",
        "port": 8088,
        "popout_url": "http://localhost:8088",
        "health_endpoint": "http://localhost:8088/api/clusters",
        "default_args": [PYTHON_EXE, "run_simulation.py", "--sim-mode", "--port", "8088"],
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
        "health_endpoint": "http://localhost:8000/healthz",
        "default_args": [PYTHON_EXE, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        "cwd": REPO_ROOT / "provider-portal",
        "summary_command": "uvicorn app.main:app --port 8000",
    },
    "chatsim": {
        "id": "chatsim",
        "name": "Meridian ChatSim Console",
        "category": "Other",
        "description": "In-cluster AI chat assistant prop running on compute nodes, reflecting real tenant branding, Netris VPC, and active GPU rails.",
        "tool_type": "subprocess",
        "port": 8765,
        "popout_url": "http://localhost:8765",
        "health_endpoint": "http://localhost:8765/api/context",
        "default_args": [PYTHON_EXE, "server.py"],
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
        "port": 8001,
        "popout_url": "http://localhost:8001",
        "health_endpoint": "http://localhost:8090/health",
        "start_script": ["./start.sh"],
        "stop_script": ["./stop.sh"],
        "cwd": REPO_ROOT / "netbox-netris",
        "summary_command": "./start-netbox-integration.sh",
    },
    "cli-inspector": {
        "id": "cli-inspector",
        "name": "Cumulus Switch CLI Inspector & Config Audit",
        "category": "Fabric Assurance & Visibility",
        "description": "Interactive CLI and web dashboard for exploring NVIDIA Cumulus switches, running live NVUE show commands, comparing configs, and tracking git revision history.",
        "tool_type": "subprocess",
        "port": 8743,
        "popout_url": "http://localhost:8743",
        "health_endpoint": "http://localhost:8743/api/health",
        "start_script": ["./start.sh"],
        "stop_script": [],
        "default_args": ["./start.sh"],
        "cli_args": ["./run.sh"],
        "cwd": REPO_ROOT / "cli-inspector",
        "summary_command": "./start.sh",
        "cli_summary_command": "./run.sh",
    },
    "fabric-builder-ui": {
        "id": "fabric-builder-ui",
        "name": "Netris Fabric Terraform Builder",
        "category": "Cloud Control Plane",
        "description": "Visual designer and code generator for Day-0 Netris OpenTofu/Terraform deployments with live controller conflict detection.",
        "tool_type": "subprocess",
        "port": 5050,
        "popout_url": "http://localhost:5050",
        "health_endpoint": "http://localhost:5050/api/health",
        "start_script": ["./start.sh"],
        "stop_script": [],
        "default_args": [PYTHON_EXE, "app.py"],
        "cwd": REPO_ROOT / "fabric-builder-ui" / "backend",
        "summary_command": "./start.sh",

    },
    "remote-tf-viewer": {
        "id": "remote-tf-viewer",
        "name": "Remote Terraform Explorer (VS Code)",
        "category": "Other",
        "description": "Opens VS Code via Remote-SSH connected directly to the Netris Controller to explore and edit live Spectrum-X Day-0 Terraform manifests.",
        "tool_type": "subprocess",
        "port": None,
        "popout_url": None,
        "health_endpoint": None,
        "default_args": [PYTHON_EXE, "open_tf.py"],
        "cwd": REPO_ROOT / "remote-tf-viewer",
        "summary_command": "./run.sh",
    }
}


SESSION_OPTIONS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "netris-prometheus-exporter": {
        "title": "Observability Stack Session Configuration",
        "description": "Configure telemetry streaming mode and Prometheus TSDB historical backfill duration before launching.",
        "fields": [
            {
                "id": "mode",
                "label": "Telemetry Stream Source",
                "type": "select",
                "default": "sim",
                "options": [
                    {"value": "sim", "label": "Offline Simulation Replay (100% Offline Loop, No Controller)"},
                    {"value": "live", "label": "Live Netris Streaming (Active Controller)"}
                ]
            },
            {
                "id": "backfill_minutes",
                "label": "Historical TSDB Backfill (Minutes)",
                "type": "number",
                "default": 90,
                "min": 0,
                "max": 360,
                "help": "Pre-populates Prometheus TSDB with instant historical metrics for immediate Grafana inspection."
            },
            {
                "id": "do_backfill",
                "label": "Pre-populate Prometheus TSDB on startup",
                "type": "boolean",
                "default": True
            }
        ]
    },
    "netris-slurm-cluster-sim": {
        "title": "Slurm Orchestrator Session Configuration",
        "description": "Configure scheduler execution speed, offline vs. live Netris synchronization, and web dashboard port.",
        "fields": [
            {
                "id": "mode",
                "label": "Execution Mode",
                "type": "select",
                "default": "sim",
                "options": [
                    {"value": "sim", "label": "Simulated Replay Engine (Offline, 12 Mock HGX Nodes)"},
                    {"value": "live", "label": "Live Netris Controller (adam-ctl.netris.io)"}
                ]
            },
            {
                "id": "speedup",
                "label": "Simulation Clock Acceleration",
                "type": "select",
                "default": "1",
                "options": [
                    {"value": "1", "label": "1x Real-Time (~2m sync per VPC/cluster)"},
                    {"value": "2", "label": "2x Accelerated (~1m sync)"},
                    {"value": "5", "label": "5x Fast Demo (~25s sync)"},
                    {"value": "10", "label": "10x High-Speed Automated (~12s sync)"}
                ]
            },
            {
                "id": "port",
                "label": "Web Dashboard Port",
                "type": "number",
                "default": 8088
            }
        ]
    },
}


def get_tool_credentials(tool_id: str) -> List[Dict[str, Any]]:
    """Return live credentials for the tool, dynamically read from its environment config."""
    creds: List[Dict[str, Any]] = []
    if tool_id == "provider-portal":
        env_path = REPO_ROOT / "provider-portal" / ".env"
        op_user, op_pass = "admin", "C1sco123!"
        cust_user, cust_pass = "user", "C1sco123!"
        if env_path.exists():
            try:
                from dotenv import dotenv_values
                vals = dotenv_values(env_path)
                op_user = vals.get("OPERATOR_USERNAME") or op_user
                op_pass = vals.get("OPERATOR_PASSWORD") or op_pass
                cust_user = vals.get("CUSTOMER_USERNAME") or cust_user
                cust_pass = vals.get("CUSTOMER_PASSWORD") or cust_pass
            except Exception:
                pass
        creds.append({"label": "Operator/Admin", "username": op_user, "password": op_pass, "role": "operator"})
        creds.append({"label": "Customer", "username": cust_user, "password": cust_pass, "role": "customer"})

    elif tool_id == "netbox-netris":
        env_path = REPO_ROOT / "netbox-netris" / ".env"
        superuser_pass = "admin"
        if env_path.exists():
            try:
                from dotenv import dotenv_values
                vals = dotenv_values(env_path)
                superuser_pass = vals.get("NETBOX_SUPERUSER_PASSWORD") or superuser_pass
            except Exception:
                pass
        creds.append({"label": "Superuser", "username": "admin", "password": superuser_pass, "role": "admin"})

    elif tool_id == "netris-prometheus-exporter":
        conf_path = REPO_ROOT / "netris-prometheus-exporter" / "config.env"
        g_user, g_pass = "admin", "admin"
        if conf_path.exists():
            try:
                from dotenv import dotenv_values
                vals = dotenv_values(conf_path)
                g_user = vals.get("GRAFANA_ADMIN_USER") or g_user
                g_pass = vals.get("GRAFANA_ADMIN_PASSWORD") or g_pass
            except Exception:
                pass
        creds.append({"label": "Grafana Admin", "username": g_user, "password": g_pass, "role": "admin"})

    elif tool_id == "netris-slurm-cluster-sim":
        creds.append({"label": "Web Dashboard", "username": "Public", "password": "No Auth", "no_auth": True, "notes": "No login required"})

    elif tool_id == "chatsim":
        creds.append({"label": "Meridian Console", "username": "Public", "password": "No Auth", "no_auth": True, "notes": "No login required"})

    elif tool_id == "gpu-ai-fabric-traffic-sim":
        creds.append({"label": "Container Fleet", "username": "root", "password": "No Auth", "no_auth": True, "notes": "8 iPerf3 rails active"})

    elif tool_id == "netris-controller-gpu-traffic-sim":
        creds.append({"label": "Netris Controller", "username": "admin", "password": "913QGAi6oQTSGgZm20eU", "notes": "adam-ctl.netris.io"})
        creds.append({"label": "Controller SSH", "username": "ubuntu", "password": "SSH Key", "notes": "adam-ctl.netris.io"})

    elif tool_id == "switch-isolation-cli":
        conf_path = REPO_ROOT / "switch-isolation-cli" / "config.json"
        n_user, jump_host, jump_user = "netris", "adam-ctl.netris.io", "ubuntu"
        if conf_path.exists():
            try:
                import json
                with open(conf_path, "r", encoding="utf-8") as f:
                    c = json.load(f)
                    n_user = c.get("netris_username") or n_user
                    jump_host = c.get("ssh_jump_host") or jump_host
                    jump_user = c.get("ssh_jump_user") or jump_user
            except Exception:
                pass
        creds.append({"label": "Netris API", "username": n_user, "password": "••••••••", "notes": "adam-ctl.netris.io"})
        creds.append({"label": "SSH Jump Host", "username": jump_user, "password": "••••••••", "notes": jump_host})

    elif tool_id == "cli-inspector":
        conf_path = REPO_ROOT / "cli-inspector" / "config.json"
        n_user, jump_host, jump_user = "netris", "adam-ctl.netris.io", "ubuntu"
        if conf_path.exists():
            try:
                import json
                with open(conf_path, "r", encoding="utf-8") as f:
                    c = json.load(f)
                    n_user = c.get("netris_username") or n_user
                    jump_host = c.get("ssh_jump_host") or jump_host
                    jump_user = c.get("ssh_jump_user") or jump_user
            except Exception:
                pass
        creds.append({"label": "Netris API", "username": n_user, "password": "••••••••", "notes": "adam-ctl.netris.io"})
        creds.append({"label": "SSH Jump Host", "username": jump_user, "password": "Key Auth", "notes": jump_host})

    elif tool_id == "fabric-builder-ui":
        creds.append({"label": "Netris Controller", "username": "netris", "password": "••••••••", "notes": "https://adam-ctl.netris.io"})

    elif tool_id == "remote-tf-viewer":
        creds.append({"label": "Netris Controller", "username": "netris", "password": "913QGAi6oQTSGgZm20eU", "notes": "adam-ctl.netris.io"})
        creds.append({"label": "SSH Controller", "username": "ubuntu", "password": "SSH Key", "notes": "adam-ctl.netris.io:~/netris-init/netris-spectrum-x-init"})

    return creds


def is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Test whether a TCP port is currently open and listening."""
    if not port:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False



# Load Dynamic Tools from tools.yaml
def load_dynamic_tools():
    yaml_path = REPO_ROOT / "demo-portal" / "tools.yaml"
    if yaml_path.exists():
        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
                if data and "tools" in data:
                    for t in data["tools"]:
                        t_id = t.get("id") or t.get("name", "").lower().replace(" ", "-")
                        t_path = REPO_ROOT / "demo-portal" / t.get("path", "")
                        
                        existing = TOOLS_METADATA.get(t_id, {})
                        
                        TOOLS_METADATA[t_id] = {
                            **existing,
                            "id": t_id,
                            "name": t.get("name", existing.get("name")),
                            "category": existing.get("category", "Dynamically Loaded"),
                            "description": t.get("description", existing.get("description", "")),
                            "tool_type": t.get("tool_type", existing.get("tool_type", "docker" if t.get("type") == "git" else "subprocess")),
                            "cwd": t_path.resolve(),
                            "optional": t.get("optional", False),
                            "url": t.get("url")
                        }
                        if "start_script" not in TOOLS_METADATA[t_id]:
                            TOOLS_METADATA[t_id]["start_script"] = ["./start.sh"]
                        if "stop_script" not in TOOLS_METADATA[t_id]:
                            TOOLS_METADATA[t_id]["stop_script"] = ["./stop.sh"]
                        if "summary_command" not in TOOLS_METADATA[t_id]:
                            TOOLS_METADATA[t_id]["summary_command"] = "./start.sh"

        except Exception as e:
            logger.error(f"Failed to load tools.yaml: {e}")

load_dynamic_tools()

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

        if meta["tool_type"] in ("subprocess", "remote", "interactive"):
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
            summary_command=meta.get("summary_command", ""),
            is_optional=meta.get("optional", False),
            is_downloaded=meta.get("cwd").exists() if meta.get("cwd") else True,
            credentials=get_tool_credentials(tool_id),
            session_options=SESSION_OPTIONS_REGISTRY.get(tool_id),
        ))
    return results


import shutil

def check_dependencies(tool_type: str, has_git_url: bool) -> tuple[bool, str]:
    missing = []
    import shutil, subprocess
    if has_git_url:
        if not shutil.which("git"):
            missing.append("git")
    
    if tool_type == "docker":
        docker_path = shutil.which("docker")
        if not docker_path:
            missing.append("docker")
        else:
            # Try both docker compose and docker-compose
            try:
                res = subprocess.run([docker_path, "compose", "version"], capture_output=True, text=True)
                if res.returncode != 0:
                    res2 = subprocess.run(["docker-compose", "version"], capture_output=True, text=True)
                    if res2.returncode != 0:
                        missing.append("docker compose")
            except Exception:
                try:
                    res2 = subprocess.run(["docker-compose", "version"], capture_output=True, text=True)
                    if res2.returncode != 0:
                        missing.append("docker compose")
                except:
                    missing.append("docker compose")
                    
    if missing:
        return False, f"Missing system dependencies: {', '.join(missing)}. Please install them and try again."
    return True, ""

def start_tool(
    tool_id: str,
    custom_args: Optional[List[str]] = None,
    session_params: Optional[Dict[str, Any]] = None
) -> tuple[bool, str]:
    """Start a tool via subprocess or Docker Compose, optionally applying session parameters."""
    meta = TOOLS_METADATA.get(tool_id)
    if not meta:
        return False, f"Tool '{tool_id}' not found."

    cwd = meta["cwd"]
    has_git = bool(meta.get("tool_type") == "git" or "url" in meta)
    
    if not cwd.exists() and not has_git:
        return False, f"Directory '{cwd}' does not exist."

    _append_log(tool_id, f"Initiating start sequence for {meta['name']}...")
    
    has_git = bool(meta.get("tool_type") == "git" or "url" in meta)
    deps_ok, deps_msg = check_dependencies(meta["tool_type"], has_git)
    if not deps_ok:
        _append_log(tool_id, deps_msg)
        return False, deps_msg
    
    # --- Dynamic Git Cloning Logic ---
    if meta.get("tool_type") == "git" or "url" in meta:
        git_url = meta.get("url")
        if not cwd.exists():
            _append_log(tool_id, f"Cloning repository {git_url} into {cwd}...")
            cwd.parent.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(["git", "clone", git_url, str(cwd)], check=True, capture_output=True, text=True)
                _append_log(tool_id, f"Successfully cloned {git_url}.")
            except subprocess.CalledProcessError as e:
                _append_log(tool_id, f"Failed to clone repository: {e.stderr}")
                return False, f"Failed to clone {git_url}"
        else:
            _append_log(tool_id, f"Repository already exists at {cwd}. Pulling latest changes...")
            try:
                subprocess.run(["git", "pull"], cwd=cwd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                _append_log(tool_id, f"Warning: Failed to pull latest changes: {e.stderr}")


    effective_cmd = custom_args
    if not effective_cmd and session_params:
        if tool_id == "netris-prometheus-exporter":
            mode = session_params.get("mode", "sim")
            effective_cmd = ["./start.sh", f"--{mode}"]
            if session_params.get("do_backfill") is False:
                effective_cmd.append("--no-backfill")
            elif session_params.get("backfill_minutes") is not None:
                effective_cmd.extend(["--backfill", str(session_params["backfill_minutes"])])
        elif tool_id == "netris-slurm-cluster-sim":
            port = str(session_params.get("port", 8088))
            effective_cmd = [PYTHON_EXE, "run_simulation.py", "--port", port]
            if session_params.get("mode", "sim") == "sim":
                effective_cmd.append("--sim-mode")
            speedup = str(session_params.get("speedup", "1"))
            if speedup != "1":
                effective_cmd.extend(["--speedup", speedup])
        elif tool_id == "netris-controller-gpu-traffic-sim":
            effective_cmd = ["./deploy.sh"]
            pattern = session_params.get("pattern")
            if pattern:
                effective_cmd.extend(["--pattern", pattern])
            duration = session_params.get("duration")
            if duration:
                effective_cmd.extend(["--duration", str(duration)])
            max_bw = session_params.get("max_bandwidth")
            if max_bw:
                effective_cmd.extend(["--max-bandwidth", str(max_bw)])
            if session_params.get("continuous"):
                effective_cmd.append("--continuous")

    if meta["tool_type"] == "subprocess":
        # Check if already running
        existing = _PROCESS_REGISTRY.get(tool_id)
        if existing and existing.poll() is None:
            return True, f"Tool '{tool_id}' is already running (PID {existing.pid})."

        try:
            from app.config_sync import load_global_config, sync_global_to_all_tools
            sync_global_to_all_tools(load_global_config())
        except Exception as e:
            logger.warning(f"Could not auto-sync global config: {e}")

        cmd = effective_cmd or meta.get("start_script") or meta["default_args"]
        proc_env = os.environ.copy()
        env_file = cwd / ".env"
        if env_file.exists():
            try:
                from dotenv import dotenv_values
                loaded_env = {k: v for k, v in dotenv_values(env_file).items() if v is not None}
                proc_env.update(loaded_env)
            except Exception as e:
                logger.warning(f"Could not load .env from {env_file}: {e}")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=proc_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
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
        cmd = effective_cmd or meta.get("start_script", ["docker", "compose", "up", "-d"])
        try:
            res = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300.0
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
        existing = _PROCESS_REGISTRY.get(tool_id)
        if existing and existing.poll() is None:
            return True, f"Tool '{tool_id}' is already running (PID {existing.pid})."

        cmd = effective_cmd or meta.get("start_script")
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            _PROCESS_REGISTRY[tool_id] = proc
            _START_TIMES[tool_id] = time.time()

            t = threading.Thread(target=_stream_output, args=(tool_id, proc), daemon=True)
            t.start()

            _append_log(tool_id, f"Started remote automation process with PID {proc.pid}: {' '.join(cmd)}")
            return True, f"Started {meta['name']} successfully (PID {proc.pid})."
        except Exception as e:
            _append_log(tool_id, f"Failed to launch remote script: {e}")
            return False, f"Failed to launch: {e}"

    elif meta["tool_type"] == "interactive":
        return launch_native_terminal(tool_id)

    return False, "Unknown tool type."


def stop_tool(tool_id: str) -> tuple[bool, str]:
    """Stop a running tool."""
    meta = TOOLS_METADATA.get(tool_id)
    if not meta:
        return False, f"Tool '{tool_id}' not found."

    cwd = meta["cwd"]
    _append_log(tool_id, f"Stopping {meta['name']}...")

    if meta["tool_type"] in ("subprocess", "remote", "interactive"):
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


def launch_native_terminal(tool_id: str) -> tuple[bool, str]:
    """Open an iTerm session (with fallback to Terminal.app) running the tool's launcher script."""
    meta = TOOLS_METADATA.get(tool_id)
    if not meta:
        return False, f"Tool '{tool_id}' not found."
    cwd = str(meta["cwd"])
    cmd_str = meta.get("cli_summary_command") or meta.get("summary_command", "./run.sh")

    # Priority 1: iTerm / iTerm2
    iterm_script = f'''
    tell application "iTerm"
        activate
        create window with default profile
        tell current session of current window
            write text "cd '{cwd}' && {cmd_str}"
        end tell
    end tell
    '''
    try:
        res = subprocess.run(["osascript", "-e", iterm_script], capture_output=True, text=True, timeout=6.0)
        if res.returncode == 0:
            _append_log(tool_id, f"Launched native iTerm session: cd '{cwd}' && {cmd_str}")
            return True, "Launched native iTerm window."
        logger.warning("iTerm AppleScript error: %s. Trying Terminal.app fallback.", res.stderr.strip())
    except Exception as e:
        logger.warning("Failed to launch iTerm: %s. Trying Terminal.app fallback.", e)

    # Priority 2: Fallback to Terminal.app if iTerm is unavailable
    terminal_script = f'''
    tell application "Terminal"
        activate
        do script "cd '{cwd}' && {cmd_str}"
    end tell
    '''
    try:
        res = subprocess.run(["osascript", "-e", terminal_script], capture_output=True, text=True, timeout=5.0)
        if res.returncode == 0:
            _append_log(tool_id, f"Launched native Terminal.app session: cd '{cwd}' && {cmd_str}")
            return True, "Launched native Terminal window."
        return False, f"AppleScript error: {res.stderr.strip()}"
    except Exception as e:
        return False, f"Failed to launch terminal: {e}"


# --- Telemetry Recording State Management ---
_RECORDING_LOCK = threading.Lock()
_RECORDING_STATE: Dict[str, Any] = {
    "is_recording": False,
    "status": "idle",
    "start_time": None,
    "elapsed_seconds": 0.0,
    "duration": 300,
    "interval": 15,
    "frames_captured": 0,
    "progress_pct": 0.0,
    "output_file": "sim_data/telemetry_recording.json",
    "file_size_mb": 0.0,
    "error": None,
    "message": None,
}
_RECORDING_PROC: Optional[subprocess.Popen] = None


def start_telemetry_recording(duration: int = 300, interval: int = 15) -> tuple[bool, str]:
    """Start on-demand telemetry recording from Netris Controller in background."""
    global _RECORDING_PROC
    with _RECORDING_LOCK:
        if _RECORDING_STATE["is_recording"]:
            return False, "A telemetry recording session is already active."

        prom_dir = REPO_ROOT / "netris-prometheus-exporter"
        output_rel = "sim_data/telemetry_recording.json"
        output_abs = prom_dir / output_rel
        output_abs.parent.mkdir(parents=True, exist_ok=True)

        _RECORDING_STATE["is_recording"] = True
        _RECORDING_STATE["status"] = "recording"
        _RECORDING_STATE["start_time"] = time.time()
        _RECORDING_STATE["elapsed_seconds"] = 0.0
        _RECORDING_STATE["duration"] = duration
        _RECORDING_STATE["interval"] = interval
        _RECORDING_STATE["frames_captured"] = 0
        _RECORDING_STATE["progress_pct"] = 0.0
        _RECORDING_STATE["output_file"] = str(output_rel)
        _RECORDING_STATE["file_size_mb"] = 0.0
        _RECORDING_STATE["error"] = None
        _RECORDING_STATE["message"] = f"Recording telemetry for {duration}s (interval: {interval}s)..."

        prom_venv = prom_dir / ".venv" / "bin" / "python3"
        py_bin = str(prom_venv) if prom_venv.exists() else PYTHON_EXE

        cmd = [py_bin, "record.py", "-d", str(duration), "-i", str(interval), "-o", str(output_rel)]
        _append_log("netris-prometheus-exporter", f"Initiating live telemetry recording: {' '.join(cmd)}")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=prom_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            _RECORDING_PROC = proc

            def _record_worker(p: subprocess.Popen, dur: int, out_path: Path):
                import re
                frame_regex = re.compile(r"(?:Capturing frame|Frame)\s+(\d+)", re.IGNORECASE)
                for raw_line in iter(p.stdout.readline, b""):
                    if not raw_line:
                        break
                    try:
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        _append_log("netris-prometheus-exporter", f"[Recorder] {line}")
                        m = frame_regex.search(line)
                        if m:
                            f_idx = int(m.group(1))
                            with _RECORDING_LOCK:
                                _RECORDING_STATE["frames_captured"] = max(_RECORDING_STATE["frames_captured"], f_idx)
                                if _RECORDING_STATE["start_time"]:
                                    elapsed = time.time() - _RECORDING_STATE["start_time"]
                                    _RECORDING_STATE["elapsed_seconds"] = round(elapsed, 1)
                                    _RECORDING_STATE["progress_pct"] = min(99.0, round((elapsed / dur) * 100, 1))
                                if out_path.exists():
                                    _RECORDING_STATE["file_size_mb"] = round(out_path.stat().st_size / (1024 * 1024), 2)
                    except Exception:
                        pass
                p.wait()
                with _RECORDING_LOCK:
                    _RECORDING_STATE["is_recording"] = False
                    if _RECORDING_STATE["status"] == "stopped":
                        # Preserved stopped state from user cancel
                        return
                    if p.returncode == 0:
                        _RECORDING_STATE["status"] = "completed"
                        _RECORDING_STATE["progress_pct"] = 100.0
                        if out_path.exists():
                            _RECORDING_STATE["file_size_mb"] = round(out_path.stat().st_size / (1024 * 1024), 2)
                        _RECORDING_STATE["message"] = f"Recording complete! Saved {_RECORDING_STATE['frames_captured']} frames ({_RECORDING_STATE['file_size_mb']} MB)."
                        _append_log("netris-prometheus-exporter", f"[Recorder] Finished successfully. Simulation replay dataset refreshed.")
                    else:
                        _RECORDING_STATE["status"] = "error"
                        _RECORDING_STATE["error"] = f"Recorder exited with code {p.returncode}"
                        _RECORDING_STATE["message"] = _RECORDING_STATE["error"]
                        _append_log("netris-prometheus-exporter", f"[Recorder] Failed with exit code {p.returncode}")

            t = threading.Thread(target=_record_worker, args=(proc, duration, output_abs), daemon=True)
            t.start()
            return True, f"Telemetry recording started for {duration} seconds."
        except Exception as e:
            _RECORDING_STATE["is_recording"] = False
            _RECORDING_STATE["status"] = "error"
            _RECORDING_STATE["error"] = str(e)
            return False, f"Failed to launch recorder: {e}"


def get_telemetry_recording_status() -> Dict[str, Any]:
    """Retrieve current telemetry recording progress and state."""
    with _RECORDING_LOCK:
        state = dict(_RECORDING_STATE)
        if state["is_recording"] and state["start_time"]:
            elapsed = time.time() - state["start_time"]
            state["elapsed_seconds"] = round(elapsed, 1)
            dur = max(1, state["duration"])
            state["progress_pct"] = min(99.0, round((elapsed / dur) * 100, 1))
            prom_dir = REPO_ROOT / "netris-prometheus-exporter"
            out_file = prom_dir / state["output_file"]
            if out_file.exists():
                state["file_size_mb"] = round(out_file.stat().st_size / (1024 * 1024), 2)
        return state


def stop_telemetry_recording() -> tuple[bool, str]:
    """Stop active telemetry recording session early and preserve captured frames."""
    global _RECORDING_PROC
    with _RECORDING_LOCK:
        if not _RECORDING_STATE["is_recording"]:
            return False, "No telemetry recording is currently in progress."
        if _RECORDING_PROC and _RECORDING_PROC.poll() is None:
            try:
                _RECORDING_PROC.terminate()
                _RECORDING_PROC.wait(timeout=3.0)
            except Exception:
                _RECORDING_PROC.kill()
        _RECORDING_STATE["is_recording"] = False
        _RECORDING_STATE["status"] = "stopped"
        _RECORDING_STATE["message"] = f"Recording stopped early ({_RECORDING_STATE['frames_captured']} frames captured)."
        _append_log("netris-prometheus-exporter", f"[Recorder] Stopped early by user.")
        return True, "Recording session stopped."

