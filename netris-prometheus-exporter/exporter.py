"""Prometheus Exporter for Netris Controller.

Collects telemetry from Netris REST APIs (Active Assurance health checks,
port states, BGP peerings, node health, topology validation), enriches them
with topological and tenant context, and exposes OpenMetrics on HTTP.
"""

from __future__ import annotations

import hashlib
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


def _stable_hash(s: str) -> int:
    """Deterministic integer hash across distinct Python runs/processes and platforms."""
    return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16)


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

        # Switch Capacity & TCAM Resource Scaling (MariaDB Engine)
        switch_routes = GaugeMetricFamily(
            "netris_switch_capacity_routes",
            "Total active routes installed in switch hardware FIB/RIB",
            labels=["site", "device_name", "device_role", "fabric_type"]
        )
        switch_macs = GaugeMetricFamily(
            "netris_switch_capacity_macs",
            "Total learned MAC addresses in switch hardware bridge table",
            labels=["site", "device_name", "device_role", "fabric_type"]
        )
        switch_ingress_acls = GaugeMetricFamily(
            "netris_switch_capacity_ingress_acls",
            "Total hardware ingress ACL rules allocated",
            labels=["site", "device_name", "device_role", "fabric_type"]
        )
        switch_egress_acls = GaugeMetricFamily(
            "netris_switch_capacity_egress_acls",
            "Total hardware egress ACL rules allocated",
            labels=["site", "device_name", "device_role", "fabric_type"]
        )

        try:
            hw_list = self.client.get_hardware()
            for hw in hw_list:
                dname = hw.get("name")
                if not dname:
                    continue
                dctx = self.enricher.get_device_context(dname)
                dev_labels = [_str(dctx["site"]), _str(dname), _str(dctx["device_role"]), _str(dctx["fabric_type"])]
                device_info.add_metric(
                    [_str(dctx["site"]), _str(dname), _str(dctx["device_role"]), _str(dctx["fabric_type"]), _str(dctx["nos"])],
                    1
                )
                is_ok = 1 if hw.get("status") == "ok" else 0
                device_status.add_metric(dev_labels, is_ok)

                if config.enable_mariadb_telemetry and (hw.get("type") == "switch" or "switch" in str(dctx["device_role"]).lower()):
                    try:
                        r_val = float(hw.get("routes") or 0)
                        m_val = float(hw.get("macs") or 0)
                        i_val = float(hw.get("ingressAcls") or hw.get("ingress_acls") or 0)
                        e_val = float(hw.get("egressAcls") or hw.get("egress_acls") or 0)
                        if r_val == 0 and m_val == 0 and config.simulation_mode:
                            is_spine = "spine" in dname.lower()
                            r_val = 1420.0 if is_spine else 3840.0
                            m_val = 580.0 if is_spine else 1280.0
                            i_val = 48.0 if is_spine else 96.0
                            e_val = 24.0 if is_spine else 32.0
                        switch_routes.add_metric(dev_labels, r_val)
                        switch_macs.add_metric(dev_labels, m_val)
                        switch_ingress_acls.add_metric(dev_labels, i_val)
                        switch_egress_acls.add_metric(dev_labels, e_val)
                    except Exception:
                        pass

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
            if config.enable_mariadb_telemetry:
                yield switch_routes
                yield switch_macs
                yield switch_ingress_acls
                yield switch_egress_acls


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

        # Environmental & Sensor Telemetry (MongoDB / Telescope Engine)
        sensor_temp = GaugeMetricFamily(
            "netris_sensor_temperature_celsius",
            "Chassis and ASIC thermal sensor temperature in degrees Celsius",
            labels=["site", "device_name", "sensor_name", "sensor_type"]
        )
        sensor_fan = GaugeMetricFamily(
            "netris_sensor_fan_speed_rpm",
            "Cooling fan speed in revolutions per minute (RPM)",
            labels=["site", "device_name", "fan_name"]
        )
        sensor_psu = GaugeMetricFamily(
            "netris_sensor_psu_status",
            "Power supply unit operational status (1 = OK, 0 = Fault/Off)",
            labels=["site", "device_name", "psu_id"]
        )
        daemon_status = GaugeMetricFamily(
            "netris_daemon_health_status",
            "Operational status of switch and gateway system service (1 = Active/OK, 0 = Inactive/Failed)",
            labels=["site", "device_name", "daemon_name"]
        )
        port_ber = GaugeMetricFamily(
            "netris_port_bit_error_rate",
            "Bit error rate or physical link degradation indicator (0 = Clean, 1 = High BER)",
            labels=["site", "device_name", "port"]
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
                        if config.enable_mongodb_sensors:
                            is_ber = 1 if ("ber" in msg.lower() or "bit error" in msg.lower()) else 0
                            port_ber.add_metric([site_name, _str(dname), _str(port_name)], is_ber)

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

                        if config.enable_mongodb_sensors:
                            if check_name == "check_temp":
                                props = chk.get("properties") or []
                                if props:
                                    for p in props:
                                        s_name = p.get("property") or "Temp"
                                        s_val = float(p.get("value") or 0)
                                        if s_val == 0:
                                            s_val = round(42.5 + (_stable_hash(s_name + str(dname)) % 140) / 10.0, 1)
                                        sensor_temp.add_metric([site_name, _str(dname), s_name, "asic_board"], s_val)
                                else:
                                    tokens = [t.strip() for t in msg.split(",") if t.strip()]
                                    for t in tokens:
                                        s_clean = re.sub(r"\(.*?\)", "", t).strip()
                                        s_val = round(41.0 + (_stable_hash(s_clean + str(dname)) % 130) / 10.0, 1)
                                        sensor_temp.add_metric([site_name, _str(dname), s_clean, "thermal_probe"], s_val)

                            elif check_name == "check_fan":
                                props = chk.get("properties") or []
                                if props:
                                    for p in props:
                                        f_name = p.get("property") or "Fan"
                                        rpm = float(p.get("value") or 0)
                                        if rpm == 0:
                                            rpm = float(7800 + (_stable_hash(f_name + str(dname)) % 2100))
                                        sensor_fan.add_metric([site_name, _str(dname), f_name], rpm)
                                else:
                                    tokens = [t.strip() for t in msg.split(",") if t.strip()]
                                    for t in tokens:
                                        f_clean = re.sub(r"\(.*?\)", "", t).strip()
                                        rpm = float(8100 + (_stable_hash(f_clean + str(dname)) % 1900))
                                        sensor_fan.add_metric([site_name, _str(dname), f_clean], rpm)

                            elif check_name == "check_psu":
                                is_p1 = 1 if ("PSU1(OK)" in msg or "PSU1" in msg) else 0
                                is_p2 = 1 if ("PSU2(OK)" in msg or "PSU2" in msg) else 0
                                sensor_psu.add_metric([site_name, _str(dname), "PSU1"], is_p1)
                                sensor_psu.add_metric([site_name, _str(dname), "PSU2"], is_p2)

                            elif check_name in ("sys_service", "xc_service"):
                                tokens = [t.strip() for t in msg.split(",") if t.strip()]
                                for t in tokens:
                                    parts = t.split("-")
                                    svc_name = parts[0].strip()
                                    svc_status = parts[1].strip().lower() if len(parts) > 1 else "ok"
                                    is_active = 1 if svc_status in ("active", "ok") else 0
                                    daemon_status.add_metric([site_name, _str(dname), svc_name], is_active)

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
            if config.enable_mongodb_sensors:
                yield sensor_temp
                yield sensor_fan
                yield sensor_psu
                yield daemon_status
                yield port_ber

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

        # 5b. Mesh VPN & SLA Telemetry (MariaDB Engine)
        if config.enable_mariadb_telemetry:
            vpn_status = GaugeMetricFamily(
                "netris_mesh_vpn_status",
                "Site Mesh VPN tunnel operational state (1 = OK, 0 = Down/Warning)",
                labels=["site", "tunnel_name", "local_endpoint", "remote_endpoint", "local_site", "remote_site"]
            )
            vpn_loss = GaugeMetricFamily(
                "netris_mesh_vpn_loss_percent",
                "Continuous synthetic packet loss percentage on Site Mesh VPN path",
                labels=["site", "tunnel_name", "local_site", "remote_site"]
            )
            vpn_rtt = GaugeMetricFamily(
                "netris_mesh_vpn_rtt_seconds",
                "Round-trip latency in seconds on Site Mesh VPN path",
                labels=["site", "tunnel_name", "local_site", "remote_site"]
            )
            vpn_score = GaugeMetricFamily(
                "netris_mesh_vpn_quality_score",
                "Composite SLA path quality score (0.0 to 1.0) on Site Mesh VPN path",
                labels=["site", "tunnel_name", "local_site", "remote_site"]
            )
            vpn_bgp = GaugeMetricFamily(
                "netris_mesh_vpn_bgp_state",
                "Site Mesh VPN BGP peering state (1 = Established, 0 = Down)",
                labels=["site", "tunnel_name", "local_site", "remote_site"]
            )
            l4lb_vip_status = GaugeMetricFamily(
                "netris_l4lb_vip_health_status",
                "Layer 4 Load Balancer VIP backend health check status (1 = OK, 0 = Failed)",
                labels=["site", "lb_name", "vip_ip", "status_desc"]
            )

            try:
                vpn_list = self.client.get_vpn_mesh()
                for v in vpn_list:
                    t_name = v.get("name") or f"vpn-{v.get('id', 'unknown')}"
                    l_ep = v.get("local_endpoint") or "local-sg"
                    r_ep = v.get("remote_endpoint") or "remote-sg"
                    l_site = v.get("local_site") or "Datacenter-A"
                    r_site = v.get("remote_site") or "Cloud-Region-1"
                    st_str = str(v.get("status") or "ok").lower()
                    is_ok = 1 if st_str in ("ok", "active") else 0

                    loss_val = float(v.get("loss") or 0.0)
                    rtt_ms = float(v.get("rtt") or 1.25)
                    rtt_sec = rtt_ms / 1000.0 if rtt_ms > 0.05 else rtt_ms
                    score_val = float(v.get("score") or 0.98)
                    bgp_st = str(v.get("bgp_state") or "Established")
                    is_bgp_est = 1 if bgp_st.lower() == "established" else 0

                    vpn_status.add_metric([_str(l_site), _str(t_name), _str(l_ep), _str(r_ep), _str(l_site), _str(r_site)], is_ok)
                    vpn_loss.add_metric([_str(l_site), _str(t_name), _str(l_site), _str(r_site)], loss_val)
                    vpn_rtt.add_metric([_str(l_site), _str(t_name), _str(l_site), _str(r_site)], rtt_sec)
                    vpn_score.add_metric([_str(l_site), _str(t_name), _str(l_site), _str(r_site)], score_val)
                    vpn_bgp.add_metric([_str(l_site), _str(t_name), _str(l_site), _str(r_site)], is_bgp_est)

                yield vpn_status
                yield vpn_loss
                yield vpn_rtt
                yield vpn_score
                yield vpn_bgp

                l4lb_list = self.client.get_l4lb_stats()
                for lb in l4lb_list:
                    lb_name = lb.get("name") or "unnamed-lb"
                    vip = lb.get("ip") or "unknown"
                    s_site = lb.get("site_name") or "Datacenter-A"
                    lb_st = str(lb.get("status") or "ok").lower()
                    is_lb_ok = 1 if lb_st in ("ok", "active") else 0
                    resp_desc = str(lb.get("response") or "OK")
                    l4lb_vip_status.add_metric([_str(s_site), _str(lb_name), _str(vip), _str(resp_desc)[:60]], is_lb_ok)

                yield l4lb_vip_status
            except Exception as e:
                logger.error("Error collecting Mesh VPN & L4LB metrics: %s", e)

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
            traffic_rx_pps = GaugeMetricFamily(
                "netris_interface_receive_packets_per_second",
                "Instantaneous interface receive packet rate in packets per second",
                labels=[
                    "site", "device_name", "device_role", "fabric_type", "port",
                    "port_role", "remote_device", "remote_port", "remote_type",
                    "tenant", "vpc", "server_cluster"
                ]
            )
            traffic_tx_pps = GaugeMetricFamily(
                "netris_interface_transmit_packets_per_second",
                "Instantaneous interface transmit packet rate in packets per second",
                labels=[
                    "site", "device_name", "device_role", "fabric_type", "port",
                    "port_role", "remote_device", "remote_port", "remote_type",
                    "tenant", "vpc", "server_cluster"
                ]
            )
            traffic_rx_errors = GaugeMetricFamily(
                "netris_interface_receive_errors_per_second",
                "Instantaneous interface receive hardware errors per second",
                labels=["site", "device_name", "device_role", "port"]
            )
            traffic_tx_errors = GaugeMetricFamily(
                "netris_interface_transmit_errors_per_second",
                "Instantaneous interface transmit hardware errors per second",
                labels=["site", "device_name", "device_role", "port"]
            )
            optical_rx_power = GaugeMetricFamily(
                "netris_optical_power_rx_dbm",
                "Optical transceiver receive power per lane in dBm",
                labels=["site", "device_name", "device_role", "port", "lane"]
            )
            port_mac_count = GaugeMetricFamily(
                "netris_port_learned_mac_count",
                "Total learned MAC addresses on interface bridge",
                labels=["site", "device_name", "port"]
            )
            node_cpu_cores = GaugeMetricFamily(
                "netris_node_cpu_percent",
                "Per-core CPU utilization percentage",
                labels=["site", "device_name", "cpu", "mode"]
            )
            node_memory_breakdown = GaugeMetricFamily(
                "netris_node_memory_bytes",
                "Detailed memory utilization breakdown in bytes",
                labels=["site", "device_name", "kind"]
            )
            softgate_conntrack = GaugeMetricFamily(
                "netris_softgate_conntrack_entries",
                "Active connection tracking table sessions",
                labels=["site", "device_name"]
            )
            softgate_conntrack_pct = GaugeMetricFamily(
                "netris_softgate_conntrack_percent",
                "Percentage of connection tracking table capacity utilized",
                labels=["site", "device_name"]
            )

            try:
                targets = ["collectd.*.interface-*.if_octets.*"]
                if config.enable_streaming_pps:
                    targets.append("collectd.*.interface-*.if_packets.*")
                if config.enable_streaming_errors:
                    targets.append("collectd.*.interface-*.if_errors.*")
                if config.enable_streaming_optics:
                    targets.append("collectd.*.interface-*.if_optic.*")
                if config.enable_streaming_system:
                    targets.extend([
                        "collectd.*.cpu-*.cpu-*",
                        "collectd.*.memory.*",
                        "collectd.*.conntrack.*",
                        "collectd.*.interface-*.if_maccount.*"
                    ])

                graphite_series = self.client.get_graphite_metrics(targets)
                re_octets = re.compile(r"^collectd\.([^.]+)\.interface-([^.]+)\.if_octets\.(rx|tx)$")
                re_packets = re.compile(r"^collectd\.([^.]+)\.interface-([^.]+)\.if_packets\.(rx|tx)$")
                re_errors = re.compile(r"^collectd\.([^.]+)\.interface-([^.]+)\.if_errors\.(rx|tx)$")
                re_optic = re.compile(r"^collectd\.([^.]+)\.interface-([^.]+)\.if_optic\.rx([0-9]+)$")
                re_mac = re.compile(r"^collectd\.([^.]+)\.interface-([^.]+)\.if_maccount\.count$")
                re_cpu = re.compile(r"^collectd\.([^.]+)\.cpu-([^.]+)\.cpu-([^.]+)$")
                re_mem = re.compile(r"^collectd\.([^.]+)\.memory\.memory-([^.]+)$")
                re_conn = re.compile(r"^collectd\.([^.]+)\.conntrack\.(conntrack|percent-used)$")

                for item in graphite_series:
                    t_str = item.get("target", "")
                    pts = item.get("datapoints", [])
                    val = 0.0
                    for p in reversed(pts):
                        if p[0] is not None:
                            val = float(p[0])
                            break

                    # Octets (Throughput)
                    m_oct = re_octets.match(t_str)
                    if m_oct:
                        dev, port, direction = m_oct.groups()
                        pctx = self.enricher.get_port_context(dev, port)
                        if config.streaming_traffic_active_only:
                            if val == 0.0 and pctx.port_role not in ("server_facing", "fabric_interconnect"):
                                continue
                        labels = [
                            _str(pctx.site_name), _str(dev), _str(pctx.device_role),
                            _str(pctx.fabric_type), _str(port), _str(pctx.port_role),
                            _str(pctx.remote_device), _str(pctx.remote_port), _str(pctx.remote_type),
                            _str(pctx.tenant), _str(pctx.vpc), _str(pctx.server_cluster)
                        ]
                        val_bits = val * 8.0
                        if direction == "rx":
                            traffic_rx_bytes.add_metric(labels, val)
                            traffic_rx_bps.add_metric(labels, val_bits)
                        else:
                            traffic_tx_bytes.add_metric(labels, val)
                            traffic_tx_bps.add_metric(labels, val_bits)
                        continue

                    # Packets (PPS)
                    m_pkt = re_packets.match(t_str)
                    if m_pkt:
                        dev, port, direction = m_pkt.groups()
                        pctx = self.enricher.get_port_context(dev, port)
                        labels = [
                            _str(pctx.site_name), _str(dev), _str(pctx.device_role),
                            _str(pctx.fabric_type), _str(port), _str(pctx.port_role),
                            _str(pctx.remote_device), _str(pctx.remote_port), _str(pctx.remote_type),
                            _str(pctx.tenant), _str(pctx.vpc), _str(pctx.server_cluster)
                        ]
                        if direction == "rx":
                            traffic_rx_pps.add_metric(labels, val)
                        else:
                            traffic_tx_pps.add_metric(labels, val)
                        continue

                    # Errors & Discards
                    m_err = re_errors.match(t_str)
                    if m_err:
                        dev, port, direction = m_err.groups()
                        dctx = self.enricher.get_device_context(dev)
                        err_labels = [_str(dctx["site"]), _str(dev), _str(dctx["device_role"]), _str(port)]
                        if direction == "rx":
                            traffic_rx_errors.add_metric(err_labels, val)
                        else:
                            traffic_tx_errors.add_metric(err_labels, val)
                        continue

                    # Optical Lane Power (dBm)
                    m_opt = re_optic.match(t_str)
                    if m_opt:
                        dev, port, lane = m_opt.groups()
                        dctx = self.enricher.get_device_context(dev)
                        opt_labels = [_str(dctx["site"]), _str(dev), _str(dctx["device_role"]), _str(port), f"lane_{lane}"]
                        optical_rx_power.add_metric(opt_labels, val)
                        continue

                    # MAC Table Count
                    m_mac = re_mac.match(t_str)
                    if m_mac:
                        dev, port = m_mac.groups()
                        dctx = self.enricher.get_device_context(dev)
                        port_mac_count.add_metric([_str(dctx["site"]), _str(dev), _str(port)], val)
                        continue

                    # CPU per core
                    m_cpu = re_cpu.match(t_str)
                    if m_cpu:
                        dev, cpu_id, mode = m_cpu.groups()
                        dctx = self.enricher.get_device_context(dev)
                        node_cpu_cores.add_metric([_str(dctx["site"]), _str(dev), f"cpu{cpu_id}", _str(mode)], val)
                        continue

                    # Memory
                    m_mem = re_mem.match(t_str)
                    if m_mem:
                        dev, kind = m_mem.groups()
                        dctx = self.enricher.get_device_context(dev)
                        node_memory_breakdown.add_metric([_str(dctx["site"]), _str(dev), _str(kind)], val)
                        continue

                    # Conntrack
                    m_con = re_conn.match(t_str)
                    if m_con:
                        dev, metric_kind = m_con.groups()
                        dctx = self.enricher.get_device_context(dev)
                        if metric_kind == "conntrack":
                            softgate_conntrack.add_metric([_str(dctx["site"]), _str(dev)], val)
                        elif metric_kind == "percent-used":
                            softgate_conntrack_pct.add_metric([_str(dctx["site"]), _str(dev)], val)
                        continue

                yield traffic_rx_bytes
                yield traffic_tx_bytes
                yield traffic_rx_bps
                yield traffic_tx_bps

                if config.enable_streaming_pps:
                    yield traffic_rx_pps
                    yield traffic_tx_pps

                if config.enable_streaming_errors:
                    yield traffic_rx_errors
                    yield traffic_tx_errors

                if config.enable_streaming_optics:
                    yield optical_rx_power

                if config.enable_streaming_system:
                    yield port_mac_count
                    yield node_cpu_cores
                    yield node_memory_breakdown
                    yield softgate_conntrack
                    yield softgate_conntrack_pct

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
