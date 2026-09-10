/**
 * app.js - Netris + Slurm GPU AI Fabric Orchestrator Frontend Logic
 * Live state polling, dynamic DOM rendering, and interactive job management.
 */

let state = null;
let pollTimer = null;
let lastRenderedEventsCount = -1;
let lastRenderedEventId = -1;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  fetchState();
  pollTimer = setInterval(fetchState, 1000);
});

async function fetchState() {
  try {
    const res = await fetch('/api/state');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state = data;
    renderUI(data);
  } catch (err) {
    console.error('Failed to fetch state:', err);
  }
}

function renderUI(data) {
  if (!data) return;
  try { renderControllerStatus(data.is_sim_mode); } catch (e) { console.error('Status render error:', e); }
  try { renderSummary(data.summary); } catch (e) { console.error('Summary render error:', e); }
  try { renderTelemetry(data.telemetry); } catch (e) { console.error('Telemetry render error:', e); }
  try { renderNodes(data.nodes); } catch (e) { console.error('Nodes render error:', e); }
  try { renderJobs(data.jobs); } catch (e) { console.error('Jobs render error:', e); }
  try { renderHistory(data.history); } catch (e) { console.error('History render error:', e); }
  try { renderNetrisClusters(data.netris_clusters); } catch (e) { console.error('Clusters render error:', e); }
  try { renderAuditStream(data.events); } catch (e) { console.error('Audit render error:', e); }
  try { updateAutopilotButton(data.summary ? data.summary.autopilot : true); } catch (e) { console.error('Autopilot render error:', e); }
}

/* ==========================================================================
   Header Controller Status & Mode
   ========================================================================== */
function renderControllerStatus(isSimMode) {
  const container = document.getElementById('controllerStatus');
  if (!container) return;

  if (isSimMode) {
    container.innerHTML = `
      <span class="status-dot amber"></span>
      <span class="status-text">Mode: <strong>Simulated Replay (Offline)</strong></span>
      <span class="status-vpc-badge badge-sim">Continuous Loop Active</span>
    `;
  } else {
    container.innerHTML = `
      <span class="status-dot green"></span>
      <span class="status-text">Netris Controller: <strong>adam-ctl.netris.io</strong></span>
      <span class="status-vpc-badge">VPC: Demo (ID: 20)</span>
    `;
  }
}

/* ==========================================================================
   Metrics Bar
   ========================================================================== */
function renderSummary(summary) {
  if (!summary) return;
  document.getElementById('statNodes').textContent = summary.total_nodes;
  document.getElementById('statGpus').textContent = `${summary.total_gpus} GPUs`;

  document.getElementById('statIdleNodes').textContent = summary.idle_nodes;
  document.getElementById('statIdleGpus').textContent = `${summary.idle_nodes * 8} GPUs Free`;

  document.getElementById('statAllocNodes').textContent = summary.allocated_nodes;
  document.getElementById('statAllocGpus').textContent = `${summary.used_gpus} GPUs In-Use`;

  document.getElementById('statActiveClusters').textContent = summary.active_jobs;

  const bw = summary.total_bandwidth_gbps || 0;
  document.getElementById('statBandwidth').textContent = bw > 0 ? bw.toFixed(1) : '0.0';
}

/* ==========================================================================
   8-Rail RoCEv2 Fabric Telemetry Panel
   ========================================================================== */
function renderTelemetry(telemetry) {
  const container = document.getElementById('railsContainer');
  if (!container || !telemetry) return;

  // Badges
  const pfc = telemetry.total_pfc_pauses || 0;
  const cnp = telemetry.total_cnp_notifications || 0;
  const lat = telemetry.avg_latency_us || 1.38;

  const badgePfc = document.getElementById('badgePfc');
  if (badgePfc) badgePfc.textContent = `PFC: ${pfc}/s`;

  const badgeCnp = document.getElementById('badgeCnp');
  if (badgeCnp) badgeCnp.textContent = `CNP: ${cnp}/s`;

  const badgeLat = document.getElementById('badgeLatency');
  if (badgeLat) badgeLat.textContent = `RTT: ${lat.toFixed(2)} µs`;

  const badgeLossless = document.getElementById('badgeLossless');
  if (badgeLossless) {
    badgeLossless.textContent = telemetry.active ? 'Zero Drops (100% Lossless)' : 'Zero Drops (Lossless Standby)';
  }

  const sub = document.getElementById('telemetryFabricSubtitle');
  if (sub && telemetry.fabric_status) {
    sub.textContent = `${telemetry.fabric_status} • 8 Rails / HGX Node • RoCEv2 Dynamic Routing`;
  }

  // Render 8 rails
  const rails = telemetry.rails || [0, 0, 0, 0, 0, 0, 0, 0];
  container.innerHTML = rails.map((bw, idx) => {
    const isActive = bw > 0;
    const utilPct = Math.min(100, Math.round((bw / 50.0) * 100));
    return `
      <div class="rail-box ${isActive ? 'active' : ''}">
        <div class="rail-header">
          <span class="rail-name">Rail ${idx}</span>
          <span class="rail-nic">ens${5 + idx}</span>
        </div>
        <div class="rail-meter">
          <div class="rail-fill" style="width: ${utilPct}%;"></div>
        </div>
        <div class="rail-stats-row">
          <span class="rail-speed ${isActive ? '' : 'idle'}">${bw > 0 ? bw.toFixed(1) : '0.0'} <small style="font-size: 9px; font-weight: normal;">Gb/s</small></span>
          <span class="rail-util">${utilPct}%</span>
        </div>
      </div>
    `;
  }).join('');
}

