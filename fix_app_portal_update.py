import re
from pathlib import Path

app = Path("demo-portal/static/app.js")
content = app.read_text()

old_global_buttons = """              <button onClick={() => alert("Global configuration saved! (Simulation only in this demo)")} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 shadow-theme-xs">
                Save Global Configuration
              </button>
            </div>
          </div>"""

new_global_buttons = """              <button 
                onClick={async () => {
                  try {
                    const res = await fetch('/api/system/update', { method: 'POST' });
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || data.message || "Update failed");
                    notify(data.message || "Portal updated successfully! You may need to restart the backend.");
                  } catch (e) {
                    notify("Update failed: " + e.message, 'error');
                  }
                }} 
                className="px-4 py-2 bg-gray-100 text-gray-700 border border-gray-300 rounded-lg text-sm font-semibold hover:bg-gray-200 shadow-theme-xs flex items-center gap-2"
              >
                <Icons.RefreshCw className="w-3.5 h-3.5" />
                Update Demo Portal
              </button>
              <button onClick={() => alert("Global configuration saved! (Simulation only in this demo)")} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 shadow-theme-xs">
                Save Global Configuration
              </button>
            </div>
          </div>"""

content = content.replace(old_global_buttons, new_global_buttons)
app.write_text(content)
print("app global update button added")
