import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import TopologyDesignView from './components/TopologyDesignView';
import FrontendStorageView from './components/FrontendStorageView';
import IpamControllerView from './components/IpamControllerView';
import ConflictInspectorView from './components/ConflictInspectorView';
import TerraformExportView from './components/TerraformExportView';
import DeployConsoleView from './components/DeployConsoleView';
import DeploymentHistoryView from './components/DeploymentHistoryView';
import SavedDesignsModal from './components/SavedDesignsModal';

const DEFAULT_CONFIG = {
  site_name: 'MSP02',
  planes_count: 2,
  ew_spines_per_plane: 2,
  ew_leaves_per_plane: 4,
  switch_port_count: 64,
  nos: 'cumulus_nvue',
  softgate_flavor: 'sg-hs',
  public_asn: 65501,
  roh_asn: 65502,
  switch_asn_base: 4200000000,
  gpu_count: 8,
  gpu_roce_ports: 8,
  gpu_ns_ports: 2,
  gpu_oob_ports: 1,
  gpu_profile: {
    preset_id: 'hgx_spectrum_x',
    name: 'NVIDIA HGX H100/H200/B200 (Spectrum-X)',
    roce_ports: 8,
    ns_ports: 2,
    oob_ports: 1,
    total_ports: 11
  },
  auto_optimize_ns: true,
  ns_spines: 2,
  ns_leaves: 2,
  softgate_count: 2,
  enable_storage: true,
  storage_leaves: 2,
  storage_servers: 4,
  storage_roce_ports: 2,
  storage_ns_ports: 2,
  storage_oob_ports: 1,
  storage_profile: {
    preset_id: 'storage_high_speed',
    name: 'High-IOPS NVMe-oF Storage Server',
    roce_ports: 2,
    ns_ports: 2,
    oob_ports: 1,
    total_ports: 5
  },
  storage_subnet: '10.200.0.0/24',
  enable_oob: true,
  oob_switches: 2,
  oob_subnet: '10.10.0.0/24',
  ew_loopback_subnet: '10.253.128.0/24',
  ew_p2p_allocation: '10.254.0.0/16',
  ns_loopback_subnet: '10.25.105.0/24',
  ns_mgmt_subnet: '10.100.0.0/24',
  controller_address: 'https://adam-ctl.netris.io',
  controller_login: 'netris',
  controller_password: '913QGAi6oQTSGgZm20eU',
  timezone: 'Etc/GMT',
  naming_scheme: 'verbose',
  oversubscription_ratio: '1:1',
  ntp_servers: ['1.pool.ntp.org', '2.pool.ntp.org'],
  dns_servers: ['1.1.1.1', '8.8.8.8'],
};

