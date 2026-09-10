from __future__ import annotations

from typing import Dict
from fastapi import APIRouter, HTTPException

from app import config_sync
from app.models import ActionResponse, GlobalConfig, ToolConfigUpdate

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/global", response_model=GlobalConfig)
def get_global_configuration():
    """Retrieve shared Netris credentials and cluster defaults."""
    return config_sync.load_global_config()


@router.post("/global", response_model=ActionResponse)
def update_global_configuration(cfg: GlobalConfig):
    """Save global config and propagate into all underlying demo tools."""
    results = config_sync.sync_global_to_all_tools(cfg)
    synced_tools = [k for k, v in results.items() if v]
    return ActionResponse(
        success=True,
        message=f"Global configuration saved and propagated to {len(synced_tools)} tools: {', '.join(synced_tools)}.",
        data={"results": results}
    )


@router.get("/tool/{tool_id}")
def get_tool_configuration(tool_id: str):
    """Retrieve the raw configuration file for an individual tool."""
    content = config_sync.get_tool_config_text(tool_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"No config file found for tool '{tool_id}'.")
    return {"tool_id": tool_id, "content": content}


@router.post("/tool/{tool_id}", response_model=ActionResponse)
def update_tool_configuration(tool_id: str, payload: ToolConfigUpdate):
    """Update the raw configuration file for an individual tool."""
    if not payload.raw_content:
        raise HTTPException(status_code=400, detail="Missing raw_content in request payload.")

    ok = config_sync.save_tool_config_text(tool_id, payload.raw_content)
    if not ok:
        raise HTTPException(status_code=500, detail=f"Failed to write configuration file for '{tool_id}'.")

    return ActionResponse(
        success=True,
        message=f"Updated configuration for '{tool_id}' successfully.",
        tool_id=tool_id
    )
