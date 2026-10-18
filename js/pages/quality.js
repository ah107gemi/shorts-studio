// ============================================
// Quality Control Page
// ============================================
import { api, showToast, navigateTo, state, escapeHtml } from '../app.js';

let currentProjectId = null;

export async function render() {
    return `
        <div class="page-header-row mb-3">
            <div>
                <h1>✅ Automated Quality Control</h1>
                <p class="text-secondary">Verify script approval, scene durations, vertical resolution, narration, and asset readiness before publishing</p>
            </div>
            <div class="btn-group">
                <button class="btn btn-primary" id="run-quality-checks-btn">🔍 Run Comprehensive Checks</button>
            </div>
        </div>

        <!-- Project Selector & Overall Score -->
        <div class="card mb-3">
            <div class="card-body flex items-center justify-between flex-wrap gap-3">
                <div class="flex items-center gap-2">
                    <label class="text-sm font-semibold" for="qc-project-select">Project:</label>
                    <select id="qc-project-select" class="form-control" style="min-width: 240px;"></select>
                </div>
                <div class="flex items-center gap-3">
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-semibold">QC Score:</span>
                        <span class="badge badge-info" id="qc-score-badge" style="font-size: 1rem; padding: 4px 12px;">—</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-semibold">Verdict:</span>
                        <span class="badge badge-draft" id="qc-verdict-badge">Not Checked</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Checks List Card -->
        <div class="card">
            <div class="card-header flex justify-between items-center">
                <h3 class="card-title">Production Quality Checklist</h3>
                <span class="text-xs text-muted" id="qc-timestamp">Last checked: Never</span>
            </div>
            <div class="card-body" id="qc-checks-container">
                <div class="empty-state" style="padding: 40px 20px;">
                    <div class="empty-state-icon">📋</div>
                    <h4>No Quality Check Run Yet</h4>
                    <p class="text-sm">Click "Run Comprehensive Checks" to inspect this project for missing assets, script approvals, and vertical video compliance.</p>
                    <button class="btn btn-primary btn-sm" onclick="document.getElementById('run-quality-checks-btn').click()">Run Checks Now</button>
                </div>
            </div>
        </div>
    `;
}

export async function init() {
    const select = document.getElementById('qc-project-select');
    await populateProjectsDropdown(select);

    select.addEventListener('change', async (e) => {
        currentProjectId = e.target.value;
        state.set('currentProject', currentProjectId);
        await loadQualityReport(currentProjectId);
    });

    document.getElementById('run-quality-checks-btn').addEventListener('click', triggerRunChecks);

    if (state.currentProject) {
        select.value = state.currentProject;
        currentProjectId = state.currentProject;
        await loadQualityReport(currentProjectId);
    } else if (select.options.length > 0) {
        select.selectedIndex = 0;
        currentProjectId = select.value;
        state.set('currentProject', currentProjectId);
        await loadQualityReport(currentProjectId);
    }
}

async function populateProjectsDropdown(select) {
    try {
        const data = await api('/projects');
        const list = Array.isArray(data) ? data : (data.items || []);
        if (list.length === 0) {
            select.innerHTML = '<option value="">No projects found</option>';
            return;
        }
        select.innerHTML = list.map(p => `
            <option value="${p.id}">${escapeHtml(p.name || p.topic || 'Untitled')}</option>
        `).join('');
    } catch {
        select.innerHTML = '<option value="">Error loading projects</option>';
    }
}

async function loadQualityReport(projectId) {
    if (!projectId) return;
    try {
        const report = await api(`/projects/${projectId}/quality-report`);
        renderReport(report);
    } catch {
        // Not run yet
    }
}

async function triggerRunChecks() {
    if (!currentProjectId) {
        showToast('warning', 'Select a project first');
        return;
    }
    const container = document.getElementById('qc-checks-container');
    container.innerHTML = '<div class="loading-overlay"><div class="spinner"></div><span>Running automated checks...</span></div>';
    try {
        const report = await api(`/projects/${currentProjectId}/quality-check`, { method: 'POST' });
        renderReport(report);
        showToast('success', `Checks complete — Score: ${report.score}%`);
    } catch (err) {
        showToast('error', 'QC failed', err.message);
    }
}

function renderReport(report) {
    const scoreBadge = document.getElementById('qc-score-badge');
    const verdictBadge = document.getElementById('qc-verdict-badge');
    const timestamp = document.getElementById('qc-timestamp');
    const container = document.getElementById('qc-checks-container');

    const score = report.score ?? 0;
    scoreBadge.textContent = `${score}%`;
    scoreBadge.className = `badge ${score >= 80 ? 'badge-success' : score >= 50 ? 'badge-warning' : 'badge-danger'}`;

    const verdict = report.overall_status || 'warning';
    verdictBadge.textContent = verdict.toUpperCase();
    verdictBadge.className = `badge ${verdict === 'pass' ? 'badge-success' : verdict === 'warning' ? 'badge-warning' : 'badge-danger'}`;

    if (report.checked_at) {
        timestamp.textContent = `Last checked: ${new Date(report.checked_at).toLocaleTimeString()}`;
    }

    const checks = report.checks || [];
    if (checks.length === 0) {
        container.innerHTML = '<p class="text-sm text-secondary">No check results returned.</p>';
        return;
    }

    container.innerHTML = `
        <div class="flex flex-col gap-2">
            ${checks.map(c => {
                const icon = c.status === 'pass' ? '✅' : c.status === 'warning' ? '⚠️' : '❌';
                const colorCls = c.status === 'pass' ? 'text-success' : c.status === 'warning' ? 'text-warning' : 'text-danger';
                return `
                    <div class="card p-3" style="background: #191924; border-left: 4px solid ${c.status === 'pass' ? '#2ecc71' : c.status === 'warning' ? '#f1c40f' : '#e74c3c'};">
                        <div class="flex justify-between items-center mb-1">
                            <div class="flex items-center gap-2">
                                <span style="font-size: 1.1rem;">${icon}</span>
                                <strong class="text-sm font-semibold">${escapeHtml(c.check_name.replace(/_/g, ' ').toUpperCase())}</strong>
                            </div>
                            <span class="badge ${c.status === 'pass' ? 'badge-success' : c.status === 'warning' ? 'badge-warning' : 'badge-danger'}">${c.status.toUpperCase()}</span>
                        </div>
                        <p class="text-sm ${colorCls} mb-1">${escapeHtml(c.message || '')}</p>
                        ${c.details ? `<pre class="text-xs text-muted" style="background: #111116; padding: 6px; border-radius: 4px; overflow-x: auto;">${escapeHtml(JSON.stringify(c.details, null, 2))}</pre>` : ''}
                    </div>
                `;
            }).join('')}
        </div>
    `;
}
