"""
tf_generator.py
Generates modular OpenTofu / Terraform configurations and CSV files
supporting Single, Dual, and Quad Plane backend fabrics and frontend networks.
"""

import ipaddress
import re
import math
from typing import Dict, Any, List, Tuple


def normalize_softgate_flavor(flavor: str) -> str:
    fl = str(flavor or "").strip().lower()
    if "hs" in fl:
        return "sg-hs"
    return "sg-pro"


def auto_calculate_backend_fabric(
    gpu_count: int,
    roce_ports: int = 8,
    planes_count: int = 2,
    switch_port_count: int = 64,
    oversubscription_ratio: float = 1.0,
) -> Dict[str, Any]:
    """
    Auto-calculates the optimal East-West AI Clos backend fabric:
    - Determines ports per GPU per plane.
    - Slices switch ports into downlinks and uplinks based on oversubscription ratio.
    - Calculates required leaves per plane and spines per plane.
    - Balances line-rate parallel spine uplinks.
    """
    ports_per_plane = max(1, roce_ports // max(1, planes_count))
    max_downlinks_per_leaf = switch_port_count // 2 if oversubscription_ratio <= 1.0 else int(switch_port_count * (oversubscription_ratio / (1 + oversubscription_ratio)))
    max_gpus_per_leaf = max(1, max_downlinks_per_leaf // ports_per_plane)
    
    ew_leaves_per_plane = max(2, math.ceil(gpu_count / max_gpus_per_leaf))
    if ew_leaves_per_plane > 2 and ew_leaves_per_plane % 2 != 0:
        ew_leaves_per_plane += 1

    actual_gpus_per_leaf = math.ceil(gpu_count / ew_leaves_per_plane)
    actual_downlinks = actual_gpus_per_leaf * ports_per_plane
    needed_uplinks = max(1, math.ceil(actual_downlinks / oversubscription_ratio))

    if ew_leaves_per_plane <= 16:
        ew_spines_per_plane = 2
    elif ew_leaves_per_plane <= 32:
        ew_spines_per_plane = 4
    else:
        ew_spines_per_plane = 8

    links_per_spine = max(1, math.ceil(needed_uplinks / ew_spines_per_plane))
    max_spine_links = max(1, switch_port_count // ew_leaves_per_plane)
    links_per_spine = min(links_per_spine, max_spine_links)
    total_uplinks = links_per_spine * ew_spines_per_plane

    total_backend_spines = ew_spines_per_plane * planes_count
    total_backend_leaves = ew_leaves_per_plane * planes_count
    total_ports_used = actual_downlinks + total_uplinks
    port_utilization_pct = min(100, round((total_ports_used / switch_port_count) * 100))

    return {
        "ew_leaves_per_plane": ew_leaves_per_plane,
        "ew_spines_per_plane": ew_spines_per_plane,
        "total_backend_leaves": total_backend_leaves,
        "total_backend_spines": total_backend_spines,
        "ports_per_plane": ports_per_plane,
        "downlinks_per_leaf": actual_downlinks,
        "uplinks_per_leaf": total_uplinks,
        "links_per_spine": links_per_spine,
        "port_utilization_pct": port_utilization_pct,
        "actual_ratio": f"{(actual_downlinks / max(1, total_uplinks)):.2f}:1",
    }


def auto_calculate_ns_fabric(
    gpu_count: int,
    gpu_ns_ports: int = 2,
    storage_servers: int = 4,
    storage_ns_ports: int = 2,
    cp_servers: int = 3,
    switch_port_count: int = 64,
    softgate_flavor: str = "sg-hs"
) -> Dict[str, Any]:
    """
    Auto-calculates the optimal North-South fabric sizing:
    - Calculates required downlinks for GPU servers, Storage servers, and K8s Control Plane nodes.
    - Sizes NS leaves in redundant pairs so leaf downlinks are never oversubscribed and leave
      room for spine uplinks and dual-homed SoftGates.
    - Sizes NS spines (2 or 4) to ensure non-blocking North-South transit.
    - Sizes SoftGates (minimum 2 for active-active HA, scales with bandwidth).
    """
    total_downlinks = (gpu_count * gpu_ns_ports) + (storage_servers * storage_ns_ports) + (cp_servers * 2)
    
    reserved_per_leaf = 8 if switch_port_count >= 64 else 6
    available_downlinks_per_leaf = max(1, switch_port_count - reserved_per_leaf)
    
    raw_leaves = math.ceil(total_downlinks / available_downlinks_per_leaf)
    ns_leaves = max(2, raw_leaves if raw_leaves % 2 == 0 else raw_leaves + 1)
    ns_spines = 2 if ns_leaves <= 16 else 4
    softgate_count = 2 if gpu_count <= 32 else 4
    
    return {
        "ns_leaves": ns_leaves,
        "ns_spines": ns_spines,
        "softgate_count": softgate_count,
        "total_downlinks": total_downlinks,
        "downlinks_per_leaf": math.ceil(total_downlinks / ns_leaves)
    }


def auto_calculate_oob_fabric(
    total_switches: int,
    total_servers: int,
) -> Dict[str, Any]:
    """
    Auto-sizes Out-of-Band (OOB) management network based on all physical switches + servers:
    Every switch mgmt port + every server BMC/IPMI port connects to 48-port OOB switches.
    Ports 47 & 48 are reserved for redundant ISL trunks between OOB switches, leaving 44 usable ports.
    """
    total_endpoints = total_switches + total_servers
    raw_oob = math.ceil(total_endpoints / 44)
    oob_switches = max(2, raw_oob if raw_oob % 2 == 0 else raw_oob + 1)
    return {
        "oob_switches": oob_switches,
        "total_endpoints": total_endpoints,
        "total_switch_mgmt_ports": total_switches,
        "total_server_bmc_ports": total_servers,
        "usable_ports_per_switch": 44,
        "total_oob_capacity": oob_switches * 44,
    }


def auto_calculate_entire_fabric(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive multi-tier fabric auto-sizing calculator:
    Evaluates GPU fleet, planes, backend Clos, frontend fabric, storage architecture,
    and Out-of-Band management in a unified sizing matrix.
    """
    gpu_count = int(config.get("gpu_count", 8))
    roce_ports = int(config.get("gpu_roce_ports", 8))
    gpu_ns_ports = int(config.get("gpu_ns_ports", 2))
    planes_count = int(config.get("planes_count", 2))
    switch_port_count = int(config.get("switch_port_count", 64))
    
    raw_ratio = config.get("oversubscription_ratio", "1:1")
    ratio = TerraformGenerator._parse_ratio(raw_ratio)
    
    enable_storage = bool(config.get("enable_storage", True))
    storage_mode = config.get("storage_network_mode", "converged")
    storage_servers = int(config.get("storage_servers", 4)) if enable_storage else 0
    storage_ns_ports = int(config.get("storage_ns_ports", 2))
    storage_roce_ports = int(config.get("storage_roce_ports", 2))
    
    # 1. Backend AI Clos Fabric
    backend = auto_calculate_backend_fabric(
        gpu_count=gpu_count,
        roce_ports=roce_ports,
        planes_count=planes_count,
        switch_port_count=switch_port_count,
        oversubscription_ratio=ratio
    )
    
    # 2. Frontend North-South Fabric
    frontend = auto_calculate_ns_fabric(
        gpu_count=gpu_count,
        gpu_ns_ports=gpu_ns_ports,
        storage_servers=storage_servers if storage_mode == "converged" else 0,
        storage_ns_ports=storage_ns_ports,
        cp_servers=3,
        switch_port_count=switch_port_count,
        softgate_flavor=config.get("softgate_flavor", "sg-hs")
    )
    
    # 3. Storage Network
    if enable_storage and storage_mode == "standalone":
        storage_leaves = max(2, math.ceil((storage_servers * storage_roce_ports) / (switch_port_count // 2)))
        if storage_leaves % 2 != 0:
            storage_leaves += 1
    else:
        storage_leaves = 0
        
    # 4. Total Switches & Servers
    total_switches = (
        backend["total_backend_spines"] + 
        backend["total_backend_leaves"] + 
        frontend["ns_spines"] + 
        frontend["ns_leaves"] + 
        storage_leaves + 
        frontend["softgate_count"]
    )
    total_servers = gpu_count + storage_servers + 3 # 3 K8s CP servers
    
    # 5. Out-of-Band Management
    oob = auto_calculate_oob_fabric(total_switches=total_switches, total_servers=total_servers)
    
    return {
        "backend": backend,
        "frontend": frontend,
        "storage": {
            "mode": storage_mode,
            "servers": storage_servers,
            "leaves": storage_leaves,
            "nvd_bw_per_gpu": f"{(gpu_ns_ports * 100 / (2 if storage_mode == 'converged' else 1)):.1f} Gbps",
            "nvd_certified": (gpu_ns_ports * 100 / (2 if storage_mode == 'converged' else 1)) >= 11.1
        },
        "oob": oob,
        "totals": {
            "total_switches": total_switches + oob["oob_switches"],
            "total_network_switches": total_switches,
            "total_oob_switches": oob["oob_switches"],
            "total_servers": total_servers,
            "gpu_count": gpu_count,
            "storage_servers": storage_servers,
            "cp_servers": 3
        }
    }


class TerraformGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config
        self.site_name = config.get("site_name", "Demo-Fabric")
        self.site_slug = self.site_name.lower().replace(" ", "-")
        self.site_id = config.get("site_id", 1)
        self.public_asn = config.get("public_asn", 65500)
        self.switch_asn_base = config.get("switch_asn_base", 4200000000)
        self.roh_asn = config.get("roh_asn", 65501)
        self.switch_port_count = int(config.get("switch_port_count", 64))
        self.nos = config.get("nos", "cumulus_nvue")
        self.switch_nos = self.nos
        self.softgate_flavor = config.get("softgate_flavor", "sg-hs")
        self.tenant_name = config.get("tenant_name", "Admin")

        # Planes & GPU Compute sizing
        self.planes_count = int(config.get("planes_count", 2))
        self.ew_spines_per_plane = int(config.get("ew_spines_per_plane", 2))
        self.ew_leaves_per_plane = int(config.get("ew_leaves_per_plane", 2))
        # GPU / Servers Profiles
        gpu_prof = config.get("gpu_profile", {})
        self.gpu_count = int(config.get("gpu_count", 4))
        if isinstance(gpu_prof, dict):
            self.gpu_roce_ports = int(gpu_prof.get("roce_ports", config.get("gpu_roce_ports", 8)))
            self.gpu_ns_ports = int(gpu_prof.get("ns_ports", config.get("gpu_ns_ports", 2)))
            self.gpu_oob_ports = int(gpu_prof.get("oob_ports", config.get("gpu_oob_ports", 1)))
            self.gpu_profile_name = str(gpu_prof.get("name", "NVIDIA HGX H100/H200/B200"))
        else:
            self.gpu_roce_ports = int(config.get("gpu_roce_ports", 8))
            self.gpu_ns_ports = int(config.get("gpu_ns_ports", 2))
            self.gpu_oob_ports = int(config.get("gpu_oob_ports", 1))
            self.gpu_profile_name = str(config.get("gpu_profile", "Custom"))
        
        # Storage Network Architecture (Converged vs Standalone)
        self.enable_storage = bool(config.get("enable_storage", True))
        self.storage_network_mode = config.get("storage_network_mode", "standalone") # "standalone" vs "converged"
        storage_prof = config.get("storage_profile", {})
        self.storage_servers = int(config.get("storage_servers", 4)) if self.enable_storage else 0
        if isinstance(storage_prof, dict):
            self.storage_roce_ports = int(storage_prof.get("roce_ports", config.get("storage_roce_ports", 2)))
            self.storage_ns_ports = int(storage_prof.get("ns_ports", config.get("storage_ns_ports", 2)))
            self.storage_oob_ports = int(storage_prof.get("oob_ports", config.get("storage_oob_ports", 1)))
        else:
            self.storage_roce_ports = int(config.get("storage_roce_ports", 2))
            self.storage_ns_ports = int(config.get("storage_ns_ports", 2))
            self.storage_oob_ports = int(config.get("storage_oob_ports", 1))
        
        if self.enable_storage and self.storage_network_mode == "standalone":
            self.storage_leaves = int(config.get("storage_leaves", 2))
        else:
            self.storage_leaves = 0

        # North-South Auto-Optimization
        self.auto_optimize_ns = bool(config.get("auto_optimize_ns", False))
        if self.auto_optimize_ns:
            recom = auto_calculate_ns_fabric(
                gpu_count=self.gpu_count,
                gpu_ns_ports=self.gpu_ns_ports,
                storage_servers=self.storage_servers,
                storage_ns_ports=self.storage_ns_ports,
                switch_port_count=self.switch_port_count,
                softgate_flavor=self.softgate_flavor
            )
            self.ns_spines = recom["ns_spines"]
            self.ns_leaves = recom["ns_leaves"]
            self.softgate_count = recom["softgate_count"]
            self.oob_switches = recom.get("oob_switches", int(config.get("oob_switches", 2)))
        else:
            self.ns_spines = int(config.get("ns_spines", 2))
            self.ns_leaves = int(config.get("ns_leaves", 2))
            self.softgate_count = int(config.get("softgate_count", 2))
            self.oob_switches = int(config.get("oob_switches", 2))

        # Hardware Port Guard: ensure physical port limits are never exceeded regardless of manual inputs
        min_leaves_needed = math.ceil(
            ((self.gpu_count * self.gpu_ns_ports) + 
             (self.storage_servers * self.storage_ns_ports if (self.enable_storage and self.storage_network_mode == "converged") else 0) + 6) / 
            max(1, self.switch_port_count - 8)
        )
        if min_leaves_needed > self.ns_leaves:
            min_leaves_needed = min_leaves_needed if min_leaves_needed % 2 == 0 else min_leaves_needed + 1
            self.ns_leaves = max(self.ns_leaves, min_leaves_needed)

        self.enable_oob = bool(config.get("enable_oob", True))
        if self.enable_oob:
            total_oob_endpoints = self.gpu_count + (self.storage_servers if self.enable_storage else 0) + 3
            raw_oob_needed = math.ceil(total_oob_endpoints / 44)
            min_oob_needed = max(2, raw_oob_needed if raw_oob_needed % 2 == 0 else raw_oob_needed + 1)
            if min_oob_needed > self.oob_switches:
                self.oob_switches = min_oob_needed
        
        # IPAM
        self.ew_loopback_subnet = config.get("ew_loopback_subnet", "172.16.0.0/24")
        self.ew_p2p_allocation = config.get("ew_p2p_allocation", "172.17.0.0/16")
        self.ns_loopback_subnet = config.get("ns_loopback_subnet", "172.16.1.0/24")
        self.ns_mgmt_subnet = config.get("ns_mgmt_subnet", "172.16.2.0/24")
        self.storage_subnet = config.get("storage_subnet", "172.16.3.0/24")
        self.oob_subnet = config.get("oob_subnet", "172.16.4.0/24")
        
        self.naming_scheme = config.get("naming_scheme", "verbose") # verbose, plane_focused, compact
        
        # Oversubscription Ratio (e.g. 1.0 for 1:1, 2.0 for 2:1, 3.0 for 3:1, 4.0 for 4:1)
        raw_ratio = config.get("oversubscription_ratio", 1.0)
        self.oversubscription_ratio = self._parse_ratio(raw_ratio)
        
        # Timezone / NTP / DNS
        self.timezone = config.get("timezone", "Etc/GMT")
        self.ntp_servers = config.get("ntp_servers", ["1.pool.ntp.org", "2.pool.ntp.org"])
        self.dns_servers = config.get("dns_servers", ["1.1.1.1", "8.8.8.8"])

        # Netris Provider Profile & Site Advanced Settings
        self.acl_default_policy = config.get("acl_default_policy", "permit")
        self.vlan_range = config.get("vlan_range", "2-4094")
        self.vlan_range_auto_assign = config.get("vlan_range_auto_assign", "2-3999")
        self.roce_adaptive_routing = bool(config.get("roce_adaptive_routing", True))
        self.congestion_control = bool(config.get("congestion_control", True))
        self.qos_and_roce = bool(config.get("qos_and_roce", True))
        self.aggregate_l3vpn_prefix = bool(config.get("aggregate_l3vpn_prefix", True))
        self.unnumbered_bgp_underlay = bool(config.get("unnumbered_bgp_underlay", True))
        self.optimise_bgp_overlay = bool(config.get("optimise_bgp_overlay", True))
        self.automatic_link_aggregation_ns = bool(config.get("automatic_link_aggregation_ns", True))
        self.automatic_link_aggregation_ew = bool(config.get("automatic_link_aggregation_ew", False))
        self.refarch_override = config.get("refarch", "")

    @staticmethod
    def _parse_ratio(val: Any) -> float:
        if isinstance(val, (int, float)):
            return float(val) if val > 0 else 1.0
        if isinstance(val, str):
            val = val.strip()
            if ":" in val:
                parts = val.split(":")
                try:
                    num = float(parts[0])
                    denom = float(parts[1]) if len(parts) > 1 and float(parts[1]) > 0 else 1.0
                    return num / denom
                except (ValueError, ZeroDivisionError):
                    return 1.0
            try:
                return float(val)
            except ValueError:
                return 1.0
        return 1.0

    # -------------------------------------------------------------------------
    # Switch & Node Naming Helpers (Verbose, Plane-Specific, and Intuitive)
    # -------------------------------------------------------------------------

    def get_backend_spine_name(self, plane: int, spine_idx: int) -> str:
        if self.naming_scheme == "plane_focused":
            return f"sw-{self.site_slug}-plane{plane}-spine{spine_idx:02d}"
        elif self.naming_scheme == "compact":
            return f"sw-{self.site_slug}-ew-pl{plane}-sp{spine_idx:02d}"
        return f"sw-{self.site_slug}-backend-plane{plane}-spine{spine_idx:02d}"

    def get_backend_leaf_name(self, plane: int, leaf_idx: int) -> str:
        if self.naming_scheme == "plane_focused":
            return f"sw-{self.site_slug}-plane{plane}-leaf{leaf_idx:02d}"
        elif self.naming_scheme == "compact":
            return f"sw-{self.site_slug}-ew-pl{plane}-lf{leaf_idx:02d}"
        return f"sw-{self.site_slug}-backend-plane{plane}-leaf{leaf_idx:02d}"

    def get_frontend_spine_name(self, spine_idx: int) -> str:
        if self.naming_scheme == "compact":
            return f"sw-{self.site_slug}-ns-sp{spine_idx:02d}"
        return f"sw-{self.site_slug}-frontend-spine{spine_idx:02d}"

    def get_frontend_leaf_name(self, leaf_idx: int) -> str:
        if self.naming_scheme == "compact":
            return f"sw-{self.site_slug}-ns-lf{leaf_idx:02d}"
        return f"sw-{self.site_slug}-frontend-leaf{leaf_idx:02d}"

    def get_storage_leaf_name(self, leaf_idx: int) -> str:
        if self.naming_scheme == "compact":
            return f"sw-{self.site_slug}-storage-lf{leaf_idx:02d}"
        return f"sw-{self.site_slug}-storage-leaf{leaf_idx:02d}"

    def get_oob_switch_name(self, oob_idx: int) -> str:
        if self.naming_scheme == "compact":
            return f"sw-{self.site_slug}-oob-sw{oob_idx:02d}"
        return f"sw-{self.site_slug}-oob-mgmt{oob_idx:02d}"

    def get_softgate_name(self, sg_idx: int) -> str:
        if self.naming_scheme == "compact":
            return f"sg-{self.site_slug}-{sg_idx:02d}"
        return f"sg-{self.site_slug}-border-gw{sg_idx:02d}"

    def generate_all_files(self) -> Dict[str, str]:
        """Generates all .tf, .tfvars, and csv/* files as a filename -> content map."""
        files = {}
        
        # 1. Main HCL files
        files["terraform.tf"] = self._gen_terraform_tf()
        files["terraform.tfvars"] = self._gen_terraform_tfvars()
        files["inventory_profile.tf"] = self._gen_inventory_profile_tf()
        files["ipam.tf"] = self._gen_ipam_tf()
        files["switches.tf"] = self._gen_switches_tf()
        files["softgates.tf"] = self._gen_softgates_tf()
        files["servers_gpu.tf"] = self._gen_servers_gpu_tf()
        files["servers_mgmt.tf"] = self._gen_servers_mgmt_tf()
        if self.enable_storage:
            files["servers_storage.tf"] = self._gen_servers_storage_tf()
        files["vpc.tf"] = self._gen_vpc_tf()
        files["vnets.tf"] = self._gen_vnets_tf()
        
        # Interconnects
        files["links_ew_switch.tf"] = self._gen_links_ew_switch_tf()
        files["links_ew_gpu.tf"] = self._gen_links_ew_gpu_tf()
        files["links_ns_switch.tf"] = self._gen_links_ns_switch_tf()
        files["links_ns_gpu.tf"] = self._gen_links_ns_gpu_tf()
        files["links_softgate.tf"] = self._gen_links_softgate_tf()
        if self.enable_storage:
            files["links_storage.tf"] = self._gen_links_storage_tf()
        if self.enable_oob:
            files["links_oob_switch.tf"] = self._gen_links_oob_switch_tf()
        files["breakouts.tf"] = self._gen_breakouts_tf()
        files["README.md"] = self._gen_readme()
        
        # 2. CSV Data files
        files["csv/switches.csv"] = self._gen_csv_switches()
        files["csv/softgates.csv"] = self._gen_csv_softgates()
        files["csv/servers_gpu.csv"] = self._gen_csv_servers_gpu()
        files["csv/servers_mgmt.csv"] = self._gen_csv_servers_mgmt()
        if self.enable_storage:
            files["csv/servers_storage.csv"] = self._gen_csv_servers_storage()
        files["csv/ipam.csv"] = self._gen_csv_ipam()
        files["csv/vnets.csv"] = self._gen_csv_vnets()
        files["csv/links_ew_switch.csv"] = self._gen_csv_links_ew_switch()
        files["csv/links_ew_gpu.csv"] = self._gen_csv_links_ew_gpu()
        files["csv/links_ns_switch.csv"] = self._gen_csv_links_ns_switch()
        files["csv/links_ns_gpu.csv"] = self._gen_csv_links_ns_gpu()
        files["csv/links_softgate.csv"] = self._gen_csv_links_softgate()
        if self.enable_storage:
            files["csv/links_storage.csv"] = self._gen_csv_links_storage()
        if self.enable_oob:
            files["csv/links_oob_switch.csv"] = self._gen_csv_links_oob_switch()
        files["csv/breakouts.csv"] = "switch,port,speed\n"
        
        return files

    def _gen_terraform_tf(self) -> str:
        return f"""# -----------------------------------------------------------------------------
# Terraform Configuration — Netris Multi-Plane Fabric Day-0
# Site: {self.site_name} | Backend Planes: {self.planes_count}
# -----------------------------------------------------------------------------

terraform {{
  required_providers {{
    netris = {{
      source  = "netrisai/netris"
      version = ">= 3.6.20, < 4.0.0"
    }}
  }}
  required_version = ">= 1.7"
}}

provider "netris" {{
  address  = var.controller_address
  login    = var.controller_login
  password = var.controller_password
}}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

variable "controller_address" {{
  type        = string
  description = "URL for Netris controller (e.g. https://adam-ctl.netris.io)"
}}

variable "controller_login" {{
  type        = string
  default     = "netris"
  description = "Admin login username"
}}

variable "controller_password" {{
  type        = string
  description = "Admin login password"
  sensitive   = true
}}

variable "site_name" {{
  type        = string
  default     = "{self.site_name}"
  description = "Datacenter site identifier"
}}

variable "public_asn" {{
  type        = number
  default     = {self.public_asn}
  description = "Public BGP ASN for the site"
}}

variable "nos" {{
  type        = string
  default     = "{self.switch_nos}"
  description = "Network Operating System on switches"
}}

variable "softgate_flavor" {{
  type        = string
  default     = "{self.softgate_flavor}"
  description = "Softgate flavor/profile"
}}

variable "tenant_name" {{
  type        = string
  default     = "Admin"
  description = "Target administrative tenant"
}}

variable "inventory_profile_timezone" {{
  type        = string
  default     = "{self.timezone}"
  description = "Timezone for inventory profiles"
}}

variable "ntp_servers" {{
  type        = list(string)
  default     = {str(self.ntp_servers).replace("'", '"')}
  description = "NTP servers"
}}

variable "dns_servers" {{
  type        = list(string)
  default     = {str(self.dns_servers).replace("'", '"')}
  description = "DNS servers"
}}

variable "acl_default_policy" {{
  type        = string
  default     = "{self.acl_default_policy}"
  description = "Default policy for undeclared traffic (permit or deny)"
}}

variable "vlan_range" {{
  type        = string
  default     = "{self.vlan_range}"
  description = "Total VLAN allocation range for site"
}}

variable "vlan_range_auto_assign" {{
  type        = string
  default     = "{self.vlan_range_auto_assign}"
  description = "Auto-assignable VLAN range"
}}

# -----------------------------------------------------------------------------
# Data Sources & Site Resource
# -----------------------------------------------------------------------------

data "netris_tenant" "admin" {{
  name = var.tenant_name
}}

resource "netris_site" "site" {{
  name                = var.site_name
  publicasn           = var.public_asn
  acldefaultpolicy    = var.acl_default_policy
  vlanrange           = var.vlan_range
  vlanrangeautoassign = var.vlan_range_auto_assign
}}
"""

    def _gen_terraform_tfvars(self) -> str:
        ntp_str = ", ".join(f'"{s}"' for s in self.ntp_servers)
        dns_str = ", ".join(f'"{s}"' for s in self.dns_servers)
        ctl_url = self.cfg.get("controller_address", "https://adam-ctl.netris.io")
        ctl_user = self.cfg.get("controller_login", "netris")
        ctl_pass = self.cfg.get("controller_password", "913QGAi6oQTSGgZm20eU")

        return f"""# =============================================================================
# Terraform Variables — {self.site_name} Day-0 Deployment
# Generated by Netris Fabric Terraform Builder
# =============================================================================

# Controller connection
controller_address  = "{ctl_url}"
controller_login    = "{ctl_user}"
controller_password = "{ctl_pass}"

# Site parameters
site_name                  = "{self.site_name}"
public_asn                 = {self.public_asn}
nos                        = "{self.switch_nos}"
softgate_flavor            = "{self.softgate_flavor}"
tenant_name                = "Admin"
inventory_profile_timezone = "{self.timezone}"
ntp_servers                = [{ntp_str}]
dns_servers                = [{dns_str}]
acl_default_policy         = "{self.acl_default_policy}"
vlan_range                 = "{self.vlan_range}"
vlan_range_auto_assign     = "{self.vlan_range_auto_assign}"
"""

    def _gen_inventory_profile_tf(self) -> str:
        plane_refarch = self.refarch_override or {
            1: "b300_spx_2_tier_single_plane",
            2: "b300_spx_2_tier_dual_plane",
            4: "b300_spx_2_tier_quad_plane"
        }.get(self.planes_count, "b300_spx_2_tier_dual_plane")

        plane_profiles = []
        for p in range(1, self.planes_count + 1):
            ft = "ew" if self.planes_count == 1 else f"ew-plane{p}"
            plane_profiles.append(f"""resource "netris_inventory_profile" "ew_profile_pl{p}" {{
  name        = "{self.site_slug}-ew-pl{p}"
  description = "East-West Spectrum-X Profile for Plane {p}"
  ipv4ssh     = ["0.0.0.0/0"]
  timezone    = var.inventory_profile_timezone
  ntpservers  = var.ntp_servers
  dnsservers  = var.dns_servers

  fabricsettings {{
    automaticlinkaggregation = {str(self.automatic_link_aggregation_ew).lower()}
    unnumberedbgpunderlay    = {str(self.unnumbered_bgp_underlay).lower()}
    optimisebgpoverlay       = {str(self.optimise_bgp_overlay).lower()}
    fabrictype               = "{ft}"
  }}

  gpuclustersettings {{
    congestioncontrol    = {str(self.congestion_control).lower()}
    qosandroce           = {str(self.qos_and_roce).lower()}
    roceadaptiverouting  = {str(self.roce_adaptive_routing).lower()}
    aggregatel3vpnprefix = {str(self.aggregate_l3vpn_prefix).lower()}
    refarch              = "{plane_refarch}"
  }}
}}
""")
        planes_hcl = "\n".join(plane_profiles)

        oob_profile = ""
        if self.enable_oob:
            oob_profile = f"""
resource "netris_inventory_profile" "oob_profile" {{
  name        = "{self.site_slug}-oob-profile"
  description = "Out-of-band management profile"
  ipv4ssh     = ["0.0.0.0/0"]
  timezone    = var.inventory_profile_timezone
  ntpservers  = var.ntp_servers
  dnsservers  = var.dns_servers

  fabricsettings {{
    fabrictype = "oob"
  }}
}}
"""

        return f"""# -----------------------------------------------------------------------------
# Inventory Profiles
# -----------------------------------------------------------------------------

resource "netris_inventory_profile" "ns_profile" {{
  name        = "{self.site_slug}-ns-profile"
  description = "North-South Front-End Inventory Profile"
  ipv4ssh     = ["0.0.0.0/0"]
  timezone    = var.inventory_profile_timezone
  ntpservers  = var.ntp_servers
  dnsservers  = var.dns_servers

  fabricsettings {{
    automaticlinkaggregation = {str(self.automatic_link_aggregation_ns).lower()}
    fabrictype               = "ns"
  }}
}}

{planes_hcl}{oob_profile}
"""

    def _gen_ipam_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# IPAM: Allocations and Subnets via csv/ipam.csv
# -----------------------------------------------------------------------------

locals {
  ipam_rows = csvdecode(file("./csv/ipam.csv"))
  allocations = {
    for row in local.ipam_rows :
    row.name => row if row.type == "allocation"
  }
  subnets = {
    for row in local.ipam_rows :
    row.name => row if row.type == "subnet"
  }
}

resource "netris_allocation" "allocations" {
  for_each = local.allocations
  name     = each.value.name
  prefix   = each.value.prefix
  tenantid = data.netris_tenant.admin.id

  depends_on = [netris_site.site]
}

resource "netris_subnet" "subnets" {
  for_each       = local.subnets
  name           = each.value.name
  prefix         = each.value.prefix
  purpose        = each.value.purpose
  defaultgateway = each.value.default_gateway != "" ? each.value.default_gateway : null
  tenantid       = data.netris_tenant.admin.id
  siteids        = [netris_site.site.id]

  depends_on = [
    netris_allocation.allocations,
    netris_site.site
  ]
}
"""

    def _gen_switches_tf(self) -> str:
        profile_map_entries = []
        for p in range(1, self.planes_count + 1):
            profile_map_entries.append(f'    "ew_profile_pl{p}" = netris_inventory_profile.ew_profile_pl{p}.id')
        profile_map_entries.append('    "ns_profile"     = netris_inventory_profile.ns_profile.id')
        if self.enable_oob:
            profile_map_entries.append('    "oob_profile"    = netris_inventory_profile.oob_profile.id')

        profiles_str = "\n".join(profile_map_entries)

        return f"""# -----------------------------------------------------------------------------
# Switches — loaded from csv/switches.csv
# -----------------------------------------------------------------------------

locals {{
  switches_rows = csvdecode(file("./csv/switches.csv"))
  switches_map = {{
    for row in local.switches_rows :
    row.index => row
  }}

  switch_profile_ids = {{
{profiles_str}
  }}
}}

resource "netris_switch" "switches" {{
  for_each    = local.switches_map
  name        = each.value.name
  description = each.value.description
  tenantid    = data.netris_tenant.admin.id
  siteid      = netris_site.site.id
  nos         = var.nos
  asnumber    = each.value.asn
  profileid   = local.switch_profile_ids[each.value.profile]
  portcount   = each.value.portcount
  mainip      = each.value.loopback
  mgmtip      = each.value.mgmtip
  role        = each.value.role

  depends_on = [
    netris_site.site,
    netris_subnet.subnets,
    netris_inventory_profile.ns_profile
  ]
}}
"""

    def _gen_softgates_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# Softgates — Border Gateway / NAT nodes from csv/softgates.csv
# -----------------------------------------------------------------------------

locals {
  softgates_rows = csvdecode(file("./csv/softgates.csv"))
  softgates_map = {
    for row in local.softgates_rows :
    row.index => row
  }
}

resource "netris_softgate" "softgates" {
  for_each    = local.softgates_map
  name        = each.value.name
  description = each.value.description
  tenantid    = data.netris_tenant.admin.id
  siteid      = netris_site.site.id
  mainip      = each.value.mainip
  mgmtip      = each.value.mgmtip
  flavor      = var.softgate_flavor
  role        = each.value.role
  profileid   = netris_inventory_profile.ns_profile.id

  depends_on = [
    netris_site.site,
    netris_subnet.subnets,
    netris_inventory_profile.ns_profile
  ]
}
"""

    def _gen_servers_gpu_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# GPU Servers from csv/servers_gpu.csv
# -----------------------------------------------------------------------------

locals {
  gpu_servers_rows = csvdecode(file("./csv/servers_gpu.csv"))
  gpu_servers_map = {
    for row in local.gpu_servers_rows :
    row.name => row
  }
}

resource "netris_server" "gpu_servers" {
  for_each    = local.gpu_servers_map
  name        = each.value.name
  description = each.value.description
  tenantid    = data.netris_tenant.admin.id
  siteid      = netris_site.site.id
  portcount   = each.value.portcount

  depends_on = [netris_site.site]
}
"""

    def _gen_servers_mgmt_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# Management / CPU Servers from csv/servers_mgmt.csv
# -----------------------------------------------------------------------------

locals {
  mgmt_servers_rows = csvdecode(file("./csv/servers_mgmt.csv"))
  mgmt_servers_map = {
    for row in local.mgmt_servers_rows :
    row.name => row
  }
}

resource "netris_server" "mgmt_servers" {
  for_each    = local.mgmt_servers_map
  name        = each.value.name
  description = each.value.description
  tenantid    = data.netris_tenant.admin.id
  siteid      = netris_site.site.id
  portcount   = each.value.portcount

  depends_on = [netris_site.site]
}
"""

    def _gen_servers_storage_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# Storage Servers from csv/servers_storage.csv
# -----------------------------------------------------------------------------

locals {
  storage_servers_rows = csvdecode(file("./csv/servers_storage.csv"))
  storage_servers_map = {
    for row in local.storage_servers_rows :
    row.name => row
  }
}

resource "netris_server" "storage_servers" {
  for_each    = local.storage_servers_map
  name        = each.value.name
  description = each.value.description
  tenantid    = data.netris_tenant.admin.id
  siteid      = netris_site.site.id
  portcount   = each.value.portcount

  depends_on = [netris_site.site]
}
"""

    def _gen_vpc_tf(self) -> str:
        vpcs_hcl = f"""# -----------------------------------------------------------------------------
# VPCs
# -----------------------------------------------------------------------------

resource "netris_vpc" "inband_mgmt" {{
  name     = "{self.site_slug}-inband-mgmt"
  tenantid = data.netris_tenant.admin.id
}}
"""
        if self.enable_oob:
            vpcs_hcl += f"""
resource "netris_vpc" "oob_mgmt" {{
  name     = "{self.site_slug}-oob-mgmt"
  tenantid = data.netris_tenant.admin.id
}}
"""
        if self.enable_storage:
            vpcs_hcl += f"""
resource "netris_vpc" "storage" {{
  name     = "{self.site_slug}-storage-vpc"
  tenantid = data.netris_tenant.admin.id
}}
"""
        return vpcs_hcl

    def _gen_vnets_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# Virtual Networks (V-Nets) from csv/vnets.csv
# -----------------------------------------------------------------------------

locals {
  vnets_rows = csvdecode(file("./csv/vnets.csv"))
  vnets_map = {
    for row in local.vnets_rows :
    row.name => row
  }
}

resource "netris_vnet" "vnets" {
  for_each = local.vnets_map
  name     = each.value.name
  tenantid = data.netris_tenant.admin.id
  state    = "active"
  vlanid   = each.value.vlan

  sites {
    id = netris_site.site.id
  }

  depends_on = [
    netris_site.site,
    netris_subnet.subnets
  ]
}
"""

    def _gen_links_ew_switch_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# East-West Spine-Leaf Interconnect Links
# -----------------------------------------------------------------------------

locals {
  links_ew_switch_rows = csvdecode(file("./csv/links_ew_switch.csv"))
  links_ew_switch_map = {
    for idx, row in local.links_ew_switch_rows :
    "${row.deviceA_port}@${row.deviceA}--${row.deviceB_port}@${row.deviceB}" => row
  }
}

resource "netris_link" "ew_switch_links" {
  for_each = local.links_ew_switch_map

  ports = [
    "${each.value.deviceA_port}@${each.value.deviceA}",
    "${each.value.deviceB_port}@${each.value.deviceB}"
  ]

  depends_on = [netris_switch.switches]
}
"""

    def _gen_links_ew_gpu_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# East-West Leaf to GPU RoCE Links
# -----------------------------------------------------------------------------

locals {
  links_ew_gpu_rows = csvdecode(file("./csv/links_ew_gpu.csv"))
  links_ew_gpu_map = {
    for idx, row in local.links_ew_gpu_rows :
    "${row.leaf_port}@${row.leaf}--${row.gpu_port}@${row.gpu}" => row
  }
}

resource "netris_link" "ew_gpu_links" {
  for_each = local.links_ew_gpu_map

  ports = [
    "${each.value.leaf_port}@${each.value.leaf}",
    "${each.value.gpu_port}@${each.value.gpu}"
  ]

  depends_on = [
    netris_switch.switches,
    netris_server.gpu_servers
  ]
}
"""

    def _gen_links_ns_switch_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# North-South Spine-Leaf Links
# -----------------------------------------------------------------------------

locals {
  links_ns_switch_rows = csvdecode(file("./csv/links_ns_switch.csv"))
  links_ns_switch_map = {
    for idx, row in local.links_ns_switch_rows :
    "${row.deviceA_port}@${row.deviceA}--${row.deviceB_port}@${row.deviceB}" => row
  }
}

resource "netris_link" "ns_switch_links" {
  for_each = local.links_ns_switch_map

  ports = [
    "${each.value.deviceA_port}@${each.value.deviceA}",
    "${each.value.deviceB_port}@${each.value.deviceB}"
  ]

  depends_on = [netris_switch.switches]
}
"""

    def _gen_links_ns_gpu_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# North-South Leaf to GPU Management Links
# -----------------------------------------------------------------------------

locals {
  links_ns_gpu_rows = csvdecode(file("./csv/links_ns_gpu.csv"))
  links_ns_gpu_map = {
    for idx, row in local.links_ns_gpu_rows :
    "${row.leaf_port}@${row.leaf}--${row.gpu_port}@${row.gpu}" => row
  }
}

resource "netris_link" "ns_gpu_links" {
  for_each = local.links_ns_gpu_map

  ports = [
    "${each.value.leaf_port}@${each.value.leaf}",
    "${each.value.gpu_port}@${each.value.gpu}"
  ]

  depends_on = [
    netris_switch.switches,
    netris_server.gpu_servers
  ]
}
"""

    def _gen_links_softgate_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# Softgate to Border/NS Leaf Links
# -----------------------------------------------------------------------------

locals {
  links_softgate_rows = csvdecode(file("./csv/links_softgate.csv"))
  links_softgate_map = {
    for idx, row in local.links_softgate_rows :
    "${row.deviceA_port}@${row.deviceA}--${row.deviceB_port}@${row.deviceB}" => row
  }
}

resource "netris_link" "softgate_links" {
  for_each = local.links_softgate_map

  ports = [
    "${each.value.deviceA_port}@${each.value.deviceA}",
    "${each.value.deviceB_port}@${each.value.deviceB}"
  ]

  depends_on = [
    netris_switch.switches,
    netris_softgate.softgates
  ]
}
"""

    def _gen_links_storage_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# Storage Server Links
# -----------------------------------------------------------------------------

locals {
  links_storage_rows = csvdecode(file("./csv/links_storage.csv"))
  links_storage_map = {
    for idx, row in local.links_storage_rows :
    "${row.leaf_port}@${row.leaf}--${row.server_port}@${row.server}" => row
  }
}

resource "netris_link" "storage_links" {
  for_each = local.links_storage_map

  ports = [
    "${each.value.leaf_port}@${each.value.leaf}",
    "${each.value.server_port}@${each.value.server}"
  ]

  depends_on = [
    netris_switch.switches,
    netris_server.storage_servers
  ]
}
"""

    def _gen_links_oob_switch_tf(self) -> str:
        depends = ["netris_switch.switches", "netris_server.mgmt_servers"]
        if self.enable_storage and self.storage_servers > 0:
            depends.append("netris_server.storage_servers")
        dep_str = ", ".join(depends)
        return f"""# -----------------------------------------------------------------------------
# Out-of-Band (OOB) Switch & Management Server Links
# -----------------------------------------------------------------------------

locals {{
  links_oob_switch_rows = csvdecode(file("./csv/links_oob_switch.csv"))
  links_oob_switch_map = {{
    for idx, row in local.links_oob_switch_rows :
    "${{row.deviceA_port}}@${{row.deviceA}}--${{row.deviceB_port}}@${{row.deviceB}}" => row
  }}
}}

resource "netris_link" "oob_switch_links" {{
  for_each = local.links_oob_switch_map

  ports = [
    "${{each.value.deviceA_port}}@${{each.value.deviceA}}",
    "${{each.value.deviceB_port}}@${{each.value.deviceB}}"
  ]

  depends_on = [{dep_str}]
}}
"""

    def _gen_breakouts_tf(self) -> str:
        return """# -----------------------------------------------------------------------------
# Port Breakouts (Optional)
# -----------------------------------------------------------------------------

locals {
  breakouts_rows = csvdecode(file("./csv/breakouts.csv"))
  breakouts_map = {
    for idx, row in local.breakouts_rows :
    "${row.port}@${row.switch}" => row
  }
}
"""

    def _gen_readme(self) -> str:
        total_switches = (
            (self.ew_spines_per_plane + self.ew_leaves_per_plane) * self.planes_count
            + self.ns_spines + self.ns_leaves
            + self.storage_leaves + self.oob_switches
        )
        return f"""# {self.site_name} — Netris Day-0 Infrastructure Deployment

This project was automatically generated by **Fabric Terraform Builder**.

## Architecture Overview
- **Backend Architecture**: {self.planes_count}-Plane Spectrum-X RoCE Fabric
  - East-West Planes: **{self.planes_count} independent planes**
  - Per-Plane Spines: **{self.ew_spines_per_plane}** | Per-Plane Leaves: **{self.ew_leaves_per_plane}**
- **Frontend Networks**:
  - North-South Fabric: **{self.ns_spines} Spines + {self.ns_leaves} Leaves**
  - Softgates: **{self.softgate_count} Border Gateway / NAT nodes**
  - Dedicated Storage: **{'Enabled (' + str(self.storage_leaves) + ' leaves, ' + str(self.storage_servers) + ' servers)' if self.enable_storage else 'Disabled'}**
  - Out-of-Band (OOB): **{'Enabled (' + str(self.oob_switches) + ' switches)' if self.enable_oob else 'Disabled'}**
- **Compute Fleet**:
  - GPU Servers: **{self.gpu_count}** ({self.gpu_roce_ports} RoCE ports striped across {self.planes_count} planes + {self.gpu_ns_ports} NS ports)
- **Total Physical Switches**: **{total_switches}**

## Quick Start

```bash
# 1. Initialize OpenTofu / Terraform
tofu init

# 2. Validate configuration syntax
tofu validate

# 3. Review proposed changes against controller
tofu plan

# 4. Apply configuration
tofu apply
```
"""

    # -------------------------------------------------------------------------
    # CSV Generators
    # -------------------------------------------------------------------------

    def _gen_csv_switches(self) -> str:
        lines = ["index,name,profile,asn,portcount,description,loopback,mgmtip,role"]
        idx = 1
        
        try:
            ew_lb_net = ipaddress.ip_network(self.ew_loopback_subnet, strict=False)
            ew_hosts = list(ew_lb_net.hosts())
        except Exception:
            ew_hosts = [ipaddress.IPv4Address(f"172.16.0.{i}") for i in range(1, 250)]

        try:
            ns_lb_net = ipaddress.ip_network(self.ns_loopback_subnet, strict=False)
            ns_lb_hosts = list(ns_lb_net.hosts())
        except Exception:
            ns_lb_hosts = [ipaddress.IPv4Address(f"172.16.1.{i}") for i in range(1, 250)]

        try:
            ns_mgmt_net = ipaddress.ip_network(self.ns_mgmt_subnet, strict=False)
            mgmt_hosts = list(ns_mgmt_net.hosts())
        except Exception:
            mgmt_hosts = [ipaddress.IPv4Address(f"172.16.2.{i}") for i in range(1, 250)]

        # Capacity validation to prevent duplicate IP assignments
        total_ew_switches = (self.ew_spines_per_plane + self.ew_leaves_per_plane) * self.planes_count
        if len(ew_hosts) < total_ew_switches:
            raise ValueError(
                f"East-West loopback subnet '{self.ew_loopback_subnet}' provides {len(ew_hosts)} usable host IPs, "
                f"but {total_ew_switches} switch loopbacks are required."
            )

        ns_switches_count = self.ns_spines + self.ns_leaves + (self.storage_leaves if self.enable_storage else 0) + (self.oob_switches if self.enable_oob else 0)
        total_ns_loopbacks = ns_switches_count + self.softgate_count
        if len(ns_lb_hosts) < total_ns_loopbacks:
            raise ValueError(
                f"North-South loopback subnet '{self.ns_loopback_subnet}' provides {len(ns_lb_hosts)} usable host IPs, "
                f"but {total_ns_loopbacks} IPs (switches + softgates) are required."
            )

        total_mgmt_ips = total_ew_switches + ns_switches_count + self.softgate_count
        if len(mgmt_hosts) < total_mgmt_ips:
            raise ValueError(
                f"Management subnet '{self.ns_mgmt_subnet}' provides {len(mgmt_hosts)} usable host IPs, "
                f"but {total_mgmt_ips} management IPs are required."
            )

        ew_lb_idx = 0
        ns_lb_idx = 0
        mgmt_idx = 0

        # Backend Planes (East-West)
        for p in range(1, self.planes_count + 1):
            prof = f"ew_profile_pl{p}"
            # Spines
            for s in range(1, self.ew_spines_per_plane + 1):
                name = self.get_backend_spine_name(p, s)
                lb = str(ew_hosts[ew_lb_idx])
                mgmt = str(mgmt_hosts[mgmt_idx])
                ew_lb_idx += 1
                mgmt_idx += 1
                desc = f"Backend Spectrum-X AI Fabric — Plane {p} Spine {s:02d} (Aggregates Plane {p} Leaves for East-West RoCE GPU Interconnect)"
                lines.append(f'{idx},{name},{prof},{self.switch_asn_base},{self.switch_port_count},"{desc}",{lb},{mgmt},spine')
                idx += 1
            # Leaves
            for l in range(1, self.ew_leaves_per_plane + 1):
                name = self.get_backend_leaf_name(p, l)
                lb = str(ew_hosts[ew_lb_idx])
                mgmt = str(mgmt_hosts[mgmt_idx])
                ew_lb_idx += 1
                mgmt_idx += 1
                desc = f"Backend Spectrum-X AI Fabric — Plane {p} Leaf {l:02d} (Dedicated RoCE Compute Access Leaf for GPU Fleet)"
                lines.append(f'{idx},{name},{prof},{self.switch_asn_base + idx},{self.switch_port_count},"{desc}",{lb},{mgmt},leaf')
                idx += 1

        # North-South Fabric
        for s in range(1, self.ns_spines + 1):
            name = self.get_frontend_spine_name(s)
            lb = str(ns_lb_hosts[ns_lb_idx])
            mgmt = str(mgmt_hosts[mgmt_idx])
            ns_lb_idx += 1
            mgmt_idx += 1
            desc = f"Frontend North-South Fabric — Spine {s:02d} (Aggregates Frontend & In-Band Management Leaves and Core Routing)"
            lines.append(f'{idx},{name},ns_profile,{self.switch_asn_base + idx},{self.switch_port_count},"{desc}",{lb},{mgmt},spine')
            idx += 1

        for l in range(1, self.ns_leaves + 1):
            name = self.get_frontend_leaf_name(l)
            lb = str(ns_lb_hosts[ns_lb_idx])
            mgmt = str(mgmt_hosts[mgmt_idx])
            ns_lb_idx += 1
            mgmt_idx += 1
            desc = f"Frontend North-South Fabric — Leaf {l:02d} (GPU In-Band Mgmt, Cluster Services & SoftGate Border Uplinks)"
            lines.append(f'{idx},{name},ns_profile,{self.switch_asn_base + idx},{self.switch_port_count},"{desc}",{lb},{mgmt},leaf')
            idx += 1

        # Storage Leaves
        if self.enable_storage:
            for l in range(1, self.storage_leaves + 1):
                name = self.get_storage_leaf_name(l)
                lb = str(ns_lb_hosts[ns_lb_idx])
                mgmt = str(mgmt_hosts[mgmt_idx])
                ns_lb_idx += 1
                mgmt_idx += 1
                desc = f"Storage Network — Leaf {l:02d} (Dedicated NVMe-oF RoCE Storage Leaf connecting Storage Nodes & GPU Fleet)"
                lines.append(f'{idx},{name},ns_profile,{self.switch_asn_base + idx},{self.switch_port_count},"{desc}",{lb},{mgmt},leaf')
                idx += 1

        # OOB Switches
        if self.enable_oob:
            for o in range(1, self.oob_switches + 1):
                name = self.get_oob_switch_name(o)
                lb = str(ns_lb_hosts[ns_lb_idx])
                mgmt = str(mgmt_hosts[mgmt_idx])
                ns_lb_idx += 1
                mgmt_idx += 1
                desc = f"Out-of-Band (OOB) Management — Switch {o:02d} (Dedicated 1G/10G Network for IPMI, BMC, Switch Consoles & Telemetry)"
                lines.append(f'{idx},{name},oob_profile,{self.switch_asn_base + idx},48,"{desc}",{lb},{mgmt},leaf')
                idx += 1

        return "\n".join(lines) + "\n"

    def _gen_csv_softgates(self) -> str:
        lines = ["index,name,description,mainip,mgmtip,role"]
        try:
            ns_lb_net = ipaddress.ip_network(self.ns_loopback_subnet, strict=False)
            ns_lb_hosts = list(ns_lb_net.hosts())
        except Exception:
            ns_lb_hosts = [ipaddress.IPv4Address(f"172.16.1.{i}") for i in range(1, 250)]

        try:
            ns_mgmt_net = ipaddress.ip_network(self.ns_mgmt_subnet, strict=False)
            mgmt_hosts = list(ns_mgmt_net.hosts())
        except Exception:
            mgmt_hosts = [ipaddress.IPv4Address(f"172.16.2.{i}") for i in range(1, 250)]

        # Softgate mainip comes from loopback subnet (sub-ns-loopbacks)
        # mgmtip comes from management subnet (sub-ns-mgmt)
        # Contiguous offset after all switches
        ns_switches_count = self.ns_spines + self.ns_leaves + (self.storage_leaves if self.enable_storage else 0) + (self.oob_switches if self.enable_oob else 0)
        total_switches_count = (self.ew_spines_per_plane + self.ew_leaves_per_plane) * self.planes_count + ns_switches_count

        for i in range(1, self.softgate_count + 1):
            name = self.get_softgate_name(i)
            desc = f"Border Gateway — SoftGate {i:02d} (Stateful NAT, Border BGP Routing, L4 Load Balancing & External Ingress/Egress Gateway)"
            main_idx = ns_switches_count + (i - 1)
            mgmt_idx = total_switches_count + (i - 1)
            mainip = str(ns_lb_hosts[main_idx % len(ns_lb_hosts)])
            mgmtip = str(mgmt_hosts[mgmt_idx % len(mgmt_hosts)])
            lines.append(f'{i},{name},"{desc}",{mainip},{mgmtip},general')
        return "\n".join(lines) + "\n"

    def _gen_csv_servers_gpu(self) -> str:
        lines = ["name,description,portcount"]
        # Total ports includes RoCE ports + North-South frontend ports + OOB IPMI port
        total_ports = self.gpu_roce_ports + self.gpu_ns_ports + self.gpu_oob_ports
        for i in range(1, self.gpu_count + 1):
            name = f"gpu-{self.site_slug}-{i:03d}"
            desc = f"{self.gpu_profile_name} Node {i:03d} ({self.gpu_roce_ports} RoCE + {self.gpu_ns_ports} NS + {self.gpu_oob_ports} OOB)"
            lines.append(f"{name},{desc},{total_ports}")
        return "\n".join(lines) + "\n"

    def _gen_csv_servers_mgmt(self) -> str:
        lines = ["name,description,portcount"]
        for i in range(1, 4):
            name = f"srv-{self.site_slug}-cp{i:02d}"
            desc = f"Control Plane / K8s Node {i:02d}"
            lines.append(f"{name},{desc},2")
        return "\n".join(lines) + "\n"

    def _gen_csv_servers_storage(self) -> str:
        lines = ["name,description,portcount"]
        # Total storage server ports includes Storage data + North-South + OOB IPMI
        total_ports = self.storage_roce_ports + self.storage_ns_ports + self.storage_oob_ports
        for i in range(1, self.storage_servers + 1):
            name = f"srv-{self.site_slug}-storage{i:02d}"
            desc = f"Storage Node {i:02d} ({self.storage_roce_ports} Storage + {self.storage_ns_ports} NS + {self.storage_oob_ports} OOB)"
            lines.append(f"{name},{desc},{total_ports}")
        return "\n".join(lines) + "\n"

    def _gen_csv_ipam(self) -> str:
        lines = [
            "type,name,prefix,purpose,default_gateway",
            f"allocation,alloc-ew-p2p,{self.ew_p2p_allocation},,",
            f"subnet,sub-ew-p2p,{self.ew_p2p_allocation},common,",
            f"allocation,alloc-ew-loopbacks,{self.ew_loopback_subnet},,",
            f"subnet,sub-ew-loopbacks,{self.ew_loopback_subnet},loopback,",
            f"allocation,alloc-ns-loopbacks,{self.ns_loopback_subnet},,",
            f"subnet,sub-ns-loopbacks,{self.ns_loopback_subnet},loopback,",
            f"allocation,alloc-ns-mgmt,{self.ns_mgmt_subnet},,",
            f"subnet,sub-ns-mgmt,{self.ns_mgmt_subnet},management,",
        ]
        if self.enable_storage:
            lines.extend([
                f"allocation,alloc-storage,{self.storage_subnet},,",
                f"subnet,sub-storage,{self.storage_subnet},common,",
            ])
        if self.enable_oob:
            lines.extend([
                f"allocation,alloc-oob,{self.oob_subnet},,",
                f"subnet,sub-oob,{self.oob_subnet},management,",
            ])
        return "\n".join(lines) + "\n"

    def _gen_csv_vnets(self) -> str:
        lines = [
            "name,vlan,purpose",
            f"vnet-{self.site_slug}-inband-mgmt,100,management"
        ]
        if self.enable_storage:
            lines.append(f"vnet-{self.site_slug}-storage,200,storage")
        if self.enable_oob:
            lines.append(f"vnet-{self.site_slug}-oob,10,oob_management")
        return "\n".join(lines) + "\n"

    def _calculate_ew_fabric_uplinks(self) -> Tuple[int, int, int]:
        """
        Calculates (downlinks_per_leaf, links_per_spine, uplink_base).
        Returns:
            downlinks_per_leaf: max downlinks assigned to GPUs on any single leaf.
            links_per_spine: number of parallel links from each leaf to each spine.
            uplink_base: leaf port number where uplinks begin (swp{uplink_base + 1}).
        """
        ports_per_plane = max(1, self.gpu_roce_ports // self.planes_count)
        gpus_on_leaf = math.ceil(self.gpu_count / self.ew_leaves_per_plane)
        downlinks_per_leaf = gpus_on_leaf * ports_per_plane

        ratio = float(self.oversubscription_ratio) if self.oversubscription_ratio > 0 else 1.0
        needed_uplinks = max(1, math.ceil(downlinks_per_leaf / ratio))
        links_per_spine = max(1, math.ceil(needed_uplinks / self.ew_spines_per_plane))

        # 1. Verify spine capacity: Each spine terminates (ew_leaves_per_plane * links_per_spine) links
        if self.ew_leaves_per_plane > self.switch_port_count:
            raise ValueError(
                f"Too many leaves per plane ({self.ew_leaves_per_plane}) for spine switch capacity ({self.switch_port_count}). "
                f"A spine switch with {self.switch_port_count} ports can terminate at most {self.switch_port_count} leaf links. "
                f"Please reduce leaves per plane or select switches with higher port capacity."
            )
        max_links_for_spine = max(1, self.switch_port_count // self.ew_leaves_per_plane)
        if links_per_spine > max_links_for_spine:
            links_per_spine = max_links_for_spine

        total_uplinks = links_per_spine * self.ew_spines_per_plane

        # 2. Verify leaf capacity: downlinks + total_uplinks must fit in switch_port_count
        if downlinks_per_leaf + total_uplinks > self.switch_port_count:
            available_for_uplinks = self.switch_port_count - downlinks_per_leaf
            if available_for_uplinks >= self.ew_spines_per_plane:
                links_per_spine = max(1, available_for_uplinks // self.ew_spines_per_plane)
                total_uplinks = links_per_spine * self.ew_spines_per_plane
            else:
                raise ValueError(
                    f"Port capacity exceeded on leaf switch: requires {downlinks_per_leaf} downlinks + "
                    f"{total_uplinks} uplinks = {downlinks_per_leaf + total_uplinks} ports, but switch only has "
                    f"{self.switch_port_count} ports. Please increase leaves per plane or switch port capacity."
                )

        uplink_base = self.switch_port_count - total_uplinks
        return downlinks_per_leaf, links_per_spine, uplink_base

    def _gen_csv_links_ew_switch(self) -> str:
        lines = ["deviceA,deviceA_port,deviceB,deviceB_port"]
        _, links_per_spine, uplink_base = self._calculate_ew_fabric_uplinks()

        for p in range(1, self.planes_count + 1):
            for s in range(1, self.ew_spines_per_plane + 1):
                sp_name = self.get_backend_spine_name(p, s)
                for l in range(1, self.ew_leaves_per_plane + 1):
                    lf_name = self.get_backend_leaf_name(p, l)
                    for k in range(1, links_per_spine + 1):
                        sp_port_num = (l - 1) * links_per_spine + k
                        if sp_port_num > self.switch_port_count:
                            raise ValueError(
                                f"Port capacity exceeded on spine {sp_name}: assigned swp{sp_port_num} exceeds switch capacity {self.switch_port_count}."
                            )
                        sp_port = f"swp{sp_port_num}"
                        lf_port_num = uplink_base + (s - 1) * links_per_spine + k
                        lf_port = f"swp{lf_port_num}"
                        lines.append(f"{sp_name},{sp_port},{lf_name},{lf_port}")
        return "\n".join(lines) + "\n"

    def _gen_csv_links_ew_gpu(self) -> str:
        lines = ["leaf,leaf_port,gpu,gpu_port"]
        ports_per_plane = max(1, self.gpu_roce_ports // self.planes_count)
        _, _, uplink_base = self._calculate_ew_fabric_uplinks()
        
        for g in range(1, self.gpu_count + 1):
            gpu_name = f"gpu-{self.site_slug}-{g:03d}"
            curr_gpu_port = 1
            for p in range(1, self.planes_count + 1):
                for port_in_plane in range(ports_per_plane):
                    leaf_num = ((g - 1) % self.ew_leaves_per_plane) + 1
                    lf_name = self.get_backend_leaf_name(p, leaf_num)
                    p_num = ((g - 1) // self.ew_leaves_per_plane) * ports_per_plane + port_in_plane + 1
                    if p_num > uplink_base:
                        raise ValueError(
                            f"Port oversubscription on {lf_name}: assigned downlink swp{p_num} exceeds available "
                            f"downlink range (swp1..swp{uplink_base}). Ports swp{uplink_base + 1}..swp{self.switch_port_count} "
                            f"are reserved for spine uplinks. Please increase leaves per plane or switch port capacity."
                        )
                    lf_port = f"swp{p_num}"
                    lines.append(f"{lf_name},{lf_port},{gpu_name},eth{curr_gpu_port}")
                    curr_gpu_port += 1
        return "\n".join(lines) + "\n"

    def _get_ns_leaf_port_allocations(self):
        """
        Precomputes SoftGate ports and available server downlink boundaries per Frontend Leaf:
        - Top ports: Spine uplinks (swp{port_count - ns_spines + 1} .. swp{port_count})
        - Upper ports: SoftGate links (downwards from swp{port_count - ns_spines})
        - Lower ports: Server downlinks (GPUs, Storage) starting at swp1 upwards
        """
        leaf_names = [self.get_frontend_leaf_name(l) for l in range(1, self.ns_leaves + 1)]
        upper_port_trackers = {lf: (self.switch_port_count - self.ns_spines) for lf in leaf_names}
        
        sg_assignments = []
        for i in range(1, self.softgate_count + 1):
            sg_name = self.get_softgate_name(i)
            # Primary leaf (Leaf A)
            lf_a_num = (((i - 1) * 2) % self.ns_leaves) + 1
            lf_a_name = self.get_frontend_leaf_name(lf_a_num)
            port_a = upper_port_trackers[lf_a_name]
            upper_port_trackers[lf_a_name] -= 1
            sg_assignments.append((sg_name, "eth1", lf_a_name, f"swp{port_a}"))

            # Secondary leaf for dual-homing (Leaf B)
            if self.ns_leaves > 1:
                lf_b_num = ((((i - 1) * 2) + 1) % self.ns_leaves) + 1
                lf_b_name = self.get_frontend_leaf_name(lf_b_num)
                port_b = upper_port_trackers[lf_b_name]
                upper_port_trackers[lf_b_name] -= 1
                sg_assignments.append((sg_name, "eth2", lf_b_name, f"swp{port_b}"))
            else:
                port_b = upper_port_trackers[lf_a_name]
                upper_port_trackers[lf_a_name] -= 1
                sg_assignments.append((sg_name, "eth2", lf_a_name, f"swp{port_b}"))

        return upper_port_trackers, sg_assignments

    def _gen_csv_links_ns_switch(self) -> str:
        lines = ["deviceA,deviceA_port,deviceB,deviceB_port"]
        for s in range(1, self.ns_spines + 1):
            sp_name = self.get_frontend_spine_name(s)
            for l in range(1, self.ns_leaves + 1):
                lf_name = self.get_frontend_leaf_name(l)
                leaf_spine_port = self.switch_port_count - self.ns_spines + s
                lines.append(f"{sp_name},swp{l},{lf_name},swp{leaf_spine_port}")
            if self.enable_storage and self.storage_network_mode == "standalone" and self.storage_leaves > 0:
                for sl in range(1, self.storage_leaves + 1):
                    sl_name = self.get_storage_leaf_name(sl)
                    leaf_spine_port = self.switch_port_count - self.ns_spines + s
                    lines.append(f"{sp_name},swp{self.ns_leaves + sl},{sl_name},swp{leaf_spine_port}")
        return "\n".join(lines) + "\n"

    def _gen_csv_links_softgate(self) -> str:
        lines = ["deviceA,deviceA_port,deviceB,deviceB_port"]
        _, sg_assignments = self._get_ns_leaf_port_allocations()
        for sg_name, eth, lf_name, port_str in sg_assignments:
            lines.append(f"{sg_name},{eth},{lf_name},{port_str}")
        return "\n".join(lines) + "\n"

    def _gen_csv_links_ns_gpu(self) -> str:
        lines = ["leaf,leaf_port,gpu,gpu_port"]
        upper_bounds, _ = self._get_ns_leaf_port_allocations()
        leaf_ports = {self.get_frontend_leaf_name(l): 1 for l in range(1, self.ns_leaves + 1)}
        for g in range(1, self.gpu_count + 1):
            gpu_name = f"gpu-{self.site_slug}-{g:03d}"
            pair_idx = ((g - 1) * 2) % self.ns_leaves
            for p in range(1, self.gpu_ns_ports + 1):
                leaf_num = ((pair_idx + (p - 1)) % self.ns_leaves) + 1
                lf_name = self.get_frontend_leaf_name(leaf_num)
                p_num = leaf_ports[lf_name]
                leaf_ports[lf_name] += 1
                if p_num > upper_bounds[lf_name]:
                    raise ValueError(
                        f"Port capacity exceeded on North-South leaf {lf_name}: assigned downlink swp{p_num} "
                        f"collides with SoftGate/spine uplinks (swp{upper_bounds[lf_name] + 1}..swp{self.switch_port_count}). "
                        f"Please increase North-South leaves (ns_leaves)."
                    )
                gpu_port_name = f"eth{self.gpu_roce_ports + p}"
                lines.append(f"{lf_name},swp{p_num},{gpu_name},{gpu_port_name}")
        self._ns_leaf_next_free_port = leaf_ports
        return "\n".join(lines) + "\n"

    def _gen_csv_links_storage(self) -> str:
        lines = ["leaf,leaf_port,server,server_port"]
        if self.storage_network_mode == "converged":
            upper_bounds, _ = self._get_ns_leaf_port_allocations()
            leaf_ports = getattr(self, "_ns_leaf_next_free_port", {
                self.get_frontend_leaf_name(l): 1 for l in range(1, self.ns_leaves + 1)
            })
            for s in range(1, self.storage_servers + 1):
                srv_name = f"srv-{self.site_slug}-storage{s:02d}"
                for p in range(1, min(3, self.storage_ns_ports + 1)):
                    lf_num = ((s - 1 + p) % self.ns_leaves) + 1
                    lf_name = self.get_frontend_leaf_name(lf_num)
                    p_num = leaf_ports[lf_name]
                    leaf_ports[lf_name] += 1
                    if p_num > upper_bounds[lf_name]:
                        raise ValueError(
                            f"Port capacity exceeded on North-South leaf {lf_name}: assigned storage downlink swp{p_num} "
                            f"collides with SoftGate/spine uplinks (swp{upper_bounds[lf_name] + 1}..swp{self.switch_port_count}). "
                            f"Please increase North-South leaves (ns_leaves)."
                        )
                    lines.append(f"{lf_name},swp{p_num},{srv_name},eth{p}")
        else:
            leaf_ports = {self.get_storage_leaf_name(l): 1 for l in range(1, self.storage_leaves + 1)}
            for s in range(1, self.storage_servers + 1):
                srv_name = f"srv-{self.site_slug}-storage{s:02d}"
                for p in range(1, min(3, self.storage_roce_ports + 1)):
                    lf_num = ((s - 1 + p) % self.storage_leaves) + 1
                    lf_name = self.get_storage_leaf_name(lf_num)
                    p_num = leaf_ports[lf_name]
                    leaf_ports[lf_name] += 1
                    lines.append(f"{lf_name},swp{p_num},{srv_name},eth{p}")
        return "\n".join(lines) + "\n"

    def _gen_csv_links_oob_switch(self) -> str:
        """
        Universal Out-of-Band (OOB) Cabling Engine:
        Connects ALL devices in the fabric to the dedicated OOB management network:
        1. Inter-switch ISL trunks between OOB switch pairs on swp47 & swp48.
        2. K8s Control Plane nodes (srv-*-cp01..cp03) on eth1 / eth2.
        3. All GPU Compute nodes (gpu-*-001..N) via dedicated IPMI/BMC port.
        4. All Storage nodes (srv-*-storage01..N) via dedicated IPMI/BMC port.
        """
        lines = ["deviceA,deviceA_port,deviceB,deviceB_port"]
        if self.oob_switches > 1:
            for o in range(1, self.oob_switches, 2):
                if o + 1 <= self.oob_switches:
                    swA = self.get_oob_switch_name(o)
                    swB = self.get_oob_switch_name(o + 1)
                    lines.append(f"{swA},swp47,{swB},swp47")
                    lines.append(f"{swA},swp48,{swB},swp48")

        MAX_OOB_DOWNLINK_PORT = 46
        oob_port_trackers = {self.get_oob_switch_name(o): 1 for o in range(1, self.oob_switches + 1)}

        def assign_oob_port(preferred_sw: int) -> Tuple[str, str]:
            order = [preferred_sw] + [x for x in range(1, self.oob_switches + 1) if x != preferred_sw]
            for sw_idx in order:
                sw_name = self.get_oob_switch_name(sw_idx)
                cur = oob_port_trackers[sw_name]
                if cur <= MAX_OOB_DOWNLINK_PORT:
                    oob_port_trackers[sw_name] += 1
                    return sw_name, f"swp{cur}"
            raise ValueError(
                f"Out-of-Band (OOB) switch port capacity exceeded: all {self.oob_switches} OOB switches are full (max 46 ports each). "
                f"Please increase OOB switch count (oob_switches) in design settings."
            )

        # 1. Connect Control Plane Nodes (srv-{site}-cp01..cp03)
        for i in range(1, 4):
            cp_name = f"srv-{self.site_slug}-cp{i:02d}"
            if self.oob_switches >= 2:
                sw1, p1 = assign_oob_port(1)
                sw2, p2 = assign_oob_port(2)
                lines.append(f"{sw1},{p1},{cp_name},eth1")
                lines.append(f"{sw2},{p2},{cp_name},eth2")
            else:
                sw1, p1 = assign_oob_port(1)
                lines.append(f"{sw1},{p1},{cp_name},eth1")

        # 2. Connect GPU Compute Nodes (IPMI / BMC interface)
        gpu_oob_nic = f"eth{self.gpu_roce_ports + self.gpu_ns_ports + 1}"
        for g in range(1, self.gpu_count + 1):
            gpu_name = f"gpu-{self.site_slug}-{g:03d}"
            target_oob_sw = ((g - 1) % self.oob_switches) + 1
            sw_name, p_num = assign_oob_port(target_oob_sw)
            lines.append(f"{sw_name},{p_num},{gpu_name},{gpu_oob_nic}")

        # 3. Connect Storage Servers (IPMI / BMC interface)
        if self.enable_storage and self.storage_servers > 0:
            storage_oob_nic = f"eth{self.storage_roce_ports + self.storage_ns_ports + 1}"
            for s in range(1, self.storage_servers + 1):
                st_name = f"srv-{self.site_slug}-storage{s:02d}"
                target_oob_sw = ((s - 1) % self.oob_switches) + 1
                sw_name, p_num = assign_oob_port(target_oob_sw)
                lines.append(f"{sw_name},{p_num},{st_name},{storage_oob_nic}")

        return "\n".join(lines) + "\n"
