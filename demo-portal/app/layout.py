from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app import manager
from app.models import CategoryItem, DashboardLayout, ToolPlacement

logger = logging.getLogger("dashboard_layout")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "demo-portal" / "data"
LAYOUT_FILE = DATA_DIR / "dashboard_layout.json"

DEFAULT_CATEGORIES: List[Dict[str, Any]] = [
    {"id": "cat-control-plane", "name": "Cloud Control Plane", "order": 0, "collapsed": False},
    {"id": "cat-orchestration", "name": "Workload Orchestration", "order": 1, "collapsed": False},
    {"id": "cat-assurance", "name": "Fabric Assurance & Visibility", "order": 2, "collapsed": False},
    {"id": "cat-telemetry", "name": "Telemetry & Monitoring", "order": 3, "collapsed": False},
    {"id": "cat-workload", "name": "Tenant Workload", "order": 4, "collapsed": False},
    {"id": "cat-traffic", "name": "Traffic Simulation", "order": 5, "collapsed": False},
    {"id": "cat-ipam", "name": "IPAM & DCIM", "order": 6, "collapsed": False},
    {"id": "cat-other", "name": "Other", "order": 7, "collapsed": True},
]

TOOL_DEFAULT_CATEGORY_MAP: Dict[str, str] = {
    "fabric-builder-ui": "cat-control-plane",
    "provider-portal": "cat-control-plane",
    "netris-slurm-cluster-sim": "cat-other",
    "cli-inspector": "cat-assurance",
    "netris-prometheus-exporter": "cat-telemetry",
    "chatsim": "cat-other",
    "netbox-netris": "cat-ipam",
    "remote-tf-viewer": "cat-other",
}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug or "category"


def get_default_layout() -> DashboardLayout:
    """Generate default category structure and tool placements from TOOLS_METADATA."""
    categories = [CategoryItem(**c) for c in DEFAULT_CATEGORIES]
    cat_ids = {c.id for c in categories}

    tool_placements: Dict[str, ToolPlacement] = {}
    cat_counters: Dict[str, int] = {c.id: 0 for c in categories}

    for tool_id, meta in manager.TOOLS_METADATA.items():
        cat_id = TOOL_DEFAULT_CATEGORY_MAP.get(tool_id)
        if not cat_id or cat_id not in cat_ids:
            # Fallback by matching category name if available
            cat_name = meta.get("category", "General Tools")
            matching_cat = next((c for c in categories if c.name.lower() == cat_name.lower()), None)
            if matching_cat:
                cat_id = matching_cat.id
            else:
                new_cat_id = f"cat-{_slugify(cat_name)}"
                new_cat = CategoryItem(id=new_cat_id, name=cat_name, order=len(categories), collapsed=False)
                categories.append(new_cat)
                cat_ids.add(new_cat_id)
                cat_counters[new_cat_id] = 0
                cat_id = new_cat_id

        order = cat_counters.get(cat_id, 0)
        cat_counters[cat_id] = order + 1
        tool_placements[tool_id] = ToolPlacement(category_id=cat_id, order=order, hidden=manager.TOOLS_METADATA[tool_id].get("hidden", False))

    return DashboardLayout(categories=categories, tool_placements=tool_placements)


def load_layout() -> DashboardLayout:
    """Load the persisted layout or return reconciled defaults."""
    if not LAYOUT_FILE.exists():
        layout = get_default_layout()
        save_layout(layout)
        return layout

    try:
        with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        layout = DashboardLayout(**raw)
    except Exception as e:
        logger.warning(f"Failed to load layout from {LAYOUT_FILE} ({e}). Generating defaults.")
        layout = get_default_layout()
        save_layout(layout)
        return layout

    # Reconcile: Ensure all tools in TOOLS_METADATA exist in tool_placements
    cat_ids = {c.id for c in layout.categories}
    if not cat_ids:
        layout = get_default_layout()
        save_layout(layout)
        return layout

    modified = False

    # Check for missing tools
    for tool_id in manager.TOOLS_METADATA.keys():
        if tool_id not in layout.tool_placements:
            target_cat = TOOL_DEFAULT_CATEGORY_MAP.get(tool_id)
            if not target_cat or target_cat not in cat_ids:
                target_cat = layout.categories[0].id
            existing_in_cat = [p for p in layout.tool_placements.values() if p.category_id == target_cat]
            new_order = max([p.order for p in existing_in_cat], default=-1) + 1
            layout.tool_placements[tool_id] = ToolPlacement(category_id=target_cat, order=new_order, hidden=manager.TOOLS_METADATA[tool_id].get("hidden", False))
            modified = True

    # Check that each placed tool references a valid category
    first_cat_id = layout.categories[0].id
    for tool_id, placement in layout.tool_placements.items():
        if placement.category_id not in cat_ids:
            placement.category_id = first_cat_id
            modified = True

    if modified:
        save_layout(layout)

    return layout


def save_layout(layout: DashboardLayout) -> bool:
    """Save the dashboard layout to disk."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(LAYOUT_FILE, "w", encoding="utf-8") as f:
            f.write(layout.model_dump_json(indent=2))
        return True
    except Exception as e:
        logger.error(f"Error saving dashboard layout: {e}")
        return False


def reset_layout() -> DashboardLayout:
    """Reset layout to factory defaults and persist."""
    layout = get_default_layout()
    save_layout(layout)
    return layout


def create_category(name: str, order: Optional[int] = None) -> CategoryItem:
    """Create a new category and save layout."""
    layout = load_layout()
    base_id = f"cat-{_slugify(name)}"
    cat_id = base_id
    idx = 1
    existing_ids = {c.id for c in layout.categories}
    while cat_id in existing_ids:
        cat_id = f"{base_id}-{idx}"
        idx += 1

    if order is None:
        order = len(layout.categories)

    new_cat = CategoryItem(id=cat_id, name=name.strip(), order=order, collapsed=False)
    layout.categories.append(new_cat)
    # Re-normalize orders
    layout.categories.sort(key=lambda c: c.order)
    for i, c in enumerate(layout.categories):
        c.order = i

    save_layout(layout)
    return new_cat


def update_category(
    cat_id: str,
    name: Optional[str] = None,
    order: Optional[int] = None,
    collapsed: Optional[bool] = None
) -> Optional[CategoryItem]:
    """Update properties of an existing category."""
    layout = load_layout()
    target = next((c for c in layout.categories if c.id == cat_id), None)
    if not target:
        return None

    if name is not None and name.strip():
        target.name = name.strip()
    if collapsed is not None:
        target.collapsed = collapsed
    if order is not None:
        target.order = order
        layout.categories.sort(key=lambda c: c.order)
        for i, c in enumerate(layout.categories):
            c.order = i

    save_layout(layout)
    return target


def delete_category(cat_id: str) -> bool:
    """Delete a category. Orphaned tools are moved to the first remaining category."""
    layout = load_layout()
    target = next((c for c in layout.categories if c.id == cat_id), None)
    if not target:
        return False

    if len(layout.categories) <= 1:
        # Cannot delete the only remaining category
        return False

    layout.categories = [c for c in layout.categories if c.id != cat_id]
    fallback_cat_id = layout.categories[0].id

    # Re-assign any tools in this category to fallback
    for tool_id, placement in layout.tool_placements.items():
        if placement.category_id == cat_id:
            placement.category_id = fallback_cat_id

    # Re-normalize orders
    layout.categories.sort(key=lambda c: c.order)
    for i, c in enumerate(layout.categories):
        c.order = i

    save_layout(layout)
    return True
