#!/usr/bin/env python3
"""
netris_api.py - Netris Controller REST API Client for Slurm Integration
Handles authentication, server discovery, and dynamic Server Cluster lifecycle
(create, read, delete) directly via the Netris Controller REST API.
"""

import copy
import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("netris_api")


class NetrisAPIClient:
    """Client for Netris Controller REST API v2 (supports both live Controller and offline Simulation/Replay mode)."""

    def __init__(
        self,
        base_url: str = "https://adam-ctl.netris.io",
        username: str = "netris",
        password: str = "913QGAi6oQTSGgZm20eU",
        event_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
        sim_mode: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.event_callback = event_callback
        self.sim_mode = sim_mode
        self.session_cookie: Optional[str] = None
        self.template_id: Optional[int] = None
        self.site_id: int = 3  # Datacenter-A
        self.vpc_id: int = 20  # Demo

        # Internal state for offline simulation / replay mode
        self._sim_cluster_counter = 100
        self._sim_clusters: Dict[int, Dict[str, Any]] = {}
        self._sim_servers = [
            {
                "id": 200 + i,
                "name": f"hgx-pod00-su0-h{i:02d}",
                "serverClusterID": None,
                "tenant": {"id": 1, "name": "Admin"},
                "site": {"id": 3, "name": "Datacenter-A"},
                "shared": False,
            }
            for i in range(6, 22)  # 16 HGX servers
        ]

        # Disable SSL verification for internal / self-signed certificates
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def _log_event(self, action: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Dispatches an event to the registered callback and logger."""
        logger.info(f"[{action}] {message}")
        if self.event_callback:
            try:
                self.event_callback(action, message, details or {})
            except Exception as e:
                logger.error(f"Error in event callback: {e}")

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        retry_on_auth: bool = True,
    ) -> Dict[str, Any]:
        """Makes an HTTP request to the Netris Controller API."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie

        payload = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=payload, headers=headers, method=method)

        start_time = time.time()
        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=15) as resp:
                status_code = resp.status
                # Save cookies if set
                set_cookie = resp.headers.get("Set-Cookie")
                if set_cookie:
                    self.session_cookie = set_cookie.split(";")[0]

                raw_body = resp.read().decode("utf-8")
                elapsed_ms = int((time.time() - start_time) * 1000)

                try:
                    result = json.loads(raw_body)
                except json.JSONDecodeError:
                    result = {"raw": raw_body, "isSuccess": status_code < 400}

                return result
        except urllib.error.HTTPError as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            raw_err = e.read().decode("utf-8")
            if e.code == 401 and retry_on_auth:
                logger.warning("Session expired (401). Re-authenticating...")
                self.authenticate()
                return self._request(method, endpoint, data=data, retry_on_auth=False)

            err_json = {}
            try:
                err_json = json.loads(raw_err)
            except json.JSONDecodeError:
                err_json = {"error": raw_err}

            raise RuntimeError(
                f"Netris API {method} {endpoint} failed ({e.code}, {elapsed_ms}ms): {err_json}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Netris API connection error: {e}") from e

    def authenticate(self) -> bool:
        """Logs into the Netris Controller and acquires a session cookie."""
        if self.sim_mode:
            self._log_event(
                "NETRIS_AUTH",
                f"[SIMULATION] Initializing Offline Simulation & Telemetry Engine (No external network)",
            )
            self._log_event(
                "NETRIS_AUTH_SUCCESS",
                f"[SIMULATION] Authenticated to Offline Netris Engine as '{self.username}'",
                {"user": "sim-admin", "mode": "simulated-replay"},
            )
            return True

        login_payload = {
            "user": self.username,
            "password": self.password,
            "authSchemeID": 0,
        }
        self._log_event("NETRIS_AUTH", f"Authenticating as '{self.username}' to {self.base_url}")
        res = self._request("POST", "/api/auth", data=login_payload, retry_on_auth=False)
        if res.get("isSuccess"):
            self._log_event(
                "NETRIS_AUTH_SUCCESS",
                f"Successfully authenticated as '{self.username}'",
                {"user": res.get("data", {}).get("name")},
            )
            return True
        else:
            raise RuntimeError(f"Netris authentication failed: {res}")

    def get_servers(self) -> List[Dict[str, Any]]:
        """Retrieves all HGX servers from Netris and their cluster assignment status."""
        if self.sim_mode:
            return copy.deepcopy(self._sim_servers)

        res = self._request("GET", "/api/v2/server-cluster/servers")
        if not res.get("isSuccess"):
            raise RuntimeError(f"Failed to fetch servers: {res}")
        return res.get("data", [])

    def get_available_servers(self, name_prefix: str = "hgx-") -> List[Dict[str, Any]]:
        """Returns servers that are currently unassigned (serverClusterID is None)."""
        all_servers = self.get_servers()
        available = [
            s
            for s in all_servers
            if s.get("serverClusterID") is None and s.get("name", "").startswith(name_prefix)
        ]
        return available

    def ensure_slurm_template(self, template_name: str = "slurm-rocev2-fabric") -> int:
        """Ensures the RoCEv2 server cluster template exists and returns its ID."""
        if self.template_id:
            return self.template_id

        if self.sim_mode:
            self.template_id = 6
            self._log_event(
                "NETRIS_CONFIG",
                f"[SIMULATION] Using template '{template_name}' (ID: {self.template_id}) with 8 RoCEv2 rails",
            )
            return self.template_id

        res = self._request("GET", "/api/v2/server-cluster-template")
        templates = res.get("data", [])
        for tmpl in templates:
            if tmpl.get("name") == template_name:
                self.template_id = tmpl.get("id")
                return self.template_id

        # Create template if not found
        self._log_event("NETRIS_CONFIG", f"Creating template '{template_name}' for 8-rail RoCEv2")
        payload = {
            "name": template_name,
            "vnets": [
                {
                    "postfix": "East-West",
                    "type": "l3vpn",
                    "vlan": "untagged",
                    "vlanID": "auto",
                    "serverNics": [
                        "eth1",
                        "eth2",
                        "eth3",
                        "eth4",
                        "eth5",
                        "eth6",
                        "eth7",
                        "eth8",
                    ],
                }
            ],
        }
        create_res = self._request("POST", "/api/v2/server-cluster-template", data=payload)
        new_id = create_res.get("data", {}).get("id")
        if not new_id:
            raise RuntimeError(f"Failed to create template '{template_name}': {create_res}")

        self.template_id = new_id
        self._log_event(
            "NETRIS_CONFIG", f"Template '{template_name}' created with ID: {self.template_id}"
        )
        return self.template_id

    def create_server_cluster(
        self,
        cluster_name: str,
        server_list: List[Dict[str, Any]],
        vpc_id: Optional[int] = None,
        site_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Provisions a new Netris Server Cluster with assigned HGX nodes and RoCEv2 V-Net.
        server_list is a list of dicts: [{"id": <int>, "name": <str>}]
        """
        tmpl_id = self.ensure_slurm_template()
        vpc_id = vpc_id or self.vpc_id
        site_id = site_id or self.site_id
        server_names = ", ".join(s["name"] for s in server_list)

        if self.sim_mode:
            self._sim_cluster_counter += 1
            cluster_id = self._sim_cluster_counter
            # Update simulated servers state
            server_id_set = {s["id"] for s in server_list}
            for s in self._sim_servers:
                if s["id"] in server_id_set or s["name"] in [item["name"] for item in server_list]:
                    s["serverClusterID"] = cluster_id

            sim_cluster = {
                "id": cluster_id,
                "name": cluster_name,
                "admin": {"id": 1, "name": "Admin"},
                "site": {"id": site_id, "name": "Datacenter-A"},
                "vpc": {"id": vpc_id, "name": "Demo"},
                "status": {"label": "Active", "type": "success"},
                "srvClusterTemplate": {"id": tmpl_id, "name": "slurm-rocev2-fabric"},
                "tags": ["slurm-automated", "gpu-fabric", "offline-sim"],
                "servers": [{"id": s["id"], "name": s["name"], "shared": False} for s in server_list],
                "resources": {
                    "vnets": [
                        {
                            "id": 1000 + cluster_id,
                            "name": f"{cluster_name}-East-West",
                            "type": "l3vpn",
                            "vlan": "untagged",
                            "status": "active",
                        }
                    ]
                },
            }
            self._sim_clusters[cluster_id] = sim_cluster

            self._log_event(
                "NETRIS_CLUSTER_CREATE",
                f"[SIMULATION] POST /api/v2/server-cluster -> '{cluster_name}' with {len(server_list)} nodes ({server_names})",
                {"cluster_name": cluster_name, "servers": [s["name"] for s in server_list]},
            )
            self._log_event(
                "NETRIS_CLUSTER_READY",
                f"[SIMULATION] Server Cluster '{cluster_name}' provisioned (ID: {cluster_id}, 8-Rail RoCEv2 active)",
                {"cluster_id": cluster_id, "cluster_name": cluster_name, "node_count": len(server_list)},
            )
            return {
                "cluster_id": cluster_id,
                "cluster_name": cluster_name,
                "elapsed_ms": 12.0,
                "servers": server_list,
            }

        payload = {
            "name": cluster_name,
            "admin": {"id": 1, "name": "Admin"},
            "site": {"id": site_id, "name": "Datacenter-A"},
            "vpc": {"id": vpc_id, "name": "Demo"},
            "vpcList": [{"id": vpc_id, "name": "Demo", "postfix": "East-West"}],
            "srvClusterTemplate": {
                "id": tmpl_id,
                "name": "slurm-rocev2-fabric",
            },
            "tags": ["slurm-automated", "gpu-fabric"],
            "servers": [
                {"id": s["id"], "name": s["name"], "shared": False} for s in server_list
            ],
        }

        self._log_event(
            "NETRIS_CLUSTER_CREATE",
            f"POST /api/v2/server-cluster -> '{cluster_name}' with {len(server_list)} nodes ({server_names})",
            {"cluster_name": cluster_name, "servers": [s["name"] for s in server_list]},
        )

        start = time.time()
        res = self._request("POST", "/api/v2/server-cluster", data=payload)
        elapsed = round((time.time() - start) * 1000, 1)

        if not res.get("isSuccess"):
            raise RuntimeError(f"Netris cluster creation failed: {res}")

        cluster_id = res.get("data", {}).get("id")
        self._log_event(
            "NETRIS_CLUSTER_READY",
            f"Server Cluster '{cluster_name}' provisioned (ID: {cluster_id}, {elapsed}ms)",
            {
                "cluster_id": cluster_id,
                "cluster_name": cluster_name,
                "node_count": len(server_list),
            },
        )
        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "elapsed_ms": elapsed,
            "servers": server_list,
        }

    def delete_server_cluster(self, cluster_id: int, cluster_name: str = "") -> bool:
        """Deprovisions a Netris Server Cluster, freeing its V-Net and assigned servers."""
        if self.sim_mode:
            for s in self._sim_servers:
                if s.get("serverClusterID") == cluster_id:
                    s["serverClusterID"] = None
            self._sim_clusters.pop(cluster_id, None)

            self._log_event(
                "NETRIS_CLUSTER_DELETE",
                f"[SIMULATION] DELETE /api/v2/server-cluster/{cluster_id} -> Deprovisioning '{cluster_name or cluster_id}'",
                {"cluster_id": cluster_id, "cluster_name": cluster_name},
            )
            self._log_event(
                "NETRIS_CLUSTER_REMOVED",
                f"[SIMULATION] Server Cluster '{cluster_name or cluster_id}' destroyed. 8 RoCEv2 rails freed.",
                {"cluster_id": cluster_id, "cluster_name": cluster_name},
            )
            return True

        self._log_event(
            "NETRIS_CLUSTER_DELETE",
            f"DELETE /api/v2/server-cluster/{cluster_id} -> Deprovisioning '{cluster_name or cluster_id}'",
            {"cluster_id": cluster_id, "cluster_name": cluster_name},
        )
        start = time.time()
        res = self._request("DELETE", f"/api/v2/server-cluster/{cluster_id}")
        elapsed = round((time.time() - start) * 1000, 1)

        if not res.get("isSuccess"):
            raise RuntimeError(f"Netris cluster deletion failed: {res}")

        self._log_event(
            "NETRIS_CLUSTER_REMOVED",
            f"Server Cluster '{cluster_name or cluster_id}' destroyed ({elapsed}ms). Nodes released.",
            {"cluster_id": cluster_id, "cluster_name": cluster_name},
        )
        return True

    def get_active_clusters(self) -> List[Dict[str, Any]]:
        """Queries the live list of Server Clusters configured in Netris."""
        if self.sim_mode:
            return copy.deepcopy(list(self._sim_clusters.values()))

        res = self._request("GET", "/api/v2/server-cluster")
        if not res.get("isSuccess"):
            return []
        return res.get("data", [])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    client = NetrisAPIClient()
    client.authenticate()
    print("Testing template check...")
    tmpl_id = client.ensure_slurm_template()
    print(f"Slurm template ID: {tmpl_id}")
    avail = client.get_available_servers()
    print(f"Available HGX servers: {len(avail)}")
    if avail:
        print(f"Sample servers: {[s['name'] for s in avail[:4]]}")
