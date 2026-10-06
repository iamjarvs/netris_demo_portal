#!/usr/bin/env python3
"""Netris Grafana Dashboard Suite Generator.

Generates executive and engineering-grade Grafana dashboards for the Netris Observability Stack:
1. netris-fabric-overview.json: General Overview (High-level glance & active assurance alerts)
2. netris-optics.json: Optics & Physical Layer (Optical transceivers, RX dBm, lanes, BER)
3. netris-hardware-overview.json: Hardware Overview (CPU, Disk, Memory, Fans, PSUs, NOS software versions)
4. netris-softgates.json: SoftGates Border & NAT Telemetry (Conntrack, throughput, VIPs, CPU/RAM)
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
        ("softgates", "🛡️ SoftGates", "/d/netris-softgates"),
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
    # Intentionally empty to remove the top redundant dashboard link bar
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

print("Generator skeleton loaded.")
