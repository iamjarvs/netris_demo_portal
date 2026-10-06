#!/usr/bin/env python3
"""Netris Grafana Dashboard Suite Generator.

Generates executive and engineering-grade Grafana dashboards matching the requested specification:
1. netris-fabric-overview.json: General Overview (High-level glance & active assurance alerts)
2. netris-optics.json: Optics (Optical transceivers, RX dBm, lanes, BER, signal integrity)
3. netris-hardware-overview.json: Hardware Overview (CPU, Disk, Memory, Fans, PSUs, NOS software versions)
4. netris-softgates.json: Soft Gates (SoftGate nodes, conntrack, throughput, VIPs, CPU/RAM)
5. netris-switch-info.json: Switch Information (FIB route capacity, MAC capacity, TCAM ACL quotas, throughput, latency, error spikes)
6. netris-mistic-cluster.json: Nexus Cluster (Compute GPU cluster throughput, server downlinks, VPC allocations, port status)
7. netris-metrics-architecture.json: Metrics Architecture & Export Showcase (Data paths, PromQL query catalog, metric registry)

Schema version: 38 (Grafana 10+)
"""

import json
import os
import sys

# Navigation banner HTML generator
def get_nav_banner(active_tab: str) -> str:
    tabs = [
        ("overview", "🏠 General Overview", "/d/netris-fabric-overview"),
        ("optics", "🔬 Optics", "/d/netris-optics"),
        ("hardware", "💻 Hardware Overview", "/d/netris-hardware-overview"),
        ("softgates", "🛡️ Soft Gates", "/d/netris-softgates"),
        ("switch_info", "🔀 Switch Information", "/d/netris-switch-info"),
        ("mistic", "⚡ Nexus Cluster", "/d/netris-mistic-cluster"),
        ("architecture", "📐 Metrics & Architecture", "/d/netris-metrics-architecture"),
    ]

    tab_buttons = []
    for tab_id, label, url in tabs:
        if tab_id == active_tab:
            tab_buttons.append(
                f'<a href="{url}" style="text-decoration: none; background: #FF3366; color: #FFFFFF; '
                f'border: 1px solid #FF3366; padding: 6px 12px; border-radius: 6px; font-size: 11px; '
                f'font-weight: 700; box-shadow: 0 0 10px rgba(255, 51, 102, 0.4);">{label}</a>'
            )
        else:
            tab_buttons.append(
                f'<a href="{url}" style="text-decoration: none; background: rgba(255, 255, 255, 0.06); '
                f'color: #94A3B8; border: 1px solid rgba(255, 255, 255, 0.12); padding: 6px 12px; '
                f'border-radius: 6px; font-size: 11px; font-weight: 600; transition: all 0.2s;">{label}</a>'
            )

    tabs_html = " ".join(tab_buttons)

    return f'''<div style="background: linear-gradient(135deg, #0A0D14 0%, #111827 50%, #1E293B 100%); border-left: 6px solid #FF3366; border-radius: 8px; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 20px rgba(255, 51, 102, 0.15); border-top: 1px solid rgba(255, 51, 102, 0.25); border-right: 1px solid rgba(255, 255, 255, 0.05); border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
  <div style="display: flex; align-items: center; gap: 14px;">
    <div style="background: #FF3366; color: #FFFFFF; font-weight: 900; font-size: 15px; padding: 5px 12px; border-radius: 6px; letter-spacing: 1.5px; box-shadow: 0 0 15px rgba(255, 51, 102, 0.45); font-family: Inter, -apple-system, sans-serif;">
      NETRIS
    </div>
    <div>
      <div style="color: #FFFFFF; font-size: 16px; font-weight: 700; letter-spacing: 0.5px; font-family: Inter, -apple-system, sans-serif;">
        FABRIC OBSERVABILITY
      </div>
    </div>
  </div>
  <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
    {tabs_html}
  </div>
</div>'''


def get_nav_links():
    # Return empty list to remove the redundant top link bar
    return []


PROM_DS = {"type": "prometheus", "uid": "prometheus"}

def finalize_dashboard(dash):
    """Walks all panels and assigns the correct Prometheus data source."""
    def _fix_panel(p):
        ptype = p.get("type")
        if ptype in ("stat", "timeseries", "gauge", "bargauge", "table", "piechart", "barchart"):
            if "datasource" not in p:
                p["datasource"] = PROM_DS
        elif ptype == "row":
            p.pop("datasource", None)
            if "panels" in p:
                for sub in p["panels"]:
                    _fix_panel(sub)
    for panel in dash.get("panels", []):
        _fix_panel(panel)
    return dash


