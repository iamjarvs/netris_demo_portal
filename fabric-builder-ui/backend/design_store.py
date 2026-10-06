"""
design_store.py
Persistent JSON storage for Netris fabric designs with pre-loaded reference templates.
"""

import os
import json
import time
import re
from typing import Dict, Any, List, Optional

DESIGNS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "saved_designs"))


STARTER_TEMPLATES = [
    {
        "id": "msp2-dual-plane",
        "name": "MSP2 Dual-Plane RoCE Fabric",
        "description": "Dual-rail 64-port Spectrum-X fabric with 8 Spines, 16 Leaves, 16 RoCE ports per GPU, and dedicated storage & OOB tiers.",
        "created_at": "2026-09-14T00:00:00Z",
        "updated_at": "2026-09-14T00:00:00Z",
        "config": {
            "site_name": "MSP02",
            "planes_count": 2,
            "ew_spines_per_plane": 2,
            "ew_leaves_per_plane": 4,
            "switch_port_count": 64,
            "nos": "cumulus_nvue",
            "softgate_flavor": "sg-hs",
            "public_asn": 65501,
            "roh_asn": 65502,
            "switch_asn_base": 4200000000,
            "gpu_count": 8,
            "gpu_roce_ports": 16,
            "gpu_ns_ports": 2,
            "ns_spines": 2,
            "ns_leaves": 2,
            "softgate_count": 2,
            "enable_storage": True,
            "storage_leaves": 2,
            "storage_servers": 4,
            "storage_subnet": "10.200.0.0/24",
            "enable_oob": True,
            "oob_switches": 2,
            "oob_subnet": "10.10.0.0/24",
            "ew_loopback_subnet": "10.253.128.0/24",
            "ew_p2p_allocation": "10.254.0.0/16",
            "ns_loopback_subnet": "10.25.105.0/24",
            "ns_mgmt_subnet": "10.100.0.0/24",
            "controller_address": "https://adam-ctl.netris.io",
            "controller_login": "netris",
            "controller_password": "913QGAi6oQTSGgZm20eU",
            "timezone": "Etc/GMT",
            "ntp_servers": ["1.pool.ntp.org", "2.pool.ntp.org"],
            "dns_servers": ["1.1.1.1", "8.8.8.8"]
        }
    },
    {
        "id": "kpn01-quad-plane",
        "name": "KPN01 Quad-Plane Ultra-Scale Fabric",
        "description": "Quad-plane 4-rail backend RoCE fabric with 128-port switches for maximum GPU cluster scale and zero cross-plane contention.",
        "created_at": "2026-09-14T00:00:00Z",
        "updated_at": "2026-09-14T00:00:00Z",
        "config": {
            "site_name": "KPN01",
            "planes_count": 4,
            "ew_spines_per_plane": 2,
            "ew_leaves_per_plane": 4,
            "switch_port_count": 128,
            "nos": "cumulus_nvue",
            "softgate_flavor": "sg-hs",
            "public_asn": 65510,
            "roh_asn": 65511,
            "switch_asn_base": 4200100000,
            "gpu_count": 16,
            "gpu_roce_ports": 16,
            "gpu_ns_ports": 2,
            "ns_spines": 2,
            "ns_leaves": 2,
            "softgate_count": 2,
            "enable_storage": True,
            "storage_leaves": 2,
            "storage_servers": 8,
            "storage_subnet": "10.201.0.0/24",
            "enable_oob": True,
            "oob_switches": 2,
            "oob_subnet": "10.11.0.0/24",
            "ew_loopback_subnet": "10.252.128.0/24",
            "ew_p2p_allocation": "10.252.0.0/16",
            "ns_loopback_subnet": "10.26.105.0/24",
            "ns_mgmt_subnet": "10.101.0.0/24",
            "controller_address": "https://adam-ctl.netris.io",
            "controller_login": "netris",
            "controller_password": "913QGAi6oQTSGgZm20eU",
            "timezone": "Etc/GMT",
            "ntp_servers": ["1.pool.ntp.org", "2.pool.ntp.org"],
            "dns_servers": ["1.1.1.1", "8.8.8.8"]
        }
    },
    {
        "id": "chl2-single-plane",
        "name": "CHL2 Single-Plane Standard Fabric",
        "description": "Standard single-plane East-West Clos fabric with 32-port switches for compact AI training or inference clusters.",
        "created_at": "2026-09-14T00:00:00Z",
        "updated_at": "2026-09-14T00:00:00Z",
        "config": {
            "site_name": "CHL02",
            "planes_count": 1,
            "ew_spines_per_plane": 2,
            "ew_leaves_per_plane": 2,
            "switch_port_count": 32,
            "nos": "cumulus_nvue",
            "softgate_flavor": "sg-std",
            "public_asn": 65520,
            "roh_asn": 65521,
            "switch_asn_base": 4200200000,
            "gpu_count": 4,
            "gpu_roce_ports": 8,
            "gpu_ns_ports": 2,
            "ns_spines": 2,
            "ns_leaves": 2,
            "softgate_count": 2,
            "enable_storage": False,
            "storage_leaves": 2,
            "storage_servers": 2,
            "storage_subnet": "10.202.0.0/24",
            "enable_oob": True,
            "oob_switches": 2,
            "oob_subnet": "10.12.0.0/24",
            "ew_loopback_subnet": "10.251.128.0/24",
            "ew_p2p_allocation": "10.251.0.0/16",
            "ns_loopback_subnet": "10.27.105.0/24",
            "ns_mgmt_subnet": "10.102.0.0/24",
            "controller_address": "https://adam-ctl.netris.io",
            "controller_login": "netris",
            "controller_password": "913QGAi6oQTSGgZm20eU",
            "timezone": "Etc/GMT",
            "ntp_servers": ["1.pool.ntp.org", "2.pool.ntp.org"],
            "dns_servers": ["1.1.1.1", "8.8.8.8"]
        }
    }
]


