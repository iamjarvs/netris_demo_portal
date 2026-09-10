from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app import manager
from app.models import ActionResponse, LogResponse, ToolInfo

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("", response_model=List[ToolInfo])
def list_tools():
    """List all demo tools and their live statuses."""
    return manager.get_all_tools()


@router.post("/{tool_id}/start", response_model=ActionResponse)
def start_tool(tool_id: str):
    """Start a specific demo tool."""
    success, msg = manager.start_tool(tool_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return ActionResponse(success=True, message=msg, tool_id=tool_id)


@router.post("/{tool_id}/stop", response_model=ActionResponse)
def stop_tool(tool_id: str):
    """Stop a specific demo tool."""
    success, msg = manager.stop_tool(tool_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return ActionResponse(success=True, message=msg, tool_id=tool_id)


@router.post("/{tool_id}/restart", response_model=ActionResponse)
def restart_tool(tool_id: str):
    """Restart a specific demo tool."""
    success, msg = manager.restart_tool(tool_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return ActionResponse(success=True, message=msg, tool_id=tool_id)


@router.get("/{tool_id}/logs", response_model=LogResponse)
def get_tool_logs(tool_id: str, limit: int = Query(default=100, ge=1, le=1000)):
    """Retrieve in-memory logs for a tool."""
    lines = manager.get_logs(tool_id, limit=limit)
    return LogResponse(tool_id=tool_id, lines=lines, total_lines=len(lines))


@router.post("/scenarios/{scenario_id}", response_model=ActionResponse)
def run_scenario(scenario_id: str):
    """Execute pre-defined demo scenarios."""
    if scenario_id == "start_ai_fabric":
        # Launch Slurm Sim & Prometheus/Grafana in sequence
        manager.start_tool("netris-slurm-cluster-sim")
        manager.start_tool("netris-prometheus-exporter")
        return ActionResponse(
            success=True,
            message="Started Slurm Orchestrator and Prometheus Observability Stack."
        )
    elif scenario_id == "stop_all":
        tools = manager.get_all_tools()
        for t in tools:
            manager.stop_tool(t.id)
        return ActionResponse(
            success=True,
            message="Stopped all active demo tools and background containers."
        )
    else:
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{scenario_id}'.")
