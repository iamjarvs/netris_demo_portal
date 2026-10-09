with open('./demo-portal/static/app.js', 'r') as f:
    lines = f.readlines()

def replace_line(prefix, new_line):
    for i, line in enumerate(lines):
        if prefix in line:
            lines[i] = new_line
            return

def replace_block(start_prefix, end_prefix, new_content, inclusive_end=True):
    start_idx = -1
    for i, line in enumerate(lines):
        if start_prefix in line:
            start_idx = i
            break
            
    end_idx = -1
    for i in range(start_idx, len(lines)):
        if end_prefix in line:
            end_idx = i
            break
            
    if start_idx != -1 and end_idx != -1:
        end = end_idx + 1 if inclusive_end else end_idx
        lines[start_idx:end] = [new_content]
    else:
        print(f"FAILED TO FIND BLOCK: {start_prefix} to {end_prefix}")

# 1. Update initial tab
replace_line("useState('global-config')", "  const [activeTab, setActiveTab] = useState('overview'); // overview, global-config, tool-configs, logs, catalogue\n")

# 2. Add states
replace_line("const [searchQuery, setSearchQuery] = useState('');", 
             "  const [searchQuery, setSearchQuery] = useState('');\n  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);\n  const [isOtherOpen, setIsOtherOpen] = useState(false);\n  const [catalogueSearchQuery, setCatalogueSearchQuery] = useState('');\n")

