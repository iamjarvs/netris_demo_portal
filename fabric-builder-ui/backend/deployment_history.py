"""
deployment_history.py
Manages deployment inventory, state inspection across workspace directories,
and persistent audit logging for OpenTofu / Terraform operations.
"""

import os
import re
import json
import time
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional

DEPLOYMENTS_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "deployments"))
HISTORY_FILE = os.path.join(DEPLOYMENTS_BASE_DIR, "history.json")


class DeploymentHistoryManager:
    def __init__(self, base_dir: str = DEPLOYMENTS_BASE_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.history_file = os.path.join(self.base_dir, "history.json")
        if not os.path.exists(self.history_file):
            self._save_history([])

    def _load_history(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_history(self, events: List[Dict[str, Any]]):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(events, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def record_event(
        self,
        site_slug: str,
        site_name: str,
        action: str,
        status: str,
        exit_code: Optional[int],
        duration_seconds: float,
        plan_summary: Optional[Dict[str, Any]] = None,
        resource_count: int = 0,
        controller_url: str = "",
        logs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Record an execution event in persistent history and save per-run log file."""
        now = datetime.now()
        timestamp_str = now.isoformat()
        event_id = f"evt-{int(now.timestamp())}-{site_slug}-{action}"

        # Save log file in deployment directory
        log_rel_path = ""
        if logs and os.path.exists(os.path.join(self.base_dir, site_slug)):
            log_dir = os.path.join(self.base_dir, site_slug, "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{action}_{status}.log"
            log_full_path = os.path.join(log_dir, log_filename)
            try:
                with open(log_full_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(logs))
                log_rel_path = os.path.join("logs", log_filename)
            except Exception:
                pass

        event = {
            "id": event_id,
            "site_slug": site_slug,
            "site_name": site_name or site_slug,
            "action": action,
            "status": status,
            "exit_code": exit_code,
            "duration_seconds": round(duration_seconds, 2),
            "timestamp": timestamp_str,
            "plan_summary": plan_summary or {"add": 0, "change": 0, "destroy": 0, "has_plan": False},
            "resource_count": resource_count,
            "controller_url": controller_url,
            "log_file": log_rel_path,
            "log_snippet": "\n".join(logs[-15:]) if logs else "",
        }

        history = self._load_history()
        history.insert(0, event)  # Most recent first
        # Keep max 500 events
        if len(history) > 500:
            history = history[:500]
        self._save_history(history)
        return event

    def get_history(self, limit: int = 50, site_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        history = self._load_history()
        if site_slug:
            history = [e for e in history if e.get("site_slug") == site_slug]
        return history[:limit]

    def scan_deployments(self) -> List[Dict[str, Any]]:
        """Scans all subdirectories in deployments/ and parses state, vars, and locks."""
        deployments = []
        if not os.path.exists(self.base_dir):
            return deployments

        for item in sorted(os.listdir(self.base_dir)):
            work_dir = os.path.join(self.base_dir, item)
            # Skip hidden folders, history file, or test runner folders like test_matrix
            if not os.path.isdir(work_dir) or item.startswith(".") or item == "test_matrix":
                continue

            info = self.inspect_deployment(item)
            deployments.append(info)

        # Sort: active deployments with resources first, then by last modified descending
        deployments.sort(
            key=lambda d: (
                1 if d.get("has_active_resources") else 0,
                d.get("last_modified_timestamp", 0)
            ),
            reverse=True
        )
        return deployments

    def inspect_deployment(self, slug: str) -> Dict[str, Any]:
        """Deeply inspects a single deployment directory."""
        work_dir = os.path.join(self.base_dir, slug)
        if not os.path.isdir(work_dir):
            return {
                "slug": slug,
                "exists": False,
                "site_name": slug,
                "resource_count": 0,
                "has_active_resources": False,
            }

        state_file = os.path.join(work_dir, "terraform.tfstate")
        vars_file = os.path.join(work_dir, "terraform.tfvars")
        lock_file = os.path.join(work_dir, ".terraform.tfstate.lock.info")
        plan_file = os.path.join(work_dir, "tofu.tfplan")

        # Extract config attributes from terraform.tfvars
        site_name = slug
        controller_address = "https://adam-ctl.netris.io"
        controller_login = "netris"
        if os.path.exists(vars_file):
            try:
                with open(vars_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    m_site = re.search(r'site_name\s*=\s*"([^"]+)"', content)
                    if m_site:
                        site_name = m_site.group(1)
                    m_ctl = re.search(r'controller_address\s*=\s*"([^"]+)"', content)
                    if m_ctl:
                        controller_address = m_ctl.group(1)
                    m_user = re.search(r'controller_login\s*=\s*"([^"]+)"', content)
                    if m_user:
                        controller_login = m_user.group(1)
            except Exception:
                pass

        # Inspect terraform.tfstate
        has_state = os.path.exists(state_file)
        serial = 0
        total_instances = 0
        resource_blocks = 0
        resources_breakdown = {}
        resource_details = []
        last_modified_ts = 0

        if has_state:
            last_modified_ts = os.path.getmtime(state_file)
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                    serial = state_data.get("serial", 0)
                    raw_resources = state_data.get("resources", [])
                    resource_blocks = len(raw_resources)

                    for r in raw_resources:
                        rtype = r.get("type", "")
                        rname = r.get("name", "")
                        instances = r.get("instances", [])
                        icount = len(instances)
                        total_instances += icount

                        # Aggregate breakdown by resource type
                        resources_breakdown[rtype] = resources_breakdown.get(rtype, 0) + icount

                        # Record detail for inspector
                        instance_keys = []
                        for inst in instances:
                            ikey = inst.get("index_key")
                            if ikey is not None:
                                instance_keys.append(str(ikey))

                        resource_details.append({
                            "type": rtype,
                            "name": rname,
                            "count": icount,
                            "mode": r.get("mode", "managed"),
                            "keys": instance_keys[:10],  # sample keys
                            "total_keys": len(instance_keys)
                        })
            except Exception as e:
                print(f"Error reading state file for {slug}: {e}")
        else:
            last_modified_ts = os.path.getmtime(work_dir)

        last_modified_str = datetime.fromtimestamp(last_modified_ts).strftime("%Y-%m-%d %H:%M:%S")

        # Also check backup state if available
        backup_file = state_file + ".backup"
        backup_instances = 0
        backup_breakdown = {}
        backup_resource_details = []
        if os.path.exists(backup_file):
            try:
                with open(backup_file, "r", encoding="utf-8") as f:
                    b_data = json.load(f)
                    for r in b_data.get("resources", []):
                        rtype = r.get("type", "")
                        rname = r.get("name", "")
                        instances = r.get("instances", [])
                        icount = len(instances)
                        backup_instances += icount
                        backup_breakdown[rtype] = backup_breakdown.get(rtype, 0) + icount
                        backup_resource_details.append({
                            "type": rtype,
                            "name": rname,
                            "count": icount,
                            "mode": r.get("mode", "managed"),
                        })
            except Exception:
                pass

        # Determine friendly status
        if total_instances > 0:
            status = "active"
        elif has_state and total_instances == 0:
            status = "destroyed"
        elif os.path.exists(plan_file):
            status = "planned"
        elif os.path.exists(vars_file):
            status = "configured"
        else:
            status = "empty"

        return {
            "slug": slug,
            "exists": True,
            "site_name": site_name,
            "work_dir": work_dir,
            "controller_address": controller_address,
            "controller_login": controller_login,
            "status": status,
            "has_state": has_state,
            "serial": serial,
            "resource_blocks": resource_blocks,
            "total_instances": total_instances,
            "has_active_resources": total_instances > 0,
            "breakdown": resources_breakdown if total_instances > 0 else backup_breakdown,
            "resource_details": resource_details if total_instances > 0 else backup_resource_details,
            "backup_instances": backup_instances,
            "is_locked": os.path.exists(lock_file),
            "has_plan": os.path.exists(plan_file),
            "last_modified": last_modified_str,
            "last_modified_timestamp": last_modified_ts,
        }

    def delete_deployment(self, slug: str, force: bool = False) -> Dict[str, Any]:
        """Deletes a deployment directory from disk. Refuses if active resources exist unless force=True."""
        info = self.inspect_deployment(slug)
        if not info.get("exists"):
            return {"success": False, "message": f"Deployment '{slug}' not found"}

        if info.get("has_active_resources") and not force:
            return {
                "success": False,
                "message": f"Deployment '{slug}' has {info.get('total_instances')} active resources. Run Destroy first!",
            }

        work_dir = info["work_dir"]
        try:
            shutil.rmtree(work_dir)
            # Log deletion event
            self.record_event(
                site_slug=slug,
                site_name=info.get("site_name", slug),
                action="delete_workspace",
                status="success",
                exit_code=0,
                duration_seconds=0.1,
                resource_count=0,
                controller_url=info.get("controller_address", ""),
                logs=[f"Deleted deployment directory {work_dir}"],
            )
            return {"success": True, "message": f"Deleted deployment workspace '{slug}'"}
        except Exception as e:
            return {"success": False, "message": str(e)}


# Singleton instance
history_manager = DeploymentHistoryManager()
