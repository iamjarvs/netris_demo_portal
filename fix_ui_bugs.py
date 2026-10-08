import re
from pathlib import Path

js_path = Path("demo-portal/static/app.js")
content = js_path.read_text()

# --- BUG 1: logs.map is not a function ---
content = content.replace(
    "fetchLogs(tool.id).then(setLogs).catch(console.error);",
    "fetchLogs(tool.id).then(res => setLogs(res.lines || [])).catch(console.error);"
)

# --- BUG 2: Add ErrorBoundary ---
error_boundary = """
class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center text-red-600 bg-red-50 rounded-xl border border-red-200 m-8">
          <h2 className="text-xl font-bold mb-2">Something went wrong.</h2>
          <pre className="text-sm font-mono overflow-auto text-left p-4 bg-red-100 rounded">{this.state.error.toString()}</pre>
          <button onClick={() => this.setState({hasError: false})} className="mt-4 px-4 py-2 bg-white border border-red-200 rounded shadow-sm text-gray-700">Try Again</button>
        </div>
      );
    }
    return this.props.children;
  }
}

// --- App Root Component ---
"""
content = content.replace("// --- App Root Component ---", error_boundary)
content = content.replace("function ToolDetailView(", "function ToolDetailViewContent(")

tool_detail_wrapper = """
function ToolDetailView(props) {
  return <ErrorBoundary><ToolDetailViewContent {...props} /></ErrorBoundary>;
}

function ToolDetailViewContent({
"""
content = content.replace("function ToolDetailViewContent({", tool_detail_wrapper)


# --- DESIGN 3: Hide tabs for uninstalled Marketplace tools ---
tabs_orig = """      {/* Tabs */}
      <div className="flex border-b border-gray-200 px-4">
        <button 
          onClick={() => setActiveSubTab('config')} 
          className={`px-4 py-3 text-sm font-medium border-b-2 ${activeSubTab === 'config' ? 'border-coral-600 text-coral-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          Configuration Files
        </button>
        <button 
          onClick={() => setActiveSubTab('logs')} 
          className={`px-4 py-3 text-sm font-medium border-b-2 ${activeSubTab === 'logs' ? 'border-coral-600 text-coral-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          Process Logs
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col relative bg-[#1E1E1E]">
        {activeSubTab === 'logs' ? ("""

tabs_new = """      {/* Tabs */}
      {!isInstalling && (
      <div className="flex border-b border-gray-200 px-4">
        <button 
          onClick={() => setActiveSubTab('config')} 
          className={`px-4 py-3 text-sm font-medium border-b-2 ${activeSubTab === 'config' ? 'border-coral-600 text-coral-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          Configuration Files
        </button>
        <button 
          onClick={() => setActiveSubTab('logs')} 
          className={`px-4 py-3 text-sm font-medium border-b-2 ${activeSubTab === 'logs' ? 'border-coral-600 text-coral-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          Process Logs
        </button>
      </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col relative bg-[#1E1E1E]">
        {isInstalling ? (
          <div className="flex-1 flex items-center justify-center bg-gray-50 text-gray-500">
             <div className="text-center">
               <svg className="w-12 h-12 mx-auto text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
               <h3 className="text-lg font-medium text-gray-900 mb-1">Tool Not Installed</h3>
               <p className="text-sm">Click "Install & Start" above to clone and initialize this tool.</p>
             </div>
          </div>
        ) : activeSubTab === 'logs' ? ("""

content = content.replace(tabs_orig, tabs_new)


# --- DESIGN 2: "Installed Tools" Count Styling ---
content = content.replace(
    """<span className="bg-gray-200 text-gray-700 py-0.5 px-2 rounded-full">{tools.filter(t => !t.is_optional || t.is_downloaded).length}</span>""",
    """<span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold text-blue-700 bg-blue-100 rounded-full">{tools.filter(t => !t.is_optional || t.is_downloaded).length}</span>"""
)


# --- DESIGN 1: Move Global Actions ---
header_title_orig = """            <h2 className="text-xl font-bold text-gray-900 capitalize">
              {activeTab === 'overview' && 'Demo Control Hub'}
              {activeTab === 'global-config' && 'Shared Controller Settings'}
              {activeTab === 'tool-configs' && 'Interactive Tool Configuration Files'}
              {activeTab === 'logs' && 'Live Process & Container Logs'}
            </h2>"""
header_title_new = """            <h2 className="text-xl font-bold text-gray-900 capitalize">
              {activeTab === 'overview' && 'Demo Control Hub'}
              {activeTab === 'global-config' && 'Shared Netris Controller Settings'}
              {activeTab === 'tool-configs' && 'Interactive Tool Configuration Files'}
              {activeTab === 'logs' && 'Live Process & Container Logs'}
              {activeTab !== 'overview' && activeTab !== 'global-config' && activeTab !== 'tool-configs' && activeTab !== 'logs' && tools.find(t=>t.id===activeTab)?.name}
            </h2>"""
content = content.replace(header_title_orig, header_title_new)

# Also wait, my previous header title update had 'Shared Controller Settings' but I changed it. 
# Let's just regex replace the h2 entirely to be safe:
import re
content = re.sub(
    r'<h2 className="text-xl font-bold text-gray-900 capitalize">.*?</h2>',
    header_title_new,
    content,
    flags=re.DOTALL
)

