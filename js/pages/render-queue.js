// ============================================
// Render Queue Page
// ============================================
import { api, showToast, navigateTo, statusBadge, formatDuration, formatDateTime, state, escapeHtml } from '../app.js';

let refreshTimer = null;

export async function render() {
    return `
        <div class="page-header-row mb-3">
            <div>
                <h1>⚙️ Render Queue</h1>
                <p class="text-secondary">Monitor multi-stage video composition, FFmpeg rendering jobs, and worker progress</p>
            </div>
            <div class="btn-group">
                <button class="btn btn-secondary" id="refresh-queue-btn">🔄 Refresh Queue</button>
                <button class="btn btn-primary" id="new-render-shortcut-btn">➕ New Render</button>
            </div>
        </div>

        <!-- Render Queue Overview Cards -->
        <div class="card-grid mb-3" style="grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));">
            <div class="card stat-card">
                <div class="stat-value text-accent" id="stat-active-renders">0</div>
                <div class="stat-label">Active Renders</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value text-warning" id="stat-pending-renders">0</div>
                <div class="stat-label">Queued / Pending</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value text-success" id="stat-completed-renders">0</div>
                <div class="stat-label">Completed Renders</div>
            </div>
        </div>

        <!-- Jobs Table Card -->
        <div class="card">
            <div class="card-header flex justify-between items-center">
                <h3 class="card-title">Production Jobs</h3>
                <span class="text-xs text-muted" id="queue-auto-refresh-indicator">Auto-refresh: Active (every 3s)</span>
            </div>
            <div class="card-body" id="queue-table-container">
                <div class="loading-overlay"><div class="spinner"></div><span>Loading render jobs...</span></div>
            </div>
        </div>
    `;
}

export async function init() {
    document.getElementById('refresh-queue-btn').addEventListener('click', loadQueue);
    document.getElementById('new-render-shortcut-btn').addEventListener('click', () => navigateTo('video-editor'));

    await loadQueue();

    // Auto-refresh queue while viewing this page
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(async () => {
        if (state.currentPage === 'render-queue') {
            await loadQueue(false);
        } else {
            clearInterval(refreshTimer);
        }
    }, 3000);
}

async function loadQueue(showLoading = true) {
    const container = document.getElementById('queue-table-container');
    if (!container) return;

    try {
        if (showLoading && !container.querySelector('table')) {
            container.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
        }

        const res = await api('/render/queue');
        const jobs = res.queue || [];

        // Update stats
        document.getElementById('stat-active-renders').textContent = res.active_count ?? 0;
        document.getElementById('stat-pending-renders').textContent = res.pending_count ?? 0;
        const completedCount = jobs.filter(j => j.status === 'completed').length;
        document.getElementById('stat-completed-renders').textContent = completedCount;

        if (jobs.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="padding: 40px 20px;">
                    <div class="empty-state-icon">⚙️</div>
                    <h4>No Rendering Jobs in Queue</h4>
                    <p class="text-sm">When you click "Start Full Render" in the Video Editor, jobs will appear and track progress here.</p>
                    <button class="btn btn-primary btn-sm" onclick="window.__navigateTo('video-editor')">Go to Video Editor</button>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <table class="table" style="width: 100%;">
                <thead>
                    <tr>
                        <th>Project</th>
                        <th>Status</th>
                        <th>Progress</th>
                        <th>Current Stage</th>
                        <th>Created</th>
                        <th style="text-align: right;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${jobs.map(j => renderJobRow(j)).join('')}
                </tbody>
            </table>
        `;

        // Attach action handlers
        container.querySelectorAll('.job-cancel-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const jobId = e.target.dataset.id;
                try {
                    await api(`/jobs/${jobId}/cancel`, { method: 'POST' });
                    showToast('info', 'Render job cancelled');
                    await loadQueue(false);
                } catch (err) {
                    showToast('error', 'Cancel failed', err.message);
                }
            });
        });

        container.querySelectorAll('.job-retry-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const jobId = e.target.dataset.id;
                try {
                    await api(`/jobs/${jobId}/retry`, { method: 'POST' });
                    showToast('success', 'Job requeued');
                    await loadQueue(false);
                } catch (err) {
                    showToast('error', 'Retry failed', err.message);
                }
            });
        });

        container.querySelectorAll('.job-export-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const projId = e.target.dataset.proj;
                state.set('currentProject', projId);
                navigateTo('export');
            });
        });

    } catch (err) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>Failed to load render queue: ${escapeHtml(err.message)}</p>
                <button class="btn btn-secondary btn-sm" onclick="document.getElementById('refresh-queue-btn').click()">Retry</button>
            </div>
        `;
    }
}

function renderJobRow(job) {
    const isRunning = job.status === 'running';
    const isPending = ['pending', 'queued'].includes(job.status);
    const isFailed = job.status === 'failed';
    const isCompleted = job.status === 'completed';

    const pct = Math.round(job.progress || 0);

    return `
        <tr>
            <td>
                <div class="font-semibold text-sm">${escapeHtml(job.project_name || 'Project')}</div>
                <div class="text-xs text-muted">ID: ${job.job_id.substring(0, 8)}</div>
            </td>
            <td>${statusBadge(job.status)}</td>
            <td style="min-width: 140px;">
                <div class="progress-bar mb-1">
                    <div class="progress-bar-fill ${isFailed ? 'bg-danger' : ''}" style="width: ${pct}%;"></div>
                </div>
                <span class="text-xs text-secondary">${pct}%</span>
            </td>
            <td>
                <span class="text-xs ${isFailed ? 'text-danger' : 'text-secondary'}">
                    ${escapeHtml(job.current_stage || (isRunning ? 'Processing video...' : job.status))}
                </span>
            </td>
            <td class="text-xs text-muted">${formatDateTime(job.created_at)}</td>
            <td style="text-align: right;">
                <div class="btn-group" style="justify-content: flex-end;">
                    ${isRunning || isPending ? `
                        <button class="btn btn-ghost btn-sm text-danger job-cancel-btn" data-id="${job.job_id}">Cancel</button>
                    ` : ''}
                    ${isFailed ? `
                        <button class="btn btn-secondary btn-sm job-retry-btn" data-id="${job.job_id}">🔄 Retry</button>
                    ` : ''}
                    ${isCompleted ? `
                        <button class="btn btn-primary btn-sm job-export-btn" data-proj="${job.project_id}">View Export →</button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `;
}
