// ============================================
// Assets Library Page
// ============================================
import { api, showToast, showModal, hideModal, confirmModal, formatFileSize, formatDate, state, escapeHtml } from '../app.js';

let assets = [];
let currentFilter = 'all';
let selectedProjectId = '';

export async function render() {
    return `
        <div class="page-header">
            <div class="page-header-row mb-2">
                <div>
                    <h1>🖼️ Visual & Media Assets Library</h1>
                    <p class="text-secondary">Upload, preview, organize, and assign media assets to video storyboard scenes</p>
                </div>
                <div class="flex items-center gap-2">
                    <label class="text-sm font-semibold" for="asset-project-select">Filter by Project:</label>
                    <select id="asset-project-select" class="form-control" style="min-width: 220px;"></select>
                </div>
            </div>
        </div>

        <!-- Upload Drop Zone -->
        <div class="drop-zone mb-3" id="asset-drop-zone">
            <div class="drop-zone-icon">📁</div>
            <div class="drop-zone-text">Drag & drop media files here, or <strong>click to browse</strong></div>
            <div class="drop-zone-hint">Supports MP4, MOV, WebM videos • PNG, JPG, WebP images • MP3, WAV audio</div>
            <input type="file" id="asset-file-input" multiple accept="image/*,video/*,audio/*">
        </div>

        <!-- Filters & Search Bar -->
        <div class="filter-bar mb-3">
            <div class="search-input">
                <input type="text" id="asset-search" placeholder="Search assets by filename...">
            </div>
            <div class="chip-group" id="asset-filters">
                <button class="chip active" data-filter="all">All Assets</button>
                <button class="chip" data-filter="image">🖼️ Images</button>
                <button class="chip" data-filter="video">🎬 Videos</button>
                <button class="chip" data-filter="audio">🎵 Audio</button>
            </div>
        </div>

        <!-- Asset Grid -->
        <div class="card-grid card-grid-sm" id="asset-grid">
            <div class="loading-overlay" style="grid-column:1/-1;"><div class="spinner"></div><span>Loading assets...</span></div>
        </div>

        <!-- Asset Detail Panel -->
        <div class="panel mt-3" id="asset-detail" style="display:none;">
            <div class="panel-header">
                <h3>Asset Details</h3>
                <button class="btn btn-ghost btn-sm" id="asset-detail-close">✕</button>
            </div>
            <div class="panel-body" id="asset-detail-body"></div>
        </div>
    `;
}

export async function init() {
    const dropZone = document.getElementById('asset-drop-zone');
    const fileInput = document.getElementById('asset-file-input');
    const projectSelect = document.getElementById('asset-project-select');

    await populateProjectsDropdown(projectSelect);

    projectSelect.addEventListener('change', async (e) => {
        selectedProjectId = e.target.value;
        if (selectedProjectId) {
            state.set('currentProject', selectedProjectId);
        }
        await loadAssets();
    });

    // Drop zone events
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
        e.target.value = '';
    });

    // Filters
    document.getElementById('asset-filters').addEventListener('click', (e) => {
        const chip = e.target.closest('.chip');
        if (!chip) return;
        document.querySelectorAll('#asset-filters .chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentFilter = chip.dataset.filter;
        renderAssets();
    });

    // Search
    document.getElementById('asset-search').addEventListener('input', renderAssets);

    // Detail close
    document.getElementById('asset-detail-close').addEventListener('click', () => {
        document.getElementById('asset-detail').style.display = 'none';
    });

    await loadAssets();
}

async function populateProjectsDropdown(select) {
    try {
        const data = await api('/projects');
        const list = Array.isArray(data) ? data : (data.items || []);
        let html = '<option value="">All Projects (Global)</option>';
        list.forEach(p => {
            const isSel = (state.currentProject && state.currentProject === p.id) ? 'selected' : '';
            html += `<option value="${p.id}" ${isSel}>${escapeHtml(p.name || p.topic || 'Untitled')}</option>`;
        });
        select.innerHTML = html;
        selectedProjectId = select.value || state.currentProject || '';
    } catch {
        select.innerHTML = '<option value="">All Projects</option>';
    }
}

async function handleFiles(files) {
    if (!files || files.length === 0) return;

    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        // Determine destination endpoint
        const targetProj = selectedProjectId || state.currentProject;
        if (targetProj) {
            formData.append('project_id', targetProj);
        }

        const uploadUrl = targetProj ? `/projects/${targetProj}/assets/upload` : '/assets/upload';

        try {
            showToast('info', 'Uploading...', file.name, 2000);
            await api(uploadUrl, { method: 'POST', body: formData });
            showToast('success', 'Uploaded', file.name);
        } catch (err) {
            showToast('error', 'Upload Failed', `${file.name}: ${err.message}`);
        }
    }
    await loadAssets();
}

