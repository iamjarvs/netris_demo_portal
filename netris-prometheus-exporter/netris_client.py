"""Netris Controller REST API Client.

Handles session cookie authentication, automatic re-authentication upon 401,
metadata retrieval (Sites, Hardware, Links, VPCs, VNets, Clusters),
and operational health/telemetry data retrieval.
"""

from __future__ import annotations

import logging
import threading
from typing import Any
import requests
import urllib3

from config import config

# Suppress insecure request warnings if SSL verification is disabled
if not config.verify_ssl:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("netris_client")


class NetrisClientError(Exception):
    """Base exception for Netris client errors."""
    pass


class NetrisAuthError(NetrisClientError):
    """Authentication failed."""
    pass


class NetrisClient:
    def __init__(self, base_url: str | None = None, username: str | None = None, password: str | None = None):
        self.base_url = (base_url or config.netris_url).rstrip("/")
        self.username = username or config.netris_username
        self.password = password or config.netris_password
        self.auth_scheme_id = config.auth_scheme_id
        self.verify_ssl = config.verify_ssl
        self.timeout = config.scrape_timeout

        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        self._authenticated = False
        self._lock = threading.Lock()

    def login(self) -> bool:
        """Authenticate with the Netris Controller via POST /api/auth."""
        with self._lock:
            url = f"{self.base_url}/api/auth"
            payload = {
                "user": self.username,
                "password": self.password,
                "auth_scheme_id": self.auth_scheme_id,
            }
            try:
                resp = self.session.post(url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if not data.get("isSuccess"):
                    err = data.get("message") or (data.get("errors") or {}).get("error") or "Unknown error"
                    logger.error("Authentication failed: %s", err)
                    self._authenticated = False
                    return False

                self._authenticated = True
                user_info = data.get("data") or {}
                logger.info("Successfully authenticated to Netris as '%s' (User ID: %s)", user_info.get("login"), user_info.get("user_id"))
                return True
            except Exception as e:
                logger.error("Error during Netris authentication: %s", e)
                self._authenticated = False
                return False

    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Perform request with automatic re-login on 401."""
        if not self._authenticated:
            if not self.login():
                raise NetrisAuthError("Cannot execute request: not authenticated.")

        path = path.lstrip("/")
        url = f"{self.base_url}/{path}"
        kwargs.setdefault("timeout", self.timeout)

        try:
            resp = self.session.request(method, url, **kwargs)
            if resp.status_code == 401:
                logger.info("Netris session expired (HTTP 401), re-authenticating...")
                self._authenticated = False
                if not self.login():
                    raise NetrisAuthError("Re-authentication failed.")
                resp = self.session.request(method, url, **kwargs)

            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, dict):
                if payload.get("isSuccess") is False:
                    logger.warning("Netris API %s returned error: %s", path, payload.get("message"))
                return payload.get("data") if "data" in payload else payload
            return payload

        except requests.exceptions.RequestException as e:
            logger.error("HTTP request error on %s: %s", path, e)
            raise NetrisClientError(f"Request failed: {e}") from e

    def get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    # --- Metadata Endpoints ---

    def get_sites(self) -> list[dict]:
        data = self.get("/api/v2/sites")
        return data if isinstance(data, list) else []

    def get_hardware(self) -> list[dict]:
        data = self.get("/api/v2/hw")
        return data if isinstance(data, list) else []

    def get_ports(self) -> list[dict]:
        data = self.get("/api/v2/hw/ports")
        return data if isinstance(data, list) else []

    def get_links(self) -> list[dict]:
        data = self.get("/api/v2/link")
        return data if isinstance(data, list) else []

    def get_vpcs(self) -> list[dict]:
        data = self.get("/api/v2/vpc")
        return data if isinstance(data, list) else []

    def get_vnets(self) -> list[dict]:
        data = self.get("/api/v2/vnet")
        return data if isinstance(data, list) else []

    def get_server_clusters(self) -> list[dict]:
        data = self.get("/api/v2/server-cluster")
        return data if isinstance(data, list) else []

    def get_ebgp(self) -> list[dict]:
        data = self.get("/api/v2/ebgp")
        return data if isinstance(data, list) else []

    def get_ipam_subnets(self) -> list[dict]:
        data = self.get("/api/v2/ipam/subnets")
        return data if isinstance(data, list) else []

    def get_tenants(self) -> list[dict]:
        data = self.get("/api/tenants")
        return data if isinstance(data, list) else []

    # --- Telemetry & Health Endpoints ---

    def get_hardware_health(self) -> list[dict]:
        """Returns the full list of Continuous Active Assurance health checks.
        Each item is a check group (or list of check entries).
        """
        data = self.get("/api/v2/dashboard/hardware-health")
        return data if isinstance(data, list) else []

    def get_agent_heartbeats(self) -> list[dict]:
        """Returns the live heartbeat status of all switch and softgate agents."""
        data = self.get("/api/v2/dashboard/agent-heartbeats")
        return data if isinstance(data, list) else []

    def get_hardware_alarms(self) -> list[dict]:
        data = self.get("/api/v2/dashboard/hardware-alarms")
        return data if isinstance(data, list) else []

    def get_graphite_metrics(
        self,
        targets: list[str] | str,
        time_from: str = "-3min",
        time_until: str = "now"
    ) -> list[dict]:
        """Query Netris embedded Graphite engine for streaming time-series data."""
        if isinstance(targets, str):
            targets = [targets]
        params = [("format", "json"), ("from", time_from), ("until", time_until)]
        for t in targets:
            params.append(("target", t))
        try:
            resp = self._request("POST", "/api/graphite", params=params)
            if isinstance(resp, list):
                return resp
            return []
        except Exception as e:
            logger.warning("Failed to query Graphite metrics: %s", e)
            return []
