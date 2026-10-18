// ============================================
// Voiceover Studio Page
// ============================================
import { api, showToast, navigateTo, state, escapeHtml, formatDuration, truncate } from '../app.js';

let scenes = [];
let projectId = null;

export async function render() {
    projectId = state.currentProject;
    return `
        <div class="page-header">
            <div class="page-header-row">
                <div>
                    <h1>🎙️ Voiceover Studio</h1>
                    <p>Generate or upload audio narration for each scene</p>
                </div>
                <div class="btn-group">
                    <select id="vo-project-select" class="form-select" style="min-width:200px;"></select>
                </div>
            </div>
        </div>

        <!-- Provider Status -->
        <div class="card mb-2" style="padding: 10px 16px;" id="vo-provider-status">
            <div class="flex items-center gap-2">
                <span class="status-dot offline" id="vo-provider-dot"></span>
                <span class="text-sm" id="vo-provider-text">Checking TTS provider...</span>
            </div>
        </div>

        <!-- Bulk Actions -->
        <div class="card mb-2" style="padding: 12px 16px;" id="vo-actions" style="display:none;">
            <div class="flex items-center justify-between flex-wrap gap-1">
                <div class="btn-group">
                    <button class="btn btn-primary" id="vo-generate-all">🤖 Generate All Voiceovers</button>
                    <button class="btn btn-secondary" id="vo-play-all">▶️ Play Full Narration</button>
                    <button class="btn btn-ghost" id="vo-import">📂 Import Pre-recorded</button>
                </div>
                <span class="text-sm text-muted" id="vo-summary">0 scenes • 0 with audio</span>
            </div>
        </div>

        <div id="vo-scene-list">
            <div class="loading-overlay"><div class="spinner"></div><span>Loading scenes...</span></div>
        </div>

        <!-- Hidden file input for import -->
        <input type="file" id="vo-file-input" accept="audio/*" style="display:none;">
    `;
}

export async function init() {
    const projectSelect = document.getElementById('vo-project-select');

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
        }
    } catch (err) {
        showToast('error', 'Load Error', err.message);
    }

    projectSelect.addEventListener('change', async () => {
        projectId = projectSelect.value;
        state.set('currentProject', projectId);
        if (projectId) await loadScenes(projectId);
    });

    // Check TTS provider
    checkProvider();

    // Generate all
    document.getElementById('vo-generate-all').addEventListener('click', async () => {
        if (!projectId) return;
        try {
            await api(`/projects/${projectId}/voiceover/generate`, { method: 'POST' });
            showToast('success', 'Voiceover Generation Started', 'Audio is being generated for all scenes.');
            setTimeout(() => loadScenes(projectId), 3000);
        } catch (err) {
            showToast('error', 'Generation Failed', err.message);
        }
    });

    // Play all in sequence
    document.getElementById('vo-play-all').addEventListener('click', () => {
        const players = document.querySelectorAll('.vo-audio-player');
        let idx = 0;
        function playNext() {
            if (idx >= players.length) return;
            const player = players[idx];
            player.play();
            player.onended = () => { idx++; playNext(); };
        }
        playNext();
    });

    // Import pre-recorded
    document.getElementById('vo-import').addEventListener('click', () => {
        document.getElementById('vo-file-input').click();
    });

    document.getElementById('vo-file-input').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file || !projectId) return;
        const formData = new FormData();
        formData.append('file', file);
        try {
            await api(`/projects/${projectId}/voiceover/import`, {
                method: 'POST', body: formData
            });
            showToast('success', 'Audio Imported');
            await loadScenes(projectId);
        } catch (err) {
            showToast('error', 'Import Failed', err.message);
        }
        e.target.value = '';
    });
}

