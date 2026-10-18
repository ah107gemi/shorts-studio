// ============================================
// Captions & Subtitles Page
// ============================================
import { api, showToast, navigateTo, state, escapeHtml } from '../app.js';

let captionsData = [];
let currentProjectId = null;

export async function render() {
    return `
        <div class="page-header-row mb-3">
            <div>
                <h1>💬 Captions & Subtitles</h1>
                <p class="text-secondary">Generate, synchronize, customize styling, and export timed captions for YouTube Shorts</p>
            </div>
            <div class="btn-group">
                <button class="btn btn-secondary" id="captions-export-srt">📥 Export SRT</button>
                <button class="btn btn-primary" id="captions-generate-btn">✨ Auto-Generate Captions</button>
            </div>
        </div>

        <!-- Project Selector & Actions -->
        <div class="card mb-3">
            <div class="card-body flex items-center justify-between flex-wrap gap-2">
                <div class="flex items-center gap-2">
                    <label class="text-sm font-semibold" for="captions-project-select">Project:</label>
                    <select id="captions-project-select" class="form-control" style="min-width: 240px;"></select>
                </div>
                <div class="btn-group">
                    <button class="btn btn-ghost btn-sm" id="captions-add-segment-btn">➕ Add Segment</button>
                    <button class="btn btn-secondary btn-sm" id="captions-save-btn">💾 Save All Changes</button>
                </div>
            </div>
        </div>

        <div class="grid grid-2 gap-3 mb-3">
            <!-- Left Column: Caption Segments List -->
            <div class="card" style="display: flex; flex-direction: column; max-height: 680px;">
                <div class="card-header flex justify-between items-center">
                    <h3 class="card-title">Caption Segments (<span id="segments-count">0</span>)</h3>
                    <span class="text-xs text-muted">Editable timestamps & text</span>
                </div>
                <div class="card-body" id="captions-list-container" style="overflow-y: auto; flex: 1; padding: 12px; display: flex; flex-direction: column; gap: 8px;">
                    <div class="loading-overlay"><div class="spinner"></div></div>
                </div>
            </div>

            <!-- Right Column: Visual Preview & Styling Controls -->
            <div class="flex flex-col gap-3">
                <!-- Visual Preview Card -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Vertical Frame Overlay Preview</h3>
                        <span class="badge badge-info">Shorts Safe Area</span>
                    </div>
                    <div class="card-body flex justify-center items-center p-3" style="background: #0d0d12;">
                        <div id="captions-mock-screen" style="width: 200px; aspect-ratio: 9/16; background: #1a1a24; border: 2px dashed #404050; border-radius: 12px; position: relative; overflow: hidden; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; padding-bottom: 30px;">
                            <div class="text-xs text-muted" style="position: absolute; top: 12px; font-size: 0.65rem;">9:16 Safe Frame</div>
                            <!-- Mock caption text -->
                            <div id="mock-caption-box" style="padding: 6px 12px; background: rgba(0,0,0,0.75); border-radius: 6px; color: #fff; font-size: 0.85rem; font-weight: 700; text-align: center; max-width: 85%; line-height: 1.2;">
                                Sample Animated Captions
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Styling Settings Card -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Caption Styling</h3>
                    </div>
                    <div class="card-body">
                        <div class="grid grid-2 gap-2 mb-2">
                            <div class="form-group">
                                <label class="form-label text-xs">Font Family</label>
                                <select id="caption-style-font" class="form-control text-sm">
                                    <option value="Arial Black">Arial Black (Bold Impact)</option>
                                    <option value="Montserrat">Montserrat</option>
                                    <option value="Impact">Impact</option>
                                    <option value="Roboto">Roboto</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label text-xs">Font Size (pt)</label>
                                <input id="caption-style-size" type="number" class="form-control text-sm" value="48" min="20" max="96">
                            </div>
                        </div>

                        <div class="grid grid-2 gap-2 mb-2">
                            <div class="form-group">
                                <label class="form-label text-xs">Text Color</label>
                                <input id="caption-style-color" type="color" class="form-control text-sm" value="#FFFFFF" style="height: 38px;">
                            </div>
                            <div class="form-group">
                                <label class="form-label text-xs">Highlight Keyword Color</label>
                                <input id="caption-style-highlight" type="color" class="form-control text-sm" value="#FFE600" style="height: 38px;">
                            </div>
                        </div>

                        <div class="form-group mb-2">
                            <label class="form-label text-xs">Screen Position</label>
                            <select id="caption-style-position" class="form-control text-sm">
                                <option value="bottom">Lower Third (Shorts Standard)</option>
                                <option value="middle">Center / Middle</option>
                                <option value="top">Top</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

export async function init() {
    const select = document.getElementById('captions-project-select');
    await populateProjectsDropdown(select);

    select.addEventListener('change', async (e) => {
        currentProjectId = e.target.value;
        state.set('currentProject', currentProjectId);
        await loadCaptions(currentProjectId);
    });

    document.getElementById('captions-generate-btn').addEventListener('click', triggerAutoGenerate);
    document.getElementById('captions-export-srt').addEventListener('click', triggerExportSrt);
    document.getElementById('captions-save-btn').addEventListener('click', saveCaptions);
    document.getElementById('captions-add-segment-btn').addEventListener('click', addSegment);

    // Style inputs preview updates
    ['caption-style-font', 'caption-style-color', 'caption-style-position'].forEach(id => {
        document.getElementById(id)?.addEventListener('input', updateMockStyle);
    });

    if (state.currentProject) {
        select.value = state.currentProject;
        currentProjectId = state.currentProject;
        await loadCaptions(currentProjectId);
    } else if (select.options.length > 0) {
        select.selectedIndex = 0;
        currentProjectId = select.value;
        state.set('currentProject', currentProjectId);
        await loadCaptions(currentProjectId);
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

async function loadCaptions(projectId) {
    const container = document.getElementById('captions-list-container');
    if (!projectId) return;
    try {
        container.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
        const res = await api(`/projects/${projectId}/captions`);
        captionsData = res.segments || [];
        document.getElementById('segments-count').textContent = captionsData.length;
        renderCaptionsList();
    } catch (err) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>Could not load captions: ${escapeHtml(err.message)}</p>
                <button class="btn btn-secondary btn-sm" id="retry-captions">Auto-Generate from Scenes</button>
            </div>
        `;
        document.getElementById('retry-captions')?.addEventListener('click', triggerAutoGenerate);
    }
}

