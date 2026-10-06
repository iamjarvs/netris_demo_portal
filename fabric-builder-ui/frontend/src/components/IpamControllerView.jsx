import React, { useState } from 'react';
import { 
  Server, 
  Share2, 
  Globe, 
  Key, 
  ShieldCheck, 
  AlertCircle, 
  RefreshCw,
  Hash,
  Clock,
  Radio,
  Sliders,
  Cpu,
  Layers,
  Shield,
  Zap,
  CheckCircle2,
  Activity,
  Workflow,
  ArrowLeft,
  ArrowRight
} from 'lucide-react';

export default function IpamControllerView({ config, onChange, onTestConnection, testingConnection, testResult, onNext, onBack }) {
  return (
    <div className="space-y-6">
      {/* 1. Netris Controller Target */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Server className="w-5 h-5 text-coral-500" />
            <div>
              <h3 className="text-base font-semibold text-gray-900">
                Netris Controller Target & Authentication
              </h3>
              <p className="text-xs text-gray-500">
                Credentials to inspect live inventory and populate Day-0 terraform.tfvars
              </p>
            </div>
          </div>
          
          <button
            onClick={onTestConnection}
            disabled={testingConnection}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium text-xs shadow-theme-xs transition cursor-pointer"
          >
            {testingConnection ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-gray-600" />
            ) : (
              <Radio className="w-3.5 h-3.5 text-coral-600" />
            )}
            <span>Test Connection</span>
          </button>
        </div>

        <div className="p-6 space-y-4">
          {testResult && (
            <div className={`p-4 rounded-xl border flex items-center gap-3 ${
              testResult.success 
                ? 'bg-success-50 border-success-500/30 text-success-700'
                : 'bg-error-50 border-error-500/30 text-error-700'
            }`}>
              {testResult.success ? (
                <ShieldCheck className="w-5 h-5 shrink-0 text-success-600" />
              ) : (
                <AlertCircle className="w-5 h-5 shrink-0 text-error-600" />
              )}
              <div className="text-xs font-medium">
                {testResult.success 
                  ? `Successfully authenticated to controller as '${testResult.user}'. Ready for live pre-flight checks.`
                  : `Authentication failed: ${testResult.message}`}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                Controller URL
              </label>
              <input
                type="text"
                value={config.controller_address || 'https://adam-ctl.netris.io'}
                onChange={(e) => onChange('controller_address', e.target.value)}
                placeholder="https://controller.example.com"
                className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                Login Username
              </label>
              <input
                type="text"
                value={config.controller_login || 'netris'}
                onChange={(e) => onChange('controller_login', e.target.value)}
                className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                Login Password
              </label>
              <input
                type="password"
                value={config.controller_password || ''}
                onChange={(e) => onChange('controller_password', e.target.value)}
                className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
              />
            </div>
          </div>
        </div>
      </div>

      {/* 2. Site Parameters & ASN Allocation */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center gap-2.5">
          <Globe className="w-5 h-5 text-coral-500" />
          <div>
            <h3 className="text-base font-semibold text-gray-900">
              Site Identifier & BGP Autonomous System Numbers (ASNs)
            </h3>
            <p className="text-xs text-gray-500">
              Physical datacenter boundary and underlay/overlay BGP ASNs
            </p>
          </div>
        </div>

        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Datacenter Site Target
            </label>
            <div className="h-11 w-full rounded-lg border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm font-bold text-gray-900 flex items-center justify-between">
              <span className="truncate">{config.site_name || 'MSP02'}</span>
              <span className="text-[10px] font-mono uppercase bg-coral-100 text-coral-800 px-2 py-0.5 rounded shrink-0">
                {(config.site_name || 'msp02').toLowerCase().replace(/[^a-z0-9_-]/g, '-')}
              </span>
            </div>
            <p className="text-[11px] text-gray-400 mt-1">Sized in Fabric Sizing</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Public BGP ASN
            </label>
            <input
              type="number"
              value={config.public_asn || 65501}
              onChange={(e) => onChange('public_asn', parseInt(e.target.value) || 65501)}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[11px] text-gray-400 mt-1">Site public ASN (16 or 32-bit)</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Routing-on-Host (RoH) ASN
            </label>
            <input
              type="number"
              value={config.roh_asn || 65502}
              onChange={(e) => onChange('roh_asn', parseInt(e.target.value) || 65502)}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[11px] text-gray-400 mt-1">Host eBGP peering ASN</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Switch ASN Base (Private 32-bit)
            </label>
            <input
              type="number"
              value={config.switch_asn_base || 4200000000}
              onChange={(e) => onChange('switch_asn_base', parseInt(e.target.value) || 4200000000)}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[11px] text-gray-400 mt-1">Starting 4-byte ASN for switches</p>
          </div>
        </div>
      </div>

      {/* 3. IPAM Allocations & Subnet CIDRs */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center gap-2.5">
          <Share2 className="w-5 h-5 text-coral-500" />
          <div>
            <h3 className="text-base font-semibold text-gray-900">
              IPAM Allocations & Subnets
            </h3>
            <p className="text-xs text-gray-500">
              CIDR prefixes for East-West RoCE P2P, VTEP Loopbacks, and Management
            </p>
          </div>
        </div>

        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              East-West P2P Allocation (Root CIDR)
            </label>
            <input
              type="text"
              value={config.ew_p2p_allocation || '10.254.0.0/16'}
              onChange={(e) => onChange('ew_p2p_allocation', e.target.value)}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[11px] text-gray-400 mt-1">Carves /31 point-to-point links for EW Spine-Leaf & GPU links</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              East-West Loopback Subnet
            </label>
            <input
              type="text"
              value={config.ew_loopback_subnet || '10.253.128.0/24'}
              onChange={(e) => onChange('ew_loopback_subnet', e.target.value)}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[11px] text-gray-400 mt-1">Switch loopbacks (purpose = loopback)</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              North-South Loopback Subnet
            </label>
            <input
              type="text"
              value={config.ns_loopback_subnet || '10.25.105.0/24'}
              onChange={(e) => onChange('ns_loopback_subnet', e.target.value)}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[11px] text-gray-400 mt-1">Front-end switch loopbacks</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              North-South Inband Management Subnet
            </label>
            <input
              type="text"
              value={config.ns_mgmt_subnet || '10.100.0.0/24'}
              onChange={(e) => onChange('ns_mgmt_subnet', e.target.value)}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[11px] text-gray-400 mt-1">Subnet for switch and Softgate mgmt IPs</p>
          </div>
        </div>
      </div>

      {/* 4. Netris Site Policy & Deployment Options */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center gap-2.5">
          <Shield className="w-5 h-5 text-coral-500" />
          <div>
            <h3 className="text-base font-semibold text-gray-900">
              Netris Site Policy & Deployment Options
            </h3>
            <p className="text-xs text-gray-500">
              Provider attributes for <code className="font-mono text-coral-600 font-medium">netris_site</code>: firewall default posture and VLAN pools
            </p>
          </div>
        </div>

        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              ACL Default Policy
            </label>
            <select
              value={config.acl_default_policy || 'permit'}
              onChange={(e) => onChange('acl_default_policy', e.target.value)}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 bg-white focus:border-coral-300 focus:ring-coral-500/20"
            >
              <option value="permit">Permit (Default / Open Inter-VNet)</option>
              <option value="deny">Deny (Zero-Trust Security / Strict)</option>
            </select>
            <p className="text-[11px] text-gray-400 mt-1">
              Controller default posture for undeclared subnet-to-subnet traffic
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Total VLAN Range
            </label>
            <input
              type="text"
              value={config.vlan_range || '2-4094'}
              onChange={(e) => onChange('vlan_range', e.target.value)}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[11px] text-gray-400 mt-1">Allowable 802.1Q VLAN boundary for fabric</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Auto-Assign VLAN Range
            </label>
            <input
              type="text"
              value={config.vlan_range_auto_assign || '2-3999'}
              onChange={(e) => onChange('vlan_range_auto_assign', e.target.value)}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
            />
            <p className="text-[11px] text-gray-400 mt-1">Pool reserved for Netris V-Net auto-assignment</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              SoftGate Performance Flavor
            </label>
            <select
              value={config.softgate_flavor || 'sg-hs'}
              onChange={(e) => onChange('softgate_flavor', e.target.value)}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 bg-white focus:border-coral-300 focus:ring-coral-500/20"
            >
              <option value="sg-s">sg-s (Small — 2vCPU / 4GB Lab)</option>
              <option value="sg-m">sg-m (Medium — 4vCPU / 8GB Edge)</option>
              <option value="sg-l">sg-l (Large — 8vCPU / 16GB Enterprise)</option>
              <option value="sg-hs">sg-hs (High-Speed DPDK Line-Rate)</option>
              <option value="sg-400g">sg-400g (Ultra 400G Line-Rate Cluster)</option>
            </select>
            <p className="text-[11px] text-gray-400 mt-1">DPDK throughput profile for border gateway</p>
          </div>
        </div>
      </div>

      {/* 5. Netris Inventory Profiles & RoCE Cluster Settings */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-theme-xs">
        <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Sliders className="w-5 h-5 text-coral-500" />
            <div>
              <h3 className="text-base font-semibold text-gray-900">
                Netris Inventory Profiles & GPU Cluster Settings
              </h3>
              <p className="text-xs text-gray-500">
                Advanced ASIC tuning for <code className="font-mono text-coral-600 font-medium">netris_inventory_profile</code>: Spectrum-X adaptive routing, congestion control, and BGP underlay
              </p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-coral-50 text-coral-700 border border-coral-200/60">
            <Zap className="w-3 h-3 text-coral-600" />
            NVIDIA Spectrum-X Ready
          </span>
        </div>

        <div className="p-6 space-y-6">
          {/* RoCE & Underlay Feature Status Banner (Unified from Step 8) */}
          <div className="p-4 rounded-xl bg-coral-25/40 border border-coral-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-coral-600" />
                <span className="text-xs font-bold text-coral-900 uppercase tracking-wider">
                  Hardware RoCE & Underlay Features (Inherited from Step 8)
                </span>
              </div>
              <p className="text-xs text-coral-800/80 mt-0.5">
                ASIC profile attributes are pre-configured in Fabric Sizing and automatically mapped into <code>netris_inventory_profile</code>.
              </p>
            </div>
            <div className="flex flex-wrap gap-1.5 shrink-0">
              <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-white border border-coral-200 text-coral-800 shadow-2xs">
                Adaptive Routing: {config.roce_adaptive_routing !== false ? 'ON' : 'OFF'}
              </span>
              <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-white border border-coral-200 text-coral-800 shadow-2xs">
                DCQCN / ECN: {config.roce_congestion_control !== false ? 'ON' : 'OFF'}
              </span>
              <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-white border border-coral-200 text-coral-800 shadow-2xs">
                PFC CoS 3: {config.roce_lossless_pfc !== false ? 'ON' : 'OFF'}
              </span>
              <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-white border border-coral-200 text-coral-800 shadow-2xs">
                BGP Unnumbered: {config.bgp_unnumbered !== false ? 'ON' : 'OFF'}
              </span>
            </div>
          </div>

          {/* Reference Architecture & Timezone Settings */}
          <div className="pt-4 border-t border-gray-200 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                NVD Reference Architecture (refarch)
              </label>
              <select
                value={config.refarch || ''}
                onChange={(e) => onChange('refarch', e.target.value)}
                className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 bg-white focus:border-coral-300 focus:ring-coral-500/20 font-mono text-xs"
              >
                <option value="">Auto-detected based on planes</option>
                <option value="b300_spx_2_tier_single_plane">b300_spx_2_tier_single_plane (1 Plane)</option>
                <option value="b300_spx_2_tier_dual_plane">b300_spx_2_tier_dual_plane (2 Planes)</option>
                <option value="b300_spx_2_tier_quad_plane">b300_spx_2_tier_quad_plane (4 Planes)</option>
              </select>
              <p className="text-[11px] text-gray-400 mt-1">Preset profile template pushed into Netris inventory profile</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                Profile Timezone
              </label>
              <input
                type="text"
                value={config.timezone || 'Etc/GMT'}
                onChange={(e) => onChange('timezone', e.target.value)}
                className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs font-mono text-gray-800 focus:border-coral-300 focus:ring-coral-500/20"
              />
              <p className="text-[11px] text-gray-400 mt-1">E.g., Etc/GMT, America/New_York, Europe/London</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                Auto Link Aggregation (NS Leaves)
              </label>
              <select
                value={config.automatic_link_aggregation_ns !== false ? 'true' : 'false'}
                onChange={(e) => onChange('automatic_link_aggregation_ns', e.target.value === 'true')}
                className="h-11 w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm shadow-theme-xs text-gray-800 bg-white focus:border-coral-300 focus:ring-coral-500/20"
              >
                <option value="true">Enabled (Auto-LACP for North-South dual-homing)</option>
                <option value="false">Disabled (Manual bonding)</option>
              </select>
              <p className="text-[11px] text-gray-400 mt-1">Auto-bonds redundant server ports into LACP trunks</p>
            </div>
          </div>
        </div>
      </div>
    
      {/* Sticky Bottom Bar with Back & Next navigation */}
      <div className="fixed bottom-0 left-[290px] right-0 bg-white/95 backdrop-blur border-t border-gray-200 px-8 py-3.5 flex items-center justify-between z-20 shadow-theme-md">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-300 hover:bg-gray-100 text-gray-700 text-sm font-semibold transition cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4 stroke-[2.5]" />
          <span>Back to Fabric Sizing</span>
        </button>

        <button
          onClick={onNext}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-coral-600 hover:bg-coral-700 text-white text-sm font-bold shadow-theme-xs transition cursor-pointer"
        >
          <span>Next: Pre-Flight Conflict Check</span>
          <ArrowRight className="w-4 h-4 stroke-[2.5]" />
        </button>
      </div>
    </div>
  );
}