import re
from pathlib import Path

js_path = Path("demo-portal/static/app.js")
content = js_path.read_text()

# 1. Add min-h-[75vh] to ToolDetailView root div
old_root = '<div className="flex flex-col h-full bg-white rounded-xl shadow-theme-sm border border-gray-200 overflow-hidden">'
new_root = '<div className="flex flex-col h-full min-h-[75vh] bg-white rounded-xl shadow-theme-sm border border-gray-200 overflow-hidden">'
content = content.replace(old_root, new_root)

# 2. Add openSessionModal prop to ToolDetailViewContent
old_props = ' tool, onStart, onStop, onRestart, fetchLogs, configCatalog, fetchConfigFile, saveConfigFile, openTerminal, actionLoading }) {'
new_props = ' tool, onStart, onStop, onRestart, fetchLogs, configCatalog, fetchConfigFile, saveConfigFile, openTerminal, actionLoading, openSessionModal }) {'
content = content.replace(old_props, new_props)

# 3. Use openSessionModal if tool.session_options exists
old_start_btn = """          ) : (
            <button onClick={() => onStart(tool.id)} disabled={actionLoading[tool.id]} className="px-4 py-2 bg-coral-600 text-white rounded-lg text-sm font-semibold hover:bg-coral-700 shadow-theme-xs">
              {actionLoading[tool.id] ? 'Starting...' : isInstalling ? 'Install & Start' : 'Start'}
            </button>
          )}"""

new_start_btn = """          ) : (
            <button 
              onClick={() => {
                if (!isInstalling && tool.session_options) {
                  openSessionModal(tool);
                } else {
                  onStart(tool.id);
                }
              }} 
              disabled={actionLoading[tool.id]} 
              className="px-4 py-2 bg-coral-600 text-white rounded-lg text-sm font-semibold hover:bg-coral-700 shadow-theme-xs"
            >
              {actionLoading[tool.id] ? 'Starting...' : isInstalling ? 'Install & Start' : tool.session_options ? 'Configure & Start' : 'Start'}
            </button>
          )}"""
content = content.replace(old_start_btn, new_start_btn)

# 4. Pass openSessionModal from App
old_tool_detail_usage = """              fetchConfigFile={fetchConfigFile}
              saveConfigFile={saveConfigFile}
              openTerminal={t => setTerminalModalTool(t)}
              actionLoading={actionLoading}
            />"""

new_tool_detail_usage = """              fetchConfigFile={fetchConfigFile}
              saveConfigFile={saveConfigFile}
              openTerminal={t => setTerminalModalTool(t)}
              actionLoading={actionLoading}
              openSessionModal={openSessionModal}
            />"""
content = content.replace(old_tool_detail_usage, new_tool_detail_usage)

js_path.write_text(content)
print("Tool Detail fixed")
