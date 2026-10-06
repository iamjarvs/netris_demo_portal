import React, { useState, useEffect } from 'react';
import { 
  Network, 
  Layers, 
  Cpu, 
  Server, 
  Activity, 
  Zap, 
  Sliders,
  Check,
  SplitSquareVertical,
  Gauge,
  Tag,
  FolderTree,
  ChevronRight,
  Shield,
  HardDrive,
  Plus,
  Minus,
  RotateCcw,
  Sparkles,
  ArrowRight,
  SlidersHorizontal,
  Info,
  CheckCircle2,
  Lock,
  Boxes,
  Radio,
  Workflow
} from 'lucide-react';
import { PREMADE_PROFILES } from './ServerProfileEditor';

export default function TopologyDesignView({ config, onChange, onContinueToIpam }) {
  // 1. Identity & Config State
  const siteName = config.site_name || 'MSP02';
  const siteSlug = (siteName || 'msp02').toLowerCase().replace(/[^a-z0-9_-]/g, '-');
  const nos = config.nos || 'cumulus_nvue';
  const switchPortCount = parseInt(config.switch_port_count) || 64;
  const namingScheme = config.naming_scheme || 'verbose';
  const oversubRatioStr = config.oversubscription_ratio || '1:1';

  // 2. GPU Modeling State
  const gpuCount = parseInt(config.gpu_count) || 8;
  const rocePorts = parseInt(config.gpu_roce_ports) || 8;
  const gpuNsPorts = parseInt(config.gpu_ns_ports) || 2;
  const gpuOobPorts = parseInt(config.gpu_oob_ports) || 1;
  const [showProfileEditor, setShowProfileEditor] = useState(false);
  const [profileEditorTarget, setProfileEditorTarget] = useState('gpu');

  // 3. Multi-Plane State
  const planesCount = parseInt(config.planes_count) || 2;
  const spinesPerPlane = parseInt(config.ew_spines_per_plane) || 2;
  const leavesPerPlane = parseInt(config.ew_leaves_per_plane) || 4;

  // 4. Storage State
  const enableStorage = config.enable_storage ?? true;
  const storageMode = config.storage_network_mode || (enableStorage ? 'converged' : 'none');
  const storageServers = storageMode !== 'none' ? (parseInt(config.storage_servers) || 4) : 0;
  const storageNsPorts = parseInt(config.storage_ns_ports) || 2;
  const storageRocePorts = parseInt(config.storage_roce_ports) || 2;

  // 5. Backend Sizing Math
  const parseRatio = (str) => {
    if (typeof str === 'number') return str > 0 ? str : 1.0;
    if (!str) return 1.0;
    if (str.includes(':')) {
      const parts = str.split(':');
      const num = parseFloat(parts[0]) || 1;
      const den = parseFloat(parts[1]) || 1;
      return num / den;
    }
    return parseFloat(str) || 1.0;
  };
  const numericRatio = parseRatio(oversubRatioStr);

  const portsPerPlaneOnGpu = Math.max(1, Math.floor(rocePorts / planesCount));
  const gpusPerLeaf = Math.max(1, Math.floor((switchPortCount / 2) / portsPerPlaneOnGpu));
  const autoLeavesPerPlane = Math.max(2, Math.ceil(gpuCount / gpusPerLeaf));
  const actualDownlinks = gpusPerLeaf * portsPerPlaneOnGpu;
  const neededUplinks = Math.max(1, Math.ceil(actualDownlinks / numericRatio));
  const linksPerSpine = Math.max(1, Math.ceil(neededUplinks / spinesPerPlane));
  const totalUplinks = linksPerSpine * spinesPerPlane;
  const totalPortsUsedPerLeaf = actualDownlinks + totalUplinks;
  const portUtilizationPct = Math.min(100, Math.round((totalPortsUsedPerLeaf / switchPortCount) * 100));

  const totalBackendSpines = spinesPerPlane * planesCount;
  const totalBackendLeaves = (config.ew_leaves_per_plane ? leavesPerPlane : autoLeavesPerPlane) * planesCount;
  const totalRoceLinks = gpuCount * rocePorts;

  // 6. Frontend Sizing Math
  const totalFrontendDownlinks = (gpuCount * gpuNsPorts) + 
    (storageMode === 'converged' ? storageServers * storageNsPorts : 0) + (3 * 2);
  const reservedPerLeaf = switchPortCount >= 64 ? 8 : 6;
  const availableDownlinksPerLeaf = Math.max(1, switchPortCount - reservedPerLeaf);
  const rawLeaves = Math.ceil(totalFrontendDownlinks / availableDownlinksPerLeaf);
  const autoNsLeaves = Math.max(2, rawLeaves % 2 === 0 ? rawLeaves : rawLeaves + 1);
  const autoNsSpines = autoNsLeaves <= 16 ? 2 : 4;
  const autoSoftgates = gpuCount <= 32 ? 2 : 4;

  const currentNsLeaves = parseInt(config.ns_leaves) || autoNsLeaves;
  const currentNsSpines = parseInt(config.ns_spines) || autoNsSpines;
  const currentSoftgates = parseInt(config.softgate_count) || autoSoftgates;

  // 7. Storage Sizing Math
  const storageLeaves = (storageMode === 'standalone' && enableStorage) 
    ? Math.max(2, Math.ceil((storageServers * storageRocePorts) / (switchPortCount / 2)) % 2 === 0 
        ? Math.ceil((storageServers * storageRocePorts) / (switchPortCount / 2)) 
        : Math.ceil((storageServers * storageRocePorts) / (switchPortCount / 2)) + 1)
    : 0;

  const targetBwPerGpu = (gpuNsPorts * 100 / (storageMode === 'converged' ? 2 : 1)).toFixed(1);
  const nvdCertified = parseFloat(targetBwPerGpu) >= 11.1;

  // 8. OOB Sizing Math
  const totalNetworkSwitches = totalBackendSpines + totalBackendLeaves + currentNsSpines + currentNsLeaves + storageLeaves + currentSoftgates;
  const totalServers = gpuCount + (storageMode !== 'none' ? storageServers : 0) + 3;
  const totalEndpoints = totalNetworkSwitches + totalServers;
  const rawOob = Math.ceil(totalEndpoints / 44);
  const autoOobSwitches = Math.max(2, rawOob % 2 === 0 ? rawOob : rawOob + 1);
  const currentOobSwitches = parseInt(config.oob_switches) || autoOobSwitches;
  const totalOobCapacity = currentOobSwitches * 44;
  const spareOobPorts = totalOobCapacity - totalEndpoints;

  const totalAllSwitches = totalNetworkSwitches + currentOobSwitches;

  // Sizing Auto-sync when GPU count or parameters change
  const [manualOverrideBackend, setManualOverrideBackend] = useState(false);

  useEffect(() => {
    if (!manualOverrideBackend) {
      if (config.ew_leaves_per_plane !== autoLeavesPerPlane) {
        onChange('ew_leaves_per_plane', autoLeavesPerPlane);
      }
    }
  }, [gpuCount, rocePorts, planesCount, switchPortCount, manualOverrideBackend]);

  const handleApplyRecommendedFrontend = () => {
    onChange('ns_leaves', autoNsLeaves);
    onChange('ns_spines', autoNsSpines);
    onChange('softgate_count', autoSoftgates);
  };

  const handleApplyRecommendedOob = () => {
    onChange('oob_switches', autoOobSwitches);
  };

  // Naming Helpers
  const getBackendSpineName = (plane, sIdx) => {
    const s = String(sIdx).padStart(2, '0');
    if (namingScheme === 'plane_focused') return `sw-${siteSlug}-plane${plane}-spine${s}`;
    if (namingScheme === 'compact') return `sw-${siteSlug}-ew-pl${plane}-sp${s}`;
    return `sw-${siteSlug}-backend-plane${plane}-spine${s}`;
  };

  const getBackendLeafName = (plane, lIdx) => {
    const l = String(lIdx).padStart(2, '0');
    if (namingScheme === 'plane_focused') return `sw-${siteSlug}-plane${plane}-leaf${l}`;
    if (namingScheme === 'compact') return `sw-${siteSlug}-ew-pl${plane}-lf${l}`;
    return `sw-${siteSlug}-backend-plane${plane}-leaf${l}`;
  };

  // Plane options
  const planeOptions = [
    {
      count: 1,
      title: 'Single Plane (1)',
      tag: 'Standard RoCE',
      description: 'Single unified East-West Spine-Leaf fabric. All GPU RoCE interfaces connect to Plane 1 leaves.',
      highlight: `${rocePorts} ports to Plane 1`,
    },
    {
      count: 2,
      title: 'Dual Plane (2)',
      tag: 'Recommended (Spectrum-X)',
      description: 'Two physically isolated East-West fabrics. GPU RoCE ports split 50/50 across Plane 1 & 2 for fault isolation.',
      highlight: `${portsPerPlaneOnGpu} ports / plane / GPU`,
    },
    {
      count: 4,
      title: 'Quad Plane (4)',
      tag: 'Ultra-Dense Rail Scale',
      description: 'Four independent East-West fabrics. Eliminates cross-plane contention for massive LLM training clusters.',
      highlight: `${Math.max(1, Math.floor(rocePorts / 4))} ports / plane / GPU`,
    },
    {
      count: 8,
      title: 'Octa Plane (8)',
      tag: 'GB200 NVL72 / SuperPOD',
      description: 'Eight dedicated rail planes. 1:1 rail-aligned mapping for 8-NIC and 18-NIC ultra-scale compute nodes.',
      highlight: `${Math.max(1, Math.floor(rocePorts / 8))} port(s) / plane / GPU`,
    },
  ];

  const oversubOptions = [
    { value: '1:1', label: '1:1 Non-Blocking', badge: 'Line-Rate / No Loss', desc: '100% bisection bandwidth. Full line-rate with zero cross-job contention. NVIDIA Spectrum-X validated.' },
    { value: '2:1', label: '2:1 Cost-Optimized', badge: 'Balanced Density', desc: '50% uplink bisection bandwidth. Halves spine optical links while serving fine-tuning and inference clusters.' },
    { value: '3:1', label: '3:1 Compute-Heavy', badge: 'Batch Inference', desc: '33% uplink bisection bandwidth. Designed for CPU/GPU hybrid nodes with intensive local compute.' },
    { value: '4:1', label: '4:1 Buffer-Optimized', badge: 'Deep-Buffer Edge', desc: '25% uplink bisection bandwidth for budget-constrained enterprise clusters with deep packet buffers.' },
  ];

  return (
    <div className="space-y-8 pb-20">
      {/* Page Header Banner */}
      <div className="rounded-2xl border border-gray-200 bg-gradient-to-r from-white via-coral-25/20 to-white p-6 shadow-theme-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-coral-100 text-coral-800 border border-coral-200">
              Sizing & Topology Engine
            </span>
            <span className="text-xs font-semibold text-gray-500">
              Automated AI Cloud Fabric Architecture
            </span>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mt-1">
            Fabric Sizing & Architecture Architect
          </h2>
          <p className="text-sm text-gray-600 mt-0.5">
            Define your deployment identity, model your GPU compute fleet, and let the engine auto-size the backend, frontend, and OOB tiers with full scaling control.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-4 py-2 rounded-xl bg-white border border-gray-200 text-right shadow-2xs">
            <div className="text-[11px] font-semibold uppercase text-gray-400">Total Fabric Hardware</div>
            <div className="text-lg font-black text-coral-700">
              {totalAllSwitches} Switches <span className="text-xs font-medium text-gray-500">({totalNetworkSwitches} Net + {currentOobSwitches} OOB)</span>
            </div>
          </div>
        </div>
      </div>

      {/* STEP 1: Deployment & Site Identity */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-coral-50 border border-coral-200 flex items-center justify-center text-coral-700 font-bold text-xs">
              01
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">Deployment & Site Identity</h3>
              <p className="text-xs text-gray-500">Name your site, choose switch operating system, and set physical port density.</p>
            </div>
          </div>
          <span className="text-xs font-mono font-bold px-3 py-1 rounded-full bg-gray-100 text-gray-700">
            Site Slug: {siteSlug}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-700 mb-1.5">
              Deployment / Site Name
            </label>
            <input
              type="text"
              value={config.site_name || ''}
              onChange={(e) => onChange('site_name', e.target.value)}
              placeholder="e.g. MSP02, DC1-EAST"
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-coral-500/30 focus:border-coral-500 transition"
            />
            <p className="text-[11px] text-gray-500 mt-1">Used in all Netris resource names and hostnames.</p>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-700 mb-1.5">
              Switch Network OS (NOS)
            </label>
            <select
              value={nos}
              onChange={(e) => onChange('nos', e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-coral-500/30 focus:border-coral-500 transition bg-white"
            >
              <option value="cumulus_nvue">NVIDIA Cumulus Linux (NVUE)</option>
              <option value="cumulus_classic">NVIDIA Cumulus Linux (Classic)</option>
              <option value="sonic">Enterprise SONiC</option>
              <option value="switch_linux">Netris Switch Linux</option>
            </select>
            <p className="text-[11px] text-gray-500 mt-1">Determines switch provision profile in Netris.</p>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-700 mb-1.5">
              Switch Port Density
            </label>
            <select
              value={switchPortCount}
              onChange={(e) => onChange('switch_port_count', parseInt(e.target.value))}
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-coral-500/30 focus:border-coral-500 transition bg-white"
            >
              <option value={64}>64-Port QSFP56-DD (400GbE / Spectrum-X)</option>
              <option value={32}>32-Port QSFP-DD (400GbE Standard)</option>
              <option value={128}>128-Port OSFP (800GbE Ultra-Scale)</option>
            </select>
            <p className="text-[11px] text-gray-500 mt-1">Physical port radix used for Clos auto-calculations.</p>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-700 mb-1.5">
              Naming Convention
            </label>
            <select
              value={namingScheme}
              onChange={(e) => onChange('naming_scheme', e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-coral-500/30 focus:border-coral-500 transition bg-white"
            >
              <option value="verbose">Verbose Self-Describing (Recommended)</option>
              <option value="plane_focused">Plane-Focused</option>
              <option value="compact">Compact Engineer Code</option>
            </select>
            <p className="text-[11px] text-gray-500 mt-1 font-mono truncate">
              Ex: {getBackendSpineName(1, 1)}
            </p>
          </div>
        </div>
      </div>

      {/* STEP 2: GPU Servers Modeling & Compute Fleet */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-coral-50 border border-coral-200 flex items-center justify-center text-coral-700 font-bold text-xs">
              02
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">GPU Compute Fleet & Server Modeling</h3>
              <p className="text-xs text-gray-500">Select an NVIDIA validated compute profile or define custom chassis NIC ports.</p>
            </div>
          </div>
          
          <span className="text-xs font-semibold px-3 py-1 rounded-full bg-coral-50 text-coral-700 border border-coral-200">
            {config.gpu_profile?.name || 'NVIDIA HGX Spectrum-X'}
          </span>
        </div>

        {/* Server Profile Quick Selector (4 cards: 3 Presets + Custom) */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {Object.entries(PREMADE_PROFILES).filter(([k, p]) => k !== 'storage_high_speed').map(([k, p]) => {
            const isSelected = (config.gpu_profile?.preset_id === k) || 
              (!config.gpu_profile?.preset_id && k === 'hgx_spectrum_x');
            return (
              <div
                key={k}
                onClick={() => {
                  if (k === 'custom') {
                    onChange('gpu_profile', {
                      preset_id: 'custom',
                      name: 'Custom Server Profile',
                      roce_ports: rocePorts,
                      ns_ports: gpuNsPorts,
                      oob_ports: gpuOobPorts,
                      total_ports: rocePorts + gpuNsPorts + gpuOobPorts,
                      roce_speed: '400G',
                      ns_speed: '100G/200G',
                      oob_speed: '1G'
                    });
                  } else {
                    onChange('gpu_profile', { ...p, preset_id: p.id });
                    onChange('gpu_roce_ports', p.roce_ports);
                    onChange('gpu_ns_ports', p.ns_ports);
                    onChange('gpu_oob_ports', p.oob_ports);
                  }
                }}
                className={`p-4 rounded-xl border-2 transition cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? 'border-coral-500 bg-coral-25/40 shadow-xs'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50/50 bg-white'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      isSelected ? 'bg-coral-100 text-coral-800' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {p.badge}
                    </span>
                    {isSelected && (
                      <div className="w-4 h-4 rounded-full bg-coral-600 text-white flex items-center justify-center">
                        <Check className="w-3 h-3 stroke-[3]" />
                      </div>
                    )}
                  </div>
                  <div className="font-bold text-sm text-gray-900 leading-tight">{p.name}</div>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{p.description}</p>
                </div>

                <div className="mt-3 pt-2.5 border-t border-gray-200/60 flex items-center justify-between text-[11px] font-semibold text-gray-700">
                  <span>{k === 'custom' ? `${rocePorts}x RoCE` : `${p.roce_ports}x RoCE`}</span>
                  <span>{k === 'custom' ? `${gpuNsPorts}x NS` : `${p.ns_ports}x NS`}</span>
                  <span>{k === 'custom' ? `${gpuOobPorts}x OOB` : `${p.oob_ports}x OOB`}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Custom Port Editor Drawer (Appears when Custom profile is active) */}
        {config.gpu_profile?.preset_id === 'custom' && (
          <div className="mb-6 p-5 rounded-xl bg-coral-25/30 border border-coral-200 animate-fadeIn">
            <div className="flex items-center gap-2 mb-3">
              <SlidersHorizontal className="w-4 h-4 text-coral-600" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-coral-900">
                Custom Hardware Interface Port Allocation
              </h4>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-white p-3.5 rounded-lg border border-coral-200 shadow-2xs">
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  RoCEv2 Rail Ports (East-West)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={1}
                    max={64}
                    value={rocePorts}
                    onChange={(e) => {
                      const val = Math.max(1, parseInt(e.target.value) || 1);
                      onChange('gpu_roce_ports', val);
                      onChange('gpu_profile', { ...config.gpu_profile, roce_ports: val });
                    }}
                    className="w-20 px-3 py-1.5 rounded-lg border border-gray-300 font-bold text-center text-sm"
                  />
                  <span className="text-xs text-gray-500">interfaces per server</span>
                </div>
                <p className="text-[10px] text-gray-400 mt-1">Distributed across the active planes</p>
              </div>

              <div className="bg-white p-3.5 rounded-lg border border-coral-200 shadow-2xs">
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  Frontend Ingress Ports (North-South)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={1}
                    max={16}
                    value={gpuNsPorts}
                    onChange={(e) => {
                      const val = Math.max(1, parseInt(e.target.value) || 1);
                      onChange('gpu_ns_ports', val);
                      onChange('gpu_profile', { ...config.gpu_profile, ns_ports: val });
                    }}
                    className="w-20 px-3 py-1.5 rounded-lg border border-gray-300 font-bold text-center text-sm"
                  />
                  <span className="text-xs text-gray-500">interfaces (LACP MLAG)</span>
                </div>
                <p className="text-[10px] text-gray-400 mt-1">Dual-homed to frontend leaves</p>
              </div>

              <div className="bg-white p-3.5 rounded-lg border border-coral-200 shadow-2xs">
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  Out-of-Band IPMI/BMC Ports
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={1}
                    max={4}
                    value={gpuOobPorts}
                    onChange={(e) => {
                      const val = Math.max(1, parseInt(e.target.value) || 1);
                      onChange('gpu_oob_ports', val);
                      onChange('gpu_profile', { ...config.gpu_profile, oob_ports: val });
                    }}
                    className="w-20 px-3 py-1.5 rounded-lg border border-gray-300 font-bold text-center text-sm"
                  />
                  <span className="text-xs text-gray-500">dedicated BMC port</span>
                </div>
                <p className="text-[10px] text-gray-400 mt-1">Cabled to 48-port OOB switches</p>
              </div>
            </div>
          </div>
        )}

        {/* Server Count Slider & Stepper */}
        <div className="p-5 rounded-xl bg-gray-50 border border-gray-200 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold uppercase tracking-wider text-gray-700">
                Number of GPU Servers in Fleet: <span className="text-coral-600 text-sm font-black">{gpuCount} Nodes</span>
              </label>
              <div className="flex items-center gap-1">
                {[8, 16, 32, 64, 128].map((n) => (
                  <button
                    key={n}
                    onClick={() => onChange('gpu_count', n)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${
                      gpuCount === n
                        ? 'bg-coral-600 text-white shadow-2xs'
                        : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-4">
              <input
                type="range"
                min={2}
                max={256}
                step={2}
                value={gpuCount}
                onChange={(e) => onChange('gpu_count', parseInt(e.target.value))}
                className="w-full accent-coral-600 cursor-pointer"
              />
              <input
                type="number"
                min={1}
                max={512}
                value={gpuCount}
                onChange={(e) => onChange('gpu_count', Math.max(1, parseInt(e.target.value) || 1))}
                className="w-20 px-2.5 py-1.5 rounded-lg border border-gray-300 text-sm font-bold text-center text-gray-900 bg-white"
              />
            </div>
          </div>

          <div className="p-4 rounded-xl bg-white border border-gray-200 shadow-2xs shrink-0 flex items-center gap-4">
            <div className="text-center">
              <div className="text-[10px] uppercase font-bold text-gray-400">Total RoCE Ports</div>
              <div className="text-base font-black text-coral-700">{gpuCount * rocePorts}</div>
            </div>
            <div className="w-px h-8 bg-gray-200" />
            <div className="text-center">
              <div className="text-[10px] uppercase font-bold text-gray-400">Total Frontend Ports</div>
              <div className="text-base font-black text-blue-700">{gpuCount * gpuNsPorts}</div>
            </div>
            <div className="w-px h-8 bg-gray-200" />
            <div className="text-center">
              <div className="text-[10px] uppercase font-bold text-gray-400">Total OOB Ports</div>
              <div className="text-base font-black text-emerald-700">{gpuCount * gpuOobPorts}</div>
            </div>
          </div>
        </div>
      </div>

      {/* STEP 3: Multi-Plane Architecture Selection */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-coral-50 border border-coral-200 flex items-center justify-center text-coral-700 font-bold text-xs">
              03
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">Multi-Plane Rail Architecture</h3>
              <p className="text-xs text-gray-500">Select the number of independent East-West RoCE fabrics for physical plane isolation.</p>
            </div>
          </div>
          <span className="text-xs font-bold px-3 py-1 rounded-full bg-coral-50 text-coral-700 border border-coral-200">
            {planesCount} Active Isolated Plane{planesCount > 1 ? 's' : ''}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {planeOptions.map((opt) => {
            const isSelected = planesCount === opt.count;
            return (
              <div
                key={opt.count}
                onClick={() => onChange('planes_count', opt.count)}
                className={`p-4 rounded-xl border-2 transition cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? 'border-coral-500 bg-coral-25/50 shadow-theme-sm'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50/60 bg-white'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      isSelected ? 'bg-coral-100 text-coral-800' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {opt.tag}
                    </span>
                    {isSelected && (
                      <div className="w-4 h-4 rounded-full bg-coral-600 text-white flex items-center justify-center">
                        <Check className="w-3 h-3 stroke-[3]" />
                      </div>
                    )}
                  </div>
                  <h4 className="text-sm font-bold text-gray-900 mb-1">{opt.title}</h4>
                  <p className="text-xs text-gray-500 leading-relaxed">{opt.description}</p>
                </div>

                <div className="mt-3 pt-2.5 border-t border-gray-200/60 text-xs font-bold text-coral-700 flex items-center gap-1">
                  <Zap className="w-3 h-3 text-coral-500 shrink-0" />
                  <span>{opt.highlight}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* STEP 4: Auto-Sized Backend AI Clos Fabric */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-coral-50 border border-coral-200 flex items-center justify-center text-coral-700 font-bold text-xs">
              04
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">Backend AI RoCE Clos Fabric (Auto-Sized)</h3>
              <p className="text-xs text-gray-500">
                Calculated to support {gpuCount} servers across {planesCount} planes at line rate with zero contention.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-bold px-3 py-1 rounded-full bg-success-50 text-success-700 border border-success-500/20 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-success-600" />
              <span>1:1 Non-Blocking Clos</span>
            </span>
          </div>
        </div>

        {/* Oversubscription Ratio Selector Strip */}
        <div className="mb-6">
          <label className="block text-xs font-bold uppercase tracking-wider text-gray-700 mb-2">
            Oversubscription Ratio Sizing Matrix
          </label>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {oversubOptions.map((opt) => {
              const isSelected = oversubRatioStr === opt.value;
              return (
                <div
                  key={opt.value}
                  onClick={() => onChange('oversubscription_ratio', opt.value)}
                  className={`p-3 rounded-xl border-2 transition cursor-pointer ${
                    isSelected
                      ? 'border-coral-500 bg-coral-25/50'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs text-gray-900">{opt.label}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      isSelected ? 'bg-coral-100 text-coral-800' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {opt.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-gray-500 leading-tight">{opt.desc}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Backend Sizing Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
            <div className="text-[11px] font-bold uppercase text-gray-500">Leaves Per Plane</div>
            <div className="text-xl font-black text-gray-900 mt-1">
              {config.ew_leaves_per_plane || autoLeavesPerPlane}
              <span className="text-xs font-medium text-gray-500 ml-1.5">
                (x{planesCount} planes = {totalBackendLeaves} total)
              </span>
            </div>
            <div className="text-[11px] text-gray-500 mt-1">
              {gpusPerLeaf} GPUs / leaf · {actualDownlinks} downlinks/leaf
            </div>
          </div>

          <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
            <div className="text-[11px] font-bold uppercase text-gray-500">Spines Per Plane</div>
            <div className="text-xl font-black text-gray-900 mt-1">
              {spinesPerPlane}
              <span className="text-xs font-medium text-gray-500 ml-1.5">
                (x{planesCount} planes = {totalBackendSpines} total)
              </span>
            </div>
            <div className="text-[11px] text-gray-500 mt-1">
              {linksPerSpine} links/spine from each leaf
            </div>
          </div>

          <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
            <div className="text-[11px] font-bold uppercase text-gray-500">Leaf Uplinks to Spines</div>
            <div className="text-xl font-black text-gray-900 mt-1">
              {totalUplinks}
              <span className="text-xs font-medium text-gray-500 ml-1.5">ports/leaf</span>
            </div>
            <div className="text-[11px] text-gray-500 mt-1">
              Actual ratio: {(actualDownlinks / Math.max(1, totalUplinks)).toFixed(2)}:1
            </div>
          </div>

          <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
            <div className="text-[11px] font-bold uppercase text-gray-500">Port Utilization</div>
            <div className="text-xl font-black text-gray-900 mt-1">
              {totalPortsUsedPerLeaf} / {switchPortCount}
              <span className="text-xs font-bold text-coral-600 ml-1.5">({portUtilizationPct}%)</span>
            </div>
            <div className="w-full bg-gray-200 h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className={`h-full ${portUtilizationPct > 90 ? 'bg-error-500' : 'bg-coral-500'}`}
                style={{ width: `${portUtilizationPct}%` }}
              />
            </div>
          </div>
        </div>

        {/* Manual Override Option */}
        <div className="pt-4 border-t border-gray-200 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="override_backend"
              checked={manualOverrideBackend}
              onChange={(e) => setManualOverrideBackend(e.target.checked)}
              className="accent-coral-600 rounded cursor-pointer"
            />
            <label htmlFor="override_backend" className="font-semibold text-gray-700 cursor-pointer">
              Enable manual override for backend switch counts
            </label>
          </div>

          {manualOverrideBackend && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="text-gray-500">Leaves/Plane:</span>
                <input
                  type="number"
                  min={2}
                  max={64}
                  value={leavesPerPlane}
                  onChange={(e) => onChange('ew_leaves_per_plane', Math.max(2, parseInt(e.target.value) || 2))}
                  className="w-16 px-2 py-1 rounded border border-gray-300 font-bold text-center"
                />
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-gray-500">Spines/Plane:</span>
                <input
                  type="number"
                  min={1}
                  max={32}
                  value={spinesPerPlane}
                  onChange={(e) => onChange('ew_spines_per_plane', Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-16 px-2 py-1 rounded border border-gray-300 font-bold text-center"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* STEP 5: Auto-Sized Frontend Network (with "Power to Add More") */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700 font-bold text-xs">
              05
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">
                Frontend North-South Fabric (Auto-Sized + Expansion Controls)
              </h3>
              <p className="text-xs text-gray-500">
                Calculated for {totalFrontendDownlinks} required downlinks. Expand with extra leaves, spines, or SoftGates anytime.
              </p>
            </div>
          </div>

          {(currentNsLeaves !== autoNsLeaves || currentNsSpines !== autoNsSpines || currentSoftgates !== autoSoftgates) ? (
            <button
              onClick={handleApplyRecommendedFrontend}
              className="flex items-center gap-1 px-3 py-1 rounded-lg bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-700 transition cursor-pointer"
            >
              <RotateCcw className="w-3 h-3 text-gray-500" />
              <span>Reset to Auto ({autoNsLeaves}L / {autoNsSpines}S / {autoSoftgates}SG)</span>
            </button>
          ) : (
            <span className="text-xs font-bold px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              Auto-Sizing Active
            </span>
          )}
        </div>

        {/* Downlink Calculation Formula Strip */}
        <div className="mb-6 p-4 rounded-xl bg-blue-25/50 border border-blue-200/80 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs text-blue-900">
          <div>
            <span className="font-bold">Downlink Port Requirement Derivation:</span>
            <span className="ml-1 text-blue-800">
              ({gpuCount} GPUs x {gpuNsPorts} ports) + 
              ({storageMode === 'converged' ? `${storageServers} Storage x ${storageNsPorts} ports` : '0 Storage (Standalone)'}) + 
              (3 K8s Control Plane x 2 ports) = <strong>{totalFrontendDownlinks} total downlinks</strong>.
            </span>
          </div>
          <div className="shrink-0 font-bold text-blue-700">
            Max {availableDownlinksPerLeaf} access ports / leaf switch
          </div>
        </div>

        {/* Expansion Stepper Controls (The "Power to Add More") */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Frontend Leaves Stepper */}
          <div className="p-5 rounded-xl border border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-700">
                Frontend Leaves (Pairs)
              </span>
              {currentNsLeaves > autoNsLeaves && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                  +{currentNsLeaves - autoNsLeaves} Extra Leaves
                </span>
              )}
            </div>
            
            <div className="flex items-center justify-between mt-3">
              <button
                onClick={() => onChange('ns_leaves', Math.max(autoNsLeaves, currentNsLeaves - 2))}
                disabled={currentNsLeaves <= autoNsLeaves}
                className="w-10 h-10 rounded-xl bg-white border border-gray-300 hover:border-gray-400 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center text-gray-700 font-bold cursor-pointer transition shadow-2xs"
              >
                <Minus className="w-4 h-4" />
              </button>

              <div className="text-center">
                <div className="text-2xl font-black text-gray-900">{currentNsLeaves}</div>
                <div className="text-[11px] text-gray-500 font-medium">
                  Auto-min: {autoNsLeaves} switches
                </div>
              </div>

              <button
                onClick={() => onChange('ns_leaves', currentNsLeaves + 2)}
                className="w-10 h-10 rounded-xl bg-white border border-gray-300 hover:border-coral-400 hover:bg-coral-50 flex items-center justify-center text-coral-600 font-bold cursor-pointer transition shadow-2xs"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            <p className="text-[11px] text-gray-500 mt-3 text-center">
              Scaled in MLAG redundant pairs for server dual-homing.
            </p>
          </div>

          {/* Frontend Spines Stepper */}
          <div className="p-5 rounded-xl border border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-700">
                Frontend Spines
              </span>
              {currentNsSpines > autoNsSpines && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                  +{currentNsSpines - autoNsSpines} Extra Spines
                </span>
              )}
            </div>
            
            <div className="flex items-center justify-between mt-3">
              <button
                onClick={() => onChange('ns_spines', Math.max(2, currentNsSpines - 2))}
                disabled={currentNsSpines <= 2}
                className="w-10 h-10 rounded-xl bg-white border border-gray-300 hover:border-gray-400 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center text-gray-700 font-bold cursor-pointer transition shadow-2xs"
              >
                <Minus className="w-4 h-4" />
              </button>

              <div className="text-center">
                <div className="text-2xl font-black text-gray-900">{currentNsSpines}</div>
                <div className="text-[11px] text-gray-500 font-medium">
                  Auto-min: {autoNsSpines} switches
                </div>
              </div>

              <button
                onClick={() => onChange('ns_spines', currentNsSpines + 2)}
                className="w-10 h-10 rounded-xl bg-white border border-gray-300 hover:border-coral-400 hover:bg-coral-50 flex items-center justify-center text-coral-600 font-bold cursor-pointer transition shadow-2xs"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            <p className="text-[11px] text-gray-500 mt-3 text-center">
              Provides non-blocking North-South transit and uplink bandwidth.
            </p>
          </div>

          {/* SoftGates Stepper */}
          <div className="p-5 rounded-xl border border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-700">
                Netris SoftGates
              </span>
              {currentSoftgates > autoSoftgates && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                  +{currentSoftgates - autoSoftgates} Extra Nodes
                </span>
              )}
            </div>
            
            <div className="flex items-center justify-between mt-3">
              <button
                onClick={() => onChange('softgate_count', Math.max(2, currentSoftgates - 2))}
                disabled={currentSoftgates <= 2}
                className="w-10 h-10 rounded-xl bg-white border border-gray-300 hover:border-gray-400 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center text-gray-700 font-bold cursor-pointer transition shadow-2xs"
              >
                <Minus className="w-4 h-4" />
              </button>

              <div className="text-center">
                <div className="text-2xl font-black text-gray-900">{currentSoftgates}</div>
                <div className="text-[11px] text-gray-500 font-medium">
                  Active-Active HA ({config.softgate_flavor || 'sg-hs'})
                </div>
              </div>

              <button
                onClick={() => onChange('softgate_count', currentSoftgates + 2)}
                className="w-10 h-10 rounded-xl bg-white border border-gray-300 hover:border-coral-400 hover:bg-coral-50 flex items-center justify-center text-coral-600 font-bold cursor-pointer transition shadow-2xs"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            <p className="text-[11px] text-gray-500 mt-3 text-center">
              Active-active gateway nodes delivering BGP routing, NAT, and load balancing.
            </p>
          </div>
        </div>
      </div>

      {/* STEP 6: Auto-Sized Out-of-Band Management (OOBM) */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 font-bold text-xs">
              06
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">
                Out-of-Band Management (OOBM) Fabric (Auto-Sized from All Endpoints)
              </h3>
              <p className="text-xs text-gray-500">
                Sizes 48-port management switches to connect every switch console/mgmt port and server BMC/IPMI interface.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-bold px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              {currentOobSwitches}x 48-Port Switches ({totalOobCapacity} Usable Ports)
            </span>
          </div>
        </div>

        {/* Formula Derivation Breakdown Card */}
        <div className="p-5 rounded-xl bg-emerald-25/40 border border-emerald-200/80 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
            <div className="p-3 bg-white rounded-lg border border-emerald-100 shadow-2xs">
              <div className="text-[10px] font-bold uppercase text-gray-400">Total Network Switches</div>
              <div className="text-lg font-black text-emerald-800">{totalNetworkSwitches}</div>
              <div className="text-[10px] text-gray-500">
                {totalBackendSpines + totalBackendLeaves} BE + {currentNsSpines + currentNsLeaves} FE + {storageLeaves} Stor + {currentSoftgates} SG
              </div>
            </div>

            <div className="p-3 bg-white rounded-lg border border-emerald-100 shadow-2xs">
              <div className="text-[10px] font-bold uppercase text-gray-400">Total Physical Servers</div>
              <div className="text-lg font-black text-emerald-800">{totalServers}</div>
              <div className="text-[10px] text-gray-500">
                {gpuCount} GPU + {storageMode !== 'none' ? storageServers : 0} Storage + 3 K8s CP
              </div>
            </div>

            <div className="p-3 bg-white rounded-lg border border-emerald-100 shadow-2xs">
              <div className="text-[10px] font-bold uppercase text-gray-400">Total OOB Endpoints</div>
              <div className="text-lg font-black text-emerald-800">{totalEndpoints}</div>
              <div className="text-[10px] text-gray-500">1:1 dedicated port per endpoint</div>
            </div>

            <div className="p-3 bg-white rounded-lg border border-emerald-100 shadow-2xs">
              <div className="text-[10px] font-bold uppercase text-gray-400">Spare OOB Ports</div>
              <div className="text-lg font-black text-emerald-800">{spareOobPorts}</div>
              <div className="text-[10px] text-gray-500">Future expansion buffer</div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-emerald-200/60 flex items-center justify-between text-xs text-emerald-900">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>
                Each 48-port management switch reserves ports 47 & 48 for redundant ISL trunks, leaving <strong>44 usable access ports</strong> per switch.
              </span>
            </div>

            {currentOobSwitches !== autoOobSwitches && (
              <button
                onClick={handleApplyRecommendedOob}
                className="text-xs font-bold text-emerald-700 hover:underline cursor-pointer"
              >
                Reset to Auto ({autoOobSwitches} switches)
              </button>
            )}
          </div>
        </div>
      </div>

      {/* STEP 7: Storage Network Selection */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-700 font-bold text-xs">
              07
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">Storage Fabric Architecture</h3>
              <p className="text-xs text-gray-500">Choose between Converged storage (NVIDIA NVD reference) or Standalone dedicated storage.</p>
            </div>
          </div>

          <span className={`text-xs font-bold px-3 py-1 rounded-full ${
            nvdCertified ? 'bg-success-50 text-success-700 border border-success-500/20' : 'bg-amber-50 text-amber-700 border border-amber-500/20'
          }`}>
            Storage Bandwidth: {targetBwPerGpu} Gbps/GPU {nvdCertified ? '(NVD Certified >= 11.1)' : ''}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Option A: Converged Storage */}
          <div
            onClick={() => {
              onChange('storage_network_mode', 'converged');
              onChange('enable_storage', true);
            }}
            className={`p-5 rounded-xl border-2 transition cursor-pointer flex flex-col justify-between ${
              storageMode === 'converged'
                ? 'border-purple-500 bg-purple-25/40 shadow-xs'
                : 'border-gray-200 hover:border-gray-300 bg-white'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-purple-100 text-purple-800">
                  NVIDIA NVD Reference
                </span>
                {storageMode === 'converged' && (
                  <div className="w-5 h-5 rounded-full bg-purple-600 text-white flex items-center justify-center">
                    <Check className="w-3.5 h-3.5 stroke-[3]" />
                  </div>
                )}
              </div>
              <h4 className="text-base font-bold text-gray-900 mb-1">Converged Storage Fabric</h4>
              <p className="text-xs text-gray-500 leading-relaxed">
                Storage servers connect directly to Frontend North-South leaf switches via RoCE or TCP. 
                Saves switch hardware and optic costs while meeting the NVIDIA Validated Design target bandwidth.
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-gray-200/60 text-xs font-bold text-purple-700">
              0 dedicated switches required · Shared high-bandwidth fabric
            </div>
          </div>

          {/* Option B: Standalone Storage */}
          <div
            onClick={() => {
              onChange('storage_network_mode', 'standalone');
              onChange('enable_storage', true);
            }}
            className={`p-5 rounded-xl border-2 transition cursor-pointer flex flex-col justify-between ${
              storageMode === 'standalone'
                ? 'border-purple-500 bg-purple-25/40 shadow-xs'
                : 'border-gray-200 hover:border-gray-300 bg-white'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-700">
                  Air-Gapped Isolation
                </span>
                {storageMode === 'standalone' && (
                  <div className="w-5 h-5 rounded-full bg-purple-600 text-white flex items-center justify-center">
                    <Check className="w-3.5 h-3.5 stroke-[3]" />
                  </div>
                )}
              </div>
              <h4 className="text-base font-bold text-gray-900 mb-1">Dedicated Standalone Storage Fabric</h4>
              <p className="text-xs text-gray-500 leading-relaxed">
                Independent spine-leaf switches specifically for NVMe-oF, Ceph, Lustre, or WekaFS. 
                Complete physical isolation from north-south user traffic and compute jobs.
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-gray-200/60 text-xs font-bold text-purple-700">
              {storageLeaves} dedicated storage leaf switches auto-sized
            </div>
          </div>
        </div>

        {/* Storage Servers Configuration Bar */}
        <div className="p-4 rounded-xl bg-gray-50 border border-gray-200 flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <HardDrive className="w-4 h-4 text-purple-600 shrink-0" />
            <span className="font-bold text-gray-700">Number of Storage Server Nodes:</span>
            <input
              type="number"
              min={0}
              max={64}
              value={storageServers}
              onChange={(e) => onChange('storage_servers', Math.max(0, parseInt(e.target.value) || 0))}
              className="w-16 px-2.5 py-1 rounded-lg border border-gray-300 font-bold text-center bg-white"
            />
          </div>

          <div className="flex items-center gap-4 text-gray-600">
            <span>Storage Ports/Server: <strong>{storageNsPorts}</strong></span>
            <span>Target Subnet: <strong className="font-mono">{config.storage_subnet || '10.200.0.0/24'}</strong></span>
          </div>
        </div>
      </div>

      {/* STEP 8: Fabric Networking Features & RoCE Optimizations */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-theme-xs">
        <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-coral-50 border border-coral-200 flex items-center justify-center text-coral-700 font-bold text-xs">
              08
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">
                Advanced Fabric Features & RoCE Optimizations
              </h3>
              <p className="text-xs text-gray-500">
                Fine-tune hardware packet handling, congestion control, and routing protocols per fabric type.
              </p>
            </div>
          </div>
          <span className="text-xs font-bold px-3 py-1 rounded-full bg-coral-50 text-coral-700 border border-coral-200">
            Spectrum-X Validated
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Backend RoCE Optimizations */}
          <div className="p-4 rounded-xl border border-gray-200 bg-gray-50/50">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-coral-600" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-gray-900">
                Backend RoCEv2 Acceleration
              </h4>
            </div>

            <div className="space-y-2.5 text-xs">
              <label className="flex items-center justify-between p-2.5 rounded-lg bg-white border border-gray-200 cursor-pointer">
                <div>
                  <div className="font-bold text-gray-900">Adaptive Routing</div>
                  <div className="text-[11px] text-gray-500">Dynamic per-packet load balancing</div>
                </div>
                <input
                  type="checkbox"
                  checked={config.roce_adaptive_routing ?? true}
                  onChange={(e) => onChange('roce_adaptive_routing', e.target.checked)}
                  className="accent-coral-600 w-4 h-4 rounded"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg bg-white border border-gray-200 cursor-pointer">
                <div>
                  <div className="font-bold text-gray-900">Congestion Control (DCQCN / ECN)</div>
                  <div className="text-[11px] text-gray-500">Hardware ECN marking on congestion</div>
                </div>
                <input
                  type="checkbox"
                  checked={config.roce_congestion_control ?? true}
                  onChange={(e) => onChange('roce_congestion_control', e.target.checked)}
                  className="accent-coral-600 w-4 h-4 rounded"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg bg-white border border-gray-200 cursor-pointer">
                <div>
                  <div className="font-bold text-gray-900">Lossless PFC (CoS 3)</div>
                  <div className="text-[11px] text-gray-500">Priority flow control zero-packet-drop</div>
                </div>
                <input
                  type="checkbox"
                  checked={config.roce_lossless_pfc ?? true}
                  onChange={(e) => onChange('roce_lossless_pfc', e.target.checked)}
                  className="accent-coral-600 w-4 h-4 rounded"
                />
              </label>
            </div>
          </div>

          {/* Frontend & Overlay Protocols */}
          <div className="p-4 rounded-xl border border-gray-200 bg-gray-50/50">
            <div className="flex items-center gap-2 mb-3">
              <Network className="w-4 h-4 text-blue-600" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-gray-900">
                Frontend & Overlay Underlay
              </h4>
            </div>

            <div className="space-y-2.5 text-xs">
              <label className="flex items-center justify-between p-2.5 rounded-lg bg-white border border-gray-200 cursor-pointer">
                <div>
                  <div className="font-bold text-gray-900">BGP Unnumbered</div>
                  <div className="text-[11px] text-gray-500">IPv6 link-local dynamic fabric peering</div>
                </div>
                <input
                  type="checkbox"
                  checked={config.bgp_unnumbered ?? true}
                  onChange={(e) => onChange('bgp_unnumbered', e.target.checked)}
                  className="accent-blue-600 w-4 h-4 rounded"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg bg-white border border-gray-200 cursor-pointer">
                <div>
                  <div className="font-bold text-gray-900">EVPN-VXLAN Multi-Tenancy</div>
                  <div className="text-[11px] text-gray-500">Virtual isolated V-Nets per customer</div>
                </div>
                <input
                  type="checkbox"
                  checked={config.evpn_vxlan ?? true}
                  onChange={(e) => onChange('evpn_vxlan', e.target.checked)}
                  className="accent-blue-600 w-4 h-4 rounded"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg bg-white border border-gray-200 cursor-pointer">
                <div>
                  <div className="font-bold text-gray-900">LACP Dual-Homing (MLAG)</div>
                  <div className="text-[11px] text-gray-500">Active-active link bonding for hosts</div>
                </div>
                <input
                  type="checkbox"
                  checked={config.lacp_dual_homing ?? true}
                  onChange={(e) => onChange('lacp_dual_homing', e.target.checked)}
                  className="accent-blue-600 w-4 h-4 rounded"
                />
              </label>
            </div>
          </div>

          {/* Security & Access Controls */}
          <div className="p-4 rounded-xl border border-gray-200 bg-gray-50/50">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="w-4 h-4 text-emerald-600" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-gray-900">
                Security & SoftGate Policies
              </h4>
            </div>

            <div className="space-y-2.5 text-xs">
              <label className="flex items-center justify-between p-2.5 rounded-lg bg-white border border-gray-200 cursor-pointer">
                <div>
                  <div className="font-bold text-gray-900">Stateful Firewall & NAT</div>
                  <div className="text-[11px] text-gray-500">Hardware-accelerated SoftGate gateway</div>
                </div>
                <input
                  type="checkbox"
                  checked={config.softgate_firewall ?? true}
                  onChange={(e) => onChange('softgate_firewall', e.target.checked)}
                  className="accent-emerald-600 w-4 h-4 rounded"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg bg-white border border-gray-200 cursor-pointer">
                <div>
                  <div className="font-bold text-gray-900">Fabric Microsegmentation</div>
                  <div className="text-[11px] text-gray-500">Isolate compute rails from management</div>
                </div>
                <input
                  type="checkbox"
                  checked={config.fabric_microsegmentation ?? true}
                  onChange={(e) => onChange('fabric_microsegmentation', e.target.checked)}
                  className="accent-emerald-600 w-4 h-4 rounded"
                />
              </label>

              <label className="flex items-center justify-between p-2.5 rounded-lg bg-white border border-gray-200 cursor-pointer">
                <div>
                  <div className="font-bold text-gray-900">Hierarchical BGP Summarization</div>
                  <div className="text-[11px] text-gray-500">Aggregate /24 prefix announcements</div>
                </div>
                <input
                  type="checkbox"
                  checked={config.bgp_route_aggregation ?? true}
                  onChange={(e) => onChange('bgp_route_aggregation', e.target.checked)}
                  className="accent-emerald-600 w-4 h-4 rounded"
                />
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* STEP 9: Sticky Bottom Bar (Summary + Continue to IPAM) */}
      <div className="fixed bottom-0 left-[290px] right-0 bg-white/95 backdrop-blur border-t border-gray-200 px-8 py-3.5 flex items-center justify-between z-20 shadow-theme-md">
        <div className="flex items-center gap-6">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Total Fabric Sizing</div>
            <div className="text-sm font-bold text-gray-900">
              {totalAllSwitches} Switches · {totalServers} Endpoints · {planesCount}-Plane Clos
            </div>
          </div>

          <div className="hidden lg:flex items-center gap-4 text-xs text-gray-500">
            <span>BE: <strong>{totalBackendSpines + totalBackendLeaves}</strong> switches</span>
            <span>FE: <strong>{currentNsSpines + currentNsLeaves}</strong> switches</span>
            <span>SoftGates: <strong>{currentSoftgates}</strong> nodes</span>
            <span>OOB: <strong>{currentOobSwitches}</strong> switches</span>
          </div>
        </div>

        <button
          onClick={onContinueToIpam}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-coral-600 hover:bg-coral-700 text-white text-sm font-bold shadow-theme-xs transition cursor-pointer"
        >
          <span>Continue to IPAM & Controller</span>
          <ArrowRight className="w-4 h-4 stroke-[2.5]" />
        </button>
      </div>


    </div>
  );
}
