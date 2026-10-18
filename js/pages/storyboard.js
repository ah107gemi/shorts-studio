// ============================================
// Storyboard Page
// ============================================
import { api, showToast, navigateTo, confirmModal, showModal, hideModal, formatDuration, state, escapeHtml, truncate } from '../app.js';

let scenes = [];
let projectId = null;

export async function render() {
    projectId = state.currentProject;
    return `
        <div class="page-header">
            <div class="page-header-row">
                <div>
                    <h1>🎞️ Storyboard</h1>
                    <p>Manage and arrange your video scenes</p>
                </div>
                <div class="btn-group">
                    <select id="sb-project-select" class="form-select" style="min-width:200px;"></select>
                    <button class="btn btn-primary" id="sb-generate">🤖 Generate from Script</button>
                    <button class="btn btn-secondary" id="sb-add-scene">➕ Add Scene</button>
                </div>
            </div>
        </div>

        <div id="sb-no-project" class="empty-state" style="display:none;">
            <div class="empty-state-icon">🎞️</div>
            <h3>Select a Project</h3>
            <p>Choose a project to view and edit its storyboard.</p>
        </div>

        <!-- Visual Consistency Indicator -->
        <div class="card mb-2" id="sb-consistency" style="display:none; padding: 10px 16px;">
            <div class="flex items-center gap-2">
                <span id="sb-consistency-icon">🎨</span>
                <span class="text-sm" id="sb-consistency-text">Visual style consistency: checking...</span>
            </div>
        </div>

        <div class="card-grid card-grid-sm" id="sb-scenes">
            <div class="loading-overlay" style="grid-column: 1/-1;"><div class="spinner"></div><span>Loading scenes...</span></div>
        </div>
    `;
}

export async function init() {
    const projectSelect = document.getElementById('sb-project-select');

    // Load projects
    try {
        const data = await api('/projects');
        const projects = Array.isArray(data) ? data : (data.projects || data.items || []);
        projectSelect.innerHTML = '<option value="">— Select project —</option>';
        projects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id || p.project_id;
            opt.textContent = p.name || p.topic || 'Untitled';
            projectSelect.appendChild(opt);
        });
        if (state.currentProject) {
            projectSelect.value = state.currentProject;
            await loadScenes(state.currentProject);
        } else {
            document.getElementById('sb-no-project').style.display = '';
            document.getElementById('sb-scenes').innerHTML = '';
        }
    } catch (err) {
        showToast('error', 'Load Error', err.message);
    }

    projectSelect.addEventListener('change', async () => {
        projectId = projectSelect.value;
        state.set('currentProject', projectId);
        if (projectId) {
            document.getElementById('sb-no-project').style.display = 'none';
            await loadScenes(projectId);
        } else {
            document.getElementById('sb-no-project').style.display = '';
            document.getElementById('sb-scenes').innerHTML = '';
        }
    });

    // Generate from script
    document.getElementById('sb-generate').addEventListener('click', async () => {
        if (!projectId) { showToast('warning', 'No Project'); return; }
        const confirmed = await confirmModal('Generate Storyboard', 'Generate scene cards from the project script?');
        if (!confirmed) return;
        try {
            await api(`/projects/${projectId}/storyboard/generate`, { method: 'POST' });
            showToast('success', 'Storyboard Generated');
            await loadScenes(projectId);
        } catch (err) {
            showToast('error', 'Generation Failed', err.message);
        }
    });

    // Add scene
    document.getElementById('sb-add-scene').addEventListener('click', () => {
        if (!projectId) { showToast('warning', 'No Project'); return; }
        openSceneModal();
    });
}

