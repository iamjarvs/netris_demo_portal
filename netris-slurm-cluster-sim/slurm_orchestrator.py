#!/usr/bin/env python3
"""
slurm_orchestrator.py - Slurm Workload Manager & Netris Lifecycle Orchestrator
Simulates realistic Slurm multi-node GPU job scheduling with dynamic Netris
Server Cluster and RoCEv2 V-Net provisioning and teardown.
"""

import copy
import logging
import random
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from netris_api import NetrisAPIClient

logger = logging.getLogger("slurm_sim")

# Catalog of realistic AI workload profiles (Minimum 7 minutes / 420s duration)
WORKLOAD_TEMPLATES = [
    {
        "name": "LLaMA-3-70B-Pretrain",
        "nodes": 4,
        "duration": 480,  # 8 minutes
        "pattern": "Ring-AllReduce",
        "user": "core-ai-infra",
        "traffic_type": "allreduce",
    },
    {
        "name": "DeepSeek-MoE-Align",
        "nodes": 8,
        "duration": 600,  # 10 minutes
        "pattern": "MoE-AllToAll",
        "user": "alignment-team",
        "traffic_type": "alltoall",
    },
    {
        "name": "Mixtral-8x7B-FineTune",
        "nodes": 2,
        "duration": 420,  # 7 minutes
        "pattern": "Tensor-Parallel",
        "user": "fine-tuning-lab",
        "traffic_type": "allreduce",
    },
    {
        "name": "SDXL-Diffusion-Batch",
        "nodes": 2,
        "duration": 450,  # 7.5 minutes
        "pattern": "Ring-AllReduce",
        "user": "generative-media",
        "traffic_type": "allreduce",
    },
    {
        "name": "AlphaFold-3-Structure",
        "nodes": 4,
        "duration": 540,  # 9 minutes
        "pattern": "MoE-AllToAll",
        "user": "biotech-research",
        "traffic_type": "alltoall",
    },
    {
        "name": "Whisper-v3-Inference",
        "nodes": 2,
        "duration": 420,  # 7 minutes
        "pattern": "Pipeline-Parallel",
        "user": "speech-systems",
        "traffic_type": "p2p",
    },
    {
        "name": "Nemotron-4-RewardModel",
        "nodes": 4,
        "duration": 510,  # 8.5 minutes
        "pattern": "Ring-AllReduce",
        "user": "rlhf-research",
        "traffic_type": "allreduce",
    },
]