actions_orig = """          <div className="flex items-center gap-3">
            {/* Quick Scenario Buttons */}
            <button
              onClick={() => handleRunScenario('start_ai_fabric')}
              className="bg-white text-gray-700 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 px-3.5 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2 shadow-theme-xs"
              title="Launch Slurm Sim and Prometheus/Grafana Stack"
            >
              <Icons.Play />
              <span>Start All AI Fabric</span>
            </button>

            <button
              onClick={() => handleRunScenario('stop_all')}
              className="bg-white text-error-600 ring-1 ring-inset ring-red-200 hover:bg-error-50 px-3.5 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2 shadow-theme-xs cursor-pointer"
              title="Stop all active demo containers and background scripts"
            >
              <Icons.Stop />
              <span>Stop All</span>
            </button>

            {/* Prometheus Telemetry Recording Button in Header */}
            <button
              onClick={() => setRecordingModalOpen(true)}
              className={`ring-1 ring-inset px-3.5 py-2 rounded-lg text-sm font-semibold transition inline-flex items-center gap-2 shadow-theme-xs cursor-pointer ${
                recordingState?.is_recording
                  ? 'bg-red-50 ring-red-400 text-red-700 animate-pulse'
                  : 'bg-white text-gray-700 ring-gray-300 hover:bg-red-50 hover:text-red-700 hover:ring-red-300'
              }`}
              title="Record live Netris telemetry for Prometheus offline looping"
            >
              <span className={`w-2.5 h-2.5 rounded-full ${recordingState?.is_recording ? 'bg-red-600 animate-ping' : 'bg-red-500'}`}></span>
              <span>{recordingState?.is_recording ? `Recording Live (${Math.round(recordingState?.elapsed_seconds || 0)}s)` : 'Record Telemetry'}</span>
            </button>

            {/* Refresh Button */}
            <button
              onClick={loadTools}
              className="bg-white text-gray-700 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 px-3 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2 shadow-theme-xs"
              title="Refresh tools"
            >
              <Icons.Refresh />
            </button>
          </div>"""

actions_new = """          {/* Global actions only shown on global-config or overview */}
          {(activeTab === 'global-config' || activeTab === 'overview') && (
            <div className="flex items-center gap-3">
              <button
                onClick={() => handleRunScenario('start_ai_fabric')}
                className="bg-white text-gray-700 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 px-3.5 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2 shadow-theme-xs"
                title="Launch Slurm Sim and Prometheus/Grafana Stack"
              >
                <Icons.Play />
                <span>Start All AI Fabric</span>
              </button>

              <button
                onClick={() => handleRunScenario('stop_all')}
                className="bg-white text-error-600 ring-1 ring-inset ring-red-200 hover:bg-error-50 px-3.5 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2 shadow-theme-xs cursor-pointer"
                title="Stop all active demo containers and background scripts"
              >
                <Icons.Stop />
                <span>Stop All</span>
              </button>

              <button
                onClick={() => setRecordingModalOpen(true)}
                className={`ring-1 ring-inset px-3.5 py-2 rounded-lg text-sm font-semibold transition inline-flex items-center gap-2 shadow-theme-xs cursor-pointer ${
                  recordingState?.is_recording
                    ? 'bg-red-50 ring-red-400 text-red-700 animate-pulse'
                    : 'bg-white text-gray-700 ring-gray-300 hover:bg-red-50 hover:text-red-700 hover:ring-red-300'
                }`}
                title="Record live Netris telemetry for Prometheus offline looping"
              >
                <span className={`w-2.5 h-2.5 rounded-full ${recordingState?.is_recording ? 'bg-red-600 animate-ping' : 'bg-red-500'}`}></span>
                <span>{recordingState?.is_recording ? `Recording Live (${Math.round(recordingState?.elapsed_seconds || 0)}s)` : 'Record Telemetry'}</span>
              </button>
              
              <button
                onClick={loadTools}
                className="bg-white text-gray-700 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 px-3 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2 shadow-theme-xs"
                title="Refresh tools"
              >
                <Icons.Refresh />
              </button>
            </div>
          )}
"""
content = content.replace(actions_orig, actions_new)

# --- BUG 3: Accessibility (A11y) Form Issues ---
content = content.replace(
    '<label className="block text-sm font-medium text-gray-700 mb-1">\n                    Netris Controller URL\n                  </label>',
    '<label htmlFor="netris_url" className="block text-sm font-medium text-gray-700 mb-1">\n                    Netris Controller URL\n                  </label>'
)
content = content.replace(
    'className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm font-mono"',
    'id="netris_url" name="netris_url" className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm font-mono"'
)

content = content.replace(
    '<label className="block text-sm font-medium text-gray-700 mb-1">\n                      Netris Admin Username\n                    </label>',
    '<label htmlFor="netris_username" className="block text-sm font-medium text-gray-700 mb-1">\n                      Netris Admin Username\n                    </label>'
)
content = content.replace(
    'placeholder="netris"\n                      required',
    'id="netris_username" name="netris_username" placeholder="netris"\n                      required'
)

content = content.replace(
    '<label className="block text-sm font-medium text-gray-700 mb-1">\n                      Netris Admin Password\n                    </label>',
    '<label htmlFor="netris_password" className="block text-sm font-medium text-gray-700 mb-1">\n                      Netris Admin Password\n                    </label>'
)
content = content.replace(
    'type={showPassword ? \'text\' : \'password\'}\n                        value={globalConfig.netris_password}',
    'type={showPassword ? \'text\' : \'password\'}\n                        id="netris_password" name="netris_password" autoComplete="current-password"\n                        value={globalConfig.netris_password}'
)

js_path.write_text(content)
print("done")