async function loadAssets() {
    const container = document.getElementById('asset-grid');
    container.innerHTML = '<div class="loading-overlay" style="grid-column:1/-1;"><div class="spinner"></div><span>Loading assets...</span></div>';

    try {
        const targetProj = selectedProjectId || state.currentProject;
        const endpoint = targetProj ? `/projects/${targetProj}/assets` : '/assets';
        const data = await api(endpoint);
        assets = Array.isArray(data) ? data : (data.assets || data.items || []);
        renderAssets();
    } catch (err) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column:1/-1;">
                <div class="empty-state-icon">🖼️</div>
                <h3>Could not load assets</h3>
                <p>${escapeHtml(err.message)}</p>
            </div>
        `;
    }
}

function renderAssets() {
    const container = document.getElementById('asset-grid');
    const query = (document.getElementById('asset-search')?.value || '').toLowerCase();

    let filtered = assets;
    if (currentFilter !== 'all') {
        filtered = filtered.filter(a => {
            const t = (a.asset_type || a.type || a.mime_type || '').toLowerCase();
            return t.includes(currentFilter);
        });
    }
    if (query) {
        filtered = filtered.filter(a => {
            const name = (a.original_filename || a.filename || a.name || '').toLowerCase();
            return name.includes(query);
        });
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column:1/-1;">
                <div class="empty-state-icon">🖼️</div>
                <h3>${assets.length === 0 ? 'No assets uploaded yet' : 'No matching assets found'}</h3>
                <p>Drag and drop videos, photos, or voiceover audio above to add them to your studio library.</p>
            </div>
        `;
        return;
    }

    const typeIcon = (type) => {
        const t = (type || '').toLowerCase();
        if (t.includes('image')) return '🖼️';
        if (t.includes('video')) return '🎬';
        if (t.includes('audio') || t.includes('voiceover') || t.includes('music')) return '🎵';
        return '📄';
    };

    container.innerHTML = filtered.map(a => {
        const id = a.id || a.asset_id;
        const assetType = (a.asset_type || a.type || '').toLowerCase();
        const isImage = assetType.includes('image');
        const isVideo = assetType.includes('video');
        const isAudio = assetType.includes('audio') || assetType.includes('voiceover');
        const fileUrl = a.url || `/api/v1/assets/${id}/file`;
        const displayName = a.original_filename || a.filename || 'Untitled';
        const sizeFormatted = formatFileSize(a.file_size_bytes || a.size);

        return `
        <div class="card card-clickable asset-card" data-id="${id}">
            <div class="scene-card-thumbnail" style="aspect-ratio: 16/9; background: #13131c; border-radius: 6px; overflow: hidden; display: flex; align-items: center; justify-content: center; position: relative;">
                ${isImage ? `
                    <img src="${fileUrl}" alt="${escapeHtml(displayName)}" style="object-fit: contain; width: 100%; height: 100%;">
                ` : isVideo ? `
                    <video src="${fileUrl}" style="object-fit: cover; width: 100%; height: 100%; pointer-events: none;" preload="metadata"></video>
                    <span style="position: absolute; bottom: 6px; right: 6px; background: rgba(0,0,0,0.7); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">🎬 Video</span>
                ` : isAudio ? `
                    <span style="font-size: 2.2rem;">🎵</span>
                    <span style="position: absolute; bottom: 6px; right: 6px; background: rgba(0,0,0,0.7); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">Audio</span>
                ` : `
                    <span style="font-size: 2.2rem;">${typeIcon(assetType)}</span>
                `}
            </div>
            <div class="mt-2">
                <p class="text-sm font-semibold truncate" title="${escapeHtml(displayName)}">${escapeHtml(displayName)}</p>
                <div class="flex justify-between items-center text-xs text-muted mt-1">
                    <span>${sizeFormatted}</span>
                    <span class="badge badge-info" style="font-size: 0.7rem; padding: 1px 6px;">${assetType.toUpperCase()}</span>
                </div>
            </div>
            <div class="flex justify-between items-center gap-1 mt-2 pt-2 border-t">
                <button class="btn btn-secondary btn-sm asset-assign" data-id="${id}" style="padding: 3px 8px; font-size: 0.75rem;" title="Assign to scene in Storyboard">🎞️ Assign</button>
                <button class="btn btn-ghost btn-sm text-danger asset-delete" data-id="${id}" style="padding: 3px 8px; font-size: 0.75rem;" title="Delete Asset">🗑️</button>
            </div>
        </div>
        `;
    }).join('');

    // Click to show detail
    container.querySelectorAll('.asset-card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (e.target.closest('button')) return;
            const asset = assets.find(a => (a.id || a.asset_id) === card.dataset.id);
            if (asset) showAssetDetail(asset);
        });
    });

    // Delete asset
    container.querySelectorAll('.asset-delete').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const confirmed = await confirmModal('Delete Asset', 'Move this asset to trash?');
            if (!confirmed) return;
            try {
                await api(`/assets/${btn.dataset.id}`, { method: 'DELETE' });
                showToast('success', 'Asset Deleted');
                await loadAssets();
            } catch (err) {
                showToast('error', 'Delete Failed', err.message);
            }
        });
    });

    // Assign to scene
    container.querySelectorAll('.asset-assign').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const targetProj = selectedProjectId || state.currentProject;
            if (!targetProj) {
                showToast('warning', 'No Project Selected', 'Please select a project from the top dropdown first.');
                return;
            }
            try {
                const scns = await api(`/projects/${targetProj}/scenes`);
                const sceneList = Array.isArray(scns) ? scns : [];
                if (sceneList.length === 0) {
                    showToast('info', 'No Scenes Found', 'Create scenes in the Storyboard first to assign visuals.');
                    return;
                }
                const sceneNames = sceneList.map((s, i) => `${s.scene_number || i + 1}: ${(s.narration_text || s.visual_description || 'Scene').substring(0, 35)}`);
                const choice = prompt(`Assign this asset to which scene?\n\n${sceneNames.map((n, i) => `[${i + 1}] ${n}`).join('\n')}\n\nEnter scene number (1-${sceneList.length}):`);
                if (!choice) return;
                const idx = parseInt(choice, 10) - 1;
                if (idx < 0 || idx >= sceneList.length) {
                    showToast('error', 'Invalid Choice', 'Scene number out of range');
                    return;
                }

                await api(`/projects/${targetProj}/scenes/${sceneList[idx].id}/asset`, {
                    method: 'PUT',
                    body: { asset_id: btn.dataset.id, role: 'visual' }
                });
                showToast('success', 'Asset Assigned', `Linked to Scene #${sceneList[idx].scene_number}`);
            } catch (err) {
                showToast('error', 'Assignment Failed', err.message);
            }
        });
    });
}

