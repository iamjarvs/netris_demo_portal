"""
Configuration Manager for Netris Switch Isolation CLI.
Handles reading, writing, and interactively modifying credentials
persisted in a local config.json file.
"""

import json
from pathlib import Path
from typing import Any, Dict
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()
CONFIG_FILE = Path(__file__).resolve().parent / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "netris_url": "https://adam-ctl.netris.io",
    "netris_username": "netris",
    "netris_password": "913QGAi6oQTSGgZm20eU",
    "ssh_jump_host": "adam-ctl.netris.io",
    "ssh_jump_port": 22,
    "ssh_jump_user": "ubuntu",
    "ssh_jump_password": "913QGAi6oQTSGgZm20eU",
    "ssh_switch_user": "cumulus",
    "ssh_switch_key_path": "/home/ubuntu/.ssh/id_rsa"
}


def load_config() -> Dict[str, Any]:
    """Loads configuration from config.json, or creates it with defaults if missing."""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Merge with defaults for any missing keys
            for k, v in DEFAULT_CONFIG.items():
                data.setdefault(k, v)
            return data
    except Exception as e:
        console.print(f"[bold red]Failed to read {CONFIG_FILE}: {e}. Using defaults.[/bold red]")
        return dict(DEFAULT_CONFIG)


def save_config(cfg: Dict[str, Any]) -> None:
    """Saves configuration to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        console.print(f"[bold red]Failed to write {CONFIG_FILE}: {e}[/bold red]")


def display_settings(cfg: Dict[str, Any]) -> None:
    """Displays current settings in a formatted table."""
    table = Table(title="Current Netris & Infrastructure Settings", box=box.ROUNDED)
    table.add_column("Parameter", style="cyan", no_wrap=True)
    table.add_column("Configured Value", style="white")

    masked_pw = "••••••••••••" if cfg.get("netris_password") else "[dim]Not Set[/dim]"
    masked_jump_pw = "••••••••••••" if cfg.get("ssh_jump_password") else "[dim]Not Set[/dim]"

    table.add_row("Netris Controller URL", cfg.get("netris_url", ""))
    table.add_row("Netris Username", cfg.get("netris_username", ""))
    table.add_row("Netris Password", masked_pw)
    table.add_row("SSH Jump Host", f"{cfg.get('ssh_jump_host', '')}:{cfg.get('ssh_jump_port', 22)}")
    table.add_row("SSH Jump User", cfg.get("ssh_jump_user", ""))
    table.add_row("SSH Jump Password", masked_jump_pw)
    table.add_row("Switch SSH User", cfg.get("ssh_switch_user", "cumulus"))
    table.add_row("Switch Key on Jump", cfg.get("ssh_switch_key_path", ""))

    console.print(table)


def settings_menu():
    """Interactive settings configuration menu."""
    while True:
        console.clear()
        cfg = load_config()
        display_settings(cfg)

        action = questionary.select(
            "Settings Menu:",
            choices=[
                "1. Edit Netris Controller URL",
                "2. Edit Netris Username",
                "3. Edit Netris Password",
                "4. Edit SSH Jump Host & Port",
                "5. Edit SSH Jump Host Credentials",
                "6. Reset to Defaults",
                "« Back to Main Menu"
            ]
        ).ask()

        if action is None or action == "« Back to Main Menu":
            break

        if action.startswith("1."):
            val = questionary.text("Enter Netris Controller URL:", default=cfg.get("netris_url", "")).ask()
            if val:
                cfg["netris_url"] = val.strip().rstrip("/")
                save_config(cfg)

        elif action.startswith("2."):
            val = questionary.text("Enter Netris Username:", default=cfg.get("netris_username", "")).ask()
            if val:
                cfg["netris_username"] = val.strip()
                save_config(cfg)

        elif action.startswith("3."):
            val = questionary.password("Enter new Netris Password:").ask()
            if val:
                cfg["netris_password"] = val
                save_config(cfg)

        elif action.startswith("4."):
            host = questionary.text("Enter SSH Jump Host:", default=cfg.get("ssh_jump_host", "")).ask()
            port = questionary.text("Enter SSH Jump Port:", default=str(cfg.get("ssh_jump_port", 22))).ask()
            if host:
                cfg["ssh_jump_host"] = host.strip()
                cfg["ssh_jump_port"] = int(port.strip() or 22)
                save_config(cfg)

        elif action.startswith("5."):
            user = questionary.text("Enter SSH Jump User:", default=cfg.get("ssh_jump_user", "")).ask()
            pw = questionary.password("Enter SSH Jump Password (leave blank to keep current):").ask()
            if user:
                cfg["ssh_jump_user"] = user.strip()
            if pw:
                cfg["ssh_jump_password"] = pw
            save_config(cfg)

        elif action.startswith("6."):
            confirm = questionary.confirm("Reset all settings to default factory values?").ask()
            if confirm:
                save_config(DEFAULT_CONFIG)
                console.print("[bold yellow]Settings reset to defaults.[/bold yellow]")
                questionary.press_any_key_to_continue().ask()