class DesignStore:
    def __init__(self):
        os.makedirs(DESIGNS_DIR, exist_ok=True)
        self._ensure_starter_templates()

    def _ensure_starter_templates(self):
        """Seed starter templates if designs directory is empty."""
        for tmpl in STARTER_TEMPLATES:
            file_path = os.path.join(DESIGNS_DIR, f"{tmpl['id']}.json")
            if not os.path.exists(file_path):
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(tmpl, f, indent=2)
                except Exception:
                    pass

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
        return slug or f"design-{int(time.time())}"

    def list_designs(self) -> List[Dict[str, Any]]:
        """List all saved designs with summary information."""
        designs = []
        if not os.path.exists(DESIGNS_DIR):
            return designs

        for fname in sorted(os.listdir(DESIGNS_DIR)):
            if fname.endswith(".json"):
                fpath = os.path.join(DESIGNS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        cfg = data.get("config", {})
                        designs.append({
                            "id": data.get("id", fname[:-5]),
                            "name": data.get("name", "Untitled Design"),
                            "description": data.get("description", ""),
                            "created_at": data.get("created_at", ""),
                            "updated_at": data.get("updated_at", ""),
                            "site_name": cfg.get("site_name", "N/A"),
                            "planes_count": cfg.get("planes_count", 1),
                            "switch_count": (
                                (cfg.get("planes_count", 1) * (cfg.get("ew_spines_per_plane", 2) + cfg.get("ew_leaves_per_plane", 4)))
                                + (cfg.get("ns_spines", 2) + cfg.get("ns_leaves", 2))
                                + (cfg.get("storage_leaves", 2) if cfg.get("enable_storage") else 0)
                                + (cfg.get("oob_switches", 2) if cfg.get("enable_oob") else 0)
                            ),
                            "gpu_count": cfg.get("gpu_count", 0),
                            "port_density": cfg.get("switch_port_count", 64),
                        })
                except Exception:
                    pass

        # Sort recently updated first
        designs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return designs

    def get_design(self, design_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full design content by id."""
        fpath = os.path.join(DESIGNS_DIR, f"{design_id}.json")
        if not os.path.exists(fpath):
            return None
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_design(self, name: str, description: str, config: Dict[str, Any], design_id: Optional[str] = None) -> Dict[str, Any]:
        """Save a new design or overwrite an existing design."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if not design_id:
            design_id = self._slugify(name)
        
        fpath = os.path.join(DESIGNS_DIR, f"{design_id}.json")
        created_at = now
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    prev = json.load(f)
                    created_at = prev.get("created_at", now)
            except Exception:
                pass

        record = {
            "id": design_id,
            "name": name,
            "description": description,
            "created_at": created_at,
            "updated_at": now,
            "config": config,
        }

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        return record

    def delete_design(self, design_id: str) -> bool:
        """Delete a saved design."""
        fpath = os.path.join(DESIGNS_DIR, f"{design_id}.json")
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
                return True
            except Exception:
                return False
        return False


design_store = DesignStore()
