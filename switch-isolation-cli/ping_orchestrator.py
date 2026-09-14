"""
Ping Orchestrator.
Automates intra-VPC cluster health checks and cross-VPC isolation verification
via cluster-ping.sh across the bare-metal fleet over the SSH Jump Host.
"""

import concurrent.futures
import paramiko
import re
from typing import Any, Callable, Dict, List, Optional, Tuple


_ALIAS_RE = re.compile(r"alias (hgx-\S+)='ssh .*?root@([0-9.]+)'")
_SU_HOST_RE = re.compile(r"su(\d+)-h(\d+)")


def parse_su_host(server_name: str) -> Optional[Tuple[int, int]]:
    """Extracts (su, host) integer tuple from server name e.g. hgx-pod00-su0-h03 -> (0, 3)."""
    m = _SU_HOST_RE.search(server_name)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


class PingOrchestrator:
    def __init__(
        self,
        jump_host: str,
        jump_port: int,
        jump_user: str,
        jump_password: str
    ):
        self.jump_host = jump_host
        self.jump_port = jump_port
        self.jump_user = jump_user
        self.jump_password = jump_password
        self._aliases: Dict[str, str] = {}
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

    def resolve_aliases(self) -> Dict[str, str]:
        """Resolves bash aliases defined in ~/.bash_aliases on the jump host."""
        if self._aliases:
            return self._aliases
        jump = self._get_jump_client()
        stdin, stdout, stderr = jump.exec_command("bash -i -c alias 2>/dev/null", timeout=10)
        raw = stdout.read().decode("utf-8")
        mapping = {}
        for line in raw.splitlines():
            m = _ALIAS_RE.search(line)
            if m:
                mapping[m.group(1)] = m.group(2)
        self._aliases = mapping
        return mapping

    def run_cluster_ping(
        self,
        source_server_name: str,
        target_su: int,
        target_host: int,
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        Executes ./cluster-ping.sh <target_su> <target_host> on source_server_name.
        Returns parsed test metrics for East-West rails, North-South, and IPMI.
        """
        aliases = self.resolve_aliases()
        source_ip = aliases.get(source_server_name)
        if not source_ip:
            raise RuntimeError(f"No IP alias found for {source_server_name} on jump host.")

        jump = self._get_jump_client()
        cmd = (
            f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
            f"-o BatchMode=yes -o ConnectTimeout=10 root@{source_ip} "
            f"\"./cluster-ping.sh {target_su} {target_host}\""
        )

        stdin, stdout, stderr = jump.exec_command(cmd, timeout=timeout)
        raw_output = stdout.read().decode("utf-8")

        # Parse rail statuses
        rails: Dict[str, str] = {}
        for r_idx in range(8):
            r_name = f"rail{r_idx}"
            # ping rail0 (172.16.0.2)    : OK
            m = re.search(rf"ping {r_name}\s+\(([^)]+)\)\s+:\s+(\w+)", raw_output)
            if m:
                rails[r_name] = {"ip": m.group(1), "status": m.group(2)}
            else:
                rails[r_name] = {"ip": "unknown", "status": "Timeout"}

        # Parse North-South bond0
        ns_m = re.search(r"ping bond0\s+\(([^)]+)\)\s+:\s+(\w+)", raw_output)
        ns_status = ns_m.group(2) if ns_m else "Timeout"
        ns_ip = ns_m.group(1) if ns_m else "unknown"

        # Parse IPMI
        ipmi_m = re.search(r"ping eth11\s+\(([^)]+)\)\s+:\s+(\w+)", raw_output)
        ipmi_status = ipmi_m.group(2) if ipmi_m else "Timeout"
        ipmi_ip = ipmi_m.group(1) if ipmi_m else "unknown"

        all_ok = (
            all(r["status"] == "OK" for r in rails.values())
            and ns_status == "OK"
            and ipmi_status == "OK"
        )
        all_timeout = (
            all(r["status"] == "Timeout" for r in rails.values())
            and ns_status == "Timeout"
        )

        return {
            "source_server": source_server_name,
            "target_su": target_su,
            "target_host": target_host,
            "rails": rails,
            "north_south": {"ip": ns_ip, "status": ns_status},
            "ipmi": {"ip": ipmi_ip, "status": ipmi_status},
            "all_ok": all_ok,
            "all_isolated": all_timeout,
            "raw_output": raw_output
        }

    def execute_intra_vpc_connectivity_matrix(
        self,
        servers: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes sequential cluster-ping across all member servers in the VPC.
        Selects a leader host (e.g. host 0) and tests connectivity to all other peer hosts.
        """
        if len(servers) < 2:
            return []

        results = []
        source_server = servers[0]["name"]
        targets = servers[1:]

        for idx, target in enumerate(targets):
            t_name = target["name"]
            su_host = parse_su_host(t_name)
            if not su_host:
                continue
            su, host_num = su_host

            if progress_callback:
                progress_callback(f"{source_server} → {t_name}", idx + 1, len(targets))

            res = self.run_cluster_ping(source_server, su, host_num)
            results.append({
                "source": source_server,
                "target": t_name,
                "su": su,
                "host": host_num,
                "result": res
            })

        return results

    def execute_cross_vpc_isolation_check(
        self,
        source_server_name: str,
        isolation_target_name: str
    ) -> Dict[str, Any]:
        """
        Executes cluster-ping from source_server to isolation_target_name.
        Validates that 100% of East-West and North-South probes time out (isolated).
        """
        su_host = parse_su_host(isolation_target_name)
        if not su_host:
            raise ValueError(f"Could not parse SU/Host from target {isolation_target_name}")

        su, host_num = su_host
        res = self.run_cluster_ping(source_server_name, su, host_num)
        return {
            "source": source_server_name,
            "target": isolation_target_name,
            "su": su,
            "host": host_num,
            "result": res,
            "is_isolated": res["all_isolated"]
        }

    def execute_multi_cross_vpc_isolation_check(
        self,
        source_server_name: str,
        isolation_targets: List[Tuple[str, str]],
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tests isolation against multiple non-VPC targets across the datacenter.
        Validates that 100% of probes time out on all targets.
        """
        results = []
        for idx, (t_name, desc) in enumerate(isolation_targets):
            su_host = parse_su_host(t_name)
            if not su_host:
                continue
            su, host_num = su_host
            if progress_callback:
                progress_callback(f"{source_server_name} → {t_name}", idx + 1, len(isolation_targets))
            res = self.run_cluster_ping(source_server_name, su, host_num)
            results.append({
                "source": source_server_name,
                "target": t_name,
                "description": desc,
                "su": su,
                "host": host_num,
                "result": res,
                "is_isolated": res["all_isolated"]
            })
        return results
