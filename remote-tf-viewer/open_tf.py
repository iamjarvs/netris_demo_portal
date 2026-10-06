#!/usr/bin/env python3
"""
Remote Terraform Viewer for Netris Controller
Launches Visual Studio Code via Remote - SSH to explore live Terraform manifests
on the remote Netris appliance.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_HOST = "ubuntu@adam-ctl.netris.io"
DEFAULT_PATH = "~/netris-init/netris-spectrum-x-init"


def load_config() -> dict:
    """Load configuration from local config.json and fallback to demo-portal global_config."""
    cfg = {
        "remote_host": DEFAULT_HOST,
        "remote_path": DEFAULT_PATH,
        "netris_url": "https://adam-ctl.netris.io",
        "netris_username": "netris",
        "netris_password": "913QGAi6oQTSGgZm20eU",
        "ssh_user": "ubuntu",
    }

    # Load local tool config
    tool_cfg_file = SCRIPT_DIR / "config.json"
    if tool_cfg_file.exists():
        try:
            with open(tool_cfg_file, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            print(f"[WARN] Could not parse {tool_cfg_file}: {e}", file=sys.stderr)

    # Check demo-portal global_config.json for dynamic credentials
    global_cfg_file = REPO_ROOT / "demo-portal" / "data" / "global_config.json"
    if global_cfg_file.exists():
        try:
            with open(global_cfg_file, "r", encoding="utf-8") as f:
                g_cfg = json.load(f)
                if g_cfg.get("netris_username"):
                    cfg["netris_username"] = g_cfg["netris_username"]
                if g_cfg.get("netris_password"):
                    cfg["netris_password"] = g_cfg["netris_password"]
                if g_cfg.get("netris_url"):
                    cfg["netris_url"] = g_cfg["netris_url"]
        except Exception:
            pass

    return cfg


def find_code_binary() -> str | None:
    """Locate the VS Code CLI binary."""
    code_bin = shutil.which("code")
    if code_bin:
        return code_bin

    candidates = [
        "/opt/homebrew/bin/code",
        "/usr/local/bin/code",
        "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
        os.path.expanduser("~/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"),
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def resolve_remote_path(host: str, path: str) -> str:
    """Resolve tilde for the remote host if applicable (e.g. ubuntu user)."""
    if path.startswith("~/"):
        user = host.split("@")[0] if "@" in host else "ubuntu"
        if user == "root":
            return f"/root/{path[2:]}"
        return f"/home/{user}/{path[2:]}"
    return path


def check_ssh_connectivity(host: str, remote_path: str) -> bool:
    """Quick check to confirm remote directory exists via SSH."""
    print(f"[*] Validating SSH connection to {host}...")
    try:
        resolved = resolve_remote_path(host, remote_path)
        res = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host, f"test -d {resolved} || test -d {remote_path}"],
            capture_output=True,
            text=True,
            timeout=8.0,
        )
        if res.returncode == 0:
            print(f"[OK] Remote host reachable and directory confirmed: {resolved}")
            return True
        else:
            print(f"[WARN] SSH test returned exit code {res.returncode}. Proceeding anyway.")
            return False
    except Exception as e:
        print(f"[WARN] Could not test SSH connection ({e}). Proceeding anyway.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Open remote Terraform files in VS Code via Remote-SSH on Netris controller."
    )
    parser.add_argument(
        "--host",
        default=None,
        help=f"Target SSH host (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--path",
        default=None,
        help=f"Remote path (default: {DEFAULT_PATH})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Perform pre-flight SSH connectivity test before launching VS Code",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for VS Code window instead of running in background",
    )

    args = parser.parse_args()
    cfg = load_config()

    host = args.host or cfg.get("remote_host", DEFAULT_HOST)
    remote_path = args.path or cfg.get("remote_path", DEFAULT_PATH)
    resolved_path = resolve_remote_path(host, remote_path)

    netris_user = cfg.get("netris_username", "netris")
    netris_pass = cfg.get("netris_password", "913QGAi6oQTSGgZm20eU")
    netris_url = cfg.get("netris_url", "https://adam-ctl.netris.io")

    print("=================================================================")
    print("      Netris Remote Terraform Explorer (VS Code Remote-SSH)      ")
    print("=================================================================")
    print(f" Target Host:       {host}")
    print(f" Remote Path:       {remote_path}")
    print(f" Resolved Path:     {resolved_path}")
    print(f" Netris Controller: {netris_url}")
    print(f" Netris Web/API:    Username: {netris_user} | Password: {netris_pass}")
    print(f" SSH User/Auth:     ubuntu (Configured SSH Key)")
    print("=================================================================")

    code_bin = find_code_binary()
    if not code_bin:
        print("[ERROR] 'code' command not found in PATH or standard locations.", file=sys.stderr)
        print("Please ensure Visual Studio Code and its shell command 'code' are installed.", file=sys.stderr)
        sys.exit(1)

    if args.check:
        check_ssh_connectivity(host, remote_path)

    cmd = [code_bin, "--remote", f"ssh-remote+{host}", resolved_path]
    print(f"[*] Command to execute: {' '.join(cmd)}")

    if args.wait:
        print("[*] Running VS Code in foreground...")
        res = subprocess.run(cmd)
        sys.exit(res.returncode)
    else:
        print("[*] Launching VS Code in background...")
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(f"[SUCCESS] VS Code launched successfully in background (PID {proc.pid}).")
        print(f"[INFO] Remote workspace: ssh-remote+{host}:{resolved_path}")


if __name__ == "__main__":
    main()
