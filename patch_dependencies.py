import re
from pathlib import Path

manager_path = Path("demo-portal/app/manager.py")
content = manager_path.read_text()

deps_func = """import shutil

def check_dependencies(tool_type: str, has_git_url: bool) -> tuple[bool, str]:
    missing = []
    if has_git_url:
        if not shutil.which("git"):
            missing.append("git")
    
    if tool_type == "docker":
        if not shutil.which("docker"):
            missing.append("docker")
        else:
            # Check docker compose
            import subprocess
            try:
                res = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
                if res.returncode != 0:
                    missing.append("docker compose (V2)")
            except Exception:
                missing.append("docker compose (V2)")
                
    if missing:
        return False, f"Missing system dependencies: {', '.join(missing)}. Please install them and try again."
    return True, ""

"""

# Insert it before start_tool
start_tool_idx = content.find("def start_tool(")
content = content[:start_tool_idx] + deps_func + content[start_tool_idx:]

# Update start_tool to call check_dependencies
old_start = """    _append_log(tool_id, f"Initiating start sequence for {meta['name']}...")
    
    # --- Dynamic Git Cloning Logic ---"""

new_start = """    _append_log(tool_id, f"Initiating start sequence for {meta['name']}...")
    
    has_git = bool(meta.get("tool_type") == "git" or "url" in meta)
    deps_ok, deps_msg = check_dependencies(meta["tool_type"], has_git)
    if not deps_ok:
        _append_log(tool_id, deps_msg)
        return False, deps_msg
    
    # --- Dynamic Git Cloning Logic ---"""

content = content.replace(old_start, new_start)
manager_path.write_text(content)
print("done")
