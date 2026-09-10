"""Prometheus Exporter for Netris Controller.

Collects telemetry from Netris REST APIs (Active Assurance health checks,
port states, BGP peerings, node health, topology validation), enriches them
with topological and tenant context, and exposes OpenMetrics on HTTP.
"""

from __future__ import annotations

import logging
import re
import sys
import time
from typing import Iterable

from prometheus_client import start_http_server
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, REGISTRY

from config import config
from enricher import NetrisEnricher
from netris_client import NetrisClient

logging.basicConfig(
    level=getattr(logging, config.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("netris_exporter")


def _str(val: any) -> str:
    """Safely convert any value (including dicts or None) to a string for Prometheus labels."""
    if val is None:
        return "none"
    if isinstance(val, dict):
        return str(val.get("name") or val.get("label") or val.get("id") or "unknown")
    return str(val)


class NetrisCollector:
    def __init__(self, client: NetrisClient, enricher: NetrisEnricher):
        self.client = client
        self.enricher = enricher

    def collect(self) -> Iterable:
        start_time = time.time()
        logger.info("Scraping Netris telemetry from %s...", self.client.base_url)

        # 1. Controller Reachability Metric
        up_metric = GaugeMetricFamily(
            "netris_up",
            "1 if Netris Controller is reachable and authenticated, 0 otherwise"
        )

        try:
            self.enricher.refresh()
            up_metric.add_metric([], 1)
            yield up_metric
        except Exception as e:
            logger.error("Netris scrape failed during metadata refresh: %s", e)
            up_metric.add_metric([], 0)
            yield up_metric
            return

        # 2. Hardware Fleet & Agent Heartbeats
        device_info = GaugeMetricFamily(
            "netris_device_info",
            "Information about managed network devices",
            labels=["site", "device_name", "device_role", "fabric_type", "nos"]
        )
        device_status = GaugeMetricFamily(
            "netris_device_status",
            "Operational status of managed network device (1 = OK, 0 = Problem)",
            labels=["site", "device_name", "device_role", "fabric_type"]
        )
        agent_heartbeat = GaugeMetricFamily(
            "netris_agent_heartbeat",
            "Status of Netris switch/softgate agent heartbeat (1 = Active, 0 = Inactive)",
            labels=["site", "device_name", "device_role", "fabric_type"]
        )

        try:
            hw_list = self.client.get_hardware()
            for hw in hw_list:
                dname = hw.get("name")
                if not dname:
                    continue
                dctx = self.enricher.get_device_context(dname)
                device_info.add_metric(
                    [_str(dctx["site"]), _str(dname), _str(dctx["device_role"]), _str(dctx["fabric_type"]), _str(dctx["nos"])],
                    1
                )
                is_ok = 1 if hw.get("status") == "ok" else 0
                device_status.add_metric(
                    [_str(dctx["site"]), _str(dname), _str(dctx["device_role"]), _str(dctx["fabric_type"])],
                    is_ok
                )

            heartbeats = self.client.get_agent_heartbeats()
            for hb in heartbeats:
                dname = hb.get("name")
                if not dname:
                    continue
                dctx = self.enricher.get_device_context(dname)
                hm = hb.get("healthMonitoring") or {}
                active = 1 if hm.get("port_status") == "ok" else 0
                agent_heartbeat.add_metric(
                    [_str(dctx["site"]), _str(dname), _str(dctx["device_role"]), _str(dctx["fabric_type"])],
                    active
                )

            yield device_info
            yield device_status
            yield agent_heartbeat

        except Exception as e:
            logger.error("Error collecting hardware inventory / heartbeats: %s", e)

        # 3. Active Assurance & Port Health Metrics
        port_status = GaugeMetricFamily(
            "netris_port_status",
            "Operational status of switch port (1 = UP, 0 = DOWN)",
            labels=[
                "site", "device_name", "device_role", "fabric_type", "port",
                "port_role", "remote_device", "remote_port", "remote_type",
                "tenant", "vpc", "server_cluster"
            ]
        )
        port_rx_util = GaugeMetricFamily(
            "netris_port_utilization_rx_percent",
            "Percentage of RX bandwidth utilization on switch port",
            labels=[
                "site", "device_name", "device_role", "fabric_type", "port",
                "port_role", "remote_device", "remote_port", "remote_type",
                "tenant", "vpc", "server_cluster"
            ]
        )
        port_tx_util = GaugeMetricFamily(
            "netris_port_utilization_tx_percent",
            "Percentage of TX bandwidth utilization on switch port",
            labels=[
                "site", "device_name", "device_role", "fabric_type", "port",
                "port_role", "remote_device", "remote_port", "remote_type",
                "tenant", "vpc", "server_cluster"
            ]
        )
        port_errors = GaugeMetricFamily(
            "netris_port_error_status",
            "Port error or drop status (1 = Error/Drops detected, 0 = Clean)",
            labels=[
                "site", "device_name", "device_role", "fabric_type", "port",
                "port_role", "remote_device", "remote_port", "remote_type"
            ]
        )
        bgp_session_state = GaugeMetricFamily(
            "netris_bgp_session_state",
            "BGP session operational state (1 = Established, 0 = Down/Other)",
            labels=["site", "device_name", "device_role", "port", "bgp_type", "peer_info"]
        )
        topology_wiring_valid = GaugeMetricFamily(
            "netris_topology_wiring_valid",
            "Cabling topology validation check (1 = Valid, 0 = Miswired/Inconsistent)",
            labels=["site", "device_name", "port", "message"]
        )

        # Node Hardware Metrics
        node_load_1m = GaugeMetricFamily(
            "netris_node_load_1m",
            "Node CPU 1-minute load average",
            labels=["site", "device_name", "device_role", "fabric_type"]
        )
        node_load_5m = GaugeMetricFamily(
            "netris_node_load_5m",
            "Node CPU 5-minute load average",
            labels=["site", "device_name", "device_role", "fabric_type"]
        )
        node_load_15m = GaugeMetricFamily(
            "netris_node_load_15m",
            "Node CPU 15-minute load average",
            labels=["site", "device_name", "device_role", "fabric_type"]
        )
        node_memory_used = GaugeMetricFamily(
            "netris_node_memory_used_percent",
            "Node RAM memory used percentage",
            labels=["site", "device_name", "device_role", "fabric_type"]
        )
        node_disk_used = GaugeMetricFamily(
            "netris_node_disk_used_percent",
            "Node disk storage used percentage",
            labels=["site", "device_name", "device_role", "fabric_type"]
        )
        node_component_status = GaugeMetricFamily(
            "netris_node_component_health",
            "Status of node subcomponent check (1 = OK, 0 = Failed/Warning)",
            labels=["site", "device_name", "device_role", "fabric_type", "check_name", "detail"]
        )

        try:
            health_devices = self.client.get_hardware_health()
            for dev in health_devices:
                dname = dev.get("name")
                site_name = _str(dev.get("site_name") or "Datacenter-A")
                dctx = self.enricher.get_device_context(dname)
                drole = dctx["device_role"]
                dfabric = dctx["fabric_type"]

                checks = dev.get("checks", [])
                for chk in checks:
                    check_name = chk.get("check_name")
                    status_str = chk.get("status", "ok")
                    msg = chk.get("message") or ""

                    # --- 1. Port Health & Optics ---
                    if check_name == "check_port":
                        port_name = chk.get("port")
                        if not port_name:
                            continue
                        pctx = self.enricher.get_port_context(dname, port_name)

                        is_up = 1 if "port is UP" in msg else 0
                        labels = [
                            _str(pctx.site_name), _str(pctx.device_name), _str(pctx.device_role),
                            _str(pctx.fabric_type), _str(pctx.port), _str(pctx.port_role),
                            _str(pctx.remote_device), _str(pctx.remote_port), _str(pctx.remote_type),
                            _str(pctx.tenant), _str(pctx.vpc), _str(pctx.server_cluster)
                        ]
                        port_status.add_metric(labels, is_up)

                        rx_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*RX", msg)
                        tx_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*TX", msg)
                        if rx_match:
                            port_rx_util.add_metric(labels, float(rx_match.group(1)))
                        if tx_match:
                            port_tx_util.add_metric(labels, float(tx_match.group(1)))

                        has_errors = 1 if ("in-errors:critical" in msg or "out-errors:critical" in msg or "drops:critical" in msg) else 0
                        port_errors.add_metric(
                            [
                                _str(pctx.site_name), _str(pctx.device_name), _str(pctx.device_role),
                                _str(pctx.fabric_type), _str(pctx.port), _str(pctx.port_role),
                                _str(pctx.remote_device), _str(pctx.remote_port), _str(pctx.remote_type)
                            ],
                            has_errors
                        )

                    # --- 2. Underlay / Fabric BGP ---
                    elif check_name in ("check_bgp", "check_bgp_underlay"):
                        port_name = chk.get("port") or "loopback"
                        is_est = 1 if ("Established" in msg or status_str == "ok") else 0
                        bgp_session_state.add_metric(
                            [site_name, _str(dname), drole, _str(port_name), "underlay", msg[:60]],
                            is_est
                        )

                    # --- 3. Topology / LLDP Cabling ---
                    elif check_name == "check_topology":
                        port_name = chk.get("port") or "all"
                        is_valid = 1 if status_str == "ok" else 0
                        topology_wiring_valid.add_metric(
                            [site_name, _str(dname), _str(port_name), msg[:80]],
                            is_valid
                        )

                    # --- 4. Node CPU Load ---
                    elif check_name == "check_load":
                        load_match = re.search(r"Load average\s+([\d\.]+),\s*([\d\.]+),\s*([\d\.]+)", msg)
                        if load_match:
                            node_load_1m.add_metric([site_name, _str(dname), drole, _str(dfabric)], float(load_match.group(1)))
                            node_load_5m.add_metric([site_name, _str(dname), drole, _str(dfabric)], float(load_match.group(2)))
                            node_load_15m.add_metric([site_name, _str(dname), drole, _str(dfabric)], float(load_match.group(3)))

                    # --- 5. Node Memory ---
                    elif check_name == "check_memory":
                        mem_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*Used", msg)
                        if mem_match:
                            node_memory_used.add_metric([site_name, _str(dname), drole, _str(dfabric)], float(mem_match.group(1)))

                    # --- 6. Node Disk ---
                    elif check_name == "check_disk":
                        disk_match = re.search(r"(\d+(?:\.\d+)?)\s*%", msg)
                        if disk_match:
                            node_disk_used.add_metric([site_name, _str(dname), drole, _str(dfabric)], float(disk_match.group(1)))

                    # --- 7. PSU, Fan, Temp, Services ---
                    elif check_name in ("check_psu", "check_fan", "check_temp", "check_frr", "sys_service", "xc_service", "xc_timesync"):
                        is_ok = 1 if status_str == "ok" else 0
                        brief = chk.get("ok_brief_message") or msg or check_name
                        node_component_status.add_metric(
                            [site_name, _str(dname), drole, _str(dfabric), check_name, brief[:40]],
                            is_ok
                        )

            yield port_status
            yield port_rx_util
            yield port_tx_util
            yield port_errors
            yield bgp_session_state
            yield topology_wiring_valid
            yield node_load_1m
            yield node_load_5m
            yield node_load_15m
            yield node_memory_used
            yield node_disk_used
            yield node_component_status

        except Exception as e:
            logger.error("Error collecting Active Assurance checks: %s", e)

        # 4. External BGP (E-BGP) Peering Telemetry
        ebgp_state = GaugeMetricFamily(
            "netris_ebgp_session_state",
            "External BGP neighbor state (1 = Established, 0 = Down)",
            labels=["site", "neighbor_name", "peer_ip", "peer_asn", "softgate", "vpc"]
        )
        ebgp_prefixes = GaugeMetricFamily(
            "netris_ebgp_prefixes_received",
            "Number of prefixes received from external BGP peer",
            labels=["site", "neighbor_name", "peer_ip", "peer_asn", "softgate", "vpc"]
        )

        try:
            ebgp_list = self.client.get_ebgp()
            for bgp in ebgp_list:
                name = bgp.get("name") or "unnamed"
                site = bgp.get("site_name") or "Datacenter-A"
                peer_ip = bgp.get("remoteIP") or bgp.get("remote_ip") or "unknown"
                peer_asn = str(bgp.get("neighborAS") or bgp.get("neighbor_as") or "0")
                sg = bgp.get("termSwName") or bgp.get("term_sw_name") or "softgate"
                vpc = (bgp.get("vpc") or {}).get("name") or "Default"

                state_str = bgp.get("bgpState") or bgp.get("bgp_state") or ""
                is_est = 1 if state_str.lower() == "established" else 0

                labels = [_str(site), _str(name), _str(peer_ip), _str(peer_asn), _str(sg), _str(vpc)]
                ebgp_state.add_metric(labels, is_est)

                try:
                    pfx_str = str(bgp.get("bgpPrefixes") or bgp.get("bgp_prefixes") or "0")
                    ebgp_prefixes.add_metric(labels, float(pfx_str))
                except (ValueError, TypeError):
                    ebgp_prefixes.add_metric(labels, 0)

            yield ebgp_state
            yield ebgp_prefixes

        except Exception as e:
            logger.error("Error collecting eBGP metrics: %s", e)

        # 5. IPAM Subnet Telemetry
        ipam_subnets = GaugeMetricFamily(
            "netris_ipam_subnet_info",
            "Configured IPAM subnets and purpose",
            labels=["site", "subnet_prefix", "purpose", "vpc", "tenant"]
        )
        try:
            subnets = self.client.get_ipam_subnets()
            for s in subnets:
                prefix = s.get("prefix") or "unknown"
                purpose = s.get("purpose") or "common"
                vpc = (s.get("vpc") or {}).get("name") or "Default"
                tenant = (s.get("tenant") or {}).get("name") or "Admin"
                sites = s.get("sites") or []
                s_name = sites[0].get("name") if sites else "Datacenter-A"

                ipam_subnets.add_metric([_str(s_name), _str(prefix), _str(purpose), _str(vpc), _str(tenant)], 1)

            yield ipam_subnets
        except Exception as e:
            logger.error("Error collecting IPAM subnets: %s", e)

        # 6. Streaming Interface Bandwidth & Telemetry (Netris Graphite Engine)
        if config.enable_streaming_traffic:
            traffic_rx_bps = GaugeMetricFamily(
                "netris_interface_receive_bits_per_second",
                "Instantaneous interface receive throughput in bits per second",
                labels=[
                    "site", "device_name", "device_role", "fabric_type", "port",
                    "port_role", "remote_device", "remote_port", "remote_type",
                    "tenant", "vpc", "server_cluster"
                ]
            )
            traffic_tx_bps = GaugeMetricFamily(
                "netris_interface_transmit_bits_per_second",
                "Instantaneous interface transmit throughput in bits per second",
                labels=[
                    "site", "device_name", "device_role", "fabric_type", "port",
                    "port_role", "remote_device", "remote_port", "remote_type",
                    "tenant", "vpc", "server_cluster"
                ]
            )
            traffic_rx_bytes = GaugeMetricFamily(
                "netris_interface_receive_bytes_per_second",
                "Instantaneous interface receive throughput in bytes per second",
                labels=[
                    "site", "device_name", "device_role", "fabric_type", "port",
                    "port_role", "remote_device", "remote_port", "remote_type",
                    "tenant", "vpc", "server_cluster"
                ]
            )
            traffic_tx_bytes = GaugeMetricFamily(
                "netris_interface_transmit_bytes_per_second",
                "Instantaneous interface transmit throughput in bytes per second",
                labels=[
                    "site", "device_name", "device_role", "fabric_type", "port",
                    "port_role", "remote_device", "remote_port", "remote_type",
                    "tenant", "vpc", "server_cluster"
                ]
            )

            try:
                graphite_series = self.client.get_graphite_metrics("collectd.*.interface-*.if_octets.*")
                target_re = re.compile(r"^collectd\.([^.]+)\.interface-([^.]+)\.if_octets\.(rx|tx)$")

                for item in graphite_series:
                    t_str = item.get("target", "")
                    m = target_re.match(t_str)
                    if not m:
                        continue
                    dev, port, direction = m.groups()
                    pts = item.get("datapoints", [])
                    val_bytes = 0.0
                    for p in reversed(pts):
                        if p[0] is not None:
                            val_bytes = float(p[0])
                            break

                    pctx = self.enricher.get_port_context(dev, port)
                    if config.streaming_traffic_active_only:
                        if val_bytes == 0.0 and pctx.port_role not in ("server_facing", "fabric_interconnect"):
                            continue

                    labels = [
                        _str(pctx.site_name), _str(dev), _str(pctx.device_role),
                        _str(pctx.fabric_type), _str(port), _str(pctx.port_role),
                        _str(pctx.remote_device), _str(pctx.remote_port), _str(pctx.remote_type),
                        _str(pctx.tenant), _str(pctx.vpc), _str(pctx.server_cluster)
                    ]

                    val_bits = val_bytes * 8.0
                    if direction == "rx":
                        traffic_rx_bytes.add_metric(labels, val_bytes)
                        traffic_rx_bps.add_metric(labels, val_bits)
                    else:
                        traffic_tx_bytes.add_metric(labels, val_bytes)
                        traffic_tx_bps.add_metric(labels, val_bits)

                yield traffic_rx_bytes
                yield traffic_tx_bytes
                yield traffic_rx_bps
                yield traffic_tx_bps
            except Exception as e:
                logger.error("Error collecting streaming traffic from Graphite: %s", e)

        duration = time.time() - start_time
        logger.info("Scrape completed in %.3f seconds.", duration)


def main():
    logger.info("Starting Netris Prometheus Exporter on %s:%d...", config.exporter_host, config.exporter_port)

    if config.simulation_mode:
        logger.info("=== SIMULATION MODE ACTIVE ===")
        logger.info("Replaying offline telemetry recording from: %s", config.sim_data_file)
        from sim_client import SimulatedNetrisClient
        client = SimulatedNetrisClient(data_file=config.sim_data_file)
    else:
        logger.info("=== LIVE MODE ACTIVE ===")
        logger.info("Connecting to live Netris Controller at: %s", config.netris_url)
        client = NetrisClient()
        if not client.login():
            logger.warning("Initial Netris login failed; exporter will retry on first scrape.")

    enricher = NetrisEnricher(client)
    collector = NetrisCollector(client, enricher)
    REGISTRY.register(collector)

    start_http_server(config.exporter_port, addr=config.exporter_host)
    logger.info("Netris Exporter is listening at http://%s:%d/metrics", config.exporter_host, config.exporter_port)

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