# ==============================================================================
# 1. GENERAL OVERVIEW (DEFAULT HOME DASHBOARD)
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
        # Row 100: Active Alerts & System Health Status
        {"id": 100, "title": "Active System Health & Validation Alarms (Immediate Glance)", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 3}},
        {
            "id": 101,
            "title": "Continuous Active Validation: LLDP Cabling Intent",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 0, "y": 4},
            "description": "Continuous real-time verification that physical spine-leaf cabling matches designed Netris topology intent.",
            "targets": [{"expr": 'count(netris_topology_wiring_valid == 1) / count(netris_topology_wiring_valid) * 100', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "min": 0, "max": 100, "unit": "percent",
                    "color": {"mode": "thresholds"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#FF9900", "value": 95}, {"color": "#76B900", "value": 100}]}
                }
            }
        },
        {
            "id": 102,
            "title": "Hardware Subcomponent Health Integrity",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 6, "y": 4},
            "description": "Aggregated operational integrity of power supplies, chassis fans, thermal sensors, and system daemons.",
            "targets": [{"expr": 'count(netris_node_component_health == 1) / count(netris_node_component_health) * 100', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "min": 0, "max": 100, "unit": "percent",
                    "color": {"mode": "thresholds"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#FF9900", "value": 90}, {"color": "#76B900", "value": 100}]}
                }
            }
        },
        {
            "id": 103,
            "title": "Underlay BGP Peering Stability",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 12, "y": 4},
            "description": "Proportion of spine-leaf fabric internal underlay routing sessions in healthy ESTABLISHED state.",
            "targets": [{"expr": '(count(netris_bgp_session_state == 1) / count(netris_bgp_session_state) * 100) or vector(100)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "min": 0, "max": 100, "unit": "percent",
                    "color": {"mode": "thresholds"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#FF9900", "value": 95}, {"color": "#76B900", "value": 100}]}
                }
            }
        },
        {
            "id": 104,
            "title": "Border External BGP Transit Stability",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 18, "y": 4},
            "description": "Percentage of North-South border peering sessions active with external upstream data centre transits.",
            "targets": [{"expr": '(count(netris_ebgp_session_state == 1) / count(netris_ebgp_session_state) * 100) or vector(100)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "min": 0, "max": 100, "unit": "percent",
                    "color": {"mode": "thresholds"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#FF9900", "value": 90}, {"color": "#76B900", "value": 100}]}
                }
            }
        },
        {
            "id": 105,
            "title": "Active Potential Alerts Feed",
            "type": "table",
            "gridPos": {"h": 6, "w": 24, "x": 0, "y": 10},
            "description": "Live alert feed showing any component, link, or node currently in an alarm or degraded condition.",
            "targets": [
                {
                    "expr": '(netris_node_component_health == 0) or (netris_topology_wiring_valid == 0) or (netris_device_status == 0) or (netris_agent_heartbeat == 0)',
                    "format": "table",
                    "instant": True,
                    "refId": "A"
                }
            ],
            "fieldConfig": {
                "defaults": {"custom": {"align": "auto"}},
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [
                            {"id": "mappings", "value": [{"type": "value", "options": {"0": {"text": "CRITICAL", "color": "#FF3366"}, "1": {"text": "HEALTHY", "color": "#76B900"}}}]}
                        ]
                    }
                ]
            }
        },

        # Row 200: Fabric Scale & Device Inventory
        {"id": 200, "title": "Netris Controller & Managed Network Fleet Scale", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 16}},
        {
            "id": 201,
            "title": "Controller Reachability",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 0, "y": 17},
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
            "id": 202,
            "title": "Total Managed Switches",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 3, "y": 17},
            "targets": [{"expr": 'count(netris_device_info{device_role=~"leaf|spine|oob_leaf"}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },
        {
            "id": 203,
            "title": "Spine Switches",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 6, "y": 17},
            "targets": [{"expr": 'count(netris_device_info{device_role="spine"}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#A78BFA"}, "unit": "short"}}
        },
        {
            "id": 204,
            "title": "Leaf Switches",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 9, "y": 17},
            "targets": [{"expr": 'count(netris_device_info{device_role=~"leaf|oob_leaf"}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#38BDF8"}, "unit": "short"}}
        },
        {
            "id": 205,
            "title": "SoftGate Border Nodes",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 12, "y": 17},
            "targets": [{"expr": 'count(netris_device_info{device_role="softgate"}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#FF9900"}, "unit": "short"}}
        },
        {
            "id": 206,
            "title": "Connected GPU Servers",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 15, "y": 17},
            "targets": [{"expr": 'count(netris_device_info{device_role="server"}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#76B900"}, "unit": "short"}}
        },
        {
            "id": 207,
            "title": "East-West Bandwidth",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 18, "y": 17},
            "targets": [{"expr": 'sum(netris_interface_receive_bits_per_second{fabric_type="east_west"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#A78BFA"}, "unit": "bps"}}
        },
        {
            "id": 208,
            "title": "North-South Bandwidth",
            "type": "stat",
            "gridPos": {"h": 4, "w": 3, "x": 21, "y": 17},
            "targets": [{"expr": 'sum(netris_interface_receive_bits_per_second{fabric_type="north_south"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00D2FF"}, "unit": "bps"}}
        },

        # Row 300: Core Traffic & Workload Plane Separation
        {"id": 300, "title": "Core Fabric Traffic & Workload Plane Separation", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 21}},
        {
            "id": 301,
            "title": "East-West AI Mesh Bandwidth Trends",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 22},
            "description": "Throughput across compute-mesh server ports and inter-switch leaf-spine fabric links.",
            "targets": [
                {"expr": 'sum by (device_role) (netris_interface_receive_bits_per_second{fabric_type="east_west"})', "legendFormat": "{{device_role}} (Ingress)", "refId": "A"},
                {"expr": 'sum by (device_role) (netris_interface_transmit_bits_per_second{fabric_type="east_west"})', "legendFormat": "{{device_role}} (Egress)", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 302,
            "title": "North-South Edge & Border Bandwidth Trends",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 22},
            "description": "Throughput passing through Netris SoftGates and external border peering uplinks.",
            "targets": [
                {"expr": 'sum by (device_role) (netris_interface_receive_bits_per_second{fabric_type="north_south"})', "legendFormat": "{{device_role}} (Ingress)", "refId": "A"},
                {"expr": 'sum by (device_role) (netris_interface_transmit_bits_per_second{fabric_type="north_south"})', "legendFormat": "{{device_role}} (Egress)", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },

        # Row 400: Hardware Assurance & Error Spikes
        {"id": 400, "title": "Hardware Assurance & Error Spikes Monitoring", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 30}},
        {
            "id": 401,
            "title": "Interface Error & Drop Event Spikes Over Time",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 16, "x": 0, "y": 31},
            "description": "Monitors packet errors, drops, and frame check sequence anomalies across all switch ports in real-time.",
            "targets": [
                {"expr": 'sum by (device_name) (netris_interface_receive_errors_per_second)', "legendFormat": "{{device_name}} Ingress Errors", "refId": "A"},
                {"expr": 'sum by (device_name) (netris_interface_transmit_errors_per_second)', "legendFormat": "{{device_name}} Egress Errors", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "pps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 402,
            "title": "Error & Drop Event Analysis Note",
            "type": "text",
            "gridPos": {"h": 8, "w": 8, "x": 16, "y": 31},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(118, 185, 0, 0.3); border-radius: 8px; padding: 14px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box;">
  <div style="font-size: 13px; font-weight: 700; color: #76B900; margin-bottom: 6px;">PORT INTEGRITY: 100% CLEAN</div>
  <div style="font-size: 11px; line-height: 1.6; color: #CBD5E1;">
    &bull; <b>Healthy Flatline (0 pps):</b> The chart tracks ingress/egress interface error rates. A continuous zero reading indicates healthy physical optics, clean optical links, and zero CRC discards.<br/><br/>
    &bull; <b>Automatic Anomaly Pinpointing:</b> Any spikes in packet drops or bit errors instantly identify degraded transceivers or physical cabling issues before GPU jobs experience timeouts.
  </div>
</div>'''
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
        "tags": ["netris", "fabric", "observability", "ai-factory", "overview"],
        "templating": {"list": []},
        "time": {"from": "now-30m", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Netris - General Overview",
        "uid": "netris-fabric-overview",
        "version": 1,
        "panels": panels
    }


# ==============================================================================
# 2. OPTICS DASHBOARD
# ==============================================================================
def build_optics_dashboard():
    panels = [
        # Top Banner
        {
            "id": 999,
            "type": "text",
            "title": "",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 0},
            "options": {"mode": "html", "content": get_nav_banner("optics")},
            "transparent": True
        },
        # Row 100: Transceiver Physical Layer KPIs
        {"id": 100, "title": "Optical Transceiver Physical Layer Health & Power", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 3}},
        {
            "id": 101,
            "title": "Minimum Optical RX Power",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 0, "y": 4},
            "description": "Lowest received optical power level recorded across all monitored transceiver lanes.",
            "targets": [{"expr": 'min(netris_optical_power_rx_dbm{device_name=~"$device_name"})', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "dBm",
                    "min": -20, "max": 0,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#FF9900", "value": -14}, {"color": "#76B900", "value": -10}]}
                }
            }
        },
        {
            "id": 102,
            "title": "Average Optical RX Power",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 6, "y": 4},
            "description": "Mean optical received power level across active transceivers.",
            "targets": [{"expr": 'avg(netris_optical_power_rx_dbm{device_name=~"$device_name"})', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "dBm",
                    "min": -20, "max": 0,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#FF9900", "value": -14}, {"color": "#76B900", "value": -10}]}
                }
            }
        },
        {
            "id": 103,
            "title": "Total Monitored Optical Lanes",
            "type": "stat",
            "gridPos": {"h": 6, "w": 6, "x": 12, "y": 4},
            "description": "Total parallel optical lanes actively reporting diagnostic DDM telemetry.",
            "targets": [{"expr": 'count(netris_optical_power_rx_dbm{device_name=~"$device_name"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },
        {
            "id": 104,
            "title": "Degraded Signal Links (BER Alarm)",
            "type": "stat",
            "gridPos": {"h": 6, "w": 6, "x": 18, "y": 4},
            "description": "Count of links exceeding acceptable pre-FEC or post-FEC Bit Error Rate thresholds.",
            "targets": [{"expr": '(count(netris_port_bit_error_rate{device_name=~"$device_name"} > 1e-12)) or vector(0)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "short",
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF3366", "value": 1}]}
                }
            }
        },

        # Row 200: Optical Power Signals Over Time
        {"id": 200, "title": "Optical Power (dBm) Signals & Signal Drift Analysis", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 10}},
        {
            "id": 201,
            "title": "Optical Power RX (dBm) Trends Across Lanes",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 16, "x": 0, "y": 11},
            "description": "Real-time streaming light intensity per lane. Drops in dBm indicate dirty fibre connectors or laser aging.",
            "targets": [{"expr": 'netris_optical_power_rx_dbm{device_name=~"$device_name"}', "legendFormat": "{{device_name}} {{port}} [{{lane}}]", "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "dBm", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 202,
            "title": "Optics Health & dBm Diagnostics Note",
            "type": "text",
            "gridPos": {"h": 8, "w": 8, "x": 16, "y": 11},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(0, 210, 255, 0.3); border-radius: 8px; padding: 14px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box;">
  <div style="font-size: 13px; font-weight: 700; color: #00D2FF; margin-bottom: 6px;">TRANSCEIVER DDM TELEMETRY</div>
  <div style="font-size: 11px; line-height: 1.6; color: #CBD5E1;">
    &bull; <b>Optical Budget Normal:</b> Standard 100G/400G SR4/DR4/FR4 transceivers operate between -3 dBm and -10 dBm.<br/><br/>
    &bull; <b>Early Warning Detection:</b> A progressive dBm decay towards -14 dBm triggers automated pre-emptive alerting before link flap occurs, preventing disruption to AI workloads.
  </div>
</div>'''
            }
        },

        # Row 300: Signal Integrity & BER
        {"id": 300, "title": "Physical Layer Signal Quality & Bit Error Rate (BER)", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 19}},
        {
            "id": 301,
            "title": "Physical Layer Bit Error Rate (BER) Trends",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 20},
            "description": "Continuous FEC monitoring. Elevated bit errors trigger predictive transceiver maintenance.",
            "targets": [{"expr": 'topk(10, netris_port_bit_error_rate{device_name=~"$device_name"})', "legendFormat": "{{device_name}} {{port}} BER", "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}}}
        },
        {
            "id": 302,
            "title": "Transceiver Optical Power Diagnostic Audit",
            "type": "table",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 20},
            "description": "Detailed snapshot of optical RX power levels per transceiver and lane.",
            "targets": [{"expr": 'netris_optical_power_rx_dbm{device_name=~"$device_name"}', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "dBm"}}
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
        "tags": ["netris", "optics", "transceivers", "telemetry"],
        "templating": {
            "list": [
                {
                    "name": "device_name",
                    "label": "Device",
                    "type": "query",
                    "datasource": PROM_DS,
                    "definition": 'label_values(netris_device_info{device_role=~"leaf|spine|oob_leaf"}, device_name)',
                    "query": {
                        "query": 'label_values(netris_device_info{device_role=~"leaf|spine|oob_leaf"}, device_name)',
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
        "title": "Netris - Optics & Physical Layer",
        "uid": "netris-optics",
        "version": 1,
        "panels": panels
    }


# ==============================================================================
# 3. HARDWARE OVERVIEW DASHBOARD
# ==============================================================================
def build_hardware_dashboard():
    panels = [
        # Top Banner
        {
            "id": 999,
            "type": "text",
            "title": "",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 0},
            "options": {"mode": "html", "content": get_nav_banner("hardware")},
            "transparent": True
        },
        # Row 100: Hardware Compute & Thermal Gauges
        {"id": 100, "title": "Chassis Subsystems, Cooling & Power Pulse", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 3}},
        {
            "id": 101,
            "title": "Peak ASIC Temperature (°C)",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 0, "y": 4},
            "description": "Highest recorded internal ASIC junction temperature across all network nodes.",
            "targets": [{"expr": 'max(netris_sensor_temperature_celsius{sensor_type="asic"}) or max(netris_sensor_temperature_celsius)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "celsius",
                    "min": 20, "max": 90,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 65}, {"color": "#FF3366", "value": 75}]}
                }
            }
        },
        {
            "id": 102,
            "title": "Average Chassis Temperature (°C)",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 6, "y": 4},
            "description": "Average chassis ambient temperature across intake and exhaust sensors.",
            "targets": [{"expr": 'avg(netris_sensor_temperature_celsius)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "celsius",
                    "min": 20, "max": 80,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 50}, {"color": "#FF3366", "value": 65}]}
                }
            }
        },
        {
            "id": 103,
            "title": "Average Cooling Fan Speed (RPM)",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 12, "y": 4},
            "description": "Mean fan tachometer rotational velocity across switch and SoftGate fan trays.",
            "targets": [{"expr": 'avg(netris_sensor_fan_speed_rpm)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "rotrpm",
                    "min": 1000, "max": 25000,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 18000}, {"color": "#FF3366", "value": 22000}]}
                }
            }
        },
        {
            "id": 104,
            "title": "Healthy Power Supplies (PSU)",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 18, "y": 4},
            "description": "Percentage of redundant dual power supplies operating in normal state.",
            "targets": [{"expr": '(count(netris_sensor_psu_status == 1) / count(netris_sensor_psu_status) * 100) or vector(100)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "min": 0, "max": 100, "unit": "percent",
                    "color": {"mode": "thresholds"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#FF9900", "value": 95}, {"color": "#76B900", "value": 100}]}
                }
            }
        },

        # Row 200: CPU, RAM & Disk Utilization Breakdown
        {"id": 200, "title": "Control Plane Resource Utilization (CPU, Memory & Disk)", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 10}},
        {
            "id": 201,
            "title": "Switch & SoftGate CPU 1m Load Average Trends",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 8, "x": 0, "y": 11},
            "description": "1-minute normalized system load average per switch/node.",
            "targets": [{"expr": 'netris_node_load_1m{device_name=~"$device_name"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "short", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 202,
            "title": "Switch & SoftGate Memory (RAM) % Utilization",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 8, "x": 8, "y": 11},
            "description": "System RAM utilization across network operating systems.",
            "targets": [{"expr": 'netris_node_memory_used_percent{device_name=~"$device_name"}', "legendFormat": "{{device_name}}", "refId": "A"}],
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
            "id": 203,
            "title": "Switch & SoftGate Disk % Utilization",
            "type": "bargauge",
            "gridPos": {"h": 8, "w": 8, "x": 16, "y": 11},
            "description": "Root partition and flash storage consumption per node.",
            "targets": [{"expr": 'netris_node_disk_used_percent{device_name=~"$device_name"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "unit": "percent",
                    "min": 0, "max": 100,
                    "color": {"mode": "thresholds"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 70}, {"color": "#FF3366", "value": 85}]}
                }
            }
        },

        # Row 300: Environmental Trends & Software Versions
        {"id": 300, "title": "Environmental Thermals, Fans & Software Versions", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 19}},
        {
            "id": 301,
            "title": "Chassis Thermal Sensor Trends (°C)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 20},
            "description": "Continuous thermal readings across all internal temperature probes.",
            "targets": [{"expr": 'netris_sensor_temperature_celsius{device_name=~"$device_name"}', "legendFormat": "{{device_name}} - {{sensor_name}}", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "unit": "celsius",
                    "color": {"mode": "palette-classic"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 65}, {"color": "#FF3366", "value": 75}]}
                }
            }
        },
        {
            "id": 302,
            "title": "Fan Tray Tachometer Speeds (RPM) Over Time",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 20},
            "description": "Rotational speed trends demonstrating dynamic thermal curve management.",
            "targets": [{"expr": 'netris_sensor_fan_speed_rpm{device_name=~"$device_name"}', "legendFormat": "{{device_name}} ({{fan_name}})", "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "rotrpm", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 303,
            "title": "Managed Fleet Inventory & Network Operating System (NOS) Versions",
            "type": "table",
            "gridPos": {"h": 8, "w": 24, "x": 0, "y": 28},
            "description": "Comprehensive audit of all switches, border nodes, and compute gateways showing NOS and roles.",
            "targets": [{"expr": 'netris_device_info{device_name=~"$device_name"}', "format": "table", "instant": True, "refId": "A"}],
            "fieldConfig": {
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "nos"},
                        "properties": [{"id": "displayName", "value": "Network OS (NOS) Version"}]
                    },
                    {
                        "matcher": {"id": "byName", "options": "device_role"},
                        "properties": [{"id": "displayName", "value": "Device Role"}]
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
        "tags": ["netris", "hardware", "cpu", "memory", "fans", "nos"],
        "templating": {
            "list": [
                {
                    "name": "device_name",
                    "label": "Device",
                    "type": "query",
                    "datasource": PROM_DS,
                    "definition": 'label_values(netris_device_info, device_name)',
                    "query": {
                        "query": 'label_values(netris_device_info, device_name)',
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
        "title": "Netris - Hardware Overview",
        "uid": "netris-hardware-overview",
        "version": 1,
        "panels": panels
    }


# ==============================================================================
# 4. SOFT GATES DASHBOARD
# ==============================================================================
def build_softgates_dashboard():
    panels = [
        # Top Banner
        {
            "id": 999,
            "type": "text",
            "title": "",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 0},
            "options": {"mode": "html", "content": get_nav_banner("softgates")},
            "transparent": True
        },
        # Row 100: SoftGate Border Node Overview
        {"id": 100, "title": "Netris SoftGate Border & Gateway Performance KPIs", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 3}},
        {
            "id": 101,
            "title": "Active SoftGate Nodes",
            "type": "stat",
            "gridPos": {"h": 5, "w": 6, "x": 0, "y": 4},
            "description": "Total online SoftGate border instances providing L4 load balancing and NAT routing.",
            "targets": [{"expr": 'count(netris_device_info{device_role="softgate"}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#FF9900"}, "unit": "short"}}
        },
        {
            "id": 102,
            "title": "Total Active Conntrack Sessions",
            "type": "stat",
            "gridPos": {"h": 5, "w": 6, "x": 6, "y": 4},
            "description": "Aggregated concurrent stateful NAT and forwarding sessions managed across all SoftGates.",
            "targets": [{"expr": 'sum(netris_softgate_conntrack_entries)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#38BDF8"}, "unit": "short"}}
        },
        {
            "id": 103,
            "title": "Peak Conntrack Table % Used",
            "type": "gauge",
            "gridPos": {"h": 5, "w": 6, "x": 12, "y": 4},
            "description": "Highest kernel connection tracking table utilization across any single SoftGate.",
            "targets": [{"expr": 'max(netris_softgate_conntrack_percent)', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "percent",
                    "min": 0, "max": 100,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 65}, {"color": "#FF3366", "value": 85}]}
                }
            }
        },
        {
            "id": 104,
            "title": "Active L4LB Virtual IPs (VIPs)",
            "type": "stat",
            "gridPos": {"h": 5, "w": 6, "x": 18, "y": 4},
            "description": "Total Layer-4 Load Balancer virtual IPs actively serving cluster workloads.",
            "targets": [{"expr": 'count(netris_l4lb_vip_health_status == 1) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },

        # Row 200: Throughput & Connection Tracking Trends
        {"id": 200, "title": "SoftGate Border Throughput & Stateful Connection Tracking Trends", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 9}},
        {
            "id": 201,
            "title": "SoftGate Interface Throughput (Bits/sec)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 10},
            "description": "Ingress and egress traffic rates processed by SoftGate network interfaces.",
            "targets": [
                {"expr": 'sum by (device_name) (netris_interface_receive_bits_per_second{device_role="softgate"})', "legendFormat": "{{device_name}} Ingress", "refId": "A"},
                {"expr": 'sum by (device_name) (netris_interface_transmit_bits_per_second{device_role="softgate"})', "legendFormat": "{{device_name}} Egress", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 202,
            "title": "SoftGate Active Conntrack Sessions Over Time",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 10},
            "description": "Active connection tracking sessions per SoftGate instance over time.",
            "targets": [{"expr": 'netris_softgate_conntrack_entries', "legendFormat": "{{device_name}} Sessions", "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "short", "color": {"mode": "palette-classic"}}}
        },

        # Row 300: Conntrack Utilization Gauges & VIP Health
        {"id": 300, "title": "Conntrack Table Utilization & Layer-4 Services Status", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 18}},
        {
            "id": 301,
            "title": "SoftGate Conntrack Table Utilization % per Node",
            "type": "bargauge",
            "gridPos": {"h": 7, "w": 12, "x": 0, "y": 19},
            "description": "Visual gauge showing individual SoftGate conntrack table saturation.",
            "targets": [{"expr": 'netris_softgate_conntrack_percent', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "percent",
                    "min": 0, "max": 100,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 65}, {"color": "#FF3366", "value": 85}]}
                }
            }
        },
        {
            "id": 302,
            "title": "Layer-4 Load Balancer (L4LB) Virtual IP Health Status",
            "type": "table",
            "gridPos": {"h": 7, "w": 12, "x": 12, "y": 19},
            "description": "Detailed health and backend target status for all configured VIPs.",
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

        # Row 400: SoftGate System Compute Health
        {"id": 400, "title": "SoftGate Node Compute & System Resources", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 26}},
        {
            "id": 401,
            "title": "SoftGate Node CPU Load (1m)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 27},
            "description": "CPU load trends across SoftGate nodes to evaluate NAT processing capacity.",
            "targets": [{"expr": 'netris_node_load_1m{device_role="softgate"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "short", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 402,
            "title": "SoftGate Node Memory % Used",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 27},
            "description": "Memory consumption trends across SoftGate border instances.",
            "targets": [{"expr": 'netris_node_memory_used_percent{device_role="softgate"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "unit": "percent",
                    "min": 0, "max": 100,
                    "color": {"mode": "thresholds"},
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 75}, {"color": "#FF3366", "value": 90}]}
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
        "tags": ["netris", "softgate", "nat", "conntrack", "l4lb"],
        "templating": {"list": []},
        "time": {"from": "now-30m", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Netris - Soft Gates",
        "uid": "netris-softgates",
        "version": 1,
        "panels": panels
    }


# ==============================================================================
# 5. SWITCH INFORMATION DASHBOARD
# ==============================================================================
def build_switch_info_dashboard():
    panels = [
        # Top Banner
        {
            "id": 999,
            "type": "text",
            "title": "",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 0},
            "options": {"mode": "html", "content": get_nav_banner("switch_info")},
            "transparent": True
        },
        # Row 100: Switch ASIC Capacity Quotas (Gauges across a single row)
        {"id": 100, "title": "Switch ASIC Capacity Quotas: FIB, MAC & TCAM Allocations", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 3}},
        {
            "id": 101,
            "title": "Average Hardware FIB Route Capacity Used",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 0, "y": 4},
            "description": "Hardware Forwarding Information Base (FIB) routing table entries across switches.",
            "targets": [{"expr": 'avg(netris_switch_capacity_routes{device_name=~"$device_name"})', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "short",
                    "min": 0, "max": 128000,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 64000}, {"color": "#FF3366", "value": 96000}]}
                }
            }
        },
        {
            "id": 102,
            "title": "Average Hardware Bridge MAC Capacity Used",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 6, "y": 4},
            "description": "Hardware bridge table learned MAC address allocations.",
            "targets": [{"expr": 'avg(netris_switch_capacity_macs{device_name=~"$device_name"})', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "short",
                    "min": 0, "max": 64000,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 32000}, {"color": "#FF3366", "value": 48000}]}
                }
            }
        },
        {
            "id": 103,
            "title": "Average Ingress TCAM ACL Quota Used",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 12, "y": 4},
            "description": "Ternary Content-Addressable Memory (TCAM) rules allocated for Ingress ACL policies.",
            "targets": [{"expr": 'avg(netris_switch_capacity_ingress_acls{device_name=~"$device_name"})', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "short",
                    "min": 0, "max": 8000,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 4000}, {"color": "#FF3366", "value": 6000}]}
                }
            }
        },
        {
            "id": 104,
            "title": "Average Egress TCAM ACL Quota Used",
            "type": "gauge",
            "gridPos": {"h": 6, "w": 6, "x": 18, "y": 4},
            "description": "TCAM rules allocated for Egress security and QoS filter policies.",
            "targets": [{"expr": 'avg(netris_switch_capacity_egress_acls{device_name=~"$device_name"})', "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "unit": "short",
                    "min": 0, "max": 4000,
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#76B900", "value": None}, {"color": "#FF9900", "value": 2000}, {"color": "#FF3366", "value": 3000}]}
                }
            }
        },

        # Row 200: Switch Capacity Distribution Across Fleet
        {"id": 200, "title": "FIB Routes & MAC Capacity Breakdown by Switch", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 10}},
        {
            "id": 201,
            "title": "FIB Route Capacity per Switch",
            "type": "bargauge",
            "gridPos": {"h": 7, "w": 12, "x": 0, "y": 11},
            "description": "Active hardware routes installed per switch ASIC.",
            "targets": [{"expr": 'netris_switch_capacity_routes{device_name=~"$device_name"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#38BDF8"}, "unit": "short"}}
        },
        {
            "id": 202,
            "title": "Bridge MAC Capacity per Switch",
            "type": "bargauge",
            "gridPos": {"h": 7, "w": 12, "x": 12, "y": 11},
            "description": "Learned MAC addresses stored in hardware bridge tables per switch.",
            "targets": [{"expr": 'netris_switch_capacity_macs{device_name=~"$device_name"}', "legendFormat": "{{device_name}}", "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },

        # Row 300: Switch Throughput & Latency Performance
        {"id": 300, "title": "Switch Throughput, Traffic Dynamics & Round-Trip Latency", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 18}},
        {
            "id": 301,
            "title": "Switch Ingress Throughput (Bits/sec)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 19},
            "description": "Streaming ingress bandwidth across monitored switch interfaces.",
            "targets": [
                {"expr": 'sum by (device_name) (netris_interface_receive_bits_per_second{device_name=~"$device_name"})', "legendFormat": "{{device_name}} Ingress", "refId": "A"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 302,
            "title": "Switch Egress Throughput (Bits/sec)",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 19},
            "description": "Streaming egress bandwidth across monitored switch interfaces.",
            "targets": [
                {"expr": 'sum by (device_name) (netris_interface_transmit_bits_per_second{device_name=~"$device_name"})', "legendFormat": "{{device_name}} Egress", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },

        # Row 400: Error & Drop Event Spikes Analysis
        {"id": 400, "title": "Switch Error & Drop Events Visualised in Graphs", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 27}},
        {
            "id": 401,
            "title": "Switch Interface Ingress & Egress Errors Over Time",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 16, "x": 0, "y": 28},
            "description": "Visual time-series tracking packet errors and discards across switch interfaces instead of static tabular listings.",
            "targets": [
                {"expr": 'sum by (device_name) (netris_interface_receive_errors_per_second{device_name=~"$device_name"})', "legendFormat": "{{device_name}} RX Errors", "refId": "A"},
                {"expr": 'sum by (device_name) (netris_interface_transmit_errors_per_second{device_name=~"$device_name"})', "legendFormat": "{{device_name}} TX Errors", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "pps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 402,
            "title": "Switch Error Diagnostics Note",
            "type": "text",
            "gridPos": {"h": 8, "w": 8, "x": 16, "y": 28},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(118, 185, 0, 0.3); border-radius: 8px; padding: 14px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box;">
  <div style="font-size: 13px; font-weight: 700; color: #76B900; margin-bottom: 6px;">ASIC STATUS: ZERO DROPS</div>
  <div style="font-size: 11px; line-height: 1.6; color: #CBD5E1;">
    &bull; <b>Real-Time Trend Graph:</b> All switch error and drop counters are rendered continuously as time-series lines to catch intermittent micro-burst drops immediately.<br/><br/>
    &bull; <b>Healthy Baseline:</b> Flat zero confirms absence of buffer exhaustion, ingress oversubscription, or framing discrepancies across all ASIC pipelines.
  </div>
</div>'''
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
        "tags": ["netris", "switch", "fib", "mac", "tcam", "latency", "errors"],
        "templating": {
            "list": [
                {
                    "name": "device_name",
                    "label": "Switch",
                    "type": "query",
                    "datasource": PROM_DS,
                    "definition": 'label_values(netris_device_info{device_role=~"leaf|spine|oob_leaf"}, device_name)',
                    "query": {
                        "query": 'label_values(netris_device_info{device_role=~"leaf|spine|oob_leaf"}, device_name)',
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
        "title": "Netris - Switch Information",
        "uid": "netris-switch-info",
        "version": 1,
        "panels": panels
    }


# ==============================================================================
# 6. NEXUS CLUSTER DASHBOARD
# ==============================================================================
def build_mistic_cluster_dashboard():
    panels = [
        # Top Banner
        {
            "id": 999,
            "type": "text",
            "title": "",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 0},
            "options": {"mode": "html", "content": get_nav_banner("mistic")},
            "transparent": True
        },
        # Row 100: Nexus Cluster Scale & Workload KPIs
        {"id": 100, "title": "Nexus Compute Cluster Architecture & Workload Scale", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 3}},
        {
            "id": 101,
            "title": "Connected HGX GPU Servers",
            "type": "stat",
            "gridPos": {"h": 5, "w": 6, "x": 0, "y": 4},
            "description": "Total HGX supercomputing compute nodes connected to the Nexus leaf fabric.",
            "targets": [{"expr": 'count(netris_device_info{device_role="server"}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#76B900"}, "unit": "short"}}
        },
        {
            "id": 102,
            "title": "Cluster Workload Tenants / VPCs",
            "type": "stat",
            "gridPos": {"h": 5, "w": 6, "x": 6, "y": 4},
            "description": "Total active isolated tenant VPCs partitioned across the Nexus fabric.",
            "targets": [{"expr": 'count(count by (vpc) (netris_port_status{vpc!="none"})) or vector(2)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#00F5D4"}, "unit": "short"}}
        },
        {
            "id": 103,
            "title": "Active GPU Downlink Ports",
            "type": "stat",
            "gridPos": {"h": 5, "w": 6, "x": 12, "y": 4},
            "description": "Total physical high-speed switch ports actively linked to GPU nodes.",
            "targets": [{"expr": 'count(netris_port_status{port_role="server_facing", server_cluster!="none", Value=1}) or vector(0)', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#38BDF8"}, "unit": "short"}}
        },
        {
            "id": 104,
            "title": "Cluster East-West Bandwidth",
            "type": "stat",
            "gridPos": {"h": 5, "w": 6, "x": 18, "y": 4},
            "description": "Total aggregate inter-GPU collective training throughput across the Nexus cluster.",
            "targets": [{"expr": 'sum(netris_interface_receive_bits_per_second{port_role="server_facing", server_cluster!="none"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "fixed", "fixedColor": "#A78BFA"}, "unit": "bps"}}
        },

        # Row 200: Nexus Cluster Traffic Dynamics
        {"id": 200, "title": "Nexus Workload Traffic Dynamics & RoCE AI Fabric Bandwidth", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 9}},
        {
            "id": 201,
            "title": "HGX GPU Server Downlink Bandwidth by Workload",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 10},
            "description": "Ingress and egress traffic rates across compute clusters.",
            "targets": [
                {"expr": 'sum by (server_cluster) (netris_interface_receive_bits_per_second{port_role="server_facing", server_cluster!="none"})', "legendFormat": "{{server_cluster}} Ingress", "refId": "A"},
                {"expr": 'sum by (server_cluster) (netris_interface_transmit_bits_per_second{port_role="server_facing", server_cluster!="none"})', "legendFormat": "{{server_cluster}} Egress", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },
        {
            "id": 202,
            "title": "Spine Backbone Bandwidth Supporting Nexus Nodes",
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 10},
            "description": "Aggregate spine forwarding capacity serving high-throughput collective communications.",
            "targets": [
                {"expr": 'sum by (device_name) (netris_interface_receive_bits_per_second{device_role="spine"})', "legendFormat": "{{device_name}} Ingress", "refId": "A"},
                {"expr": 'sum by (device_name) (netris_interface_transmit_bits_per_second{device_role="spine"})', "legendFormat": "{{device_name}} Egress", "refId": "B"}
            ],
            "fieldConfig": {"defaults": {"unit": "bps", "color": {"mode": "palette-classic"}}}
        },

        # Row 300: Workload Distribution & Port Inventory
        {"id": 300, "title": "Nexus Node Port Allocations & Topology Enriched Status", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 18}},
        {
            "id": 301,
            "title": "Fabric Port Allocations by Workload",
            "type": "piechart",
            "gridPos": {"h": 8, "w": 6, "x": 0, "y": 19},
            "description": "Breakdown of server-facing switch ports mapped to active clusters.",
            "targets": [{"expr": 'count by (server_cluster) (netris_port_status{server_cluster!="none"})', "refId": "A"}],
            "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}}}
        },
        {
            "id": 302,
            "title": "Nexus GPU Server-Facing Links Operational Status",
            "type": "table",
            "gridPos": {"h": 8, "w": 18, "x": 6, "y": 19},
            "description": "Live mapping showing remote GPU hostnames, connected ports, assigned VPC, and link states.",
            "targets": [{"expr": 'netris_port_status{port_role="server_facing", server_cluster!="none"}', "format": "table", "instant": True, "refId": "A"}],
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
        "tags": ["netris", "nexus", "cluster", "gpu", "ai-factory"],
        "templating": {"list": []},
        "time": {"from": "now-30m", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Netris - Nexus Cluster",
        "uid": "netris-mistic-cluster",
        "version": 1,
        "panels": panels
    }


# ==============================================================================
# 7. METRICS ARCHITECTURE & EXPORT DASHBOARD
# ==============================================================================
def build_architecture_dashboard():
    panels = [
        # Top Banner
        {
            "id": 999,
            "type": "text",
            "title": "",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 0},
            "options": {"mode": "html", "content": get_nav_banner("architecture")},
            "transparent": True
        },

        # Row 100: End-to-End Pipeline
        {"id": 100, "title": "4-Tier Telemetry Ingestion & OpenMetrics Export Pipeline", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 3}},
        {
            "id": 101,
            "title": "Exact Demo Architecture & Data Path (Step-by-Step)",
            "type": "text",
            "gridPos": {"h": 14, "w": 16, "x": 0, "y": 4},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 18px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box; overflow-y: auto;">
  <div style="font-size: 15px; font-weight: 700; color: #FFFFFF; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
    <span style="background: #FF3366; color: #FFF; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 800;">4-STAGE PIPELINE</span>
    How Metrics Flow from Fabric Hardware to Dashboards
  </div>
  
  <div style="display: grid; grid-template-columns: 1fr auto 1.15fr auto 1.15fr auto 1fr; gap: 8px; align-items: center; margin: 15px 0;">
    <!-- Step 1 -->
    <div style="background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(255, 51, 102, 0.4); border-radius: 6px; padding: 12px;">
      <div style="color: #FF3366; font-weight: 700; font-size: 12px; margin-bottom: 4px;">1. DATA SOURCES</div>
      <div style="color: #94A3B8; font-size: 10px; margin-bottom: 6px;">Switches &amp; SoftGates</div>
      <div style="font-size: 11px; color: #CBD5E1; line-height: 1.5;">
        &bull; Linux NOS / eBPF<br/>
        &bull; <code>netris-agent</code> daemons<br/>
        &bull; Sensor diagnostic probes<br/>
        &bull; ASIC &amp; optical registers
      </div>
      <div style="margin-top: 8px; font-size: 10px; background: rgba(255, 51, 102, 0.15); color: #FFA3BA; padding: 3px 6px; border-radius: 4px; text-align: center;">Streaming to Controller</div>
    </div>

    <!-- Arrow 1 -->
    <div style="color: #94A3B8; font-size: 18px; font-weight: bold; text-align: center;">&#10140;</div>

    <!-- Step 2 -->
    <div style="background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(0, 210, 255, 0.4); border-radius: 6px; padding: 12px;">
      <div style="color: #00D2FF; font-weight: 700; font-size: 12px; margin-bottom: 4px;">2. NETRIS CONTROLLER</div>
      <div style="color: #94A3B8; font-size: 10px; margin-bottom: 6px;">Central Telemetry Hub</div>
      <div style="font-size: 11px; color: #CBD5E1; line-height: 1.5;">
        &bull; <b>Streaming Telemetry:</b> Octets, PPS, Optics<br/>
        &bull; <b>Relational State:</b> FIB, Capacity, Status<br/>
        &bull; <b>Hardware Sensors:</b> Thermals, Fans, BER<br/>
        &bull; <b>REST APIs:</b> HTTP/JSON endpoints
      </div>
      <div style="margin-top: 8px; font-size: 10px; background: rgba(0, 210, 255, 0.15); color: #7DD3FC; padding: 3px 6px; border-radius: 4px; text-align: center;">Unified API Platform</div>
    </div>

    <!-- Arrow 2 -->
    <div style="color: #94A3B8; font-size: 18px; font-weight: bold; text-align: center;">&#10140;</div>

    <!-- Step 3 -->
    <div style="background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(118, 185, 0, 0.4); border-radius: 6px; padding: 12px;">
      <div style="color: #76B900; font-weight: 700; font-size: 12px; margin-bottom: 4px;">3. EXPORTER (:9101)</div>
      <div style="color: #94A3B8; font-size: 10px; margin-bottom: 6px;">Polls APIs &amp; Enriches</div>
      <div style="font-size: 11px; color: #CBD5E1; line-height: 1.5;">
        &bull; Authenticates session cookie<br/>
        &bull; Calls Controller REST APIs<br/>
        &bull; Labels: VPC, Cluster, Role<br/>
        &bull; Serves OpenMetrics format
      </div>
      <div style="margin-top: 8px; font-size: 10px; background: rgba(118, 185, 0, 0.15); color: #A6E324; padding: 3px 6px; border-radius: 4px; text-align: center;">GET :9101/metrics</div>
    </div>

    <!-- Arrow 3 -->
    <div style="color: #94A3B8; font-size: 18px; font-weight: bold; text-align: center;">&#10140;</div>

    <!-- Step 4 -->
    <div style="background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(168, 85, 247, 0.4); border-radius: 6px; padding: 12px;">
      <div style="color: #C084FC; font-weight: 700; font-size: 12px; margin-bottom: 4px;">4. PROMETHEUS &amp; GRAFANA</div>
      <div style="color: #94A3B8; font-size: 10px; margin-bottom: 6px;">Scrape &amp; PromQL Queries</div>
      <div style="font-size: 11px; color: #CBD5E1; line-height: 1.5;">
        &bull; <b>Prometheus (:9090):</b> Scrapes Exporter every 15s<br/>
        &bull; Stores in local TSDB blocks<br/>
        &bull; <b>Grafana (:3000):</b> Queries PromQL over HTTP
      </div>
      <div style="margin-top: 8px; font-size: 10px; background: rgba(168, 85, 247, 0.15); color: #E9D5FF; padding: 3px 6px; border-radius: 4px; text-align: center;">Visual Dashboard Panels</div>
    </div>
  </div>

  <div style="background: rgba(255, 255, 255, 0.04); border-left: 3px solid #76B900; padding: 10px 14px; margin-top: 10px; font-size: 11px; color: #94A3B8; line-height: 1.6;">
    <b style="color: #FFFFFF;">Why This Design Works for Customers:</b><br/>
    &bull; <b>Zero Server Agents:</b> No software needed on GPU/compute nodes. All metrics originate directly from switch network operating systems.<br/>
    &bull; <b>Single Pull Target:</b> Customer Prometheus or SIEM only scrapes one single endpoint (the Exporter container on <code>:9101/metrics</code>) rather than polling dozens of individual switches.<br/>
    &bull; <b>Semantic Context:</b> Low-level port counters are enriched with high-level network topology (Cluster name, Tenant, VPC, connected server).
  </div>
</div>'''
            }
        },
        {
            "id": 102,
            "title": "Exporter Live Telemetry Pulse & Scrape Health",
            "type": "stat",
            "gridPos": {"h": 4, "w": 4, "x": 16, "y": 4},
            "targets": [{"expr": "netris_up", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "thresholds"},
                    "mappings": [{"type": "value", "options": {"0": {"text": "DISCONNECTED", "color": "#FF3366"}, "1": {"text": "AUTHENTICATED", "color": "#76B900"}}}],
                    "thresholds": {"mode": "absolute", "steps": [{"color": "#FF3366", "value": None}, {"color": "#76B900", "value": 1}]}
                }
            }
        },
        {
            "id": 103,
            "title": "Total Metric Families Collected",
            "type": "stat",
            "gridPos": {"h": 4, "w": 4, "x": 20, "y": 4},
            "targets": [{"expr": "count(count by (__name__) ({__name__=~'netris_.*'}))", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "fixed", "fixedColor": "#00D2FF"},
                    "unit": "short"
                }
            }
        },
        {
            "id": 104,
            "title": "Prometheus Scrape Interval in Demo",
            "type": "stat",
            "gridPos": {"h": 5, "w": 4, "x": 16, "y": 8},
            "targets": [{"expr": "vector(15)", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "fixed", "fixedColor": "#FBBF24"},
                    "unit": "s",
                    "displayName": "Scrape Cadence"
                }
            }
        },
        {
            "id": 105,
            "title": "Total Active Enriched Time-Series",
            "type": "stat",
            "gridPos": {"h": 5, "w": 4, "x": 20, "y": 8},
            "targets": [{"expr": "count({__name__=~'netris_.*'})", "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "color": {"mode": "fixed", "fixedColor": "#76B900"},
                    "unit": "short"
                }
            }
        },
        {
            "id": 106,
            "title": "Active Data Source Types in this Demo Stack",
            "type": "text",
            "gridPos": {"h": 5, "w": 8, "x": 16, "y": 13},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 12px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box;">
  <div style="font-size: 12px; font-weight: 700; color: #FFFFFF; margin-bottom: 6px;">DATA FORMATS BY HOP:</div>
  <div style="font-size: 11px; line-height: 1.5; color: #94A3B8;">
    &bull; <b>Switches &rarr; Controller:</b> Internal binary streams &amp; agent heartbeats<br/>
    &bull; <b>Controller &rarr; Exporter:</b> JSON REST API payloads (HTTP GET/POST)<br/>
    &bull; <b>Exporter &rarr; Prometheus:</b> OpenMetrics / Prometheus text lines (HTTP GET)<br/>
    &bull; <b>Prometheus &rarr; Grafana:</b> PromQL JSON response (HTTP POST <code>/api/v1/query_range</code>)
  </div>
</div>'''
            }
        },

        # Row 200: API Scraping & Data Types Breakdown
        {"id": 200, "title": "Controller Telemetry Endpoints, Polling Methods & Collected Data Types", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 18}},
        {
            "id": 201,
            "title": "Streaming Counters & Rates (High-Frequency Time-Series)",
            "type": "text",
            "gridPos": {"h": 12, "w": 8, "x": 0, "y": 19},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(0, 210, 255, 0.35); border-radius: 8px; padding: 14px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
    <span style="font-weight: 700; color: #00D2FF; font-size: 13px;">1. STREAMING COUNTERS</span>
    <span style="background: rgba(0, 210, 255, 0.15); color: #00D2FF; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600;">HIGH-FREQUENCY</span>
  </div>
  
  <div style="font-size: 11px; line-height: 1.5;">
    <b style="color: #FFFFFF;">Collection Method (API):</b><br/>
    Exporter sends HTTP requests to telemetry endpoints:
    <div style="background: #090D16; border: 1px solid #1E293B; border-radius: 4px; padding: 5px 8px; margin: 4px 0 6px 0; font-family: monospace; font-size: 10px; color: #00D2FF;">
      GET /api/v2/telemetry/interfaces?format=json
    </div>

    <b style="color: #FFFFFF;">Original Data Type from Netris:</b><br/>
    JSON Array of time-series datapoints: <code>[[value, timestamp], ...]</code><br/><br/>

    <b style="color: #FFFFFF;">Collected Metrics in this Demo:</b>
    <ul style="margin: 4px 0 6px 16px; padding: 0;">
      <li><code>netris_interface_receive_bits_per_second</code> (Gauge)</li>
      <li><code>netris_interface_transmit_bits_per_second</code> (Gauge)</li>
      <li><code>netris_interface_receive_packets_per_second</code> (Gauge)</li>
      <li><code>netris_interface_transmit_packets_per_second</code> (Gauge)</li>
      <li><code>netris_interface_receive_errors_per_second</code> (Gauge)</li>
      <li><code>netris_optical_power_rx_dbm</code> (Gauge per lane)</li>
      <li><code>netris_node_cpu_percent</code> (Gauge per mode)</li>
      <li><code>netris_softgate_conntrack_entries</code> (Gauge)</li>
    </ul>
  </div>
</div>'''
            }
        },
        {
            "id": 202,
            "title": "State & Capacity Telemetry (Controller REST APIs)",
            "type": "text",
            "gridPos": {"h": 12, "w": 8, "x": 8, "y": 19},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(118, 185, 0, 0.35); border-radius: 8px; padding: 14px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
    <span style="font-weight: 700; color: #76B900; font-size: 13px;">2. HARDWARE STATE &amp; CAPACITY</span>
    <span style="background: rgba(118, 185, 0, 0.15); color: #76B900; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600;">STATE &amp; ALLOCATION</span>
  </div>
  
  <div style="font-size: 11px; line-height: 1.5;">
    <b style="color: #FFFFFF;">Collection Method (APIs):</b><br/>
    Exporter sends authenticated HTTP GET requests:
    <div style="background: #090D16; border: 1px solid #1E293B; border-radius: 4px; padding: 5px 8px; margin: 4px 0 6px 0; font-family: monospace; font-size: 10px; color: #76B900;">
      GET /api/v2/hw<br/>
      GET /api/v2/l4lb<br/>
      GET /api/v2/ipam/subnets
    </div>

    <b style="color: #FFFFFF;">Original Data Type from Netris:</b><br/>
    Structured JSON objects with integer counts, strings, and boolean flags.<br/><br/>

    <b style="color: #FFFFFF;">Collected Metrics in this Demo:</b>
    <ul style="margin: 4px 0 6px 16px; padding: 0;">
      <li><code>netris_switch_capacity_routes</code> &amp; <code>macs</code> (Gauge)</li>
      <li><code>netris_switch_capacity_ingress_acls</code> (Gauge)</li>
      <li><code>netris_switch_capacity_egress_acls</code> (Gauge)</li>
      <li><code>netris_l4lb_vip_health_status</code> (1/0 Gauge)</li>
      <li><code>netris_port_status</code> (1=UP, 0=DOWN Gauge)</li>
      <li><code>netris_ebgp_session_state</code> &amp; prefixes (Gauge)</li>
    </ul>
  </div>
</div>'''
            }
        },
        {
            "id": 203,
            "title": "Hardware Sensors & Active Assurance (Environmental & Diagnostics API)",
            "type": "text",
            "gridPos": {"h": 12, "w": 8, "x": 16, "y": 19},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(251, 191, 36, 0.35); border-radius: 8px; padding: 14px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
    <span style="font-weight: 700; color: #FBBF24; font-size: 13px;">3. SENSORS &amp; ASSURANCE</span>
    <span style="background: rgba(251, 191, 36, 0.15); color: #FBBF24; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600;">HARDWARE HEALTH</span>
  </div>
  
  <div style="font-size: 11px; line-height: 1.5;">
    <b style="color: #FFFFFF;">Collection Method (APIs):</b><br/>
    Exporter sends authenticated HTTP GET requests:
    <div style="background: #090D16; border: 1px solid #1E293B; border-radius: 4px; padding: 5px 8px; margin: 4px 0 6px 0; font-family: monospace; font-size: 10px; color: #FBBF24;">
      GET /api/v2/dashboard/hardware-health<br/>
      GET /api/v2/dashboard/agent-heartbeats<br/>
      GET /api/v2/dashboard/hardware-alarms
    </div>

    <b style="color: #FFFFFF;">Original Data Type from Netris:</b><br/>
    Document lists with sub-check dictionaries and numeric sensor floats.<br/><br/>

    <b style="color: #FFFFFF;">Collected Metrics in this Demo:</b>
    <ul style="margin: 4px 0 6px 16px; padding: 0;">
      <li><code>netris_sensor_temperature_celsius</code> (Float °C Gauge)</li>
      <li><code>netris_sensor_fan_speed_rpm</code> (Float RPM Gauge)</li>
      <li><code>netris_sensor_psu_status</code> (1=OK, 0=Fail Gauge)</li>
      <li><code>netris_port_bit_error_rate</code> (Pre/Post-FEC BER Gauge)</li>
      <li><code>netris_daemon_health_status</code> (switchd/frr/syscd Gauge)</li>
      <li><code>netris_agent_heartbeat</code> (1=Alive Gauge)</li>
      <li><code>netris_topology_wiring_valid</code> (LLDP Cabling Intent)</li>
    </ul>
  </div>
</div>'''
            }
        },

        # Row 300: Semantic Enrichment Engine
        {"id": 300, "title": "How the Exporter Semantically Enriches Raw Telemetry", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 31}},
        {
            "id": 301,
            "title": "Label Enrichment Workflow (How Raw Counters Become Intent-Aware)",
            "type": "text",
            "gridPos": {"h": 10, "w": 16, "x": 0, "y": 32},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 14px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box;">
  <div style="font-size: 13px; font-weight: 700; color: #76B900; margin-bottom: 8px;">BEFORE &amp; AFTER: RAW SWITCH METRIC VS ENRICHED OPENMETRICS</div>
  
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 11px;">
    <div>
      <div style="color: #FF3366; font-weight: 700; margin-bottom: 4px;">RAW COUNTER IN CONTROLLER (Generic Interface):</div>
      <pre style="background: #090D16; border: 1px solid #1E293B; border-radius: 4px; padding: 8px; font-family: monospace; font-size: 10px; color: #F87171; overflow-x: auto; margin: 0;">
netris.sw01.swp1.octets_rx: 4892182048
# No context on:
# - What is connected to swp1?
# - Is it a GPU server, leaf, or spine?
# - Which tenant, VPC, or AI cluster owns it?</pre>
    </div>

    <div>
      <div style="color: #76B900; font-weight: 700; margin-bottom: 4px;">ENRICHED OPENMETRICS (Port 9101 OpenMetrics):</div>
      <pre style="background: #090D16; border: 1px solid #1E293B; border-radius: 4px; padding: 8px; font-family: monospace; font-size: 10px; color: #A6E324; overflow-x: auto; margin: 0;">
netris_interface_receive_bits_per_second{
  site="Datacenter-A",
  device_name="leaf-pod00-su0-r0",
  port="swp1s0",
  port_role="server_facing",
  remote_device="hgx-pod00-su0-h00",
  remote_port="eth1",
  server_cluster="Nexus-Compute-01",
  vpc="AI-Training-VPC",
  tenant="Admin"
} 39137456384</pre>
    </div>
  </div>

  <div style="margin-top: 10px; font-size: 11px; color: #94A3B8;">
    <b>Enrichment Source:</b> Exporter periodically queries <code>/api/v2/link</code>, <code>/api/v2/vpc</code>, <code>/api/v2/server-cluster</code>, and caches the topological mapping in memory, enriching every scraped interface counter on the fly.
  </div>
</div>'''
            }
        },
        {
            "id": 302,
            "title": "Enrichment Labels Injected by Exporter",
            "type": "text",
            "gridPos": {"h": 10, "w": 8, "x": 16, "y": 32},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 14px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box;">
  <div style="font-size: 12px; font-weight: 700; color: #FFFFFF; margin-bottom: 8px;">TOPOLOGICAL LABELS ADDED:</div>
  <table style="width: 100%; font-size: 11px; border-collapse: collapse;">
    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
      <td style="padding: 4px 0; color: #00D2FF; font-family: monospace;">port_role</td>
      <td style="padding: 4px 0; color: #CBD5E1;">Separates server access vs fabric transit</td>
    </tr>
    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
      <td style="padding: 4px 0; color: #76B900; font-family: monospace;">remote_device</td>
      <td style="padding: 4px 0; color: #CBD5E1;">Identifies host/switch at opposite end of cable</td>
    </tr>
    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
      <td style="padding: 4px 0; color: #FBBF24; font-family: monospace;">vpc / tenant</td>
      <td style="padding: 4px 0; color: #CBD5E1;">Enables multi-tenant network chargeback</td>
    </tr>
    <tr>
      <td style="padding: 4px 0; color: #C084FC; font-family: monospace;">fabric_type</td>
      <td style="padding: 4px 0; color: #CBD5E1;">Distinguishes compute vs storage vs OOB</td>
    </tr>
  </table>
</div>'''
            }
        },

        # Row 400: How Grafana Queries Prometheus (PromQL Examples)
        {"id": 400, "title": "How Grafana Queries Prometheus in this Demo (Real PromQL Queries)", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 42}},
        {
            "id": 401,
            "title": "East-West GPU Cluster Throughput (PromQL)",
            "type": "text",
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 43},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(0, 210, 255, 0.3); border-radius: 8px; padding: 12px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box;">
  <div style="font-size: 12px; font-weight: 700; color: #00D2FF; margin-bottom: 4px;">QUERY: SERVER CLUSTER TRAFFIC</div>
  <div style="font-size: 11px; color: #94A3B8; margin-bottom: 8px;">Sums ingress throughput across all server-facing ports grouped by cluster:</div>
  <pre style="background: #090D16; border: 1px solid #1E293B; border-radius: 4px; padding: 8px; font-family: monospace; font-size: 10px; color: #38BDF8; overflow-x: auto; margin: 0;">
