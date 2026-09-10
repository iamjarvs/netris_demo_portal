from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    id: str
    name: str
    category: str
    description: str
    tool_type: str = Field(..., description="'subprocess', 'docker', or 'remote'")
    port: Optional[int] = None
    popout_url: Optional[str] = None
    health_endpoint: Optional[str] = None
    status: str = Field("stopped", description="'running', 'stopped', 'starting', 'error'")
    is_running: bool = False
    pid: Optional[int] = None
    uptime: Optional[str] = None
    summary_command: str


class GlobalConfig(BaseModel):
    netris_url: str = "https://adam-ctl.netris.io"
    netris_username: str = "netris"
    netris_password: str = ""
    netris_verify_ssl: bool = False
    default_tenant: str = "Demo"
    default_site: str = "SantaClara"


class ToolConfigUpdate(BaseModel):
    env_vars: Dict[str, str] = Field(default_factory=dict)
    raw_content: Optional[str] = None


class ActionResponse(BaseModel):
    success: bool
    message: str
    tool_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class LogResponse(BaseModel):
    tool_id: str
    lines: List[str]
    total_lines: int
