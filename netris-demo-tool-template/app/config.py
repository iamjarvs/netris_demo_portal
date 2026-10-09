"""Configuration loader supporting both .env and config.json from project root."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

# Project root directory (one level above 'app')
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env if present at project root
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except ImportError:
        # Fallback simple parser if python-dotenv is not yet installed
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k not in os.environ:
                        os.environ[k] = v

CONFIG_JSON_FILE = PROJECT_ROOT / "config.json"


def get_config() -> Dict[str, Any]:
    """Retrieve runtime configuration combining environment variables and config.json defaults."""
    cfg: Dict[str, Any] = {
        "netris_url": os.getenv("NETRIS_URL", "https://adam-ctl.netris.io").rstrip("/"),
        "netris_username": os.getenv("NETRIS_USERNAME", "netris"),
        "netris_password": os.getenv("NETRIS_PASSWORD", ""),
        "netris_verify_ssl": os.getenv("NETRIS_VERIFY_SSL", "false").lower() in ("true", "1", "yes"),
        "port": int(os.getenv("PORT", "8750")),
        "host": os.getenv("HOST", "0.0.0.0"),
        "ssh_jump_host": os.getenv("SSH_JUMP_HOST", "adam-ctl.netris.io"),
        "ssh_jump_port": int(os.getenv("SSH_JUMP_PORT", "22")),
        "ssh_jump_user": os.getenv("SSH_JUMP_USER", "ubuntu"),
        "ssh_switch_user": os.getenv("SSH_SWITCH_USER", "cumulus"),
    }

    # Overlay with config.json if present
    if CONFIG_JSON_FILE.exists():
        try:
            with open(CONFIG_JSON_FILE, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                for k, v in json_data.items():
                    if v is not None and (k not in cfg or not cfg[k]):
                        cfg[k] = v
        except Exception:
            pass

    return cfg
