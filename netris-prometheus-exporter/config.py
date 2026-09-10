"""Configuration module for Netris Prometheus Exporter.

Loads configuration from netris.var (connection credentials) and
config.env (adjustable runtime parameters).
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Explicitly load netris.var and config.env from the current/script directory
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, "netris.var"))
load_dotenv(os.path.join(_BASE_DIR, ".var"))
load_dotenv(os.path.join(_BASE_DIR, "config.env"))
load_dotenv(os.path.join(_BASE_DIR, ".env"))


@dataclass
class Config:
    # Netris Connection Parameters (loaded from netris.var)
    netris_url: str = os.getenv("NETRIS_URL", "https://adam-ctl.netris.io").rstrip("/")
    netris_username: str = os.getenv("NETRIS_USERNAME", "netris")
    netris_password: str = os.getenv("NETRIS_PASSWORD", "913QGAi6oQTSGgZm20eU")
    auth_scheme_id: int = int(os.getenv("NETRIS_AUTH_SCHEME_ID", "1"))
    verify_ssl: bool = os.getenv("NETRIS_VERIFY_SSL", "false").lower() in ("true", "1", "yes")

    # Adjustable Runtime Parameters (loaded from config.env)
    metadata_refresh_interval: int = int(os.getenv("METADATA_REFRESH_INTERVAL", "300"))
    scrape_timeout: int = int(os.getenv("SCRAPE_TIMEOUT", "20"))
    exporter_host: str = os.getenv("EXPORTER_HOST", "0.0.0.0")
    exporter_port: int = int(os.getenv("EXPORTER_PORT", "9101"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Streaming Telemetry Parameters
    enable_streaming_traffic: bool = os.getenv("ENABLE_STREAMING_TRAFFIC", "true").lower() in ("true", "1", "yes")
    streaming_traffic_active_only: bool = os.getenv("STREAMING_TRAFFIC_ACTIVE_ONLY", "true").lower() in ("true", "1", "yes")

    # Offline Simulation Replay Parameters
    simulation_mode: bool = os.getenv("SIMULATION_MODE", "false").lower() in ("true", "1", "yes")
    sim_data_file: str = os.getenv("SIM_DATA_FILE", "sim_data/telemetry_recording.json")


config = Config()
