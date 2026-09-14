from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    id: str
    name: str
    category: str
    description: str
    tool_type: str = Field(..., description="'subprocess', 'docker', 'remote', or 'interactive'")
    port: Optional[int] = None
    popout_url: Optional[str] = None
    health_endpoint: Optional[str] = None
    status: str = Field("stopped", description="'running', 'stopped', 'starting', 'error'")
    is_running: bool = False
    pid: Optional[int] = None
    uptime: Optional[str] = None
    summary_command: str
    credentials: List[Dict[str, Any]] = Field(default_factory=list)
    session_options: Optional[Dict[str, Any]] = None


class StartToolRequest(BaseModel):
    custom_args: Optional[List[str]] = None
    session_params: Optional[Dict[str, Any]] = None


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


class ConfigFileItem(BaseModel):
    id: str
    name: str
    path: str
    format: str
    description: Optional[str] = None


class ToolConfigCatalog(BaseModel):
    tool_id: str
    tool_name: str
    files: List[ConfigFileItem]


class FileContentResponse(BaseModel):
    tool_id: str
    file_id: str
    name: str
    path: str
    format: str
    content: str


class FileContentUpdate(BaseModel):
    tool_id: str
    file_id: str
    content: str


class ActionResponse(BaseModel):
    success: bool
    message: str
    tool_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class LogResponse(BaseModel):
    tool_id: str
    lines: List[str]
    total_lines: int


class RecordRequest(BaseModel):
    duration: int = Field(300, ge=10, le=7200, description="Recording duration in seconds")
    interval: int = Field(15, ge=1, le=120, description="Frame interval in seconds")
    output_file: Optional[str] = None


class RecordStatusResponse(BaseModel):
    is_recording: bool
    status: str
    start_time: Optional[float] = None
    elapsed_seconds: float = 0.0
    duration: int = 0
    interval: int = 15
    frames_captured: int = 0
    progress_pct: float = 0.0
    output_file: str = ""
    file_size_mb: float = 0.0
    error: Optional[str] = None
    message: Optional[str] = None
