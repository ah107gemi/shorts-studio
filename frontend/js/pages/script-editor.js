// ============================================
// Script Editor Page
// ============================================
import { api, showToast, navigateTo, confirmModal, showModal, hideModal, formatDuration, state, escapeHtml } from '../app.js';

let currentProject = null;
let scriptContent = '';
let versions = [];

export async function render() {
    return `
        <div class="page-header">
            <div class="page-header-row">
                <div>
                    <h1>📝 Script Editor</h1>
                    <p>Write and refine your video script</p>
                </div>
                <div class="form-group mb-0" style="min-width:240px;">
                    <select id="se-project-select" class="form-select">
                        <option value="">— Select project —</option>
                    </select>
                </div>
            </div>
        </div>

        <div id="se-no-project" class="empty-state">
            <div class="empty-state-icon">📝</div>
            <h3>Select a Project</h3>
            <p>Choose a project from the dropdown above, or create a new one.</p>
            <button class="btn btn-primary" onclick="window.__navigateTo('new-project')">➕ New Project</button>
        </div>

        <div id="se-editor" style="display:none;">
            <!-- Toolbar -->
            <div class="card mb-2" style="padding: 12px 16px;">
                <div class="flex items-center justify-between flex-wrap gap-1">
                    <div class="btn-group">
                        <button class="btn btn-primary" id="se-ai-generate">🤖 AI Generate</button>
                        <button class="btn btn-secondary" id="se-scene-split">✂️ Split Scenes</button>
                        <button class="btn btn-secondary" id="se-save">💾 Save</button>
                        <button class="btn btn-ghost" id="se-revert">↩️ Revert</button>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-sm text-muted" id="se-word-count">0 words</span>
                        <span class="text-sm text-muted">•</span>
                        <span class="text-sm text-muted" id="se-est-duration">~0s</span>
                        <button class="btn btn-primary btn-sm" id="se-approve" title="Mark script as approved">✅ Approve</button>
                    </div>
                </div>
            </div>

            <!-- Tone/Style Controls -->
            <div class="card mb-2" style="padding: 12px 16px;">
                <div class="form-row" style="margin-bottom:0;">
                    <div class="form-group mb-0">
                        <label class="form-label">Tone</label>
                        <select id="se-tone" class="form-select">
                            <option value="professional">Professional</option>
                            <option value="casual">Casual</option>
                            <option value="humorous">Humorous</option>
                            <option value="dramatic">Dramatic</option>
                            <option value="inspirational">Inspirational</option>
                        </select>
                    </div>
                    <div class="form-group mb-0">
                        <label class="form-label">Style</label>
                        <select id="se-style" class="form-select">
                            <option value="documentary">Documentary</option>
                            <option value="tutorial">Tutorial</option>
                            <option value="explainer">Explainer</option>
                            <option value="narrative">Narrative</option>
                            <option value="listicle">Listicle</option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="split-view-sidebar">
                <!-- Main Editor -->
                <div>
                    <div class="panel">
                        <div class="panel-header">
                            <h3>Full Script</h3>
                            <button class="btn btn-ghost btn-sm" id="se-edit-toggle">Edit</button>
                        </div>
                        <div class="panel-body">
                            <textarea id="se-textarea" class="form-textarea" style="min-height:400px; font-size: 0.95rem; line-height: 1.7;" placeholder="Your script will appear here. Click 'AI Generate' to create a script, or start writing manually."></textarea>
                        </div>
                    </div>

                    <!-- Narration Sections -->
                    <div class="panel mt-2" id="se-sections-panel" style="display:none;">
                        <div class="panel-header">
                            <h3>Narration Sections</h3>
                        </div>
                        <div class="panel-body" id="se-sections"></div>
                    </div>
                </div>

                <!-- Version History Sidebar -->
                <div class="panel">
                    <div class="panel-header">
                        <h3>Version History</h3>
                    </div>
                    <div class="panel-body" id="se-versions" style="max-height: 600px; overflow-y: auto;">
                        <p class="text-muted text-sm">No versions yet</p>
                    </div>
                </div>
            </div>

            <!-- AI Generation Progress -->
            <div class="card mt-2" id="se-progress-card" style="display:none;">
                <div class="card-header">
                    <h3 class="card-title">🤖 AI Generation</h3>
                    <span id="se-progress-status" class="badge badge-rendering">Generating</span>
                </div>
                <div class="card-body">
                    <div class="progress-bar progress-bar-lg">
                        <div class="progress-bar-fill" id="se-progress-fill" style="width: 0%"></div>
                    </div>
                    <p class="text-sm text-muted mt-1" id="se-progress-msg">Starting script generation...</p>
                </div>
            </div>
        </div>
    `;
}

