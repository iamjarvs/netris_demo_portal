import React, { useState } from 'react';
import { 
  FileCode2, 
  Download, 
  Check, 
  Copy, 
  Terminal, 
  FileSpreadsheet, 
  FileText, 
  Settings2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Layers,
  Workflow,
  Cpu,
  Server,
  Zap,
  ArrowRight,
  ArrowLeft,
  Shield,
  Radio,
  Clock,
  Sparkles
} from 'lucide-react';

const WAVES_DATA = [
  {
    wave: 1,
    title: 'Base Tenancy & Site Initialization',
    badge: 'Wave 1: Boundary',
    icon: Shield,
    color: 'coral',
    resources: ['netris_site.site', 'data.netris_tenant.admin'],
    apiEndpoint: 'POST /api/v2/sites',
    summary: 'Instantiates the physical datacenter site boundary, public BGP ASN, firewall ACL default posture, and master VLAN allocator pool.',
    controllerAction: 'Registers the site in Netris Controller, establishes administrative tenant permissions, and configures the default security boundary.',
    cliCommand: 'tofu apply -target=netris_site.site',
    files: ['site.tf', 'terraform.tf', 'terraform.tfvars']
  },
  {
    wave: 2,
    title: 'Master IPAM Allocations & Subnet Pools',
    badge: 'Wave 2: IPAM',
    icon: Workflow,
    color: 'blue',
    resources: ['netris_allocation (P2P Root)', 'netris_subnet (Loopbacks, Inband Mgmt, OOB)'],
    apiEndpoint: 'POST /api/v2/ipam/allocation, POST /api/v2/ipam/subnets',
    summary: 'Carves the /16 root CIDR for point-to-point links and /24 subnets for switch loopbacks, SoftGate mgmt, and IPMI networks.',
    controllerAction: 'Programs IPAM database with purpose flags ("loopback", "management", "active"). Hardware IP allocations draw directly from these subnets.',
    cliCommand: 'tofu apply -target=netris_allocation.allocations -target=netris_subnet.subnets',
    files: ['ipam.tf', 'csv/ipam.csv']
  },
  {
    wave: 3,
    title: 'Hardware Inventory Profiles & Spectrum-X RoCE',
    badge: 'Wave 3: ASIC Profiles',
    icon: Zap,
    color: 'amber',
    resources: ['netris_inventory_profile (East-West per plane, North-South, OOB)'],
    apiEndpoint: 'POST /api/v2/inventory/profiles',
    summary: 'Prepares switch NOS operating templates: RFC 5549 BGP unnumbered underlay, RoCE dynamic adaptive routing, ECN/PFC congestion control, and L3VPN route aggregation.',
    controllerAction: 'Prepares Cumulus NVUE / SONiC profile configurations that will be pushed down to physical switch ASICs upon registration.',
    cliCommand: 'tofu apply -target=netris_inventory_profile.ew_profile_pl1 -target=netris_inventory_profile.ns_profile',
    files: ['inventory_profile.tf']
  },
  {
    wave: 4,
    title: 'Physical Hardware & Compute Fleet Onboarding',
    badge: 'Wave 4: Hardware Fleet',
    icon: Server,
    color: 'purple',
    resources: ['netris_switch (Spines & Leaves)', 'netris_softgate (Border Gateways)', 'netris_server (GPU Compute, Storage, CP)'],
    apiEndpoint: 'POST /api/v2/inventory/switches, POST /api/v2/inventory/softgates, POST /api/v2/inventory/servers',
    summary: 'Binds physical switch MACs and hostnames to site, sets 32-bit private ASNs, binds profile IDs, and registers compute node interfaces.',
    controllerAction: 'Validates hardware inventory, queries switch NOS agents over out-of-band management, and prepares interface tables.',
    cliCommand: 'tofu apply -target=netris_switch.switches -target=netris_softgate.softgates -target=netris_server.gpu_servers',
    files: ['switches.tf', 'softgates.tf', 'servers_gpu.tf', 'servers_storage.tf', 'servers_mgmt.tf']
  },
  {
    wave: 5,
    title: 'Interconnect Fabric, Dynamic Cabling & Routing',
    badge: 'Wave 5: Cabling & BGP',
    icon: Layers,
    color: 'emerald',
    resources: ['netris_link (EW CLOS, NS Front-End, SoftGate Dual-Homing, Storage, OOB)'],
    apiEndpoint: 'POST /api/v2/links',
    summary: 'Cables all switches, servers, SoftGates, and storage targets. Automatically programs switch port speeds, MTU 9216 jumbo frames, and initiates BGP peering.',
    controllerAction: 'Netris Controller pushes Cumulus NVUE port configs, brings up /31 P2P links, enables BGP unnumbered underlay peering, and configures LACP bonds.',
    cliCommand: 'tofu apply -target=netris_link.links_ew_switch -target=netris_link.links_ns_gpu',
    files: ['links_ew_switch.tf', 'links_ew_gpu.tf', 'links_ns_switch.tf', 'links_ns_gpu.tf', 'links_softgate.tf', 'links_storage.tf', 'links_oob_switch.tf']
  }
];

