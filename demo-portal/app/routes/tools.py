import asyncio
import fcntl
import json
import os
import pty
import signal
import struct
import subprocess
import termios
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app import manager
from app.models import (
    ActionResponse,
    LogResponse,
    RecordRequest,
    RecordStatusResponse,
    StartToolRequest,
    ToolInfo,
)

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("", response_model=List[ToolInfo])
def list_tools():
    """List all demo tools and their live statuses."""
    return manager.get_all_tools()


@router.post("/{tool_id}/start", response_model=ActionResponse)
def start_tool(tool_id: str, request: Optional[StartToolRequest] = None):
    """Start a specific demo tool, optionally passing session parameters or custom CLI args."""
    custom_args = request.custom_args if request else None
    session_params = request.session_params if request else None
    success, msg = manager.start_tool(tool_id, custom_args=custom_args, session_params=session_params)
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


@router.post("/{tool_id}/launch-native", response_model=ActionResponse)
def launch_native_terminal(tool_id: str):
    """Launch the tool in a native iTerm (or Terminal.app) window."""
    success, msg = manager.launch_native_terminal(tool_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return ActionResponse(success=True, message=msg, tool_id=tool_id)


@router.websocket("/{tool_id}/terminal/ws")
async def terminal_websocket(websocket: WebSocket, tool_id: str):
    """Bidirectional interactive pseudo-terminal session streamed over WebSocket."""
    await websocket.accept()
    meta = manager.TOOLS_METADATA.get(tool_id)
    if not meta:
        await websocket.send_text(f"\r\n\x1b[31mError: Tool '{tool_id}' not found.\x1b[0m\r\n")
        await websocket.close()
        return

    cwd = str(meta["cwd"])
    cmd = meta.get("default_args", ["./run.sh"])

    master_fd, slave_fd = pty.openpty()

    try:
        winsize = struct.pack("HHHH", 24, 80, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
    except Exception:
        pass

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid,
        env=env,
        close_fds=True,
    )
    os.close(slave_fd)

    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    async def read_from_pty():
        try:
            while proc.poll() is None:
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        await websocket.send_bytes(data)
                    else:
                        break
                except (BlockingIOError, InterruptedError):
                    await asyncio.sleep(0.02)
                except Exception:
                    break
        except Exception:
            pass

    async def write_to_pty():
        try:
            while proc.poll() is None:
                msg = await websocket.receive()
                if "text" in msg:
                    text_data = msg["text"]
                    if text_data.startswith("{") and "resize" in text_data:
                        try:
                            payload = json.loads(text_data)
                            if payload.get("type") == "resize":
                                cols = int(payload.get("cols", 80))
                                rows = int(payload.get("rows", 24))
                                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                                continue
                        except Exception:
                            pass
                    os.write(master_fd, text_data.encode("utf-8"))
                elif "bytes" in msg:
                    os.write(master_fd, msg["bytes"])
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception:
            pass

    reader_task = asyncio.create_task(read_from_pty())
    writer_task = asyncio.create_task(write_to_pty())

    await asyncio.wait([reader_task, writer_task], return_when=asyncio.FIRST_COMPLETED)

    for task in (reader_task, writer_task):
        task.cancel()

    if proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass

    try:
        os.close(master_fd)
    except Exception:
        pass

    try:
        await websocket.close()
    except Exception:
        pass


# --- Telemetry Recording Endpoints ---

@router.post("/netris-prometheus-exporter/record", response_model=ActionResponse)
def start_telemetry_recording(req: RecordRequest):
    """Trigger background telemetry recording from Netris Controller for offline looping."""
    success, msg = manager.start_telemetry_recording(duration=req.duration, interval=req.interval)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return ActionResponse(success=True, message=msg, tool_id="netris-prometheus-exporter")


@router.get("/netris-prometheus-exporter/record/status", response_model=RecordStatusResponse)
def get_telemetry_recording_status():
    """Check live status of the background telemetry recording."""
    status = manager.get_telemetry_recording_status()
    return RecordStatusResponse(**status)


@router.post("/netris-prometheus-exporter/record/stop", response_model=ActionResponse)
def stop_telemetry_recording():
    """Halt an active telemetry recording session early."""
    success, msg = manager.stop_telemetry_recording()
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return ActionResponse(success=True, message=msg, tool_id="netris-prometheus-exporter")

