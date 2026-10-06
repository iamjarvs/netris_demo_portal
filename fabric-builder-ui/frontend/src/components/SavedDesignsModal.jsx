import React, { useState } from 'react';
import { 
  X, 
  FolderKanban, 
  Save, 
  Download, 
  Trash2, 
  Layers, 
  Server, 
  Cpu, 
  Calendar, 
  Check, 
  AlertCircle,
  Search,
  ArrowRight,
  PlusCircle
} from 'lucide-react';

export default function SavedDesignsModal({
  isOpen,
  onClose,
  mode = 'open', // 'open' | 'save'
  savedDesigns = [],
  activeDesignId,
  currentConfig,
  onSaveDesign,
  onLoadDesign,
  onDeleteDesign,
}) {
  const [activeTab, setActiveTab] = useState(mode);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Save Form State
  const [designName, setDesignName] = useState(currentConfig?.site_name ? `${currentConfig.site_name} Fabric Design` : '');
  const [designDescription, setDesignDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  if (!isOpen) return null;

  // Filter designs by search query
  const filteredDesigns = savedDesigns.filter((d) => {
    const q = searchQuery.toLowerCase();
    return (
      d.name?.toLowerCase().includes(q) ||
      d.description?.toLowerCase().includes(q) ||
      d.site_name?.toLowerCase().includes(q)
    );
  });

  const handleSaveSubmit = async (e) => {
    e.preventDefault();
    if (!designName.trim()) return;
    setSaving(true);
    try {
      await onSaveDesign(designName.trim(), designDescription.trim());
      setSaveSuccess(true);
      setTimeout(() => {
        setSaveSuccess(false);
        setActiveTab('open');
      }, 900);
    } catch (err) {
      alert('Failed to save design: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleSelectDesign = (design) => {
    onLoadDesign(design);
    onClose();
  };

  const handleDelete = (e, designId, designName) => {
    e.stopPropagation();
    if (confirm(`Are you sure you want to delete "${designName}"?`)) {
      onDeleteDesign(designId);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-theme-xl border border-gray-200 animate-in fade-in zoom-in-95 duration-150 overflow-hidden">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50/70">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-coral-50 border border-coral-200 flex items-center justify-center text-coral-600">
              <FolderKanban className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">Fabric Design Library</h3>
              <p className="text-xs text-gray-500">Save, open, and manage reusable multi-plane topologies</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="px-6 pt-3 border-b border-gray-200 flex items-center gap-4 bg-white">
          <button
            onClick={() => setActiveTab('open')}
            className={`pb-2.5 text-xs font-semibold border-b-2 transition cursor-pointer ${
              activeTab === 'open'
                ? 'border-coral-600 text-coral-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Saved Designs ({savedDesigns.length})
          </button>

          <button
            onClick={() => setActiveTab('save')}
            className={`pb-2.5 text-xs font-semibold border-b-2 transition cursor-pointer ${
              activeTab === 'save'
                ? 'border-coral-600 text-coral-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Save Current Design As...
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1">
          {activeTab === 'open' ? (
            <div className="space-y-4">
              {/* Search Bar */}
              <div className="relative">
                <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search saved designs by name, site, or description..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 rounded-xl border border-gray-300 text-xs focus:outline-none focus:ring-2 focus:ring-coral-500/20 focus:border-coral-500 transition"
                />
              </div>

              {/* Design Cards List */}
              {filteredDesigns.length === 0 ? (
                <div className="py-12 text-center">
                  <FolderKanban className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                  <div className="text-sm font-semibold text-gray-700">No matching designs found</div>
                  <p className="text-xs text-gray-500 mt-1">
                    Try another search term or click "Save Current Design As..." to save your current configuration.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredDesigns.map((d) => {
                    const isActive = d.id === activeDesignId;
                    return (
                      <div
                        key={d.id}
                        onClick={() => handleSelectDesign(d)}
                        className={`p-4 rounded-xl border transition cursor-pointer text-left relative group ${
                          isActive
                            ? 'border-coral-500 bg-coral-50/30 shadow-theme-xs'
                            : 'border-gray-200 hover:border-coral-300 hover:bg-gray-50/50'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="space-y-1 flex-1">
                            <div className="flex items-center gap-2">
                              <h4 className="text-sm font-bold text-gray-900 group-hover:text-coral-600 transition">
                                {d.name}
                              </h4>
                              {isActive && (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-coral-600 text-white">
                                  CURRENT
                                </span>
                              )}
                            </div>
                            {d.description && (
                              <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed">
                                {d.description}
                              </p>
                            )}
                          </div>

                          {/* Action Button: Delete & Open */}
                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              onClick={(e) => handleDelete(e, d.id, d.name)}
                              className="p-1.5 rounded-lg text-gray-400 hover:text-error-600 hover:bg-error-50 transition cursor-pointer"
                              title="Delete Design"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                            <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-gray-300 group-hover:border-coral-500 group-hover:text-coral-700 text-xs font-semibold text-gray-700 transition shadow-2xs">
                              <span>Open</span>
                              <ArrowRight className="w-3 h-3" />
                            </span>
                          </div>
                        </div>

                        {/* Metadata Pills */}
                        <div className="mt-3 pt-3 border-t border-gray-100 flex flex-wrap items-center gap-2 text-[11px] text-gray-500">
                          <span className="inline-flex items-center gap-1 font-medium bg-gray-100 px-2 py-0.5 rounded text-gray-700">
                            <Server className="w-3 h-3 text-gray-400" />
                            Site: {d.site_name}
                          </span>
                          <span className="inline-flex items-center gap-1 font-medium bg-coral-50 px-2 py-0.5 rounded text-coral-700">
                            <Layers className="w-3 h-3 text-coral-500" />
                            {d.planes_count} {d.planes_count === 1 ? 'Plane' : 'Planes'}
                          </span>
                          <span className="inline-flex items-center gap-1 font-medium bg-gray-100 px-2 py-0.5 rounded text-gray-700">
                            <Cpu className="w-3 h-3 text-gray-400" />
                            {d.switch_count} Switches ({d.port_density}p)
                          </span>
                          <span className="inline-flex items-center gap-1 font-medium bg-gray-100 px-2 py-0.5 rounded text-gray-700">
                            {d.gpu_count} GPUs
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <form onSubmit={handleSaveSubmit} className="space-y-5">
              {/* Current Configuration Snapshot Summary */}
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
                <div className="text-xs font-semibold text-gray-700 mb-2">
                  Current Fabric Snapshot to Save:
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div>Site: <strong className="text-gray-900">{currentConfig?.site_name}</strong></div>
                  <div>Planes: <strong className="text-gray-900">{currentConfig?.planes_count}</strong></div>
                  <div>NOS: <strong className="text-gray-900">{currentConfig?.nos}</strong></div>
                  <div>GPUs: <strong className="text-gray-900">{currentConfig?.gpu_count}</strong></div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Design Name <span className="text-error-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Austin AI Cluster - 4 Plane Spectrum-X"
                  value={designName}
                  onChange={(e) => setDesignName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 text-xs focus:outline-none focus:ring-2 focus:ring-coral-500/20 focus:border-coral-500 transition font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Description / Notes (Optional)
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. 128-port leaves, dedicated NVMe storage tier, custom loopback pools..."
                  value={designDescription}
                  onChange={(e) => setDesignDescription(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 text-xs focus:outline-none focus:ring-2 focus:ring-coral-500/20 focus:border-coral-500 transition leading-relaxed"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setActiveTab('open')}
                  className="px-4 py-2.5 rounded-xl border border-gray-300 text-gray-700 hover:bg-gray-50 text-xs font-semibold transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !designName.trim()}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-coral-600 hover:bg-coral-700 text-white text-xs font-semibold shadow-theme-xs transition disabled:opacity-50 cursor-pointer"
                >
                  {saveSuccess ? (
                    <>
                      <Check className="w-4 h-4 text-white" />
                      <span>Design Saved!</span>
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      <span>{saving ? 'Saving...' : 'Save Design'}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
