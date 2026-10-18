// ============================================
// Export Center Page
// ============================================
import { api, showToast, navigateTo, formatDuration, formatFileSize, state, escapeHtml } from '../app.js';

let currentProjectId = null;
let projectData = null;
let renderStatus = null;

export async function render() {
    return `
        <div class="page-header-row mb-3">
            <div>
                <h1>📤 Export Center & Production Reports</h1>
                <p class="text-secondary">Download finished vertical MP4 files, review stream codecs, and export multi-platform packages</p>
            </div>
            <div class="btn-group">
                <button class="btn btn-secondary" id="export-open-render-btn">🚀 Go to Render Queue</button>
            </div>
        </div>

        <!-- Project Selector -->
        <div class="card mb-3">
            <div class="card-body flex items-center justify-between flex-wrap gap-2">
                <div class="flex items-center gap-2">
                    <label class="text-sm font-semibold" for="export-project-select">Project:</label>
                    <select id="export-project-select" class="form-control" style="min-width: 240px;"></select>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-xs text-secondary">Export Preset:</span>
                    <span class="badge badge-primary">YouTube Shorts (1080×1920 • 30fps • H.264/AAC)</span>
                </div>
            </div>
        </div>

        <div class="grid grid-2 gap-3 mb-3">
            <!-- Left: Video Playback & Actions -->
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Completed Master Video</h3>
                    <span class="badge badge-success" id="export-ready-badge" style="display: none;">Ready for Export</span>
                </div>
                <div class="card-body flex flex-col items-center justify-center p-3" style="min-height: 420px; background: #0c0c11; border-radius: var(--radius-md);">
                    <div style="width: 100%; max-width: 250px; aspect-ratio: 9/16; background: #161620; border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center; position: relative;">
                        <video id="export-player-video" controls style="width: 100%; height: 100%; object-fit: contain; display: none;"></video>
                        <div id="export-player-placeholder" class="text-center p-3">
                            <div style="font-size: 3rem; margin-bottom: 8px;">🎬</div>
                            <p class="text-sm text-secondary">No Rendered Video Yet</p>
                            <p class="text-xs text-muted">Complete a render job to watch the final vertical video here.</p>
                            <button class="btn btn-primary btn-sm" style="margin-top: 12px;" onclick="window.__navigateTo('video-editor')">Render Video Now</button>
                        </div>
                    </div>
                </div>
                <div class="card-footer flex justify-between items-center" id="export-actions-bar" style="display: none;">
                    <button class="btn btn-primary btn-sm" id="download-video-btn">📥 Download MP4 Video</button>
                    <button class="btn btn-secondary btn-sm" id="download-srt-btn">💬 Download Subtitles (SRT)</button>
                </div>
            </div>

            <!-- Right: Production Report & Metadata -->
            <div class="flex flex-col gap-3">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Production Spec Report</h3>
                    </div>
                    <div class="card-body" id="export-report-body">
                        <div class="loading-overlay"><div class="spinner"></div></div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Platform Presets</h3>
                    </div>
                    <div class="card-body">
                        <div class="flex flex-col gap-2">
                            <div class="card p-2 flex justify-between items-center" style="background: #191924;">
                                <div>
                                    <strong class="text-sm">YouTube Shorts</strong>
                                    <div class="text-xs text-muted">9:16 vertical • up to 60s • 1080×1920 • Stereo AAC</div>
                                </div>
                                <span class="badge badge-success">Optimized</span>
                            </div>
                            <div class="card p-2 flex justify-between items-center" style="background: #191924;">
                                <div>
                                    <strong class="text-sm">TikTok</strong>
                                    <div class="text-xs text-muted">9:16 vertical • 1080×1920 • Safe UI margins compatible</div>
                                </div>
                                <span class="badge badge-info">Compatible</span>
                            </div>
                            <div class="card p-2 flex justify-between items-center" style="background: #191924;">
                                <div>
                                    <strong class="text-sm">Instagram Reels</strong>
                                    <div class="text-xs text-muted">9:16 vertical • 1080×1920 • 30fps H.264 standard</div>
                                </div>
                                <span class="badge badge-info">Compatible</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

export async function init() {
    const select = document.getElementById('export-project-select');
    await populateProjectsDropdown(select);

    select.addEventListener('change', async (e) => {
        currentProjectId = e.target.value;
        state.set('currentProject', currentProjectId);
        await loadProjectExport(currentProjectId);
    });

    document.getElementById('export-open-render-btn').addEventListener('click', () => navigateTo('render-queue'));

    document.getElementById('download-srt-btn')?.addEventListener('click', () => {
        if (!currentProjectId) return;
        window.open(`/api/v1/projects/${currentProjectId}/captions/export-srt`, '_blank');
    });

    if (state.currentProject) {
        select.value = state.currentProject;
        currentProjectId = state.currentProject;
        await loadProjectExport(currentProjectId);
    } else if (select.options.length > 0) {
        select.selectedIndex = 0;
        currentProjectId = select.value;
        state.set('currentProject', currentProjectId);
        await loadProjectExport(currentProjectId);
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

async function loadProjectExport(projectId) {
    if (!projectId) return;
    const reportBody = document.getElementById('export-report-body');
    const player = document.getElementById('export-player-video');
    const placeholder = document.getElementById('export-player-placeholder');
    const readyBadge = document.getElementById('export-ready-badge');
    const actionsBar = document.getElementById('export-actions-bar');
    const downloadBtn = document.getElementById('download-video-btn');

    try {
        projectData = await api(`/projects/${projectId}`);
        renderStatus = await api(`/projects/${projectId}/render/status`);

        const hasOutput = renderStatus && renderStatus.status === 'completed' && renderStatus.output_path;

        if (hasOutput) {
            readyBadge.style.display = 'inline-block';
            actionsBar.style.display = 'flex';
            player.style.display = 'block';
            placeholder.style.display = 'none';

            const videoUrl = `/api/v1/projects/${projectId}/assets/render-output/file?path=${encodeURIComponent(renderStatus.output_path)}`;
            player.src = videoUrl;

            downloadBtn.onclick = () => {
                window.open(videoUrl, '_blank');
            };
        } else {
            readyBadge.style.display = 'none';
            actionsBar.style.display = 'none';
            player.style.display = 'none';
            placeholder.style.display = 'flex';
        }

        // Render report
        reportBody.innerHTML = `
            <div class="flex flex-col gap-2 text-sm">
                <div class="flex justify-between py-1 border-b">
                    <span class="text-secondary">Project Title</span>
                    <strong class="truncate" style="max-width: 250px;">${escapeHtml(projectData.name || projectData.topic || 'Untitled')}</strong>
                </div>
                <div class="flex justify-between py-1 border-b">
                    <span class="text-secondary">Target Platform</span>
                    <span>YouTube Shorts (9:16)</span>
                </div>
                <div class="flex justify-between py-1 border-b">
                    <span class="text-secondary">Resolution & FPS</span>
                    <span>${projectData.resolution_w || 1080} × ${projectData.resolution_h || 1920} @ ${projectData.fps || 30}fps</span>
                </div>
                <div class="flex justify-between py-1 border-b">
                    <span class="text-secondary">Target Duration</span>
                    <span>${formatDuration(projectData.target_duration_seconds || 60)}</span>
                </div>
                <div class="flex justify-between py-1 border-b">
                    <span class="text-secondary">Video Codec</span>
                    <span>H.264 / AVC (libx264, yuv420p)</span>
                </div>
                <div class="flex justify-between py-1 border-b">
                    <span class="text-secondary">Audio Codec</span>
                    <span>AAC Stereo (48,000 Hz, 192 kbps)</span>
                </div>
                <div class="flex justify-between py-1 border-b">
                    <span class="text-secondary">Render Status</span>
                    <span>${renderStatus.status?.toUpperCase() || 'NONE'}</span>
                </div>
                ${hasOutput ? `
                    <div class="flex justify-between py-1">
                        <span class="text-secondary">Output Path</span>
                        <span class="text-xs text-muted truncate" style="max-width: 240px;" title="${escapeHtml(renderStatus.output_path)}">${escapeHtml(renderStatus.output_path)}</span>
                    </div>
                ` : ''}
            </div>
        `;

    } catch (err) {
        reportBody.innerHTML = `<p class="text-danger text-sm">Error loading specs: ${escapeHtml(err.message)}</p>`;
    }
}