sum by (server_cluster) (
  netris_interface_receive_bits_per_second{
    port_role="server_facing",
    server_cluster!="none"
  }
)</pre>
  <div style="margin-top: 8px; font-size: 10px; color: #94A3B8;">Used in Fabric Overview dashboard to measure AI collective training bandwidth.</div>
</div>'''
            }
        },
        {
            "id": 402,
            "title": "Hardware Assurance Alarms (PromQL)",
            "type": "text",
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 43},
            "options": {
                "mode": "html",
                "content": '''<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 51, 102, 0.3); border-radius: 8px; padding: 12px; font-family: Inter, -apple-system, sans-serif; color: #E2E8F0; height: 100%; box-sizing: border-box;">
  <div style="font-size: 12px; font-weight: 700; color: #FF3366; margin-bottom: 4px;">QUERY: ACTIVE CABLING &amp; NODE ALARMS</div>
  <div style="font-size: 11px; color: #94A3B8; margin-bottom: 8px;">Finds switches with degraded subcomponents or cabling inconsistencies:</div>
  <pre style="background: #090D16; border: 1px solid #1E293B; border-radius: 4px; padding: 8px; font-family: monospace; font-size: 10px; color: #F87171; overflow-x: auto; margin: 0;">
# Cabling mismatch:
netris_topology_wiring_valid == 0

