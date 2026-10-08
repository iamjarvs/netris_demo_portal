import re
from pathlib import Path

app = Path("demo-portal/static/app.js")
content = app.read_text()

old_props = "openSessionModal }) {"
new_props = "openSessionModal, handleUpdateTool }) {"
content = content.replace(old_props, new_props)

old_buttons = """              <button onClick={() => onRestart(tool.id)} disabled={actionLoading[tool.id]} className="p-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-semibold hover:bg-gray-200" title="Restart">
                <Icons.RefreshCw className={`w-4 h-4 ${actionLoading[tool.id] ? 'animate-spin' : ''}`} />
              </button>
            </>
          ) : ("""

new_buttons = """              <button onClick={() => onRestart(tool.id)} disabled={actionLoading[tool.id]} className="p-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-semibold hover:bg-gray-200" title="Restart">
                <Icons.RefreshCw className={`w-4 h-4 ${actionLoading[tool.id] ? 'animate-spin' : ''}`} />
              </button>
            </>
          ) : (
            <>
            {tool.is_downloaded && (
              <button 
                onClick={() => handleUpdateTool(tool.id)} 
                disabled={actionLoading[tool.id]} 
                className="px-4 py-2 bg-blue-50 text-blue-700 border border-blue-200 rounded-lg text-sm font-semibold hover:bg-blue-100 shadow-theme-xs flex items-center gap-2"
              >
                <Icons.RefreshCw className={`w-3.5 h-3.5 ${actionLoading[tool.id] ? 'animate-spin' : ''}`} />
                Update Extension
              </button>
            )}
            """
content = content.replace(old_buttons, new_buttons)

old_render = """              actionLoading={actionLoading}
              openSessionModal={openSessionModal}
            />"""

new_render = """              actionLoading={actionLoading}
              openSessionModal={openSessionModal}
              handleUpdateTool={async (id) => {
                setActionLoading(prev => ({ ...prev, [id]: true }));
                try {
                  const res = await fetch(`/api/tools/${id}/update`, { method: 'POST' });
                  const data = await res.json();
                  if (!res.ok) throw new Error(data.detail || data.message || "Update failed");
                  notify(data.message || "Tool updated successfully!");
                } catch (e) {
                  notify("Update failed: " + e.message, 'error');
                } finally {
                  setActionLoading(prev => ({ ...prev, [id]: false }));
                }
              }}
            />"""
content = content.replace(old_render, new_render)

app.write_text(content)
print("app updated")
