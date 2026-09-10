const { useState, useEffect, useRef } = React;

// --- API Service ---
const API_BASE = "";

async function fetchTools() {
  const res = await fetch(`${API_BASE}/api/tools`);
  if (!res.ok) throw new Error("Failed to fetch tools");
  return res.json();
}

async function startToolApi(toolId) {
  const res = await fetch(`${API_BASE}/api/tools/${toolId}/start`, { method: "POST" });
  return res.json();
}

async function stopToolApi(toolId) {
  const res = await fetch(`${API_BASE}/api/tools/${toolId}/stop`, { method: "POST" });
  return res.json();
}

async function restartToolApi(toolId) {
  const res = await fetch(`${API_BASE}/api/tools/${toolId}/restart`, { method: "POST" });
  return res.json();
}

async function fetchLogs(toolId, limit = 150) {
  const res = await fetch(`${API_BASE}/api/tools/${toolId}/logs?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch logs");
  return res.json();
}

async function runScenarioApi(scenarioId) {
  const res = await fetch(`${API_BASE}/api/tools/scenarios/${scenarioId}`, { method: "POST" });
  return res.json();
}

async function fetchGlobalConfig() {
  const res = await fetch(`${API_BASE}/api/config/global`);
  if (!res.ok) throw new Error("Failed to fetch global config");
  return res.json();
}

async function saveGlobalConfig(config) {
  const res = await fetch(`${API_BASE}/api/config/global`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  return res.json();
}

async function fetchToolRawConfig(toolId) {
  const res = await fetch(`${API_BASE}/api/config/tool/${toolId}`);
  if (!res.ok) throw new Error("No config available");
  return res.json();
}

async function saveToolRawConfig(toolId, content) {
  const res = await fetch(`${API_BASE}/api/config/tool/${toolId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_content: content }),
  });
  return res.json();
}

// --- Icons Component Helpers ---
const Icons = {
  Dashboard: () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  ),
  Settings: () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  ToolConfig: () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  ),
  Terminal: () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  Popout: () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
    </svg>
  ),
  Play: () => (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
    </svg>
  ),
  Stop: () => (
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clipRule="evenodd" />
    </svg>
  ),
  Refresh: () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
};

