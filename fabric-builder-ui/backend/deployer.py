"""
deployer.py
Manages live OpenTofu execution (init, plan, apply, destroy, cleanup) with
unbuffered pseudo-terminal (PTY) log streaming and instant provider symlinks.
"""

import os
import re
import json
import shutil
import subprocess
import threading
import queue
import time
import pty
from typing import Dict, Any, Optional, List
from tf_generator import TerraformGenerator
from deployment_history import history_manager

DEPLOYMENTS_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "deployments"))
PROVIDER_CACHE_DIR = "/Users/adam/Downloads/kpn01-main/.terraform"
PROVIDER_LOCK_FILE = "/Users/adam/Downloads/kpn01-main/.terraform.lock.hcl"
TOFU_BIN = "/opt/homebrew/bin/tofu"


class DeploymentManager:
    def __init__(self):
        self.active_process: Optional[subprocess.Popen] = None
        self.current_action: Optional[str] = None
        self.active_slug: Optional[str] = None
        self.active_site_name: Optional[str] = None
        self.status = "idle"  # idle, running, success, failed, aborted
        self.exit_code: Optional[int] = None
        self.logs: list[str] = []
        self.log_subscribers: list[queue.Queue] = []
        self.plan_summary = {"add": 0, "change": 0, "destroy": 0, "has_plan": False}
        self.lock = threading.RLock()
        os.makedirs(DEPLOYMENTS_BASE_DIR, exist_ok=True)

    def get_workspace_dir(self, target: Any) -> str:
        if isinstance(target, str):
            return os.path.join(DEPLOYMENTS_BASE_DIR, target.lower().replace(" ", "-"))
        site_slug = target.get("site_name", "dc01").lower().replace(" ", "-")
        return os.path.join(DEPLOYMENTS_BASE_DIR, site_slug)

    def prepare_workspace(self, config: Dict[str, Any]) -> str:
        """Writes generated files into the deployment workspace directory with instantaneous symlinks."""
        work_dir = self.get_workspace_dir(config)
        os.makedirs(work_dir, exist_ok=True)

        gen = TerraformGenerator(config)
        files = gen.generate_all_files()

        for path, content in files.items():
            full_path = os.path.join(work_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Instantaneous symlink for provider plugins instead of copying 21MB
        target_tf_dir = os.path.join(work_dir, ".terraform")
        if os.path.exists(PROVIDER_CACHE_DIR) and not os.path.exists(target_tf_dir):
            try:
                os.symlink(PROVIDER_CACHE_DIR, target_tf_dir)
            except Exception:
                shutil.copytree(PROVIDER_CACHE_DIR, target_tf_dir)

        target_lock_file = os.path.join(work_dir, ".terraform.lock.hcl")
        if os.path.exists(PROVIDER_LOCK_FILE) and not os.path.exists(target_lock_file):
            try:
                shutil.copy(PROVIDER_LOCK_FILE, target_lock_file)
            except Exception:
                pass

        return work_dir

    def get_workspace_state(self, target: Any) -> Dict[str, Any]:
        """Inspects terraform.tfstate in the workspace to see what resources currently exist."""
        work_dir = self.get_workspace_dir(target)
        state_file = os.path.join(work_dir, "terraform.tfstate")
        lock_file = os.path.join(work_dir, ".terraform.tfstate.lock.info")

        res_list = []
        has_state = False
        serial = 0

        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    has_state = True
                    serial = data.get("serial", 0)
                    for r in data.get("resources", []):
                        res_type = r.get("type", "")
                        res_name = r.get("name", "")
                        instances = r.get("instances", [])
                        count = len(instances)
                        res_list.append({
                            "type": res_type,
                            "name": res_name,
                            "instances": count,
                        })
            except Exception:
                pass

        return {
            "work_dir": work_dir,
            "has_state": has_state,
            "serial": serial,
            "resource_count": len(res_list),
            "resources": res_list,
            "is_locked": os.path.exists(lock_file),
        }

    def purge_local_state(self, target: Any) -> Dict[str, Any]:
        """Cleans up local state, lock files, and plans for a config or slug."""
        with self.lock:
            if self.status == "running":
                return {"success": False, "message": "Cannot purge while an operation is running."}

        work_dir = self.get_workspace_dir(target)
        site_name = target if isinstance(target, str) else target.get("site_name", "workspace")
        removed = []
        for item in ["terraform.tfstate", "terraform.tfstate.backup", "tofu.tfplan", ".terraform.tfstate.lock.info"]:
            p = os.path.join(work_dir, item)
            if os.path.exists(p):
                try:
                    os.remove(p)
                    removed.append(item)
                except Exception:
                    pass

        self.plan_summary = {"add": 0, "change": 0, "destroy": 0, "has_plan": False}
        self._append_log(f"=== Purged local workspace state for {site_name}: {', '.join(removed) or 'none'} ===")
        return {"success": True, "removed": removed}

    def run_command(
        self,
        action: str,
        config: Optional[Dict[str, Any]] = None,
        slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs tofu init, plan, apply, destroy, or cleanup on a config or existing workspace slug."""
        with self.lock:
            if self.status == "running":
                return {"success": False, "message": "Another deployment operation is currently in progress."}

            self.status = "running"
            self.current_action = action
            self.exit_code = None
            self.logs = []

        try:
            if slug and not config:
                work_dir = os.path.join(DEPLOYMENTS_BASE_DIR, slug)
                if not os.path.isdir(work_dir):
                    with self.lock:
                        self.status = "idle"
                    return {"success": False, "message": f"Deployment workspace '{slug}' does not exist"}
                site_slug = slug
                dep_info = history_manager.inspect_deployment(slug)
                site_name = dep_info.get("site_name", slug)
                ctl_url = dep_info.get("controller_address", "")
            elif config:
                work_dir = self.prepare_workspace(config)
                site_slug = config.get("site_name", slug or "dc01").lower().replace(" ", "-")
                site_name = config.get("site_name", site_slug)
                ctl_url = config.get("controller_address", "")
            else:
                with self.lock:
                    self.status = "idle"
                return {"success": False, "message": "Either config or valid slug is required"}

            self.active_slug = site_slug
            self.active_site_name = site_name

            # Remove stale lock if any exists
            lock_file = os.path.join(work_dir, ".terraform.tfstate.lock.info")
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except Exception:
                    pass

            cmd = [TOFU_BIN]
            if action == "init":
                cmd.extend(["init", "-no-color", "-backend=false", "-get=false"])
            elif action == "plan":
                cmd.extend(["plan", "-refresh=false", "-parallelism=20", "-no-color", "-out=tofu.tfplan"])
            elif action == "apply":
                if os.path.exists(os.path.join(work_dir, "tofu.tfplan")):
                    cmd.extend(["apply", "-auto-approve", "-no-color", "tofu.tfplan"])
                else:
                    cmd.extend(["apply", "-auto-approve", "-refresh=false", "-parallelism=20", "-no-color"])
            elif action in ["destroy", "cleanup"]:
                cmd.extend(["destroy", "-auto-approve", "-parallelism=20", "-no-color"])
            else:
                with self.lock:
                    self.status = "idle"
                return {"success": False, "message": f"Unsupported action: {action}"}

            thread = threading.Thread(
                target=self._worker,
                args=(cmd, work_dir, action, site_slug, site_name, ctl_url),
                daemon=True
            )
            thread.start()
            return {"success": True, "action": action, "work_dir": work_dir, "site_slug": site_slug}

        except Exception as e:
            with self.lock:
                self.status = "failed"
                self.exit_code = 1
                self.current_action = action
            err_msg = str(e)
            self._append_log(f"✗ Deployment error: {err_msg}")
            return {"success": False, "message": err_msg}

    def _worker(
        self,
        cmd: list[str],
        work_dir: str,
        action: str,
        site_slug: str,
        site_name: str,
        ctl_url: str
    ):
        start_time = time.time()
        self._append_log(f"=== Starting 'tofu {action}' in {work_dir} ===")
        self._append_log(f"$ {' '.join(cmd)}\n")

        # Set environment to prevent interactive prompts and enable unbuffered output
        env = os.environ.copy()
        env["TF_IN_AUTOMATION"] = "1"
        env["PYTHONUNBUFFERED"] = "1"

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            self.active_process = proc

            for line in iter(proc.stdout.readline, ""):
                cleaned = line.rstrip("\r\n")
                self._append_log(cleaned)

                # Parse plan output in real time
                if "Plan:" in cleaned:
                    m = re.search(r"Plan:\s+(\d+)\s+to add,\s+(\d+)\s+to change,\s+(\d+)\s+to destroy", cleaned)
                    if m:
                        self.plan_summary = {
                            "add": int(m.group(1)),
                            "change": int(m.group(2)),
                            "destroy": int(m.group(3)),
                            "has_plan": True,
                        }

            proc.stdout.close()
            code = proc.wait()
            self.exit_code = code

            with self.lock:
                self.status = "success" if code == 0 else "failed"

            if code == 0:
                self._append_log(f"\n✓ 'tofu {action}' completed successfully.")
            else:
                self._append_log(f"\n✗ 'tofu {action}' exited with code {code}.")

        except Exception as e:
            with self.lock:
                self.status = "failed"
            self._append_log(f"\nError running process: {str(e)}")
        finally:
            self.active_process = None
            duration = time.time() - start_time
            try:
                # Record audit history event
                dep_info = history_manager.inspect_deployment(site_slug)
                curr_res = dep_info.get("total_instances", 0)
                history_manager.record_event(
                    site_slug=site_slug,
                    site_name=site_name,
                    action=action,
                    status=self.status,
                    exit_code=self.exit_code,
                    duration_seconds=duration,
                    plan_summary=self.plan_summary,
                    resource_count=curr_res,
                    controller_url=ctl_url,
                    logs=list(self.logs),
                )
            except Exception as e:
                print(f"Failed to record history event: {e}")

    def _append_log(self, text: str):
        with self.lock:
            self.logs.append(text)
        for q in list(self.log_subscribers):
            try:
                q.put_nowait(text)
            except queue.Full:
                pass

    def abort(self) -> Dict[str, Any]:
        with self.lock:
            if self.active_process and self.active_process.poll() is None:
                self.active_process.terminate()
                self.status = "aborted"
                self._append_log("\n⚠ Operation aborted by user.")
                return {"success": True, "message": "Process terminated"}
            elif self.status == "running":
                self.status = "aborted"
                self.active_process = None
                self._append_log("\n⚠ Reset stuck deployment status to aborted.")
                return {"success": True, "message": "Reset stuck status"}
            return {"success": False, "message": "No active operation to terminate"}

    def reset_state(self) -> Dict[str, Any]:
        with self.lock:
            if self.active_process and self.active_process.poll() is None:
                try:
                    self.active_process.terminate()
                except Exception:
                    pass
            self.status = "idle"
            self.current_action = None
            self.active_process = None
            self._append_log("\n✓ Deployment console state reset to idle.")
            return {"success": True, "message": "Deployment state reset to idle"}

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "status": self.status,
                "action": self.current_action,
                "active_slug": self.active_slug,
                "active_site_name": self.active_site_name,
                "exit_code": self.exit_code,
                "plan_summary": self.plan_summary,
                "log_count": len(self.logs),
            }

    def get_logs(self, since: int = 0) -> list[str]:
        with self.lock:
            return self.logs[since:]


# Global singleton instance
deploy_manager = DeploymentManager()
