import React from 'react';
import { Server, Cpu, Shield, HardDrive, Radio, Layers, Check, Sliders, Info } from 'lucide-react';

export const PREMADE_PROFILES = {
  hgx_spectrum_x: {
    id: 'hgx_spectrum_x',
    name: 'NVIDIA HGX H100/H200/B200 (Spectrum-X)',
    badge: 'Official Spectrum-X',
    description: 'Reference architecture matching NVIDIA SuperPOD HGX. 8 independent 400G RoCE rail ports, dual-homed frontend bond0, and dedicated IPMI/BMC OOB port.',
    roce_ports: 8,
    ns_ports: 2,
    oob_ports: 1,
    total_ports: 11,
    roce_speed: '400G',
    ns_speed: '100G/200G',
    oob_speed: '1G/10G',
  },
  dual_nic_16: {
    id: 'dual_nic_16',
    name: 'Dual-NIC 16-Port AI Supernode',
    badge: 'Ultra High-Throughput',
    description: 'Multi-rail high-density server exposing 16 RoCE interfaces for quad-plane fabrics, plus 2 frontend and 1 OOB port.',
    roce_ports: 16,
    ns_ports: 2,
    oob_ports: 1,
    total_ports: 19,
    roce_speed: '400G/800G',
    ns_speed: '100G/200G',
    oob_speed: '1G/10G',
  },
  standard_4_roce: {
    id: 'standard_4_roce',
    name: 'Standard 4-RoCE Inference Node',
    badge: 'Cost-Optimized',
    description: '4-rail GPU node suitable for distributed inference, fine-tuning, and enterprise ML clusters.',
    roce_ports: 4,
    ns_ports: 2,
    oob_ports: 1,
    total_ports: 7,
    roce_speed: '200G/400G',
    ns_speed: '25G/100G',
    oob_speed: '1G',
  },
  storage_high_speed: {
    id: 'storage_high_speed',
    name: 'High-IOPS NVMe-oF Storage Server',
    badge: 'Storage Target',
    description: 'Dedicated NVMe-over-Fabrics target or Lustre/Weka/Ceph head node with 2 storage RoCE ports, 2 frontend ports, and 1 OOB port.',
    roce_ports: 2,
    ns_ports: 2,
    oob_ports: 1,
    total_ports: 5,
    roce_speed: '100G/200G',
    ns_speed: '25G/100G',
    oob_speed: '1G',
  },
  custom: {
    id: 'custom',
    name: 'Custom Server Profile',
    badge: 'Free-Form Specification',
    description: 'Freely customize RoCE, frontend, and out-of-band management interface counts to match your exact chassis.',
  }
};