export async function init() {
    const projectSelect = document.getElementById('se-project-select');
    const textarea = document.getElementById('se-textarea');
    const editorContainer = document.getElementById('se-editor');
    const noProjectMsg = document.getElementById('se-no-project');

    // Load projects for selector
    try {
        const data = await api('/projects');
        const projects = Array.isArray(data) ? data : (data.projects || data.items || []);
        projects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id || p.project_id;
            opt.textContent = p.name || p.topic || 'Untitled';
            projectSelect.appendChild(opt);
        });

        // Auto-select current project
        if (state.currentProject) {
            projectSelect.value = state.currentProject;
            await loadProject(state.currentProject);
        }
    } catch (err) {
        showToast('error', 'Load Error', err.message);
    }

    // Project selection change
    projectSelect.addEventListener('change', async () => {
        const id = projectSelect.value;
        if (id) {
            state.set('currentProject', id);
            await loadProject(id);
        } else {
            editorContainer.style.display = 'none';
            noProjectMsg.style.display = '';
        }
    });

    // Live word count
    textarea.addEventListener('input', updateStats);

    // AI Generate
    document.getElementById('se-ai-generate').addEventListener('click', async () => {
        if (!currentProject) return;
        const confirmed = await confirmModal('Generate Script', 'This will use AI to generate a script based on your project settings. Continue?');
        if (!confirmed) return;

        const progressCard = document.getElementById('se-progress-card');
        progressCard.style.display = '';
        document.getElementById('se-progress-fill').style.width = '10%';
        document.getElementById('se-progress-msg').textContent = 'Sending request to AI provider...';

        try {
            const result = await api(`/projects/${currentProject}/script/generate`, {
                method: 'POST',
                body: {
                    tone: document.getElementById('se-tone').value,
                    style: document.getElementById('se-style').value,
                }
            });

            document.getElementById('se-progress-fill').style.width = '100%';
            document.getElementById('se-progress-msg').textContent = 'Script generated!';
            document.getElementById('se-progress-status').className = 'badge badge-completed';
            document.getElementById('se-progress-status').textContent = 'Complete';

            // If result has a job_id, poll for result
            if (result.job_id) {
                await pollJobResult(result.job_id);
            } else {
                const content = result.script || result.content || result.text || '';
                textarea.value = content;
                scriptContent = content;
                updateStats();
                showSections(content);
            }

            showToast('success', 'Script Generated', 'AI script is ready for review.');
            await loadVersions();
            setTimeout(() => { progressCard.style.display = 'none'; }, 2000);
        } catch (err) {
            document.getElementById('se-progress-fill').style.width = '100%';
            document.getElementById('se-progress-fill').className = 'progress-bar-fill danger';
            document.getElementById('se-progress-msg').textContent = err.message;
            document.getElementById('se-progress-status').className = 'badge badge-failed';
            document.getElementById('se-progress-status').textContent = 'Failed';
            showToast('error', 'Generation Failed', err.message);
        }
    });

    // Save
    document.getElementById('se-save').addEventListener('click', async () => {
        if (!currentProject) return;
        try {
            await api(`/projects/${currentProject}/script`, {
                method: 'PUT',
                body: { content: textarea.value }
            });
            scriptContent = textarea.value;
            showToast('success', 'Script Saved');
            await loadVersions();
        } catch (err) {
            showToast('error', 'Save Failed', err.message);
        }
    });

    // Revert
    document.getElementById('se-revert').addEventListener('click', () => {
        textarea.value = scriptContent;
        updateStats();
        showToast('info', 'Reverted', 'Script reverted to last saved version.');
    });

    // Scene Split
    document.getElementById('se-scene-split').addEventListener('click', async () => {
        if (!currentProject || !textarea.value.trim()) {
            showToast('warning', 'No Content', 'Write or generate a script first.');
            return;
        }
        try {
            await api(`/projects/${currentProject}/script/split-scenes`, {
                method: 'POST',
                body: { content: textarea.value }
            });
            showToast('success', 'Scenes Created', 'Script has been split into storyboard scenes.');
            navigateTo('storyboard');
        } catch (err) {
            showToast('error', 'Split Failed', err.message);
        }
    });

    // Approve
    document.getElementById('se-approve').addEventListener('click', async () => {
        if (!currentProject) return;
        const confirmed = await confirmModal('Approve Script', 'Mark this script as approved and move to production?');
        if (!confirmed) return;
        try {
            await api(`/projects/${currentProject}/script/approve`, { method: 'POST' });
            showToast('success', 'Script Approved', 'Moving to storyboard stage.');
        } catch (err) {
            showToast('error', 'Approve Failed', err.message);
        }
    });

    // Edit toggle
    document.getElementById('se-edit-toggle').addEventListener('click', () => {
        const ta = document.getElementById('se-textarea');
        ta.readOnly = !ta.readOnly;
        document.getElementById('se-edit-toggle').textContent = ta.readOnly ? 'Edit' : 'Editing';
    });
}

