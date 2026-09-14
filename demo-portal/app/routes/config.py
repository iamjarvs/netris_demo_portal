from __future__ import annotations

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from app import config_sync
from app.models import (
    ActionResponse,
    FileContentResponse,
    FileContentUpdate,
    GlobalConfig,
    ToolConfigCatalog,
    ToolConfigUpdate,
)

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


@router.get("/catalog", response_model=List[ToolConfigCatalog])
def get_configuration_catalog():
    """Retrieve all tools and their respective editable configuration files."""
    return config_sync.get_tool_config_catalog()


@router.get("/file", response_model=FileContentResponse)
def get_file_content_endpoint(
    tool_id: str = Query(..., description="ID of the tool"),
    file_id: Optional[str] = Query(None, description="ID or filename of configuration file")
):
    """Retrieve content and metadata for a specific configuration file."""
    data = config_sync.get_file_content(tool_id, file_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Configuration file not found for tool '{tool_id}'.")
    return FileContentResponse(**data)


@router.post("/file", response_model=ActionResponse)
def save_file_content_endpoint(payload: FileContentUpdate):
    """Save raw content to a specific configuration file on disk."""
    ok, msg = config_sync.save_file_content(payload.tool_id, payload.file_id, payload.content)
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return ActionResponse(success=True, message=msg, tool_id=payload.tool_id)


@router.get("/tool/{tool_id}")
def get_tool_configuration(tool_id: str, file: Optional[str] = Query(None)):
    """Retrieve the raw configuration file for an individual tool."""
    content = config_sync.get_tool_config_text(tool_id, file_id=file)
    if content is None:
        raise HTTPException(status_code=404, detail=f"No config file found for tool '{tool_id}'.")
    return {"tool_id": tool_id, "content": content}


@router.post("/tool/{tool_id}", response_model=ActionResponse)
def update_tool_configuration(tool_id: str, payload: ToolConfigUpdate, file: Optional[str] = Query(None)):
    """Update the raw configuration file for an individual tool."""
    if not payload.raw_content:
        raise HTTPException(status_code=400, detail="Missing raw_content in request payload.")

    ok = config_sync.save_tool_config_text(tool_id, payload.raw_content, file_id=file)
    if not ok:
        raise HTTPException(status_code=500, detail=f"Failed to write configuration file for '{tool_id}'.")

    return ActionResponse(
        success=True,
        message=f"Updated configuration for '{tool_id}' successfully.",
        tool_id=tool_id
    )
