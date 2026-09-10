"""Netris API client. Auth is cookie-based (POST /api/auth), not a bearer token, so
this wraps a requests.Session and transparently re-authenticates on a 401.
"""
import logging

import requests

logger = logging.getLogger(__name__)


class NetrisAPIError(Exception):
    """Raised instead of a bare requests.HTTPError so the actual reason Netris gave
    (e.g. {"errors": {"prefix": "IP prefix is out of any allocation"}}) shows up
    directly in the sync-service logs, instead of a generic "400 Client Error" that
    needs manually replaying the request to decode.
    """


class NetrisClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._authenticated = False

    def _login(self):
        resp = self.session.post(
            f"{self.base_url}/api/auth",
            json={"user": self.username, "password": self.password},
            timeout=15,
        )
        resp.raise_for_status()
        self._authenticated = True
        logger.info("Authenticated to Netris at %s", self.base_url)

    def _request(self, method, path, **kwargs):
        if not self._authenticated:
            self._login()
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, timeout=30, **kwargs)
        if resp.status_code == 401:
            logger.info("Netris session expired, re-authenticating")
            self._authenticated = False
            self._login()
            resp = self.session.request(method, url, timeout=30, **kwargs)
        self._raise_for_status(resp, method, path, kwargs.get("json"))
        return resp.json() if resp.content else None

    @staticmethod
    def _raise_for_status(resp, method, path, sent_body):
        if resp.ok:
            return
        detail = None
        try:
            payload = resp.json()
            detail = payload.get("errors") or payload.get("message")
        except ValueError:
            detail = resp.text[:500] if resp.text else None
        raise NetrisAPIError(
            f"{method} {path} -> HTTP {resp.status_code}: {detail!r} (sent: {sent_body!r})"
        )

    def get(self, path, **kwargs):
        return self._request("GET", path, **kwargs)

    def post(self, path, json=None, **kwargs):
        return self._request("POST", path, json=json, **kwargs)

    def put(self, path, json=None, **kwargs):
        return self._request("PUT", path, json=json, **kwargs)

    def delete(self, path, **kwargs):
        return self._request("DELETE", path, **kwargs)

    # --- IPAM ---
    def get_ipam_tree(self, vpc_ids=None):
        """Full allocation/subnet tree (nested), the source of truth for mirroring
        Netris's existing IPAM plan into NetBox.

        Without filterByVpc, this endpoint silently only returns the Default VPC's
        data - verified empirically (a real allocation in a non-default VPC was
        completely invisible until passed explicitly). Pass every known VPC id as a
        comma-separated list to get everything in one call.
        """
        params = {}
        if vpc_ids:
            params["filterByVpc"] = ",".join(str(v) for v in vpc_ids)
        data = self.get("/api/v2/ipam", params=params)
        return (data or {}).get("data", [])

    def list_reservations(self):
        data = self.get("/api/v2/reservation/ip")
        return (data or {}).get("data", [])

    def list_subnets(self):
        data = self.get("/api/v2/ipam/subnets")
        return (data or {}).get("data", [])

    def create_subnet(self, body):
        return self.post("/api/v2/ipam/subnet", json=body)

    def update_subnet(self, subnet_id, body):
        return self.put(f"/api/v2/ipam/subnet/{subnet_id}", json=body)

    def create_allocation(self, body):
        return self.post("/api/v2/ipam/allocation", json=body)

    def update_allocation(self, allocation_id, body):
        return self.put(f"/api/v2/ipam/allocation/{allocation_id}", json=body)

    def delete_subnet(self, subnet_id):
        """Cascade-deletes: verified empirically that deleting a subnet with hosts
        assigned removes those reservations too. Callers must check for that first if
        they don't want it to happen silently."""
        return self.delete(f"/api/v2/ipam/subnet/{subnet_id}")

    def delete_allocation(self, allocation_id):
        """Cascade-deletes: verified empirically that deleting an allocation with child
        subnets removes those subnets (and any hosts under them) too. Callers must
        check for that first if they don't want it to happen silently."""
        return self.delete(f"/api/v2/ipam/allocation/{allocation_id}")

    def list_vpcs(self):
        data = self.get("/api/v2/vpc")
        return (data or {}).get("data", [])

    def get_hw(self, hw_id):
        data = self.get(f"/api/v2/hw/{hw_id}")
        if not data:
            return None
        payload = data.get("data")
        if isinstance(payload, list):
            return payload[0] if payload else None
        return payload