function renderCaptionsList() {
    const container = document.getElementById('captions-list-container');
    if (!captionsData || captionsData.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="padding: 30px;">
                <div class="empty-state-icon">💬</div>
                <h4>No Captions Generated</h4>
                <p class="text-sm">Generate timed subtitle phrases automatically from your approved script narration.</p>
                <button class="btn btn-primary btn-sm" onclick="document.getElementById('captions-generate-btn').click()">✨ Generate Now</button>
            </div>
        `;
        return;
    }

    container.innerHTML = captionsData.map((seg, idx) => `
        <div class="card p-2 segment-card" data-idx="${idx}" style="background: #191924; border: 1px solid var(--border-color); border-radius: 6px;">
            <div class="flex items-center justify-between gap-2 mb-1">
                <span class="text-xs font-semibold text-secondary">#${idx + 1}</span>
                <div class="flex items-center gap-1">
                    <input type="number" step="0.1" class="form-control text-xs seg-start" value="${seg.start_time}" style="width: 70px; padding: 2px 4px;">
                    <span class="text-xs text-muted">→</span>
                    <input type="number" step="0.1" class="form-control text-xs seg-end" value="${seg.end_time}" style="width: 70px; padding: 2px 4px;">
                    <span class="text-xs text-muted">s</span>
                </div>
                <button class="btn btn-ghost btn-sm text-danger seg-del" style="padding: 2px 6px;">✕</button>
            </div>
            <textarea class="form-control text-sm seg-text" rows="2" style="font-size: 0.85rem; padding: 4px 6px;">${escapeHtml(seg.text)}</textarea>
        </div>
    `).join('');

    // Attach listeners
    container.querySelectorAll('.seg-del').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const card = e.target.closest('.segment-card');
            const idx = parseInt(card.dataset.idx, 10);
            captionsData.splice(idx, 10);
            renderCaptionsList();
        });
    });

    container.querySelectorAll('.seg-text').forEach(t => {
        t.addEventListener('input', (e) => {
            const card = e.target.closest('.segment-card');
            const idx = parseInt(card.dataset.idx, 10);
            captionsData[idx].text = e.target.value;
            document.getElementById('mock-caption-box').textContent = e.target.value || 'Sample Caption';
        });
    });

    container.querySelectorAll('.seg-start').forEach(i => {
        i.addEventListener('change', (e) => {
            const card = e.target.closest('.segment-card');
            const idx = parseInt(card.dataset.idx, 10);
            captionsData[idx].start_time = parseFloat(e.target.value) || 0;
        });
    });

    container.querySelectorAll('.seg-end').forEach(i => {
        i.addEventListener('change', (e) => {
            const card = e.target.closest('.segment-card');
            const idx = parseInt(card.dataset.idx, 10);
            captionsData[idx].end_time = parseFloat(e.target.value) || 0;
        });
    });
}

function addSegment() {
    const lastEnd = captionsData.length > 0 ? captionsData[captionsData.length - 1].end_time : 0;
    captionsData.push({
        start_time: Math.round(lastEnd * 10) / 10,
        end_time: Math.round((lastEnd + 3.0) * 10) / 10,
        text: 'New caption text',
    });
    document.getElementById('segments-count').textContent = captionsData.length;
    renderCaptionsList();
}

async function saveCaptions() {
    if (!currentProjectId) {
        showToast('warning', 'Select a project first');
        return;
    }
    try {
        await api(`/projects/${currentProjectId}/captions`, {
            method: 'PUT',
            body: { segments: captionsData }
        });
        showToast('success', 'Captions saved successfully');
    } catch (err) {
        showToast('error', 'Save failed', err.message);
    }
}

async function triggerAutoGenerate() {
    if (!currentProjectId) {
        showToast('warning', 'Select a project first');
        return;
    }
    try {
        showToast('info', 'Generating captions from project scenes...');
        const res = await api(`/projects/${currentProjectId}/captions/generate`, {
            method: 'POST',
            body: { words_per_minute: 150.0 }
        });
        captionsData = res.segments || [];
        document.getElementById('segments-count').textContent = captionsData.length;
        renderCaptionsList();
        showToast('success', `Generated ${captionsData.length} caption phrases`);
    } catch (err) {
        showToast('error', 'Caption generation failed', err.message);
    }
}

async function triggerExportSrt() {
    if (!currentProjectId) {
        showToast('warning', 'Select a project first');
        return;
    }
    try {
        const url = `/api/v1/projects/${currentProjectId}/captions/export-srt`;
        window.open(url, '_blank');
        showToast('success', 'SRT Subtitles downloaded');
    } catch (err) {
        showToast('error', 'Export failed', err.message);
    }
}

function updateMockStyle() {
    const box = document.getElementById('mock-caption-box');
    const color = document.getElementById('caption-style-color')?.value || '#FFFFFF';
    const font = document.getElementById('caption-style-font')?.value || 'Arial';
    box.style.color = color;
    box.style.fontFamily = font;
}
