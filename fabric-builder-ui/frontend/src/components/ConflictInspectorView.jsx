import React from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw, 
  Sparkles, 
  ArrowRight,
  ArrowLeft,
  Database,
  Layers,
  Server,
  Hash
} from 'lucide-react';

export default function ConflictInspectorView({ 
  report, 
  summary, 
  onRunCheck, 
  checking, 
  onApplySuggestion, 
  onApplyAllSuggestions,
  onBack,
  onNext
}) {
  const conflicts = report?.conflicts || [];
  const suggestions = report?.suggestions || {};
  const hasRun = report !== null;
  const criticalCount = report?.critical_count || 0;
  const warningCount = report?.warning_count || 0;
  const passed = hasRun && criticalCount === 0;

  return (
    <div className="space-y-6">
      {/* 1. Controller Live Discovery Summary Banner */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-gray-100">
          <div>
            <h3 className="text-base font-semibold text-gray-900">
              Live Netris Controller Inventory & Conflict Engine
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Validates proposed CIDR pools, BGP ASNs, and names against real controller state
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onRunCheck}
              disabled={checking}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium text-xs shadow-theme-xs transition cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 text-coral-600 ${checking ? 'animate-spin' : ''}`} />
              <span>{checking ? 'Scanning Controller...' : 'Re-Run Inspection'}</span>
            </button>

            {hasRun && Object.keys(suggestions).length > 0 && (
              <button
                onClick={onApplyAllSuggestions}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-coral-600 hover:bg-coral-700 text-white font-medium text-xs shadow-theme-xs transition cursor-pointer"
              >
                <Sparkles className="w-4 h-4" />
                <span>Apply All Suggested Alternatives</span>
              </button>
            )}
          </div>
        </div>

        {/* Live Controller State Pill Counters */}
        {summary && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-5">
            <div className="p-3 rounded-xl bg-gray-50 border border-gray-200">
              <div className="text-[11px] font-medium text-gray-500">Live Sites</div>
              <div className="text-base font-bold text-gray-900 mt-0.5">
                {summary.sites?.length || 0}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 border border-gray-200">
              <div className="text-[11px] font-medium text-gray-500">Active Allocations</div>
              <div className="text-base font-bold text-gray-900 mt-0.5">
                {summary.allocations_count || 0}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 border border-gray-200">
              <div className="text-[11px] font-medium text-gray-500">Active Subnets</div>
              <div className="text-base font-bold text-gray-900 mt-0.5">
                {summary.subnets_count || 0}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 border border-gray-200">
              <div className="text-[11px] font-medium text-gray-500">Allocated ASNs</div>
              <div className="text-base font-bold text-gray-900 mt-0.5">
                {summary.asns_count || 0}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 border border-gray-200">
              <div className="text-[11px] font-medium text-gray-500">Managed Hardware</div>
              <div className="text-base font-bold text-gray-900 mt-0.5">
                {summary.hardware_count || 0}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 2. Inspection Results Card */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            {hasRun ? (
              passed ? (
                <ShieldCheck className="w-5 h-5 text-success-600" />
              ) : (
                <ShieldAlert className="w-5 h-5 text-error-600" />
              )
            ) : (
              <ShieldAlert className="w-5 h-5 text-gray-400" />
            )}
            <div>
              <h3 className="text-base font-semibold text-gray-900">
                Pre-Flight Analysis & Suggested Non-Overlapping Pools
              </h3>
              <p className="text-xs text-gray-500">
                {hasRun
                  ? passed
                    ? 'No blocking conflicts found. The configuration is ready for Terraform apply.'
                    : `Found ${criticalCount} blocking conflict${criticalCount > 1 ? 's' : ''} and ${warningCount} warning${warningCount > 1 ? 's' : ''}.`
                  : 'Click "Run Pre-Flight Check" to inspect.'}
              </p>
            </div>
          </div>

          {hasRun && (
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                passed 
                  ? 'bg-success-50 text-success-600 border border-success-500/20'
                  : 'bg-error-50 text-error-600 border border-error-500/20'
              }`}>
                {passed ? 'Clean & Safe to Deploy' : `${conflicts.length} Issues Flagged`}
              </span>
            </div>
          )}
        </div>

        {/* Conflict Items Table */}
        {!hasRun ? (
          <div className="p-12 text-center">
            <ShieldAlert className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <div className="text-sm font-semibold text-gray-700">Pre-Flight Check Not Run Yet</div>
            <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1 mb-4">
              Inspect your proposed IP pools and ASNs against the live Netris Controller to avoid deployment failures.
            </p>
            <button
              onClick={onRunCheck}
              disabled={checking}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-coral-600 hover:bg-coral-700 text-white font-medium text-xs shadow-theme-xs transition cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${checking ? 'animate-spin' : ''}`} />
              <span>Run Pre-Flight Check Now</span>
            </button>
          </div>
        ) : conflicts.length === 0 ? (
          <div className="p-10 text-center bg-success-50/20">
            <CheckCircle2 className="w-12 h-12 text-success-600 mx-auto mb-2" />
            <div className="text-base font-bold text-gray-900">All Pre-Flight Checks Passed</div>
            <p className="text-xs text-gray-600 max-w-md mx-auto mt-1">
              Zero IPAM overlaps, zero ASN collisions, and zero naming conflicts detected. The generated OpenTofu / Terraform code can be deployed safely.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3.5 text-start text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                    Severity
                  </th>
                  <th className="px-6 py-3.5 text-start text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                    Parameter
                  </th>
                  <th className="px-6 py-3.5 text-start text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                    Proposed Value
                  </th>
                  <th className="px-6 py-3.5 text-start text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                    Conflict Reason
                  </th>
                  <th className="px-6 py-3.5 text-start text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                    Suggested Non-Overlapping Fix
                  </th>
                  <th className="px-6 py-3.5 text-end text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {conflicts.map((item, idx) => {
                  const isCritical = item.severity === 'CRITICAL';
                  return (
                    <tr key={idx} className="hover:bg-gray-50/80 transition">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          isCritical
                            ? 'bg-error-50 text-error-600 border border-error-500/20'
                            : 'bg-warning-50 text-warning-600 border border-warning-500/20'
                        }`}>
                          {item.severity}
                        </span>
                      </td>

                      <td className="px-6 py-4 whitespace-nowrap text-xs font-semibold text-gray-900 font-mono">
                        {item.field}
                      </td>

                      <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-700 font-mono">
                        {String(item.value)}
                      </td>

                      <td className="px-6 py-4 text-xs text-gray-600 max-w-xs">
                        {item.message}
                      </td>

                      <td className="px-6 py-4 whitespace-nowrap">
                        {item.suggestion ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold font-mono bg-coral-50 text-coral-700 border border-coral-200">
                            <ArrowRight className="w-3 h-3 text-coral-500" />
                            {String(item.suggestion)}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>

                      <td className="px-6 py-4 whitespace-nowrap text-end">
                        {item.suggestion && (
                          <button
                            onClick={() => onApplySuggestion(item.field, item.suggestion)}
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-coral-50 hover:text-coral-700 text-gray-700 text-xs font-semibold transition cursor-pointer"
                          >
                            <span>Adopt</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    
      {/* Sticky Bottom Bar with Back & Next navigation */}
      <div className="fixed bottom-0 left-[290px] right-0 bg-white/95 backdrop-blur border-t border-gray-200 px-8 py-3.5 flex items-center justify-between z-20 shadow-theme-md">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-300 hover:bg-gray-100 text-gray-700 text-sm font-semibold transition cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4 stroke-[2.5]" />
          <span>Back to IPAM & Controller</span>
        </button>

        <button
          onClick={onNext}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-coral-600 hover:bg-coral-700 text-white text-sm font-bold shadow-theme-xs transition cursor-pointer"
        >
          <span>Next: Terraform & Export</span>
          <ArrowRight className="w-4 h-4 stroke-[2.5]" />
        </button>
      </div>
    </div>
  );
}