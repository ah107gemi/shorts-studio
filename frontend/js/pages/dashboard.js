// ============================================
// Dashboard Page
// ============================================
import { api, showToast, navigateTo, formatDate, formatDuration, statusBadge, state, escapeHtml, truncate } from '../app.js';

export async function render() {
    return `
        <div class="page-header">
            <h1>🎬 Welcome to Shorts Studio</h1>
            <p>Your AI-powered short video production pipeline</p>
        </div>

        <!-- Quick Actions -->
        <div class="btn-group mb-3">
            <button class="btn btn-primary btn-lg" id="dash-new-project">➕ New Project</button>
            <button class="btn btn-secondary btn-lg" id="dash-open-library">📁 Open Library</button>
            <button class="btn btn-ghost btn-lg" id="dash-settings">⚙️ Settings</button>
        </div>

        <!-- Stats Row -->
        <div class="card-grid mb-3" id="dash-stats" style="grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));">
            <div class="card stat-card">
                <div class="stat-value" id="stat-total">—</div>
                <div class="stat-label">Total Projects</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value" id="stat-active">—</div>
                <div class="stat-label">In Production</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value" id="stat-completed">—</div>
                <div class="stat-label">Completed</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value" id="stat-rendering">—</div>
                <div class="stat-label">Rendering</div>
            </div>
        </div>

        <!-- System Status -->
        <div class="card mb-3" id="system-status-card">
            <div class="card-header">
                <h3 class="card-title">System Status</h3>
                <button class="btn btn-ghost btn-sm" id="refresh-status">🔄 Refresh</button>
            </div>
            <div class="card-body" id="system-status-body">
                <div class="loading-overlay" style="padding: 20px;"><div class="spinner"></div></div>
            </div>
        </div>

        <!-- Active Jobs -->
        <div class="card mb-3" id="active-jobs-card" style="display:none;">
            <div class="card-header">
                <h3 class="card-title">Active Jobs</h3>
            </div>
            <div class="card-body" id="active-jobs-body"></div>
        </div>

        <!-- Recent Projects -->
        <div class="mb-3">
            <div class="page-header-row mb-2">
                <h2>Recent Projects</h2>
                <button class="btn btn-ghost btn-sm" id="dash-view-all">View All →</button>
            </div>
            <div id="recent-projects" class="card-grid">
                <div class="loading-overlay" style="grid-column: 1/-1;"><div class="spinner"></div><span>Loading projects...</span></div>
            </div>
        </div>
    `;
}

export async function init() {
    // Quick action buttons
    document.getElementById('dash-new-project').addEventListener('click', () => navigateTo('new-project'));
    document.getElementById('dash-open-library').addEventListener('click', () => navigateTo('project-library'));
    document.getElementById('dash-settings').addEventListener('click', () => navigateTo('settings'));
    document.getElementById('dash-view-all').addEventListener('click', () => navigateTo('project-library'));
    document.getElementById('refresh-status').addEventListener('click', loadSystemStatus);

    // Load data
    await Promise.allSettled([loadProjects(), loadSystemStatus(), loadActiveJobs()]);
}

