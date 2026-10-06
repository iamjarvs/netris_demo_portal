import React from 'react';
import { 
  Network, 
  Layers, 
  Share2, 
  Cpu, 
  ShieldAlert, 
  FileCode2, 
  Server,
  Activity,
  CheckCircle2,
  Rocket,
  Database
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, conflictCount, ctlStatus, planesCount, activeDeploymentsCount = 0 }) {
  const navItems = [
    {
      id: 'topology',
      label: 'Fabric Architect & Sizing',
      subtitle: `${planesCount}-Plane Architecture`,
      icon: Network,
    },
    {
      id: 'ipam-controller',
      label: 'IPAM & Controller',
      subtitle: 'Subnets, ASNs, Controller',
      icon: Share2,
    },
    {
      id: 'conflicts',
      label: 'Pre-Flight Conflict Check',
      subtitle: 'Live Netris Overlap Engine',
      icon: ShieldAlert,
      badge: conflictCount > 0 ? conflictCount : null,
      badgeColor: 'error',
    },
    {
      id: 'export',
      label: 'Terraform & Export',
      subtitle: 'OpenTofu HCL & CSV Preview',
      icon: FileCode2,
    },
    {
      id: 'deploy',
      label: 'Deploy to Netris',
      subtitle: 'Live OpenTofu Runner',
      icon: Rocket,
      highlight: true,
    },
    {
      id: 'deployments',
      label: 'Deployments & History',
      subtitle: 'Fleet Manager & Teardown',
      icon: Database,
      badge: activeDeploymentsCount > 0 ? `${activeDeploymentsCount} Live` : null,
      badgeColor: 'success',
    },
  ];

  return (
    <aside className="fixed top-0 left-0 h-screen w-[290px] bg-white border-r border-gray-200 flex flex-col z-30 select-none">
      {/* Brand Header */}
      <div className="h-[72px] px-6 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-coral-50 border border-coral-200 flex items-center justify-center text-coral-600 shadow-xs">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-gray-900 leading-tight">Fabric Builder</h1>
            <p className="text-xs text-gray-500 font-medium">Terraform & OpenTofu</p>
          </div>
        </div>
        <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
          v2.0
        </span>
      </div>

      {/* Navigation List */}
      <div className="flex-1 px-4 py-5 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
          Design Workflow
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`relative flex items-center w-full gap-3 px-3.5 py-3 rounded-lg text-start transition cursor-pointer ${
                isActive
                  ? 'bg-coral-50 text-coral-700 shadow-theme-xs font-semibold'
                  : 'text-gray-700 hover:bg-gray-100 font-medium'
              } ${item.highlight && !isActive ? 'border border-coral-200/60 bg-coral-25/30' : ''}`}
            >
              <Icon
                className={`w-5 h-5 shrink-0 transition ${
                  isActive ? 'text-coral-700' : (item.highlight ? 'text-coral-600' : 'text-gray-500')
                }`}
              />
              <div className="flex-1 min-w-0">
                <div className="text-sm truncate flex items-center gap-1.5">
                  <span>{item.label}</span>
                </div>
                <div className={`text-xs truncate ${isActive ? 'text-coral-600/80' : 'text-gray-400'}`}>
                  {item.subtitle}
                </div>
              </div>
              {item.badge && (
                <span className="shrink-0 px-2 py-0.5 text-xs font-bold rounded-full bg-error-50 text-error-600 border border-error-500/20">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Controller Status Footer Card */}
      <div className="p-4 border-t border-gray-200">
        <div className="p-3.5 rounded-xl border border-gray-200 bg-gray-50 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className={`w-2.5 h-2.5 rounded-full ${ctlStatus.connected ? 'bg-success-500 animate-pulse' : 'bg-gray-400'}`} />
            <div>
              <div className="text-xs font-semibold text-gray-800">
                {ctlStatus.connected ? 'Controller Linked' : 'Offline / Standalone'}
              </div>
              <div className="text-[11px] text-gray-500 truncate max-w-[140px]">
                {ctlStatus.url ? ctlStatus.url.replace('https://', '') : 'No host set'}
              </div>
            </div>
          </div>
          {ctlStatus.connected ? (
            <CheckCircle2 className="w-4 h-4 text-success-600" />
          ) : (
            <Activity className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </div>
    </aside>
  );
}
