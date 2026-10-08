import re
from pathlib import Path

manager = Path("demo-portal/app/manager.py")
manager_content = manager.read_text()

update_logic = """def update_tool(tool_id: str) -> dict:
    meta = TOOLS_METADATA.get(tool_id)
    if not meta:
        raise ValueError(f"Tool {tool_id} not found")
        
    cwd = Path(meta["cwd"])
    if not cwd.exists():
        raise ValueError(f"Tool {tool_id} is not downloaded. Cannot update.")
        
    import subprocess
    if (cwd / ".git").exists():
        try:
            # Stash any local changes first
            subprocess.run(["git", "stash"], cwd=cwd, check=True, capture_output=True)
            res = subprocess.run(["git", "pull", "--rebase"], cwd=cwd, check=True, capture_output=True, text=True)
            return {"success": True, "message": f"Tool {tool_id} updated successfully: " + res.stdout.strip()}
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Git pull failed: {e.stderr or e.output}")
    else:
        raise ValueError("Not a git repository, cannot auto-update.")

def start_tool(tool_id: str, session_params: dict = None) -> dict:"""

manager_content = manager_content.replace("def start_tool(tool_id: str, session_params: dict = None) -> dict:", update_logic)
manager.write_text(manager_content)
print("manager updated")

main = Path("demo-portal/app/main.py")
main_content = main.read_text()

api_logic = """@app.post("/api/tools/{tool_id}/update")
async def update_tool_endpoint(tool_id: str):
    try:
        return manager.update_tool(tool_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")

@app.post("/api/tools/{tool_id}/start")"""

main_content = main_content.replace('@app.post("/api/tools/{tool_id}/start")', api_logic)
main.write_text(main_content)
print("main updated")
