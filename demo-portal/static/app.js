const { useState, useEffect, useRef } = React;

// --- API Service ---
const API_BASE = '';

async function fetchTools() {
  const res = await fetch(`${API_BASE}/api/tools`);
  if (!res.ok) throw new Error('Failed to fetch tools');
  return res.json();
}

async function startToolApi(toolId, payload = null) {
  const options = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  };
  if (payload) {
    options.body = JSON.stringify(payload);
  }
  const res = await fetch(`${API_BASE}/api/tools/${toolId}/start`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to start tool' }));
    throw new Error(err.detail || 'Failed to start tool');
  }
  return res.json();
}

async function stopToolApi(toolId) {
  const res = await fetch(`${API_BASE}/api/tools/${toolId}/stop`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to stop tool' }));
    throw new Error(err.detail || 'Failed to stop tool');
  }
  return res.json();
}

async function restartToolApi(toolId) {
  const res = await fetch(`${API_BASE}/api/tools/${toolId}/restart`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to restart tool' }));
    throw new Error(err.detail || 'Failed to restart tool');
  }
  return res.json();
}

async function fetchLogs(toolId, limit = 150) {
  const res = await fetch(`${API_BASE}/api/tools/${toolId}/logs?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch logs');
  return res.json();
}

async function runScenarioApi(scenarioId) {
  const res = await fetch(`${API_BASE}/api/tools/scenarios/${scenarioId}`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to execute scenario');
  return res.json();
}

async function fetchGlobalConfig() {
  const res = await fetch(`${API_BASE}/api/config/global`);
  if (!res.ok) throw new Error('Failed to fetch global config');
  return res.json();
}

async function saveGlobalConfig(config) {
  const res = await fetch(`${API_BASE}/api/config/global`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error('Failed to save global config');
  return res.json();
}

async function fetchConfigCatalog() {
  const res = await fetch(`${API_BASE}/api/config/catalog`);
  if (!res.ok) throw new Error('Failed to fetch config catalog');
  return res.json();
}

async function fetchConfigFile(toolId, fileId) {
  const url = fileId
    ? `${API_BASE}/api/config/file?tool_id=${encodeURIComponent(toolId)}&file_id=${encodeURIComponent(fileId)}`
    : `${API_BASE}/api/config/file?tool_id=${encodeURIComponent(toolId)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch file content');
  return res.json();
}

async function saveConfigFile(toolId, fileId, content) {
  const res = await fetch(`${API_BASE}/api/config/file`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tool_id: toolId, file_id: fileId, content: content }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to save file' }));
    throw new Error(err.detail || 'Failed to save file');
  }
  return res.json();
}

async function launchNativeTerminalApi(toolId) {
  const res = await fetch(`${API_BASE}/api/tools/${toolId}/launch-native`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to launch native terminal' }));
    throw new Error(err.detail || 'Failed to launch native terminal');
  }
  return res.json();
}

async function startRecordingApi(duration = 300, interval = 15) {
  const res = await fetch(`${API_BASE}/api/tools/netris-prometheus-exporter/record`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ duration, interval }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to start recording' }));
    throw new Error(err.detail || 'Failed to start recording');
  }
  return res.json();
}

async function fetchRecordingStatusApi() {
  const res = await fetch(`${API_BASE}/api/tools/netris-prometheus-exporter/record/status`);
  if (!res.ok) throw new Error('Failed to fetch recording status');
  return res.json();
}

async function stopRecordingApi() {
  const res = await fetch(`${API_BASE}/api/tools/netris-prometheus-exporter/record/stop`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to stop recording' }));
    throw new Error(err.detail || 'Failed to stop recording');
  }
  return res.json();
}

async function fetchLayoutApi() {
  const res = await fetch(`${API_BASE}/api/layout`);
  if (!res.ok) throw new Error('Failed to fetch dashboard layout');
  return res.json();
}

async function saveLayoutApi(layout) {
  const res = await fetch(`${API_BASE}/api/layout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(layout),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to save layout' }));
    throw new Error(err.detail || 'Failed to save layout');
  }
  return res.json();
}

async function resetLayoutApi() {
  const res = await fetch(`${API_BASE}/api/layout/reset`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to reset dashboard layout');
  return res.json();
}

async function createCategoryApi(name, order = null) {
  const res = await fetch(`${API_BASE}/api/layout/categories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, order }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create category' }));
    throw new Error(err.detail || 'Failed to create category');
  }
  return res.json();
}

async function updateCategoryApi(catId, payload) {
  const res = await fetch(`${API_BASE}/api/layout/categories/${encodeURIComponent(catId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update category' }));
    throw new Error(err.detail || 'Failed to update category');
  }
  return res.json();
}

async function deleteCategoryApi(catId) {
  const res = await fetch(`${API_BASE}/api/layout/categories/${encodeURIComponent(catId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete category' }));
    throw new Error(err.detail || 'Failed to delete category');
  }
  return res.json();
}

// --- Icons Component Helpers ---
const Icons = {
  Globe: (props) => (
    <svg {...props} className={props.className || "w-5 h-5"} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  BarChart: (props) => (
    <svg {...props} className={props.className || "w-5 h-5"} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  Terminal: (props) => (
    <svg {...props} className={props.className || "w-5 h-5"} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  Database: (props) => (
    <svg {...props} className={props.className || "w-5 h-5"} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
    </svg>
  ),
  Box: (props) => (
    <svg {...props} className={props.className || "w-5 h-5"} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
    </svg>
  ),
  Store: (props) => (
    <svg {...props} className={props.className || "w-5 h-5"} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  ),
  ChevronLeft: (props) => (
    <svg {...props} className={props.className || "w-5 h-5"} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
    </svg>
  ),
  ChevronRight: (props) => (
    <svg {...props} className={props.className || "w-5 h-5"} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  ),
  RefreshCw: (props) => (
    <svg {...props} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  Dashboard: () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  ),
  Settings: () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  ToolConfig: () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  ),
  Terminal: () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  Popout: () => (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
    </svg>
  ),
  Play: () => (
    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
    </svg>
  ),
  Stop: () => (
    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clipRule="evenodd" />
    </svg>
  ),
  Refresh: () => (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  Key: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
    </svg>
  ),
  Copy: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  ),
  Check: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  Sliders: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
    </svg>
  ),
  FileCode: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  Grip: ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
    </svg>
  ),
  GripVertical: ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <circle cx="9" cy="5" r="1.5" />
      <circle cx="15" cy="5" r="1.5" />
      <circle cx="9" cy="12" r="1.5" />
      <circle cx="15" cy="12" r="1.5" />
      <circle cx="9" cy="19" r="1.5" />
      <circle cx="15" cy="19" r="1.5" />
    </svg>
  ),
  EyeOff: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
    </svg>
  ),
  Eye: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  ),
  ChevronDown: ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  ),
  ChevronRight: ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  ),
  Plus: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  ),
  Pencil: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
    </svg>
  ),
  ArrowUp: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
    </svg>
  ),
  ArrowDown: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  ),
  Trash: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  ),
  Search: ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  Reset: ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  Folder: ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
  ),
};

function copyToClipboard(text, key, setCopiedKey) {
  if (!text) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }).catch(() => {});
  } else {
    const el = document.createElement('textarea');
    el.value = text;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }
}

