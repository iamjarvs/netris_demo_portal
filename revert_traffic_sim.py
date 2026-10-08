import re
from pathlib import Path

manager = Path("demo-portal/app/manager.py")
content = manager.read_text()

old_block = """    "gpu-ai-fabric-traffic-sim": {
        "id": "gpu-ai-fabric-traffic-sim",
        "name": "GPU AI Fabric Traffic Simulator",
        "category": "Traffic Simulation",
        "description": "Containerized multi-rail RoCEv2 iPerf3 collective traffic generator (Ring-AllReduce, MoE All-to-All, Incast) across mock GPU nodes.",
        "tool_type": "docker",
        "port": None,
        "popout_url": None,
        "health_endpoint": None,
        "start_script": ["./start.sh"],
        "stop_script": ["./stop.sh"],"""

new_block = """    "gpu-ai-fabric-traffic-sim": {
        "id": "gpu-ai-fabric-traffic-sim",
        "name": "GPU AI Fabric Traffic Simulator",
        "category": "Traffic Simulation",
        "description": "Containerized multi-rail RoCEv2 iPerf3 collective traffic generator (Ring-AllReduce, MoE All-to-All, Incast) across mock GPU nodes.",
        "tool_type": "docker",
        "port": None,
        "popout_url": None,
        "health_endpoint": None,
        "start_script": ["docker", "compose", "up", "-d"],
        "stop_script": ["docker", "compose", "down"],"""

content = content.replace(old_block, new_block)
manager.write_text(content)
print("reverted")
