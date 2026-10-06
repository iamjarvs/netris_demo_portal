import React, { useState, useEffect, useRef } from 'react';
import { 
  Rocket, 
  Play, 
  FileSearch, 
  CheckCircle2, 
  AlertOctagon, 
  Trash2, 
  RefreshCw, 
  Copy, 
  Check, 
  Square, 
  Terminal,
  ShieldAlert,
  ArrowRight,
  ArrowLeft,
  Server,
  Layers,
  Eraser,
  Unlock,
  Network,
  RotateCcw,
  ExternalLink,
  Database
} from 'lucide-react';

export default function DeployConsoleView({ config, initialWorkspaceSlug, onSelectWorkspace, onOpenHistory, onBack }) {
  const [status, setStatus] = useState('idle');
  const [currentAction, setCurrentAction] = useState(null);
  const [logs, setLogs] = useState([]);
  const [planSummary, setPlanSummary] = useState({ add: 0, change: 0, destroy: 0, has_plan: false });
  const [copied, setCopied] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  
  const [selectedSlug, setSelectedSlug] = useState(initialWorkspaceSlug || 'current');
  const [workspacesList, setWorkspacesList] = useState([]);

  // Modals
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [showDestroyModal, setShowDestroyModal] = useState(false);
  const [showPurgeModal, setShowPurgeModal] = useState(false);

  // State Inspection
  const [workspaceState, setWorkspaceState] = useState(null);
  const [refreshingState, setRefreshingState] = useState(false);
  const [arrangingMap, setArrangingMap] = useState(false);
  const [arrangeResult, setArrangeResult] = useState(null);

  const logsEndRef = useRef(null);
  const isRunning = status === 'running';

  // Sync initialWorkspaceSlug if changed externally
  useEffect(() => {
    if (initialWorkspaceSlug) {
      setSelectedSlug(initialWorkspaceSlug);
    }
  }, [initialWorkspaceSlug]);

  // Fetch available workspaces on disk
  const fetchWorkspaces = async () => {
    try {
      const res = await fetch('/api/deployments');
      const data = await res.json();
      if (data.success) {
        setWorkspacesList(data.deployments || []);
      }
    } catch (e) {
      console.error('Error fetching workspaces list', e);
    }
  };

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  // Validate selectedSlug against available workspaces
  const isValidWorkspace = selectedSlug !== 'current' && workspacesList.some((w) => w.slug === selectedSlug);
  const effectiveSlug = isValidWorkspace ? selectedSlug : 'current';
  const isCurrent = effectiveSlug === 'current';

  // Automatically reset selectedSlug to 'current' if the workspace was deleted
  useEffect(() => {
    if (selectedSlug !== 'current' && workspacesList.length > 0 && !workspacesList.some((w) => w.slug === selectedSlug)) {
      setSelectedSlug('current');
      if (onSelectWorkspace) onSelectWorkspace('current');
    }
  }, [workspacesList, selectedSlug, onSelectWorkspace]);

  const selectedDeployment = isValidWorkspace ? workspacesList.find((w) => w.slug === selectedSlug) : null;
  const activeSiteName = isCurrent ? config.site_name : (selectedDeployment?.site_name || config.site_name);
  const activeController = isCurrent ? config.controller_address : (selectedDeployment?.controller_address || config.controller_address);
  const activeSiteId = isCurrent ? config.site_id : (selectedDeployment?.site_id || config.site_id);

  // Fetch workspace state
  const fetchWorkspaceState = async () => {
    try {
      setRefreshingState(true);
      const body = isCurrent ? { config } : { slug: effectiveSlug };
      const res = await fetch('/api/deploy/state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setWorkspaceState(data);
    } catch (e) {
      console.error('Error fetching workspace state', e);
    } finally {
      setRefreshingState(false);
    }
  };

  // Poll logs and status
  useEffect(() => {
    let interval = null;
    const fetchLogs = async () => {
      try {
        const res = await fetch(`/api/deploy/logs?since=0`);
        const data = await res.json();
        setLogs(data.logs || []);
        setStatus(data.status);
        setCurrentAction(data.action);
        if (data.plan_summary) {
          setPlanSummary(data.plan_summary);
        }
      } catch (e) {
        console.error('Error polling deploy logs', e);
      }
    };

    fetchLogs();
    fetchWorkspaceState();

    if (isRunning) {
      interval = setInterval(fetchLogs, 500);
    } else {
      interval = setInterval(fetchLogs, 2500);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRunning, selectedSlug]);

  // Auto scroll
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleRun = async (action) => {
    try {
      setStatus('running');
      setCurrentAction(action);
      const payload = isCurrent ? { action, config } : { action, slug: effectiveSlug };
      const res = await fetch('/api/deploy/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!data.success) {
        setStatus('failed');
        setCurrentAction(null);
        alert(data.message);
      }
    } catch (e) {
      setStatus('failed');
      setCurrentAction(null);
      alert('Failed to trigger deployment: ' + e.message);
    }
  };

  const handleAbort = async () => {
    try {
      await fetch('/api/deploy/abort', { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  const handleResetState = async () => {
    try {
      const res = await fetch('/api/deploy/reset-state', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setStatus('idle');
        setCurrentAction(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handlePurgeLocal = async () => {
    try {
      const payload = isCurrent ? { config } : { slug: effectiveSlug };
      const res = await fetch('/api/deploy/purge-local', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        setShowPurgeModal(false);
        fetchWorkspaceState();
        fetchWorkspaces();
      } else {
        alert(data.message);
      }
    } catch (e) {
      alert('Error purging local state: ' + e.message);
    }
  };

  const handleCopyLogs = () => {
    navigator.clipboard.writeText(logs.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleArrangeTopology = async () => {
    try {
      setArrangingMap(true);
      setArrangeResult(null);
      const res = await fetch('/api/topology/arrange', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          site_id: activeSiteId,
          site_name: activeSiteName,
          controller_address: activeController,
          controller_login: config.controller_login,
          controller_password: config.controller_password,
        }),
      });
      const data = await res.json();
      setArrangeResult(data);
    } catch (e) {
      setArrangeResult({ success: false, message: e.message });
    } finally {
      setArrangingMap(false);
    }
  };

  const handleResetTopology = async () => {
    try {
      setArrangingMap(true);
      setArrangeResult(null);
      const res = await fetch('/api/topology/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          site_id: activeSiteId,
          site_name: activeSiteName,
          controller_address: activeController,
          controller_login: config.controller_login,
          controller_password: config.controller_password,
        }),
      });
      const data = await res.json();
      setArrangeResult(data);
    } catch (e) {
      setArrangeResult({ success: false, message: e.message });
    } finally {
      setArrangingMap(false);
    }
  };

  const resourceCount = workspaceState?.resource_count || 0;

  return (
    <div className="space-y-6">
      {/* 1. Deployment Pipeline Stepper Card */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-gray-100">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-gray-900">
                Live Deployment & Teardown Console (OpenTofu CLI)
              </h3>
              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                status === 'running'
                  ? 'bg-warning-50 text-warning-600 border border-warning-500/20 animate-pulse'
                  : status === 'success'
                  ? 'bg-success-50 text-success-600 border border-success-500/20'
                  : status === 'failed'
                  ? 'bg-error-50 text-error-600 border border-error-500/20'
                  : 'bg-gray-100 text-gray-600'
              }`}>
                {status.toUpperCase()}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              Execute Day-0 underlay, switches, links, and IPAM directly to your target Netris Controller
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-gray-100 text-gray-700 border border-gray-200 font-mono">
              Site: {activeSiteName}
            </span>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-coral-50 text-coral-700 border border-coral-200 font-mono">
              {activeController}
            </span>
          </div>
        </div>

        {/* Workspace Switcher Bar */}
        <div className="mt-4 p-3 rounded-xl bg-gray-50 border border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="text-xs font-semibold text-gray-600 shrink-0">
              Target Workspace:
            </span>
            <select
              value={effectiveSlug}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedSlug(val);
                if (onSelectWorkspace) onSelectWorkspace(val);
              }}
              className="text-xs font-semibold bg-white border border-gray-300 rounded-lg px-3 py-1.5 text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral-500 cursor-pointer shadow-2xs"
            >
              <option value="current">Current Designer Fabric ({config.site_name})</option>
              {workspacesList.length > 0 && (
                <optgroup label="Discovered Disk Deployments">
                  {workspacesList.map((w) => (
                    <option key={w.slug} value={w.slug}>
                      {w.site_name} ({w.slug}) — {w.has_active_resources ? `${w.total_instances} Live Resources` : w.status}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>

          {onOpenHistory && (
            <button
              onClick={onOpenHistory}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-coral-600 hover:text-coral-800 cursor-pointer transition"
            >
              <Database className="w-3.5 h-3.5" />
              <span>Fleet Manager & History</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Action Controls Bar */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5">
            {/* 1. Init */}
            <button
              onClick={() => handleRun('init')}
              disabled={isRunning}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium text-xs shadow-theme-xs transition disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-gray-500 ${isRunning && currentAction === 'init' ? 'animate-spin text-coral-600' : ''}`} />
              <span>1. Init</span>
            </button>

            {/* 2. Plan */}
            <button
              onClick={() => handleRun('plan')}
              disabled={isRunning}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-gray-800 font-semibold text-xs shadow-theme-xs transition disabled:opacity-50 cursor-pointer"
            >
              <FileSearch className={`w-3.5 h-3.5 text-coral-600 ${isRunning && currentAction === 'plan' ? 'animate-spin' : ''}`} />
              <span>2. Run Plan (Dry-Run)</span>
            </button>

            {/* 3. Apply */}
            <button
              onClick={() => setShowApplyModal(true)}
              disabled={isRunning}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-coral-600 hover:bg-coral-700 text-white font-semibold text-xs shadow-theme-xs transition disabled:opacity-50 cursor-pointer"
            >
              <Rocket className="w-3.5 h-3.5" />
              <span>3. Apply to Controller</span>
            </button>

            {/* 4. Reset to Netris Native Auto-Layout */}
            <button
              onClick={handleResetTopology}
              disabled={isRunning || arrangingMap}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 text-xs font-semibold shadow-theme-xs transition disabled:opacity-50 cursor-pointer"
              title="Reset all fixed coordinates so Netris Controller dynamically arranges nodes using native grouping and physics"
            >
              <RotateCcw className={`w-3.5 h-3.5 text-emerald-600 ${arrangingMap ? 'animate-spin' : ''}`} />
              <span>Reset to Native Layout</span>
            </button>

            {/* 5. Spacious Multi-Plane Grid Layout */}
            <button
              onClick={handleArrangeTopology}
              disabled={isRunning || arrangingMap}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 text-xs font-semibold shadow-theme-xs transition disabled:opacity-50 cursor-pointer"
              title="Arrange nodes into a wide hierarchical tier grid with 550px+ spacing"
            >
              <Network className={`w-3.5 h-3.5 text-purple-600 ${arrangingMap ? 'animate-spin' : ''}`} />
              <span>Spacious Grid Layout</span>
            </button>

            {/* Abort button */}
            {isRunning && (
              <button
                onClick={handleAbort}
                className="inline-flex items-center gap-1 px-3 py-2 rounded-lg bg-error-50 text-error-600 border border-error-500/20 hover:bg-error-100 font-semibold text-xs transition cursor-pointer"
              >
                <Square className="w-3 h-3" />
                <span>Abort</span>
              </button>
            )}

            {/* Reset Deployer State button */}
            <button
              onClick={handleResetState}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-200 font-semibold text-xs transition cursor-pointer"
              title="Reset deployment console state to idle if a step gets stuck"
            >
              <RotateCcw className="w-3.5 h-3.5 text-gray-500" />
              <span>Reset State</span>
            </button>
          </div>

          {/* Teardown & Reset Trigger */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowDestroyModal(true)}
              disabled={isRunning}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-error-50 hover:bg-error-100 text-error-700 border border-error-500/20 text-xs font-semibold shadow-theme-xs transition disabled:opacity-50 cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5 text-error-600" />
              <span>Destroy / Cleanup Deployment</span>
            </button>
          </div>
        </div>

        {/* Topology Layout Feedback Banner */}
        {arrangeResult && (
          <div className={`mt-4 p-3.5 rounded-xl border flex items-center justify-between text-xs transition ${
            !arrangeResult.success
              ? 'bg-error-50 border-error-200 text-error-800'
              : arrangeResult.message?.includes('reset')
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-purple-50 border-purple-200 text-purple-900'
          }`}>
            <div className="flex items-center gap-2.5">
              {arrangeResult.success ? (
                <CheckCircle2 className={`w-4 h-4 shrink-0 ${arrangeResult.message?.includes('reset') ? 'text-emerald-600' : 'text-purple-600'}`} />
              ) : (
                <AlertOctagon className="w-4 h-4 text-error-600 shrink-0" />
              )}
              <span className="font-medium">{arrangeResult.message}</span>
            </div>
            {arrangeResult.success && (
              <a 
                href={`${config.controller_address || 'https://adam-ctl.netris.io'}/topology`} 
                target="_blank" 
                rel="noreferrer"
                className={`inline-flex items-center gap-1 font-bold hover:underline shrink-0 ${
                  arrangeResult.message?.includes('reset') ? 'text-emerald-700 hover:text-emerald-900' : 'text-purple-700 hover:text-purple-900'
                }`}
              >
                <span>Open Controller Map</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        )}

        {/* Plan Diff Summary Badge */}
        {planSummary.has_plan && (
          <div className="mt-4 p-3.5 rounded-xl bg-gray-50 border border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-gray-700">Latest Plan Calculation:</span>
              <span className="px-2 py-0.5 rounded text-xs font-bold bg-success-50 text-success-600 border border-success-500/20">
                +{planSummary.add} to add
              </span>
              <span className="px-2 py-0.5 rounded text-xs font-bold bg-warning-50 text-warning-600 border border-warning-500/20">
                ~{planSummary.change} to change
              </span>
              <span className="px-2 py-0.5 rounded text-xs font-bold bg-error-50 text-error-600 border border-error-500/20">
                -{planSummary.destroy} to destroy
              </span>
            </div>
            <span className="text-[11px] text-gray-400 font-mono">tofu.tfplan ready</span>
          </div>
        )}
      </div>

      {/* 2. State & Cleanup Status Card */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-100">
          <div>
            <h4 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <Layers className="w-4 h-4 text-coral-500" />
              <span>Workspace State & Recovery Center</span>
            </h4>
            <p className="text-xs text-gray-500 mt-0.5">
              Inspects OpenTofu state to detect successfully deployed or partially created resources
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchWorkspaceState}
              disabled={refreshingState}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-medium transition cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-gray-500 ${refreshingState ? 'animate-spin' : ''}`} />
              <span>Refresh State</span>
            </button>

            <button
              onClick={() => setShowPurgeModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-medium transition cursor-pointer"
            >
              <Eraser className="w-3.5 h-3.5 text-gray-500" />
              <span>Reset Local Workspace</span>
            </button>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3 rounded-xl bg-gray-50 border border-gray-200">
            <div className="text-[11px] font-medium text-gray-500">Live Resources in State</div>
            <div className="text-base font-bold text-gray-900 mt-0.5">
              {resourceCount > 0 ? (
                <span className="text-coral-700">{resourceCount} Resources Tracked</span>
              ) : (
                <span className="text-gray-500">0 (Clean)</span>
              )}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-gray-50 border border-gray-200">
            <div className="text-[11px] font-medium text-gray-500">State File Status</div>
            <div className="text-base font-bold text-gray-900 mt-0.5">
              {workspaceState?.has_state ? (
                <span className="text-success-600 text-xs font-semibold">terraform.tfstate Active</span>
              ) : (
                <span className="text-gray-400 text-xs font-semibold">No State File</span>
              )}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-gray-50 border border-gray-200">
            <div className="text-[11px] font-medium text-gray-500">Lock File Status</div>
            <div className="text-base font-bold text-gray-900 mt-0.5">
              {workspaceState?.is_locked ? (
                <span className="text-error-600 text-xs font-semibold">Workspace Locked</span>
              ) : (
                <span className="text-success-600 text-xs font-semibold">Unlocked / Ready</span>
              )}
            </div>
          </div>
        </div>

        {resourceCount > 0 && (
          <div className="mt-4 p-3 rounded-xl bg-coral-25 border border-coral-200 text-xs text-coral-900 flex items-center justify-between">
            <div>
              <strong>Active Deployment Detected:</strong> {resourceCount} resources are currently recorded in OpenTofu state. If an apply failed midway, clicking <strong>"Destroy / Cleanup Deployment"</strong> will tear down all partially created resources.
            </div>
            <button
              onClick={() => setShowDestroyModal(true)}
              className="ml-3 shrink-0 px-3 py-1.5 rounded-lg bg-coral-600 hover:bg-coral-700 text-white font-semibold text-xs shadow-xs cursor-pointer"
            >
              Run Cleanup Now
            </button>
          </div>
        )}
      </div>

      {/* 3. Interactive Terminal Window */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs overflow-hidden">
        <div className="h-11 px-5 border-b border-gray-200 bg-gray-50/70 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-gray-700">
            <Terminal className="w-4 h-4 text-coral-600" />
            <span>Console Stream</span>
            <span className="text-[11px] text-gray-400 font-normal">({logs.length} lines)</span>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-gray-300 text-coral-600 focus:ring-coral-500/20"
              />
              <span>Auto-scroll</span>
            </label>

            <button
              onClick={handleCopyLogs}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-white border border-gray-300 hover:bg-gray-50 text-gray-600 text-xs font-medium transition cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-success-600" />
                  <span className="text-success-600">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3 text-gray-400" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Terminal Stream */}
        <div className="bg-gray-950 p-4 h-[440px] overflow-y-auto font-mono text-xs text-gray-100 space-y-0.5 leading-relaxed">
          {logs.length === 0 ? (
            <div className="text-gray-500 italic">No output yet. Click "1. Init" or "2. Run Plan" to begin.</div>
          ) : (
            logs.map((line, idx) => {
              const isHeader = line.startsWith('===') || line.startsWith('$');
              const isError = line.toLowerCase().includes('error:') || line.includes('Error:');
              const isSuccess = line.startsWith('✓') || line.includes('Success!') || line.includes('Apply complete') || line.includes('Destroy complete');
              const isPlan = line.includes('Plan:');

              return (
                <div
                  key={idx}
                  className={`${
                    isHeader
                      ? 'text-coral-300 font-semibold'
                      : isError
                      ? 'text-error-400 font-semibold'
                      : isSuccess
                      ? 'text-success-400 font-semibold'
                      : isPlan
                      ? 'text-amber-300 font-bold'
                      : 'text-gray-300'
                  }`}
                >
                  {line}
                </div>
              );
            })
          )}
          <div ref={logsEndRef} />
        </div>
      </div>

      {/* Confirmation Modal for Apply */}
      {showApplyModal && (
        <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-theme-xl border border-gray-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="w-10 h-10 rounded-xl bg-coral-50 border border-coral-200 flex items-center justify-center text-coral-600 mb-4">
              <Rocket className="w-5 h-5" />
            </div>
            
            <h4 className="text-base font-bold text-gray-900">Confirm Live Deployment</h4>
            <p className="text-xs text-gray-600 mt-2 leading-relaxed">
              You are about to execute <strong>tofu apply</strong> against the Netris Controller:
            </p>

            <div className="my-4 p-3 rounded-xl bg-gray-50 border border-gray-200 text-xs font-mono space-y-1">
              <div>Controller: <strong>{config.controller_address}</strong></div>
              <div>Site Name: <strong>{config.site_name}</strong></div>
              <div>Planes: <strong>{config.planes_count}</strong></div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowApplyModal(false)}
                className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowApplyModal(false);
                  handleRun('apply');
                }}
                className="px-4 py-2 rounded-lg bg-coral-600 hover:bg-coral-700 text-white text-xs font-semibold shadow-theme-xs cursor-pointer"
              >
                Confirm & Apply
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Destroy / Cleanup */}
      {showDestroyModal && (
        <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-theme-xl border border-gray-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="w-10 h-10 rounded-xl bg-error-50 border border-error-200 flex items-center justify-center text-error-600 mb-4">
              <Trash2 className="w-5 h-5" />
            </div>
            
            <h4 className="text-base font-bold text-gray-900">Teardown / Cleanup Deployment</h4>
            <p className="text-xs text-gray-600 mt-2 leading-relaxed">
              This will run <strong>tofu destroy -auto-approve</strong> against the Netris Controller.
            </p>

            <div className="my-3 p-3 rounded-xl bg-error-50/50 border border-error-500/20 text-xs text-error-800 space-y-1">
              <div>Site: <strong>{config.site_name}</strong></div>
              <div>Resources in state: <strong>{resourceCount}</strong></div>
              <p className="mt-1 text-[11px]">
                OpenTofu will locate any successful or partially created switches, subnets, allocations, and site objects and delete them in reverse order.
              </p>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowDestroyModal(false)}
                className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowDestroyModal(false);
                  handleRun('destroy');
                }}
                className="px-4 py-2 rounded-lg bg-error-600 hover:bg-error-700 text-white text-xs font-semibold shadow-theme-xs cursor-pointer"
              >
                Destroy & Cleanup
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Local Workspace Modal */}
      {showPurgeModal && (
        <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-theme-xl border border-gray-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="w-10 h-10 rounded-xl bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-600 mb-4">
              <Eraser className="w-5 h-5" />
            </div>
            
            <h4 className="text-base font-bold text-gray-900">Reset Local Workspace</h4>
            <p className="text-xs text-gray-600 mt-2 leading-relaxed">
              This clears local <strong>terraform.tfstate</strong>, plans, and lock files for site <strong>{config.site_name}</strong>.
            </p>
            <p className="text-[11px] text-gray-500 mt-2">
              Note: This does not delete objects from the Netris Controller; use "Destroy / Cleanup Deployment" if you want OpenTofu to delete them from the controller first.
            </p>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowPurgeModal(false)}
                className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handlePurgeLocal}
                className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-900 text-white text-xs font-semibold shadow-theme-xs cursor-pointer"
              >
                Reset Local State
              </button>
            </div>
          </div>
        </div>
      )}
    
      {/* Sticky Bottom Bar with Back & View History navigation */}
      <div className="fixed bottom-0 left-[290px] right-0 bg-white/95 backdrop-blur border-t border-gray-200 px-8 py-3.5 flex items-center justify-between z-20 shadow-theme-md">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-300 hover:bg-gray-100 text-gray-700 text-sm font-semibold transition cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4 stroke-[2.5]" />
          <span>Back to Terraform Export</span>
        </button>

        <button
          onClick={onOpenHistory}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-coral-600 hover:bg-coral-700 text-white text-sm font-bold shadow-theme-xs transition cursor-pointer"
        >
          <Database className="w-4 h-4" />
          <span>View Deployments & History</span>
          <ArrowRight className="w-4 h-4 stroke-[2.5]" />
        </button>
      </div>
    </div>
  );
}