// --- Interactive In-Browser Terminal Modal (xterm.js) ---
function InteractiveTerminalModal({ tool, onClose, notify }) {
  const terminalRef = useRef(null);
  const termInstance = useRef(null);
  const wsRef = useRef(null);
  const fitAddonRef = useRef(null);
  const [connStatus, setConnStatus] = useState('connecting');

  useEffect(() => {
    if (!terminalRef.current) return;

    if (typeof Terminal === 'undefined') {
      console.error('Xterm library is not available');
      return;
    }

    const term = new Terminal({
      cursorBlink: true,
      fontFamily: "'JetBrains Mono', 'Courier New', monospace",
      fontSize: 13,
      lineHeight: 1.25,
      theme: {
        background: '#0B0F17',
        foreground: '#E2E8F0',
        cursor: '#FF3366',
        cursorAccent: '#FFFFFF',
        selectionBackground: 'rgba(255, 51, 102, 0.35)',
        black: '#1E293B',
        red: '#EF4444',
        green: '#10B981',
        yellow: '#F59E0B',
        blue: '#3B82F6',
        magenta: '#EC4899',
        cyan: '#06B6D4',
        white: '#F8FAFC',
        brightBlack: '#475569',
        brightRed: '#F87171',
        brightGreen: '#34D399',
        brightYellow: '#FBBF24',
        brightBlue: '#60A5FA',
        brightMagenta: '#F472B6',
        brightCyan: '#22D3EE',
        brightWhite: '#FFFFFF',
      },
      convertEol: true,
    });

    let fitAddon = null;
    if (typeof FitAddon !== 'undefined' && FitAddon.FitAddon) {
      fitAddon = new FitAddon.FitAddon();
      term.loadAddon(fitAddon);
      fitAddonRef.current = fitAddon;
    }

    term.open(terminalRef.current);
    if (fitAddon) {
      setTimeout(() => fitAddon.fit(), 60);
    }
    term.focus();
    termInstance.current = term;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/tools/${tool.id}/terminal/ws`;
    const ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    ws.onopen = () => {
      setConnStatus('connected');
      if (fitAddon) {
        fitAddon.fit();
        ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
      }
    };

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        term.write(event.data);
      } else if (event.data instanceof ArrayBuffer) {
        term.write(new Uint8Array(event.data));
      }
    };

    ws.onclose = () => {
      setConnStatus('disconnected');
      term.write('\r\n\r\n\x1b[33m[Interactive terminal session ended]\x1b[0m\r\n');
    };

    ws.onerror = () => {
      setConnStatus('disconnected');
      term.write('\r\n\x1b[31m[WebSocket connection encountered an error]\x1b[0m\r\n');
    };

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    const handleResize = () => {
      if (fitAddon) {
        fitAddon.fit();
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
        }
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
      term.dispose();
    };
  }, [tool.id]);

  const handleLaunchNative = async () => {
    try {
      const res = await launchNativeTerminalApi(tool.id);
      notify(res.message || 'Launched native iTerm session!');
    } catch (e) {
      notify(`Native launch error: ${e.message}`, 'error');
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="bg-[#0B0F17] rounded-2xl border border-gray-800 shadow-2xl max-w-5xl w-full flex flex-col h-[85vh] overflow-hidden text-gray-100">
        {/* Terminal Header */}
        <div className="px-6 py-3.5 bg-gray-900/90 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block"></span>
              <span className="w-3 h-3 rounded-full bg-yellow-500/80 inline-block"></span>
              <span className="w-3 h-3 rounded-full bg-green-500/80 inline-block"></span>
            </div>
            <div className="h-4 w-[1px] bg-gray-700 mx-1"></div>
            <div>
              <span className="text-sm font-bold text-white tracking-wide">{tool.name}</span>
              <span className="text-xs text-gray-400 font-mono ml-2">./run.sh</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {connStatus === 'connected' && (
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-2.5 py-0.5 rounded-full font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                PTY Active
              </span>
            )}
            {connStatus === 'connecting' && (
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-400 bg-amber-950/60 border border-amber-800/80 px-2.5 py-0.5 rounded-full font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span>
                Connecting...
              </span>
            )}
            {connStatus === 'disconnected' && (
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-400 bg-gray-800/60 border border-gray-700 px-2.5 py-0.5 rounded-full font-mono">
                Disconnected
              </span>
            )}

            <button
              onClick={handleLaunchNative}
              className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-white text-xs font-semibold transition border border-gray-700 inline-flex items-center gap-1.5 shadow-sm cursor-pointer"
              title="Open this interactive CLI in native iTerm"
            >
              <Icons.Popout />
              <span>Open in iTerm ↗</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 text-lg font-bold leading-none"
              title="Close Terminal"
            >
              &times;
            </button>
          </div>
        </div>

        {/* Terminal Screen */}
        <div className="flex-1 p-3 bg-[#0B0F17] overflow-hidden" ref={terminalRef}></div>

        {/* Terminal Footer */}
        <div className="px-6 py-2.5 bg-gray-900/90 border-t border-gray-800 flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-4">
            <span>Navigation: <kbd className="px-1.5 py-0.5 bg-gray-800 rounded text-gray-300 font-mono">↑</kbd> <kbd className="px-1.5 py-0.5 bg-gray-800 rounded text-gray-300 font-mono">↓</kbd> <kbd className="px-1.5 py-0.5 bg-gray-800 rounded text-gray-300 font-mono">Enter</kbd></span>
            <span>Exit: <kbd className="px-1.5 py-0.5 bg-gray-800 rounded text-gray-300 font-mono">Ctrl+C</kbd></span>
            <span className="text-gray-500">Auto-synced with config.json</span>
          </div>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium cursor-pointer"
          >
            Close Window
          </button>
        </div>
      </div>
    </div>
  );
}

// --- Prometheus Telemetry Looping Recording Modal ---
function TelemetryRecordingModal({ isOpen, onClose, notify, recordingState, setRecordingState }) {
  const [durationSec, setDurationSec] = useState(300);
  const [customDur, setCustomDur] = useState(300);
  const [intervalSec, setIntervalSec] = useState(15);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const isRecording = Boolean(recordingState?.is_recording);
  const progressPct = recordingState?.progress_pct || 0;
  const framesCount = recordingState?.frames_captured || 0;
  const elapsedSec = recordingState?.elapsed_seconds || 0;
  const targetDur = recordingState?.duration || (durationSec === 'custom' ? customDur : durationSec);

  const handleStartRecording = async () => {
    const finalDur = durationSec === 'custom' ? parseInt(customDur, 10) || 300 : parseInt(durationSec, 10);
    setIsSubmitting(true);
    try {
      const res = await startRecordingApi(finalDur, intervalSec);
      notify(res.message || `Started live telemetry recording for ${finalDur}s!`);
      const status = await fetchRecordingStatusApi();
      setRecordingState(status);
    } catch (e) {
      notify(`Recording error: ${e.message}`, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStopRecording = async () => {
    setIsSubmitting(true);
    try {
      const res = await stopRecordingApi();
      notify(res.message || 'Halted telemetry recording.');
      const status = await fetchRecordingStatusApi();
      setRecordingState(status);
    } catch (e) {
      notify(`Stop recording error: ${e.message}`, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-theme-lg max-w-xl w-full flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center text-red-600">
              <span className="w-3 h-3 rounded-full bg-red-600 animate-pulse"></span>
            </span>
            <div>
              <h4 className="text-base font-bold text-gray-900">Prometheus Telemetry Recorder</h4>
              <p className="text-xs text-gray-500">Capture live Netris streaming metrics to refresh offline simulation replay</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 text-lg font-bold leading-none"
          >
            &times;
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          {isRecording ? (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="relative flex h-3.5 w-3.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-red-600"></span>
                  </span>
                  <div>
                    <span className="text-xs font-bold text-red-900 uppercase tracking-wide">Recording Live Netris Stream</span>
                    <p className="text-xs text-red-700">Capturing topological metadata & interface telemetry frames</p>
                  </div>
                </div>
                <span className="text-sm font-mono font-bold text-red-800">{progressPct.toFixed(0)}%</span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-red-600 h-2.5 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(100, Math.max(2, progressPct))}%` }}
                ></div>
              </div>

              {/* Live Metrics Grid */}
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-3 bg-gray-50 rounded-xl border border-gray-200">
                  <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider block">Elapsed Time</span>
                  <span className="text-base font-bold font-mono text-gray-900">{elapsedSec}s / {targetDur}s</span>
                </div>
                <div className="p-3 bg-gray-50 rounded-xl border border-gray-200">
                  <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider block">Frames Captured</span>
                  <span className="text-base font-bold font-mono text-coral-600">{framesCount}</span>
                </div>
                <div className="p-3 bg-gray-50 rounded-xl border border-gray-200">
                  <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider block">Dataset Size</span>
                  <span className="text-base font-bold font-mono text-gray-900">{recordingState?.file_size_mb || 0} MB</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-gray-900 text-gray-300 text-xs font-mono space-y-1">
                <span className="text-gray-500 text-[10px] uppercase font-bold">Target Archive Destination:</span>
                <div className="text-emerald-400 break-all">{recordingState?.output_file || 'sim_data/telemetry_recording.json'} (+ .gz)</div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  onClick={handleStopRecording}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-theme-xs transition inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <Icons.Stop />
                  <span>Stop Recording Early & Save</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-gray-50 border border-gray-200 text-xs text-gray-600 space-y-1">
                <span className="font-semibold text-gray-900">How On-Demand Looping Works:</span>
                <p>
                  Connects to your configured Netris instance, captures topological state, and records periodic telemetry frames. Once complete, offline simulation mode (<code>--sim</code>) and instant historical TSDB backfill loop against this newly recorded dataset.
                </p>
              </div>

              {/* Duration Presets */}
              <div>
                <label className="block text-xs font-bold text-gray-800 mb-2">
                  Recording Duration ("Record for how long?")
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { label: '1 Minute', val: 60 },
                    { label: '3 Minutes', val: 180 },
                    { label: '5 Minutes', val: 300 },
                    { label: '10 Minutes', val: 600 },
                  ].map((preset) => (
                    <button
                      key={preset.val}
                      type="button"
                      onClick={() => setDurationSec(preset.val)}
                      className={`py-2 px-2.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                        durationSec === preset.val
                          ? 'bg-coral-50 border-coral-500 text-coral-700 shadow-2xs'
                          : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>

                <div className="mt-2.5 flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setDurationSec('custom')}
                    className={`py-1.5 px-3 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                      durationSec === 'custom'
                        ? 'bg-coral-50 border-coral-500 text-coral-700 shadow-2xs'
                        : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Custom Duration
                  </button>

                  {durationSec === 'custom' && (
                    <div className="flex items-center gap-1.5">
                      <input
                        type="number"
                        min="10"
                        max="7200"
                        value={customDur}
                        onChange={(e) => setCustomDur(parseInt(e.target.value, 10) || 60)}
                        className="w-24 px-2.5 py-1.5 text-xs font-mono border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-coral-500"
                      />
                      <span className="text-xs text-gray-500">seconds</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Frame Interval */}
              <div>
                <label className="block text-xs font-bold text-gray-800 mb-1.5">
                  Sampling Interval (Seconds per Frame)
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min="5"
                    max="60"
                    value={intervalSec}
                    onChange={(e) => setIntervalSec(parseInt(e.target.value, 10) || 15)}
                    className="w-24 px-2.5 py-1.5 text-xs font-mono border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-coral-500"
                  />
                  <span className="text-xs text-gray-500">
                    Expected frames: ~{Math.max(1, Math.round((durationSec === 'custom' ? customDur : durationSec) / intervalSec))} frames
                  </span>
                </div>
              </div>

              {recordingState?.status === 'completed' && (
                <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center justify-between">
                  <span className="font-semibold">✓ Previous recording completed!</span>
                  <span className="font-mono font-medium">{recordingState.frames_captured} frames ({recordingState.file_size_mb} MB)</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {!isRecording && (
          <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-gray-300 bg-white text-xs font-semibold hover:bg-gray-50 text-gray-700 cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleStartRecording}
              disabled={isSubmitting}
              className="px-5 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-theme-xs transition inline-flex items-center gap-1.5 cursor-pointer"
            >
              <span className="w-2 h-2 rounded-full bg-white animate-ping"></span>
              <span>Start Recording</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}



function ConfigFormEditor({ content, format, onChange }) {
  const [items, setItems] = React.useState([]);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (!content) {
      setItems([]);
      return;
    }
    try {
      if (format === 'json') {
        const obj = JSON.parse(content);
        const parsed = Object.keys(obj).map((k, idx) => ({
          id: idx,
          type: 'kv',
          key: k,
          value: typeof obj[k] === 'string' ? obj[k] : JSON.stringify(obj[k]),
          isSecret: /password|secret|key|token|pass/i.test(k),
          show: false
        }));
        setItems(parsed);
      } else if (format === 'yaml') {
        const parsed = content.split('\n').map((line, idx) => {
          const match = line.match(/^([a-zA-Z0-9_-]+):\s*(.*)$/);
          if (match && !line.startsWith(' ')) {
            return { id: idx, type: 'kv', key: match[1], value: match[2].replace(/^["'](.*)["']$/, '$1'), isSecret: /password|secret|key|token|pass/i.test(match[1]), show: false, raw: line };
          }
          return { id: idx, type: 'raw', raw: line };
        });
        setItems(parsed);
      } else {
        // shell / env
        const parsed = content.split('\n').map((line, idx) => {
          const match = line.match(/^([a-zA-Z0-9_.-]+)=(.*)$/);
          if (match) {
            return { id: idx, type: 'kv', key: match[1], value: match[2].replace(/^["'](.*)["']$/, '$1'), isSecret: /password|secret|key|token|pass/i.test(match[1]), show: false, raw: line };
          }
          return { id: idx, type: 'raw', raw: line };
        });
        setItems(parsed);
      }
      setError(null);
    } catch (e) {
      setError("Cannot parse this file format as a form. Please use the text editor fallback.");
      setItems([{id: 0, type: 'raw', raw: content}]); // fallback
    }
  }, [content, format]);

  const handleChange = (id, newVal) => {
    const newItems = items.map(item => item.id === id ? { ...item, value: newVal } : item);
    setItems(newItems);
    
    // Serialize back to string
    let newContent = '';
    if (format === 'json') {
      try {
        const obj = JSON.parse(content || '{}');
        newItems.forEach(item => {
           if (item.type === 'kv') {
             try {
               obj[item.key] = JSON.parse(item.value);
             } catch(e) {
               obj[item.key] = item.value;
             }
           }
        });
        newContent = JSON.stringify(obj, null, 2);
      } catch (e) {
        newContent = content; // Fallback
      }
    } else if (format === 'yaml') {
      newContent = newItems.map(item => {
        if (item.type === 'kv') {
           return `${item.key}: ${item.value}`;
        }
        return item.raw;
      }).join('\n');
    } else {
      newContent = newItems.map(item => {
        if (item.type === 'kv') {
           // wrap in quotes if there are spaces
           const v = item.value.includes(' ') ? `"${item.value}"` : item.value;
           return `${item.key}=${v}`;
        }
        return item.raw;
      }).join('\n');
    }
    onChange(newContent);
  };

  const toggleShow = (id) => {
    setItems(items.map(item => item.id === id ? { ...item, show: !item.show } : item));
  };

  const kvItems = items.filter(i => i.type === 'kv');

  if (error || kvItems.length === 0) {
    return (
      <textarea 
        value={content} 
        onChange={e => onChange(e.target.value)}
        className="flex-1 w-full bg-[#1E1E1E] text-[#D4D4D4] font-mono text-sm p-4 focus:outline-none resize-none"
        spellCheck={false}
      />
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-transparent p-6">
      <div className="max-w-4xl mx-auto space-y-4">
        {kvItems.map(item => (
          <div key={item.id} className="bg-gray-900/50 p-4 rounded-xl border border-gray-800 shadow-sm flex flex-col md:flex-row md:items-center gap-4">
            <div className="md:w-1/3 flex-shrink-0">
              <label className="block text-sm font-semibold text-gray-300 font-mono break-all">{item.key}</label>
            </div>
            <div className="flex-1 relative flex items-center">
              {item.isSecret && !item.show ? (
                <input 
                  type="password" 
                  value={item.value} 
                  onChange={(e) => handleChange(item.id, e.target.value)}
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-coral-500 focus:ring-1 focus:ring-coral-500 font-mono pr-12"
                />
              ) : (
                <input 
                  type="text" 
                  value={item.value} 
                  onChange={(e) => handleChange(item.id, e.target.value)}
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-coral-500 focus:ring-1 focus:ring-coral-500 font-mono pr-12"
                />
              )}
              {item.isSecret && (
                <button 
                  onClick={() => toggleShow(item.id)}
                  className="absolute right-3 text-gray-500 hover:text-gray-300 text-xs font-semibold"
                >
                  {item.show ? 'HIDE' : 'SHOW'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


function ToolDetailView(props) {
  return <ErrorBoundary><ToolDetailViewContent {...props} /></ErrorBoundary>;
}

function ToolDetailViewContent({
 tool, onStart, onStop, onRestart, fetchLogs, configCatalog, fetchConfigFile, saveConfigFile, openTerminal, actionLoading, openSessionModal, handleUpdateTool }) {
  const [logs, setLogs] = React.useState([]);
  const [activeSubTab, setActiveSubTab] = React.useState('overview');
  const [fileContent, setFileContent] = React.useState('');
  const [selectedFile, setSelectedFile] = React.useState(null);
  const [fileDirty, setFileDirty] = React.useState(false);
  const [fileSaving, setFileSaving] = React.useState(false);
  const [loadingFile, setLoadingFile] = React.useState(false);

  if (!tool) return null; const toolConfig = configCatalog.find(c => c.tool_id === tool.id);
  
  const activeFileObj = toolConfig?.files.find(f => f.id === selectedFile);
  const activeFileFormat = activeFileObj ? activeFileObj.format : 'shell';

  React.useEffect(() => {
    setActiveSubTab('overview');
  }, [tool.id]);

  React.useEffect(() => {
    let interval;
    if (activeSubTab === 'logs') {
      const loadLogs = () => {
        fetchLogs(tool.id).then(res => setLogs(res.lines || [])).catch(console.error);
      };
      loadLogs();
      interval = setInterval(loadLogs, 3000);
    }
    return () => clearInterval(interval);
  }, [activeSubTab, tool.id, fetchLogs]);

  React.useEffect(() => {
    if (toolConfig && toolConfig.files.length > 0) {
      handleSelectFile(toolConfig.files[0].id);
    } else {
      setSelectedFile(null);
      setFileContent('');
    }
  }, [tool.id, configCatalog]);

  const handleSelectFile = async (fileId) => {
    setSelectedFile(fileId);
    setLoadingFile(true);
    setFileDirty(false);
    try {
      const data = await fetchConfigFile(tool.id, fileId);
      setFileContent(data.content);
    } catch (e) {
      setFileContent('Error loading file');
    } finally {
      setLoadingFile(false);
    }
  };

  const handleSave = async () => {
    setFileSaving(true);
    try {
      await saveConfigFile(tool.id, selectedFile, fileContent);
      setFileDirty(false);
    } catch (e) {
      alert("Save failed: " + e.message);
    } finally {
      setFileSaving(false);
    }
  };

  const isInstalling = tool.is_optional && !tool.is_downloaded;

  return (
    <div className="flex flex-col h-full min-h-[75vh] bg-white rounded-xl shadow-theme-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h3 className="text-xl font-bold text-gray-900">{tool.name}</h3>
            {tool.status === 'running' ? (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-success-50 text-success-700 border border-success-200">RUNNING</span>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 border border-gray-200">STOPPED</span>
            )}
            {isInstalling && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">MARKETPLACE EXTENSION</span>
            )}
          </div>
          <p className="text-sm text-gray-500">{tool.description}</p>
        </div>
        
        <div className="flex items-center gap-3">
          {tool.tool_type === 'interactive' && tool.status === 'running' && (
            <button onClick={() => openTerminal(tool)} className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800">
              Open Terminal
            </button>
          )}
          
          {(tool.is_optional && tool.is_downloaded) && (
            <button 
              onClick={() => handleUpdateTool(tool.id)} 
              disabled={actionLoading[tool.id]} 
              className="px-4 py-2 bg-blue-50 text-blue-700 border border-blue-200 rounded-lg text-sm font-semibold hover:bg-blue-100 shadow-theme-xs flex items-center gap-2"
            >
              <Icons.RefreshCw className={`w-3.5 h-3.5 ${actionLoading[tool.id] ? 'animate-spin' : ''}`} />
              Update Extension
            </button>
          )}
          {tool.status === 'running' ? (
            <>
              <button onClick={() => onRestart(tool.id)} disabled={actionLoading[tool.id]} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-semibold hover:bg-gray-50">
                Restart
              </button>
              <button onClick={() => onStop(tool.id)} disabled={actionLoading[tool.id]} className="px-4 py-2 bg-white border border-red-200 text-error-600 rounded-lg text-sm font-semibold hover:bg-red-50">
                Stop
              </button>
            </>
          ) : (
            <button 
              onClick={() => {
                if (!isInstalling && tool.session_options) {
                  openSessionModal(tool);
                } else {
                  onStart(tool.id);
                }
              }} 
              disabled={actionLoading[tool.id]} 
              className="px-4 py-2 bg-coral-600 text-white rounded-lg text-sm font-semibold hover:bg-coral-700 shadow-theme-xs"
            >
              {actionLoading[tool.id] ? 'Starting...' : isInstalling ? 'Install & Start' : tool.session_options ? 'Configure & Start' : 'Start'}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      {!isInstalling && (
      <div className="flex border-b border-gray-200 px-4">
        <button 
          onClick={() => setActiveSubTab('overview')} 
          className={`px-4 py-3 text-sm font-medium border-b-2 ${activeSubTab === 'overview' ? 'border-coral-600 text-coral-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          Overview
        </button>
        <button 
          onClick={() => setActiveSubTab('config')} 
          className={`px-4 py-3 text-sm font-medium border-b-2 ${activeSubTab === 'config' ? 'border-coral-600 text-coral-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          Configuration Files
        </button>
        <button 
          onClick={() => setActiveSubTab('logs')} 
          className={`px-4 py-3 text-sm font-medium border-b-2 ${activeSubTab === 'logs' ? 'border-coral-600 text-coral-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
        >
          Process Logs
        </button>
      </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col relative bg-[#1E1E1E]">
        {isInstalling ? (
          <div className="flex-1 flex items-center justify-center bg-gray-50 text-gray-500">
             <div className="text-center">
               <svg className="w-12 h-12 mx-auto text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
               <h3 className="text-lg font-medium text-gray-900 mb-1">Tool Not Installed</h3>
               <p className="text-sm">Click "Install & Start" above to clone and initialize this tool.</p>
             </div>
          </div>
        ) : activeSubTab === 'overview' ? (
          <div className="flex-1 overflow-y-auto bg-gray-50 p-8 text-gray-800">
            <div className="max-w-3xl mx-auto space-y-6">
              <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-theme-xs">
                <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">About this tool</h3>
                <p className="text-gray-600 text-sm leading-relaxed whitespace-pre-wrap">{tool.description || 'No description available for this tool.'}</p>
              </div>
              
              {tool.status === 'running' && (
                <div className="bg-white rounded-xl border border-success-200 p-6 shadow-theme-xs">
                  <h3 className="text-sm font-bold text-success-800 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-success-500"></span> Live Metrics & Endpoints
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                     <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 shadow-inner">
                        <div className="text-xs text-gray-500 mb-1">Process State</div>
                        <div className="font-bold text-success-700 text-sm">Running</div>
                     </div>
                     {tool.uptime && (
                       <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 shadow-inner">
                          <div className="text-xs text-gray-500 mb-1">Uptime</div>
                          <div className="font-mono text-gray-800 text-sm">{tool.uptime}</div>
                       </div>
                     )}
                     {tool.port && (
                       <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 shadow-inner">
                          <div className="text-xs text-gray-500 mb-1">Local Port</div>
                          <div className="font-mono text-gray-800 text-sm">{tool.port}</div>
                       </div>
                     )}
                     {tool.popout_url && (
                       <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 shadow-inner col-span-full">
                          <div className="text-xs text-gray-500 mb-2">Web Interface</div>
                          <a href={tool.popout_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-md text-xs font-semibold transition">
                            Open {tool.name} in New Tab
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                          </a>
                       </div>
                     )}
                  </div>
                </div>
              )}

              {tool.credentials && tool.credentials.length > 0 && tool.credentials.some(c => !c.no_auth) && (
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-theme-xs">
                  <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">Access Credentials</h3>
                  <div className="space-y-3">
                    {tool.credentials.filter(c => !c.no_auth).map((cred, idx) => (
                      <div key={idx} className="flex flex-col gap-1 p-3 bg-gray-50 rounded-lg border border-gray-100">
                        <div className="text-xs text-gray-500 font-semibold">{cred.label || 'Login Info'}</div>
                        <div className="text-sm text-gray-800">
                          <span className="font-medium mr-2">User:</span> <code className="bg-white px-1.5 py-0.5 rounded border border-gray-200">{cred.username}</code>
                        </div>
                        <div className="text-sm text-gray-800">
                          <span className="font-medium mr-2">Pass:</span> <code className="bg-white px-1.5 py-0.5 rounded border border-gray-200">{cred.password}</code>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : activeSubTab === 'logs' ? (
          <div className="flex-1 overflow-y-auto p-4 font-mono text-xs text-gray-300">
            {logs.length === 0 ? (
              <div className="text-gray-500 italic text-center mt-10">No logs available</div>
            ) : (
              logs.map((l, i) => <div key={i} className="mb-1 whitespace-pre-wrap">{l}</div>)
            )}
          </div>
        ) : (
          <div className="flex-1 flex overflow-hidden">
            {toolConfig && toolConfig.files.length > 0 ? (
              <>
                <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
                  {toolConfig.files.map(f => (
                    <button 
                      key={f.id} 
                      onClick={() => handleSelectFile(f.id)}
                      className={`text-left px-4 py-3 text-sm font-medium border-b border-gray-200 ${selectedFile === f.id ? 'bg-white text-coral-600 border-l-4 border-l-coral-600' : 'text-gray-700 hover:bg-gray-100 border-l-4 border-l-transparent'}`}
                    >
                      {f.name}
                    </button>
                  ))}
                </div>
                <div className="flex-1 flex flex-col bg-[#1E1E1E]">
                  <div className="h-12 bg-[#2D2D2D] border-b border-[#404040] flex items-center justify-between px-4">
                    <span className="text-xs font-mono text-gray-300">{selectedFile} {fileDirty && '*'}</span>
                    <button 
                      onClick={handleSave} 
                      disabled={!fileDirty || fileSaving}
                      className={`text-xs px-3 py-1 rounded font-semibold ${fileDirty ? 'bg-coral-600 text-white hover:bg-coral-700' : 'bg-[#404040] text-gray-500 cursor-not-allowed'}`}
                    >
                      {fileSaving ? 'Saving...' : 'Save File'}
                    </button>
                  </div>
                  <div className="flex-1 overflow-auto bg-[#1E1E1E]">
                    <ConfigFormEditor 
                      content={fileContent} 
                      format={activeFileFormat} 
                      onChange={val => { setFileContent(val); setFileDirty(true); }} 
                    />
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500 italic bg-gray-50">
                No configuration files exposed for this tool.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center text-red-600 bg-red-50 rounded-xl border border-red-200 m-8">
          <h2 className="text-xl font-bold mb-2">Something went wrong.</h2>
          <pre className="text-sm font-mono overflow-auto text-left p-4 bg-red-100 rounded">{this.state.error.toString()}</pre>
          <button onClick={() => this.setState({hasError: false})} className="mt-4 px-4 py-2 bg-white border border-red-200 rounded shadow-sm text-gray-700">Try Again</button>
        </div>
      );
    }
    return this.props.children;
  }
}

// --- App Root Component ---


const getToolIcon = (tool) => {
  const tid = tool.id.toLowerCase();
  if (tid.includes('portal') || tid.includes('ui')) return <Icons.Globe />;
  if (tid.includes('prometheus') || tid.includes('telemetry') || tid.includes('exporter')) return <Icons.BarChart />;
  if (tid.includes('cli') || tid.includes('tf') || tid.includes('terraform')) return <Icons.Terminal />;
  if (tid.includes('netbox') || tid.includes('ipam')) return <Icons.Database />;
  return <Icons.Box />;
};

function App() {
  const [activeTab, setActiveTab] = useState('overview'); // overview, global-config, tool-configs, logs, catalogue
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState({});
  const [selectedToolLogs, setSelectedToolLogs] = useState(null);
  const [logContent, setLogContent] = useState([]);
  const [autoRefreshLogs, setAutoRefreshLogs] = useState(true);
  const [notification, setNotification] = useState(null);
  const [copiedKey, setCopiedKey] = useState(null);

  // Session Config Modal State
  const [sessionModalTool, setSessionModalTool] = useState(null);
  const [sessionParams, setSessionParams] = useState({});

  // Global Config State
  const [globalConfig, setGlobalConfig] = useState({
    netris_url: 'https://adam-ctl.netris.io',
    netris_username: 'netris',
    netris_password: '',
    netris_verify_ssl: false,
    default_tenant: 'Demo',
    default_site: 'SantaClara',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);

  // Multi-File Tool Raw Config State
  const [configCatalog, setConfigCatalog] = useState([]);
  const [selectedToolConfigId, setSelectedToolConfigId] = useState('netris-prometheus-exporter');
  const [selectedFileId, setSelectedFileId] = useState('config.env');
  const [currentFileMeta, setCurrentFileMeta] = useState(null);
  const [toolConfigContent, setToolConfigContent] = useState('');
  const [toolConfigLoading, setToolConfigLoading] = useState(false);
  const [fileDirty, setFileDirty] = useState(false);
  const [fileSaving, setFileSaving] = useState(false);

  // Interactive Terminal Modal State
  const [terminalModalTool, setTerminalModalTool] = useState(null);

  // Prometheus Telemetry Recording Modal State
  const [recordingModalOpen, setRecordingModalOpen] = useState(false);
  const [recordingState, setRecordingState] = useState(null);

  // Dashboard Layout, Custom Categories, Drag-and-Drop & Hidden Tools State
  const [layout, setLayout] = useState({ categories: [], tool_placements: {} });
  const [layoutLoading, setLayoutLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isOtherOpen, setIsOtherOpen] = useState(false);
  const [catalogueSearchQuery, setCatalogueSearchQuery] = useState('');
  const [showHiddenDrawer, setShowHiddenDrawer] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null); // { id, name }
  const [newCategoryModalOpen, setNewCategoryModalOpen] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [moveCategoryModalTool, setMoveCategoryModalTool] = useState(null); // tool for manual category move modal

  // Drag and Drop State
  const [draggedToolId, setDraggedToolId] = useState(null);
  const [dragOverCategoryId, setDragOverCategoryId] = useState(null);
  const [dragOverToolId, setDragOverToolId] = useState(null);
  const [draggedCategoryId, setDraggedCategoryId] = useState(null);
  const [dragOverCategorySectionId, setDragOverCategorySectionId] = useState(null);

  const notify = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4500);
  };

  const loadRecordingStatus = async () => {
    try {
      const status = await fetchRecordingStatusApi();
      setRecordingState(status);
    } catch (e) {
      // ignore polling errors
    }
  };

  const handleLaunchNative = async (toolId) => {
    try {
      const res = await launchNativeTerminalApi(toolId);
      notify(res.message || 'Launched native iTerm session!');
    } catch (e) {
      notify(`Native launch error: ${e.message}`, 'error');
    }
  };

  // Poll tools and recording status every 3 seconds
  useEffect(() => {
    loadTools();
    loadLayout();
    loadRecordingStatus();
    const interval = setInterval(() => {
      loadTools();
      loadRecordingStatus();
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // Fetch global config and config catalog on mount
  useEffect(() => {
    fetchGlobalConfig()
      .then((cfg) => setGlobalConfig(cfg))
      .catch((e) => console.error('Global config load error', e));

    fetchConfigCatalog()
      .then((cat) => {
        setConfigCatalog(cat);
        if (cat.length > 0) {
          const firstTool = cat[0];
          setSelectedToolConfigId(firstTool.tool_id);
          if (firstTool.files.length > 0) {
            setSelectedFileId(firstTool.files[0].id);
          }
        }
      })
      .catch((e) => console.error('Config catalog load error', e));
  }, []);

  // Load specific config file whenever tool or file selection changes
  useEffect(() => {
    if (activeTab === 'tool-configs' && selectedToolConfigId && selectedFileId) {
      loadFileContent(selectedToolConfigId, selectedFileId);
    }
  }, [activeTab, selectedToolConfigId, selectedFileId]);

  const loadTools = async () => {
    try {
      const data = await fetchTools();
      setTools(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadLayout = async () => {
    try {
      const data = await fetchLayoutApi();
      setLayout(data);
      localStorage.setItem('netris_dashboard_layout', JSON.stringify(data));
    } catch (e) {
      console.warn('Backend layout load failed, using local cache if available', e);
      const cached = localStorage.getItem('netris_dashboard_layout');
      if (cached) {
        try { setLayout(JSON.parse(cached)); } catch (_) {}
      }
    } finally {
      setLayoutLoading(false);
    }
  };

  const persistLayout = async (updatedLayout) => {
    setLayout(updatedLayout);
    localStorage.setItem('netris_dashboard_layout', JSON.stringify(updatedLayout));
    try {
      await saveLayoutApi(updatedLayout);
    } catch (e) {
      notify(`Failed to persist layout: ${e.message}`, 'error');
    }
  };

  const handleResetLayout = async () => {
    if (!window.confirm('Reset all categories and tool order back to default factory settings?')) return;
    try {
      const def = await resetLayoutApi();
      setLayout(def);
      localStorage.setItem('netris_dashboard_layout', JSON.stringify(def));
      notify('Dashboard layout reset to factory default!');
    } catch (e) {
      notify(`Failed to reset layout: ${e.message}`, 'error');
    }
  };

  const handleToggleCategoryCollapse = (catId) => {
    const updatedCategories = (layout.categories || []).map((c) =>
      c.id === catId ? { ...c, collapsed: !c.collapsed } : c
    );
    persistLayout({ ...layout, categories: updatedCategories });
  };

  const handleMoveCategoryOrder = (catId, direction) => {
    const sorted = [...(layout.categories || [])].sort((a, b) => a.order - b.order);
    const index = sorted.findIndex((c) => c.id === catId);
    if (index === -1) return;
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= sorted.length) return;

    const temp = sorted[index];
    sorted[index] = sorted[targetIndex];
    sorted[targetIndex] = temp;

    sorted.forEach((c, idx) => {
      c.order = idx;
    });

    persistLayout({ ...layout, categories: sorted });
  };

  const handleCreateCategory = async (e) => {
    e.preventDefault();
    if (!newCategoryName.trim()) return;
    try {
      const newCat = await createCategoryApi(newCategoryName.trim());
      const updatedCategories = [...(layout.categories || []), newCat].sort((a, b) => a.order - b.order);
      persistLayout({ ...layout, categories: updatedCategories });
      setNewCategoryName('');
      setNewCategoryModalOpen(false);
      notify(`Created category "${newCat.name}"`);
    } catch (e) {
      notify(`Failed to create category: ${e.message}`, 'error');
    }
  };

  const handleSaveRenameCategory = async (catId) => {
    if (!editingCategory || !editingCategory.name.trim()) {
      setEditingCategory(null);
      return;
    }
    const newName = editingCategory.name.trim();
    try {
      await updateCategoryApi(catId, { name: newName });
      const updatedCategories = (layout.categories || []).map((c) =>
        c.id === catId ? { ...c, name: newName } : c
      );
      persistLayout({ ...layout, categories: updatedCategories });
      notify(`Renamed category to "${newName}"`);
    } catch (e) {
      notify(`Failed to rename category: ${e.message}`, 'error');
    } finally {
      setEditingCategory(null);
    }
  };

  const handleDeleteCategory = async (catId) => {
    const cat = (layout.categories || []).find((c) => c.id === catId);
    if (!cat) return;
    const toolsInCat = Object.entries(layout.tool_placements || {}).filter(
      ([_, p]) => p.category_id === catId && !p.hidden
    );
    const confirmMsg = toolsInCat.length > 0
      ? `Delete category "${cat.name}"? Its ${toolsInCat.length} tool(s) will be moved to "${layout.categories[0]?.name}".`
      : `Delete empty category "${cat.name}"?`;
    if (!window.confirm(confirmMsg)) return;

    try {
      await deleteCategoryApi(catId);
      const fresh = await fetchLayoutApi();
      setLayout(fresh);
      localStorage.setItem('netris_dashboard_layout', JSON.stringify(fresh));
      notify(`Deleted category "${cat.name}"`);
    } catch (e) {
      notify(`Delete failed: ${e.message}`, 'error');
    }
  };

  const handleHideTool = (toolId) => {
    const tool = tools.find((t) => t.id === toolId);
    const current = (layout.tool_placements || {})[toolId] || {
      category_id: layout.categories[0]?.id || 'cat-general',
      order: 0,
    };
    const updatedPlacements = {
      ...(layout.tool_placements || {}),
      [toolId]: { ...current, hidden: true }
    };
    persistLayout({ ...layout, tool_placements: updatedPlacements });
    notify(`Removed "${tool ? tool.name : toolId}" from active dashboard. Available in Archived Tools.`);
  };

  const handleRestoreTool = (toolId, targetCatId = null) => {
    const tool = tools.find((t) => t.id === toolId);
    const current = (layout.tool_placements || {})[toolId] || {};
    const catId = targetCatId || current.category_id || (layout.categories[0] && layout.categories[0].id);
    const existingInCat = Object.entries(layout.tool_placements || {}).filter(
      ([id, p]) => p.category_id === catId && !p.hidden && id !== toolId
    );
    const newOrder = existingInCat.length;

    const updatedPlacements = {
      ...(layout.tool_placements || {}),
      [toolId]: { category_id: catId, order: newOrder, hidden: false }
    };
    persistLayout({ ...layout, tool_placements: updatedPlacements });
    notify(`Restored "${tool ? tool.name : toolId}" to dashboard!`);
  };

  const handleMoveToolCategory = (toolId, targetCatId) => {
    const tool = tools.find((t) => t.id === toolId);
    const current = (layout.tool_placements || {})[toolId] || { order: 0, hidden: false };
    const existingInCat = Object.entries(layout.tool_placements || {}).filter(
      ([id, p]) => p.category_id === targetCatId && !p.hidden && id !== toolId
    );
    const newOrder = existingInCat.length;

    const updatedPlacements = {
      ...(layout.tool_placements || {}),
      [toolId]: { ...current, category_id: targetCatId, order: newOrder, hidden: false }
    };
    persistLayout({ ...layout, tool_placements: updatedPlacements });
    const targetCat = (layout.categories || []).find((c) => c.id === targetCatId);
    notify(`Moved "${tool ? tool.name : toolId}" to "${targetCat ? targetCat.name : targetCatId}"`);
    setMoveCategoryModalTool(null);
  };

  // Drag and drop handlers
  const handleToolDragStart = (e, toolId) => {
    e.dataTransfer.setData('text/plain', toolId);
    e.dataTransfer.effectAllowed = 'move';
    setDraggedToolId(toolId);
  };

  const handleToolDragOver = (e, catId, targetToolId = null) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverCategoryId !== catId) {
      setDragOverCategoryId(catId);
    }
    if (targetToolId && dragOverToolId !== targetToolId) {
      setDragOverToolId(targetToolId);
    }
  };

  const handleToolDrop = (e, targetCatId, targetToolId = null) => {
    e.preventDefault();
    e.stopPropagation();
    const toolId = draggedToolId || e.dataTransfer.getData('text/plain');
    if (!toolId) return;

    const currentPlacement = (layout.tool_placements || {})[toolId] || { order: 0, hidden: false };
    const toolsInTargetCat = tools
      .filter((t) => {
        const p = (layout.tool_placements || {})[t.id];
        return p && p.category_id === targetCatId && !p.hidden && t.id !== toolId;
      })
      .sort((a, b) => {
        const ordA = ((layout.tool_placements || {})[a.id]?.order) ?? 0;
        const ordB = ((layout.tool_placements || {})[b.id]?.order) ?? 0;
        return ordA - ordB;
      })
      .map((t) => t.id);

    if (targetToolId && toolsInTargetCat.includes(targetToolId)) {
      const idx = toolsInTargetCat.indexOf(targetToolId);
      toolsInTargetCat.splice(idx, 0, toolId);
    } else {
      toolsInTargetCat.push(toolId);
    }

    const updatedPlacements = { ...(layout.tool_placements || {}) };
    toolsInTargetCat.forEach((tid, idx) => {
      const prevP = updatedPlacements[tid] || { hidden: false };
      updatedPlacements[tid] = { ...prevP, category_id: targetCatId, order: idx, hidden: false };
    });

    if (currentPlacement.category_id !== targetCatId) {
      const sourceTools = tools
        .filter((t) => {
          const p = updatedPlacements[t.id];
          return p && p.category_id === currentPlacement.category_id && !p.hidden && t.id !== toolId;
        })
        .sort((a, b) => {
          const ordA = (updatedPlacements[a.id]?.order) ?? 0;
          const ordB = (updatedPlacements[b.id]?.order) ?? 0;
          return ordA - ordB;
        })
        .map((t) => t.id);

      sourceTools.forEach((tid, idx) => {
        updatedPlacements[tid] = { ...updatedPlacements[tid], order: idx };
      });
    }

    persistLayout({ ...layout, tool_placements: updatedPlacements });

    setDraggedToolId(null);
    setDragOverCategoryId(null);
    setDragOverToolId(null);
  };

  const handleCategoryDragStart = (e, catId) => {
    e.dataTransfer.setData('category-id', catId);
    e.dataTransfer.effectAllowed = 'move';
    setDraggedCategoryId(catId);
  };

  const handleCategoryDrop = (e, targetCatId) => {
    e.preventDefault();
    e.stopPropagation();
    const catId = draggedCategoryId || e.dataTransfer.getData('category-id');
    if (!catId || catId === targetCatId) {
      setDraggedCategoryId(null);
      setDragOverCategorySectionId(null);
      return;
    }

    const sortedCats = [...(layout.categories || [])].sort((a, b) => a.order - b.order);
    const sourceIdx = sortedCats.findIndex((c) => c.id === catId);
    const targetIdx = sortedCats.findIndex((c) => c.id === targetCatId);
    if (sourceIdx === -1 || targetIdx === -1) return;

    const [removed] = sortedCats.splice(sourceIdx, 1);
    sortedCats.splice(targetIdx, 0, removed);

    sortedCats.forEach((c, idx) => {
      c.order = idx;
    });

    persistLayout({ ...layout, categories: sortedCats });
    setDraggedCategoryId(null);
    setDragOverCategorySectionId(null);
  };


  const loadFileContent = async (toolId, fileId) => {
    setToolConfigLoading(true);
    setFileDirty(false);
    try {
      const data = await fetchConfigFile(toolId, fileId);
      setToolConfigContent(data.content || '');
      setCurrentFileMeta(data);
    } catch (e) {
      setToolConfigContent('# Error loading configuration file: ' + e.message);
      setCurrentFileMeta(null);
    } finally {
      setToolConfigLoading(false);
    }
  };

  // Switch to Tool Configurations tab and pre-select tool and file
  const openConfigEditor = (toolId, fileId = null) => {
    setSelectedToolConfigId(toolId);
    const toolEntry = configCatalog.find((c) => c.tool_id === toolId);
    if (toolEntry && toolEntry.files.length > 0) {
      const targetFile = fileId || toolEntry.files[0].id;
      setSelectedFileId(targetFile);
    }
    setActiveTab('tool-configs');
  };

  // Open Session Options Modal
  const openSessionModal = (tool) => {
    if (!tool.session_options) return;
    const initial = {};
    if (tool.session_options.fields) {
      tool.session_options.fields.forEach((f) => {
        initial[f.id] = f.default;
      });
    }
    setSessionParams(initial);
    setSessionModalTool(tool);
  };

  // Launch tool with custom session parameters
  const handleLaunchWithSession = async () => {
    if (!sessionModalTool) return;
    const toolId = sessionModalTool.id;
    setActionLoading((prev) => ({ ...prev, [toolId]: true }));
    try {
      const res = await startToolApi(toolId, { session_params: sessionParams });
      notify(res.message || `Launched ${sessionModalTool.name} with custom session!`);
      setSessionModalTool(null);
      await loadTools();
    } catch (e) {
      notify(`Launch failed: ${e.message}`, 'error');
    } finally {
      setActionLoading((prev) => ({ ...prev, [toolId]: false }));
    }
  };

  // Standard Tool Actions
  const handleStart = async (toolId) => {
    setActionLoading((prev) => ({ ...prev, [toolId]: true }));
    try {
      const res = await startToolApi(toolId);
      notify(res.message || `Started ${toolId}`);
      await loadTools();
    } catch (e) {
      notify(`Start failed: ${e.message}`, 'error');
    } finally {
      setActionLoading((prev) => ({ ...prev, [toolId]: false }));
    }
  };

  const handleStop = async (toolId) => {
    setActionLoading((prev) => ({ ...prev, [toolId]: true }));
    try {
      const res = await stopToolApi(toolId);
      notify(res.message || `Stopped ${toolId}`);
      await loadTools();
    } catch (e) {
      notify(`Stop failed: ${e.message}`, 'error');
    } finally {
      setActionLoading((prev) => ({ ...prev, [toolId]: false }));
    }
  };

  const handleRestart = async (toolId) => {
    setActionLoading((prev) => ({ ...prev, [toolId]: true }));
    try {
      const res = await restartToolApi(toolId);
      notify(res.message || `Restarted ${toolId}`);
      await loadTools();
    } catch (e) {
      notify(`Restart failed: ${e.message}`, 'error');
    } finally {
      setActionLoading((prev) => ({ ...prev, [toolId]: false }));
    }
  };

  const handleRunScenario = async (scenarioId) => {
    try {
      const res = await runScenarioApi(scenarioId);
      notify(res.message);
      await loadTools();
    } catch (e) {
      notify(`Scenario error: ${e.message}`, 'error');
    }
  };

  const handleSaveGlobalConfig = async (e) => {
    e.preventDefault();
    setConfigSaving(true);
    try {
      const res = await saveGlobalConfig(globalConfig);
      notify(res.message || 'Global configuration propagated to all tools!');
    } catch (e) {
      notify(`Save error: ${e.message}`, 'error');
    } finally {
      setConfigSaving(false);
    }
  };

  const handleSaveFileContent = async () => {
    if (!selectedToolConfigId || !selectedFileId) return;
    setFileSaving(true);
    try {
      const res = await saveConfigFile(selectedToolConfigId, selectedFileId, toolConfigContent);
      notify(res.message || `Saved ${selectedFileId} directly to disk!`);
      setFileDirty(false);
      // Refresh tools list so any updated passwords in .env reflect immediately in credentials badges
      await loadTools();
    } catch (e) {
      notify(`Error saving file: ${e.message}`, 'error');
    } finally {
      setFileSaving(false);
    }
  };

  // Open Log Modal & Live Poll
  const openLogs = (toolId) => {
    setSelectedToolLogs(toolId);
    fetchLogs(toolId)
      .then((data) => setLogContent(data.lines || []))
      .catch((e) => setLogContent([`Error loading logs: ${e.message}`]));
  };

  useEffect(() => {
    if (!selectedToolLogs || !autoRefreshLogs) return;
    const interval = setInterval(() => {
      fetchLogs(selectedToolLogs)
        .then((data) => setLogContent(data.lines || []))
        .catch(() => {});
    }, 2000);
    return () => clearInterval(interval);
  }, [selectedToolLogs, autoRefreshLogs]);

  // Compute Metrics
  const runningCount = tools.filter((t) => t.is_running).length;
  const stoppedCount = tools.length - runningCount;

  // Active tool catalog entry
  const activeToolCatalogEntry = configCatalog.find((c) => c.tool_id === selectedToolConfigId);

  // Layout & Category Computations
  const sortedCategories = [...(layout.categories || [])].sort((a, b) => a.order - b.order);

  const getToolsForCategory = (catId) => {
    return tools
      .filter((t) => {
        const p = (layout.tool_placements || {})[t.id];
        if (!p) return false;
        if (p.hidden) return false;
        if (p.category_id !== catId) return false;
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          return (
            t.name.toLowerCase().includes(q) ||
            t.description.toLowerCase().includes(q) ||
            t.id.toLowerCase().includes(q) ||
            (t.category && t.category.toLowerCase().includes(q))
          );
        }
        return true;
      })
      .sort((a, b) => {
        const ordA = ((layout.tool_placements || {})[a.id]?.order) ?? 0;
        const ordB = ((layout.tool_placements || {})[b.id]?.order) ?? 0;
        return ordA - ordB;
      });
  };

  const unplacedOptionalTools = tools.filter((t) => !((layout.tool_placements || {})[t.id]) && t.is_optional);

  const hiddenTools = tools.filter((t) => {
    const p = (layout.tool_placements || {})[t.id];
    return p && p.hidden;
  });

  return (
    <div className="flex min-h-screen bg-gray-50 font-outfit text-gray-700">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed top-5 right-5 z-[999999] px-4 py-3 rounded-lg shadow-theme-lg text-sm font-medium border flex items-center gap-2 animate-bounce ${
            notification.type === 'error'
              ? 'bg-error-50 text-error-600 border-red-200'
              : 'bg-success-50 text-success-600 border-emerald-200'
          }`}
        >
          <span>{notification.message}</span>
        </div>
      )}

      {/* --- Sidebar (280px fixed) --- */}
      <aside className={`bg-white border-r border-gray-200 fixed top-0 bottom-0 left-0 flex flex-col z-30 shadow-theme-xs transition-all duration-300 ${isSidebarCollapsed ? 'w-[80px]' : 'w-[280px]'}`}>
        {/* Brand / Header */}
        <div className="h-[72px] px-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-coral-50 flex items-center justify-center border border-coral-200 shadow-2xs flex-shrink-0">
              <div className="w-4 h-4 rounded-full bg-coral-500"></div>
            </div>
            {!isSidebarCollapsed && (
              <div className="whitespace-nowrap">
                <h1 className="text-base font-bold text-gray-900 tracking-tight">Proof of Concept</h1>
                <p className="text-[10px] text-gray-400">Netris & AI Fabric Hub</p>
              </div>
            )}
          </div>
          <button 
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition hidden md:block flex-shrink-0"
            title={isSidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {isSidebarCollapsed ? <Icons.ChevronRight className="w-4 h-4" /> : <Icons.ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1.5 flex-1 overflow-y-auto overflow-x-hidden">
          <button
            onClick={() => setActiveTab('overview')}
            title="Overview Hub"
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'overview'
                ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                : 'text-gray-700 hover:bg-gray-100'
            } ${isSidebarCollapsed ? 'justify-center' : ''}`}
          >
            <Icons.Dashboard className="w-5 h-5 flex-shrink-0" />
            {!isSidebarCollapsed && <span>Overview Hub</span>}
          </button>
          
          <div className={`text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 mt-6 px-2 flex items-center ${isSidebarCollapsed ? 'justify-center' : 'justify-between'}`}>
            {!isSidebarCollapsed && <span>Installed Tools</span>}
            <span className={`inline-flex items-center justify-center text-xs font-bold text-blue-700 bg-blue-100 rounded-full ${isSidebarCollapsed ? 'w-5 h-5' : 'px-2 py-0.5'}`}>
              {tools.filter(t => (!t.is_optional || t.is_downloaded) && t.category !== 'Other').length}
            </span>
          </div>
          
          {tools.filter(t => (!t.is_optional || t.is_downloaded) && t.category !== 'Other').map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              title={t.name}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition relative group ${
                activeTab === t.id
                  ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                  : 'text-gray-700 hover:bg-gray-100'
              } ${isSidebarCollapsed ? 'justify-center' : 'justify-between'}`}
            >
              <div className="flex items-center gap-3 truncate">
                <span className="flex-shrink-0 text-gray-500 group-hover:text-current">{getToolIcon(t)}</span>
                {!isSidebarCollapsed && <span className="truncate text-left" title={t.name}>{t.name}</span>}
              </div>
              {!isSidebarCollapsed && (
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${t.status === 'running' ? 'bg-success-500' : 'bg-gray-300'}`}></span>
              )}
              {isSidebarCollapsed && t.status === 'running' && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-success-500 shadow-sm border border-white"></span>
              )}
            </button>
          ))}

          {/* Collapsible "Other" Section */}
          {tools.filter(t => (!t.is_optional || t.is_downloaded) && t.category === 'Other').length > 0 && (
            <div className="mt-4">
              <button
                onClick={() => {
                  if (isSidebarCollapsed) setIsSidebarCollapsed(false);
                  setIsOtherOpen(!isOtherOpen || isSidebarCollapsed);
                }}
                title="Other Tools"
                className={`w-full flex items-center px-2 py-1.5 text-[11px] font-bold text-gray-400 uppercase tracking-wider hover:bg-gray-100 rounded transition cursor-pointer ${isSidebarCollapsed ? 'justify-center' : 'justify-between'}`}
              >
                {!isSidebarCollapsed && <span>Other Tools</span>}
                <svg className={`w-3.5 h-3.5 transition-transform flex-shrink-0 ${isOtherOpen && !isSidebarCollapsed ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {isSidebarCollapsed ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" /> : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />}
                </svg>
              </button>
              
              {isOtherOpen && !isSidebarCollapsed && (
                <div className="mt-1 space-y-1 pl-2 border-l-2 border-gray-100 ml-3">
                  {tools.filter(t => (!t.is_optional || t.is_downloaded) && t.category === 'Other').map(t => (
                    <button
                      key={t.id}
                      onClick={() => setActiveTab(t.id)}
                      title={t.name}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition ${
                        activeTab === t.id
                          ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="flex-shrink-0 w-4 h-4 text-gray-500">{getToolIcon(t)}</span>
                        <span className="truncate text-xs" title={t.name}>{t.name}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className={`text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 mt-6 px-2 flex ${isSidebarCollapsed ? 'justify-center' : ''}`}>
            {!isSidebarCollapsed && <span>Additional Tools</span>}
          </div>
          <button
            onClick={() => setActiveTab('catalogue')}
            title="Search Tool Catalogue"
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'catalogue'
                ? 'bg-blue-50 text-blue-700 font-semibold shadow-2xs'
                : 'text-gray-700 hover:bg-gray-100'
            } ${isSidebarCollapsed ? 'justify-center' : ''}`}
          >
            <Icons.Store className="w-5 h-5 flex-shrink-0" />
            {!isSidebarCollapsed && <span>Search Tool Catalogue</span>}
          </button>

          <div className="mt-8 pt-4 border-t border-gray-100">
            <div className={`text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 px-2 flex ${isSidebarCollapsed ? 'justify-center' : ''}`}>
              {!isSidebarCollapsed && <span>Settings</span>}
            </div>
            <button
              onClick={() => setActiveTab('global-config')}
              title="Shared Controller Settings"
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'global-config'
                  ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                  : 'text-gray-700 hover:bg-gray-100'
              } ${isSidebarCollapsed ? 'justify-center' : ''}`}
            >
              <Icons.Settings className="w-5 h-5 flex-shrink-0" />
              {!isSidebarCollapsed && <span className="truncate">Shared Controller Settings</span>}
            </button>
          </div>
        </nav>
      </aside>

      {/* --- Main Content Canvas --- */}
      <main className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${isSidebarCollapsed ? "ml-[80px]" : "ml-[280px]"}`}>
        {/* Header */}
        <header className="sticky top-0 z-20 h-[72px] bg-white border-b border-gray-200 px-8 flex items-center justify-between shadow-theme-xs">
          <div>
                        <h2 className="text-xl font-bold text-gray-900 capitalize">
              {activeTab === 'overview' && 'Proof of Concept Evaluations'}
              {activeTab === 'global-config' && 'Shared Netris Controller Settings'}
              {activeTab === 'tool-configs' && 'Interactive Tool Configuration Files'}
              {activeTab === 'logs' && 'Live Process & Container Logs'}
              {activeTab !== 'overview' && activeTab !== 'global-config' && activeTab !== 'tool-configs' && activeTab !== 'logs' && tools.find(t=>t.id===activeTab)?.name}
            </h2>
          </div>

          {(activeTab === 'global-config' || activeTab === 'overview') && (
          <div className="flex items-center gap-3">
            {/* Quick Scenario Buttons */}
            <button
              onClick={() => handleRunScenario('start_ai_fabric')}
              className="bg-white text-gray-700 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 px-3.5 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2 shadow-theme-xs"
              title="Launch Slurm Sim and Prometheus/Grafana Stack"
            >
              <Icons.Play />
              <span>Start All AI Fabric</span>
            </button>

            <button
              onClick={() => handleRunScenario('stop_all')}
              className="bg-white text-error-600 ring-1 ring-inset ring-red-200 hover:bg-error-50 px-3.5 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2 shadow-theme-xs cursor-pointer"
              title="Stop all active demo containers and background scripts"
            >
              <Icons.Stop />
              <span>Stop All</span>
            </button>

            {/* Prometheus Telemetry Recording Button in Header */}
            <button
              onClick={() => setRecordingModalOpen(true)}
              className={`ring-1 ring-inset px-3.5 py-2 rounded-lg text-sm font-semibold transition inline-flex items-center gap-2 shadow-theme-xs cursor-pointer ${
                recordingState?.is_recording
                  ? 'bg-red-50 ring-red-400 text-red-700 animate-pulse'
                  : 'bg-white text-gray-700 ring-gray-300 hover:bg-red-50 hover:text-red-700 hover:ring-red-300'
              }`}
              title="Record live Netris telemetry for Prometheus offline looping"
            >
              <span className={`w-2.5 h-2.5 rounded-full ${recordingState?.is_recording ? 'bg-red-600 animate-ping' : 'bg-red-500'}`}></span>
              <span>{recordingState?.is_recording ? `Recording Live (${Math.round(recordingState?.elapsed_seconds || 0)}s)` : 'Record Telemetry'}</span>
            </button>

            {/* Refresh Button */}
            <button
              onClick={loadTools}
              className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-100 transition shadow-theme-xs cursor-pointer"
              title="Refresh status"
            >
              <Icons.Refresh />
            </button>
          </div>
          )}
        </header>

        {/* Global Live Recording Alert Banner */}
        {recordingState?.is_recording && (
          <div className="bg-red-600 text-white px-8 py-2.5 flex items-center justify-between text-sm shadow-md">
            <div className="flex items-center gap-3">
              <span className="w-2.5 h-2.5 rounded-full bg-white animate-ping"></span>
              <span className="font-bold tracking-wide uppercase text-xs">Live Telemetry Recording in Progress:</span>
              <span className="font-mono text-xs font-semibold">{Math.round(recordingState.elapsed_seconds)}s / {recordingState.duration}s ({recordingState.progress_pct}%)</span>
              <span className="text-red-100 text-xs">· {recordingState.frames_captured} frames captured</span>
            </div>
            <button
              onClick={() => setRecordingModalOpen(true)}
              className="bg-white text-red-700 hover:bg-red-50 px-3 py-1 rounded text-xs font-bold transition shadow-sm cursor-pointer"
            >
              View Progress / Stop Recording
            </button>
          </div>
        )}

        {/* Content Area */}
        <div className="p-8 max-w-[1400px] w-full mx-auto space-y-6">
          {/* ========================================================================= */}
          {/* TAB 1: OVERVIEW / DASHBOARD                                               */}
          {/* ========================================================================= */}
          {activeTab !== 'overview' && activeTab !== 'global-config' && activeTab !== 'tool-configs' && activeTab !== 'logs' && activeTab !== 'catalogue' && (
            <ToolDetailView 
              tool={tools.find(t => t.id === activeTab)}
              onStart={handleStart}
              onStop={handleStop}
              onRestart={handleRestart}
              fetchLogs={fetchLogs}
              configCatalog={configCatalog}
              fetchConfigFile={fetchConfigFile}
              saveConfigFile={saveConfigFile}
              openTerminal={t => setTerminalModalTool(t)}
              actionLoading={actionLoading}
              openSessionModal={openSessionModal}
              handleUpdateTool={async (id) => {
                setActionLoading(prev => ({ ...prev, [id]: true }));
                try {
                  const res = await fetch(`/api/tools/${id}/update`, { method: 'POST' });
                  const data = await res.json();
                  if (!res.ok) throw new Error(data.detail || data.message || "Update failed");
                  notify(data.message || "Tool updated successfully!");
                } catch (e) {
                  notify("Update failed: " + e.message, 'error');
                } finally {
                  setActionLoading(prev => ({ ...prev, [id]: false }));
                }
              }}
            />
          )}
          {activeTab === 'overview' && (
            <div className="max-w-5xl mx-auto w-full px-8 py-8 animate-in fade-in duration-300">
              {/* Intro Section */}
              <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-theme-sm text-center mb-8">
                <h2 className="text-3xl font-bold text-gray-900 mb-4">Welcome to Proof of Concept Evaluations</h2>
                <p className="text-gray-600 max-w-2xl mx-auto mb-6">
                  This hub provides centralized management and health monitoring for all Proof of Concept tools and integrations. 
                  Launch, configure, and monitor evaluations tailored for AI Fabric and cloud networking seamlessly.
                </p>
                <div className="flex justify-center gap-4">
                  <span className="inline-flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full text-sm font-medium text-gray-700 shadow-2xs">
                    <span className="w-2.5 h-2.5 rounded-full bg-success-500 animate-pulse"></span>
                    {runningCount} Tools Running
                  </span>
                  <span className="inline-flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full text-sm font-medium text-gray-700 shadow-2xs">
                    <span className="w-2.5 h-2.5 rounded-full bg-gray-400"></span>
                    {stoppedCount} Tools Stopped
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-gray-900">Installed Tools</h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {tools.filter(t => (!t.is_optional || t.is_downloaded) && t.category !== 'Other').map(tool => (
                  <div 
                    key={tool.id} 
                    onClick={() => setActiveTab(tool.id)}
                    className="bg-white rounded-xl border border-gray-200 p-5 shadow-theme-xs hover:shadow-theme-md hover:border-coral-200 transition-all cursor-pointer flex flex-col justify-between group"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <div className="w-10 h-10 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center text-gray-500 group-hover:text-coral-600 group-hover:bg-coral-50 transition-colors">
                          {getToolIcon(tool)}
                        </div>
                        <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${tool.status === 'running' ? 'bg-success-100 text-success-700' : 'bg-gray-100 text-gray-600'}`}>
                          {tool.status}
                        </span>
                      </div>
                      <h4 className="text-base font-bold text-gray-900 mb-1 group-hover:text-coral-700 transition-colors">{tool.name}</h4>
                      <p className="text-xs text-gray-500 line-clamp-2">{tool.description}</p>
                    </div>
                    <div className="mt-4 pt-3 border-t border-gray-100 flex items-center text-sm font-medium text-coral-600 group-hover:text-coral-700">
                      Open Tool
                      <svg className="w-4 h-4 ml-1 transform group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'catalogue' && (
            <div className="max-w-6xl mx-auto w-full px-8 py-8 animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Search Tool Catalogue</h2>
                  <p className="text-sm text-gray-500 mt-1">Browse and install additional Proof of Concept evaluations from the marketplace.</p>
                </div>
                <div className="relative max-w-sm w-full">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                  </div>
                  <input
                    type="text"
                    placeholder="Search catalogue..."
                    value={catalogueSearchQuery}
                    onChange={(e) => setCatalogueSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition shadow-2xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {tools
                  .filter(t => t.is_optional && !t.is_downloaded)
                  .filter(t => t.name.toLowerCase().includes(catalogueSearchQuery.toLowerCase()) || t.description.toLowerCase().includes(catalogueSearchQuery.toLowerCase()))
                  .map(tool => (
                  <div key={tool.id} className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col shadow-theme-xs">
                    <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center mb-4">
                      {getToolIcon(tool)}
                    </div>
                    <h4 className="text-base font-bold text-gray-900 mb-2">{tool.name}</h4>
                    <p className="text-xs text-gray-500 flex-1 mb-4">{tool.description}</p>
                    <button
                      onClick={() => setActiveTab(tool.id)}
                      className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition"
                    >
                      View Details & Install
                    </button>
                  </div>
                ))}
                {tools.filter(t => t.is_optional && !t.is_downloaded).length === 0 && (
                  <div className="col-span-full py-12 text-center bg-gray-50 rounded-2xl border border-dashed border-gray-300">
                    <Icons.Box className="w-10 h-10 text-gray-400 mx-auto mb-3" />
                    <h3 className="text-gray-900 font-semibold mb-1">All Tools Installed</h3>
                    <p className="text-gray-500 text-sm">There are no more tools available in the catalogue at this time.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'global-config' && (
            <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-theme-xs max-w-3xl">
              <div className="mb-6">
                <h3 className="text-lg font-bold text-gray-900">Shared Netris Controller Configuration</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Centralized settings for your Netris Controller instance. Saving here automatically propagates credentials across NetBox, Prometheus Exporter, and the Slurm Orchestrator.
                </p>
              </div>

              <form onSubmit={handleSaveGlobalConfig} className="space-y-4">
                <div>
                  <label htmlFor="netris_url" className="block text-sm font-medium text-gray-700 mb-1">
                    Netris Controller URL
                  </label>
                  <input
                    type="text"
                    value={globalConfig.netris_url}
                    onChange={(e) => setGlobalConfig({ ...globalConfig, netris_url: e.target.value })}
                    id="netris_url" name="netris_url" className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm font-mono"
                    placeholder="https://adam-ctl.netris.io"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="netris_username" className="block text-sm font-medium text-gray-700 mb-1">
                      Netris Admin Username
                    </label>
                    <input
                      type="text"
                      value={globalConfig.netris_username}
                      onChange={(e) => setGlobalConfig({ ...globalConfig, netris_username: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm"
                      id="netris_username" name="netris_username" placeholder="netris"
                      required
                    />
                  </div>

                  <div>
                    <label htmlFor="netris_password" className="block text-sm font-medium text-gray-700 mb-1">
                      Netris Admin Password
                    </label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        id="netris_password" name="netris_password" autoComplete="current-password"
                        value={globalConfig.netris_password}
                        onChange={(e) => setGlobalConfig({ ...globalConfig, netris_password: e.target.value })}
                        className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm pr-16 font-mono"
                        placeholder="••••••••••••"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2 top-2.5 text-xs text-gray-500 hover:text-gray-800 px-2 py-0.5 rounded font-medium"
                      >
                        {showPassword ? 'Hide' : 'Show'}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Default Tenant Name
                    </label>
                    <input
                      type="text"
                      value={globalConfig.default_tenant}
                      onChange={(e) => setGlobalConfig({ ...globalConfig, default_tenant: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm"
                      placeholder="Demo"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Default Site Name
                    </label>
                    <input
                      type="text"
                      value={globalConfig.default_site}
                      onChange={(e) => setGlobalConfig({ ...globalConfig, default_site: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm"
                      placeholder="SantaClara"
                    />
                  </div>
                </div>

                <div className="pt-2">
                  <label className="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={globalConfig.netris_verify_ssl}
                      onChange={(e) => setGlobalConfig({ ...globalConfig, netris_verify_ssl: e.target.checked })}
                      className="rounded border-gray-300 text-coral-600 focus:ring-coral-500 h-4 w-4"
                    />
                    <span>Verify SSL Certificates (Disable for self-signed lab certificates)</span>
                  </label>
                </div>

                {/* Target Destination File List */}
                <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 text-xs text-gray-600 space-y-1.5 mt-4">
                  <span className="font-bold text-gray-800 block mb-1">Auto-Propagation Targets on Disk:</span>
                  <div>&bull; <code className="font-mono text-gray-800">netris-prometheus-exporter/netris.var</code> and <code className="font-mono text-gray-800">.env</code></div>
                  <div>&bull; <code className="font-mono text-gray-800">netbox-netris/.env</code></div>
                  <div>&bull; <code className="font-mono text-gray-800">provider-portal/.env</code></div>
                  <div>&bull; <code className="font-mono text-gray-800">netris-slurm-cluster-sim/.env</code></div>
                </div>

                {/* Action Submit */}
                <div className="pt-4 flex items-center justify-end gap-3">
                  <button 
                    type="button"
                    onClick={async () => {
                      try {
                        const res = await fetch('/api/system/update', { method: 'POST' });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.detail || data.message || "Update failed");
                        alert(data.message || "Portal updated successfully! You may need to restart the backend.");
                      } catch (e) {
                        alert("Update failed: " + e.message);
                      }
                    }} 
                    className="px-4 py-2.5 bg-gray-100 text-gray-700 border border-gray-300 rounded-lg text-sm font-semibold hover:bg-gray-200 shadow-theme-xs flex items-center gap-2"
                  >
                    <Icons.RefreshCw className="w-4 h-4" />
                    Update Demo Portal
                  </button>
                  <button
                    type="submit"
                    disabled={configSaving}
                    className="bg-coral-600 hover:bg-coral-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold shadow-theme-xs transition"
                  >
                    {configSaving ? 'Propagating to Tools...' : 'Save & Sync Everywhere'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 3: MULTI-FILE TOOL CONFIGURATIONS                                     */}
          {/* ========================================================================= */}
          {activeTab === 'tool-configs' && (
            <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-theme-xs max-w-5xl space-y-6">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Interactive Tool Configuration Editor</h3>
                <p className="text-sm text-gray-500 mt-0.5">
                  Select any demo application below, inspect its individual environment & mapping files, edit them via the text box, and save changes directly to disk.
                </p>
              </div>

              {/* Tool Selector Tabs */}
              <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 pb-3">
                {configCatalog.map((item) => {
                  const isSelected = item.tool_id === selectedToolConfigId;
                  return (
                    <button
                      key={item.tool_id}
                      onClick={() => {
                        setSelectedToolConfigId(item.tool_id);
                        if (item.files.length > 0) {
                          setSelectedFileId(item.files[0].id);
                        }
                      }}
                      className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 ${
                        isSelected
                          ? 'bg-coral-600 text-white shadow-2xs'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      <span>{item.tool_name}</span>
                      <span
                        className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                          isSelected ? 'bg-coral-700 text-white' : 'bg-white text-gray-600'
                        }`}
                      >
                        {item.files.length}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Sub-Tabs for Files in Active Tool */}
              {activeToolCatalogEntry && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3 bg-gray-50 p-3 rounded-xl border border-gray-200">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-gray-500 uppercase">Config Files:</span>
                      <div className="flex flex-wrap items-center gap-1.5">
                        {activeToolCatalogEntry.files.map((file) => {
                          const isFileActive = file.id === selectedFileId;
                          return (
                            <button
                              key={file.id}
                              onClick={() => setSelectedFileId(file.id)}
                              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition ${
                                isFileActive
                                  ? 'bg-white text-coral-700 border border-coral-300 shadow-2xs font-bold'
                                  : 'bg-gray-200/70 text-gray-700 hover:bg-white'
                              }`}
                            >
                              {file.name}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Metadata Badges */}
                    {currentFileMeta && (
                      <div className="flex items-center gap-2 text-xs font-mono">
                        <span className="bg-gray-200/80 text-gray-700 px-2 py-0.5 rounded text-[11px]">
                          {currentFileMeta.path}
                        </span>
                        <span className="bg-coral-50 text-coral-700 border border-coral-200 px-2 py-0.5 rounded uppercase font-bold text-[10px]">
                          {currentFileMeta.format}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* File Description if available */}
                  {currentFileMeta && currentFileMeta.name && (
                    <p className="text-xs text-gray-500 px-1 italic">
                      {activeToolCatalogEntry.files.find((f) => f.id === selectedFileId)?.description}
                    </p>
                  )}

                  {/* Code Editor Box */}
                  <div className="relative rounded-xl overflow-hidden border border-gray-800 shadow-theme-md">
                    {toolConfigLoading ? (
                      <div className="h-[480px] bg-gray-950 flex items-center justify-center text-gray-400 font-mono text-sm">
                        Loading configuration from disk...
                      </div>
                    ) : (
                      <div className="h-[480px] bg-gray-950 overflow-auto border border-gray-800">
                        <ConfigFormEditor 
                          content={toolConfigContent} 
                          format={activeToolCatalogEntry?.files?.find(f => f.id === selectedFileId)?.format || 'shell'} 
                          onChange={(val) => {
                            setToolConfigContent(val);
                            setFileDirty(true);
                          }} 
                        />
                      </div>
                    )}
                  </div>

                  {/* Bottom Action Footer */}
                  <div className="flex items-center justify-between pt-2">
                    <div className="flex items-center gap-2 text-xs">
                      {fileDirty ? (
                        <span className="inline-flex items-center gap-1.5 text-warning-600 bg-warning-50 border border-amber-200 px-2.5 py-1 rounded-md font-medium">
                          ● Unsaved modifications in editor
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-gray-400">
                          <Icons.Check className="w-3.5 h-3.5 text-emerald-500" />
                          Synchronized with file on disk
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => loadFileContent(selectedToolConfigId, selectedFileId)}
                        disabled={toolConfigLoading || fileSaving}
                        className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 text-xs font-semibold shadow-2xs transition"
                      >
                        Discard & Reload
                      </button>

                      <button
                        onClick={handleSaveFileContent}
                        disabled={toolConfigLoading || fileSaving}
                        className="bg-coral-600 hover:bg-coral-700 text-white px-6 py-2 rounded-lg text-xs font-semibold shadow-theme-xs transition inline-flex items-center gap-2"
                      >
                        {fileSaving ? 'Writing to Disk...' : 'Save File to Disk'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 4: PROCESS LOGS CONSOLE                                               */}
          {/* ========================================================================= */}
          {activeTab === 'logs' && (
            <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-theme-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                <div className="flex items-center gap-3">
                  <h3 className="text-base font-bold text-gray-900">Process Console Output</h3>
                  <select
                    value={selectedToolLogs || ''}
                    onChange={(e) => openLogs(e.target.value)}
                    className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium bg-white focus:outline-none"
                  >
                    {tools.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-3 text-xs">
                  <label className="inline-flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoRefreshLogs}
                      onChange={(e) => setAutoRefreshLogs(e.target.checked)}
                      className="rounded border-gray-300 text-coral-600 focus:ring-coral-500 h-3.5 w-3.5"
                    />
                    <span>Auto-refresh (2s)</span>
                  </label>

                  <button
                    onClick={() => setLogContent([])}
                    className="px-2.5 py-1 rounded border border-gray-200 text-gray-600 hover:bg-gray-50"
                  >
                    Clear View
                  </button>
                </div>
              </div>

              {/* Terminal Screen */}
              <div className="bg-gray-950 text-emerald-400 p-5 rounded-xl font-mono text-xs overflow-auto max-h-[600px] min-h-[400px] border border-gray-900 shadow-inner">
                {logContent.length === 0 ? (
                  <div className="text-gray-600 italic">No output logged yet for this tool. Click Start to begin execution.</div>
                ) : (
                  logContent.map((line, idx) => (
                    <div key={idx} className="whitespace-pre-wrap leading-relaxed">
                      {line}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* ========================================================================= */}
      {/* MODAL 1: SESSION CONFIGURATION LAUNCHER                                    */}
      {/* ========================================================================= */}
      {sessionModalTool && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-theme-xl max-w-xl w-full flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50/50">
              <div>
                <h4 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  <Icons.Sliders className="w-4 h-4 text-coral-600" />
                  {sessionModalTool.session_options?.title || 'Session Configuration'}
                </h4>
                <p className="text-xs text-gray-500 mt-0.5">{sessionModalTool.name}</p>
              </div>

              <button
                onClick={() => setSessionModalTool(null)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            {/* Modal Form */}
            <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
              <p className="text-xs text-gray-600 leading-relaxed">
                {sessionModalTool.session_options?.description}
              </p>

              <div className="space-y-4 pt-2">
                {sessionModalTool.session_options?.fields.map((field) => {
                  const val = sessionParams[field.id] !== undefined ? sessionParams[field.id] : field.default;

                  if (field.type === 'select') {
                    return (
                      <div key={field.id}>
                        <label className="block text-xs font-bold text-gray-800 mb-1.5">
                          {field.label}
                        </label>
                        <select
                          value={val}
                          onChange={(e) => setSessionParams({ ...sessionParams, [field.id]: e.target.value })}
                          className="w-full px-3 py-2 rounded-lg border border-gray-300 text-xs font-medium bg-white focus:outline-none focus:ring-2 focus:ring-coral-500"
                        >
                          {field.options.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                        {field.help && <p className="text-[11px] text-gray-400 mt-1">{field.help}</p>}
                      </div>
                    );
                  }

                  if (field.type === 'number') {
                    return (
                      <div key={field.id}>
                        <label className="block text-xs font-bold text-gray-800 mb-1.5">
                          {field.label}
                        </label>
                        <input
                          type="number"
                          value={val}
                          min={field.min}
                          max={field.max}
                          onChange={(e) => setSessionParams({ ...sessionParams, [field.id]: parseInt(e.target.value, 10) || 0 })}
                          className="w-full px-3 py-2 rounded-lg border border-gray-300 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-coral-500 font-mono"
                        />
                        {field.help && <p className="text-[11px] text-gray-400 mt-1">{field.help}</p>}
                      </div>
                    );
                  }

                  if (field.type === 'boolean') {
                    return (
                      <div key={field.id} className="pt-1">
                        <label className="inline-flex items-center gap-2 text-xs font-medium text-gray-700 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={Boolean(val)}
                            onChange={(e) => setSessionParams({ ...sessionParams, [field.id]: e.target.checked })}
                            className="rounded border-gray-300 text-coral-600 focus:ring-coral-500 h-4 w-4"
                          />
                          <span>{field.label}</span>
                        </label>
                        {field.help && <p className="text-[11px] text-gray-400 ml-6 mt-0.5">{field.help}</p>}
                      </div>
                    );
                  }

                  if (field.type === 'text') {
                    return (
                      <div key={field.id}>
                        <label className="block text-xs font-bold text-gray-800 mb-1.5">
                          {field.label}
                        </label>
                        <input
                          type="text"
                          value={val}
                          onChange={(e) => setSessionParams({ ...sessionParams, [field.id]: e.target.value })}
                          className="w-full px-3 py-2 rounded-lg border border-gray-300 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-coral-500 font-mono"
                        />
                        {field.help && <p className="text-[11px] text-gray-400 mt-1">{field.help}</p>}
                      </div>
                    );
                  }

                  return null;
                })}
              </div>

              {/* Real-time Launch Summary Box */}
              <div className="bg-gray-900 text-gray-300 p-3 rounded-xl text-xs font-mono space-y-1 mt-4 border border-gray-800">
                <div className="text-gray-500 text-[10px] uppercase font-bold tracking-wider">Generated Execution Command:</div>
                <div className="text-emerald-400 break-all">
                  {sessionModalTool.id === 'netris-prometheus-exporter' && (
                    `./start.sh --${sessionParams.mode || 'sim'} ${sessionParams.do_backfill === false ? '--no-backfill' : `--backfill ${sessionParams.backfill_minutes || 90}`}`
                  )}
                  {sessionModalTool.id === 'netris-slurm-cluster-sim' && (
                    `python3 run_simulation.py ${sessionParams.mode === 'sim' || !sessionParams.mode ? '--sim-mode' : ''} --port ${sessionParams.port || 8088} ${sessionParams.speedup && sessionParams.speedup !== '1' ? `--speedup ${sessionParams.speedup}` : ''}`
                  )}
                  {sessionModalTool.id === 'gpu-ai-fabric-traffic-sim' && (
                    `docker compose up -d (Pattern: ${sessionParams.pattern || 'ring-allreduce'}, Duration: ${sessionParams.duration || 5}s ${sessionParams.max_bandwidth ? `@ ${sessionParams.max_bandwidth}` : ''})`
                  )}
                  {sessionModalTool.id === 'netris-controller-gpu-traffic-sim' && (
                    `./deploy.sh --pattern ${sessionParams.pattern || 'ring-allreduce'} --duration ${sessionParams.duration || 5} ${sessionParams.max_bandwidth ? `--max-bandwidth ${sessionParams.max_bandwidth}` : ''} ${sessionParams.continuous ? '--continuous' : ''}`
                  )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-end gap-3">
              <button
                onClick={() => setSessionModalTool(null)}
                className="px-4 py-2 rounded-lg border border-gray-300 bg-white text-xs font-semibold hover:bg-gray-50 text-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={handleLaunchWithSession}
                className="px-5 py-2 rounded-lg bg-coral-600 hover:bg-coral-700 text-white text-xs font-semibold shadow-theme-xs transition inline-flex items-center gap-1.5"
              >
                <Icons.Play />
                <span>Launch Session</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: LIVE PROCESS LOGS INSPECTOR                                      */}
      {/* ========================================================================= */}
      {selectedToolLogs && activeTab !== 'logs' && activeTab !== 'catalogue' && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-theme-lg max-w-4xl w-full flex flex-col max-h-[85vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h4 className="text-base font-bold text-gray-900">
                  Logs: {tools.find((t) => t.id === selectedToolLogs)?.name || selectedToolLogs}
                </h4>
                <p className="text-xs text-gray-400">Live stdout / stderr ring buffer</p>
              </div>

              <div className="flex items-center gap-3">
                <label className="text-xs inline-flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoRefreshLogs}
                    onChange={(e) => setAutoRefreshLogs(e.target.checked)}
                    className="rounded text-coral-600"
                  />
                  <span>Auto-refresh</span>
                </label>
                <button
                  onClick={() => setSelectedToolLogs(null)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 text-lg font-bold"
                >
                  &times;
                </button>
              </div>
            </div>

            <div className="p-6 bg-gray-950 text-emerald-400 font-mono text-xs overflow-auto flex-1">
              {logContent.length === 0 ? (
                <div className="text-gray-600 italic">No logs recorded yet.</div>
              ) : (
                logContent.map((l, i) => (
                  <div key={i} className="whitespace-pre-wrap leading-relaxed">{l}</div>
                ))
              )}
            </div>

            <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 flex justify-end">
              <button
                onClick={() => setSelectedToolLogs(null)}
                className="px-4 py-2 rounded-lg border border-gray-300 bg-white text-xs font-semibold hover:bg-gray-50 text-gray-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      {/* ========================================================================= */}
      {/* MODAL 3: INTERACTIVE IN-BROWSER TERMINAL (xterm.js)                       */}
      {/* ========================================================================= */}
      {terminalModalTool && (
        <InteractiveTerminalModal
          tool={terminalModalTool}
          onClose={() => setTerminalModalTool(null)}
          notify={notify}
        />
      )}

      {/* ========================================================================= */}
      {/* MODAL 4: PROMETHEUS TELEMETRY STREAM RECORDING                            */}
      {/* ========================================================================= */}
      <TelemetryRecordingModal
        isOpen={recordingModalOpen}
        onClose={() => setRecordingModalOpen(false)}
        notify={notify}
        recordingState={recordingState}
        setRecordingState={setRecordingState}
      />

      {/* ========================================================================= */}
      {/* MODAL 5: NEW CATEGORY MODAL                                               */}
      {/* ========================================================================= */}
      {newCategoryModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-gray-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-coral-50 flex items-center justify-center text-coral-600">
                  <Icons.Folder className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 text-base">Add New Category</h3>
                  <p className="text-xs text-gray-500">Create a new section to organize your demo tools</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setNewCategoryModalOpen(false);
                  setNewCategoryName('');
                }}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateCategory} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                  Category Name
                </label>
                <input
                  type="text"
                  autoFocus
                  required
                  placeholder="e.g. Storage Fabrics, AI Orchestration, Observability"
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-300 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-coral-500/20 focus:border-coral-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setNewCategoryModalOpen(false);
                    setNewCategoryName('');
                  }}
                  className="px-4 py-2 rounded-xl border border-gray-300 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newCategoryName.trim()}
                  className="px-4 py-2 rounded-xl bg-coral-600 hover:bg-coral-700 disabled:opacity-50 text-white text-xs font-semibold shadow-theme-xs cursor-pointer"
                >
                  Create Category
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 6: MOVE TOOL TO CATEGORY MODAL                                      */}
      {/* ========================================================================= */}
      {moveCategoryModalTool && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-gray-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-coral-50 flex items-center justify-center text-coral-600">
                  <Icons.Folder className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 text-base">Move Tool</h3>
                  <p className="text-xs text-gray-500">Choose a category section for <span className="font-semibold text-gray-800">{moveCategoryModalTool.name}</span></p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setMoveCategoryModalTool(null)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <div className="p-6 space-y-3">
              <div className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
                Select Destination Section:
              </div>

              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {sortedCategories.map((cat) => {
                  const currentCatId = (layout.tool_placements || {})[moveCategoryModalTool.id]?.category_id;
                  const isCurrent = currentCatId === cat.id;

                  return (
                    <button
                      key={cat.id}
                      type="button"
                      disabled={isCurrent}
                      onClick={() => handleMoveToolCategory(moveCategoryModalTool.id, cat.id)}
                      className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border text-sm text-left transition cursor-pointer ${
                        isCurrent
                          ? 'bg-coral-50 border-coral-200 text-coral-800 font-semibold cursor-default'
                          : 'bg-white border-gray-200 text-gray-800 hover:bg-gray-50 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Icons.Folder className={`w-4 h-4 ${isCurrent ? 'text-coral-600' : 'text-gray-400'}`} />
                        <span>{cat.name}</span>
                      </div>
                      {isCurrent ? (
                        <span className="text-[11px] bg-coral-100 text-coral-700 px-2 py-0.5 rounded-full font-semibold">Current</span>
                      ) : (
                        <span className="text-xs text-gray-400 font-medium">Move here &rarr;</span>
                      )}
                    </button>
                  );
                })}
              </div>

              <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => {
                    const tool = moveCategoryModalTool;
                    setMoveCategoryModalTool(null);
                    setNewCategoryName('');
                    setNewCategoryModalOpen(true);
                  }}
                  className="text-xs text-coral-600 hover:text-coral-700 font-semibold flex items-center gap-1 cursor-pointer"
                >
                  <Icons.Plus className="w-3.5 h-3.5" />
                  <span>Create new category</span>
                </button>

                <button
                  type="button"
                  onClick={() => setMoveCategoryModalTool(null)}
                  className="px-4 py-2 rounded-xl border border-gray-300 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-50 cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Render React App
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