export default function TerraformExportView({ 
  files, 
  fileTree, 
  onDownloadZip, 
  downloading,
  onValidateTofu,
  validatingTofu,
  tofuResult,
  onBack,
  onNext
}) {
  const [selectedPath, setSelectedPath] = useState(
    fileTree?.[0]?.path || 'terraform.tf'
  );
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState('files'); // 'files' | 'pipeline'
  const [selectedWave, setSelectedWave] = useState(1);

  const selectedContent = files?.[selectedPath] || '';

  const handleCopy = () => {
    navigator.clipboard.writeText(selectedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getFileIcon = (path) => {
    if (path.startsWith('csv/')) return FileSpreadsheet;
    if (path.endsWith('.tfvars')) return Settings2;
    if (path.endsWith('.md')) return FileText;
    return FileCode2;
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Toolbar with Tofu Validate & Download */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-gray-900">
            Generated OpenTofu & Terraform Day-0 Deployment
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {fileTree?.length || 0} production files ready to inspect, validate, or export
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onValidateTofu}
            disabled={validatingTofu}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium text-xs shadow-theme-xs transition cursor-pointer"
          >
            {validatingTofu ? (
              <RefreshCw className="w-4 h-4 animate-spin text-gray-600" />
            ) : (
              <Terminal className="w-4 h-4 text-coral-600" />
            )}
            <span>Validate with OpenTofu</span>
          </button>

          <button
            onClick={onDownloadZip}
            disabled={downloading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-coral-600 hover:bg-coral-700 text-white font-medium text-xs shadow-theme-xs transition cursor-pointer"
          >
            {downloading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>Download All (.zip)</span>
          </button>
        </div>
      </div>

      {/* 2. OpenTofu Validation Output Card (if run) */}
      {tofuResult && (
        <div className={`rounded-xl border p-4 shadow-theme-xs ${
          tofuResult.success 
            ? 'bg-success-50/50 border-success-500/30'
            : 'bg-error-50/50 border-error-500/30'
        }`}>
          <div className="flex items-center gap-2.5 mb-2">
            {tofuResult.success ? (
              <CheckCircle2 className="w-5 h-5 text-success-600 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-error-600 shrink-0" />
            )}
            <div className="text-sm font-semibold text-gray-900">
              {tofuResult.success 
                ? 'OpenTofu Validation Passed (Exit Code 0)'
                : `OpenTofu Validation Failed (Exit Code ${tofuResult.exit_code})`}
            </div>
          </div>
          
          <pre className="mt-2 p-3 rounded-lg bg-gray-900 text-gray-100 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
            {tofuResult.stdout || tofuResult.stderr || 'No output recorded.'}
          </pre>
        </div>
      )}

      {/* View Mode Toggle: File Explorer vs Execution Lifecycle */}
      <div className="flex items-center gap-2 border-b border-gray-200 pb-1">
        <button
          onClick={() => setViewMode('files')}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition cursor-pointer ${
            viewMode === 'files'
              ? 'bg-coral-50 text-coral-700 border border-coral-200/80 shadow-theme-xs'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <FileCode2 className="w-4 h-4" />
          <span>Project Files ({fileTree?.length || 0})</span>
        </button>

        <button
          onClick={() => setViewMode('pipeline')}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition cursor-pointer ${
            viewMode === 'pipeline'
              ? 'bg-coral-50 text-coral-700 border border-coral-200/80 shadow-theme-xs'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <Workflow className="w-4 h-4 text-coral-600" />
          <span>Execution Lifecycle & Dependency Waves (How Config is Pushed)</span>
          <span className="px-1.5 py-0.5 rounded bg-coral-100 text-coral-800 text-[10px] font-mono font-bold">
            5 Waves
          </span>
        </button>
      </div>

      {viewMode === 'files' ? (
        /* 3. Main File Explorer & Code Viewer Split Pane */
        <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs overflow-hidden flex flex-col md:flex-row min-h-[620px]">
          {/* Left File Browser (280px) */}
          <div className="w-full md:w-[280px] border-b md:border-b-0 md:border-r border-gray-200 bg-gray-50/50 flex flex-col">
            <div className="p-4 border-b border-gray-200 font-semibold text-xs text-gray-500 uppercase tracking-wider">
              Project Files ({fileTree?.length || 0})
            </div>
            <div className="p-2 space-y-1 overflow-y-auto max-h-[600px] flex-1">
              {fileTree?.map((item) => {
                const Icon = getFileIcon(item.path);
                const isSelected = selectedPath === item.path;
                return (
                  <button
                    key={item.path}
                    onClick={() => setSelectedPath(item.path)}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-start text-xs transition cursor-pointer ${
                      isSelected
                        ? 'bg-coral-50 text-coral-700 font-semibold shadow-theme-xs'
                        : 'text-gray-700 hover:bg-gray-100 font-medium'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <Icon className={`w-4 h-4 shrink-0 ${isSelected ? 'text-coral-600' : 'text-gray-400'}`} />
                      <span className="truncate">{item.path}</span>
                    </div>
                    <span className="text-[10px] text-gray-400 shrink-0 ml-1.5 font-mono">
                      {item.lines}L
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Code Viewer */}
          <div className="flex-1 flex flex-col bg-white">
            {/* File Toolbar */}
            <div className="h-12 px-5 border-b border-gray-200 flex items-center justify-between bg-gray-50/70">
              <div className="flex items-center gap-2 text-xs font-mono font-semibold text-gray-800">
                <FileCode2 className="w-4 h-4 text-coral-500" />
                <span>{selectedPath}</span>
              </div>

              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-xs font-medium shadow-theme-xs transition cursor-pointer"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-success-600" />
                    <span className="text-success-600">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-gray-500" />
                    <span>Copy Code</span>
                  </>
                )}
              </button>
            </div>

            {/* Code Viewer Body */}
            <div className="flex-1 p-4 overflow-auto max-h-[580px] bg-gray-50/30">
              <pre className="font-mono text-xs text-gray-800 leading-relaxed whitespace-pre font-normal">
                {selectedContent}
              </pre>
            </div>
          </div>
        </div>
      ) : (
        /* 4. Execution Lifecycle & Dependency Waves Panel */
        <div className="space-y-6">
          {/* Waves Horizontal Stepper */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {WAVES_DATA.map((w) => {
              const Icon = w.icon;
              const isCurrent = selectedWave === w.wave;
              return (
                <button
                  key={w.wave}
                  onClick={() => setSelectedWave(w.wave)}
                  className={`p-4 rounded-xl border text-start transition cursor-pointer relative ${
                    isCurrent
                      ? 'border-coral-500 bg-coral-50/40 shadow-theme-xs ring-2 ring-coral-500/20'
                      : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50/60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                      isCurrent ? 'bg-coral-600 text-white' : 'bg-gray-100 text-gray-700'
                    }`}>
                      {w.wave}
                    </span>
                    <Icon className={`w-4 h-4 ${isCurrent ? 'text-coral-600' : 'text-gray-400'}`} />
                  </div>
                  <div className="text-xs font-semibold text-gray-900 line-clamp-1">{w.title}</div>
                  <div className="text-[10px] text-gray-500 mt-1 font-mono">{w.badge}</div>
                </button>
              );
            })}
          </div>

          {/* Selected Wave Deep Dive Card */}
          {(() => {
            const wave = WAVES_DATA.find((w) => w.wave === selectedWave) || WAVES_DATA[0];
            const WaveIcon = wave.icon;
            return (
              <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs overflow-hidden">
                <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-coral-100 flex items-center justify-center text-coral-600">
                      <WaveIcon className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-coral-600 text-white">
                          Wave {wave.wave}
                        </span>
                        <h4 className="text-base font-semibold text-gray-900">{wave.title}</h4>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">{wave.summary}</p>
                    </div>
                  </div>

                  <span className="font-mono text-xs text-gray-500 px-3 py-1 rounded-lg bg-gray-100">
                    {wave.apiEndpoint}
                  </span>
                </div>

                <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Left Column: Resources & Files */}
                  <div className="space-y-4">
                    <div>
                      <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                        OpenTofu Resources Created
                      </h5>
                      <div className="space-y-1.5">
                        {wave.resources.map((res, idx) => (
                          <div key={idx} className="flex items-center gap-2 p-2.5 rounded-lg bg-gray-50 border border-gray-200 font-mono text-xs text-gray-800">
                            <span className="w-2 h-2 rounded-full bg-coral-500 shrink-0" />
                            <span>{res}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                        Configuration Source Files
                      </h5>
                      <div className="flex flex-wrap gap-2">
                        {wave.files.map((file, idx) => (
                          <button
                            key={idx}
                            onClick={() => {
                              setSelectedPath(file);
                              setViewMode('files');
                            }}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-gray-300 hover:border-coral-400 hover:text-coral-600 text-xs font-mono text-gray-700 shadow-theme-xs transition cursor-pointer"
                          >
                            <FileCode2 className="w-3.5 h-3.5 text-gray-400" />
                            <span>{file}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Netris Controller Impact & CLI Command */}
                  <div className="space-y-4">
                    <div>
                      <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                        Netris Controller & ASIC Impact
                      </h5>
                      <div className="p-4 rounded-xl border border-gray-200 bg-gray-50/60 text-xs text-gray-700 leading-relaxed">
                        {wave.controllerAction}
                      </div>
                    </div>

                    <div>
                      <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                        Targeted OpenTofu CLI Execution
                      </h5>
                      <div className="p-3 rounded-xl bg-gray-900 text-gray-100 font-mono text-xs flex items-center justify-between">
                        <code>{wave.cliCommand}</code>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(wave.cliCommand);
                            setCopied(true);
                            setTimeout(() => setCopied(false), 2000);
                          }}
                          className="text-gray-400 hover:text-white transition cursor-pointer ml-3 shrink-0"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Full Execution Pipeline Flow Banner */}
          <div className="rounded-2xl border border-gray-200 bg-gradient-to-r from-gray-900 to-gray-800 p-6 text-white shadow-theme-xs">
            <div className="flex items-center gap-2 text-coral-400 text-xs font-bold uppercase tracking-wider mb-2">
              <Terminal className="w-4 h-4" />
              <span>Full End-to-End Execution Sequence</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4 font-mono text-xs">
              <div className="p-3 rounded-lg bg-white/10 border border-white/10">
                <div className="text-gray-400 text-[10px]">Step 1</div>
                <div className="font-semibold text-white mt-0.5">tofu init -upgrade</div>
                <div className="text-[11px] text-gray-300 mt-1">Downloads netrisai/netris provider</div>
              </div>
              <div className="p-3 rounded-lg bg-white/10 border border-white/10">
                <div className="text-gray-400 text-[10px]">Step 2</div>
                <div className="font-semibold text-white mt-0.5">tofu validate</div>
                <div className="text-[11px] text-gray-300 mt-1">Verifies schema & syntax</div>
              </div>
              <div className="p-3 rounded-lg bg-white/10 border border-white/10">
                <div className="text-gray-400 text-[10px]">Step 3</div>
                <div className="font-semibold text-white mt-0.5">tofu plan -out=tfplan</div>
                <div className="text-[11px] text-gray-300 mt-1">Calculates 5-wave graph against API</div>
              </div>
              <div className="p-3 rounded-lg bg-coral-500/20 border border-coral-500/40">
                <div className="text-coral-300 text-[10px]">Step 4</div>
                <div className="font-semibold text-coral-200 mt-0.5">tofu apply tfplan</div>
                <div className="text-[11px] text-coral-100 mt-1">Pushes configuration to controller</div>
              </div>
            </div>
          </div>
        </div>
      )}
    
      {/* Sticky Bottom Bar with Back & Next navigation */}
      <div className="fixed bottom-0 left-[290px] right-0 bg-white/95 backdrop-blur border-t border-gray-200 px-8 py-3.5 flex items-center justify-between z-20 shadow-theme-md">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-300 hover:bg-gray-100 text-gray-700 text-sm font-semibold transition cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4 stroke-[2.5]" />
          <span>Back to Conflict Check</span>
        </button>

        <button
          onClick={onNext}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-coral-600 hover:bg-coral-700 text-white text-sm font-bold shadow-theme-xs transition cursor-pointer"
        >
          <span>Next: Deploy to Netris</span>
          <ArrowRight className="w-4 h-4 stroke-[2.5]" />
        </button>
      </div>
    </div>
  );
}