// --- App Root Component ---
function App() {
  const [activeTab, setActiveTab] = useState("overview"); // overview, global-config, tool-configs, logs
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState({});
  const [selectedToolLogs, setSelectedToolLogs] = useState(null);
  const [logContent, setLogContent] = useState([]);
  const [autoRefreshLogs, setAutoRefreshLogs] = useState(true);
  const [notification, setNotification] = useState(null);

  // Global Config State
  const [globalConfig, setGlobalConfig] = useState({
    netris_url: "https://adam-ctl.netris.io",
    netris_username: "netris",
    netris_password: "",
    netris_verify_ssl: false,
    default_tenant: "Demo",
    default_site: "SantaClara",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);

  // Tool Raw Config State
  const [selectedToolConfigId, setSelectedToolConfigId] = useState("netris-prometheus-exporter");
  const [toolConfigContent, setToolConfigContent] = useState("");
  const [toolConfigLoading, setToolConfigLoading] = useState(false);

  const notify = (message, type = "success") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4500);
  };

  // Poll tools every 3 seconds
  useEffect(() => {
    loadTools();
    const interval = setInterval(loadTools, 3000);
    return () => clearInterval(interval);
  }, []);

  // Fetch global config on mount
  useEffect(() => {
    fetchGlobalConfig()
      .then((cfg) => setGlobalConfig(cfg))
      .catch((e) => console.error("Global config load error", e));
  }, []);

  // Fetch tool config on tab / selection change
  useEffect(() => {
    if (activeTab === "tool-configs" && selectedToolConfigId) {
      loadToolRawConfig(selectedToolConfigId);
    }
  }, [activeTab, selectedToolConfigId]);

  const loadTools = async () => {
    try {
      const data = await fetchTools();
      setTools(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadToolRawConfig = async (toolId) => {
    setToolConfigLoading(true);
    try {
      const data = await fetchToolRawConfig(toolId);
      setToolConfigContent(data.content || "");
    } catch (e) {
      setToolConfigContent("# No configuration file available for this tool.");
    } finally {
      setToolConfigLoading(false);
    }
  };

  // Tool Actions
  const handleStart = async (toolId) => {
    setActionLoading((prev) => ({ ...prev, [toolId]: true }));
    try {
      const res = await startToolApi(toolId);
      notify(res.message || `Started ${toolId}`);
      await loadTools();
    } catch (e) {
      notify(`Start failed: ${e.message}`, "error");
    } finally {
      setActionLoading((prev) => ({ ...prev, [toolId]: false }));
    }
  };

  const handleStop = async (toolId) => {
    setActionLoading((prev) => ({ ...prev, [toolId]: true }));
    try {
      const res = await stopToolApi(toolId);
      notify(res.message || `Stopped ${toolId}`);
      await loadTools();
    } catch (e) {
      notify(`Stop failed: ${e.message}`, "error");
    } finally {
      setActionLoading((prev) => ({ ...prev, [toolId]: false }));
    }
  };

  const handleRestart = async (toolId) => {
    setActionLoading((prev) => ({ ...prev, [toolId]: true }));
    try {
      const res = await restartToolApi(toolId);
      notify(res.message || `Restarted ${toolId}`);
      await loadTools();
    } catch (e) {
      notify(`Restart failed: ${e.message}`, "error");
    } finally {
      setActionLoading((prev) => ({ ...prev, [toolId]: false }));
    }
  };

  const handleRunScenario = async (scenarioId) => {
    try {
      const res = await runScenarioApi(scenarioId);
      notify(res.message);
      await loadTools();
    } catch (e) {
      notify(`Scenario error: ${e.message}`, "error");
    }
  };

  const handleSaveGlobalConfig = async (e) => {
    e.preventDefault();
    setConfigSaving(true);
    try {
      const res = await saveGlobalConfig(globalConfig);
      notify(res.message || "Global configuration propagated!");
    } catch (e) {
      notify(`Save error: ${e.message}`, "error");
    } finally {
      setConfigSaving(false);
    }
  };

  const handleSaveToolRawConfig = async () => {
    try {
      const res = await saveToolRawConfig(selectedToolConfigId, toolConfigContent);
      notify(res.message || "Saved tool configuration!");
    } catch (e) {
      notify(`Error: ${e.message}`, "error");
    }
  };

  // Open Log Modal & Live Poll
  const openLogs = (toolId) => {
    setSelectedToolLogs(toolId);
    fetchLogs(toolId)
      .then((data) => setLogContent(data.lines || []))
      .catch((e) => setLogContent([`Error loading logs: ${e.message}`]));
  };

  useEffect(() => {
    if (!selectedToolLogs || !autoRefreshLogs) return;
    const interval = setInterval(() => {
      fetchLogs(selectedToolLogs)
        .then((data) => setLogContent(data.lines || []))
        .catch(() => {});
    }, 2000);
    return () => clearInterval(interval);
  }, [selectedToolLogs, autoRefreshLogs]);

  // Compute Metrics
  const runningCount = tools.filter((t) => t.is_running).length;
  const stoppedCount = tools.length - runningCount;

  return (
    <div className="flex min-h-screen bg-gray-50 font-outfit text-gray-700">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed top-5 right-5 z-[999999] px-4 py-3 rounded-lg shadow-theme-lg text-sm font-medium border flex items-center gap-2 ${
            notification.type === "error"
              ? "bg-error-50 text-error-600 border-red-200"
              : "bg-success-50 text-success-600 border-emerald-200"
          }`}
        >
          <span>{notification.message}</span>
        </div>
      )}

      {/* --- Sidebar (280px fixed per common-ui-guidelines) --- */}
      <aside className="w-[280px] bg-white border-r border-gray-200 fixed top-0 bottom-0 left-0 flex flex-col z-30 shadow-theme-xs">
        {/* Brand / Title Header (§2: generic project name, no corporate logo) */}
        <div className="h-[72px] px-6 border-b border-gray-200 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-coral-50 flex items-center justify-center border border-coral-200">
            <div className="w-3.5 h-3.5 rounded-full bg-coral-500"></div>
          </div>
          <div>
            <h1 className="text-base font-semibold text-gray-900 tracking-tight">Demo Command Center</h1>
            <p className="text-xs text-gray-400">Toolkit Management Portal</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-4 space-y-1.5 flex-1">
          <button
            onClick={() => setActiveTab("overview")}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === "overview"
                ? "bg-coral-50 text-coral-700 font-semibold"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <Icons.Dashboard />
            <span>Dashboard Hub</span>
          </button>

          <button
            onClick={() => setActiveTab("global-config")}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === "global-config"
                ? "bg-coral-50 text-coral-700 font-semibold"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <Icons.Settings />
            <span>Shared Controller Settings</span>
          </button>

          <button
            onClick={() => setActiveTab("tool-configs")}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === "tool-configs"
                ? "bg-coral-50 text-coral-700 font-semibold"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <Icons.ToolConfig />
            <span>Tool Configurations</span>
          </button>

          <button
            onClick={() => {
              setActiveTab("logs");
              if (!selectedToolLogs && tools.length > 0) {
                openLogs(tools[0].id);
              }
            }}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === "logs"
                ? "bg-coral-50 text-coral-700 font-semibold"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <Icons.Terminal />
            <span>Process Logs Console</span>
          </button>
        </nav>

        {/* Footer Info */}
        <div className="p-4 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
          <div className="flex justify-between items-center mb-1">
            <span className="font-medium text-gray-700">Port 8800 Active</span>
            <span className="inline-flex items-center gap-1 text-success-600 font-medium">
              <span className="w-2 h-2 rounded-full bg-success-500"></span> Online
            </span>
          </div>
          <p className="text-gray-400">Light theme &middot; TailAdmin v2</p>
        </div>
      </aside>

      {/* --- Main Content Canvas (offset by sidebar width) --- */}
      <main className="ml-[280px] flex-1 flex flex-col min-w-0">
        {/* Sticky Header */}
        <header className="sticky top-0 z-20 h-[72px] bg-white border-b border-gray-200 px-8 flex items-center justify-between shadow-theme-xs">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 capitalize">
              {activeTab === "overview" && "Demo Control Hub"}
              {activeTab === "global-config" && "Shared Netris Controller Settings"}
              {activeTab === "tool-configs" && "Individual Tool Configuration Editor"}
              {activeTab === "logs" && "Live Process & Container Logs"}
            </h2>
          </div>

          <div className="flex items-center gap-3">
            {/* Quick Scenario Buttons */}
            <button
              onClick={() => handleRunScenario("start_ai_fabric")}
              className="bg-white text-gray-700 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 px-3.5 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2 shadow-theme-xs"
              title="Launch Slurm Sim and Prometheus/Grafana Stack"
            >
              <Icons.Play />
              <span>Start All AI Fabric</span>
            </button>

            <button
              onClick={() => handleRunScenario("stop_all")}
              className="bg-white text-error-600 ring-1 ring-inset ring-red-200 hover:bg-error-50 px-3.5 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2 shadow-theme-xs"
              title="Stop all active demo containers and background scripts"
            >
              <Icons.Stop />
              <span>Stop All</span>
            </button>

            {/* Refresh Button */}
            <button
              onClick={loadTools}
              className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-100 transition shadow-theme-xs"
              title="Refresh status"
            >
              <Icons.Refresh />
            </button>
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8 max-w-[1400px] w-full mx-auto space-y-6">
          {/* ========================================================================= */}
          {/* TAB 1: OVERVIEW / DASHBOARD                                               */}
          {/* ========================================================================= */}
          {activeTab === "overview" && (
            <>
              {/* KPI Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-theme-xs">
                  <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Total Demo Tools</span>
                  <div className="text-2xl font-bold text-gray-900 mt-1">{tools.length}</div>
                  <span className="text-xs text-gray-500 mt-1 block">Full stack across AI cloud</span>
                </div>

                <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-theme-xs">
                  <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Running Now</span>
                  <div className="text-2xl font-bold text-success-600 mt-1 flex items-center gap-2">
                    {runningCount}
                    {runningCount > 0 && <span className="w-2.5 h-2.5 rounded-full bg-success-500 animate-ping"></span>}
                  </div>
                  <span className="text-xs text-gray-500 mt-1 block">Ready for customer demos</span>
                </div>

                <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-theme-xs">
                  <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Stopped Tools</span>
                  <div className="text-2xl font-bold text-gray-600 mt-1">{stoppedCount}</div>
                  <span className="text-xs text-gray-500 mt-1 block">Standby / inactive</span>
                </div>

                <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-theme-xs">
                  <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Target Controller</span>
                  <div className="text-sm font-semibold text-gray-900 mt-1 truncate" title={globalConfig.netris_url}>
                    {globalConfig.netris_url || "Not configured"}
                  </div>
                  <span className="text-xs text-emerald-600 mt-1 block font-medium">Shared config synced</span>
                </div>
              </div>

              {/* Tools Grid */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-gray-900">Registered Demo Applications</h3>
                  <span className="text-xs text-gray-500">Live heartbeats update every 3s</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                  {tools.map((tool) => {
                    const isRunning = tool.is_running;
                    const isBusy = actionLoading[tool.id];

                    return (
                      <div
                        key={tool.id}
                        className="bg-white rounded-2xl border border-gray-200 p-6 shadow-theme-xs hover:shadow-theme-sm transition flex flex-col justify-between"
                      >
                        <div>
                          {/* Top Tag & Status Pill */}
                          <div className="flex items-center justify-between gap-2 mb-3">
                            <span className="text-xs font-medium bg-gray-100 text-gray-700 px-2.5 py-0.5 rounded-full">
                              {tool.category}
                            </span>

                            {isRunning ? (
                              <span className="inline-flex items-center gap-1.5 bg-success-50 text-success-600 border border-emerald-200 text-xs px-2.5 py-0.5 rounded-full font-semibold">
                                <span className="w-1.5 h-1.5 rounded-full bg-success-500 animate-pulse"></span>
                                RUNNING
                              </span>
                            ) : (
                              <span className="bg-gray-100 text-gray-500 text-xs px-2.5 py-0.5 rounded-full font-medium">
                                STOPPED
                              </span>
                            )}
                          </div>

                          {/* Tool Name & Description */}
                          <h4 className="text-base font-semibold text-gray-900">{tool.name}</h4>
                          <p className="text-xs text-gray-500 mt-1.5 leading-relaxed min-h-[38px]">
                            {tool.description}
                          </p>

                          {/* Port / Type Badges */}
                          <div className="flex flex-wrap items-center gap-2 mt-4 text-xs font-mono text-gray-600">
                            {tool.port ? (
                              <span className="bg-gray-50 border border-gray-200 px-2 py-1 rounded-md">
                                Port: <strong className="text-gray-900">{tool.port}</strong>
                              </span>
                            ) : (
                              <span className="bg-gray-50 border border-gray-200 px-2 py-1 rounded-md text-gray-400">
                                No HTTP Port
                              </span>
                            )}

                            {tool.uptime && (
                              <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-1 rounded-md">
                                Uptime: {tool.uptime}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Action Buttons Row */}
                        <div className="mt-6 pt-4 border-t border-gray-100 flex items-center justify-between gap-2">
                          {/* Pop-Out Action Button */}
                          {tool.popout_url ? (
                            <button
                              onClick={() => window.open(tool.popout_url, "_blank")}
                              disabled={!isRunning}
                              className={`px-3.5 py-2 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 transition shadow-theme-xs ${
                                isRunning
                                  ? "bg-coral-600 hover:bg-coral-700 text-white cursor-pointer"
                                  : "bg-gray-100 text-gray-400 cursor-not-allowed"
                              }`}
                              title={isRunning ? `Pop out ${tool.name} in new window` : "Start the tool first to pop out"}
                            >
                              <Icons.Popout />
                              <span>Open App ↗</span>
                            </button>
                          ) : (
                            <span className="text-xs text-gray-400 italic">Backend Daemon</span>
                          )}

                          {/* Controls (Start, Stop, Restart, Logs) */}
                          <div className="flex items-center gap-1.5">
                            {isRunning ? (
                              <>
                                <button
                                  onClick={() => handleStop(tool.id)}
                                  disabled={isBusy}
                                  className="p-2 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 text-xs font-medium transition"
                                  title="Stop program"
                                >
                                  <Icons.Stop />
                                </button>
                                <button
                                  onClick={() => handleRestart(tool.id)}
                                  disabled={isBusy}
                                  className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-100 text-xs font-medium transition"
                                  title="Restart program"
                                >
                                  <Icons.Refresh />
                                </button>
                              </>
                            ) : (
                              <button
                                onClick={() => handleStart(tool.id)}
                                disabled={isBusy}
                                className="bg-white text-gray-700 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 px-3 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 transition shadow-theme-xs"
                                title="Start program"
                              >
                                <Icons.Play />
                                <span>{isBusy ? "Starting..." : "Start"}</span>
                              </button>
                            )}

                            <button
                              onClick={() => openLogs(tool.id)}
                              className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-100 text-xs font-medium transition"
                              title="Inspect live logs"
                            >
                              <Icons.Terminal />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          {/* ========================================================================= */}
          {/* TAB 2: GLOBAL CONFIGURATION                                               */}
          {/* ========================================================================= */}
          {activeTab === "global-config" && (
            <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-theme-xs max-w-3xl">
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900">Shared Netris Controller Settings</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Configure common Netris controller credentials and tenant defaults here. Once saved, these settings
                  are automatically pushed to all underlying demo tool configuration files.
                </p>
              </div>

              <form onSubmit={handleSaveGlobalConfig} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Netris Controller URL
                  </label>
                  <input
                    type="url"
                    required
                    value={globalConfig.netris_url}
                    onChange={(e) => setGlobalConfig({ ...globalConfig, netris_url: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm"
                    placeholder="https://adam-ctl.netris.io"
                  />
                  <span className="text-xs text-gray-400 mt-1 block">Full URL including https://</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Netris Admin Username
                    </label>
                    <input
                      type="text"
                      required
                      value={globalConfig.netris_username}
                      onChange={(e) => setGlobalConfig({ ...globalConfig, netris_username: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm"
                      placeholder="netris"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Netris Admin Password
                    </label>
                    <div className="relative">
                      <input
                        type={showPassword ? "text" : "password"}
                        value={globalConfig.netris_password}
                        onChange={(e) => setGlobalConfig({ ...globalConfig, netris_password: e.target.value })}
                        className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm pr-16"
                        placeholder="••••••••••••"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2 top-2.5 text-xs text-gray-500 hover:text-gray-800 px-2 py-0.5 rounded"
                      >
                        {showPassword ? "Hide" : "Show"}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Default Tenant Name
                    </label>
                    <input
                      type="text"
                      value={globalConfig.default_tenant}
                      onChange={(e) => setGlobalConfig({ ...globalConfig, default_tenant: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm"
                      placeholder="Demo / Meridian AI"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Default Site Name
                    </label>
                    <input
                      type="text"
                      value={globalConfig.default_site}
                      onChange={(e) => setGlobalConfig({ ...globalConfig, default_site: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm"
                      placeholder="SantaClara"
                    />
                  </div>
                </div>

                <div className="pt-2">
                  <label className="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={globalConfig.netris_verify_ssl}
                      onChange={(e) => setGlobalConfig({ ...globalConfig, netris_verify_ssl: e.target.checked })}
                      className="rounded border-gray-300 text-coral-600 focus:ring-coral-500 h-4 w-4"
                    />
                    <span>Verify SSL Certificates (Disable for self-signed development controllers)</span>
                  </label>
                </div>

                {/* Target Destination File List */}
                <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 text-xs text-gray-600 space-y-1.5 mt-4">
                  <span className="font-semibold text-gray-800 block mb-1">Propagation Targets:</span>
                  <div>&bull; <code className="font-mono text-gray-800">netris-prometheus-exporter/netris.var</code> and <code className="font-mono text-gray-800">.env</code></div>
                  <div>&bull; <code className="font-mono text-gray-800">netbox-netris/.env</code></div>
                  <div>&bull; <code className="font-mono text-gray-800">provider-portal/.env</code></div>
                  <div>&bull; <code className="font-mono text-gray-800">netris-slurm-cluster-sim/.env</code></div>
                </div>

                {/* Action Submit */}
                <div className="pt-4 flex items-center justify-end">
                  <button
                    type="submit"
                    disabled={configSaving}
                    className="bg-coral-600 hover:bg-coral-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold shadow-theme-xs transition"
                  >
                    {configSaving ? "Propagating..." : "Save & Propagate Everywhere"}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 3: TOOL CONFIGURATIONS                                                */}
          {/* ========================================================================= */}
          {activeTab === "tool-configs" && (
            <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-theme-xs max-w-4xl">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Per-Tool Configuration Files</h3>
                  <p className="text-sm text-gray-500 mt-0.5">
                    Directly inspect and modify environment files for individual tools.
                  </p>
                </div>

                {/* Tool Selector Dropdown */}
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium text-gray-700">Select Tool:</label>
                  <select
                    value={selectedToolConfigId}
                    onChange={(e) => setSelectedToolConfigId(e.target.value)}
                    className="px-3.5 py-2 rounded-lg border border-gray-300 text-sm font-medium bg-white focus:outline-none focus:ring-2 focus:ring-coral-500"
                  >
                    <option value="netris-prometheus-exporter">netris-prometheus-exporter (netris.var)</option>
                    <option value="netbox-netris">netbox-netris (.env)</option>
                    <option value="provider-portal">provider-portal (.env)</option>
                    <option value="netris-slurm-cluster-sim">netris-slurm-cluster-sim (.env)</option>
                  </select>
                </div>
              </div>

              {/* Code Editor */}
              <div className="relative">
                {toolConfigLoading ? (
                  <div className="h-96 flex items-center justify-center text-gray-400 text-sm">
                    Loading configuration...
                  </div>
                ) : (
                  <textarea
                    rows={16}
                    value={toolConfigContent}
                    onChange={(e) => setToolConfigContent(e.target.value)}
                    className="w-full font-mono text-xs bg-gray-900 text-gray-100 p-4 rounded-xl border border-gray-800 focus:outline-none focus:ring-2 focus:ring-coral-500 leading-relaxed resize-y"
                    spellCheck="false"
                  ></textarea>
                )}
              </div>

              <div className="mt-4 flex items-center justify-between">
                <span className="text-xs text-gray-400">Edits are saved directly to the respective file on disk.</span>
                <button
                  onClick={handleSaveToolRawConfig}
                  className="bg-coral-600 hover:bg-coral-700 text-white px-5 py-2 rounded-lg text-sm font-semibold shadow-theme-xs transition"
                >
                  Save Tool Config
                </button>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 4: PROCESS LOGS CONSOLE                                               */}
          {/* ========================================================================= */}
          {activeTab === "logs" && (
            <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-theme-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                <div className="flex items-center gap-3">
                  <h3 className="text-base font-semibold text-gray-900">Console Log Stream</h3>
                  <select
                    value={selectedToolLogs || ""}
                    onChange={(e) => openLogs(e.target.value)}
                    className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium bg-white focus:outline-none"
                  >
                    {tools.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-3 text-xs">
                  <label className="inline-flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoRefreshLogs}
                      onChange={(e) => setAutoRefreshLogs(e.target.checked)}
                      className="rounded border-gray-300 text-coral-600 focus:ring-coral-500 h-3.5 w-3.5"
                    />
                    <span>Auto-refresh (2s)</span>
                  </label>

                  <button
                    onClick={() => setLogContent([])}
                    className="px-2.5 py-1 rounded border border-gray-200 text-gray-600 hover:bg-gray-50"
                  >
                    Clear View
                  </button>
                </div>
              </div>

              {/* Terminal Screen */}
              <div className="bg-gray-950 text-emerald-400 p-5 rounded-xl font-mono text-xs overflow-auto max-h-[600px] min-h-[400px] border border-gray-900 shadow-inner">
                {logContent.length === 0 ? (
                  <div className="text-gray-600 italic">No output logged yet for this tool. Click Start to begin execution.</div>
                ) : (
                  logContent.map((line, idx) => (
                    <div key={idx} className="whitespace-pre-wrap leading-relaxed">
                      {line}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* --- Slide-Out Modal for Quick Log Inspection --- */}
      {selectedToolLogs && activeTab !== "logs" && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-theme-lg max-w-4xl w-full flex flex-col max-h-[85vh] overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h4 className="text-base font-semibold text-gray-900">
                  Logs: {tools.find((t) => t.id === selectedToolLogs)?.name || selectedToolLogs}
                </h4>
                <p className="text-xs text-gray-400">Live stdout / stderr ring buffer</p>
              </div>

              <div className="flex items-center gap-3">
                <label className="text-xs inline-flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoRefreshLogs}
                    onChange={(e) => setAutoRefreshLogs(e.target.checked)}
                    className="rounded text-coral-600"
                  />
                  <span>Auto-refresh</span>
                </label>
                <button
                  onClick={() => setSelectedToolLogs(null)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 text-lg font-bold"
                >
                  &times;
                </button>
              </div>
            </div>

            {/* Modal Body: Monospace Logs */}
            <div className="p-6 bg-gray-950 text-emerald-400 font-mono text-xs overflow-auto flex-1">
              {logContent.length === 0 ? (
                <div className="text-gray-600 italic">No logs recorded yet.</div>
              ) : (
                logContent.map((l, i) => (
                  <div key={i} className="whitespace-pre-wrap leading-relaxed">{l}</div>
                ))
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 flex justify-end">
              <button
                onClick={() => setSelectedToolLogs(null)}
                className="px-4 py-2 rounded-lg border border-gray-300 bg-white text-sm font-medium hover:bg-gray-50 text-gray-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Render React App
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
