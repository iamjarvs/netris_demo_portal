"""
topology_layout.py
Manages topology coordinates for the Netris Controller (/api/v2/topology/positions).

Provides two modes:
1. clear_layout(site_id): Clears hardcoded position overrides by setting them to None,
   allowing Netris Controller's native smart auto-layout physics and SU grouping to render cleanly.
2. apply_layout(site_id): Calculates a spacious, multi-column hierarchical grid with generous
   spacing (550px+ horizontal, 800px+ vertical) so nodes and labels never overlap.
"""

import re
import math
import json
import urllib.request
from typing import Dict, Any, List, Tuple
from netris_client import NetrisClient


class TopologyLayoutEngine:
    def __init__(self, client: NetrisClient):
        self.client = client

    def get_topology_data(self, site_id: int) -> Dict[str, Any]:
        """Fetch raw topology data for a given site."""
        endpoint = f"/api/v2/topology?siteID={site_id}"
        data = self.client._get(endpoint)
        if isinstance(data, dict):
            return data
        return {}

    def clear_layout(self, site_id: int) -> Dict[str, Any]:
        """
        Reset all saved positions to None so Netris Controller uses its native dynamic auto-layout.
        This removes any hardcoded pin overrides and lets Netris arrange the graph cleanly.
        """
        if not self.client.authenticated:
            auth = self.client.authenticate()
            if not auth["success"]:
                return {"success": False, "message": f"Auth failed: {auth['message']}"}

        top = self.get_topology_data(site_id)
        nodes = top.get("nodes", {})
        pos = top.get("positions", {})
        all_ids = set(nodes.keys()) | set(pos.keys())
        if not all_ids:
            return {"success": True, "message": "No nodes to reset in site topology."}

        # Setting position to None removes the pin/override on Netris Controller
        payload = {
            "siteID": site_id,
            "positions": {nid: None for nid in all_ids}
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.client.controller_url}/api/v2/topology/positions",
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with self.client.opener.open(req, timeout=20) as resp:
                body = resp.read().decode("utf-8")
                res = json.loads(body)
                return {
                    "success": True,
                    "site_id": site_id,
                    "message": f"Successfully reset {len(all_ids)} node positions to Netris native auto-layout.",
                    "details": res
                }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def categorize_nodes(self, nodes: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize raw Netris topology nodes into architectural roles."""
        cats = {
            "softgates": [],
            "ns_spines": [],
            "ns_leaves": [],
            "cp_servers": [],
            "backend_planes": {}, # plane_id -> {'spines': [], 'leaves': []}
            "storage_leaves": [],
            "storage_servers": [],
            "oob_switches": [],
            "gpu_servers": [],
            "other": [],
        }

        for nid, node in nodes.items():
            name = node.get("b", "") or node.get("name", "")
            ntype = node.get("d", "") or node.get("type", "")

            # Check spine / leaf via specific pattern
            is_spine = bool(re.search(r"(-sp\d+|-spine\d+)", name, re.IGNORECASE))
            is_leaf = bool(re.search(r"(-lf\d+|-leaf\d+)", name, re.IGNORECASE))

            if ntype == "offloader" or name.startswith("sg-") or "softgate" in name.lower():
                cats["softgates"].append((nid, name))
            elif "storage" in name.lower() and (ntype == "server" or name.startswith("srv-")):
                cats["storage_servers"].append((nid, name))
            elif "cp" in name.lower() and (ntype == "server" or name.startswith("srv-")):
                cats["cp_servers"].append((nid, name))
            elif "storage" in name.lower() and (ntype == "switch" or is_leaf):
                cats["storage_leaves"].append((nid, name))
            elif "oob" in name.lower() or "mgmt" in name.lower():
                cats["oob_switches"].append((nid, name))
            elif name.startswith("gpu-") or (ntype == "server" and "gpu" in name.lower()):
                cats["gpu_servers"].append((nid, name))
            elif "-ns-" in name.lower() or "frontend" in name.lower():
                if is_spine:
                    cats["ns_spines"].append((nid, name))
                else:
                    cats["ns_leaves"].append((nid, name))
            elif "-ew-" in name.lower() or "backend" in name.lower() or "plane" in name.lower():
                pl_match = re.search(r"pl(\d+)|plane(\d+)", name, re.IGNORECASE)
                pl = int(pl_match.group(1) or pl_match.group(2)) if pl_match else 1
                if pl not in cats["backend_planes"]:
                    cats["backend_planes"][pl] = {"spines": [], "leaves": []}
                if is_spine:
                    cats["backend_planes"][pl]["spines"].append((nid, name))
                else:
                    cats["backend_planes"][pl]["leaves"].append((nid, name))
            elif ntype == "server":
                cats["cp_servers"].append((nid, name))
            elif ntype == "switch":
                if is_spine:
                    cats["ns_spines"].append((nid, name))
                else:
                    cats["ns_leaves"].append((nid, name))
            else:
                cats["other"].append((nid, name))

        def sort_key(item):
            return item[1]

        cats["softgates"].sort(key=sort_key)
        cats["ns_spines"].sort(key=sort_key)
        cats["ns_leaves"].sort(key=sort_key)
        cats["cp_servers"].sort(key=sort_key)
        cats["storage_leaves"].sort(key=sort_key)
        cats["storage_servers"].sort(key=sort_key)
        cats["oob_switches"].sort(key=sort_key)
        cats["gpu_servers"].sort(key=sort_key)
        cats["other"].sort(key=sort_key)
        for pl in cats["backend_planes"]:
            cats["backend_planes"][pl]["spines"].sort(key=sort_key)
            cats["backend_planes"][pl]["leaves"].sort(key=sort_key)

        return cats

    def calculate_coordinates(self, nodes: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
        """
        Calculate spacious, non-overlapping grid coordinates following the user's architectural zones:
        1. TOP SECTION (Y: 100 - 1900):
           - Backend AI Multi-Plane Fabric:
             - Spines on top tier (Y = 100)
             - Leaves on middle tier (Y = 950)
             - GPU Compute servers spread across full width (Y = 1900)
        2. BOTTOM SECTION (Y: 3100 - 4700):
           - Frontend (North-South leaves Y=3100, spines Y=3900, SoftGates/CP servers Y=4700)
           - Storage (Storage leaves Y=3100, storage servers Y=3900)
        3. FAR-RIGHT SECTION (X > Backend Width):
           - Out-of-Band (OOB) management switches in a dedicated vertical management rail.
        """
        cats = self.categorize_nodes(nodes)
        positions = {}

        NODE_SPACING_X = 550
        PLANE_GAP = 900
        BOTTOM_POD_GAP = 900

        # -------------------------------------------------------------
        # Helper: place a single row with minimum center-to-center spacing
        # -------------------------------------------------------------
        def place_row(items: List[Tuple[str, str]], start_x: float, end_x: float, y: int):
            n = len(items)
            if n == 0:
                return
            if n == 1:
                cx = (start_x + end_x) / 2
                positions[items[0][0]] = {"x": int(cx), "y": int(y)}
                return
            width = max(end_x - start_x, (n - 1) * NODE_SPACING_X)
            step = width / (n - 1)
            mid_x = (start_x + end_x) / 2
            first_x = mid_x - ((n - 1) * step) / 2
            for i, (nid, _) in enumerate(items):
                positions[nid] = {"x": int(first_x + i * step), "y": int(y)}

        # Helper: place a multi-row grid centered between start_x and end_x
        def place_grid(items: List[Tuple[str, str]], start_x: float, end_x: float, base_y: int, max_per_row: int = 4, row_gap: int = 400):
            n = len(items)
            if n == 0:
                return
            rows = [items[i:i + max_per_row] for i in range(0, n, max_per_row)]
            for r_idx, row_items in enumerate(rows):
                y = base_y + r_idx * row_gap
                place_row(row_items, start_x, end_x, y)

        # =============================================================
        # ZONE 1: TOP - BACKEND AI MULTI-PLANE FABRIC & GPU COMPUTE
        # =============================================================
        backend_planes = cats["backend_planes"]
        gpu_servers = cats["gpu_servers"]

        Y_BACKEND_SPINES = 100
        Y_BACKEND_LEAVES = 950
        Y_GPU_SERVERS = 1900

        curr_x = 200.0
        plane_spans = {}

        # 1. Place each backend plane (spines on top, leaves below)
        sorted_planes = sorted(backend_planes.keys())
        for pl_id in sorted_planes:
            pl_data = backend_planes[pl_id]
            spines = pl_data["spines"]
            leaves = pl_data["leaves"]
            nodes_in_plane = max(len(spines), len(leaves), 1)
            plane_width = max(nodes_in_plane * NODE_SPACING_X, 1100)

            pl_start_x = curr_x
            pl_end_x = curr_x + plane_width - NODE_SPACING_X
            plane_spans[pl_id] = (pl_start_x, pl_end_x)

            place_row(spines, pl_start_x, pl_end_x, Y_BACKEND_SPINES)
            place_row(leaves, pl_start_x, pl_end_x, Y_BACKEND_LEAVES)

            curr_x += plane_width + PLANE_GAP

        backend_end_x = curr_x - PLANE_GAP if sorted_planes else 200.0

        # 2. Place GPU servers directly below the backend leaves
        # Spread them across the full width of the backend planes
        if gpu_servers:
            gpu_count = len(gpu_servers)
            gpu_span_width = max(backend_end_x - 200.0, gpu_count * NODE_SPACING_X)
            # If 16 or fewer GPUs, place in 1 wide row.
            # If more than 16 (e.g. 32), place in 2 clean staggered rows across the span
            if gpu_count <= 16:
                place_row(gpu_servers, 200.0, 200.0 + gpu_span_width, Y_GPU_SERVERS)
                gpu_max_x = 200.0 + gpu_span_width
                next_tier_y = Y_GPU_SERVERS + 1000
            else:
                half = (gpu_count + 1) // 2
                place_row(gpu_servers[:half], 200.0, 200.0 + gpu_span_width, Y_GPU_SERVERS)
                place_row(gpu_servers[half:], 200.0 + (NODE_SPACING_X / 2), 200.0 + gpu_span_width + (NODE_SPACING_X / 2), Y_GPU_SERVERS + 450)
                gpu_max_x = 200.0 + gpu_span_width + (NODE_SPACING_X / 2)
                next_tier_y = Y_GPU_SERVERS + 1200
        else:
            gpu_max_x = backend_end_x
            next_tier_y = Y_BACKEND_LEAVES + 1000

        top_max_x = max(backend_end_x, gpu_max_x)

        # =============================================================
        # ZONE 2: BOTTOM - FRONTEND & STORAGE (Below Compute Tier)
        # =============================================================
        Y_BOTTOM_TIER_1 = next_tier_y         # Leaves tier (Y ~ 3100)
        Y_BOTTOM_TIER_2 = next_tier_y + 800   # Spines & Storage Servers tier (Y ~ 3900)
        Y_BOTTOM_TIER_3 = next_tier_y + 1600  # SoftGates & CP Servers tier (Y ~ 4700)

        bottom_curr_x = 200.0

        # A. Frontend (North-South) Fabric
        softgates = cats["softgates"]
        ns_spines = cats["ns_spines"]
        ns_leaves = cats["ns_leaves"]
        cp_servers = cats["cp_servers"]

        if softgates or ns_spines or ns_leaves or cp_servers:
            fe_count = max(len(softgates), len(ns_spines), len(ns_leaves), len(cp_servers), 1)
            fe_width = max(fe_count * NODE_SPACING_X, 2200)
            fe_start_x = bottom_curr_x
            fe_end_x = bottom_curr_x + fe_width - NODE_SPACING_X

            # Frontend leaves connect to GPUs/servers, so placed at upper bottom tier
            place_row(ns_leaves, fe_start_x, fe_end_x, Y_BOTTOM_TIER_1)
            # Frontend spines
            place_row(ns_spines, fe_start_x, fe_end_x, Y_BOTTOM_TIER_2)
            # Border gateways / SoftGates at Y_BOTTOM_TIER_3
            if softgates:
                place_row(softgates, fe_start_x, fe_end_x, Y_BOTTOM_TIER_3)
            # Control Plane servers below SoftGates or alongside if no SoftGates
            if cp_servers:
                y_cp = Y_BOTTOM_TIER_3 + 500 if softgates else Y_BOTTOM_TIER_3
                place_row(cp_servers, fe_start_x, fe_end_x, y_cp)

            bottom_curr_x += fe_width + BOTTOM_POD_GAP

        # B. Storage Fabric
        storage_leaves = cats["storage_leaves"]
        storage_servers = cats["storage_servers"]

        if storage_leaves or storage_servers:
            st_count = max(len(storage_leaves), min(len(storage_servers), 4), 1)
            st_width = max(st_count * NODE_SPACING_X, 1600)
            st_start_x = bottom_curr_x
            st_end_x = bottom_curr_x + st_width - NODE_SPACING_X

            place_row(storage_leaves, st_start_x, st_end_x, Y_BOTTOM_TIER_1)
            place_grid(storage_servers, st_start_x, st_end_x, Y_BOTTOM_TIER_2, max_per_row=4, row_gap=400)

            bottom_curr_x += st_width + BOTTOM_POD_GAP

        # C. Any unclassified nodes
        if cats["other"]:
            place_grid(cats["other"], bottom_curr_x, bottom_curr_x + 1200, Y_BOTTOM_TIER_1, max_per_row=4, row_gap=400)
            bottom_curr_x += 1200 + BOTTOM_POD_GAP

        # =============================================================
        # ZONE 3: RIGHT SIDE - OUT-OF-BAND (OOB) MANAGEMENT RAIL
        # =============================================================
        oob_switches = cats["oob_switches"]
        if oob_switches:
            # Place OOB switches to the right of the entire canvas
            far_right_x = max(top_max_x, bottom_curr_x) + 900.0
            # Arrange in a clean vertical column with generous spacing
            oob_y_start = 400
            oob_y_gap = 500
            for i, (nid, _) in enumerate(oob_switches):
                positions[nid] = {"x": int(far_right_x), "y": int(oob_y_start + i * oob_y_gap)}

        return positions

    def apply_layout(self, site_id: int) -> Dict[str, Any]:
        """Fetch nodes for site_id, calculate positions, and save via Netris API."""
        if not self.client.authenticated:
            auth = self.client.authenticate()
            if not auth["success"]:
                return {"success": False, "message": f"Auth failed: {auth['message']}"}

        top = self.get_topology_data(site_id)
        nodes = top.get("nodes", {})
        if not nodes:
            return {"success": False, "message": f"No nodes found in topology for site {site_id}"}

        positions = self.calculate_coordinates(nodes)
        if not positions:
            return {"success": False, "message": "Failed to calculate positions"}

        payload = {
            "siteID": site_id,
            "positions": positions
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.client.controller_url}/api/v2/topology/positions",
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )

        try:
            with self.client.opener.open(req, timeout=20) as resp:
                body = resp.read().decode("utf-8")
                res = json.loads(body)
                is_success = res.get("isSuccess", False) or res.get("statusCode") == 200
                return {
                    "success": is_success,
                    "site_id": site_id,
                    "arranged_nodes": len(positions),
                    "message": f"Successfully arranged {len(positions)} nodes with 550px+ spacing across multi-plane pods.",
                    "details": res,
                }
        except Exception as e:
            return {"success": False, "message": str(e)}
