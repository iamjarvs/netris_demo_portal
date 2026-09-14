#!/usr/bin/env python3
"""Netris Multi-Database Grafana Dashboard Generator.

Generates 4 production-grade Grafana dashboards matching the three Netris database engines:
1. netris-fabric-overview.json: Unified Executive Fabric Observability (Default Home Dashboard)
2. netris-graphite-telemetry.json: Graphite Time-Series Performance, Packet Rates & Optics
3. netris-mariadb-state.json: MariaDB Relational State, Capacity Quotas & Multi-Site SLA
4. netris-mongodb-sensors.json: MongoDB Environmental, Thermal, Power & Telescope Sensors

Outputs JSON files to grafana/dashboards/json/ with schemaVersion 38.
"""

import json
import os
import sys

# Navigation banner HTML generator
def get_nav_banner(active_tab: str) -> str:
    tabs = [
        ("overview", "🏠 Fabric Overview", "/d/netris-fabric-overview"),
        ("graphite", "📊 Graphite Telemetry", "/d/netris-graphite-telemetry"),
        ("mariadb", "🗄️ MariaDB State & SLA", "/d/netris-mariadb-state"),
        ("mongodb", "🌡️ MongoDB Sensors", "/d/netris-mongodb-sensors"),
    ]
    
    tab_buttons = []
    for tab_id, label, url in tabs:
        if tab_id == active_tab:
            tab_buttons.append(
                f'<a href="{url}" style="text-decoration: none; background: #FF3366; color: #FFFFFF; '
                f'border: 1px solid #FF3366; padding: 6px 14px; border-radius: 6px; font-size: 12px; '
                f'font-weight: 700; box-shadow: 0 0 10px rgba(255, 51, 102, 0.4);">{label}</a>'
            )
        else:
            tab_buttons.append(
                f'<a href="{url}" style="text-decoration: none; background: rgba(255, 255, 255, 0.06); '
                f'color: #94A3B8; border: 1px solid rgba(255, 255, 255, 0.12); padding: 6px 14px; '
                f'border-radius: 6px; font-size: 12px; font-weight: 600; transition: all 0.2s;">{label}</a>'
            )
    
    tabs_html = " ".join(tab_buttons)
    
    subtitles = {
        "overview": "Unified Cross-Engine Fabric Observability &bull; Executive KPIs across Traffic, State &amp; Hardware",
        "graphite": "Graphite / Whisper Engine &bull; High-Frequency Streaming Traffic, Packet Rates, Optics dBm &amp; Conntrack",
        "mariadb": "MariaDB Relational Engine &bull; Forwarding State (FIB/MAC), TCAM Capacity, Multi-Site VPN Mesh &amp; L4LB",
        "mongodb": "MongoDB Telescope Engine &bull; Environmental Thermals (°C), Fan RPM, PSU Health, BER &amp; System Daemons",
    }
    
    subtitle = subtitles.get(active_tab, "Cloud-Native Datacenter &bull; AI Factory Networking")

    return f'''<div style="background: linear-gradient(135deg, #0A0D14 0%, #111827 50%, #1E293B 100%); border-left: 6px solid #FF3366; border-radius: 8px; padding: 14px 22px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 20px rgba(255, 51, 102, 0.15); border-top: 1px solid rgba(255, 51, 102, 0.25); border-right: 1px solid rgba(255, 255, 255, 0.05); border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
  <div style="display: flex; align-items: center; gap: 16px;">
    <div style="background: #FF3366; color: #FFFFFF; font-weight: 900; font-size: 16px; padding: 6px 14px; border-radius: 6px; letter-spacing: 1.5px; box-shadow: 0 0 15px rgba(255, 51, 102, 0.45); font-family: Inter, -apple-system, sans-serif;">
      NETRIS
    </div>
    <div>
      <div style="color: #FFFFFF; font-size: 18px; font-weight: 700; letter-spacing: 0.5px; display: flex; align-items: center; gap: 10px; font-family: Inter, -apple-system, sans-serif;">
        <span>FABRIC OBSERVABILITY</span>
        <span style="font-size: 11px; background: rgba(0, 163, 255, 0.15); color: #00D2FF; border: 1px solid rgba(0, 163, 255, 0.35); padding: 2px 8px; border-radius: 12px; font-weight: 600;">MULTI-DATABASE EDITION</span>
      </div>
      <div style="color: #94A3B8; font-size: 12px; margin-top: 2px;">
        {subtitle}
      </div>
    </div>
  </div>
  <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
    {tabs_html}
  </div>
</div>'''


def get_nav_links():
    return [
        {
            "asDropdown": False,
            "icon": "dashboard",
            "includeVars": True,
            "keepTime": True,
            "tags": ["netris"],
            "title": "Netris Observability Suite",
            "type": "dashboards"
        }
    ]


