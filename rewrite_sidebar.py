import re
from pathlib import Path

js_path = Path("demo-portal/static/app.js")
content = js_path.read_text()

# 1. Define ToolDetailView component to insert before App()
tool_detail_code = """
function ToolDetailView({ tool, onStart, onStop, onRestart, fetchLogs, configCatalog, fetchConfigFile, saveConfigFile, openTerminal, actionLoading }) {
  const [logs, setLogs] = React.useState([]);
  const [activeSubTab, setActiveSubTab] = React.useState('config');
  const [fileContent, setFileContent] = React.useState('');
  const [selectedFile, setSelectedFile] = React.useState(null);
  const [fileDirty, setFileDirty] = React.useState(false);
  const [fileSaving, setFileSaving] = React.useState(false);
  const [loadingFile, setLoadingFile] = React.useState(false);

  const toolConfig = configCatalog.find(c => c.tool_id === tool.id);
  
  React.useEffect(() => {
    let interval;
    if (activeSubTab === 'logs') {
      const loadLogs = () => {
        fetchLogs(tool.id).then(setLogs).catch(console.error);
      };
      loadLogs();
      interval = setInterval(loadLogs, 3000);
    }
    return () => clearInterval(interval);
  }, [activeSubTab, tool.id, fetchLogs]);

  React.useEffect(() => {
    if (toolConfig && toolConfig.files.length > 0) {
      handleSelectFile(toolConfig.files[0].id);
    } else {
      setSelectedFile(null);
      setFileContent('');
    }
  }, [tool.id, configCatalog]);

  const handleSelectFile = async (fileId) => {
    setSelectedFile(fileId);
    setLoadingFile(true);
    setFileDirty(false);
    try {
      const data = await fetchConfigFile(tool.id, fileId);
      setFileContent(data.content);
    } catch (e) {
      setFileContent('Error loading file');
    } finally {
      setLoadingFile(false);
    }
  };

  const handleSave = async () => {
    setFileSaving(true);
    try {
      await saveConfigFile(tool.id, selectedFile, fileContent);
      setFileDirty(false);
    } catch (e) {
      alert("Save failed: " + e.message);
    } finally {
      setFileSaving(false);
    }
  };

  const isInstalling = tool.is_optional && !tool.is_downloaded;

  return (
    <div className="flex flex-col h-full bg-white rounded-xl shadow-theme-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h3 className="text-xl font-bold text-gray-900">{tool.name}</h3>
            {tool.status === 'running' ? (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-success-50 text-success-700 border border-success-200">RUNNING</span>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 border border-gray-200">STOPPED</span>
            )}
            {isInstalling && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">MARKETPLACE EXTENSION</span>
            )}
          </div>
          <p className="text-sm text-gray-500">{tool.description}</p>
        </div>
        
        <div className="flex items-center gap-3">
          {tool.tool_type === 'interactive' && tool.status === 'running' && (
            <button onClick={() => openTerminal(tool)} className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800">
              Open Terminal
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
          ) : (
            <button onClick={() => onStart(tool.id)} disabled={actionLoading[tool.id]} className="px-4 py-2 bg-coral-600 text-white rounded-lg text-sm font-semibold hover:bg-coral-700 shadow-theme-xs">
              {actionLoading[tool.id] ? 'Starting...' : isInstalling ? 'Install & Start' : 'Start'}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
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
        {activeSubTab === 'logs' ? (
          <div className="flex-1 overflow-y-auto p-4 font-mono text-xs text-gray-300">
            {logs.length === 0 ? (
              <div className="text-gray-500 italic text-center mt-10">No logs available</div>
            ) : (
              logs.map((l, i) => <div key={i} className="mb-1 whitespace-pre-wrap">{l}</div>)
            )}
          </div>
        ) : (
          <div className="flex-1 flex overflow-hidden">
            {toolConfig && toolConfig.files.length > 0 ? (
              <>
                <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
                  {toolConfig.files.map(f => (
                    <button 
                      key={f.id} 
                      onClick={() => handleSelectFile(f.id)}
                      className={`text-left px-4 py-3 text-sm font-medium border-b border-gray-200 ${selectedFile === f.id ? 'bg-white text-coral-600 border-l-4 border-l-coral-600' : 'text-gray-700 hover:bg-gray-100 border-l-4 border-l-transparent'}`}
                    >
                      {f.name}
                    </button>
                  ))}
                </div>
                <div className="flex-1 flex flex-col bg-[#1E1E1E]">
                  <div className="h-12 bg-[#2D2D2D] border-b border-[#404040] flex items-center justify-between px-4">
                    <span className="text-xs font-mono text-gray-300">{selectedFile} {fileDirty && '*'}</span>
                    <button 
                      onClick={handleSave} 
                      disabled={!fileDirty || fileSaving}
                      className={`text-xs px-3 py-1 rounded font-semibold ${fileDirty ? 'bg-coral-600 text-white hover:bg-coral-700' : 'bg-[#404040] text-gray-500 cursor-not-allowed'}`}
                    >
                      {fileSaving ? 'Saving...' : 'Save File'}
                    </button>
                  </div>
                  <textarea 
                    value={fileContent} 
                    onChange={e => { setFileContent(e.target.value); setFileDirty(true); }}
                    className="flex-1 w-full bg-[#1E1E1E] text-[#D4D4D4] font-mono text-sm p-4 focus:outline-none resize-none"
                    spellCheck={false}
                    disabled={loadingFile}
                  />
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500 italic bg-gray-50">
                No configuration files exposed for this tool.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// --- App Root Component ---
"""

