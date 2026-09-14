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

// --- Icons Component Helpers ---
const Icons = {
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

// --- App Root Component ---
function App() {
  const [activeTab, setActiveTab] = useState('overview'); // overview, global-config, tool-configs, logs
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
      <aside className="w-[280px] bg-white border-r border-gray-200 fixed top-0 bottom-0 left-0 flex flex-col z-30 shadow-theme-xs">
        {/* Brand / Header */}
        <div className="h-[72px] px-6 border-b border-gray-200 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-coral-50 flex items-center justify-center border border-coral-200 shadow-2xs">
            <div className="w-4 h-4 rounded-full bg-coral-500"></div>
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-900 tracking-tight">Demo Command Center</h1>
            <p className="text-xs text-gray-400">Netris & AI Fabric Hub</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-4 space-y-1.5 flex-1">
          <button
            onClick={() => setActiveTab('overview')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'overview'
                ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <Icons.Dashboard />
            <span>Dashboard Hub</span>
          </button>

          <button
            onClick={() => setActiveTab('global-config')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'global-config'
                ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <Icons.Settings />
            <span>Shared Controller Settings</span>
          </button>

          <button
            onClick={() => setActiveTab('tool-configs')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'tool-configs'
                ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <Icons.ToolConfig />
            <div className="flex items-center justify-between flex-1">
              <span>Config Files Editor</span>
              <span className="text-[10px] bg-gray-200 text-gray-700 px-1.5 py-0.5 rounded font-mono">
                {configCatalog.reduce((acc, curr) => acc + curr.files.length, 0)} files
              </span>
            </div>
          </button>

          <button
            onClick={() => {
              setActiveTab('logs');
              if (!selectedToolLogs && tools.length > 0) {
                openLogs(tools[0].id);
              }
            }}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === 'logs'
                ? 'bg-coral-50 text-coral-700 font-semibold shadow-2xs'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            <Icons.Terminal />
            <span>Process Logs Console</span>
          </button>
        </nav>

        {/* Footer Info */}
        <div className="p-4 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
          <div className="flex justify-between items-center mb-1">
            <span className="font-medium text-gray-700">Port 8800 Active</span>
            <span className="inline-flex items-center gap-1 text-success-600 font-medium">
              <span className="w-2 h-2 rounded-full bg-success-500"></span> Online
            </span>
          </div>
          <p className="text-gray-400">TailAdmin v2 &middot; Netris Architecture</p>
        </div>
      </aside>

      {/* --- Main Content Canvas --- */}
      <main className="ml-[280px] flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="sticky top-0 z-20 h-[72px] bg-white border-b border-gray-200 px-8 flex items-center justify-between shadow-theme-xs">
          <div>
            <h2 className="text-xl font-bold text-gray-900 capitalize">
              {activeTab === 'overview' && 'Demo Control Hub'}
              {activeTab === 'global-config' && 'Shared Netris Controller Settings'}
              {activeTab === 'tool-configs' && 'Interactive Tool Configuration Files'}
              {activeTab === 'logs' && 'Live Process & Container Logs'}
            </h2>
          </div>

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
              className="bg-white text-error-600 ring-1 ring-inset ring-red-200 hover:bg-error-50 px-3.5 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2 shadow-theme-xs"
              title="Stop all active demo containers and background scripts"
            >
              <Icons.Stop />
              <span>Stop All</span>
            </button>

            {/* Refresh Button */}
            <button
              onClick={loadTools}
              className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-100 transition shadow-theme-xs"
              title="Refresh status"
            >
              <Icons.Refresh />
            </button>
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8 max-w-[1400px] w-full mx-auto space-y-6">
          {/* ========================================================================= */}
          {/* TAB 1: OVERVIEW / DASHBOARD                                               */}
          {/* ========================================================================= */}
          {activeTab === 'overview' && (
            <>
              {/* KPI Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-theme-xs">
                  <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Total Demo Tools</span>
                  <div className="text-2xl font-bold text-gray-900 mt-1">{tools.length}</div>
                  <span className="text-xs text-gray-500 mt-1 block">Full stack across AI cloud</span>
                </div>

                <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-theme-xs">
                  <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Running Now</span>
                  <div className="text-2xl font-bold text-success-600 mt-1 flex items-center gap-2">
                    {runningCount}
                    {runningCount > 0 && <span className="w-2.5 h-2.5 rounded-full bg-success-500 animate-ping"></span>}
                  </div>
                  <span className="text-xs text-gray-500 mt-1 block">Ready for customer demos</span>
                </div>

                <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-theme-xs">
                  <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Stopped Tools</span>
                  <div className="text-2xl font-bold text-gray-600 mt-1">{stoppedCount}</div>
                  <span className="text-xs text-gray-500 mt-1 block">Standby / inactive</span>
                </div>

                <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-theme-xs">
                  <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Target Controller</span>
                  <div className="text-sm font-semibold text-gray-900 mt-1 truncate" title={globalConfig.netris_url}>
                    {globalConfig.netris_url || 'Not configured'}
                  </div>
                  <span className="text-xs text-emerald-600 mt-1 block font-medium">Shared credentials synced</span>
                </div>
              </div>

              {/* Tools Grid */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-gray-900">Registered Demo Applications & Control Planes</h3>
                  <span className="text-xs text-gray-500">Live heartbeats update every 3s</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                  {tools.map((tool) => {
                    const isRunning = tool.is_running;
                    const isBusy = actionLoading[tool.id];
                    const hasSessionOptions = Boolean(tool.session_options);
                    const creds = tool.credentials || [];

                    return (
                      <div
                        key={tool.id}
                        className="bg-white rounded-2xl border border-gray-200 p-6 shadow-theme-xs hover:shadow-theme-sm transition flex flex-col justify-between relative"
                      >
                        <div>
                          {/* Top Tag & Status Pill */}
                          <div className="flex items-center justify-between gap-2 mb-3">
                            <span className="text-xs font-medium bg-gray-100 text-gray-700 px-2.5 py-0.5 rounded-full">
                              {tool.category}
                            </span>

                            <div className="flex items-center gap-1.5">
                              {tool.id === 'netris-prometheus-exporter' && recordingState?.is_recording && (
                                <span className="inline-flex items-center gap-1 bg-red-50 text-red-700 border border-red-200 text-[10px] px-2 py-0.5 rounded-full font-bold">
                                  <span className="w-1.5 h-1.5 rounded-full bg-red-600 animate-ping"></span>
                                  REC ({recordingState.frames_captured}f)
                                </span>
                              )}

                              {isRunning ? (
                                <span className="inline-flex items-center gap-1.5 bg-success-50 text-success-600 border border-emerald-200 text-xs px-2.5 py-0.5 rounded-full font-semibold">
                                  <span className="w-1.5 h-1.5 rounded-full bg-success-500 animate-pulse"></span>
                                  RUNNING
                                </span>
                              ) : tool.tool_type === 'interactive' ? (
                                <span className="bg-coral-50 text-coral-700 border border-coral-200 text-xs px-2.5 py-0.5 rounded-full font-semibold">
                                  INTERACTIVE
                                </span>
                              ) : (
                                <span className="bg-gray-100 text-gray-500 text-xs px-2.5 py-0.5 rounded-full font-medium">
                                  STOPPED
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Tool Name & Description */}
                          <h4 className="text-base font-bold text-gray-900">{tool.name}</h4>
                          <p className="text-xs text-gray-500 mt-1.5 leading-relaxed min-h-[38px]">
                            {tool.description}
                          </p>

                          {/* Port / Type Badges */}
                          <div className="flex flex-wrap items-center gap-2 mt-3.5 text-xs font-mono text-gray-600">
                            {tool.port ? (
                              <span className="bg-gray-50 border border-gray-200 px-2 py-1 rounded-md">
                                Port: <strong className="text-gray-900">{tool.port}</strong>
                              </span>
                            ) : (
                              <span className="bg-gray-50 border border-gray-200 px-2 py-1 rounded-md text-gray-400">
                                No HTTP Port
                              </span>
                            )}

                            {tool.uptime && (
                              <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-1 rounded-md font-sans font-medium">
                                Uptime: {tool.uptime}
                              </span>
                            )}
                          </div>

                          {/* --- UI Login Credentials Bar (Directly Above Open App) --- */}
                          {creds.length > 0 && (
                            <div className="mt-4 p-2.5 rounded-xl bg-gray-50 border border-gray-200/80 flex flex-col gap-1.5">
                              <div className="flex items-center justify-between text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                                <span className="flex items-center gap-1">
                                  <Icons.Key className="w-3 h-3 text-coral-600" />
                                  UI Login Credentials
                                </span>
                                {creds.some((c) => c.no_auth) && (
                                  <span className="text-emerald-600 font-medium normal-case">Open Web UI</span>
                                )}
                              </div>

                              <div className="flex flex-wrap items-center gap-2 mt-0.5">
                                {creds.map((cred, cIdx) => {
                                  if (cred.no_auth) {
                                    return (
                                      <span
                                        key={cIdx}
                                        className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded-md text-xs font-medium"
                                      >
                                        🔓 No Login Required
                                      </span>
                                    );
                                  }

                                  const passKey = `${tool.id}-pass-${cIdx}`;
                                  const userKey = `${tool.id}-user-${cIdx}`;

                                  return (
                                    <div
                                      key={cIdx}
                                      className="inline-flex items-center gap-1.5 bg-white border border-gray-200 px-2.5 py-1 rounded-lg shadow-2xs text-xs"
                                    >
                                      <span className="text-gray-400 font-medium text-[11px]">{cred.label}:</span>
                                      
                                      {/* Username with click to copy */}
                                      <button
                                        type="button"
                                        onClick={() => copyToClipboard(cred.username, userKey, setCopiedKey)}
                                        className="font-mono font-bold text-gray-900 hover:text-coral-600 transition inline-flex items-center gap-0.5"
                                        title="Click to copy username"
                                      >
                                        <span>{cred.username}</span>
                                        {copiedKey === userKey ? (
                                          <span className="text-emerald-600 font-bold text-[10px]">✓</span>
                                        ) : null}
                                      </button>

                                      <span className="text-gray-300 font-mono">/</span>

                                      {/* Password with dedicated copy button */}
                                      <span className="font-mono text-gray-700 max-w-[130px] truncate" title={cred.password}>
                                        {cred.password}
                                      </span>

                                      <button
                                        type="button"
                                        onClick={() => copyToClipboard(cred.password, passKey, setCopiedKey)}
                                        className="p-1 text-gray-400 hover:text-coral-600 hover:bg-gray-100 rounded transition"
                                        title="Copy password to clipboard"
                                      >
                                        {copiedKey === passKey ? (
                                          <Icons.Check className="w-3 h-3 text-emerald-600" />
                                        ) : (
                                          <Icons.Copy className="w-3 h-3" />
                                        )}
                                      </button>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Action Buttons Row */}
                        <div className="mt-5 pt-4 border-t border-gray-100 flex flex-wrap items-center justify-between gap-2">
                          {/* Left: Pop-Out, Interactive Terminal, Recording & Quick Config Actions */}
                          <div className="flex flex-wrap items-center gap-2">
                            {tool.id === 'switch-isolation-cli' ? (
                              <div className="flex items-center gap-1.5">
                                <button
                                  onClick={() => setTerminalModalTool(tool)}
                                  className="px-3 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 transition shadow-theme-xs bg-coral-600 hover:bg-coral-700 text-white cursor-pointer"
                                  title="Open interactive CLI session directly in browser"
                                >
                                  <Icons.Terminal />
                                  <span>Launch CLI ↗</span>
                                </button>

                                <button
                                  onClick={() => handleLaunchNative(tool.id)}
                                  className="px-2.5 py-1.5 rounded-lg border border-gray-200 bg-white text-gray-700 hover:bg-gray-100 text-xs font-semibold transition shadow-2xs inline-flex items-center gap-1 cursor-pointer"
                                  title="Open in native iTerm"
                                >
                                  <Icons.Popout />
                                  <span className="text-[11px]">iTerm</span>
                                </button>
                              </div>
                            ) : tool.popout_url ? (
                              <button
                                onClick={() => window.open(tool.popout_url, '_blank')}
                                disabled={!isRunning}
                                className={`px-3 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 transition shadow-theme-xs ${
                                  isRunning
                                    ? 'bg-coral-600 hover:bg-coral-700 text-white cursor-pointer'
                                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                }`}
                                title={isRunning ? `Open ${tool.name} in new browser tab` : 'Start tool first to open app'}
                              >
                                <Icons.Popout />
                                <span>Open App ↗</span>
                              </button>
                            ) : (
                              <span className="text-xs text-gray-400 italic px-1">Backend Daemon</span>
                            )}

                            {/* Telemetry Recording Trigger Button on Prometheus Card */}
                            {tool.id === 'netris-prometheus-exporter' && (
                              <button
                                onClick={() => setRecordingModalOpen(true)}
                                className={`p-1.5 rounded-lg border text-xs font-medium transition shadow-2xs inline-flex items-center gap-1.5 cursor-pointer ${
                                  recordingState?.is_recording
                                    ? 'bg-red-50 border-red-300 text-red-700 animate-pulse'
                                    : 'border-gray-200 text-gray-700 hover:bg-gray-100 hover:text-red-600'
                                }`}
                                title="Record live Netris telemetry for offline simulation looping"
                              >
                                <span className={`w-2 h-2 rounded-full ${recordingState?.is_recording ? 'bg-red-600 animate-ping' : 'bg-red-500'}`}></span>
                                <span className="text-[11px] font-semibold">Record</span>
                              </button>
                            )}

                            {/* Direct Config File Jump */}
                            <button
                              onClick={() => openConfigEditor(tool.id)}
                              className="p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-100 hover:text-coral-700 text-xs font-medium transition shadow-2xs inline-flex items-center gap-1 cursor-pointer"
                              title="Edit configuration files for this tool"
                            >
                              <Icons.FileCode className="w-3.5 h-3.5 text-gray-500" />
                              <span className="text-[11px]">Config</span>
                            </button>
                          </div>

                          {/* Right: Controls (Start, Session Options, Stop, Restart, Logs) */}
                          <div className="flex items-center gap-1.5">
                            {isRunning ? (
                              <>
                                <button
                                  onClick={() => handleStop(tool.id)}
                                  disabled={isBusy}
                                  className="p-2 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 text-xs font-medium transition shadow-2xs"
                                  title="Stop application"
                                >
                                  <Icons.Stop />
                                </button>
                                <button
                                  onClick={() => handleRestart(tool.id)}
                                  disabled={isBusy}
                                  className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-100 text-xs font-medium transition shadow-2xs"
                                  title="Restart application"
                                >
                                  <Icons.Refresh />
                                </button>
                              </>
                            ) : (
                              <>
                                {/* Session Configurator Trigger Button */}
                                {hasSessionOptions && (
                                  <button
                                    onClick={() => openSessionModal(tool)}
                                    disabled={isBusy}
                                    className="p-1.5 rounded-lg border border-coral-200 text-coral-700 bg-coral-50 hover:bg-coral-100 text-xs font-medium transition shadow-2xs inline-flex items-center gap-1"
                                    title="Configure session inputs before starting"
                                  >
                                    <Icons.Sliders className="w-3.5 h-3.5 text-coral-600" />
                                    <span className="text-[11px] font-semibold">Session</span>
                                  </button>
                                )}

                                <button
                                  onClick={() => handleStart(tool.id)}
                                  disabled={isBusy}
                                  className="bg-white text-gray-700 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 px-3 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 transition shadow-theme-xs"
                                  title="Start program with defaults"
                                >
                                  <Icons.Play />
                                  <span>{isBusy ? 'Starting...' : 'Start'}</span>
                                </button>
                              </>
                            )}

                            <button
                              onClick={() => openLogs(tool.id)}
                              className="p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-100 text-xs font-medium transition shadow-2xs"
                              title="Inspect live console logs"
                            >
                              <Icons.Terminal />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          {/* ========================================================================= */}
          {/* TAB 2: GLOBAL CONFIGURATION                                               */}
          {/* ========================================================================= */}
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Netris Controller URL
                  </label>
                  <input
                    type="text"
                    value={globalConfig.netris_url}
                    onChange={(e) => setGlobalConfig({ ...globalConfig, netris_url: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm font-mono"
                    placeholder="https://adam-ctl.netris.io"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Netris Admin Username
                    </label>
                    <input
                      type="text"
                      value={globalConfig.netris_username}
                      onChange={(e) => setGlobalConfig({ ...globalConfig, netris_username: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-coral-500 text-sm"
                      placeholder="netris"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Netris Admin Password
                    </label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
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
                <div className="pt-4 flex items-center justify-end">
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
                      <textarea
                        rows={22}
                        value={toolConfigContent}
                        onChange={(e) => {
                          setToolConfigContent(e.target.value);
                          setFileDirty(true);
                        }}
                        className="w-full font-mono text-xs bg-gray-950 text-emerald-300 p-5 focus:outline-none focus:ring-2 focus:ring-coral-500 leading-relaxed resize-y"
                        spellCheck="false"
                      ></textarea>
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
      {selectedToolLogs && activeTab !== 'logs' && (
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
    </div>
  );
}

// Render React App
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
