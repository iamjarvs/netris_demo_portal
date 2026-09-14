"""
Netris REST API Client for Switch Isolation Testing.
Fetches VPCs, server clusters, server assignments, and switch topology mappings.
"""

import json
import ssl
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


class NetrisAPI:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.cookie: Optional[str] = None
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE

    def login(self) -> bool:
        """Authenticate with the Netris Controller via POST /api/auth."""
        url = f"{self.base_url}/api/auth"
        payload = json.dumps({
            "user": self.username,
            "password": self.password,
            "auth_scheme_id": 1
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, context=self._ctx, timeout=15)
            set_cookie = resp.headers.get("Set-Cookie")
            if set_cookie:
                self.cookie = set_cookie.split(";")[0]
                return True
            return False
        except Exception as e:
            raise RuntimeError(f"Failed to authenticate against Netris Controller: {e}") from e

    def _request(self, method: str, path: str, data: Optional[dict] = None) -> Any:
        if not self.cookie:
            self.login()

        url = f"{self.base_url}{path}"
        headers = {"Cookie": self.cookie}
        payload = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req, context=self._ctx, timeout=20)
            return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Re-login once and retry
                self.login()
                headers["Cookie"] = self.cookie
                req = urllib.request.Request(url, data=payload, headers=headers, method=method)
                resp = urllib.request.urlopen(req, context=self._ctx, timeout=20)
                return json.loads(resp.read().decode("utf-8"))
            raise RuntimeError(f"Netris API error ({e.code}) on {path}: {e}") from e

    def get_vpcs(self) -> List[Dict[str, Any]]:
        """Retrieve list of all active VPCs."""
        res = self._request("GET", "/api/v2/vpc")
        return res.get("data", [])

    def get_server_clusters(self) -> List[Dict[str, Any]]:
        """Retrieve all server clusters with their assigned VPCs and servers."""
        res = self._request("GET", "/api/v2/server-cluster")
        return res.get("data", [])

    def get_vnets(self) -> List[Dict[str, Any]]:
        """Retrieve all V-Nets."""
        res = self._request("GET", "/api/v2/vnet")
        return res.get("data", [])

    def get_hardware_inventory(self) -> List[Dict[str, Any]]:
        """Retrieve hardware switches, softgates, and devices."""
        res = self._request("GET", "/api/v2/hw")
        return res.get("data", [])

    def get_links(self) -> List[Dict[str, Any]]:
        """Retrieve physical and overlay links between switches and servers."""
        res = self._request("GET", "/api/v2/link")
        return res.get("data", [])

    def get_vpc_details(self, vpc_id: int) -> Dict[str, Any]:
        """
        Aggregates full details for a chosen VPC:
        - Cluster info
        - Member hosts
        - Associated V-Nets (East-West Pure VRF, North-South EVPN/VXLAN, OOB)
        - Connected switch links
        """
        clusters = self.get_server_clusters()
        matched_cluster = None
        for c in clusters:
            cVpc = c.get("vpc") or {}
            if cVpc.get("id") == vpc_id:
                matched_cluster = c
                break

        vnets = self.get_vnets()
        vpc_vnets = [v for v in vnets if (v.get("vpc") or {}).get("id") == vpc_id]

        servers = []
        if matched_cluster:
            servers = matched_cluster.get("servers", [])

        # Segregate V-Nets by fabric role
        east_west_vnet = next((v for v in vpc_vnets if "east-west" in v.get("name", "").lower()), None)
        north_south_vnet = next((v for v in vpc_vnets if "north-south" in v.get("name", "").lower()), None)
        oob_vnet = next((v for v in vpc_vnets if "oob" in v.get("name", "").lower()), None)

        return {
            "vpc_id": vpc_id,
            "cluster": matched_cluster,
            "servers": servers,
            "vnets": vpc_vnets,
            "east_west_vnet": east_west_vnet,
            "north_south_vnet": north_south_vnet,
            "oob_vnet": oob_vnet
        }

    def resolve_server_switch_links(self, server_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Finds all switch connections for the specified list of server names.
        Returns a map: server_name -> list of link dicts containing switch name, port, IP, and fabric role.
        """
        links_data = self.get_links()
        result: Dict[str, List[Dict[str, Any]]] = {s: [] for s in server_names}
        server_set = set(server_names)

        for l in links_data:
            local = l.get("local", {})
            remote = l.get("remote", {})
            local_hw = local.get("hardware", {})
            remote_hw = remote.get("hardware", {})

            # Check if remote is one of our servers and local is a switch
            if remote_hw.get("name") in server_set and local_hw.get("type") == "switch":
                sname = remote_hw.get("name")
                sw_name = local_hw.get("name")
                sw_port = local.get("port")
                host_port = remote.get("port")
                ip = local.get("ipv4")

                # Categorize fabric role
                role = "East-West (RoCE/GPU)" if "leaf-pod" in sw_name or "spine" in sw_name else "North-South"

                result[sname].append({
                    "switch_name": sw_name,
                    "switch_port": sw_port,
                    "host_port": host_port,
                    "ipv4": ip,
                    "fabric_role": role
                })

            # Check if local is one of our servers and remote is a switch
            elif local_hw.get("name") in server_set and remote_hw.get("type") == "switch":
                sname = local_hw.get("name")
                sw_name = remote_hw.get("name")
                sw_port = remote.get("port")
                host_port = local.get("port")
                ip = remote.get("ipv4")

                role = "East-West (RoCE/GPU)" if "leaf-pod" in sw_name or "spine" in sw_name else "North-South"

                result[sname].append({
                    "switch_name": sw_name,
                    "switch_port": sw_port,
                    "host_port": host_port,
                    "ipv4": ip,
                    "fabric_role": role
                })

        return result
