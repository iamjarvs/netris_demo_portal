"""
netris_client.py
Communicates with Netris Controller REST API to fetch live state for pre-flight validation.
"""

import json
import urllib.request
import urllib.error
import http.cookiejar
from typing import Dict, Any, List, Optional


class NetrisClient:
    def __init__(self, controller_url: str, username: str = "netris", password: str = ""):
        self.controller_url = controller_url.rstrip("/")
        self.username = username
        self.password = password
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )
        self.authenticated = False

    def authenticate(self) -> Dict[str, Any]:
        """Authenticate with Netris Controller via /api/auth."""
        auth_url = f"{self.controller_url}/api/auth"
        payload = {
            "user": self.username,
            "password": self.password,
            "auth_scheme_id": 1,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            auth_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with self.opener.open(req, timeout=10) as resp:
                body = resp.read().decode("utf-8")
                res = json.loads(body)
                if resp.status == 200:
                    self.authenticated = True
                    return {
                        "success": True,
                        "message": "Authenticated successfully",
                        "user": res.get("data", {}).get("login", self.username),
                    }
                return {
                    "success": False,
                    "message": res.get("message", "Authentication failed"),
                }
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                msg = err_body.get("message", f"HTTP Error {e.code}")
            except Exception:
                msg = f"HTTP Error {e.code}: {e.reason}"
            return {"success": False, "message": msg}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _get(self, endpoint: str) -> Optional[Any]:
        """Send authenticated GET request to Netris API."""
        if not self.authenticated:
            auth_res = self.authenticate()
            if not auth_res["success"]:
                raise RuntimeError(auth_res["message"])

        url = f"{self.controller_url}{endpoint}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with self.opener.open(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("data", data)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            raise
        except Exception:
            return []

    def fetch_full_state(self) -> Dict[str, Any]:
        """Query controller for all relevant resources to check for conflicts."""
        sites = self._get("/api/v2/sites") or []
        allocations = self._get("/api/v2/ipam") or []
        subnets = self._get("/api/v2/ipam/subnets") or []
        hardware = self._get("/api/v2/hw") or []
        used_ips = self._get("/api/v2/hw/usedips") or []
        vnets = self._get("/api/v2/vnet") or []
        vpcs = self._get("/api/v2/vpc") or []
        ebgp = self._get("/api/v2/ebgp") or []
        profiles = self._get("/api/inventoryProfiles") or []

        # Extract ASNs
        asns = set()
        for site in sites:
            if isinstance(site, dict):
                if site.get("publicAsn"):
                    asns.add(int(site["publicAsn"]))
                if site.get("rohAsn") and site["rohAsn"] > 0:
                    asns.add(int(site["rohAsn"]))
                if site.get("vmAsn") and site["vmAsn"] > 0:
                    asns.add(int(site["vmAsn"]))

        for hw in hardware:
            if isinstance(hw, dict) and hw.get("asnumber"):
                try:
                    asns.add(int(hw["asnumber"]))
                except (ValueError, TypeError):
                    pass

        for peer in ebgp:
            if isinstance(peer, dict):
                if peer.get("local_asn"):
                    asns.add(int(peer["local_asn"]))
                if peer.get("remote_asn"):
                    asns.add(int(peer["remote_asn"]))

        # Extract names
        names = {
            "sites": [s.get("name") for s in sites if isinstance(s, dict) and s.get("name")],
            "switches": [
                h.get("name")
                for h in hardware
                if isinstance(h, dict) and h.get("type") == "switch" and h.get("name")
            ],
            "softgates": [
                h.get("name")
                for h in hardware
                if isinstance(h, dict) and h.get("type") == "softgate" and h.get("name")
            ],
            "servers": [
                h.get("name")
                for h in hardware
                if isinstance(h, dict) and h.get("type") == "server" and h.get("name")
            ],
            "vnets": [v.get("name") for v in vnets if isinstance(v, dict) and v.get("name")],
            "vpcs": [v.get("name") for v in vpcs if isinstance(v, dict) and v.get("name")],
            "profiles": [p.get("name") for p in profiles if isinstance(p, dict) and p.get("name")],
        }

        # Extract IP prefixes
        existing_allocations = []
        for a in allocations:
            if isinstance(a, dict) and a.get("prefix"):
                existing_allocations.append({
                    "id": a.get("id"),
                    "name": a.get("name", ""),
                    "prefix": a.get("prefix"),
                    "description": a.get("description", "")
                })

        existing_subnets = []
        for s in subnets:
            if isinstance(s, dict) and s.get("prefix"):
                existing_subnets.append({
                    "id": s.get("id"),
                    "name": s.get("name", ""),
                    "prefix": s.get("prefix"),
                    "purpose": s.get("purpose", ""),
                    "allocation_id": s.get("allocationID"),
                })

        return {
            "sites": sites,
            "allocations": existing_allocations,
            "subnets": existing_subnets,
            "hardware_count": len(hardware),
            "vnets_count": len(vnets),
            "vpcs": [{"id": v.get("id"), "name": v.get("name")} for v in vpcs if isinstance(v, dict)],
            "existing_asns": sorted(list(asns)),
            "existing_names": names,
            "used_ips_count": len(used_ips),
        }
