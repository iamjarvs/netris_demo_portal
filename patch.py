import sys

def modify_app_js():
    with open('./demo-portal/static/app.js', 'r') as f:
        content = f.read()

    # 1. Update initial state and add useEffect
    target_state = """  const [logs, setLogs] = React.useState([]);
  const [activeSubTab, setActiveSubTab] = React.useState('config');
  const [fileContent, setFileContent] = React.useState('');
  const [selectedFile, setSelectedFile] = React.useState(null);
  const [fileDirty, setFileDirty] = React.useState(false);
  const [fileSaving, setFileSaving] = React.useState(false);
  const [loadingFile, setLoadingFile] = React.useState(false);

  if (!tool) return null; const toolConfig = configCatalog.find(c => c.tool_id === tool.id);
  
  React.useEffect(() => {"""
    
    new_state = """  const [logs, setLogs] = React.useState([]);
  const [activeSubTab, setActiveSubTab] = React.useState('overview');
  const [fileContent, setFileContent] = React.useState('');
  const [selectedFile, setSelectedFile] = React.useState(null);
  const [fileDirty, setFileDirty] = React.useState(false);
  const [fileSaving, setFileSaving] = React.useState(false);
  const [loadingFile, setLoadingFile] = React.useState(false);

  if (!tool) return null; const toolConfig = configCatalog.find(c => c.tool_id === tool.id);
  
  const activeFileObj = toolConfig?.files.find(f => f.id === selectedFile);
  const activeFileFormat = activeFileObj ? activeFileObj.format : 'shell';

  React.useEffect(() => {
    setActiveSubTab('overview');
  }, [tool.id]);

  React.useEffect(() => {"""
    content = content.replace(target_state, new_state)

    # 2. Add Overview tab button
    target_tabs = """      {/* Tabs */}
      {!isInstalling && (
      <div className="flex border-b border-gray-200 px-4">
        <button 
          onClick={() => setActiveSubTab('config')} 
          className={`px-4 py-3 text-sm font-medium border-b-2 ${activeSubTab === 'config' ? 'border-coral-600 text-coral-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          Configuration Files
        </button>"""
        
    new_tabs = """      {/* Tabs */}
      {!isInstalling && (
      <div className="flex border-b border-gray-200 px-4">
        <button 
          onClick={() => setActiveSubTab('overview')} 
          className={`px-4 py-3 text-sm font-medium border-b-2 ${activeSubTab === 'overview' ? 'border-coral-600 text-coral-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          Overview
        </button>
        <button 
          onClick={() => setActiveSubTab('config')} 
          className={`px-4 py-3 text-sm font-medium border-b-2 ${activeSubTab === 'config' ? 'border-coral-600 text-coral-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          Configuration Files
        </button>"""
    content = content.replace(target_tabs, new_tabs)

    # 3. Add Overview content, removing startup command and only showing credentials if present
    target_content_start = """        ) : activeSubTab === 'logs' ? ("""
    new_overview_content = """        ) : activeSubTab === 'overview' ? (
          <div className="flex-1 overflow-y-auto bg-gray-50 p-8 text-gray-800">
            <div className="max-w-3xl mx-auto space-y-6">
              <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-theme-xs">
                <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">About this tool</h3>
                <p className="text-gray-600 text-sm leading-relaxed whitespace-pre-wrap">{tool.description || 'No description available for this tool.'}</p>
              </div>
              
              {tool.status === 'running' && (
                <div className="bg-white rounded-xl border border-success-200 p-6 shadow-theme-xs">
                  <h3 className="text-sm font-bold text-success-800 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-success-500"></span> Live Metrics & Endpoints
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                     <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 shadow-inner">
                        <div className="text-xs text-gray-500 mb-1">Process State</div>
                        <div className="font-bold text-success-700 text-sm">Running</div>
                     </div>
                     {tool.uptime && (
                       <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 shadow-inner">
                          <div className="text-xs text-gray-500 mb-1">Uptime</div>
                          <div className="font-mono text-gray-800 text-sm">{tool.uptime}</div>
                       </div>
                     )}
                     {tool.port && (
                       <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 shadow-inner">
                          <div className="text-xs text-gray-500 mb-1">Local Port</div>
                          <div className="font-mono text-gray-800 text-sm">{tool.port}</div>
                       </div>
                     )}
                     {tool.popout_url && (
                       <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 shadow-inner col-span-full">
                          <div className="text-xs text-gray-500 mb-2">Web Interface</div>
                          <a href={tool.popout_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-md text-xs font-semibold transition">
                            Open {tool.name} in New Tab
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                          </a>
                       </div>
                     )}
                  </div>
                </div>
              )}

              {tool.credentials && tool.credentials.length > 0 && tool.credentials.some(c => !c.no_auth) && (
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-theme-xs">
                  <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">Access Credentials</h3>
                  <div className="space-y-3">
                    {tool.credentials.filter(c => !c.no_auth).map((cred, idx) => (
                      <div key={idx} className="flex flex-col gap-1 p-3 bg-gray-50 rounded-lg border border-gray-100">
                        <div className="text-xs text-gray-500 font-semibold">{cred.label || 'Login Info'}</div>
                        <div className="text-sm text-gray-800">
                          <span className="font-medium mr-2">User:</span> <code className="bg-white px-1.5 py-0.5 rounded border border-gray-200">{cred.username}</code>
                        </div>
                        <div className="text-sm text-gray-800">
                          <span className="font-medium mr-2">Pass:</span> <code className="bg-white px-1.5 py-0.5 rounded border border-gray-200">{cred.password}</code>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : activeSubTab === 'logs' ? ("""
    content = content.replace(target_content_start, new_overview_content)

    # 4. Inject ConfigFormEditor component before ToolDetailView
    with open('patch_config_form.js', 'r') as patch_file:
        config_form_code = patch_file.read()
    
    target_tool_detail_view = """function ToolDetailView(props) {"""
    new_tool_detail_view = config_form_code + "\n\n" + target_tool_detail_view
    content = content.replace(target_tool_detail_view, new_tool_detail_view)

    # 5. Replace textareas with ConfigFormEditor
    target_textarea_1 = """                  <textarea 
                    value={fileContent} 
                    onChange={e => { setFileContent(e.target.value); setFileDirty(true); }}
                    className="flex-1 w-full bg-[#1E1E1E] text-[#D4D4D4] font-mono text-sm p-4 focus:outline-none resize-none"
                    spellCheck={false}
                    disabled={loadingFile}
                  />"""
    new_editor_1 = """                  <div className="flex-1 overflow-auto bg-[#1E1E1E]">
                    <ConfigFormEditor 
                      content={fileContent} 
                      format={activeFileFormat} 
                      onChange={val => { setFileContent(val); setFileDirty(true); }} 
                    />
                  </div>"""
    content = content.replace(target_textarea_1, new_editor_1)

    target_textarea_2 = """                      <textarea
                        rows={22}
                        value={toolConfigContent}
                        onChange={(e) => {
                          setToolConfigContent(e.target.value);
                          setFileDirty(true);
                        }}
                        className="w-full font-mono text-xs bg-gray-950 text-emerald-300 p-5 focus:outline-none focus:ring-2 focus:ring-coral-500 leading-relaxed resize-y"
                        spellCheck="false"
                      ></textarea>"""
    new_editor_2 = """                      <div className="h-[480px] bg-gray-950 overflow-auto border border-gray-800">
                        <ConfigFormEditor 
                          content={toolConfigContent} 
                          format={activeToolCatalogEntry?.files?.find(f => f.id === selectedFileId)?.format || 'shell'} 
                          onChange={(val) => {
                            setToolConfigContent(val);
                            setFileDirty(true);
                          }} 
                        />
                      </div>"""
    content = content.replace(target_textarea_2, new_editor_2)

    with open('./demo-portal/static/app.js', 'w') as f:
        f.write(content)

modify_app_js()
