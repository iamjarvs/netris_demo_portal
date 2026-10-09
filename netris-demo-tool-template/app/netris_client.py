"""Canonical Netris API Client wrapper for demonstration tools."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import urllib3
import requests

logger = logging.getLogger("netris_client")


class NetrisAPIError(RuntimeError):
    """Raised when the Netris Controller API rejects a request."""

    def __init__(self, message: str, status_code: int = 500, payload: Any = None):
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.payload = payload


class NetrisClient:
    """Synchronous HTTP client for interacting with the Netris Controller API."""

    def __init__(
        self,
        host: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        verify: bool = False,
        timeout: float = 30.0,
    ):
        self.host = host.rstrip("/")
        self.session = requests.Session()
        self.session.verify = verify
        self.timeout = timeout

        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        if token:
            self.session.cookies.set("connect.sid", token)
        elif username and password:
            self.login(username, password)
        else:
            logger.warning("NetrisClient initialised without credentials; API calls may fail.")

    def login(self, username: str, password: str, auth_scheme_id: Optional[int] = None) -> None:
        """Authenticate against POST /api/auth and capture the session cookie."""
        url = f"{self.host}/api/auth"
        body: Dict[str, Any] = {"user": username, "password": password}
        if auth_scheme_id is not None:
            body["authSchemeID"] = auth_scheme_id

        try:
            resp = self.session.post(url, json=body, timeout=self.timeout)
        except requests.RequestException as exc:
            raise NetrisAPIError(f"Connection failure contacting {url}: {exc}") from exc

        if resp.status_code not in (200, 201):
            raise NetrisAPIError(
                f"Authentication failed for user '{username}'",
                status_code=resp.status_code,
                payload=resp.text,
            )

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute authenticated GET request."""
        path = endpoint.lstrip("/")
        url = f"{self.host}/{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        if not resp.ok:
            raise NetrisAPIError(f"GET {path} failed: {resp.text}", resp.status_code)
        return resp.json()

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Any:
        """Execute authenticated POST request."""
        path = endpoint.lstrip("/")
        url = f"{self.host}/{path}"
        resp = self.session.post(url, json=json_data, timeout=self.timeout)
        if not resp.ok:
            raise NetrisAPIError(f"POST {path} failed: {resp.text}", resp.status_code)
        return resp.json()

    def get_sites(self) -> List[Dict[str, Any]]:
        """Fetch all sites configured on the controller."""
        data = self.get("api/v2/sites")
        return data.get("data", []) if isinstance(data, dict) else data

    def get_inventory(self) -> List[Dict[str, Any]]:
        """Fetch all network switches and hardware nodes."""
        data = self.get("api/v2/switches")
        return data.get("data", []) if isinstance(data, dict) else data

    def get_vnets(self) -> List[Dict[str, Any]]:
        """Fetch all tenant V-Nets."""
        data = self.get("api/v2/vnet")
        return data.get("data", []) if isinstance(data, dict) else data
