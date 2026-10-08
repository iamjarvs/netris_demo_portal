import re
from pathlib import Path

js_path = Path("demo-portal/static/app.js")
content = js_path.read_text()

# Find the header buttons div
start_marker = '          <div className="flex items-center gap-3">\n            {/* Quick Scenario Buttons */}'
end_marker = '            </button>\n          </div>'

idx1 = content.find(start_marker)
if idx1 != -1:
    idx2 = content.find(end_marker, idx1) + len(end_marker)
    original_block = content[idx1:idx2]
    
    new_block = "          {(activeTab === 'global-config' || activeTab === 'overview') && (\n" + original_block + "\n          )}"
    content = content.replace(original_block, new_block)
    js_path.write_text(content)
    print("global actions fixed")
else:
    print("could not find marker")
