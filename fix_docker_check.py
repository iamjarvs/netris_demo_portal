import re
from pathlib import Path

manager_path = Path("demo-portal/app/manager.py")
content = manager_path.read_text()

old_deps = """def check_dependencies(tool_type: str, has_git_url: bool) -> tuple[bool, str]:
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
    return True, \"\""""

new_deps = """def check_dependencies(tool_type: str, has_git_url: bool) -> tuple[bool, str]:
    missing = []
    import shutil, subprocess
    if has_git_url:
        if not shutil.which("git"):
            missing.append("git")
    
    if tool_type == "docker":
        docker_path = shutil.which("docker")
        if not docker_path:
            missing.append("docker")
        else:
            # Try both docker compose and docker-compose
            try:
                res = subprocess.run([docker_path, "compose", "version"], capture_output=True, text=True)
                if res.returncode != 0:
                    res2 = subprocess.run(["docker-compose", "version"], capture_output=True, text=True)
                    if res2.returncode != 0:
                        missing.append("docker compose")
            except Exception:
                try:
                    res2 = subprocess.run(["docker-compose", "version"], capture_output=True, text=True)
                    if res2.returncode != 0:
                        missing.append("docker compose")
                except:
                    missing.append("docker compose")
                    
    if missing:
        return False, f"Missing system dependencies: {', '.join(missing)}. Please install them and try again."
    return True, \"\""""

content = content.replace(old_deps, new_deps)
manager_path.write_text(content)
print("Docker check fixed")
