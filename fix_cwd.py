import re
from pathlib import Path

manager_path = Path("demo-portal/app/manager.py")
content = manager_path.read_text()

old_check = """    cwd = meta["cwd"]
    if not cwd.exists():
        return False, f"Directory '{cwd}' does not exist."

    
    _append_log(tool_id, f"Initiating start sequence for {meta['name']}...")"""

new_check = """    cwd = meta["cwd"]
    has_git = bool(meta.get("tool_type") == "git" or "url" in meta)
    
    if not cwd.exists() and not has_git:
        return False, f"Directory '{cwd}' does not exist."

    _append_log(tool_id, f"Initiating start sequence for {meta['name']}...")"""

content = content.replace(old_check, new_check)
manager_path.write_text(content)
print("done")
