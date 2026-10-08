import re
from pathlib import Path

manager_path = Path("demo-portal/app/manager.py")
content = manager_path.read_text()

# Fix netbox-netris
content = content.replace(
    '"start_script": ["docker", "compose", "up", "-d"],',
    '"start_script": ["./start.sh"],'
)
content = content.replace(
    '"stop_script": ["docker", "compose", "down"],',
    '"stop_script": ["./stop.sh"],'
)

# Fix cli-inspector
content = content.replace(
    '"start_script": ["./start_web.sh"],',
    '"start_script": ["./start.sh"],'
)

# Fix gpu-ai-fabric-traffic-sim
content = content.replace(
    '"summary_command": "docker compose up -d",',
    '"summary_command": "./start.sh",'
)

manager_path.write_text(content)
print("done")
