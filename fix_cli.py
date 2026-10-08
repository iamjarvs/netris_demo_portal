from pathlib import Path

start_sh = Path("demo-portal/managed-tools/cli-inspector/start.sh")
content = start_sh.read_text()
old_check = """if [ ! -f config.json ]; then
  echo "No config.json found. Copy config.example.json to config.json."
  exit 1
fi"""

new_check = """if [ ! -f config.json ]; then
  echo "No config.json found. Copying config.example.json to config.json."
  cp config.example.json config.json
fi"""
content = content.replace(old_check, new_check)
start_sh.write_text(content)
print("done")
