import React from 'react';
import { 
  Download, 
  ShieldCheck, 
  ShieldAlert, 
  RefreshCw, 
  Server,
  Layers,
  Sparkles,
  FolderKanban,
  Save,
  Plus
} from 'lucide-react';

export default function Header({ 
  siteName, 
  planesCount, 
  activeDesignName,
  savedDesignsCount = 0,
  onCreateNew,
  onOpenDesignsModal,
  conflictReport, 
  onRunCheck, 
  checkingConflicts,
  onDownloadZip,
  downloading,
  setActiveTab 
}) {
  const criticals = conflictReport?.critical_count || 0;
  const warnings = conflictReport?.warning_count || 0;
  const hasRun = conflictReport !== null;
  const passed = hasRun && criticals === 0;

  return (
    <header className="sticky top-0 z-20 min-h-[68px] bg-white border-b border-gray-200 px-6 py-2.5 flex items-center justify-between gap-4 shadow-theme-xs">
      {/* Breadcrumb / Title Area */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-xs text-gray-500 font-medium whitespace-nowrap">
            <span>Fabric Workspace</span>
            <span className="text-gray-300">/</span>
            <span className="text-gray-700 font-semibold">{siteName || 'Site Configuration'}</span>
            <span className="text-gray-300">/</span>
            {activeDesignName ? (
              <span className="inline-flex items-center gap-1 text-coral-700 font-semibold bg-coral-50 px-2 py-0.5 rounded-md text-[11px] border border-coral-200 whitespace-nowrap">
                <FolderKanban className="w-3 h-3 text-coral-600 shrink-0" />
                <span className="max-w-[150px] sm:max-w-[220px] truncate">{activeDesignName}</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-gray-600 font-medium bg-gray-100 px-2 py-0.5 rounded-md text-[11px] border border-gray-200 whitespace-nowrap">
                <Sparkles className="w-3 h-3 text-amber-500 shrink-0" />
                <span>New Design</span>
              </span>
            )}
          </div>
          <h2 className="text-lg font-bold text-gray-900 truncate leading-tight mt-0.5">
            {activeDesignName ? activeDesignName : `${siteName || 'Multi-Plane'} Fabric Architecture`}
          </h2>
        </div>

        {/* Informational Status Pills (Hidden on narrower screens to prevent crowding) */}
        <div className="hidden 2xl:flex items-center gap-2 ml-2 pl-3 border-l border-gray-200 shrink-0">
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-coral-50 text-coral-700 border border-coral-200 whitespace-nowrap">
            <Layers className="w-3.5 h-3.5" />
            {planesCount} {planesCount === 1 ? 'Plane' : 'Planes'}
          </span>
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700 border border-gray-200 whitespace-nowrap">
            <Server className="w-3.5 h-3.5 text-gray-500" />
            Site: {siteName}
          </span>
        </div>
      </div>

      {/* Action Buttons Toolbar */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Create New Button */}
        <button
          onClick={onCreateNew}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 hover:border-gray-400 text-gray-700 text-xs font-semibold shadow-theme-xs transition cursor-pointer whitespace-nowrap"
          title="Create New Fabric Design"
        >
          <Plus className="w-3.5 h-3.5 text-coral-600" />
          <span>Create New</span>
        </button>

        {/* Saved Designs Library Button */}
        <button
          onClick={() => onOpenDesignsModal('open')}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold shadow-theme-xs transition cursor-pointer whitespace-nowrap"
          title="Open Saved Fabric Designs"
        >
          <FolderKanban className="w-3.5 h-3.5 text-coral-600" />
          <span className="hidden sm:inline">Designs</span>
          <span className="px-1.5 py-0.2 rounded-full bg-gray-100 text-[10px] font-bold text-gray-600 border border-gray-200">
            {savedDesignsCount}
          </span>
        </button>

        {/* Save As Button */}
        <button
          onClick={() => onOpenDesignsModal('save')}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-semibold shadow-theme-xs transition cursor-pointer whitespace-nowrap"
          title="Save Current Design"
        >
          <Save className="w-3.5 h-3.5 text-gray-500" />
          <span className="hidden sm:inline">Save As...</span>
        </button>

        {/* Pre-Flight Status Badge / Button */}
        <button
          onClick={() => {
            setActiveTab('conflicts');
            onRunCheck();
          }}
          disabled={checkingConflicts}
          className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition border whitespace-nowrap cursor-pointer ${
            !hasRun
              ? 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              : passed
              ? 'bg-success-50 text-success-600 border-success-500/30 hover:bg-success-100'
              : 'bg-error-50 text-error-600 border-error-500/30 hover:bg-error-100'
          }`}
          title="Run Pre-Flight Controller Check"
        >
          {checkingConflicts ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-gray-600" />
          ) : !hasRun ? (
            <ShieldAlert className="w-3.5 h-3.5 text-gray-500" />
          ) : passed ? (
            <ShieldCheck className="w-3.5 h-3.5 text-success-600" />
          ) : (
            <ShieldAlert className="w-3.5 h-3.5 text-error-600" />
          )}

          <span>
            {checkingConflicts
              ? 'Checking...'
              : !hasRun
              ? 'Pre-Flight'
              : passed
              ? 'Pre-Flight Clean'
              : `${criticals} Conflict${criticals > 1 ? 's' : ''}`}
          </span>
        </button>

        {/* Download Zip CTA */}
        <button
          onClick={onDownloadZip}
          disabled={downloading}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-coral-600 text-white font-medium text-xs shadow-theme-xs hover:bg-coral-700 active:bg-coral-800 disabled:opacity-50 transition cursor-pointer whitespace-nowrap"
        >
          {downloading ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Download className="w-3.5 h-3.5" />
          )}
          <span>Download (.zip)</span>
        </button>
      </div>
    </header>
  );
}