/* ==========================================================================
   Node Matrix
   ========================================================================== */
function renderNodes(nodes) {
  const container = document.getElementById('nodeGrid');
  if (!nodes || !nodes.length) {
    container.innerHTML = '<div class="empty-state">No nodes in pool</div>';
    return;
  }

  container.innerHTML = nodes.map(node => {
    const stateClass = `state-${node.state.toLowerCase()}`;
    const badgeClass = `badge-${node.state.toLowerCase()}`;
    const jobTag = node.job_id ? `<span class="node-job-tag">${node.job_id}</span>` : '<span>Pool: IDLE</span>';
    const clusterTag = node.cluster_id ? `<span class="badge badge-cluster">C-ID: ${node.cluster_id}</span>` : '';

    const railsHtml = (node.rail_activity && node.rail_activity.length === 8)
      ? node.rail_activity.map(bw => `<span class="rail-bar ${bw > 0 ? 'active' : ''}" style="${bw > 0 ? 'opacity: 1; background: var(--color-orange);' : ''}" title="${bw > 0 ? bw.toFixed(1) + ' Gbps' : 'Idle'}"></span>`).join('')
      : Array(8).fill('<span class="rail-bar"></span>').join('');

    return `
      <div class="node-card ${stateClass}" id="node-${node.name}">
        <div class="node-card-header">
          <span class="node-name">${node.name}</span>
          <span class="node-badge ${badgeClass}">${node.state}</span>
        </div>
        <div class="node-rails-visual" title="8x 400G RoCEv2 Spectrum-X Rails">
          ${railsHtml}
        </div>
        <div class="node-meta-row">
          ${jobTag}
          ${clusterTag}
        </div>
      </div>
    `;
  }).join('');
}

/* ==========================================================================
   Helper Functions
   ========================================================================== */