# 3. Replace aside
new_aside = """      <aside className={`bg-white border-r border-gray-200 fixed top-0 bottom-0 left-0 flex flex-col z-30 shadow-theme-xs transition-all duration-300 ${isSidebarCollapsed ? 'w-[80px]' : 'w-[280px]'}`}>
        {/* Brand / Header */}
        <div className="h-[72px] px-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-coral-50 flex items-center justify-center border border-coral-200 shadow-2xs flex-shrink-0">
              <div className="w-4 h-4 rounded-full bg-coral-500"></div>
            </div>
            {!isSidebarCollapsed && (
              <div className="whitespace-nowrap">
                <h1 className="text-base font-bold text-gray-900 tracking-tight">Proof of Concept</h1>
                <p className="text-[10px] text-gray-400">Netris & AI Fabric Hub</p>
              </div>
            )}
          </div>
          <button 
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition hidden md:block flex-shrink-0"
            title={isSidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {isSidebarCollapsed ? <Icons.ChevronRight className="w-4 h-4" /> : <Icons.ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1.5 flex-1 overflow-y-auto overflow-x-hidden">
          <button
            onClick={() => setActiveTab('overview')}
            title="Overview Hub"
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'overview'
                ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                : 'text-gray-700 hover:bg-gray-100'
            } ${isSidebarCollapsed ? 'justify-center' : ''}`}
          >
            <Icons.Dashboard className="w-5 h-5 flex-shrink-0" />
            {!isSidebarCollapsed && <span>Overview Hub</span>}
          </button>
          
          <div className={`text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 mt-6 px-2 flex items-center ${isSidebarCollapsed ? 'justify-center' : 'justify-between'}`}>
            {!isSidebarCollapsed && <span>Installed Tools</span>}
            <span className={`inline-flex items-center justify-center text-xs font-bold text-blue-700 bg-blue-100 rounded-full ${isSidebarCollapsed ? 'w-5 h-5' : 'px-2 py-0.5'}`}>
              {tools.filter(t => (!t.is_optional || t.is_downloaded) && t.category !== 'Other').length}
            </span>
          </div>
          
          {tools.filter(t => (!t.is_optional || t.is_downloaded) && t.category !== 'Other').map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              title={t.name}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition relative group ${
                activeTab === t.id
                  ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                  : 'text-gray-700 hover:bg-gray-100'
              } ${isSidebarCollapsed ? 'justify-center' : 'justify-between'}`}
            >
              <div className="flex items-center gap-3 truncate">
                <span className="flex-shrink-0 text-gray-500 group-hover:text-current">{getToolIcon(t)}</span>
                {!isSidebarCollapsed && <span className="truncate text-left" title={t.name}>{t.name}</span>}
              </div>
              {!isSidebarCollapsed && (
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${t.status === 'running' ? 'bg-success-500' : 'bg-gray-300'}`}></span>
              )}
              {isSidebarCollapsed && t.status === 'running' && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-success-500 shadow-sm border border-white"></span>
              )}
            </button>
          ))}

          {/* Collapsible "Other" Section */}
          {tools.filter(t => (!t.is_optional || t.is_downloaded) && t.category === 'Other').length > 0 && (
            <div className="mt-4">
              <button
                onClick={() => {
                  if (isSidebarCollapsed) setIsSidebarCollapsed(false);
                  setIsOtherOpen(!isOtherOpen || isSidebarCollapsed);
                }}
                title="Other Tools"
                className={`w-full flex items-center px-2 py-1.5 text-[11px] font-bold text-gray-400 uppercase tracking-wider hover:bg-gray-100 rounded transition cursor-pointer ${isSidebarCollapsed ? 'justify-center' : 'justify-between'}`}
              >
                {!isSidebarCollapsed && <span>Other Tools</span>}
                <svg className={`w-3.5 h-3.5 transition-transform flex-shrink-0 ${isOtherOpen && !isSidebarCollapsed ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {isSidebarCollapsed ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" /> : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />}
                </svg>
              </button>
              
              {isOtherOpen && !isSidebarCollapsed && (
                <div className="mt-1 space-y-1 pl-2 border-l-2 border-gray-100 ml-3">
                  {tools.filter(t => (!t.is_optional || t.is_downloaded) && t.category === 'Other').map(t => (
                    <button
                      key={t.id}
                      onClick={() => setActiveTab(t.id)}
                      title={t.name}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition ${
                        activeTab === t.id
                          ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="flex-shrink-0 w-4 h-4 text-gray-500">{getToolIcon(t)}</span>
                        <span className="truncate text-xs" title={t.name}>{t.name}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className={`text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 mt-6 px-2 flex ${isSidebarCollapsed ? 'justify-center' : ''}`}>
            {!isSidebarCollapsed && <span>Additional Tools</span>}
          </div>
          <button
            onClick={() => setActiveTab('catalogue')}
            title="Search Tool Catalogue"
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'catalogue'
                ? 'bg-blue-50 text-blue-700 font-semibold shadow-2xs'
                : 'text-gray-700 hover:bg-gray-100'
            } ${isSidebarCollapsed ? 'justify-center' : ''}`}
          >
            <Icons.Store className="w-5 h-5 flex-shrink-0" />
            {!isSidebarCollapsed && <span>Search Tool Catalogue</span>}
          </button>

          <div className="mt-8 pt-4 border-t border-gray-100">
            <div className={`text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 px-2 flex ${isSidebarCollapsed ? 'justify-center' : ''}`}>
              {!isSidebarCollapsed && <span>Settings</span>}
            </div>
            <button
              onClick={() => setActiveTab('global-config')}
              title="Shared Controller Settings"
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'global-config'
                  ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                  : 'text-gray-700 hover:bg-gray-100'
              } ${isSidebarCollapsed ? 'justify-center' : ''}`}
            >
              <Icons.Settings className="w-5 h-5 flex-shrink-0" />
              {!isSidebarCollapsed && <span className="truncate">Shared Controller Settings</span>}
            </button>
          </div>
        </nav>
      </aside>\n"""
replace_block('<aside className="w-[280px]', '</aside>', new_aside, inclusive_end=True)

# 4. Replace main wrapper
replace_line('<main className="ml-[280px]', '      <main className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${isSidebarCollapsed ? "ml-[80px]" : "ml-[280px]"}`}>\n')