async function loadScenes(pid) {
    const container = document.getElementById('sb-scenes');
    container.innerHTML = '<div class="loading-overlay" style="grid-column:1/-1;"><div class="spinner"></div></div>';
    try {
        const data = await api(`/projects/${pid}/scenes`);
        scenes = Array.isArray(data) ? data : (data.scenes || data.items || []);
        renderScenes();
        checkConsistency();
    } catch (err) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column:1/-1;">
                <div class="empty-state-icon">🎞️</div>
                <h3>No scenes yet</h3>
                <p>Generate a storyboard from your script or add scenes manually.</p>
            </div>
        `;
    }
}

function renderScenes() {
    const container = document.getElementById('sb-scenes');
    if (scenes.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column:1/-1;">
                <div class="empty-state-icon">🎞️</div>
                <h3>No scenes</h3>
                <p>Generate from your script or add scenes manually.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = scenes.map((s, i) => {
        const hasVideo = s.asset_url && (s.asset_filename?.match(/\.(mp4|mov|webm|mkv)$/i) || s.asset_url.includes('.mp4'));
        const thumbHtml = hasVideo
            ? `<video src="${s.asset_url}" muted preload="metadata" style="width:100%;height:100%;object-fit:cover;border-radius:var(--radius-sm);"></video>`
            : (s.thumbnail || s.asset_url ? `<img src="${s.thumbnail || s.asset_url}" alt="">` : '🖼️');

        return `
        <div class="scene-card" data-idx="${i}">
            <div class="scene-card-thumbnail">
                ${thumbHtml}
            </div>
            <div class="flex items-center justify-between mb-1">
                <span class="scene-card-number">#${s.scene_number || i + 1}</span>
                <span class="text-xs text-muted">${formatDuration(s.duration_seconds || s.duration)}</span>
            </div>
            <div class="scene-card-preview mb-1">${escapeHtml(truncate(s.narration_text || s.narration || s.text || '', 100))}</div>
            <p class="text-xs text-muted">${escapeHtml(truncate(s.visual_description || s.description || '', 60))}</p>
            ${s.asset_filename ? `<div class="text-xs text-info truncate" style="margin-top:4px;font-size:0.75rem;">📁 ${escapeHtml(s.asset_filename)}</div>` : ''}
            <div class="scene-card-meta">
                <div class="btn-group">
                    <button class="btn btn-ghost btn-sm sb-move-up" data-idx="${i}" title="Move up">⬆️</button>
                    <button class="btn btn-ghost btn-sm sb-move-down" data-idx="${i}" title="Move down">⬇️</button>
                    <button class="btn btn-ghost btn-sm sb-edit" data-idx="${i}" title="Edit">✏️</button>
                    <button class="btn btn-ghost btn-sm sb-dup" data-idx="${i}" title="Duplicate">📋</button>
                    <button class="btn btn-ghost btn-sm sb-del" data-idx="${i}" title="Delete">🗑️</button>
                </div>
            </div>
        </div>
        `;
    }).join('');

    // Event handlers
    container.querySelectorAll('.sb-edit').forEach(btn => {
        btn.addEventListener('click', () => openSceneModal(scenes[btn.dataset.idx], btn.dataset.idx));
    });

    container.querySelectorAll('.sb-del').forEach(btn => {
        btn.addEventListener('click', async () => {
            const confirmed = await confirmModal('Delete Scene', 'Remove this scene from the storyboard?');
            if (!confirmed) return;
            const scene = scenes[btn.dataset.idx];
            try {
                await api(`/projects/${projectId}/scenes/${scene.id || scene.scene_id}`, { method: 'DELETE' });
                showToast('success', 'Scene Deleted');
                await loadScenes(projectId);
            } catch (err) {
                showToast('error', 'Delete Failed', err.message);
            }
        });
    });

    container.querySelectorAll('.sb-dup').forEach(btn => {
        btn.addEventListener('click', async () => {
            const scene = scenes[btn.dataset.idx];
            try {
                await api(`/projects/${projectId}/scenes`, {
                    method: 'POST',
                    body: { ...scene, id: undefined, scene_id: undefined, scene_number: scenes.length + 1 }
                });
                showToast('success', 'Scene Duplicated');
                await loadScenes(projectId);
            } catch (err) {
                showToast('error', 'Duplicate Failed', err.message);
            }
        });
    });

    container.querySelectorAll('.sb-move-up').forEach(btn => {
        btn.addEventListener('click', () => moveScene(parseInt(btn.dataset.idx), -1));
    });
    container.querySelectorAll('.sb-move-down').forEach(btn => {
        btn.addEventListener('click', () => moveScene(parseInt(btn.dataset.idx), 1));
    });
}

async function moveScene(idx, direction) {
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= scenes.length) return;
    try {
        await api(`/projects/${projectId}/scenes/reorder`, {
            method: 'POST',
            body: { scene_index: idx, new_index: newIdx }
        });
        await loadScenes(projectId);
    } catch {
        // Fallback: reorder locally
        const [item] = scenes.splice(idx, 1);
        scenes.splice(newIdx, 0, item);
        renderScenes();
    }
}

async function openSceneModal(scene = null, idx = null) {
    const isEdit = scene !== null;
    const title = isEdit ? 'Edit Scene' : 'Add Scene';

    // Fetch project assets to populate asset selector
    let assets = [];
    if (projectId) {
        try {
            const assetData = await api(`/projects/${projectId}/assets`);
            assets = Array.isArray(assetData) ? assetData : (assetData.assets || assetData.items || []);
        } catch {
            assets = [];
        }
    }

    const assetOptions = [
        '<option value="">— None (Procedural / Generated) —</option>',
        ...assets.map(a => `<option value="${a.id}" ${scene?.asset_id === a.id ? 'selected' : ''}>${escapeHtml(a.original_filename || a.filename)} (${a.asset_type || 'asset'})</option>`)
    ].join('');

    showModal(title, `
        <div class="form-group">
            <label class="form-label">Narration / Text</label>
            <textarea id="sm-narration" class="form-textarea" rows="4" placeholder="Scene narration text...">${escapeHtml(scene?.narration_text || scene?.narration || scene?.text || '')}</textarea>
        </div>
        <div class="form-group">
            <label class="form-label">Visual Description</label>
            <textarea id="sm-visual" class="form-textarea" rows="3" placeholder="Describe what should be shown visually...">${escapeHtml(scene?.visual_description || scene?.description || '')}</textarea>
        </div>
        <div class="form-group">
            <label class="form-label">Attached Visual Asset</label>
            <select id="sm-asset" class="form-select">
                ${assetOptions}
            </select>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label class="form-label">Duration (seconds)</label>
                <input type="number" id="sm-duration" class="form-input" value="${scene?.duration_seconds || scene?.duration || 5}" min="1" max="60" step="0.5">
            </div>
            <div class="form-group">
                <label class="form-label">Scene Number</label>
                <input type="number" id="sm-number" class="form-input" value="${scene?.scene_number || scenes.length + 1}" min="1">
            </div>
        </div>
    `, `
        <button class="btn btn-secondary" onclick="window.__hideModal()">Cancel</button>
        <button class="btn btn-primary" id="sm-save">${isEdit ? 'Update' : 'Add'} Scene</button>
    `);

    // Expose hideModal globally for inline onclick
    window.__hideModal = hideModal;

    setTimeout(() => {
        document.getElementById('sm-save').addEventListener('click', async () => {
            const payload = {
                narration_text: document.getElementById('sm-narration').value,
                visual_description: document.getElementById('sm-visual').value,
                duration_seconds: parseFloat(document.getElementById('sm-duration').value) || 5,
                scene_number: parseInt(document.getElementById('sm-number').value) || scenes.length + 1,
                asset_id: document.getElementById('sm-asset').value || null,
            };

            try {
                if (isEdit) {
                    await api(`/projects/${projectId}/scenes/${scene.id || scene.scene_id}`, {
                        method: 'PUT', body: payload
                    });
                } else {
                    let scriptId = scene?.script_id;
                    if (!scriptId && scenes.length > 0) {
                        scriptId = scenes[0].script_id;
                    }
                    await api(`/projects/${projectId}/scenes`, {
                        method: 'POST', body: { ...payload, script_id: scriptId }
                    });
                }
                hideModal();
                showToast('success', isEdit ? 'Scene Updated' : 'Scene Added');
                await loadScenes(projectId);
            } catch (err) {
                showToast('error', 'Save Failed', err.message);
            }
        });
    }, 0);
}

function checkConsistency() {
    const card = document.getElementById('sb-consistency');
    if (scenes.length < 2) { card.style.display = 'none'; return; }

    card.style.display = '';
    const styles = scenes.map(s => s.visual_style || s.style || '').filter(Boolean);
    const unique = new Set(styles);

    if (unique.size <= 1) {
        document.getElementById('sb-consistency-icon').textContent = '✅';
        document.getElementById('sb-consistency-text').textContent = 'Visual style is consistent across all scenes';
    } else {
        document.getElementById('sb-consistency-icon').textContent = '⚠️';
        document.getElementById('sb-consistency-text').textContent = `Mixed visual styles detected (${unique.size} different styles)`;
    }
}