function formatDuration(sec) {
  if (sec === undefined || sec === null) return '0s';
  sec = Math.max(0, Math.round(sec));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s < 10 ? '0' : ''}${s}s`;
}

/* ==========================================================================
   Active Slurm Jobs Table
   ========================================================================== */
function renderJobs(jobs) {
  const tbody = document.getElementById('jobsTableBody');
  const countBadge = document.getElementById('activeJobsCountBadge');

  if (!jobs || !jobs.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center empty-state">No Slurm jobs currently running. (Submit one above or wait for Autopilot)</td></tr>';
    countBadge.textContent = '0 Running';
    return;
  }

  countBadge.textContent = `${jobs.length} Active`;

  tbody.innerHTML = jobs.map(job => {
    const nodesList = job.allocated_nodes && job.allocated_nodes.length
      ? `${job.nodes_count} nodes (${job.nodes_count * 8} GPUs)`
      : `${job.nodes_count} nodes (Queued)`;

    let clusterPill = '';
    let progressHtml = '';

    if (job.state === 'PROVISIONING') {
      const provElapsed = job.provision_elapsed || 0;
      const provTotal = job.provision_time || 120;
      const provPct = Math.min(100, Math.round((provElapsed / provTotal) * 100));
      clusterPill = job.cluster_id
        ? `<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">Prov C-ID #${job.cluster_id}</span>`
        : `<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">Creating Netris Cluster...</span>`;

      progressHtml = `
        <div class="job-progress-wrapper">
          <div class="job-progress-bar">
            <div class="job-progress-fill" style="width: ${provPct}%; background: linear-gradient(90deg, #f59e0b, #d97706);"></div>
          </div>
          <div class="job-progress-text">
            <span>Netris Sync ${provPct}%</span>
            <span>${formatDuration(provElapsed)} / ~2m</span>
          </div>
        </div>
      `;
    } else if (job.state === 'TEARDOWN') {
      const tearElapsed = job.teardown_elapsed || 0;
      const tearTotal = job.teardown_time || 120;
      const tearPct = Math.min(100, Math.round((tearElapsed / tearTotal) * 100));
      clusterPill = `<span class="badge" style="background: rgba(239, 68, 68, 0.2); color: #f87171;">Tearing Down #${job.cluster_id}</span>`;

      progressHtml = `
        <div class="job-progress-wrapper">
          <div class="job-progress-bar">
            <div class="job-progress-fill" style="width: ${tearPct}%; background: linear-gradient(90deg, #ef4444, #b91c1c);"></div>
          </div>
          <div class="job-progress-text">
            <span>Teardown ${tearPct}%</span>
            <span>${formatDuration(tearElapsed)} / ~2m</span>
          </div>
        </div>
      `;
    } else {
      // RUNNING or PENDING
      const remainingSec = Math.max(0, Math.round(job.duration - (job.elapsed || 0)));
      const pct = job.progress || 0;
      clusterPill = job.cluster_id
        ? `<span class="badge badge-cluster" title="Netris Server Cluster ID">#${job.cluster_id} (${job.cluster_name})</span>`
        : `<span class="badge" style="color: #fbbf24;">Queued...</span>`;

      progressHtml = `
        <div class="job-progress-wrapper">
          <div class="job-progress-bar">
            <div class="job-progress-fill" style="width: ${pct}%;"></div>
          </div>
          <div class="job-progress-text">
            <span>${pct.toFixed(0)}% • ${formatDuration(remainingSec)} left</span>
            <span>${formatDuration(job.elapsed)} / ${formatDuration(job.duration)}</span>
          </div>
        </div>
      `;
    }

    return `
      <tr>
        <td><strong style="font-family: var(--font-mono); color: #38bdf8;">${job.id}</strong></td>
        <td>
          <div style="font-weight: 600;">${job.name}</div>
          <div style="font-size: 10px; color: var(--text-dim);">${job.user}</div>
        </td>
        <td>${nodesList}</td>
        <td><span class="badge badge-pattern">${job.pattern}</span></td>
        <td>${clusterPill}</td>
        <td>${progressHtml}</td>
        <td style="font-family: var(--font-mono); color: var(--color-orange);">${(job.throughput_gbps || 0).toFixed(1)} Gb/s</td>
        <td>
          <button class="btn btn-sm btn-ghost text-danger" onclick="cancelJob('${job.id}')" title="Cancel & Teardown">Cancel</button>
        </td>
      </tr>
    `;
  }).join('');
}

/* ==========================================================================
   Completed Jobs History
   ========================================================================== */
function renderHistory(history) {
  const tbody = document.getElementById('historyTableBody');
  if (!history || !history.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center empty-state">No historical runs yet.</td></tr>';
    return;
  }

  tbody.innerHTML = history.slice(0, 8).map(job => {
    return `
      <tr>
        <td style="font-family: var(--font-mono);">${job.id}</td>
        <td>${job.name}</td>
        <td>${job.nodes_count} nodes</td>
        <td>${formatDuration(job.duration)}</td>
        <td style="color: var(--text-dim); font-size: 11px;">~2m Prov → ~${formatDuration(job.duration)} Run → ~2m Teardown</td>
        <td><span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399;">COMPLETED</span></td>
      </tr>
    `;
  }).join('');
}

/* ==========================================================================
   Netris Controller Sync View
   ========================================================================== */
function renderNetrisClusters(clusters) {
  const container = document.getElementById('netrisClustersContainer');
  if (!clusters || !clusters.length) {
    container.innerHTML = '<div class="empty-state">No Server Clusters configured in Netris.</div>';
    return;
  }

  container.innerHTML = clusters.map(c => {
    const serversCount = c.servers ? c.servers.length : 0;
    const vnets = (c.resources && c.resources.vnets) ? c.resources.vnets : [];
    const vnetNames = vnets.map(v => v.name).join(', ') || 'None';

    return `
      <div class="netris-cluster-card">
        <div class="cluster-header">
          <span class="cluster-title">${c.name}</span>
          <span class="cluster-id-badge">ID: ${c.id}</span>
        </div>
        <div class="cluster-details">
          <span>VPC: <strong>${c.vpc?.name || 'Demo'}</strong></span>
          <span>•</span>
          <span class="cluster-nodes-pill">${serversCount} HGX Servers</span>
          <span>•</span>
          <span class="cluster-vnet-tag">V-Net: ${vnetNames}</span>
        </div>
      </div>
    `;
  }).join('');
}

