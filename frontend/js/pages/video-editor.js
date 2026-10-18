// ============================================
// Video Editor & Timeline Page
// ============================================
import { api, showToast, navigateTo, formatDuration, state, escapeHtml } from '../app.js';

let scenes = [];
let project = null;

export async function render() {
    return `
        <div class="page-header-row mb-3">
            <div>
                <h1>🎬 Video Editor & Timeline</h1>
                <p class="text-secondary">Preview scenes, arrange timeline sequence, and configure render settings</p>
            </div>
            <div class="btn-group">
                <button class="btn btn-secondary" id="editor-preview-btn">🔍 Generate Preview</button>
                <button class="btn btn-primary" id="editor-render-btn">🚀 Start Full Render</button>
            </div>
        </div>

        <!-- Project Selector & Stats Bar -->
        <div class="card mb-3">
            <div class="card-body flex items-center justify-between flex-wrap gap-2">
                <div class="flex items-center gap-2">
                    <label class="text-sm font-semibold" for="editor-project-select">Project:</label>
                    <select id="editor-project-select" class="form-control" style="min-width: 240px;"></select>
                </div>
                <div class="flex items-center gap-3 text-sm text-secondary" id="editor-stats">
                    <span>Duration: <strong id="editor-total-duration">0s</strong></span>
                    <span>•</span>
                    <span>Scenes: <strong id="editor-scene-count">0</strong></span>
                    <span>•</span>
                    <span>Resolution: <strong id="editor-resolution">1080×1920 (9:16)</strong></span>
                    <span>•</span>
                    <span>FPS: <strong id="editor-fps">30</strong></span>
                </div>
            </div>
        </div>

        <!-- Main Workspace: Preview Player + Scene Details -->
        <div class="grid grid-2 mb-3" style="gap: 20px;">
            <!-- Video Player Preview -->
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Monitor Preview</h3>
                    <span class="badge badge-info" id="monitor-status-badge">Standby</span>
                </div>
                <div class="card-body flex flex-col items-center justify-center" style="min-height: 420px; background: #0a0a0f; border-radius: var(--radius-md);">
                    <div id="player-container" style="width: 100%; max-width: 260px; aspect-ratio: 9/16; background: #121218; border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center; position: relative;">
                        <video id="preview-video" controls style="width: 100%; height: 100%; object-fit: contain; display: none;"></video>
                        <div id="player-placeholder" class="text-center p-3">
                            <div style="font-size: 3rem; margin-bottom: 8px;">📱</div>
                            <p class="text-sm text-secondary">Vertical 9:16 Frame</p>
                            <p class="text-xs text-muted" id="player-msg">Generate preview or full render to playback</p>
                        </div>
                    </div>
                </div>
                <div class="card-footer flex justify-between items-center">
                    <span class="text-xs text-muted" id="render-status-text">No active render job</span>
                    <button class="btn btn-ghost btn-sm" id="view-render-queue-btn">Open Queue →</button>
                </div>
            </div>

            <!-- Scene Timeline Properties -->
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Scene Inspector</h3>
                    <span class="text-xs text-muted" id="selected-scene-label">Select a scene below</span>
                </div>
                <div class="card-body" id="scene-inspector-body">
                    <div class="empty-state" style="padding: 40px 20px;">
                        <div class="empty-state-icon">🎞️</div>
                        <h4>No Scene Selected</h4>
                        <p class="text-sm">Click on any scene in the timeline below to inspect and customize transitions, narration, and timings.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Visual Multi-Track Timeline -->
        <div class="card mb-3">
            <div class="card-header">
                <div class="flex items-center gap-2">
                    <span style="font-size: 1.2rem;">⏱️</span>
                    <h3 class="card-title">Visual Sequence Timeline</h3>
                </div>
                <div class="flex items-center gap-2">
                    <button class="btn btn-ghost btn-sm" id="editor-goto-storyboard">Edit in Storyboard ↗</button>
                </div>
            </div>
            <div class="card-body" style="overflow-x: auto;">
                <div class="timeline-container" id="timeline-tracks" style="min-width: 600px; display: flex; flex-direction: column; gap: 12px; padding: 10px 0;">
                    <!-- Track 1: Visual Scenes -->
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 110px; font-weight: 600; font-size: 0.85rem; color: var(--text-secondary); text-transform: uppercase;">
                            Visuals
                        </div>
                        <div id="timeline-scene-track" style="flex: 1; display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px;">
                            <!-- Scene blocks rendered dynamically -->
                        </div>
                    </div>

                    <!-- Track 2: Voiceover / Narration -->
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 110px; font-weight: 600; font-size: 0.85rem; color: var(--text-secondary); text-transform: uppercase;">
                            Voiceover
                        </div>
                        <div id="timeline-audio-track" style="flex: 1; display: flex; gap: 8px; overflow-x: auto;">
                            <!-- Audio blocks rendered dynamically -->
                        </div>
                    </div>

                    <!-- Track 3: Captions Overlay -->
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 110px; font-weight: 600; font-size: 0.85rem; color: var(--text-secondary); text-transform: uppercase;">
                            Captions
                        </div>
                        <div id="timeline-caption-track" style="flex: 1; display: flex; gap: 8px; overflow-x: auto;">
                            <!-- Caption blocks rendered dynamically -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

export async function init() {
    const select = document.getElementById('editor-project-select');
    await populateProjectsDropdown(select);

    select.addEventListener('change', async (e) => {
        state.set('currentProject', e.target.value);
        await loadProjectData(e.target.value);
    });

    document.getElementById('editor-preview-btn').addEventListener('click', triggerPreview);
    document.getElementById('editor-render-btn').addEventListener('click', triggerRender);
    document.getElementById('view-render-queue-btn').addEventListener('click', () => navigateTo('render-queue'));
    document.getElementById('editor-goto-storyboard').addEventListener('click', () => navigateTo('storyboard'));

    if (state.currentProject) {
        select.value = state.currentProject;
        await loadProjectData(state.currentProject);
    } else if (select.options.length > 0) {
        select.selectedIndex = 0;
        state.set('currentProject', select.value);
        await loadProjectData(select.value);
    }
}

async function populateProjectsDropdown(select) {
    try {
        const data = await api('/projects');
        const list = Array.isArray(data) ? data : (data.items || []);
        if (list.length === 0) {
            select.innerHTML = '<option value="">No projects available</option>';
            return;
        }
        select.innerHTML = list.map(p => `
            <option value="${p.id}">${escapeHtml(p.name || p.topic || 'Untitled')}</option>
        `).join('');
    } catch (err) {
        select.innerHTML = '<option value="">Failed to load projects</option>';
    }
}

async function loadProjectData(projectId) {
    if (!projectId) return;
    try {
        project = await api(`/projects/${projectId}`);
        scenes = await api(`/projects/${projectId}/scenes`);

        // Update stats
        const totalSec = scenes.reduce((acc, s) => acc + (s.duration_seconds || 5), 0);
        document.getElementById('editor-total-duration').textContent = formatDuration(totalSec);
        document.getElementById('editor-scene-count').textContent = scenes.length;
        document.getElementById('editor-resolution').textContent = `${project.resolution_w || 1080}×${project.resolution_h || 1920}`;
        document.getElementById('editor-fps').textContent = project.fps || 30;

        renderTimelineTracks(scenes);
        await checkExistingRenders(projectId);
    } catch (err) {
        showToast('error', 'Failed to load project details', err.message);
    }
}

function renderTimelineTracks(scenesList) {
    const visualTrack = document.getElementById('timeline-scene-track');
    const audioTrack = document.getElementById('timeline-audio-track');
    const captionTrack = document.getElementById('timeline-caption-track');

    if (!scenesList || scenesList.length === 0) {
        visualTrack.innerHTML = '<span class="text-xs text-muted p-2">No scenes in this project. Use Storyboard to add scenes.</span>';
        audioTrack.innerHTML = '<span class="text-xs text-muted p-2">No audio tracks</span>';
        captionTrack.innerHTML = '<span class="text-xs text-muted p-2">No captions</span>';
        return;
    }

    visualTrack.innerHTML = scenesList.map((sc, idx) => {
        const dur = sc.duration_seconds || 5;
        const width = Math.max(100, Math.min(260, Math.round(dur * 24)));
        return `
            <div class="timeline-block scene-block" data-idx="${idx}" style="min-width: ${width}px; background: #20202d; border: 1px solid var(--border-color); border-radius: 6px; padding: 8px; cursor: pointer; transition: all 0.2s;">
                <div class="flex justify-between items-center text-xs font-semibold mb-1">
                    <span>#${sc.scene_number} Scene</span>
                    <span class="text-muted">${dur.toFixed(1)}s</span>
                </div>
                <div class="text-xs text-secondary truncate">${escapeHtml(sc.visual_description || 'Visual')}</div>
                ${sc.asset_filename ? `<div class="text-xs text-info truncate" style="font-size:0.7rem;margin-top:2px;">📁 ${escapeHtml(sc.asset_filename)}</div>` : ''}
                <div class="text-xs text-muted" style="margin-top: 4px;">Transition: ${escapeHtml(sc.transition || 'cut')}</div>
            </div>
        `;
    }).join('');

    audioTrack.innerHTML = scenesList.map((sc) => {
        const dur = sc.duration_seconds || 5;
        const width = Math.max(100, Math.min(260, Math.round(dur * 24)));
        const hasVo = !!sc.voiceover_asset_id;
        return `
            <div class="timeline-block audio-block" style="min-width: ${width}px; background: ${hasVo ? '#1e3a2f' : '#22232e'}; border: 1px solid ${hasVo ? '#2ecc71' : 'var(--border-color)'}; border-radius: 6px; padding: 6px 8px; font-size: 0.75rem;">
                <div class="flex items-center gap-1">
                    <span>${hasVo ? '🎙️' : '🔇'}</span>
                    <span class="truncate">${hasVo ? 'Recorded VO' : 'TTS / Silent'}</span>
                </div>
            </div>
        `;
    }).join('');

    captionTrack.innerHTML = scenesList.map((sc) => {
        const dur = sc.duration_seconds || 5;
        const width = Math.max(100, Math.min(260, Math.round(dur * 24)));
        return `
            <div class="timeline-block caption-block" style="min-width: ${width}px; background: #242238; border: 1px solid #7d5fff; border-radius: 6px; padding: 6px 8px; font-size: 0.75rem;">
                <div class="truncate text-secondary">💬 ${escapeHtml(sc.narration_text || 'No text')}</div>
            </div>
        `;
    }).join('');

    // Attach click listeners to inspect scene
    visualTrack.querySelectorAll('.scene-block').forEach(el => {
        el.addEventListener('click', () => {
            visualTrack.querySelectorAll('.scene-block').forEach(b => b.style.borderColor = 'var(--border-color)');
            el.style.borderColor = 'var(--accent-color)';
            const idx = parseInt(el.dataset.idx, 10);
            inspectScene(scenesList[idx]);
        });
    });
}

async function inspectScene(scene) {
    if (!scene) return;
    document.getElementById('selected-scene-label').textContent = `Scene #${scene.scene_number}`;
    const inspector = document.getElementById('scene-inspector-body');

    // Fetch assets for project
    let assets = [];
    try {
        const assetData = await api(`/projects/${scene.project_id}/assets`);
        assets = Array.isArray(assetData) ? assetData : (assetData.assets || assetData.items || []);
    } catch {
        assets = [];
    }

    const assetOptions = [
        '<option value="">— None (Procedural / Generated) —</option>',
        ...assets.map(a => `<option value="${a.id}" ${scene.asset_id === a.id ? 'selected' : ''}>${escapeHtml(a.original_filename || a.filename)} (${a.asset_type || 'asset'})</option>`)
    ].join('');

    const hasVideo = scene.asset_url && (scene.asset_filename?.match(/\.(mp4|mov|webm|mkv)$/i) || scene.asset_url.includes('.mp4'));
    const assetPreviewHtml = scene.asset_url ? (
        hasVideo
            ? `<div class="mb-2" style="max-height:140px;overflow:hidden;border-radius:6px;border:1px solid var(--border-color);"><video src="${scene.asset_url}" controls muted style="width:100%;max-height:140px;object-fit:cover;"></video></div>`
            : `<div class="mb-2" style="max-height:140px;overflow:hidden;border-radius:6px;border:1px solid var(--border-color);"><img src="${scene.asset_url}" style="width:100%;max-height:140px;object-fit:cover;"></div>`
    ) : '';

    inspector.innerHTML = `
        ${assetPreviewHtml}
        <div class="form-group mb-2">
            <label class="form-label text-xs">Narration Text</label>
            <textarea id="inspect-narration" class="form-control text-sm" rows="3">${escapeHtml(scene.narration_text || '')}</textarea>
        </div>
        <div class="form-group mb-2">
            <label class="form-label text-xs">Visual Description</label>
            <input id="inspect-visual" type="text" class="form-control text-sm" value="${escapeHtml(scene.visual_description || '')}">
        </div>
        <div class="form-group mb-2">
            <label class="form-label text-xs">Assigned Visual Asset</label>
            <select id="inspect-asset" class="form-control text-sm">
                ${assetOptions}
            </select>
        </div>
        <div class="grid grid-2 gap-2 mb-3">
            <div class="form-group">
                <label class="form-label text-xs">Duration (seconds)</label>
                <input id="inspect-duration" type="number" step="0.5" min="1" max="60" class="form-control text-sm" value="${scene.duration_seconds || 5}">
            </div>
            <div class="form-group">
                <label class="form-label text-xs">Transition</label>
                <select id="inspect-transition" class="form-control text-sm">
                    <option value="crossfade" ${scene.transition === 'crossfade' ? 'selected' : ''}>Crossfade</option>
                    <option value="fade" ${scene.transition === 'fade' ? 'selected' : ''}>Fade to Black</option>
                    <option value="wipeleft" ${scene.transition === 'wipeleft' ? 'selected' : ''}>Wipe Left</option>
                    <option value="cut" ${scene.transition === 'cut' ? 'selected' : ''}>Hard Cut</option>
                </select>
            </div>
        </div>
        <button class="btn btn-primary btn-sm w-full" id="save-scene-inspect-btn">Save Scene Changes</button>
    `;

    document.getElementById('save-scene-inspect-btn').addEventListener('click', async () => {
        try {
            await api(`/projects/${scene.project_id}/scenes/${scene.id}`, {
                method: 'PUT',
                body: {
                    narration_text: document.getElementById('inspect-narration').value,
                    visual_description: document.getElementById('inspect-visual').value,
                    duration_seconds: parseFloat(document.getElementById('inspect-duration').value) || 5,
                    transition: document.getElementById('inspect-transition').value,
                    asset_id: document.getElementById('inspect-asset').value || null,
                }
            });
            showToast('success', 'Scene updated');
            await loadProjectData(scene.project_id);
        } catch (err) {
            showToast('error', 'Save failed', err.message);
        }
    });
}