async function loadProject(projectId) {
    currentProject = projectId;
    document.getElementById('se-editor').style.display = '';
    document.getElementById('se-no-project').style.display = 'none';

    try {
        const project = await api(`/projects/${projectId}`);
        const script = project.script || project.script_content || '';
        document.getElementById('se-textarea').value = script;
        scriptContent = script;

        if (project.tone) document.getElementById('se-tone').value = project.tone;
        if (project.style) document.getElementById('se-style').value = project.style;

        updateStats();
        showSections(script);
        await loadVersions();
    } catch (err) {
        showToast('error', 'Load Error', err.message);
    }
}

async function loadVersions() {
    const container = document.getElementById('se-versions');
    try {
        const data = await api(`/projects/${currentProject}/script/versions`);
        versions = Array.isArray(data) ? data : (data.versions || data.items || []);
        if (versions.length === 0) {
            container.innerHTML = '<p class="text-muted text-sm">No versions yet</p>';
            return;
        }
        container.innerHTML = versions.map((v, i) => `
            <div class="card card-clickable mb-1 version-item" data-idx="${i}" style="padding: 10px;">
                <div class="flex items-center justify-between">
                    <strong class="text-sm">v${v.version || (versions.length - i)}</strong>
                    <span class="text-xs text-muted">${v.created_at ? new Date(v.created_at).toLocaleString() : ''}</span>
                </div>
                <p class="text-xs text-muted mt-1">${escapeHtml((v.content || v.script || '').substring(0, 60))}...</p>
            </div>
        `).join('');

        container.querySelectorAll('.version-item').forEach(item => {
            item.addEventListener('click', () => {
                const v = versions[item.dataset.idx];
                document.getElementById('se-textarea').value = v.content || v.script || '';
                updateStats();
                showToast('info', 'Version Loaded', `Loaded v${v.version || ''}`);
            });
        });
    } catch {
        container.innerHTML = '<p class="text-muted text-sm">No version history available</p>';
    }
}

function updateStats() {
    const text = document.getElementById('se-textarea').value;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    const estDuration = Math.round(words / 2.5); // ~150 wpm = 2.5 wps
    document.getElementById('se-word-count').textContent = `${words} words`;
    document.getElementById('se-est-duration').textContent = `~${formatDuration(estDuration)}`;
}

function showSections(text) {
    const panel = document.getElementById('se-sections-panel');
    const container = document.getElementById('se-sections');
    if (!text || !text.trim()) {
        panel.style.display = 'none';
        return;
    }

    const paragraphs = text.split(/\n\s*\n/).filter(p => p.trim());
    if (paragraphs.length <= 1) {
        panel.style.display = 'none';
        return;
    }

    panel.style.display = '';
    container.innerHTML = paragraphs.map((p, i) => `
        <div class="scene-card mb-1">
            <div class="flex items-center gap-1 mb-1">
                <span class="scene-card-number">${i + 1}</span>
                <span class="text-xs text-muted">${p.trim().split(/\s+/).length} words</span>
            </div>
            <p class="scene-card-preview">${escapeHtml(p.trim())}</p>
        </div>
    `).join('');
}

async function pollJobResult(jobId) {
    const maxAttempts = 60;
    for (let i = 0; i < maxAttempts; i++) {
        await new Promise(r => setTimeout(r, 2000));
        try {
            const job = await api(`/jobs/${jobId}`);
            const progress = job.progress || 0;
            document.getElementById('se-progress-fill').style.width = `${progress}%`;
            document.getElementById('se-progress-msg').textContent = job.message || `Progress: ${progress}%`;

            if (job.status === 'completed' || job.status === 'done') {
                const result = job.result || {};
                const content = result.script || result.content || result.text || '';
                if (content) {
                    document.getElementById('se-textarea').value = content;
                    scriptContent = content;
                    updateStats();
                    showSections(content);
                }
                return;
            }
            if (job.status === 'failed' || job.status === 'error') {
                throw new Error(job.error || job.message || 'Job failed');
            }
        } catch (err) {
            if (i === maxAttempts - 1) throw err;
        }
    }
}