/* ==========================================================================
   Live Audit Stream
   ========================================================================== */
function renderAuditStream(events) {
  const container = document.getElementById('auditStream');
  if (!container) return;
  if (!events || !events.length) {
    container.innerHTML = '<div class="empty-state">No events recorded.</div>';
    return;
  }

  const lastEvent = events[events.length - 1];
  const lastId = lastEvent ? lastEvent.id : events.length;
  if (events.length === lastRenderedEventsCount && lastId === lastRenderedEventId) return;
  lastRenderedEventsCount = events.length;
  lastRenderedEventId = lastId;

  const reversed = [...events].reverse();
  container.innerHTML = reversed.map(e => {
    let tagClass = 'tag-slurm';
    const src = e.source || '';
    if (src.includes('NETRIS_API')) tagClass = 'tag-netris-api';
    else if (src.includes('NETRIS')) tagClass = 'tag-netris';
    else if (src.includes('FABRIC')) tagClass = 'tag-fabric';

    return `
      <div class="audit-row">
        <span class="audit-time">${escapeHtml(e.timestamp || '')}</span>
        <span class="audit-tag ${tagClass}">[${escapeHtml(src)}]</span>
        <span class="audit-msg">${escapeHtml(e.message || '')}</span>
      </div>
    `;
  }).join('');
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/* ==========================================================================
   Actions & Handlers
   ========================================================================== */
async function toggleAutopilot() {
  try {
    const res = await fetch('/api/autopilot', { method: 'POST' });
    const data = await res.json();
    updateAutopilotButton(data.autopilot);
    fetchState();
  } catch (err) {
    console.error('Error toggling autopilot:', err);
  }
}

function updateAutopilotButton(isActive) {
  const btn = document.getElementById('autopilotToggle');
  const txt = btn.querySelector('.toggle-text');
  if (isActive) {
    btn.classList.add('active');
    txt.textContent = 'ON';
  } else {
    btn.classList.remove('active');
    txt.textContent = 'OFF';
  }
}

async function cancelJob(jobId) {
  if (!confirm(`Cancel Job ${jobId} and deprovision its Netris Server Cluster?`)) return;
  try {
    await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
    fetchState();
  } catch (err) {
    console.error('Error cancelling job:', err);
  }
}

async function triggerTeardown() {
  if (!confirm('Emergency Teardown: Deprovision all active Netris Server Clusters and reset the Slurm pool to IDLE?')) return;
  try {
    await fetch('/api/teardown', { method: 'POST' });
    fetchState();
  } catch (err) {
    console.error('Error triggering teardown:', err);
  }
}

async function refreshNetrisClusters() {
  fetchState();
}

function clearEventLog() {
  document.getElementById('auditStream').innerHTML = '<div class="empty-state">Log cleared.</div>';
}

/* ==========================================================================
   Modal Dialog
   ========================================================================== */
function openSubmitModal() {
  document.getElementById('submitModal').style.display = 'flex';
}

function closeSubmitModal() {
  document.getElementById('submitModal').style.display = 'none';
}

function onModelSelectChange() {
  const select = document.getElementById('modalModelSelect');
  const opt = select.options[select.selectedIndex];
  const customGroup = document.getElementById('customNameGroup');

  if (opt.value === 'Custom') {
    customGroup.style.display = 'flex';
  } else {
    customGroup.style.display = 'none';
    if (opt.dataset.nodes) {
      document.getElementById('modalNodesSelect').value = opt.dataset.nodes;
    }
    if (opt.dataset.dur) {
      document.getElementById('modalDurationInput').value = opt.dataset.dur;
    }
    if (opt.dataset.pattern) {
      document.getElementById('modalPatternSelect').value = opt.dataset.pattern;
    }
  }
}

async function submitCustomJob() {
  const select = document.getElementById('modalModelSelect');
  const isCustom = select.value === 'Custom';
  const name = isCustom ? (document.getElementById('modalCustomName').value || 'Custom-AI-Job') : select.value;
  const nodes = parseInt(document.getElementById('modalNodesSelect').value, 10);
  const duration = parseInt(document.getElementById('modalDurationInput').value, 10);
  const pattern = document.getElementById('modalPatternSelect').value;

  try {
    const res = await fetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        nodes,
        duration,
        pattern,
        user: 'interactive-eng'
      })
    });
    if (!res.ok) {
      const errData = await res.json();
      alert(`Submission failed: ${errData.error || res.statusText}`);
      return;
    }
    closeSubmitModal();
    fetchState();
  } catch (err) {
    alert(`Error submitting job: ${err.message}`);
  }
}
