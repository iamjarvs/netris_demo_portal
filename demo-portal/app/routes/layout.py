from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException

from app import layout as layout_svc
from app.models import (
    ActionResponse,
    CategoryItem,
    CreateCategoryRequest,
    DashboardLayout,
    UpdateCategoryRequest,
)

router = APIRouter(prefix="/api/layout", tags=["layout"])


@router.get("", response_model=DashboardLayout)
def get_dashboard_layout():
    """Retrieve current dashboard layout, categories, and tool placements."""
    return layout_svc.load_layout()


@router.post("", response_model=ActionResponse)
def save_dashboard_layout(payload: DashboardLayout):
    """Save updated dashboard layout with custom categories and tool ordering."""
    ok = layout_svc.save_layout(payload)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save dashboard layout configuration.")
    return ActionResponse(success=True, message="Dashboard layout saved successfully.")


@router.post("/reset", response_model=DashboardLayout)
def reset_dashboard_layout():
    """Reset the dashboard layout to factory default Netris demo categories and tool order."""
    return layout_svc.reset_layout()


@router.post("/categories", response_model=CategoryItem)
def create_category(payload: CreateCategoryRequest):
    """Create a new custom category."""
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Category name cannot be empty.")
    return layout_svc.create_category(payload.name, payload.order)


@router.put("/categories/{cat_id}", response_model=CategoryItem)
def update_category(cat_id: str, payload: UpdateCategoryRequest):
    """Update a category's name, order, or collapse status."""
    cat = layout_svc.update_category(
        cat_id,
        name=payload.name,
        order=payload.order,
        collapsed=payload.collapsed
    )
    if not cat:
        raise HTTPException(status_code=404, detail=f"Category '{cat_id}' not found.")
    return cat


@router.delete("/categories/{cat_id}", response_model=ActionResponse)
def delete_category(cat_id: str):
    """Delete a category. Any contained tools are moved to the primary category."""
    ok = layout_svc.delete_category(cat_id)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category '{cat_id}'. Ensure it exists and is not the last remaining category."
        )
    return ActionResponse(success=True, message=f"Category '{cat_id}' deleted successfully.")
