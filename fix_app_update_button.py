import re
from pathlib import Path

app = Path("demo-portal/static/app.js")
content = app.read_text()

old_block = """          {tool.status === 'running' ? (
            <>
              <button onClick={() => onRestart(tool.id)} disabled={actionLoading[tool.id]} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-semibold hover:bg-gray-50">
                Restart
              </button>
              <button onClick={() => onStop(tool.id)} disabled={actionLoading[tool.id]} className="px-4 py-2 bg-white border border-red-200 text-error-600 rounded-lg text-sm font-semibold hover:bg-red-50">
                Stop
              </button>
            </>
          ) : ("""

new_block = """          {(tool.is_optional && tool.is_downloaded) && (
            <button 
              onClick={() => handleUpdateTool(tool.id)} 
              disabled={actionLoading[tool.id]} 
              className="px-4 py-2 bg-blue-50 text-blue-700 border border-blue-200 rounded-lg text-sm font-semibold hover:bg-blue-100 shadow-theme-xs flex items-center gap-2"
            >
              <Icons.RefreshCw className={`w-3.5 h-3.5 ${actionLoading[tool.id] ? 'animate-spin' : ''}`} />
              Update Extension
            </button>
          )}
          {tool.status === 'running' ? (
            <>
              <button onClick={() => onRestart(tool.id)} disabled={actionLoading[tool.id]} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-semibold hover:bg-gray-50">
                Restart
              </button>
              <button onClick={() => onStop(tool.id)} disabled={actionLoading[tool.id]} className="px-4 py-2 bg-white border border-red-200 text-error-600 rounded-lg text-sm font-semibold hover:bg-red-50">
                Stop
              </button>
            </>
          ) : ("""

if old_block in content:
    content = content.replace(old_block, new_block)
    app.write_text(content)
    print("app updated")
else:
    print("could not find block")
