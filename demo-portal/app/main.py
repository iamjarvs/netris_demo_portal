from __future__ import annotations

import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import manager
from app.routes.config import router as config_router
from app.routes.layout import router as layout_router
from app.routes.tools import router as tools_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("demo_portal")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="Proof of Concept Evaluations",
    description="Centralized process management, health monitoring, and configuration portal for demo tools.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_control_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.post("/api/system/update")
async def update_portal():
    import subprocess
    from fastapi import HTTPException
    from app.manager import REPO_ROOT
    try:
        res = subprocess.run(["git", "pull", "--rebase"], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
        return {"success": True, "message": "Demo portal updated: " + res.stdout.strip()}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Git pull failed: {e.stderr or e.output}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")

app.include_router(tools_router)
app.include_router(config_router)
app.include_router(layout_router)

# Mount static folder for assets (JS, CSS, SVGs)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
@app.head("/", include_in_schema=False)
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Proof of Concept Evaluations API is running. Build the frontend or check /docs."}


@app.get("/healthz")
@app.head("/healthz")
def health_check():
    return {"status": "ok", "service": "demo-control-portal"}


@app.on_event("shutdown")
def on_shutdown():
    logger.info("Demo Control Portal shutting down. Cleaning up processes...")
    tools = manager.get_all_tools()
    for t in tools:
        if t.tool_type == "subprocess" and t.is_running:
            manager.stop_tool(t.id)