export default function ServerProfileEditor({ 
  profileType = 'gpu', 
  profileData, 
  onChangeProfile,
  planesCount = 2
}) {
  const selectedPreset = profileData?.preset_id || (profileType === 'storage' ? 'storage_high_speed' : 'hgx_spectrum_x');
  const rocePorts = parseInt(profileData?.roce_ports) || (profileType === 'storage' ? 2 : 8);
  const nsPorts = parseInt(profileData?.ns_ports) || 2;
  const oobPorts = parseInt(profileData?.oob_ports) || 1;
  const totalPorts = rocePorts + nsPorts + oobPorts;

  const handleSelectPreset = (presetKey) => {
    if (presetKey === 'custom') {
      onChangeProfile({
        ...profileData,
        preset_id: 'custom',
        name: 'Custom Server Profile'
      });
      return;
    }
    const preset = PREMADE_PROFILES[presetKey];
    if (preset) {
      onChangeProfile({
        preset_id: preset.id,
        name: preset.name,
        roce_ports: preset.roce_ports,
        ns_ports: preset.ns_ports,
        oob_ports: preset.oob_ports,
        total_ports: preset.total_ports,
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* Preset Selector Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Object.entries(PREMADE_PROFILES).map(([key, p]) => {
          if (profileType === 'storage' && key !== 'storage_high_speed' && key !== 'custom') return null;
          if (profileType === 'gpu' && key === 'storage_high_speed') return null;

          const isSelected = selectedPreset === key;
          return (
            <div
              key={key}
              onClick={() => handleSelectPreset(key)}
              className={`p-3.5 rounded-xl border-2 transition cursor-pointer flex flex-col justify-between ${
                isSelected
                  ? 'border-coral-500 bg-coral-25/40 shadow-theme-xs'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50/60 bg-white'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
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
                <h5 className="text-sm font-bold text-gray-900 leading-tight">{p.name}</h5>
                <p className="text-xs text-gray-500 mt-1 line-clamp-2 leading-relaxed">{p.description}</p>
              </div>

              {p.roce_ports !== undefined && (
                <div className="mt-3 pt-2.5 border-t border-gray-100 flex items-center gap-3 text-[11px] font-medium text-gray-600">
                  <span className="text-coral-600 font-semibold">{p.roce_ports} {profileType === 'storage' ? 'Storage' : 'RoCE'}</span>
                  <span>•</span>
                  <span className="text-blue-600 font-semibold">{p.ns_ports} NS Front</span>
                  <span>•</span>
                  <span className="text-amber-600 font-semibold">{p.oob_ports} OOB</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Port Specification Controls */}
      <div className="p-4 rounded-xl bg-gray-50 border border-gray-200 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-gray-700" />
            <span className="text-xs font-bold uppercase tracking-wider text-gray-700">
              Chassis Port Breakdown (Total: {totalPorts} Physical Interfaces)
            </span>
          </div>
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-white border border-gray-200 text-gray-700 shadow-xs">
            {profileData?.name || 'Server Profile'}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* RoCE / Data Ports */}
          <div className="p-3 rounded-lg bg-white border border-coral-200 shadow-xs">
            <label className="block text-[11px] font-bold text-coral-700 uppercase tracking-wider mb-1">
              {profileType === 'storage' ? 'Storage Data Ports' : 'East-West RoCE Rails'}
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="64"
                value={rocePorts}
                onChange={(e) => {
                  const val = Math.max(1, parseInt(e.target.value) || 1);
                  onChangeProfile({ ...profileData, preset_id: 'custom', roce_ports: val });
                }}
                className="h-9 w-20 rounded-md border border-gray-300 px-2.5 py-1 text-sm font-bold text-gray-900 focus:border-coral-400 focus:ring-coral-500/20"
              />
              {profileType !== 'storage' && (
                <span className="text-xs text-gray-500">
                  ({(rocePorts / planesCount).toFixed(1)} / plane)
                </span>
              )}
            </div>
            <p className="text-[10px] text-gray-400 mt-1">eth1..eth{rocePorts}</p>
          </div>

          {/* North-South Frontend Ports */}
          <div className="p-3 rounded-lg bg-white border border-blue-200 shadow-xs">
            <label className="block text-[11px] font-bold text-blue-700 uppercase tracking-wider mb-1">
              North-South Front Ports
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="16"
                value={nsPorts}
                onChange={(e) => {
                  const val = Math.max(1, parseInt(e.target.value) || 1);
                  onChangeProfile({ ...profileData, preset_id: 'custom', ns_ports: val });
                }}
                className="h-9 w-20 rounded-md border border-gray-300 px-2.5 py-1 text-sm font-bold text-gray-900 focus:border-blue-400 focus:ring-blue-500/20"
              />
              <span className="text-xs text-gray-500">
                {nsPorts >= 2 ? 'Dual-Homed' : 'Single-Homed'}
              </span>
            </div>
            <p className="text-[10px] text-gray-400 mt-1">
              eth{rocePorts + 1}..eth{rocePorts + nsPorts} (bond0)
            </p>
          </div>

          {/* OOB Management Ports */}
          <div className="p-3 rounded-lg bg-white border border-amber-200 shadow-xs">
            <label className="block text-[11px] font-bold text-amber-700 uppercase tracking-wider mb-1">
              Out-of-Band IPMI / BMC
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="4"
                value={oobPorts}
                onChange={(e) => {
                  const val = Math.max(1, parseInt(e.target.value) || 1);
                  onChangeProfile({ ...profileData, preset_id: 'custom', oob_ports: val });
                }}
                className="h-9 w-20 rounded-md border border-gray-300 px-2.5 py-1 text-sm font-bold text-gray-900 focus:border-amber-400 focus:ring-amber-500/20"
              />
              <span className="text-xs text-gray-500">Dedicated OOB</span>
            </div>
            <p className="text-[10px] text-gray-400 mt-1">eth{rocePorts + nsPorts + 1}</p>
          </div>
        </div>

        {/* Visual Server Chassis Port Map */}
        <div className="p-3 rounded-lg bg-white border border-gray-200">
          <div className="text-[11px] font-semibold text-gray-600 mb-2 flex items-center justify-between">
            <span>Physical Interface Map (NIC Layout)</span>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-sm bg-coral-500 inline-block"></span>
                {profileType === 'storage' ? 'Storage Data' : 'Backend RoCE'} ({rocePorts})
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-sm bg-blue-500 inline-block"></span>
                Frontend NS ({nsPorts})
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-sm bg-amber-500 inline-block"></span>
                OOB IPMI ({oobPorts})
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5 pt-1">
            {/* RoCE / Storage Ports */}
            {Array.from({ length: rocePorts }).map((_, idx) => (
              <div 
                key={`roce-${idx}`} 
                className="px-2 py-1 rounded bg-coral-50 border border-coral-300 text-coral-800 font-mono text-[10px] font-bold shadow-2xs"
                title={`${profileType === 'storage' ? 'Storage Data Port' : 'RoCE Rail'} ${idx + 1}`}
              >
                eth{idx + 1}
              </div>
            ))}
            {/* NS Ports */}
            {Array.from({ length: nsPorts }).map((_, idx) => (
              <div 
                key={`ns-${idx}`} 
                className="px-2 py-1 rounded bg-blue-50 border border-blue-300 text-blue-800 font-mono text-[10px] font-bold shadow-2xs"
                title={`Frontend Inband L2VPN Gateway -> NS Leaf ${(idx % 2) + 1}`}
              >
                eth{rocePorts + idx + 1}
              </div>
            ))}
            {/* OOB Ports */}
            {Array.from({ length: oobPorts }).map((_, idx) => (
              <div 
                key={`oob-${idx}`} 
                className="px-2 py-1 rounded bg-amber-50 border border-amber-300 text-amber-800 font-mono text-[10px] font-bold shadow-2xs"
                title="Dedicated IPMI / BMC -> OOB Management Switch"
              >
                eth{rocePorts + nsPorts + idx + 1}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
