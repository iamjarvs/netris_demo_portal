import React, { useState, useEffect } from 'react';
import {
  Server,
  Trash2,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Activity,
  Database,
  ExternalLink,
  Eye,
  ChevronDown,
  ChevronUp,
  Layers,
  Network,
  ArrowRight,
  ArrowLeft,
  ShieldAlert,
  Terminal,
  Eraser,
  Rocket
} from 'lucide-react';

export default function DeploymentHistoryView({ onSelectWorkspace, onOpenConsole, onBack }) {
  const [deployments, setDeployments] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('fleet'); // 'fleet' or 'history'
  
  // Modals
  const [inspectTarget, setInspectTarget] = useState(null);
  const [destroyTarget, setDestroyTarget] = useState(null);
  const [destroying, setDestroying] = useState(false);
  const [purgeTarget, setPurgeTarget] = useState(null);
  const [expandedLogId, setExpandedLogId] = useState(null);

  // Fetch Deployments & History
  const fetchData = async () => {
    try {
      setLoading(true);
      const [depsRes, histRes] = await Promise.all([
        fetch('/api/deployments'),
        fetch('/api/deployments/history')
      ]);
      const depsData = await depsRes.json();
      const histData = await histRes.json();
      if (depsData.success) {
        setDeployments(depsData.deployments || []);
      }
      if (histData.success) {
        setHistory(histData.history || []);
      }
    } catch (e) {
      console.error('Failed to fetch deployment data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Execute Destroy on a target deployment
  const handleConfirmDestroy = async () => {
    if (!destroyTarget) return;
    try {
      setDestroying(true);
      const res = await fetch(`/api/deployments/${destroyTarget.slug}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'destroy' }),
      });
      const data = await res.json();
      if (data.success) {
        setDestroyTarget(null);
        // Switch to deploy console to watch real-time stream
        if (onOpenConsole) {
          onOpenConsole(destroyTarget.slug);
        }
      } else {
        alert('Failed to trigger destroy: ' + (data.message || 'Unknown error'));
      }
    } catch (e) {
      alert('Error triggering destroy: ' + e.message);
    } finally {
      setDestroying(false);
    }
  };

  // Execute Purge Local State
  const handleConfirmPurge = async () => {
    if (!purgeTarget) return;
    try {
      const res = await fetch(`/api/deployments/${purgeTarget.slug}/purge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      if (data.success) {
        setPurgeTarget(null);
        await fetchData();
      } else {
        alert('Failed to purge state: ' + (data.message || 'Unknown error'));
      }
    } catch (e) {
      alert('Error purging state: ' + e.message);
    }
  };

  // Delete Empty Workspace
  const handleDeleteWorkspace = async (slug) => {
    if (!window.confirm(`Are you sure you want to permanently delete the workspace directory for '${slug}'?`)) {
      return;
    }
    try {
      const res = await fetch(`/api/deployments/${slug}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        await fetchData();
      } else {
        alert('Cannot delete: ' + data.message);
      }
    } catch (e) {
      alert('Error deleting workspace: ' + e.message);
    }
  };

  const activeDeployments = deployments.filter((d) => d.has_active_resources);
  const totalLiveResources = deployments.reduce((acc, d) => acc + (d.total_instances || 0), 0);

  return (
    <div className="space-y-6">
      {/* 1. Header & Summary Metric Cards */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900 tracking-tight flex items-center gap-2.5">
            <Database className="w-6 h-6 text-coral-600" />
            <span>Deployment Fleet & Audit History</span>
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Manage active fabrics, inspect state resources, track operations, and safely destroy legacy deployments
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 text-xs font-semibold shadow-theme-xs transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-coral-600' : 'text-gray-500'}`} />
            <span>Refresh Fleet</span>
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-white border border-gray-200 shadow-theme-xs flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-gray-500">Live Active Fabrics</span>
            <div className="text-2xl font-bold text-gray-900 mt-0.5">{activeDeployments.length}</div>
            <span className="text-[11px] text-gray-400">Deployed to Netris Controller</span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Activity className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white border border-gray-200 shadow-theme-xs flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-gray-500">Total Managed Instances</span>
            <div className="text-2xl font-bold text-coral-600 mt-0.5">{totalLiveResources}</div>
            <span className="text-[11px] text-gray-400">Switches, servers, links & subnets</span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-coral-50 text-coral-600 flex items-center justify-center">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white border border-gray-200 shadow-theme-xs flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-gray-500">Workspace History Count</span>
            <div className="text-2xl font-bold text-gray-900 mt-0.5">{deployments.length}</div>
            <span className="text-[11px] text-gray-400">Saved site directories on disk</span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* 2. Tabs Switcher */}
      <div className="flex border-b border-gray-200 gap-6">
        <button
          onClick={() => setActiveTab('fleet')}
          className={`pb-3 text-sm font-semibold border-b-2 transition cursor-pointer flex items-center gap-2 ${
            activeTab === 'fleet'
              ? 'border-coral-600 text-coral-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Server className="w-4 h-4" />
          <span>Deployments Fleet ({deployments.length})</span>
          {activeDeployments.length > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
              {activeDeployments.length} Live
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`pb-3 text-sm font-semibold border-b-2 transition cursor-pointer flex items-center gap-2 ${
            activeTab === 'history'
              ? 'border-coral-600 text-coral-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Audit History Trail ({history.length})</span>
        </button>
      </div>

      {/* TAB 1: FLEET OVERVIEW */}
      {activeTab === 'fleet' && (
        <div className="space-y-4">
          {deployments.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-white border border-gray-200">
              <Server className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm font-semibold text-gray-700">No deployment workspaces found</p>
              <p className="text-xs text-gray-400 mt-1">
                Generate and deploy a topology to see it appear in your fleet.
              </p>
            </div>
          ) : (
            deployments.map((dep) => {
              const isLive = dep.has_active_resources;
              const peakCount = dep.backup_instances || dep.total_instances || 0;
              const breakdown = dep.breakdown || {};

              return (
                <div
                  key={dep.slug}
                  className={`rounded-2xl border bg-white p-5 shadow-theme-xs transition ${
                    isLive ? 'border-emerald-300 ring-1 ring-emerald-200' : 'border-gray-200'
                  }`}
                >
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    {/* Left: Site Info */}
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2.5">
                        <h3 className="text-base font-bold text-gray-900">{dep.site_name}</h3>
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                          {dep.slug}
                        </span>

                        {isLive ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-300 animate-pulse">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>LIVE: {dep.total_instances} Resources</span>
                          </span>
                        ) : dep.status === 'destroyed' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 border border-gray-200">
                            <span>Cleaned Up (Peak: {peakCount})</span>
                          </span>
                        ) : dep.status === 'planned' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                            <span>Plan Generated</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                            <span>Configured</span>
                          </span>
                        )}

                        {dep.is_locked && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-error-50 text-error-700 border border-error-200">
                            <span>Locked</span>
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Network className="w-3.5 h-3.5 text-gray-400" />
                          <span className="font-mono text-gray-700">{dep.controller_address}</span>
                        </span>
                        <span>•</span>
                        <span>Last modified: <strong className="text-gray-700">{dep.last_modified}</strong></span>
                        {dep.serial > 0 && (
                          <>
                            <span>•</span>
                            <span>State Serial: <strong>{dep.serial}</strong></span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Right: Actions Bar */}
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Inspect Resources */}
                      <button
                        onClick={() => setInspectTarget(dep)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold shadow-theme-xs transition cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5 text-gray-500" />
                        <span>Inspect State ({isLive ? dep.total_instances : peakCount})</span>
                      </button>

                      {/* Open in Deploy Console */}
                      <button
                        onClick={() => {
                          if (onOpenConsole) onOpenConsole(dep.slug);
                        }}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-coral-50 hover:bg-coral-100 text-coral-700 border border-coral-200 text-xs font-semibold shadow-theme-xs transition cursor-pointer"
                        title="Open this deployment in the live console"
                      >
                        <Terminal className="w-3.5 h-3.5 text-coral-600" />
                        <span>Open Console</span>
                      </button>

                      {/* Destroy Deployment Button */}
                      <button
                        onClick={() => setDestroyTarget(dep)}
                        className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-theme-xs transition cursor-pointer ${
                          isLive
                            ? 'bg-error-600 hover:bg-error-700 text-white'
                            : 'bg-error-50 hover:bg-error-100 text-error-700 border border-error-200'
                        }`}
                        title="Run OpenTofu destroy to tear down all resources from Netris"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Destroy Deployment</span>
                      </button>

                      {/* Purge Local State */}
                      <button
                        onClick={() => setPurgeTarget(dep)}
                        className="p-1.5 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-gray-500 hover:text-gray-700 transition cursor-pointer"
                        title="Purge local terraform.tfstate and lock files"
                      >
                        <Eraser className="w-4 h-4" />
                      </button>

                      {/* Delete Workspace Directory if empty */}
                      {!isLive && (
                        <button
                          onClick={() => handleDeleteWorkspace(dep.slug)}
                          className="p-1.5 rounded-lg bg-white border border-gray-300 hover:bg-error-50 text-gray-400 hover:text-error-600 transition cursor-pointer"
                          title="Delete empty workspace directory from disk"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Resource Breakdown Pills */}
                  {Object.keys(breakdown).length > 0 && (
                    <div className="mt-3.5 pt-3.5 border-t border-gray-100 flex flex-wrap items-center gap-1.5">
                      <span className="text-[11px] font-semibold text-gray-400 mr-1">Inventory:</span>
                      {breakdown.netris_switch && (
                        <span className="px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 border border-purple-200 text-[11px] font-medium">
                          {breakdown.netris_switch} Switches
                        </span>
                      )}
                      {breakdown.netris_server && (
                        <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200 text-[11px] font-medium">
                          {breakdown.netris_server} Servers
                        </span>
                      )}
                      {breakdown.netris_softgate && (
                        <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-medium">
                          {breakdown.netris_softgate} SoftGates
                        </span>
                      )}
                      {breakdown.netris_link && (
                        <span className="px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 text-[11px] font-medium">
                          {breakdown.netris_link} Links
                        </span>
                      )}
                      {breakdown.netris_vpc && (
                        <span className="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200 text-[11px] font-medium">
                          {breakdown.netris_vpc} VPCs
                        </span>
                      )}
                      {breakdown.netris_subnet && (
                        <span className="px-2 py-0.5 rounded-md bg-gray-100 text-gray-700 border border-gray-200 text-[11px] font-medium">
                          {breakdown.netris_subnet} Subnets
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* TAB 2: AUDIT HISTORY TIMELINE */}
      {activeTab === 'history' && (
        <div className="space-y-3">
          {history.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-white border border-gray-200">
              <Clock className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm font-semibold text-gray-700">No deployment actions recorded yet</p>
              <p className="text-xs text-gray-400 mt-1">
                Operations like Init, Plan, Apply, and Destroy will be permanently logged here.
              </p>
            </div>
          ) : (
            history.map((item) => {
              const isSuccess = item.status === 'success';
              const isExpanded = expandedLogId === item.id;
              const dateFormatted = new Date(item.timestamp).toLocaleString();

              return (
                <div
                  key={item.id}
                  className="rounded-xl border border-gray-200 bg-white p-4 shadow-theme-xs space-y-2.5"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase ${
                        item.action === 'apply'
                          ? 'bg-coral-50 text-coral-700 border border-coral-200'
                          : item.action === 'destroy'
                          ? 'bg-error-50 text-error-700 border border-error-200'
                          : item.action === 'plan'
                          ? 'bg-blue-50 text-blue-700 border border-blue-200'
                          : 'bg-gray-100 text-gray-700 border border-gray-200'
                      }`}>
                        tofu {item.action}
                      </span>

                      <span className="text-sm font-bold text-gray-900">{item.site_name}</span>
                      <span className="text-xs font-mono text-gray-400">({item.site_slug})</span>

                      <span className={`px-2 py-0.2 rounded text-[11px] font-semibold ${
                        isSuccess
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-error-50 text-error-700'
                      }`}>
                        {item.status} (exit {item.exit_code ?? 0})
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span>Duration: <strong>{item.duration_seconds}s</strong></span>
                      <span>•</span>
                      <span>{dateFormatted}</span>
                      {item.log_snippet && (
                        <button
                          onClick={() => setExpandedLogId(isExpanded ? null : item.id)}
                          className="text-coral-600 hover:text-coral-800 font-medium inline-flex items-center gap-0.5 cursor-pointer ml-1"
                        >
                          <span>{isExpanded ? 'Hide Log' : 'View Log'}</span>
                          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Plan Summary Badge if applicable */}
                  {item.plan_summary?.has_plan && (
                    <div className="text-xs flex items-center gap-2 text-gray-600 bg-gray-50 p-2 rounded-lg border border-gray-100">
                      <span className="font-semibold">Calculated Plan:</span>
                      <span className="text-emerald-600 font-bold">+{item.plan_summary.add} add</span>
                      <span className="text-amber-600 font-bold">~{item.plan_summary.change} change</span>
                      <span className="text-error-600 font-bold">-{item.plan_summary.destroy} destroy</span>
                    </div>
                  )}

                  {/* Expandable Log Snippet */}
                  {isExpanded && item.log_snippet && (
                    <div className="mt-2 p-3 rounded-lg bg-gray-950 text-gray-200 font-mono text-xs overflow-x-auto border border-gray-800 leading-relaxed">
                      <pre>{item.log_snippet}</pre>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* 3. CONFIRM DESTROY MODAL */}
      {destroyTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-200 space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-error-50 text-error-600 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-gray-900">
                  Confirm Destroy: {destroyTarget.site_name}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Are you sure you want to trigger a full OpenTofu destroy on this site?
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-error-50/60 border border-error-200 text-xs text-error-900 space-y-1.5">
              <p className="font-semibold">Destructive Action Warning:</p>
              <ul className="list-disc list-inside space-y-1 text-error-800">
                <li>Target: <strong>{destroyTarget.slug}</strong></li>
                <li>Controller: <strong>{destroyTarget.controller_address}</strong></li>
                <li>Live Instances: <strong>{destroyTarget.total_instances}</strong></li>
              </ul>
              <p className="text-[11px] text-error-700 pt-1">
                OpenTofu will execute <code>tofu destroy -auto-approve</code> against the controller to remove all switches, links, and IPAM subnets for this site.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setDestroyTarget(null)}
                disabled={destroying}
                className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDestroy}
                disabled={destroying}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-error-600 hover:bg-error-700 text-white text-xs font-semibold shadow-theme-xs transition cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{destroying ? 'Starting Destroy...' : 'Confirm & Destroy Deployment'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. INSPECT RESOURCES MODAL */}
      {inspectTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-gray-200">
            {/* Modal Header */}
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  <Eye className="w-4 h-4 text-coral-600" />
                  <span>State Inventory: {inspectTarget.site_name}</span>
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Showing tracked resources from <code>terraform.tfstate</code>
                </p>
              </div>
              <button
                onClick={() => setInspectTarget(null)}
                className="text-gray-400 hover:text-gray-600 text-sm font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-5 overflow-y-auto flex-1 space-y-3">
              {inspectTarget.resource_details?.length === 0 ? (
                <p className="text-xs text-gray-500 text-center py-6">No resources found in state.</p>
              ) : (
                <div className="border border-gray-200 rounded-xl overflow-hidden">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200 text-gray-500 font-semibold uppercase text-[10px]">
                        <th className="py-2.5 px-3">Resource Type</th>
                        <th className="py-2.5 px-3">Name</th>
                        <th className="py-2.5 px-3">Mode</th>
                        <th className="py-2.5 px-3 text-right">Instances</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 font-mono">
                      {inspectTarget.resource_details.map((r, i) => (
                        <tr key={i} className="hover:bg-gray-50/60">
                          <td className="py-2 px-3 text-coral-700 font-medium">{r.type}</td>
                          <td className="py-2 px-3 text-gray-800">{r.name}</td>
                          <td className="py-2 px-3 text-gray-500 text-[11px]">{r.mode}</td>
                          <td className="py-2 px-3 text-right font-bold text-gray-900">{r.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-gray-100 flex items-center justify-between bg-gray-50 rounded-b-2xl">
              <span className="text-xs text-gray-500">
                Total Instances: <strong className="text-gray-900">{inspectTarget.total_instances || inspectTarget.backup_instances}</strong>
              </span>
              <button
                onClick={() => setInspectTarget(null)}
                className="px-4 py-1.5 rounded-lg bg-white border border-gray-300 text-gray-700 hover:bg-gray-100 text-xs font-semibold cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. PURGE CONFIRM MODAL */}
      {purgeTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-5 shadow-2xl border border-gray-200 space-y-3">
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <Eraser className="w-4 h-4 text-amber-600" />
              <span>Purge Workspace State?</span>
            </h3>
            <p className="text-xs text-gray-500">
              This will remove <code>terraform.tfstate</code> and any lock files for <strong>{purgeTarget.site_name}</strong>. OpenTofu will forget these resources.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setPurgeTarget(null)}
                className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmPurge}
                className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold cursor-pointer"
              >
                Confirm Purge
              </button>
            </div>
          </div>
        </div>
      )}
    
      {/* Sticky Bottom Bar with Back to Deploy Console */}
      <div className="fixed bottom-0 left-[290px] right-0 bg-white/95 backdrop-blur border-t border-gray-200 px-8 py-3.5 flex items-center justify-between z-20 shadow-theme-md">
        <button
          onClick={onBack || (() => onOpenConsole?.('current'))}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-300 hover:bg-gray-100 text-gray-700 text-sm font-semibold transition cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4 stroke-[2.5]" />
          <span>Back to Deploy Console</span>
        </button>

        <div className="text-xs text-gray-500 font-medium">
          Fleet Manager & Multi-Site Teardown
        </div>
      </div>
    </div>
  );
}