function showAssetDetail(asset) {
    const panel = document.getElementById('asset-detail');
    const body = document.getElementById('asset-detail-body');
    panel.style.display = '';

    const assetType = (asset.asset_type || asset.type || '').toLowerCase();
    const isImage = assetType.includes('image');
    const isVideo = assetType.includes('video');
    const isAudio = assetType.includes('audio') || assetType.includes('voiceover');
    const fileUrl = asset.url || `/api/v1/assets/${asset.id}/file`;
    const displayName = asset.original_filename || asset.filename || 'Untitled';

    body.innerHTML = `
        <div class="flex gap-3" style="flex-wrap: wrap;">
            <div style="flex: 0 0 260px; max-width: 100%; background: #0e0e14; border-radius: 8px; padding: 8px; border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: center;">
                ${isImage ? `<img src="${fileUrl}" alt="" style="width: 100%; max-height: 240px; object-fit: contain; border-radius: 4px;">` : ''}
                ${isVideo ? `<video src="${fileUrl}" controls style="width: 100%; max-height: 240px; border-radius: 4px;"></video>` : ''}
                ${isAudio ? `<audio src="${fileUrl}" controls style="width: 100%; margin: 20px 0;"></audio>` : ''}
            </div>
            <div style="flex: 1; min-width: 220px;">
                <table class="table" style="width: 100%; font-size: 0.85rem;">
                    <tr><td class="text-secondary" style="width: 110px;">Filename:</td><td><strong>${escapeHtml(displayName)}</strong></td></tr>
                    <tr><td class="text-secondary">Type:</td><td><span class="badge badge-info">${escapeHtml(assetType.toUpperCase())}</span></td></tr>
                    <tr><td class="text-secondary">File Size:</td><td>${formatFileSize(asset.file_size_bytes || asset.size)}</td></tr>
                    <tr><td class="text-secondary">MIME Type:</td><td>${escapeHtml(asset.mime_type || '—')}</td></tr>
                    <tr><td class="text-secondary">Created:</td><td>${formatDate(asset.created_at)}</td></tr>
                    ${asset.width ? `<tr><td class="text-secondary">Dimensions:</td><td>${asset.width} × ${asset.height}</td></tr>` : ''}
                    ${asset.duration_seconds ? `<tr><td class="text-secondary">Duration:</td><td>${asset.duration_seconds.toFixed(1)}s</td></tr>` : ''}
                </table>
                <div class="mt-3">
                    <a href="${fileUrl}" target="_blank" download="${escapeHtml(displayName)}" class="btn btn-secondary btn-sm">📥 Download Original File</a>
                </div>
            </div>
        </div>
    `;
    panel.scrollIntoView({ behavior: 'smooth' });
}