async function checkExistingRenders(projectId) {
    try {
        const status = await api(`/projects/${projectId}/render/status`);
        const badge = document.getElementById('monitor-status-badge');
        const statusText = document.getElementById('render-status-text');
        const video = document.getElementById('preview-video');
        const placeholder = document.getElementById('player-placeholder');

        if (status && status.status === 'completed' && status.output_path) {
            badge.className = 'badge badge-success';
            badge.textContent = 'Render Ready';
            statusText.textContent = `Completed render available`;
            video.src = `/api/v1/projects/${projectId}/assets/render-output/file?path=${encodeURIComponent(status.output_path)}`;
            video.style.display = 'block';
            placeholder.style.display = 'none';
        } else if (status && ['running', 'queued', 'pending'].includes(status.status)) {
            badge.className = 'badge badge-warning';
            badge.textContent = `${status.status.toUpperCase()} (${Math.round(status.progress || 0)}%)`;
            statusText.textContent = status.current_stage || 'Processing video render...';
        } else {
            badge.className = 'badge badge-info';
            badge.textContent = 'No Render';
            statusText.textContent = 'Ready to render';
            video.style.display = 'none';
            placeholder.style.display = 'flex';
        }
    } catch {
        // no renders yet
    }
}

async function triggerPreview() {
    if (!state.currentProject) {
        showToast('warning', 'Please select a project first');
        return;
    }
    try {
        showToast('info', 'Starting preview generation...', 'Low-resolution quick render');
        await api(`/projects/${state.currentProject}/render/preview`);
        showToast('success', 'Preview render queued');
        navigateTo('render-queue');
    } catch (err) {
        showToast('error', 'Preview failed', err.message);
    }
}

async function triggerRender() {
    if (!state.currentProject) {
        showToast('warning', 'Please select a project first');
        return;
    }
    if (scenes.length === 0) {
        showToast('warning', 'Project has no scenes', 'Add scenes before rendering');
        return;
    }
    try {
        showToast('info', 'Queuing full video render...');
        await api(`/projects/${state.currentProject}/render`, {
            method: 'POST',
            body: {
                quality: 'high',
                output_format: 'mp4',
            }
        });
        showToast('success', 'Full render job started');
        navigateTo('render-queue');
    } catch (err) {
        showToast('error', 'Render start failed', err.message);
    }
}