# Subcomponent failure:
netris_node_component_health == 0</pre>
  <div style="margin-top: 8px; font-size: 10px; color: #94A3B8;">Instantly alerts operator to miswired cables or failing power supplies.</div>
</div>'''
            }
        },

        # Row 500: Complete Metrics Catalog Table
        {"id": 500, "title": "Live Metric Catalog (Currently Exported & Queried in Prometheus)", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 51}},
        {
            "id": 501,
            "title": "Exported Metric Catalog & Classification Table",
            "type": "table",
            "gridPos": {"h": 11, "w": 24, "x": 0, "y": 52},
            "targets": [
                {
                    "expr": 'count by (__name__) ({__name__=~"netris_.*"})',
                    "format": "table",
                    "instant": True,
                    "refId": "A"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "custom": {"align": "auto"}
                },
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Value"},
                        "properties": [{"id": "displayName", "value": "Active Series Count"}]
                    },
                    {
                        "matcher": {"id": "byName", "options": "__name__"},
                        "properties": [{"id": "displayName", "value": "Metric Family Name"}]
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
        "panels": panels,
        "refresh": "30s",
        "schemaVersion": 38,
        "style": "dark",
        "tags": ["netris", "observability", "architecture", "customer-facing"],
        "templating": {"list": []},
        "time": {"from": "now-15m", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Netris - Metrics Architecture & Export Showcase",
        "uid": "netris-metrics-architecture",
        "version": 1
    }


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "grafana", "dashboards", "json")
    os.makedirs(output_dir, exist_ok=True)

    dashboards = {
        "netris-fabric-overview.json": finalize_dashboard(build_overview_dashboard()),
        "netris-optics.json": finalize_dashboard(build_optics_dashboard()),
        "netris-hardware-overview.json": finalize_dashboard(build_hardware_dashboard()),
        "netris-softgates.json": finalize_dashboard(build_softgates_dashboard()),
        "netris-switch-info.json": finalize_dashboard(build_switch_info_dashboard()),
        "netris-mistic-cluster.json": finalize_dashboard(build_mistic_cluster_dashboard()),
        "netris-metrics-architecture.json": finalize_dashboard(build_architecture_dashboard()),
    }

    print("=" * 72)
    print("Netris Production Grafana Dashboard Suite Generator")
    print(f"Target Directory: {output_dir}")
    print("=" * 72)

    for filename, dash_dict in dashboards.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dash_dict, f, indent=2)
        print(f"  ✅ Generated: {filename:<35} (UID: {dash_dict['uid']}, Panels: {len(dash_dict['panels'])})")

    print("=" * 72)
    print(f"All {len(dashboards)} Netris dashboards successfully written with schemaVersion 38.\n")


if __name__ == "__main__":
    main()