# 5. Replace overview and insert catalogue
new_overview = """          {activeTab === 'overview' && (
            <div className="max-w-5xl mx-auto w-full px-8 py-8 animate-in fade-in duration-300">
              {/* Intro Section */}
              <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-theme-sm text-center mb-8">
                <h2 className="text-3xl font-bold text-gray-900 mb-4">Welcome to Proof of Concept Evaluations</h2>
                <p className="text-gray-600 max-w-2xl mx-auto mb-6">
                  This hub provides centralized management and health monitoring for all Proof of Concept tools and integrations. 
                  Launch, configure, and monitor evaluations tailored for AI Fabric and cloud networking seamlessly.
                </p>
                <div className="flex justify-center gap-4">
                  <span className="inline-flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full text-sm font-medium text-gray-700 shadow-2xs">
                    <span className="w-2.5 h-2.5 rounded-full bg-success-500 animate-pulse"></span>
                    {runningCount} Tools Running
                  </span>
                  <span className="inline-flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full text-sm font-medium text-gray-700 shadow-2xs">
                    <span className="w-2.5 h-2.5 rounded-full bg-gray-400"></span>
                    {stoppedCount} Tools Stopped
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-gray-900">Installed Tools</h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {tools.filter(t => (!t.is_optional || t.is_downloaded) && t.category !== 'Other').map(tool => (
                  <div 
                    key={tool.id} 
                    onClick={() => setActiveTab(tool.id)}
                    className="bg-white rounded-xl border border-gray-200 p-5 shadow-theme-xs hover:shadow-theme-md hover:border-coral-200 transition-all cursor-pointer flex flex-col justify-between group"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <div className="w-10 h-10 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center text-gray-500 group-hover:text-coral-600 group-hover:bg-coral-50 transition-colors">
                          {getToolIcon(tool)}
                        </div>
                        <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${tool.status === 'running' ? 'bg-success-100 text-success-700' : 'bg-gray-100 text-gray-600'}`}>
                          {tool.status}
                        </span>
                      </div>
                      <h4 className="text-base font-bold text-gray-900 mb-1 group-hover:text-coral-700 transition-colors">{tool.name}</h4>
                      <p className="text-xs text-gray-500 line-clamp-2">{tool.description}</p>
                    </div>
                    <div className="mt-4 pt-3 border-t border-gray-100 flex items-center text-sm font-medium text-coral-600 group-hover:text-coral-700">
                      Open Tool
                      <svg className="w-4 h-4 ml-1 transform group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'catalogue' && (
            <div className="max-w-6xl mx-auto w-full px-8 py-8 animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Search Tool Catalogue</h2>
                  <p className="text-sm text-gray-500 mt-1">Browse and install additional Proof of Concept evaluations from the marketplace.</p>
                </div>
                <div className="relative max-w-sm w-full">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                  </div>
                  <input
                    type="text"
                    placeholder="Search catalogue..."
                    value={catalogueSearchQuery}
                    onChange={(e) => setCatalogueSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition shadow-2xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {tools
                  .filter(t => t.is_optional && !t.is_downloaded)
                  .filter(t => t.name.toLowerCase().includes(catalogueSearchQuery.toLowerCase()) || t.description.toLowerCase().includes(catalogueSearchQuery.toLowerCase()))
                  .map(tool => (
                  <div key={tool.id} className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col shadow-theme-xs">
                    <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center mb-4">
                      {getToolIcon(tool)}
                    </div>
                    <h4 className="text-base font-bold text-gray-900 mb-2">{tool.name}</h4>
                    <p className="text-xs text-gray-500 flex-1 mb-4">{tool.description}</p>
                    <button
                      onClick={() => setActiveTab(tool.id)}
                      className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition"
                    >
                      View Details & Install
                    </button>
                  </div>
                ))}
                {tools.filter(t => t.is_optional && !t.is_downloaded).length === 0 && (
                  <div className="col-span-full py-12 text-center bg-gray-50 rounded-2xl border border-dashed border-gray-300">
                    <Icons.Box className="w-10 h-10 text-gray-400 mx-auto mb-3" />
                    <h3 className="text-gray-900 font-semibold mb-1">All Tools Installed</h3>
                    <p className="text-gray-500 text-sm">There are no more tools available in the catalogue at this time.</p>
                  </div>
                )}
              </div>
            </div>
          )}\n"""

replace_block("activeTab === 'overview' && (", "activeTab === 'global-config' && (", new_overview, inclusive_end=False)

with open('./demo-portal/static/app.js', 'w') as f:
    f.writelines(lines)