async function checkProvider() {
    try {
        const health = await api('/health');
        const ttsAvailable = health.providers?.tts?.configured ||
                             health.providers?.elevenlabs?.configured ||
                             health.providers?.['text-to-speech']?.configured ||
                             false;
        document.getElementById('vo-provider-dot').className = `status-dot ${ttsAvailable ? 'online' : 'warning'}`;
        document.getElementById('vo-provider-text').textContent = ttsAvailable
            ? 'TTS Provider: Connected'
            : 'TTS Provider: Not configured — you can still upload audio files';
    } catch {
        document.getElementById('vo-provider-dot').className = 'status-dot offline';
        document.getElementById('vo-provider-text').textContent = 'Cannot check provider status';
    }
}

async function loadScenes(pid) {
    const container = document.getElementById('vo-scene-list');
    try {
        const data = await api(`/projects/${pid}/scenes`);
        scenes = Array.isArray(data) ? data : (data.scenes || data.items || []);
        renderScenes();
    } catch (err) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🎙️</div>
                <h3>No scenes found</h3>
                <p>Create a storyboard first, then come back to add voiceovers.</p>
                <button class="btn btn-primary" onclick="window.__navigateTo('storyboard')">Go to Storyboard</button>
            </div>
        `;
    }
}

function renderScenes() {
    const container = document.getElementById('vo-scene-list');
    const withAudio = scenes.filter(s => s.audio_url || s.voiceover_url).length;
    document.getElementById('vo-summary').textContent = `${scenes.length} scenes • ${withAudio} with audio`;
    document.getElementById('vo-actions').style.display = scenes.length ? '' : 'none';

    if (scenes.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🎙️</div>
                <h3>No scenes</h3>
                <p>Add scenes in the storyboard first.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = scenes.map((s, i) => {
        const audioUrl = s.audio_url || s.voiceover_url;
        const hasAudio = !!audioUrl;
        return `
        <div class="card mb-2" style="padding: 16px;">
            <div class="flex items-center justify-between mb-1">
                <div class="flex items-center gap-2">
                    <span class="scene-card-number">${s.scene_number || i + 1}</span>
                    <span class="badge ${hasAudio ? 'badge-completed' : 'badge-draft'}">${hasAudio ? 'Audio Ready' : 'No Audio'}</span>
                </div>
                <span class="text-xs text-muted">${formatDuration(s.duration)}</span>
            </div>
            <p class="text-sm mb-2" style="color: var(--text-secondary);">${escapeHtml(s.narration || s.text || 'No narration text')}</p>
            ${hasAudio ? `
                <div class="audio-player mb-1">
                    <audio controls class="vo-audio-player" src="${audioUrl}" preload="metadata" style="width:100%; height:32px;"></audio>
                </div>
            ` : ''}
            <div class="btn-group">
                <button class="btn btn-secondary btn-sm vo-generate-one" data-id="${s.id || s.scene_id}" data-idx="${i}">
                    ${hasAudio ? '🔄 Regenerate' : '🤖 Generate'}
                </button>
                <button class="btn btn-ghost btn-sm vo-upload-one" data-id="${s.id || s.scene_id}" data-idx="${i}">📁 Upload</button>
            </div>
        </div>
        `;
    }).join('');

    // Per-scene generate
    container.querySelectorAll('.vo-generate-one').forEach(btn => {
        btn.addEventListener('click', async () => {
            const sceneId = btn.dataset.id;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Generating...';
            try {
                await api(`/projects/${projectId}/scenes/${sceneId}/voiceover/generate`, { method: 'POST' });
                showToast('success', 'Voiceover Generated', `Scene ${parseInt(btn.dataset.idx) + 1} audio ready.`);
                await loadScenes(projectId);
            } catch (err) {
                showToast('error', 'Generation Failed', err.message);
                btn.disabled = false;
                btn.textContent = '🤖 Generate';
            }
        });
    });

    // Per-scene upload
    container.querySelectorAll('.vo-upload-one').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'audio/*';
            input.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                const formData = new FormData();
                formData.append('file', file);
                try {
                    await api(`/projects/${projectId}/scenes/${btn.dataset.id}/voiceover`, {
                        method: 'POST', body: formData
                    });
                    showToast('success', 'Audio Uploaded');
                    await loadScenes(projectId);
                } catch (err) {
                    showToast('error', 'Upload Failed', err.message);
                }
            };
            input.click();
        });
    });
}