class SlurmOrchestrator:
    """Manages the Slurm node pool, job queue, and Netris cluster lifecycle."""

    def __init__(
        self,
        netris_client: NetrisAPIClient,
        pool_size: int = 12,
        node_prefix: str = "hgx-pod00-su0-h",
        autopilot: bool = True,
        prov_time: int = 120,          # ~2 mins to provision VPC & RoCEv2 V-Net
        teardown_time: int = 120,      # ~2 mins to tear down
        min_job_duration: int = 420,   # Minimum 7 minutes run time
        autopilot_interval: int = 60,  # Seconds between autopilot scheduling attempts
        speedup: float = 1.0,          # Speedup multiplier for simulation clock
        on_state_change: Optional[Callable[[], None]] = None,
    ):
        self.client = netris_client
        self.pool_size = pool_size
        self.node_prefix = node_prefix
        self.autopilot = autopilot
        self.prov_time = max(5, int(prov_time / speedup))
        self.teardown_time = max(5, int(teardown_time / speedup))
        self.min_job_duration = max(5, int(min_job_duration / speedup))
        self.autopilot_interval = max(5, int(autopilot_interval / speedup))
        self.speedup = speedup
        self.on_state_change = on_state_change

        self.lock = threading.RLock()
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.last_autopilot_dispatch = 0.0

        # Data structures
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.job_history: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.job_counter = 1000

        # Wire client events into orchestrator event log
        self.client.event_callback = self._on_client_event

    def _log_event(self, source: str, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Records a timestamped event into the log buffer."""
        event = {
            "id": len(self.events) + 1,
            "timestamp": time.strftime("%H:%M:%S"),
            "source": source,  # SLURM, NETRIS, FABRIC
            "type": event_type,
            "message": message,
            "details": details or {},
        }
        with self.lock:
            self.events.append(event)
            if len(self.events) > 150:
                self.events.pop(0)

        logger.info(f"[{source}] [{event_type}] {message}")
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception:
                pass

    def _on_client_event(self, action: str, message: str, details: Dict[str, Any]):
        """Handler for events coming directly from Netris API client."""
        source = "NETRIS"
        if "CLUSTER_CREATE" in action:
            source = "NETRIS_API"
        elif "CLUSTER_READY" in action:
            source = "NETRIS_FABRIC"
        elif "CLUSTER_DELETE" in action:
            source = "NETRIS_API"
        elif "CLUSTER_REMOVED" in action:
            source = "NETRIS_FABRIC"
        self._log_event(source, action, message, details)

    def initialize_node_pool(self):
        """Discovers unassigned HGX nodes from Netris and initializes the Slurm partition."""
        self._log_event("SLURM", "INIT", "Interrogating Netris Controller for unassigned HGX GPU servers...")
        available = self.client.get_available_servers(name_prefix=self.node_prefix)
        if not available:
            # Fallback to any hgx- servers if prefix didn't match
            available = self.client.get_available_servers(name_prefix="hgx-")
        if not available and getattr(self.client, "sim_mode", False):
            available = self.client.get_servers()

        # Sort nodes naturally by hostname
        available.sort(key=lambda s: s.get("name", ""))

        # Take up to pool_size nodes
        selected = available[: self.pool_size]
        with self.lock:
            self.nodes.clear()
            for s in selected:
                name = s["name"]
                self.nodes[name] = {
                    "id": s["id"],
                    "name": name,
                    "state": "IDLE",  # IDLE, PROVISIONING, ALLOCATED, TEARDOWN
                    "job_id": None,
                    "cluster_id": None,
                    "cluster_name": None,
                    "gpus": 8,
                    "rails": 8,
                    "rail_activity": [0.0] * 8,
                    "site_id": s.get("site", {}).get("id", 3),
                    "tenant_id": s.get("tenant", {}).get("id", 1),
                }

        node_names = list(self.nodes.keys())
        self._log_event(
            "SLURM",
            "POOL_READY",
            f"Slurm partition initialized with {len(self.nodes)} HGX servers ({len(self.nodes) * 8} GPUs): {node_names[0]}..{node_names[-1]}",
            {"nodes": node_names, "total_gpus": len(self.nodes) * 8},
        )

    def get_idle_nodes(self) -> List[Dict[str, Any]]:
        """Returns list of currently idle nodes."""
        with self.lock:
            return [n for n in self.nodes.values() if n["state"] == "IDLE"]

    def submit_job(
        self,
        name: str,
        nodes_count: int,
        duration: int,
        pattern: str = "Ring-AllReduce",
        user: str = "ai-researcher",
        traffic_type: str = "allreduce",
    ) -> str:
        """Submits a new AI job to the Slurm queue."""
        with self.lock:
            self.job_counter += 1
            job_id = f"job-{self.job_counter}"
            final_duration = max(self.min_job_duration, duration)
            job = {
                "id": job_id,
                "name": name,
                "nodes_count": nodes_count,
                "duration": final_duration,
                "pattern": pattern,
                "traffic_type": traffic_type,
                "user": user,
                "state": "PENDING",  # PENDING, PROVISIONING, RUNNING, TEARDOWN, COMPLETED
                "created_at": time.time(),
                "provision_started_at": None,
                "provision_elapsed": 0.0,
                "provision_time": self.prov_time,
                "started_at": None,
                "elapsed": 0.0,
                "progress": 0.0,
                "teardown_started_at": None,
                "teardown_elapsed": 0.0,
                "teardown_time": self.teardown_time,
                "allocated_nodes": [],
                "cluster_id": None,
                "cluster_name": f"slurm-{job_id}",
                "vnet_name": f"slurm-{job_id}-East-West",
                "throughput_gbps": 0.0,
            }
            self.jobs[job_id] = job

        dur_m = int(final_duration // 60)
        dur_s = int(final_duration % 60)
        self._log_event(
            "SLURM",
            "JOB_SUBMITTED",
            f"Job {job_id} ('{name}') submitted by '{user}' - requesting {nodes_count} nodes ({nodes_count * 8} GPUs), duration {dur_m}m {dur_s}s [{pattern}]",
            {"job_id": job_id, "nodes_requested": nodes_count, "workload": name},
        )
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        """Cancels a pending or running job and triggers teardown."""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            if job["state"] == "PENDING":
                job["state"] = "CANCELLED"
                self.job_history.insert(0, copy.deepcopy(job))
                del self.jobs[job_id]
                self._log_event("SLURM", "JOB_CANCELLED", f"Job {job_id} cancelled while pending.")
                return True

            if job["state"] in ("PROVISIONING", "RUNNING"):
                job["state"] = "TEARDOWN"
                self._log_event("SLURM", "JOB_CANCELLED", f"Job {job_id} marked for immediate teardown.")
                return True

        return False

    def teardown_all(self):
        """Immediately cleans up all Netris clusters and resets all nodes to IDLE."""
        self._log_event("SLURM", "EMERGENCY_TEARDOWN", "Initiating global teardown of all Slurm clusters...")
        with self.lock:
            active_jobs = list(self.jobs.values())

        for job in active_jobs:
            cid = job.get("cluster_id")
            cname = job.get("cluster_name")
            if cid:
                try:
                    self.client.delete_server_cluster(cid, cluster_name=cname)
                except Exception as e:
                    logger.error(f"Error deleting cluster {cid}: {e}")

        # Also query Netris directly for any orphan clusters starting with 'slurm-'
        try:
            live_clusters = self.client.get_active_clusters()
            for c in live_clusters:
                if c.get("name", "").startswith("slurm-"):
                    cid = c.get("id")
                    cname = c.get("name")
                    try:
                        self.client.delete_server_cluster(cid, cluster_name=cname)
                    except Exception as e:
                        logger.error(f"Error cleaning orphan cluster {cid}: {e}")
        except Exception as e:
            logger.error(f"Error checking live clusters: {e}")

        with self.lock:
            for n in self.nodes.values():
                n["state"] = "IDLE"
                n["job_id"] = None
                n["cluster_id"] = None
                n["cluster_name"] = None
            self.jobs.clear()

        self._log_event("SLURM", "RESET_COMPLETE", "All Netris Server Clusters deprovisioned. Node pool reset to IDLE.")

    def _provision_job(self, job: Dict[str, Any], idle_nodes: List[Dict[str, Any]]):
        """Allocates nodes and initiates Netris Server Cluster provisioning (~2m)."""
        req_count = job["nodes_count"]
        allocated = idle_nodes[:req_count]
        node_names = [n["name"] for n in allocated]

        with self.lock:
            job["state"] = "PROVISIONING"
            job["provision_started_at"] = time.time()
            job["allocated_nodes"] = node_names
            for n in allocated:
                node_entry = self.nodes[n["name"]]
                node_entry["state"] = "PROVISIONING"
                node_entry["job_id"] = job["id"]
                node_entry["cluster_name"] = job["cluster_name"]

        self._log_event(
            "SLURM",
            "NODES_ASSIGNED",
            f"Job {job['id']} assigned {len(allocated)} nodes: {', '.join(node_names)} -> Initiating Netris Server Cluster & RoCEv2 V-Net provisioning (~2m expected)",
            {"job_id": job["id"], "nodes": node_names, "prov_time": self.prov_time},
        )

        def _do_netris_call():
            cluster_name = job["cluster_name"]
            server_payload = [{"id": n["id"], "name": n["name"]} for n in allocated]
            try:
                res = self.client.create_server_cluster(
                    cluster_name=cluster_name,
                    server_list=server_payload,
                )
                cid = res["cluster_id"]
                with self.lock:
                    if job["id"] in self.jobs:
                        job["cluster_id"] = cid
                        # Stays in PROVISIONING until prov_time (120s) elapses
                        for n in allocated:
                            if n["name"] in self.nodes:
                                self.nodes[n["name"]]["cluster_id"] = cid

                self._log_event(
                    "NETRIS_API",
                    "CLUSTER_CREATED",
                    f"Netris Controller created Server Cluster '{cluster_name}' (ID: {cid}). "
                    f"Switch agents synchronizing BGP EVPN & RoCEv2 V-Net (~2 mins)...",
                    {"job_id": job["id"], "cluster_id": cid, "nodes": node_names},
                )
            except Exception as e:
                logger.error(f"Failed to provision Netris cluster for {job['id']}: {e}")
                self._log_event(
                    "NETRIS",
                    "PROVISION_FAILED",
                    f"Netris failed to provision cluster for Job {job['id']}: {e}",
                    {"job_id": job["id"], "error": str(e)},
                )
                with self.lock:
                    job["state"] = "FAILED"
                    for n in allocated:
                        if n["name"] in self.nodes:
                            self.nodes[n["name"]]["state"] = "IDLE"
                            self.nodes[n["name"]]["job_id"] = None
                            self.nodes[n["name"]]["cluster_name"] = None

        threading.Thread(target=_do_netris_call, daemon=True).start()

    def _teardown_job(self, job: Dict[str, Any]):
        """Initiates Netris Server Cluster deprovisioning (~2m)."""
        cid = job.get("cluster_id")
        cname = job.get("cluster_name")
        allocated_names = job.get("allocated_nodes", [])

        with self.lock:
            job["state"] = "TEARDOWN"
            job["teardown_started_at"] = time.time()
            job["throughput_gbps"] = 0.0
            for name in allocated_names:
                if name in self.nodes:
                    self.nodes[name]["state"] = "TEARDOWN"
                    self.nodes[name]["rail_activity"] = [0.0] * 8

        dur_m = int(job['duration'] // 60)
        dur_s = int(job['duration'] % 60)
        self._log_event(
            "SLURM",
            "JOB_COMPLETED",
            f"Job {job['id']} training phase completed ({dur_m}m {dur_s}s) -> Initiating Netris deprovisioning (~2m expected)",
            {"job_id": job["id"], "cluster_id": cid, "teardown_time": self.teardown_time},
        )

        def _do_netris_teardown():
            if cid:
                try:
                    self.client.delete_server_cluster(cid, cluster_name=cname)
                except Exception as e:
                    logger.error(f"Error deprovisioning Netris cluster {cid}: {e}")

            self._log_event(
                "NETRIS_API",
                "CLUSTER_DELETE_REQUESTED",
                f"Netris Controller DELETE /api/v2/server-cluster/{cid} submitted. Deconfiguring switch ports & withdrawing routes...",
                {"job_id": job["id"], "cluster_id": cid},
            )

        threading.Thread(target=_do_netris_teardown, daemon=True).start()

    def _scheduler_tick(self):
        """Single tick of the Slurm scheduling loop."""
        now = time.time()

        # 1. Update jobs in PROVISIONING phase (simulate ~2m Netris switch agent programming)
        with self.lock:
            prov_jobs = [j for j in self.jobs.values() if j["state"] == "PROVISIONING"]

        for job in prov_jobs:
            if job["provision_started_at"]:
                elapsed_prov = now - job["provision_started_at"]
                job["provision_elapsed"] = round(elapsed_prov, 1)

                prov_sec = int(elapsed_prov)
                if prov_sec in (30, 60, 90) and job.get("_last_logged_prov") != prov_sec:
                    job["_last_logged_prov"] = prov_sec
                    self._log_event(
                        "NETRIS",
                        "PROVISIONING_SYNC",
                        f"Netris Cluster #{job.get('cluster_id', '')} ({job['cluster_name']}) provisioning in progress: "
                        f"Leaf switch agents configuring RoCEv2 fabric ({prov_sec}s / {self.prov_time}s)...",
                        {"job_id": job["id"], "cluster_id": job.get("cluster_id")},
                    )

                # Transition to RUNNING once prov_time (120s) has elapsed AND cluster_id is received
                if elapsed_prov >= self.prov_time and job.get("cluster_id"):
                    with self.lock:
                        job["state"] = "RUNNING"
                        job["started_at"] = now
                        for name in job["allocated_nodes"]:
                            if name in self.nodes:
                                self.nodes[name]["state"] = "ALLOCATED"

                    dur_m = int(job['duration'] // 60)
                    dur_s = int(job['duration'] % 60)
                    self._log_event(
                        "FABRIC",
                        "TRAFFIC_ACTIVE",
                        f"Netris Server Cluster #{job['cluster_id']} is Active! RoCEv2 fabric converged (~2m). "
                        f"Commencing distributed {job['pattern']} on Job {job['id']} across {len(job['allocated_nodes'])} nodes "
                        f"for {dur_m}m {dur_s}s.",
                        {"job_id": job["id"], "cluster_id": job["cluster_id"], "nodes": job["allocated_nodes"]},
                    )

        # 2. Update jobs in RUNNING phase (training workload for minimum 7 minutes)
        with self.lock:
            running_jobs = [j for j in self.jobs.values() if j["state"] == "RUNNING"]

        for job in running_jobs:
            if job["started_at"]:
                elapsed = now - job["started_at"]
                job["elapsed"] = round(elapsed, 1)
                job["progress"] = min(100.0, round((elapsed / job["duration"]) * 100, 1))

                # Simulate realistic 8-rail RoCEv2 collective throughput with 20% variation
                base_rail_bw = 48.0  # Gbps per 400G RoCEv2 rail (~384 Gbps aggregate per node)
                rails_data = []
                node_total_bw = 0.0
                total_pfc_pauses = 0
                total_cnp_pkts = 0

                for r in range(8):
                    # 20% variance per rail (0.80 to 1.20)
                    rail_var = random.uniform(0.80, 1.20)
                    r_bw = round(base_rail_bw * rail_var, 2)
                    node_total_bw += r_bw
                    pfc = random.randint(0, 3)
                    cnp = random.randint(1, 8)
                    total_pfc_pauses += pfc
                    total_cnp_pkts += cnp
                    rails_data.append({
                        "rail": r,
                        "interface": f"ens{5+r}",
                        "bandwidth_gbps": r_bw,
                        "utilization_pct": round((r_bw / 50.0) * 100, 1),
                        "pfc_pause_sec": pfc,
                        "cnp_pkts_sec": cnp,
                        "latency_us": round(random.uniform(1.25, 1.55), 2),
                        "lossless_drops": 0,
                    })

                # Scale aggregate throughput across all allocated nodes for this job
                job_total_bw = round(node_total_bw * job["nodes_count"], 1)
                job["throughput_gbps"] = job_total_bw
                job["telemetry"] = {
                    "rails": rails_data,
                    "avg_rail_bw_gbps": round(node_total_bw / 8.0, 2),
                    "node_aggregate_gbps": round(node_total_bw, 1),
                    "total_pfc_pause_sec": total_pfc_pauses * job["nodes_count"],
                    "total_cnp_pkts_sec": total_cnp_pkts * job["nodes_count"],
                    "fabric_latency_us": round(random.uniform(1.30, 1.45), 2),
                    "lossless_quality": "100.0% (Zero Drops)",
                    "chunk_transfer_mb": 64 if "AllReduce" in job["pattern"] else (128 if "AllToAll" in job["pattern"] else 32),
                }

                # Update live rail activity on each allocated node
                with self.lock:
                    for name in job.get("allocated_nodes", []):
                        if name in self.nodes:
                            self.nodes[name]["rail_activity"] = [r["bandwidth_gbps"] for r in rails_data]

                if elapsed >= job["duration"]:
                    self._teardown_job(job)

        # 3. Update jobs in TEARDOWN phase (~2m Netris deconfiguration & route withdrawal)
        with self.lock:
            teardown_jobs = [j for j in self.jobs.values() if j["state"] == "TEARDOWN"]

        for job in teardown_jobs:
            if job["teardown_started_at"]:
                elapsed_tear = now - job["teardown_started_at"]
                job["teardown_elapsed"] = round(elapsed_tear, 1)

                tear_sec = int(elapsed_tear)
                if tear_sec in (30, 60, 90) and job.get("_last_logged_tear") != tear_sec:
                    job["_last_logged_tear"] = tear_sec
                    self._log_event(
                        "NETRIS",
                        "TEARDOWN_SYNC",
                        f"Server Cluster #{job.get('cluster_id', '')} teardown in progress: "
                        f"Deconfiguring leaf switch ports & withdrawing routes ({tear_sec}s / {self.teardown_time}s)...",
                        {"job_id": job["id"], "cluster_id": job.get("cluster_id")},
                    )

                if elapsed_tear >= self.teardown_time:
                    allocated_names = job.get("allocated_nodes", [])
                    with self.lock:
                        for name in allocated_names:
                            if name in self.nodes:
                                self.nodes[name]["state"] = "IDLE"
                                self.nodes[name]["job_id"] = None
                                self.nodes[name]["cluster_id"] = None
                                self.nodes[name]["cluster_name"] = None
                                self.nodes[name]["rail_activity"] = [0.0] * 8

                        job["state"] = "COMPLETED"
                        job["completed_at"] = now
                        self.job_history.insert(0, copy.deepcopy(job))
                        if len(self.job_history) > 25:
                            self.job_history.pop()

                        if job["id"] in self.jobs:
                            del self.jobs[job["id"]]

                    self._log_event(
                        "SLURM",
                        "NODES_RELEASED",
                        f"Netris teardown complete (~2m). Job {job['id']} finished. "
                        f"{len(allocated_names)} nodes returned to IDLE pool: {', '.join(allocated_names)}",
                        {"job_id": job["id"], "released_nodes": allocated_names},
                    )

        # 4. Schedule pending jobs if nodes are available
        with self.lock:
            pending_jobs = [j for j in self.jobs.values() if j["state"] == "PENDING"]
            idle_nodes = [n for n in self.nodes.values() if n["state"] == "IDLE"]

        for job in pending_jobs:
            if len(idle_nodes) >= job["nodes_count"]:
                self._provision_job(job, idle_nodes)
                idle_nodes = idle_nodes[job["nodes_count"] :]

        # 5. Autopilot: Slowly schedule realistic AI jobs with measured pacing
        if self.autopilot:
            with self.lock:
                current_idle = len([n for n in self.nodes.values() if n["state"] == "IDLE"])
                pending_count = len([j for j in self.jobs.values() if j["state"] == "PENDING"])
                prov_count = len([j for j in self.jobs.values() if j["state"] == "PROVISIONING"])

            # Wait at least autopilot_interval between job dispatches and limit concurrent provisioning
            if (now - self.last_autopilot_dispatch >= self.autopilot_interval) and current_idle >= 2 and pending_count == 0 and prov_count < 2:
                fitting_templates = [t for t in WORKLOAD_TEMPLATES if t["nodes"] <= current_idle]
                if fitting_templates:
                    tmpl = random.choice(fitting_templates)
                    dur = max(self.min_job_duration, int(tmpl["duration"] * random.uniform(0.9, 1.1)))
                    self.last_autopilot_dispatch = now
                    self.submit_job(
                        name=tmpl["name"],
                        nodes_count=tmpl["nodes"],
                        duration=dur,
                        pattern=tmpl["pattern"],
                        user=tmpl["user"],
                        traffic_type=tmpl["traffic_type"],
                    )

    def start(self):
        """Starts the background Slurm scheduler thread."""
        if self.running:
            return
        self.running = True
        self.initialize_node_pool()

        def _run_loop():
            logger.info("Slurm Orchestrator scheduler loop started.")
            while self.running:
                try:
                    self._scheduler_tick()
                except Exception as e:
                    logger.error(f"Scheduler tick error: {e}", exc_info=True)
                time.sleep(1.0)
            logger.info("Slurm Orchestrator scheduler loop stopped.")

        self.scheduler_thread = threading.Thread(target=_run_loop, daemon=True)
        self.scheduler_thread.start()

    def stop(self):
        """Stops the scheduler loop."""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=3.0)

    def get_cluster_snapshot(self) -> Dict[str, Any]:
        """Returns a complete JSON-serializable snapshot of the cluster state."""
        with self.lock:
            idle_count = len([n for n in self.nodes.values() if n["state"] == "IDLE"])
            alloc_count = len([n for n in self.nodes.values() if n["state"] in ("ALLOCATED", "PROVISIONING")])
            total_nodes = len(self.nodes)
            total_gpus = total_nodes * 8
            used_gpus = alloc_count * 8

            total_bw = sum(j.get("throughput_gbps", 0.0) for j in self.jobs.values() if j["state"] == "RUNNING")

            # Aggregate 8-rail fabric telemetry
            active_running_jobs = [j for j in self.jobs.values() if j["state"] == "RUNNING"]
            if active_running_jobs:
                fabric_rails = [0.0] * 8
                pfc_total = 0
                cnp_total = 0
                latency_samples = []
                for j in active_running_jobs:
                    tel = j.get("telemetry", {})
                    pfc_total += tel.get("total_pfc_pause_sec", 0)
                    cnp_total += tel.get("total_cnp_pkts_sec", 0)
                    if "fabric_latency_us" in tel:
                        latency_samples.append(tel["fabric_latency_us"])
                    for idx, r in enumerate(tel.get("rails", [])):
                        fabric_rails[idx] += r.get("bandwidth_gbps", 0.0)

                avg_lat = round(sum(latency_samples) / max(1, len(latency_samples)), 2) if latency_samples else 1.38
                global_telemetry = {
                    "active": True,
                    "rails": [round(b, 1) for b in fabric_rails],
                    "total_pfc_pauses": pfc_total,
                    "total_cnp_notifications": cnp_total,
                    "avg_latency_us": avg_lat,
                    "lossless_drops": 0,
                    "fabric_status": "RoCEv2 Lossless Active (PFC+ETS Converged)",
                }
            else:
                global_telemetry = {
                    "active": False,
                    "rails": [0.0] * 8,
                    "total_pfc_pauses": 0,
                    "total_cnp_notifications": 0,
                    "avg_latency_us": 0.0,
                    "lossless_drops": 0,
                    "fabric_status": "Standby (Awaiting Workload)",
                }

            snapshot = {
                "summary": {
                    "total_nodes": total_nodes,
                    "idle_nodes": idle_count,
                    "allocated_nodes": alloc_count,
                    "total_gpus": total_gpus,
                    "used_gpus": used_gpus,
                    "active_jobs": len([j for j in self.jobs.values() if j["state"] == "RUNNING"]),
                    "pending_jobs": len([j for j in self.jobs.values() if j["state"] == "PENDING"]),
                    "total_bandwidth_gbps": round(total_bw, 1),
                    "autopilot": self.autopilot,
                },
                "is_sim_mode": getattr(self.client, "sim_mode", False),
                "telemetry": global_telemetry,
                "nodes": list(self.nodes.values()),
                "jobs": list(self.jobs.values()),
                "history": list(self.job_history),
                "events": list(self.events),
            }
            return snapshot


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    client = NetrisAPIClient()
    client.authenticate()
    orch = SlurmOrchestrator(client, pool_size=8, autopilot=False)
    orch.start()
    print("Pool initialized.")
    time.sleep(2)
    job_id = orch.submit_job("Test-MoE", nodes_count=2, duration=15)
    print(f"Submitted {job_id}. Waiting for execution...")
    time.sleep(20)
    orch.stop()
    print("Test run completed.")