content = content.replace("// --- App Root Component ---\n", tool_detail_code)

# 2. Update default activeTab in App
content = content.replace("useState('overview');", "useState('global-config');")

# 3. Replace the sidebar nav
old_nav_start = '<nav className="p-4 space-y-1.5 flex-1">'
old_nav_end = '        {/* Footer Info */}'
idx1 = content.find(old_nav_start)
idx2 = content.find(old_nav_end)

new_nav = """        <nav className="p-4 space-y-1.5 flex-1 overflow-y-auto">
          <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 mt-2 px-2">Settings</div>
          <button
            onClick={() => setActiveTab('global-config')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'global-config'
                ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <Icons.Settings />
            <span>Shared Controller Settings</span>
          </button>
          
          <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 mt-6 px-2 flex justify-between items-center">
            <span>Installed Tools</span>
            <span className="bg-gray-200 text-gray-700 py-0.5 px-2 rounded-full">{tools.filter(t => !t.is_optional || t.is_downloaded).length}</span>
          </div>
          {tools.filter(t => !t.is_optional || t.is_downloaded).map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === t.id
                  ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <div className="flex items-center gap-3 truncate">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${t.status === 'running' ? 'bg-success-500' : 'bg-gray-300'}`}></span>
                <span className="truncate" title={t.name}>{t.name}</span>
              </div>
            </button>
          ))}
          
          {tools.filter(t => t.is_optional && !t.is_downloaded).length > 0 && (
            <>
              <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 mt-6 px-2">Marketplace</div>
              {tools.filter(t => t.is_optional && !t.is_downloaded).map(t => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
                    activeTab === t.id
                      ? 'bg-blue-50 text-blue-700 font-semibold shadow-2xs'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <Icons.Download />
                  <span className="truncate" title={t.name}>{t.name}</span>
                </button>
              ))}
            </>
          )}
        </nav>
"""
content = content[:idx1] + new_nav + content[idx2:]

# 4. Inject ToolDetailView inside <main>
old_main = """          {activeTab === 'overview' && ("""
new_main = """          {activeTab !== 'overview' && activeTab !== 'global-config' && activeTab !== 'tool-configs' && activeTab !== 'logs' && (
            <ToolDetailView 
              tool={tools.find(t => t.id === activeTab)}
              onStart={(id) => handleStartTool(tools.find(t => t.id === id))}
              onStop={(id) => handleStopTool(tools.find(t => t.id === id))}
              onRestart={(id) => handleRestartTool(tools.find(t => t.id === id))}
              fetchLogs={fetchLogs}
              configCatalog={configCatalog}
              fetchConfigFile={fetchConfigFile}
              saveConfigFile={saveConfigFile}
              openTerminal={t => setTerminalModalTool(t)}
              actionLoading={actionLoading}
            />
          )}
          {activeTab === 'overview' && ("""

content = content.replace(old_main, new_main)

js_path.write_text(content)
print("patch applied")
