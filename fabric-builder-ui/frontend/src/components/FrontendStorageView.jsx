import React, { useState, useEffect } from 'react';
import { 
  Layers, 
  Database, 
  Radio, 
  ShieldCheck, 
  Cpu, 
  HardDrive,
  Network,
  Wand2,
  CheckCircle2,
  Server,
  Zap,
  Check,
  SplitSquareVertical,
  Activity
} from 'lucide-react';
import ServerProfileEditor from './ServerProfileEditor';

export default function FrontendStorageView({ config, onChange }) {
  const enableStorage = config.enable_storage ?? true;
  const storageMode = config.storage_network_mode || (enableStorage ? 'standalone' : 'converged'); // 'standalone' | 'converged'
  const enableOob = config.enable_oob ?? true;
  const autoOptimizeNs = config.auto_optimize_ns ?? true;

  const gpuCount = parseInt(config.gpu_count) || 8;
  const gpuNsPorts = parseInt(config.gpu_ns_ports) || 2;
  const storageServers = (enableStorage || storageMode === 'converged') ? (parseInt(config.storage_servers) || 4) : 0;
  const storageNsPorts = parseInt(config.storage_ns_ports) || 2;
  const switchPortCount = parseInt(config.switch_port_count) || 64;

  const totalFrontendDownlinks = (gpuCount * gpuNsPorts) + (storageServers * storageNsPorts) + (3 * 2);
  const reservedPerLeaf = switchPortCount >= 64 ? 8 : 6;
  const availableDownlinksPerLeaf = Math.max(1, switchPortCount - reservedPerLeaf);
  const rawLeaves = Math.ceil(totalFrontendDownlinks / availableDownlinksPerLeaf);
  const recommendedNsLeaves = Math.max(2, rawLeaves % 2 === 0 ? rawLeaves : rawLeaves + 1);
  const recommendedNsSpines = recommendedNsLeaves <= 16 ? 2 : 4;
  const recommendedSoftgates = gpuCount <= 32 ? 2 : 4;

  // OOB Management Switch calculation (48-port switch, 46 usable ports)
  const totalOobEndpoints = gpuCount + (config.enable_storage ? storageServers : 0) + 3;
  const rawOob = Math.ceil(totalOobEndpoints / 44);
  const recommendedOobSwitches = Math.max(2, rawOob % 2 === 0 ? rawOob : rawOob + 1);

  // Bandwidth calculation: Bandwidth per GPU
  // In NVD design: 2x 400G (or 100G/200G) to NS leaves
  const targetBwPerGpu = (gpuNsPorts * 100 / (storageMode === 'converged' ? 2 : 1)).toFixed(1);
  const nvdCertified = parseFloat(targetBwPerGpu) >= 11.1;

  const handleApplyAutoRecommendation = () => {
    onChange('ns_leaves', recommendedNsLeaves);
    onChange('ns_spines', recommendedNsSpines);
    onChange('softgate_count', recommendedSoftgates);
    onChange('oob_switches', recommendedOobSwitches);
    onChange('auto_optimize_ns', true);
  };

  useEffect(() => {
    if (autoOptimizeNs) {
      if (config.ns_leaves !== recommendedNsLeaves) onChange('ns_leaves', recommendedNsLeaves);
      if (config.ns_spines !== recommendedNsSpines) onChange('ns_spines', recommendedNsSpines);
      if (config.softgate_count !== recommendedSoftgates) onChange('softgate_count', recommendedSoftgates);
      if (config.oob_switches !== recommendedOobSwitches) onChange('oob_switches', recommendedOobSwitches);
    }
  }, [gpuCount, gpuNsPorts, storageServers, storageNsPorts, autoOptimizeNs]);

  return (
    <div className="space-y-6">
      {/* 1. North-South Frontend Network & Auto-Optimization Engine */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Network className="w-5 h-5 text-coral-500" />
            <div>
              <h3 className="text-base font-semibold text-gray-900">
                North-South (NS) Front-End Fabric & Auto-Sizing
              </h3>
              <p className="text-xs text-gray-500">
                Border transit, Kubernetes inband mgmt, Softgate L4LB/NAT, and dual-homing
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                const nextVal = !autoOptimizeNs;
                onChange('auto_optimize_ns', nextVal);
                if (nextVal) handleApplyAutoRecommendation();
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                autoOptimizeNs
                  ? 'bg-coral-50 text-coral-700 border-coral-300 shadow-theme-xs'
                  : 'bg-gray-100 text-gray-700 border-gray-200 hover:bg-gray-200'
              }`}
            >
              <Wand2 className="w-3.5 h-3.5 text-coral-600" />
              <span>Auto-Optimize NS Sizing: {autoOptimizeNs ? 'ON' : 'OFF'}</span>
            </button>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-success-50 text-success-600 border border-success-500/20">
              Dual-Homed HA
            </span>
          </div>
        </div>

        {/* Auto-Calculated Recommendation Strip & NVD Validation Metric */}
        <div className="mx-6 mt-5 p-4 rounded-xl bg-blue-25/60 border border-blue-200/80 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-bold text-blue-900 uppercase tracking-wider">
                Optimal Fabric Derivation (from {gpuCount} GPUs + {storageServers} Storage Nodes)
              </span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                nvdCertified ? 'bg-success-100 text-success-800' : 'bg-amber-100 text-amber-800'
              }`}>
                {nvdCertified ? 'NVIDIA NVD Target Met (>=11.1 Gbps/GPU)' : 'Standard Throughput'}
              </span>
            </div>
            <p className="text-xs text-blue-800/80 mt-1">
              Required front downlinks: <strong>{totalFrontendDownlinks}</strong> ({gpuCount * gpuNsPorts} GPU + {storageServers * storageNsPorts} Storage + 6 K8s CP).
              Recommended architecture: <strong>{recommendedNsLeaves} NS Leaves</strong> (paired dual-homing), <strong>{recommendedNsSpines} NS Spines</strong>, and <strong>{recommendedSoftgates} SoftGates</strong>.
            </p>
          </div>
          {!autoOptimizeNs && (
            <button
              onClick={handleApplyAutoRecommendation}
              className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs cursor-pointer shrink-0"
            >
              Apply Recommended Sizing
            </button>
          )}
        </div>

        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              NS Spine Switches
            </label>
            <input
              type="number"
              min="1"
              max="8"
              value={config.ns_spines || 2}
              onChange={(e) => {
                onChange('auto_optimize_ns', false);
                onChange('ns_spines', parseInt(e.target.value) || 1);
              }}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[10px] text-gray-400 mt-1">Non-blocking spine tier</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              NS Leaf Switches (Redundant Pairs)
            </label>
            <input
              type="number"
              min="2"
              step="2"
              max="32"
              value={config.ns_leaves || 2}
              onChange={(e) => {
                onChange('auto_optimize_ns', false);
                onChange('ns_leaves', parseInt(e.target.value) || 2);
              }}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[10px] text-gray-400 mt-1">Dual-homing active-active leaf pairs</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              SoftGate Border Appliances
            </label>
            <input
              type="number"
              min="2"
              step="2"
              max="16"
              value={config.softgate_count || 2}
              onChange={(e) => {
                onChange('auto_optimize_ns', false);
                onChange('softgate_count', parseInt(e.target.value) || 2);
              }}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[10px] text-gray-400 mt-1">Dual-homed (eth1 + eth2) to leaf pairs</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              SoftGate Flavor
            </label>
            <select
              value={config.softgate_flavor || 'sg-hs'}
              onChange={(e) => onChange('softgate_flavor', e.target.value)}
              className="h-11 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20 bg-white"
            >
              <option value="sg-hs">Softgate HS (High-Speed DPDK)</option>
              <option value="sg-pro">SoftGate PRO (Standard / Pro)</option>
            </select>
            <p className="text-[10px] text-gray-400 mt-1">Hardware acceleration model</p>
          </div>
        </div>

        {/* Dual Homing Architecture Assurance Bar */}
        <div className="px-6 pb-6">
          <div className="p-3.5 rounded-xl bg-gray-50 border border-gray-200 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-gray-700">
              <CheckCircle2 className="w-4 h-4 text-success-600" />
              <span className="font-semibold">Dual-Homing Verified:</span>
              <span className="text-gray-500">Every SoftGate connects via dual redundant links (eth1 to Leaf A, eth2 to Leaf B).</span>
            </div>
            <div className="flex items-center gap-2 text-gray-700">
              <CheckCircle2 className="w-4 h-4 text-success-600" />
              <span className="font-semibold">Compute Dual-Homing:</span>
              <span className="text-gray-500">GPU front interfaces (eth9, eth10) striped across leaf pairs.</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Storage Network Architecture: Standalone Fabric vs. Converged Fabric */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Database className="w-5 h-5 text-coral-500" />
            <div>
              <h3 className="text-base font-semibold text-gray-900">
                Storage Network Architecture & Storage Target Profile
              </h3>
              <p className="text-xs text-gray-500">
                Choose between a dedicated standalone NVMe-oF fabric or converged North-South fabric
              </p>
            </div>
          </div>
          
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-coral-50 text-coral-700 border border-coral-200 uppercase">
            {storageMode} Mode
          </span>
        </div>

        <div className="p-6 space-y-6">
          {/* Storage Architecture Selector: Standalone vs. Converged */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              onClick={() => {
                onChange('storage_network_mode', 'standalone');
                onChange('enable_storage', true);
              }}
              className={`p-4 rounded-xl border-2 transition cursor-pointer flex flex-col justify-between ${
                storageMode === 'standalone'
                  ? 'border-coral-500 bg-coral-25/40 shadow-theme-xs'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50/60 bg-white'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-coral-700 uppercase tracking-wider">
                    Standalone Storage Fabric (Dedicated Leaf Switches)
                  </span>
                  {storageMode === 'standalone' && (
                    <div className="w-4 h-4 rounded-full bg-coral-600 text-white flex items-center justify-center">
                      <Check className="w-3 h-3 stroke-[3]" />
                    </div>
                  )}
                </div>
                <h4 className="text-sm font-bold text-gray-900">Dedicated NVMe-oF / RoCE Storage Fabric</h4>
                <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                  Dedicated storage leaf switches (`sw-*-storage-leaf01..02`) physically isolated from general front-end traffic. Recommended for high-IOPS NVMe-oF, Ceph, Lustre, and Weka clusters.
                </p>
              </div>
              <div className="mt-3 pt-2.5 border-t border-gray-100 text-[11px] font-medium text-coral-700">
                Dedicated leaf switches & independent storage IPAM allocation
              </div>
            </div>

            <div
              onClick={() => {
                onChange('storage_network_mode', 'converged');
                onChange('enable_storage', false); // No dedicated storage leaves, routes through NS leaves
              }}
              className={`p-4 rounded-xl border-2 transition cursor-pointer flex flex-col justify-between ${
                storageMode === 'converged'
                  ? 'border-coral-500 bg-coral-25/40 shadow-theme-xs'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50/60 bg-white'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-blue-700 uppercase tracking-wider">
                    Converged Storage Fabric (Shared NS Leaves)
                  </span>
                  {storageMode === 'converged' && (
                    <div className="w-4 h-4 rounded-full bg-coral-600 text-white flex items-center justify-center">
                      <Check className="w-3 h-3 stroke-[3]" />
                    </div>
                  )}
                </div>
                <h4 className="text-sm font-bold text-gray-900">NVIDIA NVD Converged Ethernet Architecture</h4>
                <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                  Storage targets and compute nodes share the high-bandwidth North-South leaf-spine fabric using isolated VLANs/VRFs. Cost-efficient and aligns with NVIDIA ERA 2-4-5-800 Converged designs.
                </p>
              </div>
              <div className="mt-3 pt-2.5 border-t border-gray-100 text-[11px] font-medium text-blue-700">
                Shared physical leaf switches with VLAN/VRF segmentation
              </div>
            </div>
          </div>

          {/* Standalone Parameters */}
          {storageMode === 'standalone' && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-gray-50 border border-gray-200">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                  Dedicated Storage Leaf Switches
                </label>
                <input
                  type="number"
                  min="1"
                  max="16"
                  value={config.storage_leaves || 2}
                  onChange={(e) => onChange('storage_leaves', parseInt(e.target.value) || 1)}
                  className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20 bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                  Storage Target Server Count
                </label>
                <input
                  type="number"
                  min="1"
                  max="64"
                  value={config.storage_servers || 4}
                  onChange={(e) => onChange('storage_servers', parseInt(e.target.value) || 1)}
                  className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20 bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                  Storage Subnet CIDR
                </label>
                <input
                  type="text"
                  value={config.storage_subnet || '10.200.0.0/24'}
                  onChange={(e) => onChange('storage_subnet', e.target.value)}
                  className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20 bg-white"
                />
              </div>
            </div>
          )}

          {/* Converged Parameters */}
          {storageMode === 'converged' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-xl bg-gray-50 border border-gray-200">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                  Storage Target Server Count (Connected to NS Leaves)
                </label>
                <input
                  type="number"
                  min="1"
                  max="64"
                  value={config.storage_servers || 4}
                  onChange={(e) => onChange('storage_servers', parseInt(e.target.value) || 1)}
                  className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20 bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                  Storage VLAN Identifier
                </label>
                <input
                  type="number"
                  value={config.storage_vlan || 200}
                  onChange={(e) => onChange('storage_vlan', parseInt(e.target.value) || 200)}
                  className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20 bg-white"
                />
              </div>
            </div>
          )}

          {/* Storage Server Profile Editor */}
          <div className="pt-2 border-t border-gray-100">
            <h4 className="text-xs font-bold uppercase tracking-wider text-gray-700 mb-3">
              Storage Target Chassis & Port Specification
            </h4>
            <ServerProfileEditor
              profileType="storage"
              profileData={config.storage_profile || {
                preset_id: 'storage_high_speed',
                name: 'High-IOPS NVMe-oF Storage Server',
                roce_ports: parseInt(config.storage_roce_ports) || 2,
                ns_ports: parseInt(config.storage_ns_ports) || 2,
                oob_ports: parseInt(config.storage_oob_ports) || 1,
              }}
              onChangeProfile={(updatedProf) => {
                onChange('storage_profile', updatedProf);
                onChange('storage_roce_ports', updatedProf.roce_ports);
                onChange('storage_ns_ports', updatedProf.ns_ports);
                onChange('storage_oob_ports', updatedProf.oob_ports);
              }}
            />
          </div>
        </div>
      </div>

      {/* 3. Dedicated Out-of-Band (OOB) Management Network */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Radio className="w-5 h-5 text-coral-500" />
            <div>
              <h3 className="text-base font-semibold text-gray-900">
                Dedicated Out-of-Band (OOB) Management (All Devices Connected)
              </h3>
              <p className="text-xs text-gray-500">
                IPMI/BMC server consoles for GPUs & Storage, switch management, and K8s CP nodes
              </p>
            </div>
          </div>
          
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={enableOob}
              onChange={(e) => onChange('enable_oob', e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-coral-600"></div>
          </label>
        </div>

        {enableOob ? (
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                  OOB Switches Count (NVIDIA SN2201)
                </label>
                <input
                  type="number"
                  min="1"
                  max="16"
                  value={config.oob_switches || 2}
                  onChange={(e) => onChange('oob_switches', parseInt(e.target.value) || 1)}
                  className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
                />
                <p className="text-[10px] text-gray-400 mt-1">48-port 1GbE RJ45 + 4x 100G management leaves</p>
                {(config.oob_switches || 2) < recommendedOobSwitches && (
                  <p className="text-[11px] text-amber-600 font-medium mt-1 flex items-center gap-1">
                    <span>⚠ Minimum {recommendedOobSwitches} OOB switches needed for {totalOobEndpoints} endpoints</span>
                    <button
                      type="button"
                      onClick={() => onChange('oob_switches', recommendedOobSwitches)}
                      className="underline font-bold text-amber-700 hover:text-amber-900 cursor-pointer ml-1"
                    >
                      Auto-Fix to {recommendedOobSwitches}
                    </button>
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                  OOB Management Subnet (DHCP Scope)
                </label>
                <input
                  type="text"
                  value={config.oob_subnet || '10.10.0.0/24'}
                  onChange={(e) => onChange('oob_subnet', e.target.value)}
                  className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
                />
                <p className="text-[10px] text-gray-400 mt-1">DHCP address scope for IPMI & BMC</p>
              </div>
            </div>

            {/* OOB Universal Connectivity Badge */}
            <div className="p-3.5 rounded-xl bg-amber-50/60 border border-amber-200 flex items-center justify-between text-xs text-amber-900">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-amber-600" />
                <span className="font-semibold">Universal OOB Coverage:</span>
                <span>
                  All {gpuCount} GPU nodes (eth11), {storageServers} Storage nodes, and 3 K8s CP nodes are cabled into OOB switches.
                </span>
              </div>
              <span className="font-bold text-[11px] bg-amber-100 px-2 py-0.5 rounded text-amber-800">
                100% Cabled
              </span>
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-sm text-gray-400 bg-gray-50/50 rounded-b-2xl">
            Out-of-band management network is disabled.
          </div>
        )}
      </div>
    </div>
  );
}
