"""Data Enrichment Engine for Netris Metrics.

Maintains an in-memory cache of Netris topology, hardware inventory,
cabling links, VPCs, VNets, and Server Clusters to inject rich semantic
labels into raw Prometheus metrics.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from config import config
from netris_client import NetrisClient

logger = logging.getLogger("enricher")


@dataclass
class PortContext:
    device_name: str
    device_role: str
    fabric_type: str
    site_name: str
    port: str
    port_role: str = "unassigned"  # server_facing, fabric_interconnect, softgate_uplink, etc.
    remote_device: str = "unknown"
    remote_port: str = "unknown"
    remote_type: str = "unknown"   # server, switch, softgate
    tenant: str = "Admin"
    vpc: str = "none"
    server_cluster: str = "none"


class NetrisEnricher:
    def __init__(self, client: NetrisClient):
        self.client = client
        self.last_refresh: float = 0
        self.refresh_interval: int = config.metadata_refresh_interval

        # Lookup caches
        self.sites_by_id: dict[int, str] = {}
        self.hw_by_id: dict[int, dict] = {}
        self.hw_by_name: dict[str, dict] = {}
        self.port_context: dict[tuple[str, str], PortContext] = {}  # (device_name, port_name) -> PortContext
        self.servers_to_cluster: dict[str, str] = {}  # server_name -> cluster_name
        self.servers_to_vpc: dict[str, str] = {}      # server_name -> vpc_name
        self.vpcs_by_id: dict[int, str] = {}

    def refresh(self, force: bool = False) -> None:
        """Fetch fresh metadata from Netris and rebuild enrichment index."""
        now = time.time()
        if not force and (now - self.last_refresh < self.refresh_interval) and self.port_context:
            return

        logger.info("Refreshing Netris enrichment metadata...")
        try:
            sites = self.client.get_sites()
            hw_list = self.client.get_hardware()
            links = self.client.get_links()
            vpcs = self.client.get_vpcs()
            clusters = self.client.get_server_clusters()

            # Index Sites
            self.sites_by_id = {s["id"]: s.get("name", "unknown") for s in sites if "id" in s}

            # Index Hardware
            self.hw_by_id.clear()
            self.hw_by_name.clear()
            for h in hw_list:
                hid = h.get("id")
                name = h.get("name")
                if hid and name:
                    self.hw_by_id[hid] = h
                    self.hw_by_name[name] = h

            # Index VPCs
            self.vpcs_by_id = {v["id"]: v.get("name", "unknown") for v in vpcs if "id" in v}

            # Index Server Clusters
            self.servers_to_cluster.clear()
            self.servers_to_vpc.clear()
            for sc in clusters:
                cname = sc.get("name", "none")
                vpc_name = (sc.get("vpc") or {}).get("name", "none")
                for srv in sc.get("servers", []):
                    sname = srv.get("name")
                    if sname:
                        self.servers_to_cluster[sname] = cname
                        self.servers_to_vpc[sname] = vpc_name

            # Build Port Contexts reciprocally
            new_port_context: dict[tuple[str, str], PortContext] = {}

            for link in links:
                local = link.get("local") or {}
                remote = link.get("remote") or {}

                loc_hw = local.get("hardware") or {}
                rem_hw = remote.get("hardware") or {}

                loc_name = loc_hw.get("name")
                loc_port = local.get("port")
                loc_type = loc_hw.get("type") or "switch"

                rem_name = rem_hw.get("name")
                rem_port = remote.get("port")
                rem_type = rem_hw.get("type") or "unknown"

                if not loc_name or not loc_port:
                    continue

                # 1. Local Perspective
                loc_port_role = self._determine_port_role(rem_type, rem_name)
                loc_hw_meta = self.hw_by_name.get(loc_name, {})
                loc_site = self._extract_site_name(loc_hw_meta.get("site")) or "Datacenter-A"
                loc_cluster = self.servers_to_cluster.get(rem_name, "none")
                loc_vpc = self.servers_to_vpc.get(rem_name, "none")

                new_port_context[(loc_name, loc_port)] = PortContext(
                    device_name=loc_name,
                    device_role=self._determine_device_role(loc_name, loc_type),
                    fabric_type=self._determine_fabric_type(loc_name),
                    site_name=loc_site,
                    port=loc_port,
                    port_role=loc_port_role,
                    remote_device=rem_name or "unknown",
                    remote_port=rem_port or "unknown",
                    remote_type=rem_type,
                    tenant=loc_hw_meta.get("tenantName", "Admin"),
                    vpc=loc_vpc,
                    server_cluster=loc_cluster,
                )

                # 2. Reciprocal Remote Perspective (e.g. Spine seeing Leaf)
                if rem_name and rem_port:
                    rem_port_role = self._determine_port_role(loc_type, loc_name)
                    rem_hw_meta = self.hw_by_name.get(rem_name, {})
                    rem_site = self._extract_site_name(rem_hw_meta.get("site")) or loc_site
                    rem_cluster = self.servers_to_cluster.get(loc_name, "none")
                    rem_vpc = self.servers_to_vpc.get(loc_name, "none")

                    new_port_context[(rem_name, rem_port)] = PortContext(
                        device_name=rem_name,
                        device_role=self._determine_device_role(rem_name, rem_type),
                        fabric_type=self._determine_fabric_type(rem_name),
                        site_name=rem_site,
                        port=rem_port,
                        port_role=rem_port_role,
                        remote_device=loc_name,
                        remote_port=loc_port,
                        remote_type=loc_type,
                        tenant=rem_hw_meta.get("tenantName", "Admin"),
                        vpc=rem_vpc,
                        server_cluster=rem_cluster,
                    )

            self.port_context = new_port_context
            self.last_refresh = now
            logger.info("Enrichment metadata refreshed successfully. Indexed %d ports, %d devices.",
                        len(self.port_context), len(self.hw_by_id))

        except Exception as e:
            logger.error("Failed to refresh enrichment metadata: %s", e)

    def get_port_context(self, device_name: str, port_name: str) -> PortContext:
        """Retrieve contextual labels for a specific device and port."""
        if (device_name, port_name) in self.port_context:
            return self.port_context[(device_name, port_name)]

        # Fallback if port wasn't found in declared links
        hw_meta = self.hw_by_name.get(device_name, {})
        site_name = self._extract_site_name(hw_meta.get("site")) or "Datacenter-A"
        device_role = self._determine_device_role(device_name, hw_meta.get("type", "switch"))
        fabric_type = self._determine_fabric_type(device_name)

        return PortContext(
            device_name=device_name,
            device_role=device_role,
            fabric_type=fabric_type,
            site_name=site_name,
            port=port_name,
            tenant=hw_meta.get("tenantName", "Admin"),
        )

    def get_device_context(self, device_name: str) -> dict[str, str]:
        """Retrieve contextual labels for a device."""
        hw_meta = self.hw_by_name.get(device_name, {})
        site_name = self._extract_site_name(hw_meta.get("site")) or "Datacenter-A"
        device_role = self._determine_device_role(device_name, hw_meta.get("type", "switch"))
        fabric_type = self._determine_fabric_type(device_name)
        nos = (hw_meta.get("nos") or {}).get("tag") or "unknown"

        return {
            "site": site_name,
            "device_name": device_name,
            "device_role": device_role,
            "fabric_type": fabric_type,
            "nos": nos,
        }

    @staticmethod
    def _extract_site_name(site: Any) -> str:
        if isinstance(site, dict):
            return site.get("name") or "Datacenter-A"
        if isinstance(site, str) and site:
            return site
        return "Datacenter-A"

    @staticmethod
    def _determine_port_role(remote_type: str, remote_name: str | None) -> str:
        rname = (remote_name or "").lower()
        if remote_type == "server" or rname.startswith("hgx"):
            return "server_facing"
        if remote_type == "switch" or "spine" in rname or "leaf" in rname:
            return "fabric_interconnect"
        if remote_type == "softgate" or "softgate" in rname:
            return "softgate_uplink"
        return "network_link"

    @staticmethod
    def _determine_device_role(name: str, hw_type: str) -> str:
        name_lower = name.lower()
        if hw_type == "softgate" or name_lower.startswith("ns-softgate"):
            return "softgate"
        if hw_type == "server" or name_lower.startswith("hgx"):
            return "server"
        if "spine" in name_lower:
            return "spine"
        if "oob-leaf" in name_lower:
            return "oob_leaf"
        if "leaf" in name_lower:
            return "leaf"
        return hw_type or "switch"

    @staticmethod
    def _determine_fabric_type(name: str) -> str:
        name_lower = name.lower()
        if name_lower.startswith("ns-oob"):
            return "oob"
        if name_lower.startswith("ns-"):
            return "north_south"
        if "pod" in name_lower:
            return "east_west"
        return "general"