# ==============================================================================
# 1. UNIFIED FABRIC OVERVIEW (DEFAULT HOME DASHBOARD)
# ==============================================================================
def build_overview_dashboard():
    panels = [
        # Top Banner
        {
            "id": 999,
            "type": "text",
            "title": "",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 0},
            "options": {"mode": "html", "content": get_nav_banner("overview")},
            "transparent": True
        },
        # Row 100: Controller & Fleet Scale Overview
        {"id": 100, "title": "Netris Controller & Fabric Fleet Overview", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 3}},
        {
            "id": 1,
            "title": "Controller Reachability",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 0, "y": 4},
            "targets": [{"expr": "netris_up", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "mappings": [{"type": "value", "options": {"0": {"text": "DOWN", "color": "#FF3366"}, "1": {"text": "UP", "color": "#76B900"}}}],
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#76B900", "value": 1}]}
                }
            }
        },
        {
            "id": 2,
            "title": "Total Managed Switches",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 3, "y": 4},
            "targets": [{"expr": '(count(netris_device_info{fabric_type=~"${fabric_type:regex}", device_role=~"leaf|spine|oob_leaf"})) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },
        {
            "id": 3,
            "title": "Spine Switches",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 6, "y": 4},
            "targets": [{"expr": '(count(netris_device_info{fabric_type=~"${fabric_type:regex}", device_role="spine"})) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#A78BFA"}, "unit": "short"}}
        },
        {
            "id": 4,
            "title": "Leaf Switches",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 9, "y": 4},
            "targets": [{"expr": '(count(netris_device_info{fabric_type=~"${fabric_type:regex}", device_role=~"leaf|oob_leaf"})) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#38BDF8"}, "unit": "short"}}
        },
        {
            "id": 5,
            "title": "SoftGate Border Nodes",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 12, "y": 4},
            "targets": [{"expr": 'count(netris_device_info{fabric_type=~"${fabric_type:regex}", device_role="softgate"}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#FF9900"}, "unit": "short"}}
        },
        {
            "id": 6,
            "title": "HGX GPU Servers",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 15, "y": 4},
            "targets": [{"expr": 'count(netris_device_info{fabric_type=~"${fabric_type:regex}", device_role="server"}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#76B900"}, "unit": "short"}}
        },
        {
            "id": 7,
            "title": "East-West Bandwidth (Compute)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 18, "y": 4},
            "targets": [{"expr": 'sum(netris_interface_receive_bits_per_second{fabric_type="east_west"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#A78BFA"}, "unit": "bps"}}
        },
        {
            "id": 8,
            "title": "North-South Bandwidth (Border)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 21, "y": 4},
            "targets": [{"expr": 'sum(netris_interface_receive_bits_per_second{fabric_type="north_south"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00D2FF"}, "unit": "bps"}}
        },
        
        # Row 150: Tri-Engine Cross-Database Health & SLA Highlights
        {"id": 150, "title": "Tri-Engine Health & Multi-Site SLA Assurance (Graphite · MariaDB · MongoDB)", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 8}},
        {
            "id": 151,
            "title": "Multi-Site VPN SLA Score (MariaDB)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 4, "x": 0, "y": 9},
            "targets": [{"expr": "avg(netris_mesh_vpn_quality_score) or vector(100)", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "none",
                    "min": 0, "max": 100,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#FF9900", "value": 70}, {"color": "#76B900", "value": 90}]}
                }
            }
        },
        {
            "id": 152,
            "title": "Mesh Tunnel Latency RTT (MariaDB)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 4, "x": 4, "y": 9},
            "targets": [{"expr": "avg(netris_mesh_vpn_rtt_seconds) * 1000", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "ms",
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 30}, {"color": "#FF3366", "value": 60}]}
                }
            }
        },
        {
            "id": 153,
            "title": "Active SoftGate Conntrack (Graphite)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 4, "x": 8, "y": 9},
            "targets": [{"expr": "sum(netris_softgate_conntrack_entries)", "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#38BDF8"}, "unit": "short"}}
        },
        {
            "id": 154,
            "title": "Peak ASIC Temperature (MongoDB)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 4, "x": 12, "y": 9},
            "targets": [{"expr": 'max(netris_sensor_temperature_celsius{sensor_type="asic"}) or max(netris_sensor_temperature_celsius)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "celsius",
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 65}, {"color": "#FF3366", "value": 75}]}
                }
            }
        },
        {
            "id": 155,
            "title": "Signal Degradation Links (MongoDB)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 4, "x": 16, "y": 9},
            "targets": [{"expr": "(count(netris_port_bit_error_rate > 1e-12)) or vector(0)", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "short",
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF3366", "value": 1}]}
                }
            }
        },
        {
            "id": 156,
            "title": "Active L4LB VIPs (MariaDB)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 4, "x": 20, "y": 9},
            "targets": [{"expr": "(count(netris_l4lb_vip_health_status == 1)) or vector(0)", "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },

        # Row 200: Dual-Plane Traffic Separation
        {"id": 200, "title": "Dual-Plane Traffic Separation: East-West (Compute Mesh) vs North-South (Edge Border)", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 13}},
        {
            "id": 44,
            "title": "East-West Compute Mesh Throughput (RoCE / GPU / Leaf-Spine)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 14},
            "targets": [
                {"expr": 'sum by (device_role) (netris_interface_receive_bits_per_second{fabric_type="east_west"})', "legendFormat": "{{device_role}} (Ingress)", "refId": "A"},
                {"expr": 'sum by (device_role) (netris_interface_transmit_bits_per_second{fabric_type="east_west"})', "legendFormat": "{{device_role}} (Egress)", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 45,
            "title": "North-South Edge & Border Throughput (SoftGates / External Transits)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 14},
            "targets": [
                {"expr": 'sum by (device_role) (netris_interface_receive_bits_per_second{fabric_type="north_south"})', "legendFormat": "{{device_role}} (Ingress)", "refId": "A"},
                {"expr": 'sum by (device_role) (netris_interface_transmit_bits_per_second{fabric_type="north_south"})', "legendFormat": "{{device_role}} (Egress)", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 41,
            "title": "HGX GPU Server Downlink Bandwidth (East-West AI Cluster)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 22},
            "targets": [
                {"expr": 'sum by (server_cluster) (netris_interface_receive_bits_per_second{port_role="server_facing", server_cluster!="none"})', "legendFormat": "{{server_cluster}} Ingress", "refId": "A"},
                {"expr": 'sum by (server_cluster) (netris_interface_transmit_bits_per_second{port_role="server_facing", server_cluster!="none"})', "legendFormat": "{{server_cluster}} Egress", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 42,
            "title": "Spine Core Interlink Bandwidth (Fabric Backbone)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 22},
            "targets": [
                {"expr": 'sum by (device_name) (netris_interface_receive_bits_per_second{device_role="spine"})', "legendFormat": "{{device_name}} Ingress", "refId": "A"},
                {"expr": 'sum by (device_name) (netris_interface_transmit_bits_per_second{device_role="spine"})', "legendFormat": "{{device_name}} Egress", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },

        # Row 300: Hardware Telemetry & Node Resource Trends
        {"id": 300, "title": "Hardware Telemetry & Node Resource Trends (Filtered by Fabric Plane)", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 30}},
        {
            "id": 50,
            "title": "Switch / SoftGate CPU 1m Load Average Trends Over Time",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 31},
            "targets": [{"expr": 'netris_node_load_1m{fabric_type=~"${fabric_type:regex}"}', "legendFormat": "{{device_name}} ({{device_role}})", "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "short", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 51,
            "title": "Switch / SoftGate Memory (RAM) % Utilization Trends Over Time",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 31},
            "targets": [{"expr": 'netris_node_memory_used_percent{fabric_type=~"${fabric_type:regex}"}', "legendFormat": "{{device_name}} ({{device_role}})", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "unit": "percent",
                    "min": 0, "max": 100,
                    "color": {"mode": "thresholds"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 75}, {"color": "#FF3366", "value": 90}]}
                }
            }
        },
        {
            "id": 30,
            "title": "Instantaneous Node CPU Load",
            "type": "bargauge",
            "gridPos": {"h": 7, "w": 12, "x": 0, "y": 39},
            "targets": [{"expr": 'netris_node_load_1m{fabric_type=~"${fabric_type:regex}"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 2}, {"color": "#FF3366", "value": 4}]}
                }
            }
        },
        {
            "id": 31,
            "title": "Instantaneous Node Memory (RAM) % Used",
            "type": "bargauge",
            "gridPos": {"h": 7, "w": 12, "x": 12, "y": 39},
            "targets": [{"expr": 'netris_node_memory_used_percent{fabric_type=~"${fabric_type:regex}"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "percent",
                    "min": 0, "max": 100,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 75}, {"color": "#FF3366", "value": 90}]}
                }
            }
        },

        # Row 400: Fabric Assurance & Link Stability
        {"id": 400, "title": "Fabric Assurance, Continuous Active Validation & Link Stability", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 46}},
        {
            "id": 60,
            "title": "Interface Error & Drop Event Spikes Over Time",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 47},
            "targets": [
                {"expr": 'sum by (device_name) (netris_interface_receive_errors_per_second) > 0', "legendFormat": "{{device_name}} Ingress Errors", "refId": "A"},
                {"expr": 'sum by (device_name) (netris_interface_transmit_errors_per_second) > 0', "legendFormat": "{{device_name}} Egress Errors", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "pps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 10,
            "title": "Continuous Active Assurance: LLDP Cabling Validation",
            "type": "table",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 47},
            "targets": [{"expr": 'netris_topology_wiring_valid == 1', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [
                            {"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "MISWIRED", "color": "#FF3366"}, "1": {"text": "VERIFIED", "color": "#76B900"}}}]}
                        ]
                    }
                ]
            }
        },
        {
            "id": 11,
            "title": "External BGP (E-BGP) Peering Status (North-South Edge Transit)",
            "type": "table",
            "gridPos": {"h": 7, "w": 12, "x": 0, "y": 55},
            "targets": [{"expr": 'netris_ebgp_session_state', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [
                            {"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "DOWN", "color": "#FF3366"}, "1": {"text": "ESTABLISHED", "color": "#76B900"}}}]}
                        ]
                    }
                ]
            }
        },
        {
            "id": 32,
            "title": "Hardware Subcomponents Health (PSU, Fan, Temp, Services)",
            "type": "table",
            "gridPos": {"h": 7, "w": 12, "x": 12, "y": 55},
            "targets": [{"expr": 'netris_node_component_health{fabric_type=~"${fabric_type:regex}"}', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [
                            {"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "FAILED", "color": "#FF3366"}, "1": {"text": "HEALTHY", "color": "#76B900"}}}]}
                        ]
                    }
                ]
            }
        },

        # Row 500: Server Clusters & Enriched Port Telemetry
        {"id": 500, "title": "Server Clusters & Enriched Port Telemetry", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 62}},
        {
            "id": 20,
            "title": "Ports Enriched by Server Cluster",
            "type": "piechart",
            "gridPos": {"h": 8, "w": 6, "x": 0, "y": 63},
            "targets": [{"expr": 'count by (server_cluster) (netris_port_status{server_cluster!="none", fabric_type=~"${fabric_type:regex}"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}}}
        },
        {
            "id": 21,
            "title": "Server-Facing Ports (HGX GPU Links)",
            "type": "table",
            "gridPos": {"h": 8, "w": 18, "x": 6, "y": 63},
            "targets": [{"expr": 'netris_port_status{port_role="server_facing", fabric_type=~"${fabric_type:regex}"}', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [
                            {"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "DOWN", "color": "#FF3366"}, "1": {"text": "UP", "color": "#76B900"}}}]}
                        ]
                    }
                ]
            }
        }
    ]

    return {
        "annotations": {"list": []},
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": get_nav_links(),
        "liveNow": False,
        "refresh": "15s",
        "schemaVersion": 38,
        "style": "dark",
        "tags": ["netris", "fabric", "observability", "ai-factory", "east-west", "north-south", "overview"],
        "templating": {
            "list": [
                {
                    "name": "fabric_type",
                    "label": "Fabric Plane",
                    "type": "custom",
                    "query": "east_west : East-West (Compute / GPU Mesh), north_south : North-South (Border & SoftGates), oob : Out-of-Band (Management)",
                    "current": {"selected": True, "text": "All", "value": "$__all"},
                    "options": [
                        {"selected": True, "text": "All", "value": "$__all"},
                        {"selected": False, "text": "East-West (Compute / GPU Mesh)", "value": "east_west"},
                        {"selected": False, "text": "North-South (Border & SoftGates)", "value": "north_south"},
                        {"selected": False, "text": "Out-of-Band (Management)", "value": "oob"}
                    ],
                    "includeAll": True,
                    "multi": True,
                    "allValue": ".*"
                }
            ]
        },
        "time": {"from": "now-30m", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Netris Fabric Observability",
        "uid": "netris-fabric-overview",
        "version": 11,
        "panels": panels
    }


# ==============================================================================
# 2. GRAPHITE TIME-SERIES TELEMETRY DASHBOARD
# ==============================================================================
def build_graphite_dashboard():
    panels = [
        # Top Banner
        {
            "id": 999,
            "type": "text",
            "title": "",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 0},
            "options": {"mode": "html", "content": get_nav_banner("graphite")},
            "transparent": True
        },
        # Row 100: Traffic & Packet Flow Rates
        {"id": 100, "title": "Graphite Streaming Traffic & Packet Rate (PPS) Engine", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 3}},
        {
            "id": 101,
            "title": "Total Ingress Throughput",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 0, "y": 4},
            "targets": [{"expr": 'sum(netris_interface_receive_bits_per_second{fabric_type=~"${fabric_type:regex}"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "bps"}}
        },
        {
            "id": 102,
            "title": "Total Egress Throughput",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 6, "y": 4},
            "targets": [{"expr": 'sum(netris_interface_transmit_bits_per_second{fabric_type=~"${fabric_type:regex}"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#38BDF8"}, "unit": "bps"}}
        },
        {
            "id": 103,
            "title": "Total Ingress Packet Rate",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 12, "y": 4},
            "targets": [{"expr": 'sum(netris_interface_receive_packets_per_second{fabric_type=~"${fabric_type:regex}"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#A78BFA"}, "unit": "pps"}}
        },
        {
            "id": 104,
            "title": "Total Egress Packet Rate",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 18, "y": 4},
            "targets": [{"expr": 'sum(netris_interface_transmit_packets_per_second{fabric_type=~"${fabric_type:regex}"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#F472B6"}, "unit": "pps"}}
        },
        {
            "id": 105,
            "title": "Interface Throughput by Device (Bits/sec)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
            "targets": [
                {"expr": 'sum by (device_name) (netris_interface_receive_bits_per_second{device_name=~"$device_name", fabric_type=~"${fabric_type:regex}"})', "legendFormat": "{{device_name}} Ingress", "refId": "A"},
                {"expr": 'sum by (device_name) (netris_interface_transmit_bits_per_second{device_name=~"$device_name", fabric_type=~"${fabric_type:regex}"})', "legendFormat": "{{device_name}} Egress", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 106,
            "title": "Interface Packet Rates by Device (Packets/sec)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
            "targets": [
                {"expr": 'sum by (device_name) (netris_interface_receive_packets_per_second{device_name=~"$device_name", fabric_type=~"${fabric_type:regex}"})', "legendFormat": "{{device_name}} Ingress PPS", "refId": "A"},
                {"expr": 'sum by (device_name) (netris_interface_transmit_packets_per_second{device_name=~"$device_name", fabric_type=~"${fabric_type:regex}"})', "legendFormat": "{{device_name}} Egress PPS", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "pps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 107,
            "title": "Interface Discards & Errors per Second",
            "type": "timeseries",
            "gridPos": {"h": 7, "w": 12, "x": 0, "y": 16},
            "targets": [
                {"expr": 'sum by (device_name, port) (netris_interface_receive_errors_per_second{device_name=~"$device_name"}) > 0', "legendFormat": "{{device_name}} {{port}} RX Errors", "refId": "A"},
                {"expr": 'sum by (device_name, port) (netris_interface_transmit_errors_per_second{device_name=~"$device_name"}) > 0', "legendFormat": "{{device_name}} {{port}} TX Errors", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "pps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 108,
            "title": "Top Links by RX/TX Bandwidth Utilization %",
            "type": "table",
            "gridPos": {"h": 7, "w": 12, "x": 12, "y": 16},
            "targets": [{"expr": 'topk(15, netris_port_utilization_rx_percent{device_name=~"$device_name"})', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "percent"}}
        },

        # Row 200: Optical Physical Layer Transceiver Telemetry
        {"id": 200, "title": "Optical Transceiver Physical Layer Telemetry (dBm & Laser Bias)", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 23}},
        {
            "id": 201,
            "title": "Minimum Optical RX Power",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 0, "y": 24},
            "targets": [{"expr": 'min(netris_optical_power_rx_dbm{device_name=~"$device_name"})', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "dBm",
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#FF9900", "value": -14}, {"color": "#76B900", "value": -10}]}
                }
            }
        },
        {
            "id": 202,
            "title": "Total Monitored Optical Lanes",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 6, "y": 24},
            "targets": [{"expr": 'count(netris_optical_power_rx_dbm{device_name=~"$device_name"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },
        {
            "id": 203,
            "title": "Optical Power RX (dBm) Trends Across Lanes",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24},
            "targets": [{"expr": 'netris_optical_power_rx_dbm{device_name=~"$device_name"}', "legendFormat": "{{device_name}} {{port}} [{{lane}}]", "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "dBm", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 204,
            "title": "Transceiver Optical Power Diagnostic Audit",
            "type": "table",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 28},
            "targets": [{"expr": 'netris_optical_power_rx_dbm{device_name=~"$device_name"}', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "dBm"}}
        },

        # Row 300: Compute Telemetry & SoftGate Conntrack
        {"id": 300, "title": "Switch & SoftGate Compute Telemetry & NAT Connection Tracking", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 36}},
        {
            "id": 301,
            "title": "Per-Core CPU Utilization Breakdown (%)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 37},
            "targets": [
                {"expr": 'netris_node_cpu_percent{device_name=~"$device_name", mode!="idle"}', "legendFormat": "{{device_name}} {{cpu}} ({{mode}})", "refId": "A"}
            ],
            "fieldConfig": {"defaults": {"unit": "percent", "min": 0, "max": 100, "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 302,
            "title": "System Memory Breakdown (Bytes)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 37},
            "targets": [
                {"expr": 'netris_node_memory_bytes{device_name=~"$device_name"}', "legendFormat": "{{device_name}} ({{kind}})", "refId": "A"}
            ],
            "fieldConfig": {"defaults": {"unit": "bytes", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 303,
            "title": "SoftGate Active Conntrack Sessions",
            "type": "timeseries",
            "gridPos": {"h": 7, "w": 12, "x": 0, "y": 45},
            "targets": [{"expr": 'netris_softgate_conntrack_entries', "legendFormat": "{{device_name}} Sessions", "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "short", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 304,
            "title": "SoftGate Conntrack Table Utilization %",
            "type": "bargauge",
            "gridPos": {"h": 7, "w": 12, "x": 12, "y": 45},
            "targets": [{"expr": 'netris_softgate_conntrack_percent', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "percent",
                    "min": 0, "max": 100,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 65}, {"color": "#FF3366", "value": 85}]}
                }
            }
        }
    ]

    return {
        "annotations": {"list": []},
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": get_nav_links(),
        "liveNow": False,
        "refresh": "15s",
        "schemaVersion": 38,
        "style": "dark",
        "tags": ["netris", "graphite", "telemetry", "optics", "traffic", "conntrack"],
        "templating": {
            "list": [
                {
                    "name": "fabric_type",
                    "label": "Fabric Plane",
                    "type": "custom",
                    "query": "east_west : East-West (Compute / GPU Mesh), north_south : North-South (Border & SoftGates), oob : Out-of-Band (Management)",
                    "current": {"selected": True, "text": "All", "value": "$__all"},
                    "options": [
                        {"selected": True, "text": "All", "value": "$__all"},
                        {"selected": False, "text": "East-West (Compute / GPU Mesh)", "value": "east_west"},
                        {"selected": False, "text": "North-South (Border & SoftGates)", "value": "north_south"},
                        {"selected": False, "text": "Out-of-Band (Management)", "value": "oob"}
                    ],
                    "includeAll": True,
                    "multi": True,
                    "allValue": ".*"
                },
                {
                    "name": "device_name",
                    "label": "Device",
                    "type": "query",
                    "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "definition": 'label_values(netris_device_info{fabric_type=~"${fabric_type:regex}"}, device_name)',
                    "query": {
                        "query": 'label_values(netris_device_info{fabric_type=~"${fabric_type:regex}"}, device_name)',
                        "refId": "StandardVariableQuery"
                    },
                    "refresh": 1,
                    "sort": 1,
                    "includeAll": True,
                    "multi": True,
                    "allValue": ".*",
                    "current": {"selected": True, "text": "All", "value": "$__all"}
                }
            ]
        },
        "time": {"from": "now-30m", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Netris - Graphite Time-Series Engine (Performance & Optics)",
        "uid": "netris-graphite-telemetry",
        "version": 1,
        "panels": panels
    }


# ==============================================================================
# 3. MARIADB RELATIONAL STATE & SLA DASHBOARD
# ==============================================================================
def build_mariadb_dashboard():
    panels = [
        # Top Banner
        {
            "id": 999,
            "type": "text",
            "title": "",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 0},
            "options": {"mode": "html", "content": get_nav_banner("mariadb")},
            "transparent": True
        },
        # Row 100: Multi-Site Netris VPC & VPN Mesh SLA Assurance
        {"id": 100, "title": "Multi-Site Netris VPC & VPN Mesh SLA Assurance", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 3}},
        {
            "id": 101,
            "title": "Active VPN Mesh Tunnels",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 0, "y": 4},
            "targets": [{"expr": 'count(netris_mesh_vpn_status == 1) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#76B900"}, "unit": "short"}}
        },
        {
            "id": 102,
            "title": "Average Mesh SLA Quality Score",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 6, "y": 4},
            "targets": [{"expr": 'avg(netris_mesh_vpn_quality_score) or vector(100)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "none",
                    "min": 0, "max": 100,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#FF9900", "value": 70}, {"color": "#76B900", "value": 90}]}
                }
            }
        },
        {
            "id": 103,
            "title": "Average Round-Trip Latency (RTT)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 12, "y": 4},
            "targets": [{"expr": 'avg(netris_mesh_vpn_rtt_seconds) * 1000', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "ms",
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 30}, {"color": "#FF3366", "value": 60}]}
                }
            }
        },
        {
            "id": 104,
            "title": "Average Mesh Packet Loss %",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 18, "y": 4},
            "targets": [{"expr": 'avg(netris_mesh_vpn_loss_percent)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "percent",
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 0.5}, {"color": "#FF3366", "value": 2.0}]}
                }
            }
        },
        {
            "id": 105,
            "title": "Multi-Site VPN SLA Quality Score Over Time (0-100)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 8, "x": 0, "y": 8},
            "targets": [{"expr": 'netris_mesh_vpn_quality_score', "legendFormat": "{{tunnel_name}} ({{local_site}} ↔ {{remote_site}})", "refId": "A"}],
            "fieldConfig": {"defaults": {"min": 0, "max": 100, "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 106,
            "title": "Multi-Site VPN Round-Trip Latency (ms)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 8, "x": 8, "y": 8},
            "targets": [{"expr": 'netris_mesh_vpn_rtt_seconds * 1000', "legendFormat": "{{tunnel_name}} (RTT ms)", "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "ms", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 107,
            "title": "Multi-Site VPN Packet Loss Rate (%)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 8, "x": 16, "y": 8},
            "targets": [{"expr": 'netris_mesh_vpn_loss_percent', "legendFormat": "{{tunnel_name}} Loss %", "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "percent", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 108,
            "title": "Multi-Site Mesh Tunnel Inventory & Underlay Peering Status",
            "type": "table",
            "gridPos": {"h": 6, "w": 24, "x": 0, "y": 16},
            "targets": [{"expr": 'netris_mesh_vpn_status', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [
                            {"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "DOWN", "color": "#FF3366"}, "1": {"text": "ACTIVE", "color": "#76B900"}}}]}
                        ]
                    }
                ]
            }
        },

        # Row 200: Forwarding State & TCAM Capacity Quotas
        {"id": 200, "title": "Hardware Forwarding State (FIB) & TCAM Capacity Quotas", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 22}},
        {
            "id": 201,
            "title": "Switch Hardware FIB Route Capacity Used",
            "type": "bargauge",
            "gridPos": {"h": 7, "w": 6, "x": 0, "y": 23},
            "targets": [{"expr": 'netris_switch_capacity_routes{device_name=~"$device_name"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#38BDF8"}, "unit": "short"}}
        },
        {
            "id": 202,
            "title": "Switch Hardware Bridge MAC Capacity Used",
            "type": "bargauge",
            "gridPos": {"h": 7, "w": 6, "x": 6, "y": 23},
            "targets": [{"expr": 'netris_switch_capacity_macs{device_name=~"$device_name"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },
        {
            "id": 203,
            "title": "TCAM Ingress ACL Quota Used",
            "type": "bargauge",
            "gridPos": {"h": 7, "w": 6, "x": 12, "y": 23},
            "targets": [{"expr": 'netris_switch_capacity_ingress_acls{device_name=~"$device_name"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#A78BFA"}, "unit": "short"}}
        },
        {
            "id": 204,
            "title": "TCAM Egress ACL Quota Used",
            "type": "bargauge",
            "gridPos": {"h": 7, "w": 6, "x": 18, "y": 23},
            "targets": [{"expr": 'netris_switch_capacity_egress_acls{device_name=~"$device_name"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#F472B6"}, "unit": "short"}}
        },
        {
            "id": 205,
            "title": "Switch Hardware Resource Allocation Matrix",
            "type": "table",
            "gridPos": {"h": 8, "w": 24, "x": 0, "y": 30},
            "targets": [{"expr": 'netris_switch_capacity_routes{device_name=~"$device_name"}', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "short"}}
        },

        # Row 300: L4 Load Balancers & IPAM Subnets
        {"id": 300, "title": "Layer-4 Load Balancer (L4LB) Services & IPAM Subnet Allocations", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 38}},
        {
            "id": 301,
            "title": "Active L4LB Virtual IPs (VIPs)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 0, "y": 39},
            "targets": [{"expr": 'count(netris_l4lb_vip_health_status == 1) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#76B900"}, "unit": "short"}}
        },
        {
            "id": 302,
            "title": "Allocated IPAM Subnets",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 6, "y": 39},
            "targets": [{"expr": 'count(netris_ipam_subnet_info) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },
        {
            "id": 303,
            "title": "Layer-4 Load Balancer (L4LB) VIP State & Health",
            "type": "table",
            "gridPos": {"h": 7, "w": 12, "x": 12, "y": 39},
            "targets": [{"expr": 'netris_l4lb_vip_health_status', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [
                            {"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "DEGRADED", "color": "#FF3366"}, "1": {"text": "HEALTHY", "color": "#76B900"}}}]}
                        ]
                    }
                ]
            }
        },
        {
            "id": 304,
            "title": "Fabric IPAM Subnet Inventory & VPC Allocations",
            "type": "table",
            "gridPos": {"h": 7, "w": 12, "x": 0, "y": 43},
            "targets": [{"expr": 'netris_ipam_subnet_info', "format": "table", "instant": True, "refId": "A"}]
        },
        {
            "id": 305,
            "title": "Port Configuration & Remote Topology Links",
            "type": "table",
            "gridPos": {"h": 7, "w": 12, "x": 12, "y": 46},
            "targets": [{"expr": 'topk(20, netris_port_status{device_name=~"$device_name"})', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [
                            {"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "DOWN", "color": "#FF3366"}, "1": {"text": "UP", "color": "#76B900"}}}]}
                        ]
                    }
                ]
            }
        }
    ]

    return {
        "annotations": {"list": []},
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": get_nav_links(),
        "liveNow": False,
        "refresh": "15s",
        "schemaVersion": 38,
        "style": "dark",
        "tags": ["netris", "mariadb", "state", "vpn", "sla", "tcam", "fib", "l4lb"],
        "templating": {
            "list": [
                {
                    "name": "site",
                    "label": "Site",
                    "type": "query",
                    "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "definition": "label_values(netris_device_info, site)",
                    "query": {
                        "query": "label_values(netris_device_info, site)",
                        "refId": "StandardVariableQuery"
                    },
                    "refresh": 1,
                    "sort": 1,
                    "includeAll": True,
                    "multi": True,
                    "allValue": ".*",
                    "current": {"selected": True, "text": "All", "value": "$__all"}
                },
                {
                    "name": "device_name",
                    "label": "Device",
                    "type": "query",
                    "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "definition": 'label_values(netris_device_info{site=~"$site"}, device_name)',
                    "query": {
                        "query": 'label_values(netris_device_info{site=~"$site"}, device_name)',
                        "refId": "StandardVariableQuery"
                    },
                    "refresh": 1,
                    "sort": 1,
                    "includeAll": True,
                    "multi": True,
                    "allValue": ".*",
                    "current": {"selected": True, "text": "All", "value": "$__all"}
                }
            ]
        },
        "time": {"from": "now-30m", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Netris - MariaDB Relational State & SLA Assurance",
        "uid": "netris-mariadb-state",
        "version": 1,
        "panels": panels
    }


# ==============================================================================
# 4. MONGODB ENVIRONMENTAL & SENSOR DASHBOARD
# ==============================================================================
def build_mongodb_dashboard():
    panels = [
        # Top Banner
        {
            "id": 999,
            "type": "text",
            "title": "",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 0},
            "options": {"mode": "html", "content": get_nav_banner("mongodb")},
            "transparent": True
        },
        # Row 100: Environmental Thermal Management & Active Cooling
        {"id": 100, "title": "Environmental Thermal Management & Active Cooling Telemetry", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 3}},
        {
            "id": 101,
            "title": "Peak ASIC Temperature (°C)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 0, "y": 4},
            "targets": [{"expr": 'max(netris_sensor_temperature_celsius{sensor_type="asic"}) or max(netris_sensor_temperature_celsius)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "celsius",
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 65}, {"color": "#FF3366", "value": 75}]}
                }
            }
        },
        {
            "id": 102,
            "title": "Average Chassis Temperature (°C)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 6, "y": 4},
            "targets": [{"expr": 'avg(netris_sensor_temperature_celsius)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "celsius",
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 50}, {"color": "#FF3366", "value": 65}]}
                }
            }
        },
        {
            "id": 103,
            "title": "Average Fan Speed (RPM)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 12, "y": 4},
            "targets": [{"expr": 'avg(netris_sensor_fan_speed_rpm)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#38BDF8"}, "unit": "rotrpm"}}
        },
        {
            "id": 104,
            "title": "Active Telescope Daemon Agents",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 18, "y": 4},
            "targets": [{"expr": 'count(netris_agent_heartbeat == 1) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },
        {
            "id": 105,
            "title": "Thermal Sensor Trends (°C) across ASIC, Intake & Exhaust",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
            "targets": [{"expr": 'netris_sensor_temperature_celsius{device_name=~"$device_name"}', "legendFormat": "{{device_name}} ({{sensor_name}})", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "unit": "celsius",
                    "color": {"mode": "palette-classic"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 65}, {"color": "#FF3366", "value": 75}]}
                }
            }
        },
        {
            "id": 106,
            "title": "Fan Tray Tachometer Speeds (RPM) Over Time",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
            "targets": [{"expr": 'netris_sensor_fan_speed_rpm{device_name=~"$device_name"}', "legendFormat": "{{device_name}} ({{fan_name}})", "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "rotrpm", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 107,
            "title": "Instantaneous Temperature Readings by Sensor (°C)",
            "type": "bargauge",
            "gridPos": {"h": 7, "w": 24, "x": 0, "y": 16},
            "targets": [{"expr": 'netris_sensor_temperature_celsius{device_name=~"$device_name"}', "legendFormat": "{{device_name}} - {{sensor_name}}", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "unit": "celsius",
                    "color": {"mode": "thresholds"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 60}, {"color": "#FF3366", "value": 75}]}
                }
            }
        },

        # Row 200: Power Supply Units (PSU) & Hardware Subcomponents
        {"id": 200, "title": "Power Supply Units (PSU) & Hardware Subcomponent Diagnostics", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 23}},
        {
            "id": 201,
            "title": "Monitored PSUs",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 0, "y": 24},
            "targets": [{"expr": 'count(netris_sensor_psu_status{device_name=~"$device_name"}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#38BDF8"}, "unit": "short"}}
        },
        {
            "id": 202,
            "title": "Healthy PSUs",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 6, "y": 24},
            "targets": [{"expr": 'count(netris_sensor_psu_status{device_name=~"$device_name"} == 1) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#76B900"}, "unit": "short"}}
        },
        {
            "id": 203,
            "title": "Power Supply Unit (PSU) Status Matrix",
            "type": "table",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24},
            "targets": [{"expr": 'netris_sensor_psu_status{device_name=~"$device_name"}', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [
                            {"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "FAILED", "color": "#FF3366"}, "1": {"text": "OK", "color": "#76B900"}}}]}
                        ]
                    }
                ]
            }
        },
        {
            "id": 204,
            "title": "Hardware Subsystem Component Health Audit",
            "type": "table",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 28},
            "targets": [{"expr": 'netris_node_component_health{device_name=~"$device_name"}', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [
                            {"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "ALARM", "color": "#FF3366"}, "1": {"text": "NORMAL", "color": "#76B900"}}}]}
                        ]
                    }
                ]
            }
        },

        # Row 300: Physical Layer Signal Integrity & Bit Error Rate (BER)
        {"id": 300, "title": "Physical Layer Signal Integrity & Bit Error Rate (Pre/Post-FEC BER)", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 36}},
        {
            "id": 301,
            "title": "Active Monitored BER Links",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 0, "y": 37},
            "targets": [{"expr": 'count(netris_port_bit_error_rate{device_name=~"$device_name"}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },
        {
            "id": 302,
            "title": "Signal Degradation Links (BER > 1e-12)",
            "type": "stat",
            "gridPos": {"h": 4, "w": 6, "x": 6, "y": 37},
            "targets": [{"expr": '(count(netris_port_bit_error_rate{device_name=~"$device_name"} > 1e-12)) or vector(0)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "short",
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF3366", "value": 1}]}
                }
            }
        },
        {
            "id": 303,
            "title": "Physical Layer Bit Error Rate (BER) Trends",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 37},
            "targets": [{"expr": 'topk(10, netris_port_bit_error_rate{device_name=~"$device_name"})', "legendFormat": "{{device_name}} {{port}} BER", "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}}}
        },
        {
            "id": 304,
            "title": "Interface Signal Quality & Bit Error Rate Audit",
            "type": "table",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 41},
            "targets": [{"expr": 'topk(20, netris_port_bit_error_rate{device_name=~"$device_name"})', "format": "table", "instant": True, "refId": "A"}]
        },

        # Row 400: Switch NOS System Services & Telescope Daemons
        {"id": 400, "title": "Switch NOS System Services & Telescope Agent Daemons", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 49}},
        {
            "id": 401,
            "title": "Switch NOS Critical System Daemons (switchd, frr, syscd)",
            "type": "table",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 50},
            "targets": [{"expr": 'netris_daemon_health_status{device_name=~"$device_name"}', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [
                            {"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "FAILED", "color": "#FF3366"}, "1": {"text": "RUNNING", "color": "#76B900"}}}]}
                        ]
                    }
                ]
            }
        },
        {
            "id": 402,
            "title": "Telescope Agent Heartbeat Reliability Over Time",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 50},
            "targets": [{"expr": 'netris_agent_heartbeat{device_name=~"$device_name"}', "legendFormat": "{{device_name}} Agent", "refId": "A"}],
            "fieldConfig": {"defaults": {"min": 0, "max": 1, "color": {"mode": "palette-classic"}}}
        }
    ]

    return {
        "annotations": {"list": []},
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": get_nav_links(),
        "liveNow": False,
        "refresh": "15s",
        "schemaVersion": 38,
        "style": "dark",
        "tags": ["netris", "mongodb", "telescope", "sensors", "thermal", "fans", "ber", "daemons"],
        "templating": {
            "list": [
                {
                    "name": "site",
                    "label": "Site",
                    "type": "query",
                    "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "definition": "label_values(netris_device_info, site)",
                    "query": {
                        "query": "label_values(netris_device_info, site)",
                        "refId": "StandardVariableQuery"
                    },
                    "refresh": 1,
                    "sort": 1,
                    "includeAll": True,
                    "multi": True,
                    "allValue": ".*",
                    "current": {"selected": True, "text": "All", "value": "$__all"}
                },
                {
                    "name": "device_name",
                    "label": "Device",
                    "type": "query",
                    "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "definition": 'label_values(netris_device_info{site=~"$site"}, device_name)',
                    "query": {
                        "query": 'label_values(netris_device_info{site=~"$site"}, device_name)',
                        "refId": "StandardVariableQuery"
                    },
                    "refresh": 1,
                    "sort": 1,
                    "includeAll": True,
                    "multi": True,
                    "allValue": ".*",
                    "current": {"selected": True, "text": "All", "value": "$__all"}
                }
            ]
        },
        "time": {"from": "now-30m", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Netris - MongoDB Environmental & Telescope Sensor Telemetry",
        "uid": "netris-mongodb-sensors",
        "version": 1,
        "panels": panels
    }


PROM_DS = {"type": "prometheus", "uid": "prometheus"}

def finalize_dashboard(dash):
    for panel in dash.get("panels", []):
        ptype = panel.get("type")
        if ptype in ("row", "text"):
            continue
        if "targets" in panel:
            panel["datasource"] = PROM_DS
            for target in panel.get("targets", []):
                target["datasource"] = PROM_DS
    return dash


def main():
    dest_dir = "grafana/dashboards/json"
    os.makedirs(dest_dir, exist_ok=True)

    dashboards = {
        "netris-fabric-overview.json": finalize_dashboard(build_overview_dashboard()),
        "netris-graphite-telemetry.json": finalize_dashboard(build_graphite_dashboard()),
        "netris-mariadb-state.json": finalize_dashboard(build_mariadb_dashboard()),
        "netris-mongodb-sensors.json": finalize_dashboard(build_mongodb_dashboard()),
    }

    print("=" * 72)
    print("      NETRIS MULTI-DATABASE GRAFANA DASHBOARD SUITE GENERATOR        ")
    print("=" * 72)

    for filename, dash_dict in dashboards.items():
        filepath = os.path.join(dest_dir, filename)
        with open(filepath, "w") as f:
            json.dump(dash_dict, f, indent=2)
        print(f"  ✅ Generated: {filepath:<40} (UID: {dash_dict['uid']}, Panels: {len(dash_dict['panels'])})")

    print("=" * 72)
    print("All 4 Netris dashboards successfully written with schemaVersion 38.\n")


if __name__ == "__main__":
    main()