export default function App() {
  const [activeTab, setActiveTab] = useState('topology');
  const [config, setConfig] = useState(DEFAULT_CONFIG);

  // Saved Designs State
  const [savedDesigns, setSavedDesigns] = useState([]);
  const [activeDesign, setActiveDesign] = useState(null);
  const [showDesignsModal, setShowDesignsModal] = useState(false);
  const [designsModalMode, setDesignsModalMode] = useState('open');

  // Controller State
  const [ctlStatus, setCtlStatus] = useState({ connected: false, url: DEFAULT_CONFIG.controller_address });
  const [testingCtl, setTestingCtl] = useState(false);
  const [testResult, setTestResult] = useState(null);

  // Pre-Flight State
  const [conflictReport, setConflictReport] = useState(null);
  const [stateSummary, setStateSummary] = useState(null);
  const [checkingConflicts, setCheckingConflicts] = useState(false);

  // Code Gen State
  const [genData, setGenData] = useState({ total_files: 0, file_tree: [], files: {} });
  const [downloading, setDownloading] = useState(false);
  const [validatingTofu, setValidatingTofu] = useState(false);
  const [tofuResult, setTofuResult] = useState(null);

  // Deployment Workspace & History State
  const [selectedWorkspaceSlug, setSelectedWorkspaceSlug] = useState('current');
  const [activeDeploymentsCount, setActiveDeploymentsCount] = useState(0);

  const fetchDeploymentsCount = async () => {
    try {
      const res = await fetch('/api/deployments');
      const data = await res.json();
      if (data.success) {
        const liveCount = (data.deployments || []).filter((d) => d.has_active_resources).length;
        setActiveDeploymentsCount(liveCount);
      }
    } catch (e) {
      console.error('Error fetching deployments count', e);
    }
  };

  const handleConfigChange = (field, val) => {
    setConfig((prev) => ({
      ...prev,
      [field]: val,
    }));
  };

  // Fetch Saved Designs Library
  const fetchDesigns = async () => {
    try {
      const res = await fetch('/api/designs');
      const data = await res.json();
      if (data.success) {
        setSavedDesigns(data.designs || []);
      }
    } catch (e) {
      console.error('Error fetching designs:', e);
    }
  };

  // Save Current Design
  const handleSaveDesign = async (name, description) => {
    const res = await fetch('/api/designs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        description,
        config,
        id: activeDesign?.id,
      }),
    });
    const data = await res.json();
    if (data.success) {
      setActiveDesign(data.design);
      await fetchDesigns();
    } else {
      throw new Error(data.message || 'Save failed');
    }
  };

  // Load a Saved Design
  const handleLoadDesign = async (designSummary) => {
    try {
      const res = await fetch(`/api/designs/${designSummary.id}`);
      const data = await res.json();
      if (data.success && data.design?.config) {
        setConfig(data.design.config);
        setActiveDesign(data.design);
        setSelectedWorkspaceSlug('current');
        // Trigger immediate conflict check for newly loaded design
        handleRunConflictCheck(data.design.config);
      }
    } catch (e) {
      alert('Error loading design: ' + e.message);
    }
  };

  // Delete a Saved Design
  const handleDeleteDesign = async (designId) => {
    try {
      await fetch(`/api/designs/${designId}`, { method: 'DELETE' });
      if (activeDesign?.id === designId) {
        setActiveDesign(null);
      }
      await fetchDesigns();
    } catch (e) {
      console.error('Error deleting design:', e);
    }
  };

  // Create New Design — resets to clean default template
  const handleCreateNew = () => {
    setConfig(DEFAULT_CONFIG);
    setActiveDesign(null);
    setSelectedWorkspaceSlug('current');
    setTofuResult(null);
    setConflictReport(null);
    setActiveTab('topology');
    handleRunConflictCheck(DEFAULT_CONFIG);
  };

  // 1. Test Controller Connection
  const handleTestConnection = async () => {
    setTestingCtl(true);
    setTestResult(null);
    try {
      const res = await fetch('/api/netris/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          controller_address: config.controller_address,
          controller_login: config.controller_login,
          controller_password: config.controller_password,
        }),
      });
      const data = await res.json();
      setTestResult(data);
      if (data.success) {
        setCtlStatus({ connected: true, url: config.controller_address });
      } else {
        setCtlStatus({ connected: false, url: config.controller_address });
      }
    } catch (e) {
      setTestResult({ success: false, message: e.message });
      setCtlStatus({ connected: false, url: config.controller_address });
    } finally {
      setTestingCtl(false);
    }
  };

  // 2. Run Pre-Flight Conflict Check (Straight Away & Safe against Stale Closures)
  const handleRunConflictCheck = async (overrideConfig) => {
    const targetConfig = overrideConfig || config;
    setCheckingConflicts(true);
    try {
      const res = await fetch('/api/netris/check-conflicts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fabric_config: targetConfig }),
      });
      const data = await res.json();
      if (data.success) {
        setConflictReport(data.report);
        setStateSummary(data.state_summary);
        setCtlStatus({ connected: true, url: targetConfig.controller_address });
      } else {
        console.warn(data.message || 'Controller check failed');
      }
    } catch (e) {
      console.error('Error running conflict analysis:', e);
    } finally {
      setCheckingConflicts(false);
    }
  };

  // 3. Adopt single suggestion
  const handleApplySuggestion = (field, suggestion) => {
    const updated = { ...config, [field]: suggestion };
    setConfig(updated);
    handleRunConflictCheck(updated);
  };

  // 4. Adopt all suggestions (Direct re-validation, guaranteed 0 conflicts on pass 1)
  const handleApplyAllSuggestions = () => {
    if (!conflictReport?.suggestions) return;
    const updated = { ...config, ...conflictReport.suggestions };
    setConfig(updated);
    handleRunConflictCheck(updated);
  };

  // 5. Generate Preview
  const handleGeneratePreview = async () => {
    try {
      const res = await fetch('/api/generator/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      const data = await res.json();
      if (data.success) {
        setGenData({
          total_files: data.total_files,
          file_tree: data.file_tree,
          files: data.files,
        });
      }
    } catch (e) {
      console.error('Failed to generate preview', e);
    }
  };

  // 6. Download ZIP
  const handleDownloadZip = async () => {
    setDownloading(true);
    try {
      const res = await fetch('/api/generator/download-zip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(config.site_name || 'fabric').toLowerCase()}-netris-terraform.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert('Failed to download zip: ' + e.message);
    } finally {
      setDownloading(false);
    }
  };

  // 7. Validate OpenTofu
  const handleValidateTofu = async () => {
    setValidatingTofu(true);
    setTofuResult(null);
    try {
      const res = await fetch('/api/generator/validate-tofu', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      const data = await res.json();
      setTofuResult(data);
    } catch (e) {
      setTofuResult({ success: false, exit_code: 1, stderr: e.message });
    } finally {
      setValidatingTofu(false);
    }
  };

  // Initial preview on mount & when config changes
  useEffect(() => {
    handleGeneratePreview();
  }, [config]);

  // Initial connection test, designs fetch, conflict scan, and deployment fleet check on mount
  useEffect(() => {
    handleTestConnection();
    fetchDesigns();
    handleRunConflictCheck();
    fetchDeploymentsCount();
  }, []);

  // Automatic immediate scan when switching to the conflicts tab if not run yet
  useEffect(() => {
    if (activeTab === 'conflicts' && !conflictReport) {
      handleRunConflictCheck();
    }
  }, [activeTab]);

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* 290px Fixed Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        conflictCount={conflictReport?.critical_count || 0}
        ctlStatus={ctlStatus}
        planesCount={config.planes_count}
        activeDeploymentsCount={activeDeploymentsCount}
      />

      {/* Main Content Area */}
      <div className="flex-1 ml-[290px] flex flex-col min-h-screen">
        <Header
          siteName={config.site_name}
          planesCount={config.planes_count}
          activeDesignName={activeDesign?.name}
          savedDesignsCount={savedDesigns.length}
          onCreateNew={handleCreateNew}
          onOpenDesignsModal={(mode) => {
            setDesignsModalMode(mode);
            setShowDesignsModal(true);
          }}
          conflictReport={conflictReport}
          onRunCheck={() => handleRunConflictCheck()}
          checkingConflicts={checkingConflicts}
          onDownloadZip={handleDownloadZip}
          downloading={downloading}
          setActiveTab={setActiveTab}
        />

        <main className="flex-1 p-8 max-w-7xl mx-auto w-full">
          {activeTab === 'topology' && (
            <TopologyDesignView
              config={config}
              onChange={handleConfigChange}
              onContinueToIpam={() => setActiveTab('ipam-controller')}
              onNext={() => setActiveTab('ipam-controller')}
            />
          )}

          {activeTab === 'frontend-storage' && (
            <TopologyDesignView
              config={config}
              onChange={handleConfigChange}
              onContinueToIpam={() => setActiveTab('ipam-controller')}
              onNext={() => setActiveTab('ipam-controller')}
            />
          )}

          {activeTab === 'ipam-controller' && (
            <IpamControllerView
              config={config}
              onChange={handleConfigChange}
              onTestConnection={handleTestConnection}
              testingConnection={testingCtl}
              testResult={testResult}
              onBack={() => setActiveTab('topology')}
              onNext={() => setActiveTab('conflicts')}
            />
          )}

          {activeTab === 'conflicts' && (
            <ConflictInspectorView
              report={conflictReport}
              summary={stateSummary}
              onRunCheck={() => handleRunConflictCheck()}
              checking={checkingConflicts}
              onApplySuggestion={handleApplySuggestion}
              onApplyAllSuggestions={handleApplyAllSuggestions}
              onBack={() => setActiveTab('ipam-controller')}
              onNext={() => setActiveTab('export')}
            />
          )}

          {activeTab === 'export' && (
            <TerraformExportView
              files={genData.files}
              fileTree={genData.file_tree}
              onDownloadZip={handleDownloadZip}
              downloading={downloading}
              onValidateTofu={handleValidateTofu}
              validatingTofu={validatingTofu}
              tofuResult={tofuResult}
              onBack={() => setActiveTab('conflicts')}
              onNext={() => setActiveTab('deploy')}
            />
          )}

          {activeTab === 'deploy' && (
            <DeployConsoleView
              config={config}
              initialWorkspaceSlug={selectedWorkspaceSlug}
              onSelectWorkspace={(slug) => setSelectedWorkspaceSlug(slug)}
              onOpenHistory={() => setActiveTab('deployments')}
              onBack={() => setActiveTab('export')}
            />
          )}

          {activeTab === 'deployments' && (
            <DeploymentHistoryView
              onOpenConsole={(slug) => {
                setSelectedWorkspaceSlug(slug);
                setActiveTab('deploy');
              }}
              onBack={() => setActiveTab('deploy')}
            />
          )}
        </main>
      </div>

      {/* Saved Designs Modal */}
      <SavedDesignsModal
        isOpen={showDesignsModal}
        onClose={() => setShowDesignsModal(false)}
        mode={designsModalMode}
        savedDesigns={savedDesigns}
        activeDesignId={activeDesign?.id}
        currentConfig={config}
        onSaveDesign={handleSaveDesign}
        onLoadDesign={handleLoadDesign}
        onDeleteDesign={handleDeleteDesign}
      />
    </div>
  );
}
