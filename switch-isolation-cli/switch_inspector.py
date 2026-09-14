"""
Switch Inspection Engine.
Connects via SSH Jump Host to physical fabric switches:
- North-South switch (ns-leaf-0): EVPN / VXLAN VNI inspection
- East-West switch (leaf-pod00-su0-r0): Pure VRF routing table inspection
"""

import paramiko
import re
from typing import Any, Dict, List, Optional, Tuple


class SwitchInspector:
    def __init__(
        self,
        jump_host: str,
        jump_port: int,
        jump_user: str,
        jump_password: str,
        switch_user: str = "cumulus",
        switch_key_path: str = "/home/ubuntu/.ssh/id_rsa",
        ns_switch_ip: str = "10.3.0.1",
        ew_switch_ip: str = "10.253.0.1"
    ):
        self.jump_host = jump_host
        self.jump_port = jump_port
        self.jump_user = jump_user
        self.jump_password = jump_password
        self.switch_user = switch_user
        self.switch_key_path = switch_key_path
        self.ns_switch_ip = ns_switch_ip
        self.ew_switch_ip = ew_switch_ip
        self._jump_client: Optional[paramiko.SSHClient] = None

    def _get_jump_client(self) -> paramiko.SSHClient:
        if self._jump_client is None:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.jump_host,
                port=self.jump_port,
                username=self.jump_user,
                password=self.jump_password,
                timeout=12
            )
            self._jump_client = ssh
        return self._jump_client

    def close(self):
        if self._jump_client:
            try:
                self._jump_client.close()
            except Exception:
                pass
            self._jump_client = None

    def _exec_on_switch(self, switch_ip: str, cmd: str, timeout: int = 15) -> str:
        jump = self._get_jump_client()
        remote_cmd = (
            f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
            f"-o BatchMode=yes -i {self.switch_key_path} {self.switch_user}@{switch_ip} "
            f"\"{cmd}\""
        )
        stdin, stdout, stderr = jump.exec_command(remote_cmd, timeout=timeout)
        return stdout.read().decode("utf-8")

    # ------------------------------------------------------------------
    # North-South EVPN / VXLAN Inspection
    # ------------------------------------------------------------------
    def inspect_ns_evpn_tables(self, target_vpc_id: int) -> Dict[str, Any]:
        """
        Queries North-South switch (ns-leaf-0) for:
        1. EVPN VNI table: vtysh -c 'show evpn vni'
        2. VRF table: vtysh -c 'show vrf'
        Categorizes VNIs belonging to target VPC vs other tenants.
        """
        raw_vni = self._exec_on_switch(self.ns_switch_ip, "sudo vtysh -c 'show evpn vni'")
        raw_vrf = self._exec_on_switch(self.ns_switch_ip, "sudo vtysh -c 'show vrf'")

        target_vrf_name = f"Vrf_{target_vpc_id}"
        
        # Parse EVPN VNI table
        vni_rows: List[Dict[str, str]] = []
        for line in raw_vni.splitlines():
            line_s = line.strip()
            if not line_s or line_s.startswith("VNI") or line_s.startswith("-"):
                continue
            parts = line_s.split()
            if len(parts) >= 6 and parts[0].isdigit():
                # Columns: VNI Type VxLAN_IF #MACs #ARPs #Remote_VTEPs Tenant_VRF VLAN BRIDGE
                vni_num = parts[0]
                vni_type = parts[1]
                vxlan_if = parts[2]
                tenant_vrf = "unknown"
                vlan = ""
                # Locate Tenant VRF and VLAN
                for idx, p in enumerate(parts):
                    if p.startswith("Vrf_") or p == "default":
                        tenant_vrf = p
                        if idx + 1 < len(parts):
                            vlan = parts[idx + 1]
                        break

                vni_rows.append({
                    "vni": vni_num,
                    "type": vni_type,
                    "vxlan_if": vxlan_if,
                    "tenant_vrf": tenant_vrf,
                    "vlan": vlan,
                    "is_target": tenant_vrf.lower() == target_vrf_name.lower()
                })

        # Parse VRF table
        vrf_list: List[Dict[str, str]] = []
        for line in raw_vrf.splitlines():
            # Example: vrf Vrf_31 id 107 table 1003 (configured)
            m = re.search(r"vrf\s+(\S+)\s+(?:id\s+(\d+)\s+)?table\s+(\d+)", line)
            if m:
                vrf_list.append({
                    "name": m.group(1),
                    "table_id": m.group(3),
                    "is_target": m.group(1).lower() == target_vrf_name.lower()
                })

        target_vnis = [r for r in vni_rows if r["is_target"]]
        other_vnis = [r for r in vni_rows if not r["is_target"] and r["tenant_vrf"].startswith("Vrf_")]

        # Query detailed VNI state for target L2 VNI and alternate L2 VNI
        target_l2_vni = next((v["vni"] for v in target_vnis if v["type"] == "L2"), None)
        other_l2_vni = next((v["vni"] for v in other_vnis if v["type"] == "L2"), None)

        raw_vni_detail_target = ""
        if target_l2_vni:
            raw_vni_detail_target = self._exec_on_switch(
                self.ns_switch_ip, f"sudo vtysh -c 'show evpn vni {target_l2_vni}'"
            )

        raw_vni_detail_other = ""
        if other_l2_vni:
            raw_vni_detail_other = self._exec_on_switch(
                self.ns_switch_ip, f"sudo vtysh -c 'show evpn vni {other_l2_vni}'"
            )

        # Query Linux kernel VLAN-aware bridge port membership
        raw_bridge_vlan = self._exec_on_switch(self.ns_switch_ip, "sudo bridge vlan show")

        return {
            "switch_name": "ns-leaf-0",
            "switch_ip": self.ns_switch_ip,
            "target_vrf": target_vrf_name,
            "all_vnis": vni_rows,
            "target_vnis": target_vnis,
            "other_tenant_vnis": other_vnis,
            "vrfs": vrf_list,
            "raw_output": raw_vni,
            "raw_vni_detail_target": raw_vni_detail_target,
            "raw_vni_detail_other": raw_vni_detail_other,
            "raw_bridge_vlan": raw_bridge_vlan
        }

    # ------------------------------------------------------------------
    # East-West Pure VRF Inspection
    # ------------------------------------------------------------------
    def inspect_ew_vrf_tables(self, target_vpc_id: int, other_vpc_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Queries East-West switch (leaf-pod00-su0-r0) for:
        1. Pure VRF table definitions
        2. Routes inside the target VPC VRF
        3. Routes inside other tenant VRFs to prove zero route leakage.
        """
        target_vrf = f"Vrf_{target_vpc_id}"
        other_vrf = f"Vrf_{other_vpc_id}" if other_vpc_id else None

        raw_vrf = self._exec_on_switch(self.ew_switch_ip, "sudo vtysh -c 'show vrf'")
        raw_routes_target = self._exec_on_switch(
            self.ew_switch_ip, f"sudo vtysh -c 'show ip route vrf {target_vrf}'"
        )

        raw_routes_other = ""
        if other_vrf:
            raw_routes_other = self._exec_on_switch(
                self.ew_switch_ip, f"sudo vtysh -c 'show ip route vrf {other_vrf}'"
            )

        # Parse connected routes & interfaces for target VRF
        target_subnets = []
        for line in raw_routes_target.splitlines():
            # Example: C>* 172.16.0.0/31 is directly connected, swp1s0, 09:56:13
            m = re.search(r"C>\*\s+([0-9./]+)\s+is directly connected,\s+(\S+)", line)
            if m:
                target_subnets.append({"subnet": m.group(1), "interface": m.group(2).rstrip(",")})

        other_subnets = []
        if raw_routes_other:
            for line in raw_routes_other.splitlines():
                m = re.search(r"C>\*\s+([0-9./]+)\s+is directly connected,\s+(\S+)", line)
                if m:
                    other_subnets.append({"subnet": m.group(1), "interface": m.group(2).rstrip(",")})

        return {
            "switch_name": "leaf-pod00-su0-r0",
            "switch_ip": self.ew_switch_ip,
            "target_vrf": target_vrf,
            "target_subnets": target_subnets,
            "other_vrf": other_vrf,
            "other_subnets": other_subnets,
            "raw_routes_target": raw_routes_target,
            "raw_routes_other": raw_routes_other
        }