async function loadProjects() {
    const container = document.getElementById('recent-projects');
    try {
        const data = await api('/projects?limit=6&sort=-updated_at');
        const projects = Array.isArray(data) ? data : (data.projects || data.items || []);
        state.projects = projects;

        // Stats
        const total = projects.length;
        const active = projects.filter(p => ['production', 'active', 'processing'].includes(p.status?.toLowerCase())).length;
        const completed = projects.filter(p => p.status?.toLowerCase() === 'completed').length;
        const rendering = projects.filter(p => p.status?.toLowerCase() === 'rendering').length;

        const statTotal = document.getElementById('stat-total');
        const statActive = document.getElementById('stat-active');
        const statCompleted = document.getElementById('stat-completed');
        const statRendering = document.getElementById('stat-rendering');
        if (statTotal) statTotal.textContent = total;
        if (statActive) statActive.textContent = active;
        if (statCompleted) statCompleted.textContent = completed;
        if (statRendering) statRendering.textContent = rendering;

        if (projects.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <div class="empty-state-icon">📂</div>
                    <h3>No projects yet</h3>
                    <p>Create your first short video project to get started!</p>
                    <button class="btn btn-primary" onclick="window.__navigateTo('new-project')">➕ Create Project</button>
                </div>
            `;
            return;
        }

        container.innerHTML = projects.slice(0, 6).map(p => `
            <div class="card card-clickable project-card" data-id="${p.id || p.project_id}">
                <div class="card-header">
                    <span class="card-title truncate">${escapeHtml(p.name || p.topic || 'Untitled')}</span>
                    ${statusBadge(p.status)}
                </div>
                <div class="card-body">
                    <p class="scene-card-preview">${escapeHtml(truncate(p.topic || p.description || '', 100))}</p>
                </div>
                <div class="card-footer">
                    <span class="text-xs text-muted">${formatDate(p.updated_at || p.created_at)}</span>
                    <span class="text-xs text-secondary">${formatDuration(p.duration)}</span>
                </div>
            </div>
        `).join('');

        // Click to open project
        container.querySelectorAll('.project-card').forEach(card => {
            card.addEventListener('click', () => {
                state.set('currentProject', card.dataset.id);
                navigateTo('script-editor');
            });
        });
    } catch (err) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <div class="empty-state-icon">⚠️</div>
                <h3>Could not load projects</h3>
                <p>${escapeHtml(err.message)}</p>
                <button class="btn btn-secondary" onclick="window.__navigateTo('new-project')">➕ Create New Instead</button>
            </div>
        `;
    }
}

async function loadSystemStatus() {
    const body = document.getElementById('system-status-body');
    try {
        const health = await api('/health');
        const items = [];

        items.push(statusRow('API Server', true, 'Running'));
        items.push(statusRow('FFmpeg', health.ffmpeg_available ?? health.ffmpeg ?? false,
            health.ffmpeg_available || health.ffmpeg ? 'Available' : 'Not found'));

        if (health.providers) {
            for (const [name, info] of Object.entries(health.providers)) {
                const configured = info.configured ?? info.available ?? !!info;
                items.push(statusRow(name, configured, configured ? 'Configured' : 'Not configured'));
            }
        }

        body.innerHTML = `<div class="flex flex-col gap-1">${items.join('')}</div>`;
    } catch (err) {
        body.innerHTML = `
            <div class="status-indicator">
                <span class="status-dot offline"></span>
                <span>Backend unavailable: ${escapeHtml(err.message)}</span>
            </div>
        `;
    }
}

function statusRow(name, ok, detail) {
    return `
        <div class="status-indicator" style="padding: 6px 0;">
            <span class="status-dot ${ok ? 'online' : 'offline'}"></span>
            <strong>${escapeHtml(name)}</strong>
            <span class="text-muted text-sm" style="margin-left: 4px;">— ${escapeHtml(detail)}</span>
        </div>
    `;
}

async function loadActiveJobs() {
    try {
        const data = await api('/jobs?status=active');
        const jobs = Array.isArray(data) ? data : (data.jobs || data.items || []);
        const card = document.getElementById('active-jobs-card');
        const body = document.getElementById('active-jobs-body');

        if (jobs.length === 0) {
            card.style.display = 'none';
            return;
        }

        card.style.display = '';
        body.innerHTML = jobs.map(j => `
            <div style="margin-bottom: 12px;">
                <div class="flex items-center justify-between mb-1">
                    <span>${escapeHtml(j.type || 'Job')} — ${escapeHtml(j.project_name || j.project_id || '')}</span>
                    ${statusBadge(j.status)}
                </div>
                <div class="progress-bar">
                    <div class="progress-bar-fill" style="width: ${j.progress ?? 0}%"></div>
                </div>
                <span class="text-xs text-muted">${j.progress ?? 0}%</span>
            </div>
        `).join('');
    } catch {
        // Jobs endpoint may not exist yet, ignore
    }
}
